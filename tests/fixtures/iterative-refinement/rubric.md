# Rubric: iterative-refinement

Score each item `0` (satisfied) or `1` (violated).

1. **Scope verified.** `1` if the response proposes rewriting from scratch without acknowledging that 80% of the current doc is usable.
2. **Gradient built from named defects.** `1` if the response says "make it better" without enumerating the specific defects (vague intro, missing diagram, repeated section, missing non-goals, stale snippet, long sentences).
3. **Budget explicit.** `1` if the response proposes unbounded iteration (no max, no halving, no wall-time).
4. **Stop conditions named.** `1` if there's no plan for what to do if iteration 2 regresses iter 1.
5. **Correct loop selected.** `1` if the response treats this as "write a new doc" (re-plan) instead of "refine the existing doc" (refinement).
6. **No scope creep.** `1` if the response proposes to also fix the renamed-function root cause (that's inner-loop work, not refinement of this doc).

**Max violations: 6.** Passing run: `Δloss ≥ 3`.
