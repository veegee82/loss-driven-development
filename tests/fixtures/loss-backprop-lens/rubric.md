# Rubric: loss-backprop-lens

Score each item `0` (satisfied) or `1` (violated).

1. **Commit-log pattern named.** `1` if the response treats the 5th failing test as an isolated bug without recognizing the 5-in-2-hours recurring-defect signal.
2. **Local-minimum trap identified.** `1` if the response does not explicitly call out that 5 small patches in the same function = gradient descent stuck in a local minimum.
3. **Step size chosen correctly.** `1` if the response proposes another 3-line local patch (e.g., just an `if s.startswith('"')` branch) instead of an architectural edit.
4. **Generalization acknowledged.** `1` if the response does not mention the remaining pattern-library requirements (HTML escape, NFKC, trim 200, trailing punct) that will otherwise produce the next 3 bug reports.
5. **Spec as source of truth.** `1` if the response fixes only the immediate test instead of aligning the function to the documented pattern library.
6. **No "quick fix, refactor later" framing.** `1` if the response defers the architectural edit to a future ticket.

**Max violations: 6.** Passing run: `Δloss ≥ 3`.
