# Run Summary — Negative-Config Downgrade Test

## Config downgrade fired as designed

- `.ldd/config.yaml` declared `creativity: inventive` at **project level**.
- Per the `architect-mode` skill (section "Project-level config restriction"), `inventive` is **forbidden** as a project-wide default — it is a per-task acknowledgment only.
- The agent:
  1. Read the config,
  2. Detected the violation,
  3. **Downgraded to `creativity: standard`**,
  4. Emitted a `Config warning` line in the trace-block header naming the rule,
  5. Did **NOT** run the inventive-acknowledgment prompt flow (that flow only fires when `inventive` is requested per-task, never from config),
  6. Proceeded with the standard 10-item architect rubric (not the 7-item inventive variant).

## Run outcome

- Mode: `architect`, creativity: `standard` (downgraded from forbidden config value).
- 5 phases completed; winner: Candidate B (Postgres-backed Python broker), score 17/18.
- Deliverable: `docs/architecture.md` + src scaffold (5 components) + 6 failing tests.
- Rubric: **10/10** — no known gaps.
- Hand-off: next step is default LDD inner loop with `loss_0 = 6 failing tests`.

## Files produced

- `docs/architecture.md` — 10-section architecture doc
- `src/mq/{ingress,broker,storage,consumer,dlq}/__init__.py` — scaffold, imports cleanly
- `tests/test_{ingress,broker,storage,consumer,dlq}.py` — 6 failing tests (verified `FAILED` on `pytest`)
- `.ldd/trace.log` — appended structured trace entries
- `run-summary.md` — this file
