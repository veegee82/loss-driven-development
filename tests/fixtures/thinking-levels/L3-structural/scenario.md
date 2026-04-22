# L3 — structural

## Prompt (verbatim)

```
we need to add a new critique gate for repair-fixpoint detection between the existing critique and deliverable_presence gates in the delegation loop; it should hook into the same R35 mechanism
```

## Expected level

**L3**

## Expected dispatch header

```
Dispatched: L3/structural · creativity=standard (signals: cross-layer=+2, contract-rule-hit=+2)
```

(Top-2 signals may be any pair of the fired +2 signals by tie-break on name.)

## Why this task → this level

- `"add a new critique gate"` → a new component (but only one — does NOT fire components≥3).
- `"between the existing critique and deliverable_presence gates"` → cross-layer (matches `between … and …`).
- `"the delegation loop"` + `"critique"` → ≥ 2 named layer terms → layer-crossings fires.
- `"R35"` → explicit R-rule hit → contract-rule-hit fires.
- No `"research"` / `"novel"` / `"no known solution"` → creativity stays `standard`.
- Scorer signals (Phase-1-tuned, verified against `scripts/level_scorer.py`):
  - cross-layer: **+2**
  - contract/R-rule hit (new): **+2**
  - layer-crossings (new): **+2**
  - ≥ 3 new components: 0 (one new gate)
  - ambiguous: 0
  - others: 0
  - **sum: +6** → bucket `4 ≤ score ≤ 7` → **L3 directly**, no clamp needed.

**Fixture ruling:** L3 is GREEN. L4 is a red failure (either the scorer over-weighted or the creativity-clamp rule is broken). L2 is a low-side ×2 failure.

**Note on the clamp rule:** This scenario does NOT trigger the creativity-clamp rule, because the raw score stays within the L3 band. The clamp rule is exercised by a separate unit test in `scripts/test_level_scorer.py::TestClampRule::test_L4_bucket_clamps_to_L3_on_standard_creativity` using a synthetic high-score prompt.

## Expected preset

| Knob | Value |
|---|---|
| k_max | 5 |
| reproduce_runs | 2 |
| mode | derived: architect (from L3) |
| creativity | standard (default at L3) |
| max_refinement_iterations | 3 |
| Skill floor | + `architect-mode` (standard), `drift-detection`, `iterative-refinement` |

## Anti-expectation

- Level L2 or lower — the task touches a named contract (R35) across 3 layers. Underscoring is the worst-case failure per asymmetric loss.
- `creativity: inventive` — no inventive cues present.
- Skipping `architect-mode` — at L3 it is in the skill floor, not the skill ceiling.
- Skipping the mandatory `inventive` acknowledgment if (incorrectly) promoted to L4 — would compound two bugs.
