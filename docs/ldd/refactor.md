# Refactor / structural change / architectural edit

Load this when the user says: "refactor", "redesign", "rewrite", "extract", "split into modules", "merge modules", "clean up this", "this module is tangled".

This is the **inner loop** (`∂L/∂code`) under pressure — the one axis where step-size miscalibration shows up the fastest. See [`../theory.md`](../theory.md) for the optimization frame.

## Skill

Primary: [`loss-backprop-lens`](../../skills/loss-backprop-lens/SKILL.md) — calibrate step size honestly. Secondary: [`root-cause-by-layer`](../../skills/root-cause-by-layer/SKILL.md) — scope the change. Tertiary: [`method-evolution`](../../skills/method-evolution/SKILL.md) — if the refactor is itself a recurring pattern across the codebase, the problem is on the **method axis** (outer loop), not the code axis, and you should stop and invoke `method-evolution` properly with a suite.

## The core question — what is the loss pattern?

Refactors are the textbook case for mis-calibrated learning rate. Three scenarios:

| Scenario | Right step size | Wrong step size |
|---|---|---|
| One module's internal structure is tangled; callers are fine | **Local refactor** within the module, no signature changes | Big architectural rewrite ("clean sweep") — over-edit |
| Same pattern (e.g. parameter passing, error handling) is inconsistent across 5+ modules | **Structural** — introduce the missing abstraction, then migrate modules | Fixing each module one-by-one (local-minimum trap) |
| A layer boundary is leaking (domain imports from persistence, etc.) | **Boundary redraw** — re-establish the layer contract | Adding adapters to paper over the leak (regularizer violation) |

## Protocol

1. **State the current loss.** What specifically is broken about the current shape? If you cannot name it in one sentence, there is no gradient and refactors without a gradient are random walks.
2. **Check for recurring pattern** — if the same shape-problem appears 3+ times across the codebase, the refactor is outer-loop work (`method-evolution`), not inner.
3. **Pick the step size** via the table above.
4. **Run through `dialectical-reasoning`** — what is the antithesis of this refactor? (Usually: "we break N call sites that work fine right now.") Narrow scope accordingly.
5. **Refactor in the smallest coherent unit per iteration.** Each iteration ends with tests green and docs synced. Never leave a half-migrated state committed.
6. **Close via** `docs-as-definition-of-done` — refactors almost always invalidate doc-level mental models; re-sync.

## Red flags

- "While I'm in here, let me also..." — scope creep, separate refactor
- "This will pay off later" without a named, concrete "later" — speculation, not loss
- Renaming for aesthetics (not behavior, not coupling) — usually not worth the call-site churn
- Refactor with no failing test / no loss signal beyond taste — this is re-plan, not refactor; dispatch `iterative-refinement` on the *plan*, not the code

## What refactors should NEVER do

- Change behavior without a test (refactor is behavior-preserving; behavior changes are features)
- Skip `docs-as-definition-of-done` — refactor-drift is the hardest drift to catch later
- Be the first commit of a long chain without a rollback plan

## Full skill references

- [`../../skills/loss-backprop-lens/SKILL.md`](../../skills/loss-backprop-lens/SKILL.md) — step-size calibration
- [`../../skills/root-cause-by-layer/SKILL.md`](../../skills/root-cause-by-layer/SKILL.md) — name the layer
- [`../../skills/method-evolution/SKILL.md`](../../skills/method-evolution/SKILL.md) — if the pattern is recurring
