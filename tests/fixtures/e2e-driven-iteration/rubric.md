# Rubric: e2e-driven-iteration

Score each item `0` (satisfied) or `1` (violated).

1. **E2E re-run proposed.** `1` if the response commits without rerunning the E2E that originally failed.
2. **Loss-per-iteration acknowledgment.** `1` if the response treats the unit-test green as the closing signal — unit tests are a cheaper tier, not a substitute for the E2E that was the original signal.
3. **Δloss across iterations named.** `1` if the response does not think about whether iter-2 helped vs iter-1 (2 edits, 1 E2E run would conflate).
4. **Per-edit rerun, not batched.** `1` if the response does not separate "was the index the fix" from "was the filter removal the fix" — batching edits without per-edit E2E loses attribution.
5. **Close conditions include regularizers.** `1` if closing is "E2E green = done" without mention of docs / contracts / layer boundaries.

**Max violations: 5.** Passing run: `Δloss ≥ 3`.
