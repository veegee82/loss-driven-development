# Score — e2e-driven-iteration — 2026-04-20

**Scorer:** Silvio Jurk (skill author — circular, raw artifacts attached for re-scoring)
**Rubric:** `../../rubric.md` (5 binary items)

| # | Item | RED | GREEN | Notes |
|---|---|---|---|---|
| 1 | E2E re-run proposed before commit | 0 | 0 | Both propose E2E run before commit |
| 2 | Loss-per-iteration acknowledgment | 0 | 0 | Both note unit green ≠ E2E coverage for timeout |
| 3 | Δloss across iterations named | **1** | 0 | RED mentions attribution concern but defers "after green"; GREEN names it explicitly and proposes `git stash` to isolate the index effect |
| 4 | Per-edit rerun (not batched) | **1** | 0 | RED doesn't call out that iter 1 → iter 2 batched two edits without intermediate E2E; GREEN flags this as "Let me batch 3 fixes and run once" red flag hit |
| 5 | Close conditions include regularizers | **1** | 0 | RED closes on E2E green alone; GREEN requires contracts/docs/layer-boundaries honored |

**Baseline violations (RED):   3 / 5**
**With-skill violations (GREEN): 0 / 5**
**Δloss = 3 − 0 = +3**

The scenario's specific shape (two iterations without E2E, unit-test-only verification) directly tests the skill's core rule. RED catches one aspect (run E2E before commit) but misses the other two (attribution across iterations, regularizer close condition).
