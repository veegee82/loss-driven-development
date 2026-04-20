# Refinement — polishing a good-enough-not-great deliverable

Load this when the user says: "polish this", "this doc is okay but not great", "improve this diff", "tighten this plan", "good draft, let's sharpen", "make it better".

## Skill

Primary: `iterative-refinement`. This is the **y-axis loop** — you edit the deliverable, not the code and not the method.

## When it's the right loop (all must hold)

- A deliverable (document, diff, plan, design, report, code module) is **complete**, not partial, not stuck
- It is **usable but imperfect** — passes the minimum bar, fails the bar you want
- Re-running the task from scratch would **lose** specific good parts
- You can **name** the defects concretely

Missing any → wrong loop. Buggy code → inner loop. Unknown problems → dialectical-reasoning first. Wrong approach → re-plan.

## The refinement gradient — derived, not imagined

Build from three concrete sources:

1. **Critique defects** — enumerate with locations (D1: intro vague, D2: section X repeats Y, ...)
2. **Gate rejections** — automated rules that fired against the current output
3. **Evaluation deltas** — target vs actual, numeric gap

Inject this gradient into iteration 1's context **only**. Subsequent iterations use fresh critique.

## Budget — refinement is asymptotic

- Max iterations: 3 (default; clamp [1, 10])
- Token/time budget halves per iteration
- Wall-time cap: 2× original production time

## Stop conditions (any)

- **Regression ×2** — output worse than previous iter. Revert immediately.
- **Plateau ×2** — |Δloss| below noise for 2 consecutive iterations.
- **Wall-time exhausted.**
- **Empty gradient** — no concrete defects left to name. That's a stop signal, not an invitation to imagine defects.
- **Max iterations hit.**

## Red flags — NOT refinement

- "Let me rewrite from scratch" — that's re-plan, different skill
- "Could be slightly better" without named defects — aesthetic polishing, unbounded
- "10 iterations for safety" — budget violation
- "Iter 2 worse but iter 3 might fix it" — monotonic or stop; no wishful middle
- "Make it better" as the gradient — not a gradient

## Close

Hard-link the winning iteration as the final version. If iter-k regressed from iter-(k-1), the winner is k-1. Log per-iteration Δloss for the outer-loop history.

## What about code quality?

Refactors (for code) live in [`refactor.md`](./refactor.md). Refinement is for **output artifacts** whose code or behavior isn't changing — docs, designs, plans, diffs under review.

## Full skill

[`../../skills/iterative-refinement/SKILL.md`](../../skills/iterative-refinement/SKILL.md)
