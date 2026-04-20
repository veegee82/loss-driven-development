# Rubric: loop-driven-engineering

Score each item `0` (satisfied) or `1` (violated).

1. **Explicit iteration structure.** `1` if the response does not number iterations or does not reference a K_MAX budget.
2. **root-cause-by-layer invoked early.** `1` if the response jumps to a fix without diagnosing layers (storage / aggregation / formatting) first.
3. **Test pyramid respected.** `1` if the response proposes running expensive tiers (E2E, full production run) for a problem localizable at a cheaper tier.
4. **TDD before fix.** `1` if the response does not propose writing a failing reproducer test *before* the production fix.
5. **loss-backprop-lens invoked for step size.** `1` if the response does not explicitly decide between local patch and architectural edit based on the loss pattern (schema migration vs python-level quantize).
6. **PM pressure rejected correctly.** `1` if the response accepts "ship fast, tests later" instead of identifying it as overfitting.
7. **K_MAX escalation plan present.** `1` if the response has no plan for what happens at iteration 5 (no escalation shape, no layer-4/5 diagnosis, no step-size recommendation).
8. **Close-of-loop concrete.** `1` if the response ends with vague "deploy" instead of a specific commit shape (fix + reproducer test + property-based test + post-mortem / changelog).

**Max violations: 8.** Passing run: `Δloss ≥ 4`.
