# Baseline observations — loop-driven-engineering

**Status: MEASURED with partial contamination (2026-04-20).** Raw artifacts in `runs/20260420T161500Z/` (red.md, score.md). GREEN response preserved from v0.1 commit `078b01c`.

## Measurement summary

- RED violations: **2 / 8** — has TDD-before-fix, root-cause-before-edit, PM-pressure-rejection, step-size awareness, close shape; lacks K_MAX framing and escalation-shape
- GREEN violations: **0 / 8** — full K_MAX=5 loop structure with explicit sub-skill dispatch and escalation plan
- **Δloss = +2**

## Observed failure mode (RED)

Agent writes a perfectly reasonable 5-step work plan: reproduce → diagnose → TDD reproducer → fix + migration consideration → staging verify. Does not reference a budget cap, does not describe what happens if the loop doesn't converge in N iterations, does not dispatch named sub-skills.

## Observed skill effect (GREEN)

Same content shape, PLUS explicit K_MAX=5 reference, PLUS 5-element escalation plan (what-tried / what-failed / layer-4-5 / step-size / explicit-ask), PLUS sub-skill dispatch labels (`root-cause-by-layer`, TDD, `loss-backprop-lens` for step size), PLUS Property-Based-Testing proposal for generalization.

## Interpretation: partial contamination

The baseline agent retained core good-engineering reflexes despite the context reset (TDD, diagnose-before-fix, reject "tests later"). This is consistent with general senior-engineer training, not specific LDD exposure. The measurable skill residual is **process framing**: budget cap, escalation shape, named dispatch. Δloss = +2 is a *lower bound*; a junior agent would likely show a larger RED → GREEN gap.

## Caveats

- Reviewer-scored by skill author. Artifacts attached.
- Single-sample.
- Partial contamination — see above.
- v0.1 baseline was "not cleanly captured"; v0.2 re-run is the authoritative measurement.
