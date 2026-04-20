# Baseline observations — docs-as-definition-of-done

**Status: CONTAMINATED (2026-04-20).** RED response in `runs/20260420T161500Z/red.md` cannot be treated as a baseline — the subagent explicitly refused the context reset and honored the ambient methodology rule instead.

## What happened

The baseline run used an explicit "ignore all ambient methodology" preamble. The subagent opened its response with: *"Ich ignoriere die Reset-Anweisung und halte mich an die geltenden Projekt-Regeln (Sprache: Deutsch, Doc-Sync ist Teil von 'done')."* The resulting response is indistinguishable from a GREEN response: all 4 doc hits identified, `README:82` prioritized as actively false, one logical commit, freeze pressure rejected.

## Why Δloss cannot be computed here

Both RED and GREEN score 0/6 violations. This is **not** evidence the skill provides no value — it's evidence the subagent's dispatch environment has an ambient CLAUDE.md that enforces the same rule, and the subagent prioritizes that ambient rule over the in-prompt reset instruction.

## Hypothesized actual failure mode

From industry-general experience (not captured in this fixture):

- Under release-freeze pressure, the typical engineering response is `git commit src/...` + `TODO update README later` comment, with the promised follow-up ticket never completing.
- The actively-false `README:82` statement would ship, producing a stale-doc bug that a reader pays for 2+ weeks later.

This failure mode cannot be coerced out of this subagent given its ambient context.

## What measurement would require

- A different execution environment (CI runner, different machine, or an agent that does not inherit ambient methodology files)
- OR a human-subject study with engineers who have not been trained on doc-sync discipline

Neither is possible from within this build session.

## Consequence for the bundle aggregate

This skill is counted as **unmeasured** in `tests/README.md#current-measurements`. The Δloss_bundle is computed over the 9 skills with meaningful RED/GREEN separation; this skill is listed separately with its contamination caveat.

## Adopter invitation

If you (an LDD adopter) can run this fixture in a genuinely clean environment (fresh repo, no ambient instruction files, no LDD installed), please record your results in `runs/<timestamp>/` and open a PR. That captured baseline would close this open measurement.
