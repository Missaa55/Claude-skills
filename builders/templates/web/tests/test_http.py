import http.client
from contextlib import closing
import json
from pathlib import Path
import sqlite3
import tempfile
import threading
import unittest
import server


class WebTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = Path(self.tmp.name) / "test.sqlite3"
        self.http = server.make_server(database=self.db)
        self.thread = threading.Thread(target=self.http.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self):
        self.http.shutdown()
        self.http.server_close()
        self.thread.join(3)
        self.tmp.cleanup()

    def request(self, method="GET", path="/", data=None, headers=None, raw=None):
        conn = http.client.HTTPConnection("127.0.0.1", self.http.server_port, timeout=5)
        extra = {"Content-Type": "application/json", "Origin": f"http://127.0.0.1:{self.http.server_port}", **(headers or {})}
        try:
            conn.request(method, path, raw if raw is not None else json.dumps(data) if data is not None else None, extra)
            response = conn.getresponse()
            return response.status, response.read(), dict(response.getheaders())
        finally:
            conn.close()

    def payload(self):
        return {"name": "Syntetický Test", "email": "synthetic@example.invalid", "message": "Pouze testovací elektroinstalace", "service": "Revize a měření", "consent": True}

    def test_actual_built_site_and_security_headers(self):
        code, body, headers = self.request()
        self.assertEqual(code, 200)
        self.assertIn(b'<html lang="cs">', body)
        self.assertIn("frame-ancestors 'none'", headers["Content-Security-Policy"])
        self.assertEqual(headers["X-Content-Type-Options"], "nosniff")

    def test_real_form_persistence(self):
        self.assertEqual(self.request("POST", "/api/enquiries", self.payload())[0], 201)
        with closing(sqlite3.connect(self.db)) as db, db:
            self.assertEqual(db.execute("SELECT COUNT(*) FROM enquiries").fetchone()[0], 1)

    def test_invalid_data(self):
        for field, value in (("email", "invalid"), ("message", "x"), ("consent", False), ("service", "unknown"), ("name", [])):
            data = self.payload()
            data[field] = value
            self.assertEqual(self.request("POST", "/api/enquiries", data)[0], 422)

    def test_origin_and_size_limits(self):
        self.assertEqual(self.request("POST", "/api/enquiries", self.payload(), {"Origin": "https://attacker.invalid"})[0], 403)
        self.assertEqual(self.request("POST", "/api/enquiries", raw="x"*17000)[0], 413)
        self.assertEqual(self.request("POST", "/api/enquiries", raw="{")[0], 422)

    def test_unknown_paths_and_rate_limit(self):
        self.assertEqual(self.request(path="/../../server.py")[0], 404)
        self.assertEqual(self.request(path="/enquiries.sqlite3")[0], 404)
        for _ in range(10):
            self.assertEqual(self.request("POST", "/api/enquiries", self.payload())[0], 201)
        self.assertEqual(self.request("POST", "/api/enquiries", self.payload())[0], 429)


if __name__ == "__main__":
    unittest.main()
