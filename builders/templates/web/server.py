"""Loopback-only reference server. Stores synthetic enquiries, sends no mail."""
import argparse
from collections import defaultdict, deque
from contextlib import closing
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import re
import sqlite3
import threading
import time
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parent
SERVICES = {"Rekonstrukce elektroinstalace", "Nová elektroinstalace", "Revize a měření", "Chytrá domácnost"}


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT / "dist"), **kwargs)

    def end_headers(self):
        self.send_header("Content-Security-Policy", "default-src 'self'; img-src 'self' data:; script-src 'self'; style-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'; form-action 'self'")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "strict-origin-when-cross-origin")
        self.send_header("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def log_message(self, *_):
        pass

    def reply(self, code, value):
        data = json.dumps(value, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        path = urlsplit(self.path).path
        if path not in ("/", "/index.html", "/style.css", "/site.js", "/mark.svg", "/build-manifest.json"):
            return self.reply(404, {"error": "Stránka neexistuje."})
        super().do_GET()

    def do_POST(self):
        if self.path != "/api/enquiries":
            return self.reply(404, {"error": "Neznámý požadavek."})
        expected = f"http://{self.server.server_name}:{self.server.server_port}"
        allowed = {expected, f"http://127.0.0.1:{self.server.server_port}", f"http://localhost:{self.server.server_port}"}
        if self.headers.get("Origin") not in allowed or self.headers.get("Content-Type", "").split(";")[0] != "application/json":
            return self.reply(403, {"error": "Požadavek není povolen."})
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if not 1 <= length <= 16000:
                return self.reply(413, {"error": "Příliš velký požadavek."})
            data = json.loads(self.rfile.read(length))
            if not isinstance(data, dict) or set(data) != {"name", "email", "message", "service", "consent"}:
                raise ValueError()
            if any(not isinstance(data.get(k), str) for k in ("name", "email", "message", "service")):
                raise ValueError()
            if not 1 <= len(data["name"].strip()) <= 100 or not 10 <= len(data["message"].strip()) <= 3000:
                raise ValueError()
            if len(data["email"]) > 254 or not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", data["email"]):
                raise ValueError()
            if data["service"] not in SERVICES or data["consent"] is not True:
                raise ValueError()
        except (ValueError, UnicodeError):
            return self.reply(422, {"error": "Zkontrolujte jméno, e-mail, popis a souhlas."})
        with self.server.rate_lock:
            rate = self.server.rate[self.client_address[0]]
            now = time.monotonic()
            while rate and now - rate[0] > 60:
                rate.popleft()
            if len(rate) >= 10:
                return self.reply(429, {"error": "Příliš mnoho pokusů. Zkuste to za minutu."})
            rate.append(now)
        try:
            with closing(sqlite3.connect(self.server.database)) as db, db:
                cur = db.execute("INSERT INTO enquiries(name,email,service,message) VALUES(?,?,?,?)", tuple(data[k].strip() for k in ("name", "email", "service", "message")))
                identity = cur.lastrowid
        except sqlite3.Error:
            return self.reply(503, {"error": "Úložiště je dočasně nedostupné. Zkuste to znovu."})
        self.reply(201, {"id": identity, "synthetic": True})


def make_server(port=0, database=None):
    database = database or ROOT / "enquiries.sqlite3"
    with closing(sqlite3.connect(database)) as db, db:
        db.execute("CREATE TABLE IF NOT EXISTS enquiries(id INTEGER PRIMARY KEY,name TEXT NOT NULL,email TEXT NOT NULL,service TEXT NOT NULL,message TEXT NOT NULL)")
    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    server.database, server.rate, server.rate_lock = database, defaultdict(deque), threading.Lock()
    return server


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8080)
    parser.add_argument("--db", type=Path)
    args = parser.parse_args()
    server = make_server(args.port, args.db)
    print(f"Local: http://127.0.0.1:{server.server_port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
