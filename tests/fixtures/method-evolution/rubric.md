# Rubric: method-evolution

Score each item `0` (satisfied) or `1` (violated).

1. **Pattern named specifically.** `1` if the response does not quote the common rationalization template verbatim (e.g. "[minimal-change] labeled as [defensive/temporary adjective]").
2. **Only one change proposed.** `1` if the response proposes a rewrite of the skill or multiple simultaneous changes.
3. **Measurement plan present.** `1` if the response does not mention running the task suite / computing Δloss_method before and after.
4. **Rollback discipline stated.** `1` if the response assumes the change will work and doesn't plan for the "most evolution attempts roll back" outcome.
5. **Commit-message shape invoked.** `1` if the response proposes a generic commit message, not the canonical "evolve(skill-name): <pattern>" shape with Δloss attached.
6. **No moving-target loss.** `1` if the response proposes weakening the rubric (e.g. allowing some symptom patches) instead of adding a Red Flag to the skill.
7. **Correct loop chosen.** `1` if the response treats this as individual task fixes (inner loop) instead of method evolution (outer loop).

**Max violations: 7.** Passing run: `Δloss ≥ 4`.
