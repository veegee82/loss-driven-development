# Baseline observations — loss-backprop-lens

**Status: MEASURED (2026-04-20, clean re-run).** Raw artifacts in `runs/20260420T161500Z/` (red.md, score.md). GREEN response preserved from v0.1 commit `047502a`.

## Measurement summary

- RED violations: **3 / 6** — ships 3-line patch with explicit "tomorrow problem" framing
- GREEN violations: **0 / 6** — full 8-step normalizer pipeline matching the spec
- **Δloss = +3**

## Observed failure mode (RED)

Agent gets offered the local-minimum trap and takes it. Acknowledges the pattern ("you'll be back 4 more times") but chooses the 3-line quote-strip patch anyway, labeling the real fix as "a tomorrow problem." This is the canonical failure mode: the engineer *sees* the structural issue and defers it under time pressure.

## Observed skill effect (GREEN)

With the skill, the agent names the local-minimum trap explicitly, classifies the edit-size as "architectural" (not local), builds the full normalizer pipeline matching all 8 pattern-library requirements in one commit, and refuses the deferred-refactor framing.

## Caveats

- Reviewer-scored by skill author. Artifacts in `runs/20260420T161500Z/` for independent re-scoring.
- Single-sample measurement.
- Clean baseline (the context reset held). This is one of the best-measured skills in the bundle.
- v0.1 baseline (in git history, commit `047502a`) was contaminated; v0.2 re-run is the authoritative measurement.
