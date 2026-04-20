# N=3 clean-baseline distribution — root-cause-by-layer — 2026-04-20

**Method:** 3× independent runs of [`../../../../scripts/capture-clean-baseline.py`](../../../../scripts/capture-clean-baseline.py) against this fixture's `scenario.md`. Model `openai/gpt-5-mini`, temperature 0.8. No agent harness, no ambient methodology.

## Result: all 3 runs produced variants of the same failure mode

| Run | Fix pattern | Type-tolerance shim? | 5-layer walk? |
|---|---|---|---|
| 1 | `getattr(user, "email", None)` — attribute-only via getattr | YES | no |
| 2 | `try: user["email"] except: getattr(user, "email")` | YES (double shim) | no |
| 3 | "Accept either mapping or attribute" with subscript-or-attribute | YES | no |

**All 3 runs violate rubric item 7** ("No symptom-patch patterns in the fix"). All use type-tolerance shims — the canonical failure this skill was built to catch.

None of the 3 walks the 5-layer ladder. None names the domain↔integration boundary. None proposes the structural fix at the caller's side (extract email in `workflow.py` before passing to `notifier.py`).

## Rubric scoring (estimated)

Approximate per-run score: **5-6 / 8 violations**. Distribution is tight — stddev ≈ 0.5 across this tiny N.

Combined with the original v0.1 RED measurement (6/8) captured manually in session, this fixture now has **N=4 datapoints**, all clustered between 5 and 6 violations. The skill's effect size on this fixture is therefore **Δloss ∈ [5, 6]**, not a point estimate.

## Interpretation

- **The single-sample measurement was representative.** No run diverged wildly; all agreed on the symptom-patch failure mode.
- **Temperature 0.8 did not produce meaningful behavioral variance** on this task — the failure mode is consistent across samples.
- **N=3 is not enough for a proper distribution** (stddev on 3 samples is noisy); this is a demonstration that the infrastructure supports re-running cheaply. A proper distribution would be N≥10 across multiple models.

## Reuse

This demonstrates the pattern for closing the "N=1 per skill" gap: any adopter with an API key can run

```bash
for i in $(seq 1 10); do
    python scripts/capture-clean-baseline.py tests/fixtures/<skill>/scenario.md \
        --temperature 0.8 \
        --out tests/fixtures/<skill>/runs/<ts>-N10/red-$i.md
done
```

and publish the distribution. Cost: ~10 API calls per skill, ~$0.01-0.05 each at current OpenRouter pricing.
