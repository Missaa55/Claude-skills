CREATE INDEX jobs_assignee ON jobs(assigned_to);
CREATE INDEX jobs_customer ON jobs(customer_id);
CREATE INDEX materials_job ON materials(job_id);
CREATE INDEX sessions_expiry ON sessions(expires_at);
CREATE INDEX customers_owner ON customers(owner_id);
