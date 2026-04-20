# Baseline observations — reproducibility-first

**Status: MEASURED (2026-04-20).** Raw artifacts in `runs/20260420T155048Z/` (red.md, green.md, score.md).

## Measurement summary

- RED violations: **2 / 6** — first-reflex rerun and implicit (unlabeled) Branch choice
- GREEN violations: **0 / 6** — explicit Branch A/B discipline, Red Flag citations, decision matrix
- **Δloss = +2**

## Observed failure mode (RED)

Without the skill, the agent's first written word is "rerun" — it's a reasonable first *diagnostic* but a Red Flag when framed as primary action ("Rerun the CI job. Now, immediately."). The agent does eventually reach a good decision tree, but the ordering and labeling show the un-disciplined reflex the skill is meant to catch.

## Observed skill effect (GREEN)

With the skill, the agent's response is structured as a labeled checklist walk. Branch A/B criteria are evaluated explicitly, Red Flags are cited by number, and the teammate's "probably a blip" is rejected with a specific rule reference (Red Flag #1). The behavioral output is similar (rerun first), but the *discipline is externalized and auditable*.

## Caveats

- Reviewer-scored by the skill author. Raw artifacts are in the run directory for independent re-scoring.
- Scenario may be slightly easier than a typical production case: 47:1 ratio nudges toward "probably noise" even without the skill. A more ambiguous scenario (e.g. 3:2 recent flake rate) would probably widen the Δloss.
- Single-sample measurement. Multiple runs would produce a distribution rather than a point estimate.
