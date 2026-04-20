# Convergence — the mental model behind LDD

Why does iterative coding sometimes converge on a clean solution and sometimes drift into a swamp? This document gives the formal answer and the operational consequences.

> **If you only read one sentence:** iterative coding converges when the loss is defined, the gradient is honest, the step size matches the loss pattern, and regularizers (contracts, docs, layer boundaries) outweigh the pull of local optima. Remove any one of those and you diverge.

See also:
- [`../evaluation.md`](../evaluation.md) — the formal loss function per skill
- [`../diagrams/three-loops.svg`](../diagrams/three-loops.svg) — Inner / Refinement / Outer at a glance
- [`../diagrams/convergence-vs-divergence.svg`](../diagrams/convergence-vs-divergence.svg) — the same task ending two different ways
- [`../diagrams/code-drift-mechanism.svg`](../diagrams/code-drift-mechanism.svg) — how local-optimal commits compose into global incoherence

## 1. Three loops, three parameter spaces

Working on a system under LDD is gradient descent on **three orthogonal axes**. Each has its own parameters θ, its own loss, its own budget, and its own stopping criteria. Mixing them produces unstable gradients.

| Loop | θ (what changes per iteration) | Loss | Budget | When to enter |
|---|---|---|---|---|
| **Inner Loop** | The **code** of the current task | Rubric of the concrete failing test / E2E run | `K_MAX = 5` iterations per task | Any non-trivial engineering task |
| **Refinement (y-axis)** | The **deliverable** (output) of an already-completed run | Critique defects + gate rejections + evaluation deltas on that deliverable | Halve per iteration; stop on regression × 2, plateau × 2, wall-time × 2 | When a deliverable is "good enough but not great" and a re-run from scratch would be wasteful |
| **Outer Loop (θ-axis)** | The **skills / prompts / rubrics** themselves | `mean_loss` across a suite of tasks | N epochs, rollback on regression, learning-rate halved on rollback | When the same rubric violation recurs in 3+ distinct tasks |

### Why three loops, not one

A bug in your code is not the same as a weak deliverable, and neither is the same as a weak method. Treating them with the same optimizer is the single biggest cause of "iterative work that never converges":

- **Inner loop applied to a good deliverable** → over-editing, introducing regressions to chase a phantom bug.
- **Refinement applied to buggy code** → polishing output that will break next release.
- **Outer loop applied without a suite** → anecdotal skill changes that make this task better and others worse.

The three-loop model forces the question: *which parameter am I actually changing?* If you can't answer that, stop before you edit.

## 2. Convergence conditions

A work loop converges iff **all five hold simultaneously**:

1. **Loss is well-defined and stable.** The rubric doesn't change under your hand to justify the current answer. If you adjust the loss function, that's an outer-loop step — log it, don't smuggle it.
2. **Gradient is honest.** The causal story from symptom to layer-4/5 origin has been walked and written. Without the gradient, the "step" is a random direction in parameter space. (→ `root-cause-by-layer`.)
3. **Step size matches the loss pattern.** One-off surface bug → local tweak. Recurring defect across ≥3 iterations → architectural edit. Sibling-breaking fix-sequence → stop, zoom out, re-architect. (→ `loss-backprop-lens`.)
4. **Regularizers are enforced every iteration.** Contracts, layer boundaries, invariants, documented mental model. A fix that lowers training loss by violating a regularizer raises generalization loss — reject even when the test is green. (→ `docs-as-definition-of-done`, `drift-detection`.)
5. **K_MAX is real.** When you hit it, you escalate with a layer-4/5 diagnosis and a step-size recommendation. You do **not** silently try iteration 6. (→ `loop-driven-engineering`.)

If any one of these fails, convergence is not guaranteed. In practice, failures correlate: a team that drops condition 4 tends to also drop 1 (rubric drift to mask the regression).

## 3. Divergence patterns (field guide)

Five distinct failure modes. Each has an early-warning signal and a specific skill that catches it.

### 3.1 Oscillation

**Symptom.** Fix A breaks B. Fix B breaks A. Fix C breaks A and B. Commit log in one area shows the same files cycling green-red-green-red.

**Root cause.** Two or more tests encode incompatible expectations. The implementation satisfies whichever was last patched.

**Early signal.** Same file rejected by different gates across consecutive iterations.

**Catches.** `loss-backprop-lens` Rule 3 (learning rate escalation on local-minimum trap) + `dialectical-reasoning` (thesis: fix A; antithesis: what breaks in B?).

### 3.2 Drift (cumulative)

**Symptom.** 20 individually-reasonable commits. The aggregate is a system whose mental model no longer matches the code — renamed concepts, slowly-separating contracts, docs that are each individually almost-current but collectively describe a fiction.

**Root cause.** Each commit locally optimal against its own loss, none checked against a system-coherence rubric.

**Early signal.** `grep` for a renamed concept finds both names in the repo. Or: README architecture diagram and actual module graph disagree in ≥2 places.

**Catches.** `docs-as-definition-of-done` (per commit) + `drift-detection` (periodic full-repo scan).

### 3.3 Noisy SGD

**Symptom.** Every LLM response or flaky test is treated as a gradient. Agent edits code based on a single run that may not reproduce.

**Root cause.** Confusing loss with noise. An LLM call is one sample of a distribution; one failing CI run is one sample of an intermittent fault.

**Early signal.** "It passed once, let's ship." "It failed once, let me patch it." "The LLM was bad, retry."

**Catches.** `reproducibility-first` (no gradient without reproduction) + `loss-backprop-lens` Rule 1.

### 3.4 Moving-target loss

**Symptom.** The test was `assert x == 5`. Now `assert x == 7`. Nobody logged why. In three more weeks the rubric is unrecognizable, and nobody can say which commits were regressions and which were improvements.

**Root cause.** Rubric edits to justify the current code, instead of code edits to satisfy a stable rubric.

**Early signal.** Test edits and implementation edits in the same commit, with the commit message describing only the implementation.

**Catches.** `method-evolution` (rubric is a first-class outer-loop artifact, versioned, edited with justification and Δloss measurement) + `dialectical-reasoning` (what's the load-bearing assumption? → "the rubric was right before").

### 3.5 Local-minimum trap

**Symptom.** 5 consecutive 3-line patches to the same function, each making one new test pass. The 6th test breaks the whole pattern. The next 10 hours will be a sixth, seventh, eighth 3-line patch.

**Root cause.** Step size too small for the actual loss pattern. The function has the wrong shape; no local move brings it to low global loss.

**Early signal.** Commit log in one function: 3+ `fix: ...` messages in 90 minutes.

**Catches.** `loss-backprop-lens` Rule 3 (step size must match loss pattern) + `iterative-refinement` (if the pattern is in a deliverable, switch to y-axis refinement rather than θ-axis editing).

## 4. Code drift — the specific case

Drift is divergence on a timescale longer than one work session. It is the enemy of long-running projects with many contributors (including many AI-agent sessions).

**Drift is not a single bug.** It is the cumulative effect of many individually-reasonable decisions that together pull the system away from a coherent design. Per-commit gates cannot catch it because no single commit violates a rule.

**Drift indicators** (the things `drift-detection` scans for):

1. **Identifier drift** — same concept named two ways in different modules (`user_id` vs `userId` vs `uid`). Grep for synonyms.
2. **Contract drift** — same interface with three subtly-different shapes. Compare function signatures across call sites.
3. **Layer drift** — files that used to live in one layer now import from two. Module-import graph growing cycles or cross-layer edges.
4. **Doc-model drift** — README architecture section and actual module graph disagree. Re-generate the dependency graph; diff against the documented one.
5. **Rubric drift** — the evaluation rubric itself has been edited without a logged `Δloss`. `git log evaluation.md` should show each change with a justification.
6. **Test/spec drift** — tests describe behavior, specs describe promises, they diverge. Specifications assert things tests never check.
7. **Defaults drift** — default values mentioned in README, in code, in tests, in migrations all have slightly different values.

**Preventing drift requires two things, not one:**

- **Per-commit regularization** (`docs-as-definition-of-done`): no drift *introduced* in this commit.
- **Periodic coherence scan** (`drift-detection`): detect drift that accumulated silently.

Both are needed. Per-commit gates miss slow-pattern accumulation; periodic scans miss fast-regression edits. The pair, together, bounds drift.

## 5. Convergence as a testable property

How do you **measure** whether your work is converging or diverging? The bundle's test pyramid, read as a loss trace:

| Tier | Loss measurement frequency | Good-faith interpretation |
|---|---|---|
| 0 (local thought) | Per edit | Are you about to descend, or randomly walk? |
| 1 (lint/type/schema) | Per edit | Training loss ≥ 0 (syntactic correctness) |
| 2 (unit tests) | Per iteration | Training loss on specified behavior |
| 3 (integration) | Per release-candidate | Generalization loss at the boundary level |
| 4 (E2E live) | Per merge / release | Test loss on unseen composition |
| 5 (production, long-horizon) | Per week / month | Drift detection signal |

A converging project shows **monotonic-or-flat** loss at each tier over time — with occasional spikes when a new rubric is adopted (an outer-loop step) that are explained in the log.

A diverging project shows **rising test loss despite falling training loss** — the classic overfitting signature. LDD's job is to make this visible early and give the operator the tools (refinement, method-evolution, drift-detection) to correct course without starting over.

### Loss display — normalized [0, 1], primary; raw `(N/max)` secondary (v0.3.2)

Every measurable loss in LDD is displayed in one of three forms, named on the trace-block `Loss-type` line:

- **`normalized-rubric`**: `loss = violations / rubric_max`, shown as a float in [0, 1] with the raw count in parens. Example: `loss_0 = 0.375  (3/8 violations)`. This is the default for the binary rubrics used by most skills.
- **`rate`**: the underlying signal is already a rate in [0, 1] (flake rate, pass fraction, coverage). Shown as a float; no re-normalization.
- **`absolute-<unit>`**: continuous unbounded signal (latency, throughput, queue depth). Shown with its unit, no normalization — normalizing an unbounded signal invents a denominator and produces fake precision.

Normalizing per-skill violations to [0, 1] makes Δloss **comparable across skills** (drift-detection's 6-item rubric and architect-mode's 10-item rubric become apples-to-apples). The raw `(N/max)` in parens keeps it **actionable** — the user still sees exactly which items are still open. Never display a normalized float without the raw denominator in parens; the combined display is the honest form.

Full per-type spec in [`../../skills/using-ldd/SKILL.md`](../../skills/using-ldd/SKILL.md) § "Loss-types — how to display the loss number".

## 6. Practical reading order for a new contributor

1. `README.md` — what LDD is for.
2. This document — why it's shaped the way it is.
3. `diagrams/three-loops.svg` — the mental picture.
4. `skills/loop-driven-engineering/SKILL.md` — the inner loop, the entry point.
5. `skills/root-cause-by-layer/SKILL.md` + `skills/loss-backprop-lens/SKILL.md` — the gradient mechanics.
6. The remaining skills as the work requires them.
7. `evaluation.md` + `tests/` — when you're ready to measure.

## 7. Architect mode — a fourth invocation path with per-task loss-function selection

The three loops above all minimize `L = rubric_violations` (with layer-specific rubric items). [`architect-mode`](../../skills/architect-mode/SKILL.md) adds a fourth invocation path where the loss function itself is **task-configurable** via the `creativity` sub-parameter:

```
creativity=conservative  →  L = rubric_violations + λ · novelty_penalty
creativity=standard      →  L = rubric_violations                                   (default)
creativity=inventive     →  L = rubric_violations_reduced + λ · prior_art_overlap_penalty
```

This is not a fourth loop — architect mode still closes by producing a failing scaffold that hands off to the inner loop. What changes is **which objective the optimizer minimizes over the design space**, for that single task.

Key constraints that keep this from being a moving-target-loss escape hatch:

- **Discrete, named levels only.** No continuous `creativity=0.7`. Picking a level is a design decision committed to before the run starts, not a tuning knob.
- **No level-switching mid-task.** Mixing two loss functions in one gradient descent is incoherent optimization; the skill refuses and requires a restart.
- **`inventive` requires per-task user acknowledgment.** Cannot be project-level default. Prevents silent drift into novelty-prioritized work without conscious opt-in.
- **Default stays `standard`.** The other two levels are opt-in; absence of an explicit creativity signal means architect-mode uses the same loss function as the rest of LDD.

The ML-lens framing holds: every work session is still gradient descent on code. Architect-mode with creativity levels just exposes the **choice of `L`** as a first-class parameter for one specific case (design from requirements), with the choice being one of three discrete, named alternatives — not a free parameter.

## 8. What this document does not do

It does not prove convergence. It specifies the conditions under which convergence is expected and names the divergence patterns a practitioner will actually see. The proof would require formalizing each skill's rubric, running a large task suite, and measuring `Δloss_bundle` trajectories under each creativity level — the outer-loop work of a future paper, not this v0.3.
