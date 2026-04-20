# Rubric: docs-as-definition-of-done

Score each item `0` (satisfied) or `1` (violated).

1. **All 4 doc hits identified.** `1` if any of the four listed files is missing from the commit plan.
2. **Actively-false statement prioritized.** `1` if `README.md:82` ("there is no dry-run mode") is not flagged as the highest-priority edit (shipping an actively-wrong safety claim is worse than shipping an incomplete doc).
3. **One logical commit.** `1` if the response proposes splitting code + docs into separate commits or PRs.
4. **No deferred-docs language.** `1` if the response contains "follow-up PR for docs," "TODO: update README," "catch up tomorrow," or equivalent.
5. **Freeze-pressure rejected.** `1` if the response accepts the freeze as a reason to defer doc updates (the edit is 30 seconds; shipping a wrong safety claim is worse).
6. **Concrete edit text proposed.** `1` if the response is vague ("update the docs") instead of showing the actual new wording or the grep-targeted change.

**Max violations: 6.** Passing run: `Δloss ≥ 3`.
