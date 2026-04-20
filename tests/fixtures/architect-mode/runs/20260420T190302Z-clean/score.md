# Score — architect-mode — 2026-04-20 (CLEAN baseline via direct API)

**Scorer:** Silvio Jurk. Raw RED + GREEN attached in this directory.
**Rubric:** `../../rubric.md` (10 binary items).
**Capture:** `scripts/capture-clean-baseline.py` — `openai/gpt-5-mini`, T=0.7, no agent harness, no ambient methodology.

| # | Item | RED | GREEN | Notes |
|---|---|---|---|---|
| 1 | All stated requirements in constraint table | **1** | 0 | RED: no constraint table, requirements mixed into prose. GREEN: 7-row table, each row citing the source phrase verbatim from the user's ask |
| 2 | Uncertainties named, not silently invented | **1** | 0 | RED: invents "90 days retention" without flagging it as an assumption. GREEN: 8 uncertainties explicitly listed + asks one clarifying question (retention) |
| 3 | ≥3 concrete non-goals | **1** | 0 | RED: no non-goals section at all. GREEN: 4 adjacent non-goals before any design work ("not a full event-processing platform", "not multi-region", "not a transformation engine", "not exactly-once guarantor") |
| 4 | Exactly 3 candidates on a load-bearing axis | **1** | 0 | RED: proposes ONE design (Postgres + S3 + Redis queue) without comparison. GREEN: 3 candidates on storage/replay axis (Object-index hybrid / Kafka-first / Postgres JSONB) |
| 5 | Scoring table explicit (rows × 6 dimensions) | **1** | 0 | RED: narrative "why this wins". GREEN: explicit 3×6 table with per-row totals (27/30, 20/30, 20/30) |
| 6 | Real antithesis on winner, not strawman | **1** | 0 | RED: no dialectical pass. GREEN: thesis + explicit 4-concern antithesis (split-system inconsistency, S3 GET latency, ordering determinism, scan cost) + sharpened synthesis |
| 7 | Architecture doc has 9 Phase-5 subsections | **1** | 0 | RED: ~3 of 9 (data model, flow, security — missing verbatim problem quote, non-goals, candidates+rejection, scoring, test strategy, rollback). GREEN: all 9 present |
| 8 | Scaffold compiles (not pseudocode) | **1** | 0 | RED: no scaffold. GREEN: full file tree (FastAPI + SQLAlchemy + aioboto3 + click + pytest), valid Python imports, `raise NotImplementedError` for method bodies |
| 9 | ≥1 failing test per component | **1** | 0 | RED: no tests. GREEN: 4 components (api, storage, worker, cli) × 4 failing tests with explicit `assert False, "<expected behavior>"` messages |
| 10 | Measurable success metric per requirement | **1** | 0 | RED: only "~500/min" throughput mentioned. GREEN: 7 numeric metrics (99.9% ingest success, 200 ms p95 query, 2500/min replay throughput, <1 s CLI start, 30-day retention, 8-week launch target) |

**RED: 10 / 10**   **GREEN: 0 / 10**   **Δloss = +10**

## Interpretation

- Largest Δloss in the LDD bundle (previous max: `root-cause-by-layer` at +6). The architect-mode skill closes a complete behavioral gap — without it, `openai/gpt-5-mini` produces a coherent-looking design doc that violates every single architect-mode rubric item. With it, all 10 items pass on the first try.
- The GREEN response is **faithful to the 5-phase protocol without padding** — it runs each phase, acknowledges the clarifying question at Phase 1, declares non-goals before design, compares 3 candidates on a real axis, scores explicitly, dialectics the winner, and closes with a full deliverable (doc + scaffold + failing tests + hand-off line).
- Hand-off line emitted correctly at the end: *"architect-mode closed 0/10 rubric; next: default LDD inner loop; loss_0 = 4 failing tests"*. The skill's compliance checklist passes.

## Caveats

- Reviewer-scored by skill author. Raw RED + GREEN artifacts attached.
- Single-sample measurement at T=0.7. Distribution would require N≥5.
- `openai/gpt-5-mini` specifically — other base models may score differently.
- The failing tests in the scaffold use `assert False, "..."` rather than true behavior-driven tests; acceptable per rubric item 9 ("the failing state is explicit"), but stronger scaffolds would write parameterized pytest cases against the named API contracts. Minor.

## Comparison to other skills' Δloss

| Skill | Δloss | Rubric max |
|---|---:|---:|
| architect-mode | **+10** | 10 |
| root-cause-by-layer | +6 | 8 |
| drift-detection | +5 | 6 |
| method-evolution | +4 | 7 |
| loss-backprop-lens | +3 | 6 |
| e2e-driven-iteration | +3 | 5 |
| dialectical-reasoning | +3 | 6 |
| iterative-refinement | +3 | 6 |
| docs-as-definition-of-done | +2 | 6 |
| reproducibility-first | +2 | 6 |
| loop-driven-engineering | +2 | 8 |

Architect-mode is now the largest effect-size skill in the bundle. Consistent with its role — the behavioral gap between "agent invents whatever design feels right" and "agent runs a 5-phase discipline with explicit rubric" is structurally larger than any reactive-mode skill's gap.
