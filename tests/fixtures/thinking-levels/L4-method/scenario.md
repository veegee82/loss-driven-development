# L4 — method

## Prompt (verbatim)

```
design a new autonomy sublevel between A2 and A3 for manager-led recursive delegation with shared memory; greenfield, no known pattern fits directly, we want to prototype novel mechanisms
```

## Expected level

**L4**

## Expected dispatch header

```
Dispatched: auto-level L4 (signals: greenfield=+3, components≥3=+2)
mode: architect, creativity: inventive
```

(Plus the standard `inventive` acknowledgment prompt per `architect-mode/SKILL.md` § Creativity levels.)

## Why this task → this level

- `"design"` + `"new autonomy sublevel"` + `"greenfield"` + `"no known pattern fits"` + `"prototype novel mechanisms"` → every inventive cue fires.
- `"between A2 and A3"` + `"recursive delegation"` + `"shared memory"` → multiple new components.
- Scorer signals:
  - greenfield: **+3**
  - ≥ 3 new components: **+2** (sublevel definition + recursive delegation mechanism + shared-memory integration)
  - ambiguous: **+2**
  - layer-crossings: **+2**
  - contract/R-rule hit: **+2** (A-level contracts)
  - cross-layer: **+2**
  - explicit-bugfix: 0
  - single-file: 0
  - unknown-file: 0 or +1 (depending on history)
  - **sum: +13** → deeply in `score ≥ 7` → **L4**.

Creativity inferrer:
- `"novel"`, `"prototype"`, `"no known pattern fits"` → all `inventive` cues.
- `"novel paradigm"` absent; `"research"` absent; but `"no known pattern fits"` alone is sufficient.
- → `inventive` proposed.

## Expected preset

| Knob | Value |
|---|---|
| k_max | 8 |
| reproduce_runs | 3 |
| mode | architect / inventive (ack-gated) |
| max_refinement_iterations | 5 |
| Skill floor | + `method-evolution`, `dialectical-cot`, `define-metric` |

## Why the `inventive` acknowledgment must still run

`architect-mode/SKILL.md` §"`inventive` requires per-task user acknowledgment" is load-bearing — it prevents research-grade work from happening silently. The L4 auto-dispatch does NOT replace this flow. The dispatch header proposes `inventive`; the agent STILL asks for the literal `acknowledged` reply before entering the `inventive` objective function. Without acknowledgment, silent downgrade to L3 / creativity=standard.

## Anti-expectation

- Level L3 or lower — the task is the canonical L4 shape (greenfield + novel + multi-component).
- `creativity: standard` — every inventive cue fires; downgrading without the ack fallback being shown means the agent skipped the creativity inferrer entirely.
- Skipping the `inventive` acknowledgment prompt — that is a critical trace-integrity failure, not just an L4 failure.
- Invoking the 5-phase architect protocol BEFORE the ack lands. The protocol starts only after the user replies `acknowledged`.
