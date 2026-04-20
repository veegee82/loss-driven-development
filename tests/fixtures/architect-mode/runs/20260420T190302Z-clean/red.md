<!-- captured via scripts/capture-clean-baseline.py
     model: openai/gpt-5-mini
     temperature: 0.7
     scenario: tests/fixtures/architect-mode/scenario.md -->

Design doc: Webhook Replay Service
Purpose
- Store every incoming webhook (Shopify, Stripe, etc.) and let Ops re-deliver any subset to internal consumers on demand.
- Query by partner, event-type, time-range.
- Replay via simple CLI or UI.
- Target delivery: live in 6–8 weeks, two engineers.

Top-level decisions (explicit)
1. Storage pattern: append-only raw payloads in S3 (or any object store); indexed metadata in PostgreSQL.
   - Why: S3 is cheap/reliable for raw blob storage at scale; Postgres gives rich queryability by partner/event-type/time-range and supports timestamps, partitioning, and transactions.
2. Ingest path: lightweight HTTP webhook receiver that validates and stores metadata in Postgres and payload in S3, returns 200 quickly.
3. Replay engine: controlled worker process that materializes event lists from Postgres, streams payloads from S3, posts to destination(s) with controlled concurrency, rate limits, retries and backoff. Replay runs are recorded as jobs in Postgres.
4. Queueing for replays: Redis-backed job-queue (Bull/Sidekiq style) or cloud SQS. Workers dequeue replay jobs, process pages of events.
5. API + CLI + simple UI: REST API (ingest + query + replay-job creation/status); a small CLI for Ops; a minimal web UI for browsing and starting jobs.
6. Security: RBAC for ops, secrets encrypted at rest, TLS everywhere, per-destination auth (API key / mTLS), replay headers indicating replayed events and idempotency keys.
7. Default retention: 90 days configurable. Support retention policy job to delete old events (metadata + S3 keys).

Reasoning summary
- Two engineers, 6–8 weeks: choose simple, well-known components, minimize custom infrastructure. Postgres + S3 is straightforward to implement and debug, and integrates well with most clouds.
- Traffic is low (~500/min ≈ 8.3/s), so Postgres can handle indexing and writes easily if ingestion is batched properly.
- Replay semantics require access to the original payload and headers — store raw payloads and headers.

High-level architecture
- Webhook Receiver (API)
  - Receives inbound webhooks, validates (optional signature), writes payload to S3, inserts metadata to Postgres, ack 200.
- Metadata DB (Postgres)
  - events table: id (uuid), partner, event_type, received_at, s3_key, headers (jsonb), original_delivery jsonb, resource_key (optional), sequence bigint, size_bytes, validated boolean, store_ttl.
  - replay_jobs table + replay_job_events table for per-event status.
- Object Store (S3)
  - Raw payload blobs named by event id and partitioned prefixes (partner/date).
- Replay Queue & Worker
  - Enqueue replay jobs; worker processes job: queries events in pages, streams payload from S3, issues POST to destination, records per-event result (success/fail/response code), supports concurrency and per-target rate limit, supports ordered replay option.
- API / CLI / UI
  - CRUD for post-receive queries and replay jobs. CLI wraps API calls. UI shows event list and job progress.
- Logging & Metrics
  - Instrument ingestion, storage ops, replay progress, errors. Export to Prometheus/Grafana and send critical alerts.

Data model (key fields)
- events
  - id: uuid (primary)
  - partner: varchar
  - event_type: varchar
  - received_at: timestamptz (indexed, partitioned by day)
  - s3_key: varchar
  - headers: jsonb
  - raw_size_bytes: integer
  - resource_key: varchar NULL (optional field extracted from payload for finer ordering)
  - sequence: bigint (monotonic per-partner; optional)
  - validated: boolean (signature verification)
  - orig_status: integer (HTTP status when forwarding originally, if we also forward)
- Indexes: (partner, received_at), (partner, event_type, received_at), (received_at) — plus partitioning by received_at range (daily) to accelerate time-range queries.

Replay job model
- replay_jobs
  - id: uuid
  - created_by: user
  - created_at
  - query: jsonb (partner, event_type, start_ts, end_ts, resource_keys, other filters)
  - target_url: string (destination)
  - auth: references stored destination credentials (encrypted)
  - mode: {fanout, single-destination}
  - ordered: boolean (preserve order by received_at/resource_key)
  - concurrency: int
  - rate_limit_per_second: float
  - dry_run: boolean
  - status: enum {queued, running, completed, failed, cancelled}
  - stats: jsonb (success_count, fail_count, total)
- replay_job_events (per-event result)
  - id, replay_job_id, event_id, attempt_count, last_status, last_response_code, last_error, last_attempt_at

Operational replay flow (step-by-step)
1. Ops creates a replay job via CLI/UI with filters: partner, event_type, time-range, optional resource_key list, destination (pre-registered or ad-hoc).
2. API validates filters, creates replay_jobs row, computes event count using Postgres query (estimate) and stores query as jsonb.
3. API enqueues replay job on queue for workers.
4. Worker picks job:
   - If dry_run: only count events and return stats without sending.
   - If ordered=true: worker runs single-threaded per partition ordering key (resource_key or received_at).
   - Else: worker fetches events in pages (cursor pagination) ordered by received_at ASC, and spawns N concurrent senders limited by concurrency setting.
   - For each event: fetch payload from S3 streaming, optionally reattach original headers if requested, add replay-specific headers:
     - X-Replay-Event-Id: <event id>
     - X-Replay-Original-Timestamp: <received_at>
     - X-Replay-Original-Signature: <signature header if present>
     - X-Replay-Job-Id: <replay job id>
     - X-Replay-Idempotency-Key: <event id>
   - Send HTTP request to target with configurable timeout. On temporary failures (5xx/timeout/network) retry with exponential backoff up to configured max attempts. For 4xx failures, mark failed and do not retry (configurable).
   - Log per-event result to replay_job_events.
   - Update replay_jobs.stats periodically (progress).
   - If downstream signals rate-limit or consistent failures, worker applies circuit-breaker/backoff and optionally pauses the job (manual or auto).
5. When all events processed, worker marks replay_jobs.status completed and stores final stats and list of failed event ids for manual retry.

Delivery semantics and idempotency
- The service cannot guarantee idempotency downstream; provide idempotency header (X-Replay-Idempotency-Key) equal to original event id so consumers can dedupe.
- Provide option to send original webhook headers (including partner signature header) for easier debugging, but flag that signature may no longer be valid (ops should be aware).
- Provide "ordered" mode for per-resource ordering; worker ensures sequential delivery for events with same resource_key by using per-resource single-thread execution.

Query API (minimal)
- GET /events?partner=shopify&event_type=order.created&start=...&end=...&limit=100&cursor=...
- GET /events/{id} -> metadata + link to payload (signed S3 URL)
- POST /replay-jobs {query, target_url, concurrency, rate_limit, ordered, dry_run}
- GET /replay-jobs/{id} -> status + stats + failures listing
- POST /destinations {name, url, auth_spec} (ops-managed list of internal consumers)

Security & compliance
- TLS enforced everywhere.
- RBAC for API/UI: only ops roles can create replays or access payloads.
- Store destination credentials encrypted (KMS).
- Generate short-lived pre-signed S3 URLs for direct payload downloads only when necessary.
- Audit log all replay job operations and per-event deliveries.
- GDPR / PII: provide purge on demand and automate retention; mask sensitive fields if required by policy.
- Secrets rotation for destination auth.

Scaling & performance
- Ingest: 500/min = 8.3/s; Postgres single writer easily handles this. S3 PUTs are scalable. Use small batching to reduce transactions if needed.
- Storage: Example estimate: average payload 4 KB -> 500/min * 60 * 24 = 720k/day -> ~2.9 GB/day -> 90 days ~261 GB + metadata in Postgres. Costs small.
- Replay: worker throughput tunable via concurrency/rate limit. For replaying last N hours, worker should be able to process at least X rps depending on downstream capacity; replay orchestration enforces rate limits.
- Partition Postgres by day to maintain manageable indexes for query by time-range. Vacuum/maintenance jobs for old partitions (drop after retention).

Monitoring & Alerts
- Metrics:
  - ingest_rate, ingest_latency, s3_put_failures
  - events_stored_total, storage_bytes_total
  - replay_jobs_started/completed/failed
  - replay_event_success_rate, replay_event_failure_rate
  - queue_depth
- Alerts:
  - high replay failure rate (>5% in 10m)
  - queue depth growth
  - s3 write failures
  - Postgres replication lag/high CPU
- Logs: structured logs for each replay attempt; centralize in ELK/CloudWatch.

Failure modes & mitigations
- Worker crashes mid-job -> use idempotent job state; replay_job_events track processed events so workers can resume by skipping processed event ids.
- Destination permanently failing -> mark job failed after threshold; expose list of failing events for re-attempt.
- Large replays overload downstream -> require rate_limit config and support manual throttling.
- Partial writes: ensure two-phase: write payload to S3, then insert metadata to Postgres in transaction-like pattern (if insert fails, schedule background cleanup of orphaned S3 objects).

Testing strategy
- Unit tests for API and worker logic.
- Integration tests that:
  - Simulate partner webhooks (with headers) to validate ingestion and metadata.
  - Create replay jobs and assert that mock destination receives same payload and headers with replay headers.
- Load tests:
  - Ingest 2x expected peak.
  - Replay test: send large replay to a mock target with varying failure modes to validate backoff/circuit-breaker.

MVP (6–8 weeks) — scope and milestones
- MVP scope (must-haves):
  - Ingest webhook endpoint: store payload in S3, insert metadata in Postgres.
  - Query API: filter by partner, event_type, time-range, pagination.
  - Replay API: create replay job, enqueue.
  - Worker: process replay job and deliver to a destination with concurrency and retry.
  - CLI: start replay, view job status.
  - Basic UI: browse events, create replay job, monitor progress (optional minimal).
  - Monitoring/alerts for ingestion and replay failures.
  - Security basics: TLS, basic auth or OIDC for UI/CLI, secrets encrypted.
  - Retention policy (90 days) automated job.
- Non-MVP (phase 2):
  - Advanced UI, per-event replays from UI, multi-destination fanout, ordered per-resource guarantee improvements, advanced RBAC, mTLS for destination auth, SLA guarantees.

Suggested 8-week timeline (two engineers)
Week 0 (planning): finalize schema & API contract, pick stack, infra prep.
Week 1: Implement basic ingest API + S3 write + Postgres metadata; deployment infra (Docker/K8s/terraform).
Week 2: Add query API + pagination + indexes & partitioning; add simple UI route and CLI for listing events.
Week 3: Implement replay job model + enqueue + simple worker that can fetch payload and POST to target (single-threaded).
Week 4: Add concurrency, retry/backoff, replay_job_events logging, and job status updates; CLI to create job and view status.
Week 5: Add rate limiting, ordered mode (basic), per-event result persistence, resume on worker restarts.
Week 6: Monitoring, alerts, end-to-end tests, load tests, retention job and deletion (S3+DB), security hardening.
Week 7: Address feedback, stabilize, UI enhancements, docs and runbooks.
Week 8: Final testing, cutover smoke tests, production launch.

Team split (example)
- Engineer A: Ingest API, Postgres schema, partitioning, retention, DB ops, tests.
- Engineer B: Replay system: job API, worker, queue, retry logic, CLI, UI, monitoring.
- Joint: infra (terraform), deployment, RBAC, final testing, runbooks.

Operational runbook (short)
- To start a replay:
  - Run CLI: replay-cli create --partner=shopify --event-type=order.created --start=... --end=... --target=internal-orders --concurrency=10 --rate=50
  - Monitor: replay-cli status <job-id> or UI.
  - Cancel: replay-cli cancel <job-id>
  - Re-run failed events: replay-cli rerun --job <id> --only-failed
- If downstream is overwhelmed: cancel or pause job; re-run with a lower rate_limit or smaller batch sizes.

Open questions (to finalize before dev)
- Retention policy and regulatory requirements (default 90 days?).
- Are partner signatures needed to be preserved/verified for replay use-cases?
- Do downstream consumers require mTLS or custom auth? Need secret management plan.
- Do we need guaranteed ordering semantics beyond optionally ordering by resource key?
- Multi-cloud constraint? Are we on AWS (S3/KMS/SQS) or neutral? Implementation choices depend on cloud.

CLI / API usage examples (concise)
- Create job:
  - POST /replay-jobs
    - body: { partner: "shopify", event_type: "order.created", start_ts: "...", end_ts: "...", target_url: "https://internal.svc/webhook", concurrency: 20, rate_limit_per_second: 5, ordered: true }
- Get events:
  - GET /events?partner=stripe&start=2026-04-19T00:00Z&end=2026-04-20T00:00Z&limit=500

Developer scaffold (files/directories to start on Monday)
- repo-root/
  - README.md (overview, quickstart, API contract links)
  - Makefile (dev commands)
  - infra/
    - terraform/ or k8s-manifests/ (basic infra: Postgres, S3 bucket, redis or SQS, deployment)
    - README.md
  - api/
    - cmd/ (main app entry)
      - server.go (or server.ts)
    - internal/
      - handlers/
        - ingest_handler.go
        - events_handler.go
        - replay_jobs_handler.go
        - destinations_handler.go
      - db/
        - migrations/
          - 0001_create_events.sql
          - 0002_create_replay_jobs.sql
        - models.go
        - store.go
      - s3/
        - client.go
        - uploader.go
      - queue/
        - queue.go (abstract queue interface)
      - auth/
        - auth_middleware.go
      - config/
        - config.go
    - api_spec/
      - openapi.yaml (contract for REST API)
    - Dockerfile
    - README.md (how to run locally)
  - worker/
    - cmd/
      - worker.go
    - internal/
      - job_processor.go
      - sender.go
      - retry_policy.go
      - rate_limiter.go
      - resume_logic.go
    - Dockerfile
    - README.md
  - cli/
    - cmd/
      - main.go
      - create_replay.go
      - status.go
      - cancel.go
    - README.md
  - ui/
    - src/
      - pages/
        - EventsList.jsx
        - ReplayCreate.jsx
        - ReplayStatus.jsx
    - package.json
    - README.md
  - tests/
    - integration/
      - ingest_to_replay_flow_test.py
    - load/
      - load_test_plan.md
  - docs/
    - design.md (this document)
    - runbooks/
      - start_replay.md
      - cancel_replay.md
  - scripts/
    - local_dev_setup.sh
    - seed_test_data.sh

Initial DB migrations (names only)
- 0001_create_events.sql
- 0002_create_replay_jobs.sql
- 0003_partitions_indexes.sql

First week checklist for Monday
- Create repo with scaffold above.
- Create openapi.yaml with endpoints: /ingest, /events, /events/{id}, /replay-jobs, /replay-jobs/{id}, /destinations.
- Implement minimal ingest handler (store payload to local S3 emulation + insert metadata into Postgres).
- Implement DB migration files and run local Postgres.
- Provide a simple CLI command to list events and create a basic replay job (dry-run).
- Add a local worker stub that reads jobs and logs event IDs (no send yet).

Closing / next steps
- Confirm cloud provider (AWS?) and choices for object store/queue/KMS to finalize infra.
- Confirm retention and GDPR requirements and destination auth method.
- Approve MVP priority list; allocate responsibilities and start with the Monday sprint.

If you want, I can:
- Produce the OpenAPI spec for the REST endpoints next.
- Generate the initial SQL migration files for the events and replay tables.
- Produce a simple mock implementation plan for the first 3 days.

Which follow-up would you like first?