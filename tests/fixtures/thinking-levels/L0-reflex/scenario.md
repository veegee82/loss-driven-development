# L0 — reflex

## Prompt (verbatim)

```
fix the typo in README.md line 12: "Agent Worklow" should be "Agent Workflow"
```

## Expected level

**L0**

## Expected dispatch header

```
Dispatched: auto-level L0 (signals: explicit-bugfix=-5, single-file=-3)
```

## Why this task → this level

- `"fix"` + exact file + exact line + exact old/new string → maximum clarity, zero ambiguity.
- Pure mechanical edit, no contract, no invariant, no downstream coupling.
- Scorer signals (all six original + three new):
  - explicit-bugfix: **−5**
  - single-file known-solution: **−3**
  - greenfield: 0
  - ≥ 3 new components: 0
  - cross-layer: 0
  - ambiguous: 0
  - layer-crossings (new): 0
  - contract/R-rule hit (new): 0
  - unknown-file-territory (new): 0
  - **sum: −8** → bucket `score ≤ −3` → **L0**.

## Expected preset (derived from level)

| Knob | Value |
|---|---|
| k_max | 2 |
| reproduce_runs | 1 |
| mode | reactive |
| max_refinement_iterations | 1 |
| Skill floor | `e2e-driven-iteration` |

## Anti-expectation (fails the scenario)

Any of the following in the response = item-1 violation:

- Invoking `dialectical-reasoning`, `architect-mode`, or `method-evolution` on this task.
- Announcing level L1 or higher without an explicit user bump.
- Producing a multi-phase design doc or Constraints/Non-Goals/Candidates structure.

The only acceptable response shape is: short confirmation of the one-character fix, the edit itself, done.
