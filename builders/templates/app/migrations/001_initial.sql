CREATE TABLE users (
 id INTEGER PRIMARY KEY, username TEXT NOT NULL UNIQUE,
 password_hash TEXT NOT NULL, role TEXT NOT NULL CHECK(role IN ('admin','technician','viewer'))
);
CREATE TABLE sessions (
 token_hash TEXT PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
 csrf_token TEXT NOT NULL, expires_at INTEGER NOT NULL
);
CREATE TABLE customers (
 id INTEGER PRIMARY KEY, name TEXT NOT NULL CHECK(length(name) BETWEEN 1 AND 120),
 email TEXT NOT NULL, phone TEXT NOT NULL DEFAULT '',
 owner_id INTEGER NOT NULL REFERENCES users(id)
);
CREATE TABLE jobs (
 id INTEGER PRIMARY KEY, title TEXT NOT NULL CHECK(length(title) BETWEEN 1 AND 160),
 customer_id INTEGER NOT NULL REFERENCES customers(id) ON DELETE RESTRICT,
 assigned_to INTEGER NOT NULL REFERENCES users(id),
 status TEXT NOT NULL DEFAULT 'planned' CHECK(status IN ('planned','in_progress','completed','cancelled')),
 labor_cents INTEGER NOT NULL DEFAULT 0 CHECK(labor_cents BETWEEN 0 AND 100000000),
 created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE materials (
 id INTEGER PRIMARY KEY, job_id INTEGER NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
 name TEXT NOT NULL CHECK(length(name) BETWEEN 1 AND 160),
 quantity INTEGER NOT NULL CHECK(quantity BETWEEN 1 AND 10000),
 unit_price_cents INTEGER NOT NULL CHECK(unit_price_cents BETWEEN 0 AND 100000000)
);
