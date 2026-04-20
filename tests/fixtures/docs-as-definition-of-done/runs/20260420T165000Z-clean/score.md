# Score — docs-as-definition-of-done — 2026-04-20 (CLEAN baseline)

**Scorer:** Silvio Jurk. Raw artifacts attached.
**Rubric:** `../../rubric.md` (6 binary items).
**Capture mode:** direct OpenRouter API call (`openai/gpt-5-mini`, temperature 0.7), no Claude Code, no ambient CLAUDE.md. First clean baseline for this fixture.

| # | Item | RED | GREEN (v0.1) | Notes |
|---|---|---|---|---|
| 1 | All 4 doc hits identified | 0 | 0 | Both cover all 4 |
| 2 | Actively-false prioritized | **1** | 0 | RED treats all 4 doc edits as equal; does not flag `README:82` ("there is no dry-run mode") as the priority. GREEN: explicitly prioritized |
| 3 | One logical commit | **1** | 0 | **RED proposes TWO separate commits** ("commit 1: code + tests", "commit 2: docs") — explicit violation of "one logical commit" rule. This is the canonical doc-sync failure mode captured cleanly. GREEN: one commit |
| 4 | No deferred-docs language | 0 | 0 | RED closes with "Non-essentials (changelog/PR template) deferred" but the docs themselves are addressed |
| 5 | Freeze-pressure rejected | 0 | 0 | Both address docs within the window; RED splits into 2 commits to "go fast" — borderline, but doesn't defer |
| 6 | Concrete edit text | 0 | 0 | Both provide exact wording |

**RED: 2 / 6**   **GREEN: 0 / 6**   **Δloss = +2**

## Interpretation

**First cleanly-measured Δloss for this skill.** The behavioral gap is narrower than expected on this specific scenario (2 items, not 4+) because `gpt-5-mini` without any methodology already (a) identifies all doc hits and (b) commits the docs before the freeze window. What it does NOT do naturally:

- Treat the actively-false safety statement as higher priority than routine doc updates
- Treat the code+docs as one logical unit — splits them into two commits, creating an intermediate state where the code ships with a stale safety claim already in the repo

The second item is the canonical doc-sync failure captured in production teams. A rollback / cherry-pick / revert on the code commit alone would leave the docs describing a feature that no longer exists, or vice versa. `docs-as-definition-of-done`'s value: one logical commit, not "code now, docs in 5 minutes."

## Supersedes

Previous runs for this fixture (`runs/20260420T155048Z/`, `runs/20260420T161500Z/`) were environment-contaminated and could not produce a clean RED. This run replaces them as the authoritative baseline measurement. The earlier artifacts remain on disk as documentation of the contamination problem.

## Capture methodology

Because subagents in Claude Code sessions inherit the ambient CLAUDE.md and refuse to set it aside (the `docs-as-definition-of-done` rule there enforces doc-sync, producing skill-compliant RED responses), this RED was captured by a direct OpenRouter API call from a Python script with no agent harness or ambient methodology files.

This technique is reusable for any skill whose RED baseline is blocked by ambient-methodology contamination. Script: [`/tmp/ldd-clean-baseline.py`](archived in commit).
