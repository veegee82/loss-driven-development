# Baseline observations — e2e-driven-iteration

**Status: MEASURED (2026-04-20).** Raw artifacts in `runs/20260420T155048Z/` (red.md, green.md, score.md).

## Measurement summary

- RED violations: **3 / 5** — misses per-iteration attribution, batched-edit detection, regularizer close
- GREEN violations: **0 / 5** — explicit five-step walk, `git stash` isolation proposal, regularizer gate
- **Δloss = +3**

## Observed failure mode (RED)

The agent correctly identifies that unit-tests-green ≠ E2E-green and proposes running E2E before commit. What it misses:

- **Attribution.** Two edits (index + redundant filter removal) landed between iter-1 and iter-2 without an intermediate E2E run. RED defers this concern ("Das ist aber nach dem grünen E2E") instead of treating it as a current-iteration concern.
- **Regularizers.** RED closes on "E2E grün → commit." GREEN requires contracts / docs / layer-boundaries also honored — the close has two conditions, not one.

## Observed skill effect (GREEN)

With the skill, the agent explicitly walks the 5-step iteration, names each missed step ("FEHLT" for both E2E runs), and proposes a `git stash` split to *retroactively recover* attribution on the batched edits.

## Caveats

- Reviewer-scored by skill author. Artifacts attached for re-scoring.
- Single run. No distribution.
- Scenario explicitly signals "you think you're done" — which may prime the agent toward the skill's behavior. A less loaded scenario phrasing would stress-test harder.
