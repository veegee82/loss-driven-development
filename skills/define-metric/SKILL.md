---
name: define-metric
description: Use when the agent or the user wants to introduce a new measurable quantity as a first-class loss component — e.g., tracking cyclomatic complexity alongside test_pass_rate, or adding a domain-specific rubric to a reasoning chain. Forbids ad-hoc arithmetic on observations and forbids using a new metric as a load-bearing decision gate until calibration has passed. Extends LDD's loss framework to agent-defined objectives without touching LDD core.
---

# Define-Metric — cross-cutting, extends [Gradient Descent for Agents](../../docs/theory.md) to agent-defined objectives

## The Metaphor

**The apprentice at the instrument workshop.** A new scale, balance, or caliper can be introduced at any time — but before it measures anything load-bearing, it must be **calibrated** against an already-trusted instrument. A newly-ground calibration weight isn't trusted until it has been compared N times against certified weights and shown consistent agreement. So for agent-authored metrics: any new instrument starts as **advisory-only**; only after the calibration gate (`n ≥ 5`, `MAE ≤ 0.15`) passes may it be promoted to **load-bearing** and used as a decision gate.

An uncalibrated instrument looks exactly like a calibrated one — until you use it to make a real decision. That's the failure mode this skill prevents.

## Overview

**This skill extends LDD's loss framework to new parameter spaces without touching LDD core.** The [four standard gradients](../../docs/ldd/convergence.md) — code / output / method / thought — each come with their own default loss (failing tests, rubric violations, `mean_loss` across a suite, per-step verification). This skill lets an agent add new first-class loss components (complexity, latency, vuln count, accessibility score) via the Metric Algebra, calibrate them over N observations, and only then let them decide anything load-bearing. The same bias-invariance and calibration discipline that keeps the four standard gradients honest applies to agent-authored ones.

v0.9.0 introduces **Metric Algebra** — five primitives (`Metric`, `Loss`, `Signal`, `Estimator`, `Calibrator`) that generalize every specific loss mechanism from v0.5.1 through v0.8.0. With this skill, an agent can:

1. **Introduce a new Metric** at any point in a session (e.g., "I also want to track `docstring_coverage`")
2. **Compose metrics** into new ones via algebraic operators (weighted sum, max, min)
3. **Calibrate** the new metric against observations over N iterations
4. **Promote** it to load-bearing only after the calibration gate passes

All without modifying LDD core. Metric specs are serialized to `.ldd/metrics.json`; calibration pairs to `.ldd/metric_calibrations.jsonl`.

## When to Use

- Agent needs a domain-specific signal (complexity, accessibility score, latency, vuln count) beyond what's in the default rubric
- User wants to mix multiple objectives (test_pass + lint + latency) into a single trackable loss
- Task requires a custom loss for a particular class of refactor, where the default `L = failing_tests/total` doesn't capture the nuance
- Agent is in a reasoning task and wants to define a success criterion based on domain rules (e.g., "for math proofs, penalize non-rigorous steps")

## When NOT to Use

- Trivial one-off tasks where the default loss suffices — don't introduce metric churn
- Measurements that can't be made deterministically (e.g., "readability", "elegance") — these fail the gaming-guard
- Cross-project metrics — LDD is per-project by bias-invariance; global metrics risk signal-mixing
- Metrics whose description rewards the agent's current approach — gaming-guard will reject

## Scalar vs. Vector — which loss shape to pick (v0.13.x Fix 1)

Before defining a metric, decide whether the task genuinely needs a **scalar** (`normalized-rubric` / `rate` / `absolute`) or a **vector** (`loss_vec`) shape. The wrong shape hides the wrong thing.

| Shape | Pick when | Avoid when | Example |
|---|---|---|---|
| **Scalar `normalized-rubric`** | Binary rubric items that can all be counted the same way; no inter-item trade-off | The items have different cost classes you need to see separately | `drift-detection` rubric — 6 binary checks of the same kind |
| **Scalar `rate`** | Single bounded ratio, no dimensions | You need to know which sub-population is failing | Flake rate on a single test suite |
| **Scalar `absolute`** | Unbounded single-axis measurement with a meaningful unit | The unit is actually two-dim (latency+memory, throughput+error-rate) | p99 latency in ms |
| **Vector `loss_vec`** | Multi-objective where you need to see trade-offs explicitly; the scalar aggregate would hide Pareto dominance | Single-axis measurements — vector mode costs rendering complexity you don't need | IoT consensus: `latency:0.8,memory:0.4,correctness:0.2` — all three must descend; any pair can trade off |

**The decisive question:** if a candidate change improved dim A by 0.3 and worsened dim B by 0.3, would the user genuinely have to think about which they prefer? If yes → **vector**. If the user would always prefer one dim (or the two are monotone in practice) → scalar, and the scalar is honest.

**Anti-pattern — "just average them":** Weighted-sum aggregation into a scalar is only defensible when the weights are **empirically calibrated** and the aggregate is **monotone in user preference**. A weighted sum that produces `Δloss = 0` for a real trade-off is giving a misleading gradient and must be either (a) calibrated with a real preference elicitation or (b) replaced with a vector.

## The Protocol

### Step 1 — Specify the metric

Every metric has a `MetricSpec`:

```python
MetricSpec(
    name         = "test_pass_rate",       # unique per project
    kind         = "bounded",              # bounded | positive | signed
    unit         = "rate",                 # rate | ms | count | dimensionless
    description  = "fraction of tests passing in the suite",
    version      = 1,                      # bump on semantic change
    advisory_only= True,                   # ALWAYS true at registration
)
```

**Gaming-guard (non-negotiable)**: the `description` MUST describe WHAT is measured, NOT reward the agent's current approach. Self-referential phrases (`"my current action"`, `"the action just taken"`, `"i want"`, `"i prefer"`) are rejected at construction time with a `gaming-guard` error.

### Step 2 — Provide the measurement function (accessor)

Three concrete metric types map to a bounded, positive, or signed observation:

| Kind | Use when | Example |
|---|---|---|
| `bounded` | Observation ∈ [0, 1] by construction | `failing / total` rate |
| `positive` | Observation ≥ 0 (may saturate at `normalize_scale`) | latency_ms, vuln_count |
| `signed`   | Observation ∈ ℝ (sigmoid-normalized) | Δloss between iterations |

```python
from ldd_trace.metric import bounded_rate, positive_count, signed_delta

test_pass = bounded_rate(
    "test_pass_rate",
    accessor=lambda θ: (θ["tests_failing"], θ["tests_total"]),
    description="fraction of failing tests in the suite",
)
```

The `accessor` must be **deterministic** and **read-only** w.r.t. θ.

### Step 3 — Register

```python
from ldd_trace.metric_registry import MetricRegistry
from ldd_trace import TraceStore

store = TraceStore(".")
reg = MetricRegistry(store)
reg.register(test_pass)
```

Registration:
- Adds spec to `.ldd/metrics.json`
- Sets `is_load_bearing = False` (advisory-only)
- Fails on name collision (unless version bump)
- For composed metrics: fails if components aren't yet registered

### Step 4 — Compose (optional)

If you want a combined metric:

```python
from ldd_trace.metric_compose import weighted_sum, maximum, minimum

combined = weighted_sum(
    "combined_quality",
    [(test_pass, 4.0), (lint, 1.0), (latency_p99, 1.0)],
    description="4:1:1 weighted sum — tests dominate",
)
reg.register(combined)
```

Algebraic laws (enforced by `test_metric_properties.py`):
- Output always ∈ [0, 1]
- Commutative over components (same weights)
- Homogeneous in weights (scaling all by λ doesn't change output)
- Equal weights → arithmetic mean
- max/min idempotent, commutative

### Step 5 — Calibrate over ≥5 iterations

For each subsequent iteration, log a (predicted, observed) pair:

```python
from ldd_trace.metric_registry import Calibrator

cal = Calibrator(reg)
cal.log("test_pass_rate", predicted=0.3, observed=0.28)
# ... repeat over ≥ 5 iterations ...
```

Or via CLI:

```bash
python -m ldd_trace metric calibrate --name test_pass_rate --predicted 0.3 --observed 0.28
```

### Step 6 — Promote (automatic once gate passes)

```python
cal.try_promote("test_pass_rate")
# returns True once n ≥ 5 AND MAE ≤ 0.15
```

Or: CLI `metric calibrate` auto-promotes when the gate passes.

Once `load_bearing = True`, the metric can be used as:
- A decision gate (commit/reject based on its value)
- A load-bearing component of a composed loss
- An input to `loop-driven-engineering`'s K_MAX discussions (metric-specific budgets)

## The Calibration Gate — why it's load-bearing

**A metric that hasn't been validated against ground truth is a rumor.** The gate parameters:

| Parameter | Default | Justification |
|---|---|---|
| `min_n` | 5 | Below this, MAE is noise |
| `max_mae` | 0.15 | Above this, predictions ≠ observations by more than 15%-points on average — metric doesn't describe reality |

Both tunable via project config (future extension), but conservative defaults apply until tuned.

**Failure mode the gate prevents**: agent registers a metric, uses it as a decision criterion on the first observation, metric was wrong. Calibration gate forbids this: the metric *observes* for N iterations; the agent *cannot* predict using it as authority until the observations validate predictions.

## Bias Invariance (load-bearing principle)

Metric Algebra must satisfy:

$$
\forall \theta, \theta' : L_T(\theta) < L_T(\theta') \implies L_T(\theta) < L_T(\theta')
$$

Concretely:
- **Registration never alters existing observations.** Registering metric B does not change `metric_A.observed(θ)` for any θ.
- **Calibration never alters observed values.** Logging `(predicted=0.3, observed=0.28)` is an audit log; it does not mutate either `predicted` or `observed`.
- **Promotion is a flag, not a transform.** A metric's `observed()` output is the same before and after promotion.
- **No cross-metric signal mixing.** Composed metric's `observed()` depends only on its components' `observed()` outputs at the current θ.

The test class `TestBiasInvariance` in `test_metric_properties.py` enforces this over hundreds of hypothesis-generated scenarios.

## Hard Rules

1. **Every new metric starts `advisory_only = True`**. No exceptions.
2. **No self-referential descriptions** (gaming-guard). Reject at spec construction.
3. **No runtime mutation** of registered specs. Version bump required for changes.
4. **Composition before registration of components fails**. Register leaf metrics first.
5. **Promotion requires `n ≥ 5 AND mae ≤ 0.15`**. Both conditions, both hard.
6. **Calibration is deterministic on raw observations.** The agent never curates the log.
7. **No cross-project metrics.** One project's registry is isolated.

## Red Flags — STOP, the discipline is degrading

- "This metric is obviously right, let me use it as a gate right away" → NO. Advisory-only until calibrated.
- "MAE is 0.2, but the metric is intuitive — promote it" → NO. The gate exists to catch exactly this.
- "Let me tweak the accessor slightly and keep the same name" → NO. Version bump (`version=2`) required.
- "I'll skip calibration and define a composed metric" → composed metrics inherit advisory-only state; they only become load-bearing when ALL components are load-bearing AND the composite itself passes calibration.
- "This metric has `prob_correct_for_current_action`" in its description" → gaming-guard rejects. The metric measures a WORLD property, not a reward for the agent.
- "I'll use this metric to evaluate the last decision retrospectively and change the commit" → no. Metrics inform FUTURE search; they do not modify PAST loss measurements.

## Relation to Other LDD Concepts

| Prior LDD feature | Now expressible as |
|---|---|
| v0.5.1 test pass rate loss | `BoundedRateMetric` |
| v0.5.2 skill effectiveness | `MeanHistoryEstimator` |
| v0.7.0 quantitative dialectic synthesis | `BayesianSynthesisEstimator` |
| v0.8.0 chain_correct (product of step predicteds) | `weighted_sum` or custom estimator |
| v0.7.0 MAE drift detection | `Calibrator.mae + can_promote` |
| Latency, vuln count, complexity | `PositiveCountMetric` |
| Δloss between iterations | `Signal` over any Loss |

v0.9.0 is **backward-compatible** — every prior LDD loss is now an instance of this general framework. The test `test_metric_e2e.py::TestE2E_BayesianSynthesisEstimatorReplicates_v0_7_0` explicitly verifies this generalization claim.

## Tooling

```bash
# List all metrics with their kind + load_bearing state
python -m ldd_trace metric list --project .

# Show calibration status per metric (n_samples, mae)
python -m ldd_trace metric status --project .

# Log one (predicted, observed) pair; auto-promotes if gate passes
python -m ldd_trace metric calibrate --name X --predicted 0.3 --observed 0.28
```

## What This Enables

1. **Domain portability** — LDD is no longer code-specific. Any domain with measurable quantities can use the full framework (inner/refine/outer/thought loops) with domain-specific metrics.
2. **Agent autonomy** — an LLM in a reasoning session can propose a new metric ("for THIS math problem I'm going to also track `proof_rigor`") and LDD applies the calibration discipline automatically.
3. **External tool integration** — any external scanner (SAST, perf profiler, accessibility checker) becomes a `PositiveCountMetric` with one accessor.
4. **Evidence-based multi-objective** — trade-offs are formal (`weighted_sum`), not ad-hoc reasoning. "This change: +0.05 on latency normalized, -0.20 on tests — net −0.15, commit."
5. **Calibration accountability** — every agent-authored metric carries its MAE history. Bad metrics self-identify by failing the gate.

See `docs/theory.md` §4 for the formal specification, `scripts/ldd_trace/test_metric_e2e.py` for 11 end-to-end scenarios, and `scripts/ldd_trace/test_metric_properties.py` for 23 hypothesis-proven algebraic laws.
