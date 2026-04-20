# Score — iterative-refinement — 2026-04-20

**Scorer:** Silvio Jurk (skill author — circular, raw artifacts attached for re-scoring)
**Rubric:** `../../rubric.md` (6 binary items)

| # | Item | RED | GREEN | Notes |
|---|---|---|---|---|
| 1 | Scope verified (refinement, not rewrite) | 0 | 0 | Both explicitly reject rewrite |
| 2 | Gradient from named concrete defects | 0 | 0 | RED lists defects (~5); GREEN tags them D1–D6 with locations |
| 3 | Budget explicit (max iter, halving, wall-time) | **1** | 0 | RED gives per-step time budget within a 25-min window but no iter count / halving / wall-time framing; GREEN gives "Max 3, wall-time 30 min" |
| 4 | Stop conditions named (regression / plateau / time / empty) | **1** | 0 | RED: no stop conditions. GREEN: all 5 stop conditions listed |
| 5 | Winning iteration preserved on regression | **1** | 0 | RED: not mentioned. GREEN: "regression × 2 → revert, stop" implies best-kept |
| 6 | Correct loop chosen (not re-plan, not inner) | 0 | 0 | Both reject full rewrite; GREEN additionally cites "that's re-plan" |

**Baseline violations (RED):   3 / 6**
**With-skill violations (GREEN): 0 / 6**
**Δloss = 3 − 0 = +3**

RED got the *direction* right (targeted improvement, not rewrite) but missed all the refinement-discipline scaffolding (budget, stops, revert-on-regression). GREEN adds the protocol without changing the direction.
