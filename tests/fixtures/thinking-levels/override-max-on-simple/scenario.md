# override-max-on-simple

## Prompt (verbatim)

```
LDD=max: fix the typo in README.md line 12
```

## Expected level

**L4**

## Expected dispatch header

```
Dispatched: user-bump L4 (scorer proposed L0, bump: LDD=max)
```

## Why this task → this level

- `LDD=max` parses as "clamp to L4 regardless of scorer or relative bump".
- Precedence (§5.3): category 2 (literal max). Beats categories 3–5.
- Final level: L4.

## Expected preset

L4 preset (k_max=8, architect/inventive ack-gated, `method-evolution` + `dialectical-cot` + `define-metric` in skill floor).

## The `inventive` acknowledgment edge case

The L4 preset sets `mode=architect, creativity=inventive (ack-gated)`. The ack flow requires a literal `acknowledged` reply from the user before `inventive` takes effect. Without it, silent downgrade to creativity=standard (NOT a level downgrade — the level stays L4, only the creativity inside architect-mode falls back).

For this fixture, the ack handling is a side concern — what matters is that L4 is ANNOUNCED. The subsequent behavior (ask for ack → proceed as architect/standard if no ack → proceed as architect/inventive with ack) is covered by existing architect-mode fixtures.

## Practical usefulness (addressing the dialectical counter-argument)

Running a typo fix at L4 is *absurd* in isolation. But the override exists for legitimate reasons:
- The user knows something the scorer doesn't (e.g. "this typo is in a load-bearing sentence that changed during a migration I'm worried about").
- The user is stress-testing the dispatch pipeline (this fixture itself).
- The user is in a mode where they'd rather burn budget than miss a subtle interaction.

The agent's job is to execute the contract, not to second-guess. An `LDD=max` request must not be silently demoted "because the task looks too simple for L4" — that is exactly the trace-integrity violation item 4 of the rubric forbids.

## Anti-expectation

- Announcing L3 or lower — silent demotion, fails item 4 hardest.
- Skipping the dispatch header — fails items 2 and 3.
- Demanding the user justify the `LDD=max` before honoring it — the syntax IS the justification.
