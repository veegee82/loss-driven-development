<!-- captured via scripts/capture-red-green.py
     model: openai/gpt-5-mini
     temperature: 0.7
     scenario: typical-standard
     prompt: 'design a webhook replay service that stores every inbound webhook and lets partners replay arbitrary subsets; ~500/min, 6-8 week timeline, team of 2' -->

Below is a practical, implementation-focused design you can deliver with a 2‑person team in 6–8 weeks. It covers architecture, data model, APIs, replay mechanics, resiliency, security, testing, and a week-by-week plan. I assume a cloud provider (AWS) and common tools to minimize ops overhead.

High-level goals
- Capture and persist every inbound webhook (500/min ~ 8.3/sec sustained).
- Allow partners/ops to query stored webhooks and request replays of arbitrary subsets (by filters, explicit ID lists, or time ranges).
- Replays preserve original payloads/headers, support retries/backoff, and record outcomes.
- Secure, auditable, and observable.

Key design choices (reasoning)
- Use S3 for raw payload storage (cheap, durable).
- Use a relational DB (Postgres) for metadata, indexes, and flexible querying for partners/ops.
- Use a queue (SQS) and background workers for async processing and replays.
- Keep ingestion service simple and stateless behind a load balancer for scalability.
- Use managed infra (RDS, S3, SQS, ECS/Fargate) to reduce operational burden for a small team.

Architecture (textual)
- Ingress HTTP service (FastAPI/Express/Go net/http) behind ALB/API Gateway.
  - Validates, optionally authenticates/signs, writes payload to S3, inserts metadata row to Postgres, enqueues message to SQS for async processing (dedup, metrics).
- Postgres stores metadata rows referencing S3 object keys + indexes for queries (partner_id, event_type, timestamp, delivery_status).
- Replay API/UI that allows selecting subsets by filters, uploading list of IDs, or scheduling replays. Submits a Replay Job.
- Replay Job stored in DB with status and queue message(s). Replay worker(s) consume job and dispatch HTTP requests to partner endpoints, honoring concurrency/rate limits, retries and backoff, and logging delivery results to DB.
- Worker fetches original payload from S3 for each event.
- Monitoring: CloudWatch/Prometheus, logs, traces.
- AuthZ: token-based (OAuth2/JWT) and partner-scoped permissions.
- Audit logs and metrics for billing/SLAs.

Data model (simplified)
- webhooks (metadata)
  - id (UUID)
  - received_at (timestamp)
  - partner_id
  - event_type
  - s3_key (payload location)
  - headers (jsonb)
  - original_signature (optional)
  - checksum (sha256)
  - processing_status (enum: ingested/validated/failed/...)
  - size_bytes
  - delivery_status (last delivery result if applicable)
  - deleted_at (for soft deletes / retention)
  - indexes on partner_id, received_at, event_type

- replay_jobs
  - id
  - owner (partner or ops)
  - created_at, started_at, finished_at
  - filters (json) OR explicit_ids (array of UUID)
  - total_events
  - submitted_events_processed
  - concurrency_limit, retry_policy
  - status (pending/running/complete/failed/cancelled)
  - results_summary (success/fail counts)

- replay_attempts
  - id
  - replay_job_id
  - webhook_id
  - attempt_number
  - started_at, finished_at
  - status (success/fail)
  - http_status
  - response_body/snippet
  - latency_ms
  - error (if any)

APIs (minimal set)
- POST /webhook (ingest endpoint; public endpoint that partners call)
  - body: raw payload; headers forwarded; partner identification via API key/host header
  - response: 202 accepted, id
- GET /webhooks?partner_id=&event_type=&start=&end=&limit=&cursor=
  - returns metadata and pagination
- GET /webhooks/{id} -> metadata + pointer to download payload (pre-signed S3 URL)
- POST /replay_jobs
  - body: {filters: {...} OR ids: [...], concurrency: n, retry_policy: {...}, scheduled_at: optional}
  - returns job id
- GET /replay_jobs/{id} -> status and metrics
- POST /replay_jobs/{id}/cancel

Replay flow (details)
1. User requests replay job (filters or explicit IDs).
2. System resolves filter to list of webhook IDs (snapshotted at job creation).
3. Replay job enqueues work items (batched) to SQS (for large jobs chunked e.g. N=50).
4. Replay workers consume SQS, fetch payload from S3, forward HTTP request to partner endpoint including:
   - Original headers (optionally sanitized), new header X-Original-Id, X-Replay-Job-Id
   - Optional signature header: server signs payload with replay key so partner can trust replay
5. Worker records attempt in replay_attempts; on failure, obey retry policy (exponential backoff, up to max attempts).
6. On completion, job status and summary updated.

Rate limiting / concurrency
- Per-replay job concurrency limit (e.g., default 4) and global per-partner throttling to avoid overwhelming partner endpoints.
- Use leaky-bucket/token-bucket in worker or a concurrency semaphore in job scheduler.
- Enforce retries with jitter & exponential backoff.

Deduplication & idempotency
- Each ingested webhook gets canonical id and checksum; if duplicate delivered, detect via checksum + headers and either mark as duplicate or ingest separate copy depending on business rule.
- Replayed requests include headers allowing recipients to deduplicate (X-Original-Id).

Storage, retention, and cost
- Payloads in S3 with lifecycle rules: hot storage for N days (e.g., 90), then archive (Glacier) or delete based on partner SLA.
- Postgres stores metadata for query; purge older rows or offload to analytics store for very long retention.
- Consider compression and multipart uploads for large payloads.

Security & compliance
- TLS everywhere.
- At ingress: API keys for partners, IP allowlist optional.
- Sign inbound webhooks if needed; verify partner signatures on ingress (store original signature).
- Encrypt S3 & DB at rest, use KMS-managed keys.
- RBAC for UI/API; audit logs for replay requests & download access.
- Data deletion workflows for GDPR requests (delete S3 object, null metadata or mark deleted).

Observability & monitoring
- Metrics: ingestion rate, failures, replay success rate, latency, queue depth.
- Logs: structured logs with webhook_id, job_id, worker id.
- Tracing: add distributed traces for replay path.
- Alerts: queue depth > threshold, replay failure rate spikes, ingestion error increase.

Testing & reliability
- Unit tests for API and worker logic.
- End-to-end tests: ingest -> replay -> assert partner received with original payload.
- Load tests: 500/min + burst (e.g., 2x–5x) to validate autoscaling.
- Chaos testing for S3/RDS latency and worker failures.
- Contract tests for partner replay signature/headers.

Operational concerns
- Partner endpoint failure handling: exponential backoff, circuit breaker per endpoint (open after N consecutive failures for T minutes).
- Partial replays: support resume/cancel; track per-webhook attempt history.
- Large replays: chunk and paginate the job resolution and enqueueing.

Tech stack suggestions (fast to deliver & low maintenance)
- Ingest & API: Python (FastAPI) or Node (Express/Nest). Use pydantic/types for schema.
- Worker: Python with asyncio or Go for efficient concurrency.
- DB: AWS RDS Postgres (or Aurora Serverless if preferred).
- Queue: AWS SQS Standard (simple, reliable).
- Storage: AWS S3 + pre-signed URLs.
- Deployment: ECS Fargate or Lambda for small services; use Terraform for infra as code.
- CI/CD: GitHub Actions -> deploy images.
- UI: small React app for partners/ops (or reuse internal admin UI).

Security headers & replay signature
- Add X-Replayed-By: service-name
- Provide HMAC-Signature header on replayed requests using a per-partner replay signing key so partners can authenticate replays.

6–8 week schedule for 2 engineers (MVP first; assume engineers are full-stack capable)
- Week 0: Planning & infra setup (1–2 days)
  - Finalize requirements, SLAs, retention, replay rules, auth model.
  - Create Terraform skeleton, provisioning accounts, S3, RDS, SQS, ECS cluster.

- Week 1: Ingestion MVP
  - Implement ingest endpoint: accepts webhook, writes payload to S3, writes metadata to Postgres, returns id.
  - Basic auth by API-key.
  - Unit tests + basic integration test.
  - Deploy to staging.

- Week 2: Query APIs + metadata search
  - Implement GET /webhooks, GET /webhooks/{id}, pre-signed download URLs.
  - Implement simple UI to list & view webhook.
  - Add indexing and pagination.

- Week 3: Replay job API + basic worker
  - Implement POST /replay_jobs storing job and resolving filters to IDs (snapshot).
  - Implement a simple worker that processes a small job and sends HTTP to partner endpoint (single attempt, no retries).
  - Implement replay attempt logging.
  - E2E test: ingest -> create job -> worker sends to test endpoint.

- Week 4: Robust replay mechanics
  - Add retries/backoff, per-job concurrency, chunking, and SQS enqueueing.
  - Add headers/signing on replay.
  - Implement job status and cancellation.
  - Add simple rate-limiting/throttling per partner.

- Week 5: Security, monitoring, and operational features
  - Add encryption, KMS integration, RBAC for UI.
  - Add metrics (Prometheus/CloudWatch), logs, basic alerts.
  - Add circuit-breaker logic for failing endpoints.

- Week 6: Hardening, load testing, and polish
  - Load tests to 500/min sustained plus bursts; tune autoscaling and DB connections.
  - Add lifecycle policies for S3, retention config and delete endpoints.
  - Add audit logs and usage metrics for billing.

- Week 7 (optional, if 8-week plan): Partner UX + Docs
  - Improve UI, add replay scheduling, throttling controls, partner docs for signature verification.
  - Implement long-term retention/archive flows.

- Week 8: Production rollout & follow-ups
  - Run canary with a small partner, verify SLAs, monitor metrics, address issues.
  - Post-launch bug fixes and operational runbook.

Rough effort split (2 engineers)
- Engineer A: API/ingest, DB modeling, security.
- Engineer B: Worker/replay engine, queueing, retries, rate-limiting.
- Both: deployment/infra, E2E tests, load testing, UI/UX and documentation.

Non-functional targets and capacity
- Ingestion: 500/min (8.3/sec). This is low: a single Fargate task with autoscaling should handle it; design for bursts up to 2–3k/min by autoscaling.
- Storage estimates: assume avg payload 10 KB -> 500/min * 60 * 24 = 720,000 KB/day ≈ 0.7 GB/day; S3 is cheap.
- DB: metadata inserts at same rate; connection pooling required; batch inserts not necessary but DB tuning (connection limits, indices) is important.

Open tradeoffs & decisions you should make early
- Query complexity: use Postgres for flexible queries; for very advanced search (full-text, high cardinality filters), consider OpenSearch.
- Duplicate semantics: store duplicates as separate entries vs dedupe—depends on business rules.
- Replay ordering: do you need guaranteed ordering per partner? If so, the complexity increases (single-worker per partner or ordered queues).
- Long-term storage vs cost: agree retention SLAs to avoid surprises.

Deliverables for MVP
- Ingest endpoint (production ready), metadata store, S3 payload storage
- Query API and simple UI to view webhooks and download payload
- Replay job API + worker supporting concurrency, retries, and logs
- Monitoring dashboards and runbook
- Basic security (API keys, TLS, encryption, per-partner replay signature)

If you want, I can:
- Produce a concrete DB schema (CREATE TABLEs) for Postgres.
- Draft OpenAPI for the APIs.
- Sketch Terraform snippets for S3/RDS/SQS/ECS.
- Provide example worker pseudo-code for replaying (with concurrency and retries).

Which of those follow-ups would be most useful next?