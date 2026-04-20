# Baseline observations — loss-backprop-lens

**Important caveat:** the baseline for this scenario was captured from a subagent that **refused to ignore** the parent project's `CLAUDE.md` and produced a skill-correct architectural answer even without the skill loaded. The captured "baseline" is therefore contaminated and not a useful measurement.

What we observed with the skill loaded (GREEN): the agent correctly identified the local-minimum trap, chose architectural step size, and produced a normalizer pipeline matching the full 8-step spec instead of a 6th 3-line patch. `Δloss` cannot be honestly computed from this run.

To fix: the fixture must be re-run from a truly clean directory (`/tmp/fresh/` with no `CLAUDE.md` anywhere in the ancestor chain). The prompt as written in `scenario.md` is ready; only the execution environment needs to be cleaner.

This is an open issue. See [../../../GAPS.md](../../../GAPS.md).
