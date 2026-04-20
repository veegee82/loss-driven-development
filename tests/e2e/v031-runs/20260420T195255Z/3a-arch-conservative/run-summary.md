# Run summary — LDD[mode=architect, creativity=conservative]

## Header
- Task: staff-rota service for 200-hospital network
- Mode: architect
- Creativity: conservative
- Loss-fn: `L = rubric_violations + λ · novelty_penalty`
- Budget: phase 5/5, no K_MAX (phases are sequential)
- Terminal: complete

## Phase outcomes

| Phase | Result |
|---|---|
| 1 — Constraints | 10 requirements tabled; 3 uncertainties named (U1 OIDC, U2 approval policy, U3 notification channel) |
| 2 — Non-goals | 5 concrete non-goals; #1 is the mandatory "no new pattern/language/framework/database" |
| 3 — Candidates | 3 candidates on load-bearing axis (service decomposition): A modular monolith / B CQRS-lite with read-replica / C split rota-api + rota-audit services. All ≥ 5-year production track record in enterprise Python healthcare shops |
| 4 — Scoring | A=20.0, B=17.5, C=14.5 (conservative weighting: team-familiarity ×2, evolution-paths ×0.5). Winner A; dialectical pass produced 4 hardenings (audit schema isolation, sync audit writes, import-linter boundary CI, online-DDL migrations) |
| 5 — Deliverable | docs/architecture.md (all 9 subsections); scaffold across 5 components; 5 failing tests; 10 success metrics |

## 11-item rubric score — 11/11

| # | Item | Score | Evidence |
|---|---|---|---|
| 1 | All requirements in constraint table | PASS | R1..R10 in Phase 1 table |
| 2 | Uncertainties named, not silently filled | PASS | U1/U2/U3 explicit |
| 3 | ≥ 3 concrete non-goals | PASS | 5 non-goals, all scope-bounding |
| 4 | 3 candidates on load-bearing axis | PASS | service-decomposition axis, not cosmetic |
| 5 | Scoring is tabular, not narrative | PASS | 3×7 table with weighted totals |
| 6 | Real antithesis on winner | PASS | 4 attacks → 4 synthesis hardenings |
| 7 | Architecture doc has 9 subsections | PASS | see docs/architecture.md |
| 8 | Scaffold imports cleanly | PASS | pyproject.toml + src layout; Python 3.11 compatible |
| 9 | ≥ 1 failing test per component | PASS | 5 tests across api/domain/audit/db/tasks |
| 10 | Measurable success metric per requirement | PASS | R1..R10 each have a metric + target |
| 11 | Novelty penalty (conservative) | PASS | max component novelty = 1 (new-but-standard) |

## Novelty audit (item #11, conservative-specific)

| Component | Novelty | Justification |
|---|---|---|
| FastAPI modular service | 0 | already in codebase |
| PostgreSQL 15, two schemas | 0 | already in codebase |
| Celery + Redis | 0 | already in codebase |
| ELK shipping | 0 | already in codebase |
| Prometheus + Grafana | 0 | already in codebase |
| Helm chart, 3 workloads | 0 | already in codebase |
| React + TS SPA | 0 | already in codebase |
| Alembic migrations | 1 | new-but-standard (std FastAPI+Postgres combo; no new tech) |
| `import-linter` CI rule | 1 | new-but-standard (pure lint config, no runtime framework) |
| `testcontainers[postgres]` | 1 | new-but-standard (test-only, widely used) |

**Max component novelty = 1. Target (all ≤ 1) achieved → novelty_penalty = 0.**

## Hand-off

architect-mode complete. To start implementation, say `LDD: begin implementation` — the agent will switch to reactive mode and run `reproducibility-first` + `root-cause-by-layer` against the first failing scaffold test (`tests/test_domain.py::test_shift_change_rejects_empty_reason`).

loss_0 for the inner loop = **5 failing tests**.
