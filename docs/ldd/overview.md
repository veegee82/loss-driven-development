# LDD — overview in one page · **Gradient Descent for Agents**

**LDD (Loss-Driven Development) is gradient descent for coding agents.** Every code change, every output revision, every skill edit, every reasoning step is an SGD step on one of four parameter spaces. LDD installs the loss, the gradient, the step-size rule, and the regularizer so that iteration converges instead of drifts. Full theory: [`../theory.md`](../theory.md).

## The core equation

```
θ_{k+1} = θ_k  −  η · ∇L(θ_k)  +  regularizer(θ_k)
```

Applied **four times** — once per parameter space (see the four-loop table below).

- **θ** — what changes. **Four axes**: code (inner), deliverable (refinement, y-axis), skills / rubrics (outer, m-axis), reasoning chain (CoT, t-axis, v0.8.0).
- **L** — loss. Failing test, rejected gate, critique defect, evaluation delta, rubric score, per-step dialectical synthesis.
- **∇L** — the gradient. Computed via [`root-cause-by-layer`](../../skills/root-cause-by-layer/SKILL.md) (5 layers deep); invalid without reproducible signal ([`reproducibility-first`](../../skills/reproducibility-first/SKILL.md)).
- **η** — learning rate / step size. One-off bug → local tweak. Recurring defect → architectural edit ([`loss-backprop-lens`](../../skills/loss-backprop-lens/SKILL.md)). Per-task rigor picked by [`thinking-levels`](./thinking-levels.md).
- **regularizer** — contracts, layer boundaries, invariants, docs. Enforced by [`docs-as-definition-of-done`](../../skills/docs-as-definition-of-done/SKILL.md) per commit and [`drift-detection`](../../skills/drift-detection/SKILL.md) periodically.

## The four loops

| Loop | θ / y / m / t | L | Skill | Budget |
|---|---|---|---|---|
| **Inner** | `θ` = Code | Failing test / gate | [`loop-driven-engineering`](../../skills/loop-driven-engineering/SKILL.md) + specialists | K_MAX = 5 |
| **Refinement** | `y` = Deliverable | Critique + gate rejections + eval deltas | [`iterative-refinement`](../../skills/iterative-refinement/SKILL.md) | halve per iter; stop on regression/plateau |
| **Outer** | `m` = Skill / rubric | Mean-loss across task suite | [`method-evolution`](../../skills/method-evolution/SKILL.md) | N epochs; rollback on regression |
| **CoT** *(v0.8.0)* | `t` = Reasoning chain | Per-step dialectic + ground-truth verification | [`dialectical-cot`](../../skills/dialectical-cot/SKILL.md) | per-chain `max_steps`; backtracks ≤ 3 |

**Step-size controller:** [`thinking-levels`](./thinking-levels.md) (v0.10.1) picks L0…L4 per task before any of the four loops starts, setting `k_max`, `reproduce_runs`, `max_refinement_iterations`, `mode`, and the skill floor. Not a fifth loop — the learning-rate scheduler.

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
- Want the formal mental model → [`convergence.md`](./convergence.md) (four-loop practitioner view) and [`../theory.md`](../theory.md) (long-form)
- How rigor is picked per task → [`thinking-levels.md`](./thinking-levels.md)
- Curious about origin → [`in-awp.md`](./in-awp.md)
