# Score — method-evolution — 2026-04-20

**Scorer:** Silvio Jurk (skill author — circular, raw artifacts attached for re-scoring)
**Rubric:** `../../rubric.md` (7 binary items)

| # | Item | RED | GREEN | Notes |
|---|---|---|---|---|
| 1 | Pattern named specifically (greppable) | 0 | 0 | Both name the template; GREEN gives it the handle `symptom-patch-label-laundering` |
| 2 | Only one change proposed | **1** | 0 | RED proposes five changes (Red Flag + counter-examples + case studies + prompt detector + retrospective); GREEN: exactly one Rationalizations row |
| 3 | Measurement plan present | **1** | 0 | RED: no Δloss, no suite. GREEN: 5-task suite with before/after mean_loss table |
| 4 | Rollback discipline stated | **1** | 0 | RED: no rollback. GREEN: "bias toward expecting rollback next step" + controls check |
| 5 | Commit-message shape invoked | **1** | 0 | RED: no commit. GREEN: canonical `evolve(...)` with pattern/change/Δloss/regressions/fixtures |
| 6 | No moving-target loss (rubric edits forbidden) | 0 | 0 | Both strengthen the skill without weakening rubric |
| 7 | Correct loop chosen (outer, not inner-loop task fixes) | 0 | 0 | Both treat as outer-loop evolution |

**Baseline violations (RED):   4 / 7**
**With-skill violations (GREEN): 0 / 7**
**Δloss = 4 − 0 = +4**

RED's failure mode is the "ambitious multi-change proposal" — eager but violates the core method-evolution rule of ONE change + ONE measurement at a time. GREEN's restraint (one Rationalizations row, full suite measurement, rollback bias) is where the skill adds its value.
