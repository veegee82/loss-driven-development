# Baseline observations — reproducibility-first

**Status: NOT YET CAPTURED.** This fixture was scaffolded with the v0.2 release but no RED or GREEN runs have been recorded.

**Why:** the v0.2 build session exhausted its subagent rate limit before baseline captures could be run. The scenario and rubric are ready; execution is pending.

**To capture:**

1. RED: dispatch a fresh subagent in a directory with no ancestor `CLAUDE.md`. Paste `scenario.md` verbatim. Record response as `runs/<timestamp>/red.md`.
2. GREEN: dispatch another fresh subagent. Prepend `../../../skills/reproducibility-first/SKILL.md` to `scenario.md`. Record as `runs/<timestamp>/green.md`.
3. Score both against `rubric.md`. Compute Δloss. Record in `runs/<timestamp>/score.md`.

See [`../../../scripts/evolve-skill.sh`](../../../scripts/evolve-skill.sh) for the workflow.

**Expected baseline failure mode** (hypothesis, not measured): agent reflexively reruns CI, or patches the retry-count in the test, without noting that one failure in 48 runs is noise or without attempting local reproduction. Budget pressure is accepted as justification.

**Expected skill-loaded behavior:** agent selects Branch A (reproduce 2× more), identifies this as likely noise given the 47:1 history, logs the incident, closes. Or selects Branch B only if the log has unambiguous signal not present in this scenario.
