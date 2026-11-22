"""Real HTTP + SQLite integration, exclusively synthetic users and customers."""
import hashlib
from contextlib import closing
import http.client
import json
from pathlib import Path
import sqlite3
import tempfile
import threading
import time
import unittest
import server

PASSWORD = "Synthetic-only-passphrase7!"


class ApiTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = Path(self.tmp.name) / "test.sqlite3"
        server.migrate(self.db)
        self.admin = server.create_user(self.db, "admin_test", PASSWORD, "admin")
        self.tech = server.create_user(self.db, "tech_test", PASSWORD, "technician")
        self.viewer = server.create_user(self.db, "viewer_test", PASSWORD, "viewer")
        self.http = server.make_server(self.db)
        self.thread = threading.Thread(target=self.http.serve_forever, daemon=True)
        self.thread.start()
        self.cookie, self.csrf = "", ""
        self.login()

    def tearDown(self):
        self.http.shutdown()
        self.http.server_close()
        self.thread.join(3)
        self.tmp.cleanup()

    def request(self, path, method="GET", data=None, headers=None, raw=None):
        conn = http.client.HTTPConnection("127.0.0.1", self.http.server_port, timeout=5)
        extra = {"Content-Type": "application/json", "Origin": f"http://127.0.0.1:{self.http.server_port}", "Cookie": self.cookie, "X-CSRF-Token": self.csrf, **(headers or {})}
        body = raw if raw is not None else json.dumps(data) if data is not None else None
        try:
            conn.request(method, path, body, extra)
            response = conn.getresponse()
            payload = response.read()
            return response.status, json.loads(payload) if "application/json" in response.getheader("Content-Type", "") else payload, dict(response.getheaders())
        finally:
            conn.close()

    def login(self, username="admin_test"):
        code, data, headers = self.request("/api/login", "POST", {"username": username, "password": PASSWORD})
        self.assertEqual(code, 200)
        self.cookie, self.csrf = headers["Set-Cookie"].split(";", 1)[0], data["csrf_token"]
        return headers

    def customer(self, name="Syntetický zákazník"):
        code, data, _ = self.request("/api/customers", "POST", {"name": name, "email": "synthetic@example.invalid", "phone": ""})
        self.assertEqual(code, 201, data)
        return data["id"]

    def job(self):
        code, data, _ = self.request("/api/jobs", "POST", {"title": "Test rozvaděče", "customer_id": self.customer(), "labor_cents": 10005})
        self.assertEqual(code, 201, data)
        return data["id"]

    def test_password_scrypt_salted(self):
        first, second = server.password_hash(PASSWORD), server.password_hash(PASSWORD)
        self.assertNotEqual(first, second)
        self.assertTrue(server.password_matches(PASSWORD, first))
        self.assertFalse(server.password_matches("incorrect", first))

    def test_migrations_idempotent_and_recorded(self):
        server.migrate(self.db)
        with closing(sqlite3.connect(self.db)) as db, db:
            self.assertEqual(db.execute("SELECT COUNT(*) FROM schema_migrations").fetchone()[0], 2)

    def test_migration_checksum_conflict_rejected(self):
        with closing(sqlite3.connect(self.db)) as db, db:
            db.execute("UPDATE schema_migrations SET sha256='tampered'")
        with self.assertRaises(ValueError):
            server.migrate(self.db)

    def test_cookie_and_hashed_session(self):
        headers = self.login()
        self.assertIn("HttpOnly", headers["Set-Cookie"])
        self.assertIn("SameSite=Strict", headers["Set-Cookie"])
        token = self.cookie.split("=", 1)[1]
        with closing(sqlite3.connect(self.db)) as db, db:
            self.assertIsNotNone(db.execute("SELECT 1 FROM sessions WHERE token_hash=?", (hashlib.sha256(token.encode()).hexdigest(),)).fetchone())
            self.assertIsNone(db.execute("SELECT 1 FROM sessions WHERE token_hash=?", (token,)).fetchone())

    def test_no_auth_and_expired_auth(self):
        with closing(sqlite3.connect(self.db)) as db, db:
            db.execute("UPDATE sessions SET expires_at=0")
        self.assertEqual(self.request("/api/jobs")[0], 401)
        self.cookie = ""
        self.assertEqual(self.request("/api/customers")[0], 401)

    def test_bad_password_and_sql_injection_login(self):
        for username, password in (("admin_test", "wrong-password"), ("' OR 1=1 --", PASSWORD)):
            self.assertEqual(self.request("/api/login", "POST", {"username": username, "password": password})[0], 401)

    def test_rate_limit(self):
        for _ in range(10):
            code, _, _ = self.request("/api/login", "POST", {"username": "missing", "password": PASSWORD})
        self.assertEqual(code, 429)

    def test_csrf_and_cross_origin_rejected(self):
        self.assertEqual(self.request("/api/customers", "POST", {}, {"X-CSRF-Token": "wrong"})[0], 403)
        self.assertEqual(self.request("/api/customers", "POST", {}, {"Origin": "https://attacker.invalid"})[0], 403)
        self.assertEqual(self.request("/api/jobs", headers={"Host": "attacker.invalid"})[0], 403)

    def test_customers_crud_and_literal_sql_payload(self):
        identity = self.customer("Robert'); DROP TABLE customers; --")
        self.assertEqual(self.request(f"/api/customers/{identity}")[1]["name"], "Robert'); DROP TABLE customers; --")
        self.assertEqual(self.request(f"/api/customers/{identity}", "PATCH", {"name": "Upravený syntetický", "email": "edit@example.invalid"})[0], 200)
        self.assertEqual(self.request(f"/api/customers/{identity}", "DELETE")[0], 200)
        self.assertEqual(self.request(f"/api/customers/{identity}")[0], 404)

    def test_invalid_inputs_and_unknown_fields(self):
        for payload in ({"name": "", "email": "x"}, {"name": "Valid", "email": "invalid"}, {"name": "Valid", "email": "test@example.invalid", "role": "admin"}):
            self.assertEqual(self.request("/api/customers", "POST", payload)[0], 422)
        customer = self.customer()
        for payload in ({"title": "x", "customer_id": True}, {"title": "x", "customer_id": customer, "labor_cents": -1}, {"title": "x", "customer_id": customer, "status": "nonsense"}):
            self.assertEqual(self.request("/api/jobs", "POST", payload)[0], 422)

    def test_invalid_json_and_body_limits(self):
        self.assertEqual(self.request("/api/jobs", "POST", raw="{")[0], 422)
        self.assertEqual(self.request("/api/jobs", "POST", raw="[]")[0], 422)
        self.assertEqual(self.request("/api/jobs", "POST", raw="x"*33000)[0], 413)
        self.assertEqual(self.request("/api/jobs", "POST", {}, {"Content-Type": "text/plain"})[0], 415)

    def test_job_materials_calculation_and_crud(self):
        identity = self.job()
        code, material, _ = self.request(f"/api/jobs/{identity}/materials", "POST", {"name": "CYKY test", "quantity": 3, "unit_price_cents": 1099})
        self.assertEqual(code, 201)
        self.assertEqual(material["job"]["total_cents"], 13302)
        item = material["id"]
        self.assertEqual(self.request(f"/api/materials/{item}", "PATCH", {"name": "CYKY změna", "quantity": 2, "unit_price_cents": 1005})[0], 200)
        job = self.request(f"/api/jobs/{identity}")[1]
        self.assertEqual(job["total_cents"], 12015)
        self.assertEqual(self.request(f"/api/jobs/{identity}", "PATCH", {"title": "Hotovo", "customer_id": job["customer_id"], "status": "completed", "labor_cents": 10005})[0], 200)
        self.assertEqual(self.request(f"/api/customers/{job['customer_id']}", "DELETE")[0], 409)
        self.assertEqual(self.request(f"/api/materials/{item}", "DELETE")[0], 200)
        self.assertEqual(self.request(f"/api/jobs/{identity}", "DELETE")[0], 200)

    def test_authorization_and_object_isolation(self):
        identity = self.job()
        self.login("tech_test")
        self.assertEqual(self.request(f"/api/jobs/{identity}")[0], 404)
        self.assertEqual(self.request(f"/api/jobs/{identity}", "DELETE")[0], 404)
        self.assertEqual(self.request("/api/jobs")[1], [])
        self.assertEqual(self.request("/api/customers")[1], [])
        self.assertEqual(self.request("/api/users")[0], 403)
        mine = self.customer()
        self.assertEqual(self.request("/api/jobs", "POST", {"title": "Attempt", "customer_id": mine, "assigned_to": self.admin})[0], 403)

    def test_viewer_read_only_and_logout(self):
        self.job()
        self.login("viewer_test")
        self.assertEqual(len(self.request("/api/jobs")[1]), 1)
        self.assertEqual(self.request("/api/customers", "POST", {})[0], 403)
        self.assertEqual(self.request("/api/logout", "POST", {})[0], 200)
        self.assertEqual(self.request("/api/jobs")[0], 401)

    def test_assigned_technician_can_access_attached_customer(self):
        customer = self.customer()
        code, job, _ = self.request("/api/jobs", "POST", {"title": "Assigned test", "customer_id": customer, "assigned_to": self.tech})
        self.assertEqual(code, 201)
        self.login("tech_test")
        self.assertEqual(self.request(f"/api/customers/{customer}")[0], 200)
        self.assertEqual(len(self.request("/api/customers")[1]), 1)
        self.assertEqual(self.request(f"/api/jobs/{job['id']}", "PATCH", {"title": "Working", "customer_id": customer, "status": "in_progress"})[0], 200)

    def test_static_headers_and_missing_paths(self):
        code, body, headers = self.request("/")
        self.assertEqual(code, 200)
        self.assertIn(b"<!doctype html>", body)
        self.assertIn("frame-ancestors 'none'", headers["Content-Security-Policy"])
        self.assertEqual(headers["X-Content-Type-Options"], "nosniff")
        for path in ("/../server.py", "/jobs.sqlite3", "/api/missing"):
            self.assertEqual(self.request(path)[0], 404)

    def test_persistence_across_connections(self):
        identity = self.customer()
        with closing(sqlite3.connect(self.db)) as db, db:
            self.assertEqual(db.execute("SELECT name FROM customers WHERE id=?", (identity,)).fetchone()[0], "Syntetický zákazník")


if __name__ == "__main__":
    unittest.main()
