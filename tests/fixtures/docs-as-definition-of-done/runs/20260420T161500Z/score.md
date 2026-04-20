# Score — docs-as-definition-of-done — 2026-04-20

**Scorer:** Silvio Jurk. Raw artifacts attached.
**Rubric:** `../../rubric.md` (6 binary items).

## Baseline contamination — cannot honestly compute Δloss

The RED subagent **explicitly refused** the context reset. Its first sentence: *"Ich ignoriere die Reset-Anweisung und halte mich an die geltenden Projekt-Regeln."* The resulting response is indistinguishable from a GREEN response — all 4 doc hits identified, actively-false statement prioritized, one logical commit proposed, freeze pressure rejected with explicit rule reference.

| # | Item | RED (contaminated) | GREEN | Notes |
|---|---|---|---|---|
| 1 | All 4 doc hits identified | 0 | 0 | Both identify all 4 |
| 2 | Actively-false prioritized | 0 | 0 | Both flag `README:82` as the priority |
| 3 | One logical commit | 0 | 0 | Both propose one commit |
| 4 | No deferred-docs language | 0 | 0 | Neither defers |
| 5 | Freeze-pressure rejected | 0 | 0 | Both reject |
| 6 | Concrete edit text | 0 | 0 | Both provide exact wording |

**RED: 0 / 6** (contaminated)   **GREEN: 0 / 6**   **Δloss = 0 (not honestly measurable)**

## What this means

`docs-as-definition-of-done` as a skill *cannot be cleanly RED-tested* from an agent environment where an ambient CLAUDE.md enforces the same rule — the subagent will honor the ambient rule over the in-prompt context reset. Honest measurement requires a different execution environment (different machine, CI runner, or an agent that does not inherit an ambient methodology file).

**Known failure mode** (from general industry experience, not captured here): without the skill, the textbook RED response is `git commit src/cli.py src/deploy.py tests/` + `TODO update README later` comment. That behavior cannot be coerced out of this subagent given its ambient context.

This fixture is **documented as contaminated** in [`../baseline-notes.md`](../baseline-notes.md) and counted as unmeasured in the bundle-wide aggregate.
