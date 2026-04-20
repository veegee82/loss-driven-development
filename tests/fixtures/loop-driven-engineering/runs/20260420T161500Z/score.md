# Score — loop-driven-engineering — 2026-04-20

**Scorer:** Silvio Jurk. Raw artifacts attached.
**Rubric:** `../../rubric.md` (8 binary items).

| # | Item | RED | GREEN (v0.1) | Notes |
|---|---|---|---|---|
| 1 | Explicit iteration structure (K_MAX referenced) | **1** | 0 | RED numbers steps (1–5) but no K_MAX; GREEN cites K_MAX=5 and the 5-iter loop |
| 2 | root-cause-by-layer invoked early | 0 | 0 | Both diagnose before fixing |
| 3 | Test pyramid respected | 0 | 0 | Neither escalates to expensive tier unnecessarily |
| 4 | TDD before fix | 0 | 0 | Both write reproducer before production fix |
| 5 | loss-backprop-lens step size | 0 | 0 | Both consider local vs. structural |
| 6 | PM pressure rejected correctly | 0 | 0 | Both reject "tests later" |
| 7 | K_MAX escalation plan | **1** | 0 | RED no escalation plan; GREEN explicitly: escalation with 5 required elements |
| 8 | Close-of-loop concrete | 0 | 0 | Both specify close shape |

**RED: 2 / 8**   **GREEN: 0 / 8**   **Δloss = +2**

Partial contamination — agent produced TDD-before-fix, root-cause-before-edit, PM-pressure-rejection even without the skill, suggesting ambient influence. The clean remainder (K_MAX + escalation-shape) is the measurable residual Δ. Like `dialectical-reasoning`, the skill's *procedural discipline* is what survives the contamination — agents have the instincts, but the framework bindings (K_MAX, escalation shape) only appear with the skill loaded.
