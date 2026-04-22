# Theory of Loss-Driven Development — **Gradient Descent for Agents**

**A discipline for AI-era software engineering, framed as stochastic gradient descent across four parameter spaces.**

---

## Abstract

**Loss-Driven Development is gradient descent for coding agents.** Coding agents are stochastic, and the code they produce is an optimization target. LDD installs the four missing pieces of a working optimizer: a **loss function** (rubric violations + test outcomes + critique defects + eval deltas), a **gradient estimate** (structured diagnosis from symptom to structural origin), a **step-size rule** (edit aggressiveness matched to the loss pattern), and a **regularizer** (contracts, layer boundaries, docs). Every engineering task becomes an optimization problem; every code change becomes an SGD step that is either signal or noise.

LDD separates **four nested optimization loops**, each acting on a different parameter space:

- **Inner loop** — optimizes `θ = code` against failing tests (`∂L/∂code`).
- **Refinement loop** — optimizes `y = deliverable` against rubric + critique (`∂L/∂output`).
- **Outer loop** — optimizes `m = skills / prompts / rubrics` against N-task loss (`∂L/∂method`).
- **CoT loop** — optimizes `t = reasoning chain` against per-step verification (`∂L/∂thought`).

A fifth mechanism, the **thinking-levels auto-dispatch**, decides HOW MUCH rigor to apply *before* any loop starts — it is the step-size controller of the gradient descent, not a fifth loop. The discipline is self-calibrating via the **quantitative dialectic**: synthesis produces an expected-loss number that is validated post-hoc, closing the loop between the agent's internal priors and the observed world.

LDD is a **skill** — a reasoning protocol, not a framework. The discipline lives in the skill text. The accompanying Python tool (`ldd_trace`) exists only to make compliance ergonomic.

---

## 1. The Metaphor — The Climber Without a Summit View

Imagine a climber on a cloud-shrouded mountain. The summit (`L = 0`) is somewhere above; every step changes altitude by some amount (Δ loss). The climber cannot see the summit, only:

- **Altimeter** — tells them their current height (the loss `L(θ)` at the current state)
- **Sense of slope** — local gradient: where does the ground fall away most steeply?
- **Log book** — every past step: "I went north and lost 200m; then east and gained 50m"
- **A fellow climber's hostile questions** — "are you sure that direction? the fog is thickest there"

A reckless climber walks by altitude alone, committing to every downward step. A disciplined climber does four things:
1. **Reads the altimeter before every step** (inner loop: measure `L` per iteration)
2. **Reasons about the terrain**, not just the gradient (dialectical: probe orthogonal directions)
3. **Consults the log book** for patterns (memory: historical step outcomes)
4. **Calibrates**: "I predicted −50m for this kind of step; I got −30m. My compass drifts right."

LDD encodes these four behaviors. Every other specialist skill (`root-cause-by-layer`, `reproducibility-first`, `method-evolution`, …) is a sub-protocol for one of them.

---

## 2. High-Level Structure — Four Gradients, Four Loops

LDD is organized as **four nested optimization loops**, each operating on a distinct parameter space, each with its own loss function, gradient source, and budget. The word "gradient" is meant literally: each loop produces a directional signal that reduces loss against its rubric.

| Loop | Parameter | Gradient (`∂L/∂·`) | Loss source | Budget | Home skill(s) |
|---|---|---|---|---|---|
| **Inner** | `θ` = code | `∂L/∂code` | Rubric / failing test / E2E | K_MAX = 5 iterations | [`reproducibility-first`](./reproducibility-first.md), [`root-cause-by-layer`](./root-cause-by-layer.md), [`loss-backprop-lens`](./loss-backprop-lens.md), [`e2e-driven-iteration`](./e2e-driven-iteration.md), [`loop-driven-engineering`](./loop-driven-engineering.md) |
| **Refinement** | `y` = deliverable output | `∂L/∂output` | Critique defects + gate rejections + eval deltas | Halved per iteration, stops on plateau | [`iterative-refinement`](./iterative-refinement.md) |
| **Outer** | `m` = skill / prompt / rubric | `∂L/∂method` | `mean_loss` across an N-task suite | N epochs; rollback on regression | [`method-evolution`](./method-evolution.md), [`drift-detection`](./drift-detection.md) |
| **CoT** | `t` = reasoning chain | `∂L/∂thought` | Per-step dialectic + ground-truth verification | Per-chain `max_steps`; backtracks ≤ 3 | [`dialectical-cot`](./dialectical-cot.md) |

**Step-size controller** — an independent mechanism decides **how much of the apparatus to spin up** before any loop begins. The [`thinking-levels`](./thinking-levels.md) auto-dispatch scores the task on 9 signals and picks a rigor level L0…L4; L0 runs a minimal reflex loop, L4 activates `method-evolution`, `dialectical-cot`, and `define-metric` on top of everything else. The thinking-levels mechanism is not a fifth loop — it is the **learning-rate scheduler for the gradient descent**, deciding depth-of-deliberation ahead of the first forward pass.

Orthogonal to all four loops, LDD provides **navigational instruments** that refine the gradient estimate without biasing the loss function:

| Instrument | SGD analog | Role |
|---|---|---|
| `ldd_trace` / project memory | First moment (momentum-like prior) | Accumulates empirical Δloss per skill |
| `dialectical-reasoning` | Second moment (local Hessian probe) | Tests orthogonal directions; produces expected-Δloss |
| `loss-backprop-lens` | Adaptive learning rate | Matches edit-size to loss structure |
| `reproducibility-first` | Noise-suppression | Rejects single-sample gradient estimates |
| `docs-as-definition-of-done` | Regularizer | Penalizes under-documented (future-loss-inducing) edits |

**Bias invariant** (load-bearing): none of these instruments may modify the loss function `L(θ)`. They inform the search for the gradient; they do not redefine progress.

See (diagram omitted in web bundle) for the loop-nesting diagram showing all four loops — inner / refinement / outer on the code-axis trunk plus CoT as the thought-axis branch — (diagram omitted in web bundle) for the CoT-loop's per-step protocol, and (diagram omitted in web bundle) for the full four-axis parameter-space picture.

---

## 3. Formalization

### 3.1 Code as Parameter Space

Let `θ ∈ Θ` denote the complete state of the code at a given moment: every file's bytes, every test's contents, every config value. The space `Θ` is discrete and enormous, but local neighborhoods (small diffs from `θ`) are well-defined.

### 3.2 The Loss Function

For a given engineering task `T`, the loss function is:

$$
L_T(\theta) = \frac{|\{r \in R_T : r \text{ violated at } \theta\}|}{|R_T|}
$$

where `R_T` is the rubric: the set of pass/fail checks defining success for `T`. This is **rate-typed** loss (`L ∈ [0,1]`). For absolute-typed losses (latency, throughput), the same frame applies with a task-specific denominator; normalization is deferred to the display layer, not the optimization.

**Key property**: `L_T` is externally specified — by tests, by docs, by explicit R-rules. It is not a function of the agent's beliefs. This is why "memory cannot bias the loss" is a meaningful rule: even if memory tells the agent that skill X is best, L only registers what X *actually achieved*.

### 3.3 Gradient Descent Step

Given the current state `θ_k` with `L_T(θ_k) > 0`, the next iteration produces:

$$
\theta_{k+1} = \theta_k + \Delta\theta_k
$$

where `Δθ_k` is the edit made during iteration `k`. The observable gradient signal is:

$$
\Delta L_k = L_T(\theta_{k+1}) - L_T(\theta_k)
$$

Progress: `Δ L_k < 0`. Plateau: `|ΔL_k| < ε` (typically `ε = 0.005`). Regression: `ΔL_k > 0`.

### 3.4 Inner Loop — K_MAX-Bounded SGD

The inner loop runs:

```
for k = 0 ... K_MAX:
    L_k = measure(θ_k)                        // E2E / rubric / tests
    if L_k == 0: break                        // converged
    diagnose(θ_k, L_k)                         // root-cause-by-layer
    Δθ_k = edit(diagnosis)                     // smallest coherent change
    θ_{k+1} = apply(θ_k, Δθ_k)
    emit_trace(k, skill, Δθ, L_k, ΔL_k)        // discipline, not optional
if k == K_MAX and L_k > 0: escalate           // budget exhaustion signal
```

The discipline: measure *before* the edit (to know the gradient), emit the trace *after* the edit (so the log encodes the descent), and escalate at `K_MAX` instead of silently continuing. Budget exhaustion is a **signal**, not a failure: it says the current parameterization is inadequate, which hands off to the outer loop.

### 3.5 Refinement Loop — Y-Axis Optimization

When the inner loop has converged (`L = 0`), the artifact is *done* in the rubric sense, but may be "good enough, not great." Refinement loop optimizes **deliverable quality** (`y`), not correctness:

$$
y_{k+1} = \text{refine}(y_k, \text{review-rubric})
$$

with halved budget per step and plateau-detection termination. This is not the inner loop rerun — the loss function itself changes (from `rubric_violations` to `reviewer_notes`).

### 3.6 Outer Loop — θ-Axis Optimization

When the same rubric violation recurs across N ≥ 3 tasks, the parameter space shifts to **the skills/rubrics themselves**. This is `method-evolution`: modify the skill's rules, measure `mean_Δloss_over_tasks` before and after, rollback on regression.

The outer loop closes the self-improvement circuit: the system learns not just individual tasks but how to do tasks.

### 3.7 Memory as First-Moment Estimator

The persistent trace (`.ldd/trace.log`) records, for every iteration:

$$
e_i = (t_i, \text{loop}, k, \text{skill}, \Delta\theta\text{-summary}, L_k, \Delta L_k, \hat L_k)
$$

where `t_i` is timestamp and `L̂_k` is the predicted Δloss from the quantitative dialectic (if applied; see §3.9).

The aggregator maintains a **project memory**:

$$
\mu_s = \frac{1}{n_s} \sum_{e : \text{skill}(e) = s} \Delta L_e
$$

The per-skill mean Δloss `μ_s` is an estimator of "what does this skill typically do in this project." Bias-guards:

- **Survivorship**: `μ_s` is computed over *all* terminal states; per-terminal breakdown is exposed separately.
- **Regression to mean**: both absolute `μ_s^{abs}` and relative `μ_s^{rel} = E[ΔL/L_{prev}]` are reported.
- **Recency drift**: lifetime and last-30-day windows both tracked.
- **Confirmation**: aggregation is deterministic on raw trace; no agent curation.

Memory serves as a **prior**, not a rule. It informs `P(skill_s | current_task)` without altering `L_T`.

### 3.8 Dialectic as Hessian Probe

Dialectical reasoning — the thesis → antithesis → synthesis protocol — is LDD's second-order-information mechanism. The agent proposes a gradient direction (thesis = `Δθ_{thesis}`); the antithesis generates counter-cases (`Δθ_{anti,i}`) that probe orthogonal directions where `L` reacts non-monotonically.

Formally, if the thesis is `Δθ_t` with expected progress `-g_t`, and a primer surfaces a counter-direction `v_i` with historical impact `+h_i`, the **Hessian-projected cost** is:

$$
\mathcal{H}_{i} = v_i^\top \nabla^2 L(\theta) \, \Delta\theta_t \quad \text{(informal)}
$$

In practice, `∇²L` is not computed; the primer encodes it heuristically as a *probability that the counter-case applies times its impact*. The synthesis step aggregates:

$$
\mathbb{E}[\Delta L \mid \text{thesis}] = \sum_i \Pr(v_i \text{ applies}) \cdot h_i + \Big(1 - \sum_i \Pr(v_i)\Big) \cdot \hat L_{thesis}
$$

This is the **Bayesian-expectation** formulation of the synthesis — not a black-box reasoning output, but a number the agent computes and can be checked against observation.

### 3.9 The Quantitative Dialectic

The full protocol:

1. **Thesis** with `predicted_Δloss` from `μ_{skill}` and `confidence = clamp(log(1+n)/log(11), 0, 1)`
2. **Primers** (from `prime-antithesis`): each maps to `{Pr(applies), impact}`
3. **Synthesis** computes `E[ΔL | thesis]` per §3.8
4. **Decision**:
   - commit if `E[ΔL | thesis] < 0` ∧ no alternative dominates by > 0.1
   - reject if `E[ΔL | thesis] ≥ 0` ∨ alternative dominates by > 0.1
   - escalate if within-ambiguity band
5. **Calibration** (§3.10) logs `predicted_Δloss` alongside `actual_Δloss`

This is where the "gradient-via-dialectic" metaphor becomes a computable gradient estimate — computed by the agent's reasoning, not the tool's code, but reduced to a number that can be right or wrong.

### 3.10 Calibration Feedback Loop

Given a series of (predicted, actual) pairs `{(L̂_i, L_i)}_{i=1..N}`:

$$
\text{err}_i = \hat L_i - \Delta L_i \qquad \text{MAE} = \frac{1}{N}\sum_i |\text{err}_i|
$$

The aggregator emits `drift_warning: true` when `MAE > 0.15 ∧ N ≥ 5`. This is the explicit signal that the agent's in-head priors are miscalibrated; the response is `method-evolution` (outer loop), not silent loss modification.

Per-skill MAE is also tracked — a skill with good overall calibration but bad MAE on one skill-choice signals that the specific skill's behavior has drifted (e.g., the skill definition was updated).

### 3.11a Thought-Loop — Dialectical CoT (fourth optimizer layer)

The first three loops (inner/refine/outer) treat θ as code, deliverable, or skill respectively. The **fourth loop — the thought-loop** — treats θ as a **reasoning trajectory** (chain of thoughts) and applies the quantitative-dialectic protocol to each step.

For a chain `[θ_0, θ_1, ..., θ_N]` where each `θ_k` is the partial reasoning state after step `k`:

$$
\theta_{k+1} = \theta_k \oplus \text{step}_k
$$

where `⊕` denotes chain-extension. Standard CoT is greedy: `step_k = \arg\max P(\cdot | \theta_k)` under the language model's distribution. Dialectical-CoT introduces a per-step gate:

$$
\mathbb{E}[\text{correct} | \text{thesis}_k] = (1 - \sum_i \Pr(\alpha_i)) \cdot \pi_k + \sum_i \Pr(\alpha_i) \cdot \text{clip}(\pi_k + \Delta_i, 0, 1)
$$

where `π_k` is the LLM's self-rated prior for the proposed step, `α_i` are antitheses (primers + independent), and `Δ_i` is the impact if `α_i` applies.

**Decision rule**:

- `E ≥ 0.7` → commit step, append to chain
- `0.4 ≤ E < 0.7` → revise (synthesis rewrites the step addressing antitheses)
- `E < 0.4` → reject; backtrack to an earlier chain state (budget-capped at `K_MAX_BACKTRACKS = 3`)

**Chain-level prediction**: predicted correctness of the full chain is the product of per-step predicteds:

$$
\hat P_{\text{chain correct}} = \prod_{k=1}^{N} \mathbb{E}[\text{correct} | \text{thesis}_k]
$$

**Calibration loop** (extends §3.10 to chain level): for each (predicted, actual) pair over all chains in a task-type, track MAE; emit `drift_warning` when `MAE > 0.15 ∧ n ≥ 5`. Per-task-type partitioning prevents signal-mixing.

**Memory layer** (`.ldd/cot_memory.json`): per-task-type step effectiveness, common failure modes, calibration MAE, step-decision distribution. Feeds primers back into the antithesis generation on subsequent chains via `cot_primers_for_task_type(task_type)`.

**Cost model**: a chain of length `N` with `b` backtracks costs roughly `3N + b·(|Δ_backtrack|)` LLM calls versus `N` for greedy CoT. Break-even over greedy-CoT-with-retry occurs when greedy success rate on the task-class is below ~70%.

**Related work**: Tree-of-Thoughts (Yao et al. 2023) MCTS-style, Chain-of-Verification (Dhuliawala et al. 2023) post-hoc critique, Self-Consistency (Wang et al. 2022) multiple samples. LDD's contribution is (a) explicit Hessian-interpretation of the antithesis, (b) the bias-invariance guarantee at the protocol level, and (c) the calibration loop that closes back into method-evolution.

See (diagram omitted in web bundle) for the per-step protocol diagram and `./dialectical-cot.md` for the full skill specification.

### 3.11b Metric Algebra (v0.9.0, extensible foundation)

v0.5.1–v0.8.0 introduced specific loss instances (rubric violations, Δloss, chain correctness). v0.9.0 generalizes all of them into an algebra of five primitives that agents can extend without touching LDD core.

**Primitives**:

| Primitive | Signature | Role |
|---|---|---|
| `Metric`     | `Observation → ℝ` | Any measurable quantity; three concrete kinds: `bounded` (rate ∈ [0,1]), `positive` (count, latency ≥ 0), `signed` (Δ ∈ ℝ) |
| `Loss`       | `θ → ℝ` | A Metric bound to the parameter space θ; `L(θ) := metric.observed(θ)` |
| `Signal`     | `(θ_before, θ_after) → ℝ` | `S(a, θ) = L(θ ⊕ a) − L(θ)`; the observable Δ |
| `Estimator`  | `(Action, Context) → (predicted_Signal, confidence)` | Predicts Signal before the action |
| `Calibrator` | `stream[(predicted, observed)] → drift_signal` | Tracks MAE; promotes `advisory_only → load_bearing` on gate pass |

**Composition algebra** — three operators produce new metrics from existing ones, with algebraic laws enforced by property tests:

$$
\begin{aligned}
L_{\text{weighted-sum}} &= \frac{\sum_i w_i \cdot \text{normalize}(L_i)}{\sum_i w_i} \\
L_{\text{max}}          &= \max_i \text{normalize}(L_i)     \quad \text{(any-fail)} \\
L_{\text{min}}          &= \min_i \text{normalize}(L_i)     \quad \text{(all-pass)}
\end{aligned}
$$

**Algebraic laws** (verified by hypothesis in `test_metric_properties.py`):

1. **Bounds**: `normalize(·) ∈ [0, 1]` for any input (test coverage: ~10⁴ random values per metric type)
2. **Weighted-sum homogeneity**: scaling all weights by λ > 0 does not change output
3. **Weighted-sum commutativity**: component order doesn't matter when weights paired correctly
4. **Max/min idempotency**: `max(L, L) ≡ L` and `min(L, L) ≡ L`
5. **Max/min commutativity**: `max(L₁, L₂) ≡ max(L₂, L₁)`
6. **Bias-invariance**: `metric.observed(θ)` is invariant under registry/calibrator activity

**Calibration gate** — a new metric is `advisory_only = True` at registration. It becomes `load_bearing = True` iff both:

$$
n \geq n_{\min} = 5 \quad \wedge \quad \text{MAE} = \frac{1}{n}\sum_i |\hat L_i - L_i| \leq \epsilon_{\max} = 0.15
$$

This generalizes v0.7.0's drift detection to arbitrary agent-defined metrics.

**Gaming-guard** — metric specifications with self-referential descriptions (phrases like "my current action", "rewards my approach") are rejected at construction time. Property test `TestGamingGuard` enforces coverage over all guard phrases.

**Backward compatibility** — every prior LDD loss is expressible:

| Prior | Expressed as |
|---|---|
| v0.5.1 test-pass-rate | `BoundedRateMetric(accessor=failing/total)` |
| v0.5.2 skill Δloss_mean | `MeanHistoryEstimator` |
| v0.7.0 quantitative dialectic | `BayesianSynthesisEstimator` |
| v0.7.0 MAE drift | `Calibrator.can_promote` |
| v0.8.0 chain-level predicted | `weighted_sum` of per-step predicteds |

The test `TestE2E_BayesianSynthesisEstimatorReplicates_v0_7_0` in `test_metric_e2e.py` explicitly verifies that v0.7.0's worked example (prior=0.8, primer prob=0.5, impact=-0.4 → E=0.6) reproduces exactly under the generic estimator.

**Why this matters**:

1. **Domain portability** — LDD becomes applicable to any domain where metrics can be defined (infra cost, ML val_loss, security scanner output, custom agent rubrics)
2. **Agent autonomy** — an LLM can propose `L_complexity = cyclomatic_complexity × 0.3 + maintainability_index × 0.7` and LDD enforces the same discipline (prediction → observation → calibration → promotion) on the agent-authored metric
3. **External tool plug-in** — any CLI/API that produces a scalar becomes a metric via a one-line accessor
4. **Calibration accountability** — agent-authored metrics self-identify as trustworthy or drifting via the MAE gate

See (diagram omitted in web bundle) for the primitive composition flow and `./define-metric.md` for the agent-facing protocol.

### 3.11 Bias Invariance Principle (Load-Bearing)

All navigational instruments (memory, dialectical, calibration, suggestions) MUST satisfy:

$$
\forall \theta, \theta' : L_T(\theta) < L_T(\theta') \implies L_T(\theta) < L_T(\theta')
$$

(The loss ordering is preserved under any navigational intervention.) In plain terms:

- Memory cannot make a regressive edit look progressive
- Primers cannot invert the sign of `ΔL`
- Rank scores cannot relabel a violation as a non-violation
- Calibration adjustments apply to *predictions*, not to observations

Violations of this principle turn LDD into a moving-target-loss system and collapse the convergence guarantee. The memory module is tested (`TestBiasInvariant`) to enforce this at code level.

---

## 4. The Complete Protocol

A single LDD inner-loop iteration in full:

```
# Before
assert .ldd/trace.log exists                    # recover prior state
state = ldd_trace.status(project)              # know which k we're on

# During
for k = current_k ... K_MAX:
    L_k = run_e2e()                             # reproducibility-first
    if L_k == 0: break
    diag = root_cause_by_layer(L_k, θ_k)        # name layers 4-5
    thesis = propose_edit(diag)                 # from the diagnosis
    primers = prime_antithesis(                 # memory feeds dialectical
        memory, thesis, files=touched
    )
    E_ΔL = dialectical_synthesis(thesis, primers)  # §3.9
    if E_ΔL >= 0 or alternative_dominates:
        reject(thesis)  or  pivot()
        continue
    apply(thesis)                                # commit the edit
    L_{k+1} = run_e2e()
    ldd_trace.append(                            # discipline
        loop=inner, k=k, skill=..., action=...,
        loss_norm=L_{k+1}, raw=...,
        predicted_delta=E_ΔL                     # for calibration
    )
    if L_{k+1} == 0: break

# After
docs_as_definition_of_done()                     # regularizer
ldd_trace.close(                                 # terminal state
    terminal=complete, layer=...,
    docs=synced
)
# auto: aggregate refreshes project_memory.json
```

Each step corresponds to one skill. Skipping a step is a rubric violation.

---

## 5. Relation to Prior Work

| Concept | Prior art | LDD's contribution |
|---|---|---|
| Gradient descent | Stochastic Gradient Descent (SGD) | Apply to code as parameter space; reasoning agent as optimizer |
| Momentum | Nesterov / Adam | Bias-guarded per-project memory; explicit "prior ≠ rule" |
| Hessian probing | Newton methods | Natural-language antitheses as orthogonal-direction probes |
| Dialectical reasoning | Hegel (obviously) | Bound to an observable loss; synthesis produces `E[ΔL]` |
| Bayesian decision theory | Laplace / Jaynes | Per-iteration posterior over skill choice |
| Calibration | Brier scores, conformal prediction | Post-hoc `predicted vs. actual` logging, drift-warning trigger |
| Test-driven development | Beck | Generalized to ANY measurable loss (tests are one instance) |

The distinction: LDD does not replace any of these; it *composes* them into a single protocol applicable to AI-era software engineering, where a reasoning agent is the optimizer.

---

## 6. Open Questions

- **Cross-project memory**: currently forbidden (signal-mixing risk). Could a bias-guarded global aggregate — conditioned on task-type — help or harm? Requires validation beyond a single-project demonstration.
- **Confidence estimation**: the `confidence = log(1+n)/log(11)` heuristic is ad-hoc. A proper posterior (Beta / Gamma on Δloss distribution) would be more principled, at the cost of protocol complexity.
- **Non-stationarity**: skill definitions evolve (the outer loop changes them). Current calibration assumes stationary priors. A proper handling requires change-point detection on the trace.
- **Meta-calibration**: does the protocol itself require a meta-level calibration? When drift_warning fires repeatedly, is the problem in the skills, the rubrics, or the protocol's structure?

---

## 7. Where the Theory Materializes in the Code

| Theory | Implementation |
|---|---|
| `L_T(θ)` — loss function | `run_e2e` results; rubric scoring |
| `ΔL` signal | `ldd_trace append --loss-norm ... --raw ...` |
| Per-skill `μ_s` | `project_memory.json` → `skill_effectiveness.delta_mean_abs` |
| Plateau resolution `μ_resolver` | `project_memory.json` → `plateau_resolution_patterns` |
| `E[ΔL | thesis]` (§3.8–3.9) | Agent reasoning, primed by `ldd_trace prime-antithesis` |
| `predicted_Δloss` log | `ldd_trace append --predicted-delta <float>` |
| `MAE`, `drift_warning` | `project_memory.json` → `calibration` |
| Bias invariance | `scripts/ldd_trace/test_e2e_memory.py::TestBiasInvariant` |

The theory is the specification; the code is an ergonomic shim that makes the specification cheap to honor.

---

*See (diagram omitted in web bundle) (top-level picture), (diagram omitted in web bundle) (loop-nesting view across all four axes), (diagram omitted in web bundle) (CoT per-step protocol), (diagram omitted in web bundle), (diagram omitted in web bundle), and (diagram omitted in web bundle) for visual intuition.*
