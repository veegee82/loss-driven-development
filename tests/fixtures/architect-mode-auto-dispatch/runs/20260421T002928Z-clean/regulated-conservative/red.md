<!-- captured via scripts/capture-red-green.py
     model: openai/gpt-5-mini
     temperature: 0.7
     scenario: regulated-conservative
     prompt: 'design a medical records ingestion service for our HIPAA-regulated stack — must use our existing Postgres+Python stack, no new tech, 6-week deadline, team of 2, production-critical' -->

Below is a pragmatic, HIPAA-focused design you can implement in 6 weeks with a two-person team using only your existing Python + Postgres stack (no new tech). It’s intentionally conservative and buildable: minimal moving parts, no new infra dependencies (no new message broker, S3, or external services), while meeting HIPAA controls for PHI handling, auditing, and availability.

If anything below assumes an existing component you don’t have (web framework, secrets store, backup process), call it out now and I’ll adjust the plan to your environment.

High-level goals (MVP)
- Securely accept medical records from integrations (structured JSON/FHIR, HL7 or files like PDF).
- Validate, normalize minimal metadata, persist encrypted at rest.
- Expose secure API for ingestion and status checks.
- Robust audit trail of every action with immutable records.
- Operable in production: monitoring, alerting, backup/restore, and an incident runbook.
- Deliverable in 6 weeks by 2 engineers.

Core constraints
- Technology: Python + Postgres only. Use your existing Python web framework (Flask/Django/FastAPI) and ORM (SQLAlchemy/Django ORM). Use Alembic or your current migration tooling.
- No new external services. If you currently use object storage or KMS, you can leverage them; if not, the design keeps everything in Postgres.
- HIPAA compliance: encryption in transit & at rest, least privilege, audit logs, breach detection & notification readiness.

1) System architecture (minimal, no new tech)
- Ingestion API (Python app): HTTP(S) endpoints protected by your existing auth mechanism.
  - Accepts structured JSON (FHIR/your schema), HL7 plaintext, or file uploads (PDF, images).
  - Performs schema/basic content validation and metadata extraction.
  - Inserts metadata + encryption-wrapped payload into Postgres.
  - Creates an ingestion job record for asynchronous processing.
- Worker process (same Python codebase, run as background worker/service):
  - Periodically polls a Postgres jobs table and picks up jobs using Postgres advisory locks (no message broker needed).
  - Performs heavier processing (format-specific parsing, text extraction, de-dup, indexing) and updates status.
- Postgres (single authoritative store):
  - Tables for patients (if needed), records, attachments, ingestion_jobs, audit_logs, and system configuration.
  - Payloads stored encrypted (bytea) if object storage is not available.
- Monitoring & alerting: integrate with your existing monitoring stack (CPU, DB size, slow queries, job backlog, exceptions).
- Backups and DR: use your platform’s Postgres backup mechanism (logical or base backups) and test restore.

2) Data model (DDL sketch)
Use explicit audit trail and minimal PHI in cleartext. Encrypt sensitive fields.

Example tables (simplified):

- records
  - id (PK)
  - patient_id (nullable) -- link or hashed identifier
  - record_type (e.g., FHIR:Observation, PDF, HL7)
  - status (ingested/processing/complete/failed)
  - created_at, updated_at
  - metadata jsonb (non-PHI metadata: source, external_id, mime_type, size)
  - encrypted_payload bytea (AES-GCM encrypted content)
  - payload_checksum text (SHA256)
  - blob_storage_ref text (nullable, if you have external storage)
- ingestion_jobs
  - id
  - record_id (FK)
  - attempt_count int
  - locked_by text
  - lock_at timestamptz
  - next_retry_at timestamptz
  - error_message text
  - created_at, updated_at
- audit_logs (immutable)
  - id
  - target_table text
  - target_id uuid
  - action text (CREATE/UPDATE/DELETE/ACCESS)
  - actor text (user/service id)
  - details jsonb (non-sensitive)
  - created_at timestamptz
- access_events (for access auditing / breach detection)
  - id
  - record_id
  - accessed_by
  - access_purpose
  - access_time
  - access_method
- users/clients (if you manage clients) - store minimal auth metadata and roles

Encryption notes:
- Payload encryption: application-level AES-256-GCM encryption. Implement encryption/decryption in Python app at write/read time.
- Store only ciphertext in encrypted_payload. Never log plaintext payloads.
- Keys: must be stored in your existing secrets management. If you don’t have one, use environment variables deployed via CI/CD secrets (short-term) but plan to adopt a KMS. Document this as a compliance gap if no KMS exists.

3) Ingestion flow (step-by-step)
Synchronous API path (for real-time integrations):
1. Client authenticates with your existing auth (client certificate / token).
2. Client POSTs record: metadata + payload (JSON or file).
3. API validates size limits, content type, and basic schema checks.
4. Compute payload_checksum (SHA-256) and check recent duplicates (optional).
5. Encrypt payload and insert a record into records table with status=ingested.
6. Create ingestion_job row linked to the record.
7. Return 202 Accepted + job_id to client.

Asynchronous processing (worker):
1. Worker polls ingestion_jobs for status=queued and next_retry_at <= now.
2. Acquire lock via Postgres advisory lock on ingestion_job.id. Mark locked_by and lock_at.
3. Process payload: parse FHIR/HL7, extract key fields, normalize, attach indexing metadata.
4. Update records.metadata and set status=complete or failed with error details.
5. Record audit logs for processing steps and any access to PHI.
6. Release lock and update ingestion_job (completed or scheduled retry).

Why advisory locks: fits constraint of no new queue tech and avoids race conditions.

4) Security & HIPAA controls (must-haves)
- Transport: enforce HTTPS/TLS for all endpoints; disable old TLS versions. Use your existing cert management.
- Authentication & authorization:
  - Integrate with your existing identity provider. Use short-lived tokens. If none exists, require client certificates or long tokens rotated regularly.
  - Implement RBAC: only specific service accounts/roles can ingest, others can only read limited metadata or status.
  - Enforce principle of least privilege in DB credentials.
- Encryption:
  - In transit: TLS only.
  - At rest: application-level encryption of PHI payloads (AES-256-GCM). Use Postgres transparent encryption only if your infra supports it, but application-level encryption gives defense-in-depth.
  - Encrypt DB backups.
- Audit logging:
  - Immutable audit_logs and access_events tables that record who accessed what and why.
  - Write audit logs in same transaction as data changes to ensure consistency.
  - Restrict who can query full audit tables; keep a separate aggregated metrics view for ops.
- Key management:
  - Keys in your existing secrets manager. If none, keys in environment variables with strict rotation process.
  - Rotate data encryption keys: implement envelope encryption plan (data encrypted by DEK; DEKs encrypted by KEK).
- Data minimization:
  - Only store PHI required by the product.
  - Keep metadata (create_by, source) but avoid storing unnecessary identifiers in cleartext.
- Logging hygiene:
  - Ensure app logs do not include PHI. Sanitize exceptions and payloads.
  - Store logs in your existing logging system, and restrict log access to authorized personnel.
- Backups & DR:
  - Schedule encrypted backups; document retention and deletion timelines.
  - Regularly test restores in non-prod with scrubbed data.
- Incident response:
  - Have breach notification playbook and roles (legal, security, engineering). Logging must support root cause analysis.
- BAAs:
  - Document Business Associate Agreements for any third party that handles PHI (e.g., if you use a managed Postgres provider).

5) Reliability, performance & scaling
- Start simple:
  - Worker concurrency controlled by number of worker processes. Use multiple worker processes/instances for throughput.
  - Scale horizontally at the app layer behind your existing load balancer.
- DB sizing:
  - Avoid storing large binary blobs inline forever. If you hit size issues, move to an external blob store (plan but do not implement new tech in MVP).
  - Use partitioning for records table by ingestion date after steady state to limit table size impact on queries (Postgres native).
- Backpressure and rate limiting:
  - Enforce per-client rate limits (use existing API gateway or implement simple token bucket).
  - Reject oversized uploads and return meaningful errors.
- Monitoring & alerting:
  - Monitor ingestion queue length (ingestion_jobs backlog), rate of failures, worker CPU, DB growth, long-running transactions.
  - Alerts: ingestion backlog > threshold, repeated client auth failures, DB size growth > threshold, missing backups or failed restores.
- Fault tolerance:
  - Worker retries with exponential backoff; move to error queue after N attempts.
  - Idempotency: support idempotent ingestion using client-supplied idempotency_key or checksum dedupe.

6) Testing strategy
- Unit tests for encryption/decryption, DB ops, and validation.
- Integration tests against a test Postgres instance (CI).
- Contract tests for ingestion API: positive and negative cases, large payloads, invalid payloads.
- Security tests: ensure no PHI ends up in logs, keys not in code, TLS enforced.
- Load tests: simulate expected peak + 2x to validate worker throughput and DB behavior. Use your existing tooling.
- Backup & restore test: perform weekly restores into dev environment to ensure procedures work.

7) Observability & operations
- Metrics to emit:
  - ingestion_count, ingestion_success_rate, ingestion_latency, job_backlog, worker_errors, DB_size_bytes, encrypted_payload_size.
- Logs:
  - Structured logs with request IDs and non-PHI metadata. Ensure logs can be filtered by request ID for debugging.
- Dashboard:
  - Ingestion queue backlog, failure rates, 95/99th latency, DB size trends.
- Runbook (short):
  - How to restart workers.
  - How to reprocess failed records (retry endpoint or manual job restart).
  - How to rotate encryption keys.
  - How to restore from backup and failover DB.
  - How to handle a suspected breach: freeze ingestion, preserve logs, notify security/legal, begin investigation.

8) API surface (MVP)
POST /v1/ingest
- Auth required
- Payload: multipart/form-data (file) OR application/json {metadata, payload_base64}
- Optional: idempotency_key
- Response: 202 {record_id, job_id, status_url}

GET /v1/ingest/{job_id}/status
- Auth required
- Returns job status, errors (no PHI in error message).

POST /v1/ingest/{record_id}/reprocess (admin)
- For manual retry.

GET /v1/records/{record_id}/metadata
- Returns metadata only. Retrieval of payload requires additional authorization and server-side decryption flow with stronger audit.

GET /v1/records/{record_id}/download
- Returns decrypted payload but only to authorized roles. Log access in access_events.

9) Implementation notes & pitfalls
- Keep plaintext PHI out of logs and audit details. Only log structured non-PHI metadata and request IDs.
- Avoid storing raw patient identifiers in separate columns unless needed — consider hashed identifiers for linkability (HMAC with secret key).
- Beware long-running DB transactions when processing large payloads — handle payload read + decrypt outside of long transactions where possible.
- Implement strict DB connection pool sizing and monitoring to avoid connection exhaustion.

10) 6-week delivery plan (team of 2)
Assume each engineer is full-time. Weeks are deliver sprint-style; iterate and demo weekly.

Week 0 (prep, 2–3 days): Kickoff + clarify gaps
- Confirm: existing web framework, ORM, secrets storage, backup tooling, monitoring, auth provider.
- Define acceptance criteria and sample producers.
Deliverable: Detailed implementation tasks, API contract.

Week 1: Core API + schema + migrations
- Design DB schema, create Alembic migrations.
- Implement /v1/ingest endpoint (basic validation, store encrypted payload).
- Implement idempotency (checksum or client key).
- Unit tests for crypto and DB layer.
Deliverable: Ingest API that accepts payloads and stores records (status=ingested).

Week 2: Worker + job table + advisory locks
- Implement worker loop with advisory locks.
- Implement ingestion_jobs lifecycle, status transitions, retry logic.
- Integrate basic parsing (JSON/FHIR minimal, file types accepted).
- CI integration and staging environment.
Deliverable: Worker that processes ingested records and updates status.

Week 3: Audit logging + access control
- Add immutable audit_logs and access_events; record relevant events in transactions.
- Implement /status and /metadata endpoints.
- Implement role checks on download endpoint and log access events.
Deliverable: Audit trail implemented; authorized retrieval of metadata.

Week 4: Encryption key management + backups + testing
- Integrate secrets for encryption keys; implement key rotation stub.
- Ensure backups are encrypted and scheduled; perform first test restore in dev.
- Write integration tests for full flow.
Deliverable: End-to-end working in staging with tested backups.

Week 5: Hardening & observability
- Implement metrics, add dashboard, add alerts (queue backlog, failure rate).
- Logging sanitization checks.
- Load testing at expected + buffer and tune worker concurrency, DB settings.
Deliverable: Monitoring + load-tested pipeline in staging.

Week 6: Compliance docs, runbooks, production rollout
- Finalize runbooks, incident response, and deploy to production via your existing pipeline (canary/blue-green recommended).
- Perform smoke tests, validate audit logs and backups.
- Handoff to ops & security; demo to stakeholders.
Deliverable: Production service with runbooks and compliance artifacts.

Estimate of effort (rough)
- Implementation tasks: ~5–6 engineer-weeks each (two engineers share tasks).
- Testing, hardening, documentation & compliance: ~1–2 engineer-weeks.
Given two engineers in parallel, 6 weeks is feasible if scope is limited to ingest + basic processing + audit.

11) Risks & mitigations
- Risk: DB growth from storing large files. Mitigation: enforce upload size limits, plan migration to object store in next phase.
- Risk: No KMS/secrets store. Mitigation: use environment secret manager short-term; treat as compliance risk and plan KMS onboarding.
- Risk: Production performance issues. Mitigation: do load testing early, tune worker concurrency and DB configs, add partitioning later.
- Risk: Missing BAAs for third-party providers. Mitigation: audit vendor contracts before using managed services.

12) Next-phase recommendations (post-MVP)
- Move binary blobs to an object store (S3/GCS) with server-side encryption and store only references in Postgres.
- Add a real queue (RabbitMQ/SQS) for higher throughput and better retry semantics.
- Implement full FHIR validation library and mapping to your internal model.
- Add a KMS for envelope encryption and rotation.
- Automate key rotation and key versioning for decrypting older payloads.
- PCA/pen test and independent HIPAA readiness review.

Final checklist for you to confirm now (I can update plan immediately if any answers differ):
- What Python web framework + ORM do you use?
- Do you have a secrets manager/KMS today? (If yes, name it.)
- How are you deployed (VMs, containers, k8s, PaaS)?
- Do you have existing auth/identity provider for clients? (OAuth/JWT, mTLS, etc.)
- Expected peak ingestion rate (records/min and average payload size).
- Any requirement to support specific formats first (FHIR R4 / HL7 / PDFs)?

If you confirm the above, I’ll produce:
- Concrete SQL migration scripts (DDL) for your Postgres.
- A small, copy-pasteable worker loop using advisory locks and SQLAlchemy (or your ORM).
- Example API endpoint handlers (Flask/FastAPI/Django style) for ingestion and download, implementing AES-GCM encryption/decryption and audit logging.