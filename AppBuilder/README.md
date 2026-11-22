# AppBuilder

Independent runtime, four portable skills and a runnable reference job-management app.
The reference uses Python's standard library, SQLite and browser-native HTML/CSS/JS.
It includes sessions, admin/technician/viewer permissions, customers, jobs, status,
materials, integer-cent prices and REST endpoints. All example data is synthetic.

```bash
python -m core.builder_cli create --spec examples/briefs/app.json --workspace ../new-app
python -m core.builder_cli check app --workspace ../new-app --execute --trusted-local
python ../new-app/server.py init --demo
python ../new-app/server.py serve --port 8787
```

Review source before host execution. Initialization generates a new demo password;
no default credentials or public registration endpoint exists. Admin manages all records;
technicians access their assigned jobs and associated/owned customers; viewers read only.
Mutations require same-origin JSON requests and a per-session CSRF token. Passwords use
salted scrypt; session tokens are stored as hashes and expire. Material/calculation logic
uses integers, never floating point money.

`build.py` produces a runnable `dist/` with server/static/migrations. The integration
suite starts actual loopback HTTP servers and disposable SQLite databases; browser QA
exercises real user journeys. Migration checksums reject changed applied migrations.

Installation: `python -m distribution.cli install app`. The installed launcher is
`appbuilder-orchestrator/runtime/builder.py`, with its own matching example brief.
No Minecraft/WebBuilder or additional skill collection is required.

This is a local reference, not a public production server: TLS/reverse proxy, operational
backups, pagination beyond the 500-record list cap, password reset and broader production
hardening are outside the current implementation. Authenticated free-form Claude/Codex
generation is NOT VERIFIED. Read the repository verification report before claiming readiness.
