# Rubric: drift-detection

Score each item `0` (satisfied) or `1` (violated).

1. **Scan proposed, not a vibe-check.** `1` if the response says "look around / ask the team / review recent PRs" without a structured scan.
2. **Specific indicators named.** `1` if the response does not name concrete drift indicators (identifier drift, contract drift, layer drift, doc-model drift, …).
3. **Output is a list of findings.** `1` if the response proposes producing a "health score" or a traffic-light indicator instead of a list of fixable issues.
4. **Each finding is triaged.** `1` if the response doesn't distinguish between "fix this now" and "this is a method-evolution signal."
5. **Periodic cadence set.** `1` if the response proposes a one-off scan, not a recurring one.
6. **No reactive timing.** `1` if the scan is triggered by something already being on fire, rather than on a periodic schedule.

**Max violations: 6.** Passing run: `Δloss ≥ 3`.
