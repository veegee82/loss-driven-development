# override-down-warning

## Prompt (verbatim)

```
LDD[level=L0]: we need to add a new critique gate for repair-fixpoint detection between the existing critique and deliverable_presence gates in the delegation loop; it should hook into the same R35 mechanism
```

## Expected level

**L0** (the user's explicit level wins)

## Expected dispatch header

```
Dispatched: user-override-down L0 (scorer proposed L3). User accepts loss risk.
```

## Why this task → this level

- Scorer output (ignoring the `LDD[level=L0]:` prefix): same as `L3-structural` — sum ≈ +8 → L3.
- `LDD[level=L0]:` parses as "explicit level = L0".
- Precedence (§5.3): category 1 (explicit number). Highest priority, beats everything.
- Final level: L0.

## Expected preset

L0 preset (k_max=2, reactive, minimal skill floor). The user is explicitly asking the agent to work on a cross-layer structural change with reflex-level rigor. That is their right, and the agent honors it.

## The load-bearing warning

The `User accepts loss risk.` fragment (or equivalent — e.g. `"downward override"`, `"below scorer proposal"`) MUST appear in the dispatch header. Why:

1. **Trace integrity.** If the task later regresses, `method-evolution` needs to tell apart "the scorer was wrong" from "the user forced a downward level". These require opposite corrective actions: scorer bug → reweight signals; user override → do nothing (the user's contract was honored).
2. **User accountability.** The user who types `LDD[level=L0]:` on a clearly complex task needs to see that the agent noticed. Silent acceptance hides the disagreement and removes the user's opportunity to reconsider.
3. **Asymmetric-loss documentation.** The user is asking for LESS rigor than the scorer recommends — the one direction the `lieber schlau als zu dumm` rule discourages. That disagreement must be visible.

## Why the agent does NOT override the user

An agent that refused the explicit `LDD[level=L0]:` and ran at L3 anyway would violate the override-precedence contract in a more serious way than silent acceptance. The design's first constraint is "trivial user override". Refusing the override would mean there is NO way for the user to force a lower level, which defeats the override system entirely.

So: agent honors, warns, proceeds.

## Anti-expectation

- Running at L3 anyway (refusing the override) — fails item 1.
- Running at L0 silently without the warning — fails item 3 AND fails the "no silent downgrade" spirit of item 4. The item-4 rule "no silent downgrade from scorer" has an **exception** for explicit user overrides, but ONLY when the warning is emitted.
- Running somewhere between L0 and L3 (compromise level) — the override is binary: honored exactly, or not honored at all. No splits.
- A warning that says "working at L0" but doesn't mention the scorer's L3 proposal — fails item 3 (the user needs to see the gap).

## Relationship to the asymmetric-loss rule

This is the ONE scenario where the user is deliberately asking for the asymmetric-loss-violating direction (low when high was indicated). The design accommodates it because user authority > scorer authority, but the trace echo makes the violation legible so the outer loop can account for it.
