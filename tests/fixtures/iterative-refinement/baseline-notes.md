# Baseline observations — iterative-refinement

**Status: MEASURED (2026-04-20).** Raw artifacts in `runs/20260420T155048Z/` (red.md, green.md, score.md).

## Measurement summary

- RED violations: **3 / 6** — no explicit budget/iter framing, no stop conditions, no revert-on-regression plan
- GREEN violations: **0 / 6** — structured gradient D1–D6, max-iter+wall-time, all 5 stop conditions, monotonicity
- **Δloss = +3**

## Observed failure mode (RED)

The agent gets the *direction* right: rejects full rewrite, rejects ship-as-is, proposes a targeted pass at named defects. What it misses is the refinement *protocol*:

- **Budget framing.** RED sets per-step time budgets but no iteration count, no halving, no "max 3."
- **Stop conditions.** No regression / plateau / wall-time / empty-gradient stops.
- **Revert.** No plan for what to do if a revision makes the doc worse.

## Observed skill effect (GREEN)

Structured gradient (D1–D6 with locations), explicit budget (max 3 iters, wall-time 30 min), all 5 stop conditions enumerated, monotonicity rule ("each iter must close ≥1 named defect"), and explicit framing: "Not doing: full rewrite (that's re-plan)." The direction doesn't change — the discipline does.

## Caveats

- Reviewer-scored. Raw artifacts attached.
- Single run.
- The scenario lists the defects explicitly, so RED gets defect enumeration "for free." A scenario where the agent has to *find* defects itself would test the gradient-construction step more rigorously.
