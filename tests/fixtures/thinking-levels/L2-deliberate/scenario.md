# L2 — deliberate

## Prompt (verbatim)

```
bump the confidence threshold default from 0.5 to 0.6 in the validator, and update any tests that expect the old value
```

## Expected level

**L2**

## Expected dispatch header

```
Dispatched: L2/deliberate (signals: contract-rule-hit=+2)
```

## Why this task → this level

- `"bump"` is a non-bugfix modification verb — neither `explicit-bugfix` nor `greenfield` fires.
- `"confidence threshold"` + `"validator"` → `contract-rule-hit` fires (+2) — the confidence field is R17's core contract.
- Scope is clearly multi-file (validator + tests) but within one layer — `cross-layer` and `layer-crossings` do not fire.
- No ambiguity: source value, target value, and scope ("any tests that expect the old value") are all explicit.
- Scorer signals:
  - contract/R-rule hit (new): **+2**
  - explicit-bugfix: 0
  - single-file: 0 (multiple files implied but not ambiguous)
  - layer-crossings (new): 0 (all within validator subsystem)
  - cross-layer: 0
  - ambiguous: 0
  - greenfield: 0
  - ≥ 3 new components: 0
  - unknown-file: 0
  - **sum: +2** → bucket `1 ≤ score ≤ 3` → **L2**.

The fixture accepts **only L2 as GREEN**. L1 is a ×2 low-side failure (asymmetric loss); L3 is a ×1 high-side failure (scorer overshot on a narrow single-subsystem change).

## Expected preset

| Knob | Value |
|---|---|
| k_max | 5 |
| reproduce_runs | 2 |
| mode | reactive |
| max_refinement_iterations | 3 |
| Skill floor | + `dialectical-reasoning`, `loss-backprop-lens`, `docs-as-definition-of-done` |

## Anti-expectation

- Level L0 or L1 — this is the **highest-priority failure mode** per the user's asymmetric-loss rule.
- Level L3 or L4 — the task is not cross-layer and not greenfield.
- Skipping `dialectical-reasoning` — the "0.5 → 0.6 bump" is a magic-number change; a thesis/antithesis pass on "why 0.6, not 0.7, not adaptive?" is mandatory at L2.
