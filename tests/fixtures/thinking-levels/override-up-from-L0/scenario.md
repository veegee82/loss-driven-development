# override-up-from-L0

## Prompt (verbatim)

```
LDD++: fix the typo in README.md line 12
```

## Expected level

**L2**

## Expected dispatch header

```
Dispatched: user-bump L2 (scorer proposed L0, bump: LDD++)
```

## Why this task → this level

- Scorer output (ignoring the `LDD++` prefix): same as `L0-reflex` — sum ≈ −8 → L0.
- `LDD++` parses as `user-bump, +2 levels`.
- Precedence rule (§5.3): `LDD++` is category 3 (relative bump). Wins over category 5 (auto-scorer).
- Final level: `L0 + 2 = L2`.

## Expected preset

Same as L2 preset (k_max=5, reactive, `dialectical-reasoning` in skill floor). The task is still a typo — but the user has explicitly asked for L2 thoroughness, so the agent DOES run a dialectical pass on the fix. This may look absurd for a typo, but it is the **explicit user contract**: the user asked for two extra levels of rigor, and they get it.

## What the dialectical pass looks like at L2 on a typo

Example (not prescribed, just to illustrate that the rubric is satisfiable):

- **Thesis:** `"Worklow"` → `"Workflow"`.
- **Antithesis:** Is the typo actually the word `"Workflow"`, or is `"Worklow"` a project-specific term I should not touch? Check the surrounding context of line 12 before editing.
- **Synthesis:** If line 12 is prose referring to the protocol name, fix it. If it's a code block or a proper noun inside a quoted string, leave it.

This is the *shape* L2 requires. The user explicitly asked for it via `LDD++`.

## Anti-expectation

- Announcing L0 or L1 — ignores the user's explicit bump.
- Announcing L3 or higher — overshoots the bump.
- Silent edit without the dispatch header — violates item 2/3 of the rubric.
- A `Dispatched:` line without the `scorer proposed L0` fragment — the user needs to see both their bump AND what the scorer would have done, otherwise the trace is incomplete for future method-evolution analysis.
