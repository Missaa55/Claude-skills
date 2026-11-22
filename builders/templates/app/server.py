"""Synthetic job-management reference. Loopback server, SQLite, stdlib only."""
import argparse
from collections import defaultdict, deque
import hashlib
import hmac
from http.cookies import SimpleCookie, CookieError
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import re
import secrets
import sqlite3
import threading
import time
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parent
ROLES = {"admin", "technician", "viewer"}
STATUSES = {"planned", "in_progress", "completed", "cancelled"}
SESSION_SECONDS = 8 * 3600
PASSWORD_PATTERN = re.compile(r"[A-Za-z0-9_-]{3,64}")


class ApiError(Exception):
    def __init__(self, status, message):
        self.status, self.message = status, message


def connect(database):
    db = sqlite3.connect(database, timeout=5)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys=ON")
    return db


def migrate(database):
    db = connect(database)
    try:
        db.execute("CREATE TABLE IF NOT EXISTS schema_migrations(name TEXT PRIMARY KEY,sha256 TEXT NOT NULL)")
        db.commit()
        for path in sorted((ROOT / "migrations").glob("*.sql")):
            data = path.read_text(encoding="utf-8")
            digest = hashlib.sha256(data.encode()).hexdigest()
            db.execute("BEGIN IMMEDIATE")
            try:
                previous = db.execute("SELECT sha256 FROM schema_migrations WHERE name=?", (path.name,)).fetchone()
                if previous and previous[0] != digest:
                    raise ValueError("Applied migration changed; restore original source before continuing")
                if not previous:
                    # Migrations are repository-controlled SQL. No executescript implicit commit.
                    for statement in data.split(";"):
                        if statement.strip():
                            db.execute(statement)
                    db.execute("INSERT INTO schema_migrations VALUES(?,?)", (path.name, digest))
                db.commit()
            except BaseException:
                db.rollback()
                raise
    finally:
        db.close()


def password_hash(password, salt=None):
    if not isinstance(password, str) or not 12 <= len(password) <= 200:
        raise ValueError("Password must contain 12–200 characters")
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, n=16384, r=8, p=1, maxmem=64*1024*1024)
    return "scrypt$16384$8$1$" + salt.hex() + "$" + digest.hex()


def password_matches(password, encoded):
    try:
        kind, n, r, p, salt, digest = encoded.split("$")
        if (kind, n, r, p) != ("scrypt", "16384", "8", "1"):
            return False
        if not isinstance(password, str) or len(password) > 200:
            return False
        actual = hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt), n=16384, r=8, p=1, maxmem=64*1024*1024)
        return hmac.compare_digest(actual.hex(), digest)
    except (ValueError, TypeError):
        return False


def create_user(database, username, password, role="technician"):
    if not PASSWORD_PATTERN.fullmatch(username) or role not in ROLES:
        raise ValueError("Invalid username or role")
    db = connect(database)
    try:
        with db:
            return db.execute("INSERT INTO users(username,password_hash,role) VALUES(?,?,?)", (username, password_hash(password), role)).lastrowid
    finally:
        db.close()


def text(data, key, limit, *, empty=False):
    value = data.get(key)
    if not isinstance(value, str) or not (0 if empty else 1) <= len(value.strip()) <= limit or any(ord(c) < 32 for c in value):
        raise ApiError(422, f"Neplatné pole: {key}")
    return value.strip()


def integer(data, key, low=0, high=100000000):
    value = data.get(key)
    if type(value) is not int or not low <= value <= high:
        raise ApiError(422, f"Neplatné celé číslo: {key}")
    return value


def fields(data, allowed, required=()):
    if set(data) - set(allowed) or set(required) - set(data):
        raise ApiError(422, "Chybějící nebo neznámá pole.")


class Handler(BaseHTTPRequestHandler):
    server_version = "JobReference"

    def setup(self):
        super().setup()
        self.connection.settimeout(10)

    def log_message(self, *_):
        pass  # Do not log cookies, login bodies, customer data or tokens.

    def reply(self, status, value, *, cookie=None, content_type="application/json; charset=utf-8"):
        body = json.dumps(value, ensure_ascii=False).encode() if not isinstance(value, bytes) else value
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Referrer-Policy", "same-origin")
        self.send_header("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
        self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self'; object-src 'none'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'")
        if cookie:
            self.send_header("Set-Cookie", cookie)
        self.end_headers()
        self.wfile.write(body)

    def body(self):
        if self.headers.get("Content-Type", "").split(";")[0] != "application/json":
            raise ApiError(415, "Použijte JSON.")
        try:
            size = int(self.headers.get("Content-Length", "0"))
            if not 1 <= size <= 32768:
                raise ApiError(413, "Nepovolená velikost požadavku.")
            value = json.loads(self.rfile.read(size))
            if not isinstance(value, dict):
                raise ValueError()
            return value
        except (ValueError, UnicodeError):
            raise ApiError(422, "Neplatný JSON.") from None

    def session(self, db):
        try:
            cookies = SimpleCookie()
            cookies.load(self.headers.get("Cookie", ""))
            token = cookies["session"].value
        except (KeyError, CookieError):
            raise ApiError(401, "Přihlaste se.") from None
        if not re.fullmatch(r"[A-Za-z0-9_-]{43}", token):
            raise ApiError(401, "Přihlaste se.")
        row = db.execute("SELECT users.*,sessions.csrf_token,sessions.token_hash FROM sessions JOIN users ON users.id=sessions.user_id WHERE token_hash=? AND expires_at>?", (hashlib.sha256(token.encode()).hexdigest(), int(time.time()))).fetchone()
        if not row:
            raise ApiError(401, "Platnost přihlášení skončila.")
        return row

    def require_write(self, user):
        if user["role"] == "viewer":
            raise ApiError(403, "Máte oprávnění pouze ke čtení.")
        if not hmac.compare_digest(self.headers.get("X-CSRF-Token", ""), user["csrf_token"]):
            raise ApiError(403, "Neplatný bezpečnostní token.")

    def scoped(self, db, table, identity, user):
        row = db.execute(f"SELECT * FROM {table} WHERE id=?", (identity,)).fetchone()
        owner = "owner_id" if table == "customers" else "assigned_to"
        if row is None or user["role"] == "technician" and row[owner] != user["id"]:
            raise ApiError(404, "Záznam neexistuje.")
        return row

    def job(self, db, identity, user):
        result = dict(self.scoped(db, "jobs", identity, user))
        result["materials"] = [dict(row) for row in db.execute("SELECT * FROM materials WHERE job_id=? ORDER BY id", (identity,))]
        result["material_total_cents"] = sum(row["quantity"] * row["unit_price_cents"] for row in result["materials"])
        result["total_cents"] = result["labor_cents"] + result["material_total_cents"]
        return result

    def route(self, db, method, path):
        if path == "/api/login" and method == "POST":
            data = self.body()
            fields(data, ("username", "password"), ("username", "password"))
            username = text(data, "username", 64)
            password = data.get("password")
            with self.server.rate_lock:
                rate = self.server.attempts[self.client_address[0]]
                now = time.monotonic()
                while rate and now - rate[0] > 60:
                    rate.popleft()
                if len(rate) >= 10:
                    raise ApiError(429, "Příliš mnoho pokusů. Počkejte minutu.")
                rate.append(now)
            user = db.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
            # A fixed dummy hash avoids an obvious missing-username fast path.
            encoded = user["password_hash"] if user else self.server.dummy_hash
            if not password_matches(password, encoded) or user is None:
                raise ApiError(401, "Nesprávné přihlašovací údaje.")
            token, csrf = secrets.token_urlsafe(32), secrets.token_urlsafe(24)
            db.execute("DELETE FROM sessions WHERE expires_at<=?", (int(time.time()),))
            db.execute("INSERT INTO sessions VALUES(?,?,?,?)", (hashlib.sha256(token.encode()).hexdigest(), user["id"], csrf, int(time.time()) + SESSION_SECONDS))
            db.commit()
            return self.reply(200, {"username": username, "role": user["role"], "csrf_token": csrf}, cookie=f"session={token}; HttpOnly; SameSite=Strict; Path=/; Max-Age={SESSION_SECONDS}")
        user = self.session(db)
        if path == "/api/me" and method == "GET":
            return self.reply(200, {"id": user["id"], "username": user["username"], "role": user["role"], "csrf_token": user["csrf_token"]})
        if method != "GET":
            self.require_write(user) if path != "/api/logout" else self.check_logout(user)
        if path == "/api/logout" and method == "POST":
            db.execute("DELETE FROM sessions WHERE token_hash=?", (user["token_hash"],))
            db.commit()
            return self.reply(200, {"ok": True}, cookie="session=; HttpOnly; SameSite=Strict; Path=/; Max-Age=0")
        if path == "/api/users" and method == "GET":
            if user["role"] != "admin":
                raise ApiError(403, "Vyžaduje správce.")
            return self.reply(200, [dict(row) for row in db.execute("SELECT id,username,role FROM users ORDER BY id")])
        match = re.fullmatch(r"/api/(customers|jobs|materials)(?:/([1-9][0-9]{0,9}))?(?:/(materials))?", path)
        if not match:
            raise ApiError(404, "Neznámý požadavek.")
        table, identity, nested = match.groups()
        identity = int(identity) if identity else None
        if nested and (table != "jobs" or identity is None):
            raise ApiError(404, "Neznámý požadavek.")
        if table == "materials" or nested:
            if nested:
                self.scoped(db, "jobs", identity, user)
                if method != "POST":
                    raise ApiError(405, "Nepodporovaná metoda.")
                material, job_id = None, identity
            else:
                material = db.execute("SELECT * FROM materials WHERE id=?", (identity,)).fetchone()
                if not material:
                    raise ApiError(404, "Položka neexistuje.")
                job_id = material["job_id"]
                self.scoped(db, "jobs", job_id, user)
            if method == "DELETE" and material:
                db.execute("DELETE FROM materials WHERE id=?", (identity,))
                db.commit()
                return self.reply(200, {"ok": True})
            if method not in ("POST", "PATCH") or method == "POST" and material:
                raise ApiError(405, "Nepodporovaná metoda.")
            data = self.body()
            fields(data, ("name", "quantity", "unit_price_cents"), ("name", "quantity", "unit_price_cents"))
            values = (text(data, "name", 160), integer(data, "quantity", 1, 10000), integer(data, "unit_price_cents"))
            if material:
                db.execute("UPDATE materials SET name=?,quantity=?,unit_price_cents=? WHERE id=?", (*values, identity))
            else:
                identity = db.execute("INSERT INTO materials(name,quantity,unit_price_cents,job_id) VALUES(?,?,?,?)", (*values, job_id)).lastrowid
            db.commit()
            return self.reply(200 if material else 201, {"id": identity, "job": self.job(db, job_id, user)})
        if identity is None and method == "GET":
            owner = "owner_id" if table == "customers" else "assigned_to"
            where, args = (f" WHERE {owner}=?", (user["id"],)) if user["role"] == "technician" else ("", ())
            rows = db.execute(f"SELECT * FROM {table}{where} ORDER BY id DESC LIMIT 500", args).fetchall()
            return self.reply(200, [dict(row) if table == "customers" else self.job(db, row["id"], user) for row in rows])
        previous = self.scoped(db, table, identity, user) if identity else None
        if previous and method == "GET":
            return self.reply(200, dict(previous) if table == "customers" else self.job(db, identity, user))
        if previous and method == "DELETE":
            db.execute(f"DELETE FROM {table} WHERE id=?", (identity,))
            db.commit()
            return self.reply(200, {"ok": True})
        if method not in ("POST", "PATCH") or (method == "POST") != (identity is None):
            raise ApiError(405, "Nepodporovaná metoda.")
        data = self.body()
        if table == "customers":
            fields(data, ("name", "email", "phone"), ("name", "email"))
            name, email = text(data, "name", 120), text(data, "email", 254)
            phone = text({"phone": data.get("phone", "")}, "phone", 40, empty=True)
            if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", email):
                raise ApiError(422, "Neplatný e-mail.")
            if previous:
                db.execute("UPDATE customers SET name=?,email=?,phone=? WHERE id=?", (name, email, phone, identity))
            else:
                identity = db.execute("INSERT INTO customers(name,email,phone,owner_id) VALUES(?,?,?,?)", (name, email, phone, user["id"])).lastrowid
        else:
            fields(data, ("title", "customer_id", "assigned_to", "status", "labor_cents"), ("title", "customer_id"))
            title, customer_id = text(data, "title", 160), integer(data, "customer_id", 1)
            self.scoped(db, "customers", customer_id, user)
            status = data.get("status", previous["status"] if previous else "planned")
            if not isinstance(status, str) or status not in STATUSES:
                raise ApiError(422, "Neplatný stav zakázky.")
            labor = integer({"labor_cents": data.get("labor_cents", previous["labor_cents"] if previous else 0)}, "labor_cents")
            assignee = integer({"assigned_to": data.get("assigned_to", previous["assigned_to"] if previous else user["id"])}, "assigned_to", 1)
            if assignee != user["id"] and user["role"] != "admin":
                raise ApiError(403, "Přiřazení jiné osobě vyžaduje správce.")
            if not db.execute("SELECT 1 FROM users WHERE id=? AND role!='viewer'", (assignee,)).fetchone():
                raise ApiError(422, "Neplatný řešitel.")
            values = (title, customer_id, assignee, status, labor)
            if previous:
                db.execute("UPDATE jobs SET title=?,customer_id=?,assigned_to=?,status=?,labor_cents=? WHERE id=?", (*values, identity))
            else:
                identity = db.execute("INSERT INTO jobs(title,customer_id,assigned_to,status,labor_cents) VALUES(?,?,?,?,?)", values).lastrowid
        db.commit()
        return self.reply(200 if previous else 201, dict(db.execute("SELECT * FROM customers WHERE id=?", (identity,)).fetchone()) if table == "customers" else self.job(db, identity, user))

    def check_logout(self, user):
        if not hmac.compare_digest(self.headers.get("X-CSRF-Token", ""), user["csrf_token"]):
            raise ApiError(403, "Neplatný bezpečnostní token.")

    def handle_request(self):
        path = urlsplit(self.path).path
        allowed_hosts = {f"127.0.0.1:{self.server.server_port}", f"localhost:{self.server.server_port}"}
        if self.headers.get("Host") not in allowed_hosts:
            return self.reply(403, {"error": "Nepovolený hostitel."})
        if self.command != "GET" and self.headers.get("Origin") not in {f"http://{host}" for host in allowed_hosts}:
            return self.reply(403, {"error": "Nepovolený původ požadavku."})
        if not path.startswith("/api/"):
            static = {"/": ("index.html", "text/html; charset=utf-8"), "/app.js": ("app.js", "text/javascript; charset=utf-8"), "/app.css": ("app.css", "text/css; charset=utf-8")}
            if self.command != "GET" or path not in static:
                return self.reply(404, {"error": "Stránka neexistuje."})
            name, kind = static[path]
            return self.reply(200, (ROOT / "static" / name).read_bytes(), content_type=kind)
        db = connect(self.server.database)
        try:
            self.route(db, self.command, path)
        except ApiError as exc:
            db.rollback()
            self.reply(exc.status, {"error": exc.message})
        except sqlite3.IntegrityError:
            db.rollback()
            self.reply(409, {"error": "Záznam je používán nebo odporuje databázovým pravidlům."})
        except sqlite3.Error:
            db.rollback()
            self.reply(503, {"error": "Databáze je dočasně nedostupná."})
        finally:
            db.close()

    do_GET = do_POST = do_PATCH = do_DELETE = handle_request


def make_server(database, port=0):
    migrate(database)
    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    server.database = database
    server.attempts, server.rate_lock = defaultdict(deque), threading.Lock()
    server.dummy_hash = password_hash("synthetic-dummy-password-only", b"0" * 16)
    return server


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("init", "serve"))
    parser.add_argument("--db", type=Path, default=ROOT / "jobs.sqlite3")
    parser.add_argument("--port", type=int, default=8787)
    parser.add_argument("--demo", action="store_true")
    args = parser.parse_args()
    if args.db.is_symlink() or (hasattr(args.db, "is_junction") and args.db.is_junction()):
        parser.error("Linked database rejected")
    if args.command == "init":
        migrate(args.db)
        if args.demo:
            password = secrets.token_urlsafe(16)
            create_user(args.db, "demo_admin", password, "admin")
            print(f"Synthetic demo account: demo_admin\nOne-time generated password: {password}")
    else:
        server = make_server(args.db, args.port)
        print(f"Local: http://127.0.0.1:{server.server_port}", flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
        finally:
            server.server_close()
