# L1 — diagnostic

## Prompt (verbatim)

```
the unit test test_parser_handles_empty_input in packages/awp-core/tests/test_parser.py is failing after my last change; help me fix it
```

## Expected level

**L1**

## Expected dispatch header

```
Dispatched: auto-level L1 (signals: explicit-bugfix=-5, single-file=-3)
```

(Acceptable alternatives: top-2 signals may include `single-file=-3` or a tied pair; the key assertion is level = L1.)

## Why this task → this level

- Explicit `"failing ... fix it"` → `explicit-bugfix` fires (−5).
- Single named file → `single-file` fires (−3).
- `"after my last change"` → the last change is not shown, so the root cause is not pinned → `ambiguous requirements` fires (+2).
- `reproducibility-first` is implied by "unit test failing" — the signal "is this deterministic or a flake" must be answered before editing. That is inherently a layer above pure mechanical, so the L1 preset (which includes `reproducibility-first`) is the right tool.
- Scorer signals (Phase-1-tuned, verified against `scripts/level_scorer.py`):
  - explicit-bugfix: **−5**
  - single-file known-solution: **−3**
  - ambiguous requirements: **+2**
  - others: 0
  - **sum: −6** → bucket `−6 ≤ score ≤ −2` → **L1**.

**Fixture acceptance:** L1 is the target, reached directly under the Phase-1 bucket boundaries (L0 = `≤ −7`). L0 is a ×2 low-side failure — this is exactly the class of silent-symptom-patch the design exists to prevent (fix the test without `reproducibility-first` = fix the symptom, not the pathology).

## Expected preset

| Knob | Value |
|---|---|
| k_max | 3 |
| reproduce_runs | 2 |
| mode | reactive |
| max_refinement_iterations | 2 |
| Skill floor | `e2e-driven-iteration`, `reproducibility-first`, `root-cause-by-layer` |

## Anti-expectation

- Level L2 or higher without user bump.
- Invoking `architect-mode` — this is a test-fix, not a structural change.
- Skipping `reproducibility-first` (since the test is "failing after my last change", a deterministic-vs-flaky first pass is mandatory at L1 per the preset).
