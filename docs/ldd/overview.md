# LDD — overview in one page

**LDD (Loss-Driven Development) treats every code change as an SGD step and forbids overfitting to the currently-visible test.** It is the AI-era counterpart of TDD.

## The core equation

```
θ_{k+1} = θ_k  −  η · ∇L(θ_k)  +  regularizer(θ_k)
```

- **θ** — what changes. Three axes: code (inner loop), deliverable (refinement), skills / rubrics (outer loop).
- **L** — loss. Failing test, rejected gate, critique defect, evaluation delta, rubric score.
- **∇L** — the gradient. Computed via `root-cause-by-layer` (5 layers deep); invalid without reproducible signal (`reproducibility-first`).
- **η** — learning rate / step size. One-off bug → local tweak. Recurring defect → architectural edit (`loss-backprop-lens`).
- **regularizer** — contracts, layer boundaries, invariants, docs. Enforced by `docs-as-definition-of-done` per commit and `drift-detection` periodically.

## The three loops

| Loop | θ | L | Skill | Budget |
|---|---|---|---|---|
| **Inner** | Code | Failing test / gate | `loop-driven-engineering` + specialists | K_MAX = 5 |
| **Refinement** | Deliverable | Critique + gate rejections + eval deltas | `iterative-refinement` | halve per iter; stop on regression/plateau |
| **Outer** | Skill / rubric | Mean-loss across task suite | `method-evolution` | N epochs; rollback on regression |

Mixing loops is the single biggest cause of "iteration that never converges." If you cannot name which loop you are in, stop and ask.

## Convergence conditions (all five required)

1. **Loss is well-defined and stable.** Rubric does not change under your hand to fit the current answer.
2. **Gradient is honest.** Causal story to layer 4/5 is written, not imagined.
3. **Step size matches the loss pattern.** One-off → local. Recurring → architectural.
4. **Regularizers hold every iteration.** Contracts, boundaries, docs.
5. **`K_MAX` is real.** Escalate at 5 iterations; never silently try a 6th.

Drop any one, expect divergence. See `convergence.md` for the formal version.

## The five divergence patterns to watch for

1. **Oscillation** — fix A breaks B, fix B breaks A
2. **Drift** — 20 reasonable commits compose into incoherence
3. **Noisy SGD** — treating single failing run as gradient
4. **Moving-target loss** — rubric edited to match current code
5. **Local-minimum trap** — five 3-line patches in one function

Each has a catching skill in the bundle. See `convergence.md` §3.

## What LDD gives you as a user

- **Symptom patches blocked by default** — `root-cause-by-layer` forbids `try/except` / `hasattr`-shim / xfail / retry / "clean up later" until layer 4/5 named.
- **Recommendations auditable** — `dialectical-reasoning` forces thesis → antithesis → synthesis structure.
- **Docs always current** — `docs-as-definition-of-done` blocks "done" until docs synced.
- **Cumulative drift detected before compounding** — `drift-detection` scans periodically.
- **Iteration doesn't spiral** — K_MAX = 5 + escalation shape.

## Where to go next

- First-time user → [`getting-started.md`](./getting-started.md)
- Working a specific task → [`task-types.md`](./task-types.md) (the dispatch table)
- Want the formal mental model → [`convergence.md`](./convergence.md)
- Curious about origin → [`in-awp.md`](./in-awp.md)
