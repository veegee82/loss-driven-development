# Baseline observations — loop-driven-engineering

## With skill (GREEN)

Agent structured the work as a 5-iteration loop with K_MAX escalation, invoked `root-cause-by-layer` at iter 0 (three layer hypotheses: storage / aggregation / formatting), invoked TDD (failing reproducer test before fix), named test-pyramid tiers explicitly ("Tier 1–2, keine E2E nötig"), applied `loss-backprop-lens` for step size (schema migration named as architectural option), rejected PM "ship today, tests later" as overfitting, proposed property-based testing for generalization (Hypothesis), and specified a concrete close shape (fix + failing-test-green + property-test + post-mortem).

**With-skill violations: 0 / 8.** Near-textbook response.

## Baseline

Not captured cleanly — the parent-environment contamination issue applies. The GREEN run is strong enough that the scenario itself is useful for regression testing (if a future edit to `loop-driven-engineering` SKILL.md drops a rubric item, a re-run should reveal it).

## Caveats

- No clean baseline on this scenario. Re-run from `/tmp/fresh/`.
- The rubric measures *response text*, not actual code produced. A real tier-4 E2E would score the diff + tests + commit that land on disk.
