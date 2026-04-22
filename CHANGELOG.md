# Changelog

All notable changes to this plugin are documented here. Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/). This project uses [Semantic Versioning](https://semver.org/).

## [0.10.1] — 2026-04-22

### Added — Thinking-levels auto-dispatch

Every non-trivial task is now auto-scored onto a 5-step rigor ladder (L0 reflex → L1 diagnostic → L2 deliberate → L3 structural → L4 method) before any work begins. The scorer is deterministic (no LLM call), zero-config, upward-biased on boundaries, and trivially overridable per-task. Architect-mode is reached through the L3 / L4 presets — the separate "auto-dispatch for architect-mode" threshold is retired (its 6 signals are retained as a subset of the new 9-signal scorer; all prior dispatch behavior is preserved).

**New artifacts:**

- `scripts/level_scorer.py` — 9-signal deterministic scorer + 5-level bucketing + creativity-clamp + override parser + dispatch-header renderer. Pure function, CLI + library API.
- `scripts/test_level_scorer.py` — 55 unit + end-to-end tests covering per-signal detection, bucketing, creativity inference, override precedence, clamp rule, and all 9 fixture scenarios.
- `scripts/demo-thinking-levels-e2e.py` — integration walkthrough over 12 scenarios (5 level + 4 override + 3 stress); verifies scorer output matches documented contract.
- `tests/fixtures/thinking-levels/` — 9 fixture scenarios with verbatim prompts + expected-level contracts + asymmetric-loss-weighted rubric.
- `docs/ldd/thinking-levels.md` — authoritative reference for the 5 levels, 9 signals, override syntax, ack liberalization.
- `docs/superpowers/specs/2026-04-22-ldd-thinking-levels-design.md` — architect-mode 5-phase design spec.

**Integration:**

- `skills/using-ldd/SKILL.md` — § Auto-dispatch completely rewritten from binary "architect on/off" to the 5-level scorer; inline overrides extended with `LDD[level=Lx]:`; relative bumps `LDD+` / `LDD++` / `LDD=max`; natural-language bumps (bilingual, semantic dedup); precedence split into level-selection (5 categories) and other-hyperparameters blocks.
- `skills/using-ldd/SKILL.md` — new § Inventive ack documenting three paths (explicit flag / liberalized natural-language token / implicit ack from ≥2 inventive cues in prompt). The agent never selects inventive unilaterally; moving-target-loss protection preserved.
- `skills/method-evolution/SKILL.md` — new automatic trigger: 3 low-side auto-level regressions in 20 tasks → propose scorer-weight adjustment with rollback-on-regression.
- `skills/architect-mode/SKILL.md` — description updated to reference thinking-levels; auto-dispatch summary points at the 9-signal scorer and notes L3/L4 as the architect-mode path.
- `scripts/ldd_trace/store.py` — `TraceStore.init()` accepts `level_chosen` + `dispatch_source`; `append_close()` accepts `loss_final` + `regression_followed`. These persist the dispatch decision into `.ldd/trace.log` for method-evolution consumption.
- `scripts/drift-scan.py` — new `check_thinking_levels_drift` verifies bucket boundaries in `level_scorer.py` match `thinking-levels.md` and `using-ldd/SKILL.md` tables.
- `docs/ldd/hyperparameters.md` — one row added to §"What is NOT exposed": `level` is derived, never persisted.

**Design principle encoded throughout:**

> "lieber ein klein wenig schlau als zu dumm"

Asymmetric loss — low-side failures (level too low → silent symptom-patch) count ×2 more than high-side failures (level too high → wasted tokens). Encoded in: baseline L2 (not L0), tie-break on boundaries picks higher, natural-language bumps recognized liberally, fixture rubric suite-level weighting.

### Backward compatibility

- All prior architect-mode auto-dispatch behavior (`score ≥ 4 → architect`) is preserved through the L3 bucket (4 ≤ score ≤ 7) with `mode=architect`.
- The pre-existing `tests/fixtures/architect-mode-auto-dispatch/` fixture remains exercised as a regression baseline; its scenarios all still pass under the new scorer.
- No existing user-facing flag (`LDD[mode=...]`, `LDD[k=...]`, `LDD[creativity=...]`) changed semantics.

### Measurements

- Unit tests: 55 passing (scorer, override parsing, bucketing, clamp rule, fixture end-to-end)
- E2E walkthrough: 12/12 scenarios green (5 level + 4 override + 3 stress) — persisted under `tests/fixtures/thinking-levels/runs/`.
- Drift-scan: no new findings on thinking-levels artifacts.

## [0.9.1] — 2026-04-22

### Added — self-consistency release (14/15 audit findings resolved)

v0.9.1 applies LDD's own discipline to LDD's own code. The v0.9.0 audit
(docs/audit/v0-9-0-findings.md) surfaced 15 collapse/unsoundness modes.
v0.9.1 resolves 14 of them across 6 structural patterns. The remaining
finding (H7: recursive coupling / meta-calibration) is v0.10.0 scope
because it requires method-evolution-rollback infrastructure.

### P1 — Trust Boundary Layer (fixes C1, C2, H1, H4, L1)

New module `scripts/ldd_trace/trust_guard.py`:

  - `TrustGuard.guard_prior(prior)` caps at `MAX_PRIOR=0.9` (C2 fix)
  - `TrustGuard.guard_antitheses(antis, allow_empty=False)` validates
    prob ∈ [0,1] and |impact| ≤ 1; rejects empty list by default (H1, C2 fix)
  - `TrustGuard.guard_verify_fn(fn, required=True)` rejects None with
    a clear error pointing to canonicalize-then-compare (H4 fix)
  - `TrustGuard.guard_accessor(accessor, spec_name)` AST-audits for
    goodhart-identifier patterns (`lines_added`, `_by_agent`, etc.) (C1 fix)
  - `MULTILINGUAL_GAMING_PHRASES` extends phrase list to EN + DE + FR + ES (L1 fix)

Integration:
  - `MetricSpec.__post_init__` calls `TrustGuard.check_description_multilingual`
  - `CoTRunner.__init__` accepts `trust_guard` parameter; default is
    `default_trust_guard`. `require_antithesis=True` is the new default;
    old callers opt out via `require_antithesis=False`.
  - `CoTRunner._run_step` caps `thesis_prior` and validates antitheses;
    AntithesisAbsentError soft-lands with a degenerate reject step.

New exceptions:
  - `AntithesisAbsentError`, `ImpactOutOfRangeError`, `PriorTooHighError`,
    `VerifyFnMissingError`, `GoodhartAccessorError`, `TrustGuardError`

### P2 — Single Source of Truth (fixes C3, H5, M1)

- `MetricRegistry.list_names()` now returns `sorted(self._specs.keys())`,
  not `self._metrics.keys()`. API alignment — no more list_names-vs-specs
  disagreement after session reopen.
- `MetricRegistry.get(name)` raises `SpecExistsButCallableMissing` when
  the spec is on disk but the callable wasn't re-registered this session.
  Replaces the silent `None` return of v0.9.0.
- New `MetricRegistry.has_callable(name)` introspection helper.

### P3 — Multi-Statistic Gate + Rolling Window + Tri-State (fixes H2, H3, M2, M3)

`CalibrationRecord` unchanged; `Calibrator` extended:

  - `p95_error(name)` — 95th-percentile absolute error (H2 tail-risk)
  - `worst_error(name)` — max absolute error (H2 catastrophic-miss)
  - `mae_window(name, window=10)` — rolling MAE for demotion detection (M3)
  - `evaluate_state(name)` — returns tri-state+ verdict:
    `INSUFFICIENT_DATA` (n < min_n) — explicit third state (H3 fix)
    `CATASTROPHIC_OUTLIER` (worst > 0.50) — blocks promotion (H2)
    `TAIL_RISK_HIGH` (p95 > 0.30) — blocks promotion (H2)
    `DRIFTING` (mae > 0.15) — blocks promotion; enables demotion
    `LOAD_BEARING` (all gates pass)
  - `try_promote(name)` — now also DEMOTES a previously-promoted metric
    if recent-window MAE drifts above threshold (M3 monotonic-promotion fix)

`PromotionState` extended:
  - `state` field (string) — authoritative tri-state+ replaces
    binary `is_load_bearing`
  - `is_load_bearing` retained as read-only `@property` for v0.9.0 compat
  - `demoted_at`, `last_p95_error`, `last_worst_error` new audit fields

### P5 — Explicit Writer Model (fixes H6)

`Calibrator` constructor takes `writer_mode` ∈ `{"single_writer", "shared"}`:
  - `single_writer` (default): fast path, caller guarantees exclusivity
  - `shared`: wraps each append in `fcntl.flock(LOCK_EX)` so multiple
    processes / threads can safely append

The assumption becomes **contractual** rather than implicit.

### P6 — Type-Safe Composition (fixes M4)

`metric_compose` operators (`weighted_sum`, `maximum`, `minimum`) now check
that all components share the same `kind`:
  - Same kind → composes normally
  - Different kinds → raises `IncompatibleUnitsError` with a message
    explaining the user must either (a) choose same-kind components or
    (b) pass `force_incompatible=True` and attest the scale choice.

### Deferred — H7 recursive coupling (v0.10.0)

The method-evolution ↔ project_memory ↔ prime_antithesis cycle requires
a meta-calibration layer AND a skill-change-rollback mechanism. Both are
architectural v0.10.0 work — not a bugfix.

### Tests — 208 new total

  - `test_trust_guard.py` (24 tests): TrustGuard unit + integration tests
  - `test_v0_9_0_audit.py`: 4 audit tests inverted from "vulnerability" to
    "defense_in_v0_9_1" — evidence that the fixes hold
  - `test_metric.py`, `test_metric_e2e.py`: updated 1 test to use
    `force_incompatible=True` for legitimate cross-kind compositions
  - `test_cot.py`: 2 legacy tests opt out of new `require_antithesis=True`
    default via `require_antithesis=False`

All green: `python -m pytest scripts/ldd_trace/ -q` → 208 passed.

### Backward-compat notes

  - `PromotionState.is_load_bearing` is a read-only property now. Code
    that wrote to it must write to `state` instead. The one internal
    usage was updated; external callers must do the same.
  - `CoTRunner` default behavior changed: empty antithesis list → soft-land
    as `terminal=partial` + degenerate reject step. Legacy mock-LLM tests
    opt out via `require_antithesis=False`.
  - Cross-kind composition now requires `force_incompatible=True`. Legacy
    cross-kind calls will raise `IncompatibleUnitsError`.

### Dogfood — v0.9.1 built with LDD on itself

Audit-driven release: v0.9.0 audit surfaced findings → v0.9.1 closes 14
of them under LDD discipline. Trace persisted in `.ldd/trace.log`. This
is the self-consistency loop — LDD used LDD's tooling (`ldd_trace append`,
quantitative dialectic, method-evolution lens) to fix LDD's own code.

### Philosophical upshot

The v0.9.0 audit showed: LDD had weaknesses where it hadn't applied its
own discipline internally. v0.9.1 closes those gaps. When a framework
that teaches discipline internally violates the same principles, it's
not a bug — it's a credibility crisis. v0.9.1 is the credibility repair.

## [0.9.0] — 2026-04-21

### Added — Metric Algebra (extensible foundation for agent-defined losses)

v0.5.1–v0.8.0 introduced specific loss mechanisms (rubric rate, Δloss, chain correctness). v0.9.0 generalizes all of them into a **five-primitive algebra** that agents can extend without modifying LDD core.

### The five primitives

Defined in `scripts/ldd_trace/metric.py`:

| Primitive | Signature | Role |
|---|---|---|
| `Metric` | `Observation → ℝ` | Any measurable quantity (three kinds: `bounded`, `positive`, `signed`) |
| `Loss` | `θ → ℝ` | Metric bound to parameter space |
| `Signal` | `(θ_before, θ_after) → ℝ` | Observable Δ under an action |
| `Estimator` | `(Action, Context) → Prediction` | Predicts Signal before the action |
| `Calibrator` | `stream[(pred, obs)] → drift_signal` | Tracks MAE, promotes advisory → load-bearing |

Three concrete Metric classes ship: `BoundedRateMetric` (rate), `PositiveCountMetric` (count/latency/complexity), `SignedDeltaMetric` (signed Δ). Two Estimator implementations: `MeanHistoryEstimator` (v0.5.2's skill_effectiveness generalized) and `BayesianSynthesisEstimator` (v0.7.0's quantitative dialectic generalized).

### Composition algebra

Defined in `scripts/ldd_trace/metric_compose.py`:

- `weighted_sum(name, [(m₁, w₁), (m₂, w₂), ...])` → `Σ wᵢ·normalize(Lᵢ) / Σ wᵢ`
- `maximum(name, [m₁, m₂, ...])` → `max_i normalize(L_i)` (any-fail)
- `minimum(name, [m₁, m₂, ...])` → `min_i normalize(L_i)` (all-pass)

All composed metrics output ∈ [0, 1] by construction. Output-range preservation is the load-bearing property for cross-metric composition.

### Registry + Calibration gate

Defined in `scripts/ldd_trace/metric_registry.py`:

- `.ldd/metrics.json` — spec storage + promotion state (advisory vs load-bearing)
- `.ldd/metric_calibrations.jsonl` — append-only log of (metric_name, predicted, observed) pairs
- **Gate**: a metric goes from `advisory_only=True` to `is_load_bearing=True` iff `n_samples ≥ 5 AND MAE ≤ 0.15`. Until the gate passes, the metric cannot be used as a decision authority.

### Gaming-guard

`MetricSpec.__post_init__` rejects any spec whose description contains self-referential phrases (e.g., "my current action", "rewards my approach"). This prevents agents from registering metrics that game the optimizer toward their current behavior. The phrase list is tested by property-based coverage (`TestGamingGuard::test_any_self_ref_phrase_rejected`).

### New skill: `define-metric`

`skills/define-metric/SKILL.md` — the skill-level protocol. Metaphor: the apprentice at the instrument workshop — new instruments start advisory, calibration against trusted instruments promotes them. Six-step protocol: specify → accessor → register → compose (optional) → calibrate ≥5 times → auto-promote.

### CLI surface

```bash
python -m ldd_trace metric list      --project .
python -m ldd_trace metric status    --project .
python -m ldd_trace metric calibrate --project . --name X --predicted 0.3 --observed 0.28
```

### Tests — 82 new, 169 total

Evidence-based testing across three tiers:

- **Unit tests** (`test_metric.py`, 48 tests): spec validation, gaming-guard, each metric type's semantics, Loss/Signal, both Estimators, Registry, Calibrator gate behavior
- **Property-based tests** (`test_metric_properties.py`, 23 tests via hypothesis): algebraic laws — normalize bounds, normalize idempotency for bounded, weighted-sum homogeneity + commutativity, max/min idempotency + commutativity + duality, bias-invariance under registry/calibrator activity, gaming-guard phrase-coverage, distributional agreement with stdlib max/min
- **LDD E2E scenarios** (`test_metric_e2e.py`, 11 tests): realistic end-to-end workflows — agent-introduces-custom-metric, calibration-gate-promotes-after-evidence, poorly-calibrated-metric-stays-advisory, composition-drives-multi-objective-decision, bias-invariance-under-intense-registry-activity, gaming-guard-blocks-self-ref-spec, persistence-across-sessions, MeanHistoryEstimator, BayesianSynthesisEstimator-replicates-v0.7.0, full-workflow-end-to-end

All green: `python -m pytest scripts/ldd_trace/ -q` → 169 passed.

### Backward compatibility

Every prior LDD loss is now expressible in the new abstraction (test explicitly verifies this):

| Prior | Expressed as |
|---|---|
| v0.5.1 test-pass-rate | `BoundedRateMetric` |
| v0.5.2 skill Δloss_mean | `MeanHistoryEstimator` |
| v0.7.0 quantitative dialectic | `BayesianSynthesisEstimator` |
| v0.7.0 MAE drift detection | `Calibrator.can_promote` |
| v0.8.0 chain-level predicted | `weighted_sum` or custom estimator |

### Theoretical framing

`docs/theory.md` §3.11b — formal spec of the Metric Algebra with composition formulas, calibration gate, backward-compat mapping, algebraic laws. Updated §2 still shows four optimizer loops (Metric Algebra is horizontal, not a new loop).

New diagram: `diagrams/metric-algebra.svg` — the five primitives + composition + gate.

### Dogfood — built with LDD on itself

v0.9.0 was built as an LDD task on the loss-driven-development repo itself. `.ldd/trace.log` captures the iteration trace:

```
Trajectory : █▅▃·   1.000 → 0.630 → 0.408 → 0.215 → 0.000  ↓
```

Four inner-loop iterations: scaffold → core + unit tests → property tests → E2E tests → close. Loss reduced from 1.000 to 0.000 (169/169 tests green) under K_MAX=5 budget.

### Philosophical upshot

LDD was a fixed skill set for SGD on code/deliverable/skill/thought. With Metric Algebra, it becomes a **kernel**: agents define new objectives; the framework enforces the same discipline (prediction → observation → calibration → method-evolution) with bias-invariance guarantees. The framework is now **self-extensible** under hard invariants.

## [0.8.0] — 2026-04-21

### Added — Dialectical Chain-of-Thought (thought-loop, the fourth LDD optimizer layer)

v0.7.0 made the synthesis step of dialectical reasoning produce a number (`E[Δloss | thesis]`). v0.8.0 applies that machinery to each step of a multi-step reasoning chain — turning CoT from greedy-SGD-on-thoughts into **quantitative-gradient-SGD-on-thoughts** with per-chain calibration.

### The new skill: `dialectical-cot`

- `skills/dialectical-cot/SKILL.md` — full 5-step-per-step protocol specification with worked math-problem example. Metaphor: the climber who probes every step before committing weight.
- Decision thresholds: `commit ≥ 0.7`, `revise 0.4–0.7`, `reject < 0.4` (calibratable via outer loop).
- Hard rule: ≥ 1 antithesis per step MUST be independent of memory primers (anti-groupthink guard).
- Bias invariance enforced: memory/primers/synthesis NEVER modify ground-truth verification.

### Python harness

- `scripts/ldd_trace/cot.py` — data classes (`Step`, `CoTChain`, `Antithesis`), `CoTRunner`, synthesis math (`compute_predicted_correct`, `decide_from_predicted`), gather_primers bridge to v0.6.0
- `scripts/ldd_trace/cot_llm.py` — abstract `CotLLMClient` protocol; `MockCotLLMClient` (deterministic, for tests); `OpenRouterCotLLMClient` (real LLM via OpenRouter, stdlib-only HTTP, activates on `OPENROUTER_API_KEY` env var)
- `scripts/ldd_trace/cot_memory.py` — `.ldd/cot_traces.jsonl` (append-only per-chain log) + `.ldd/cot_memory.json` (per-task-type aggregate)
- CLI: `python -m ldd_trace cot run --task ... --task-type math --ground-truth ...`, `cot aggregate`, `cot health`

### Memory & calibration

Per-task-type partitioning prevents cross-type signal mixing:
- `step_decision_distribution` per task_type
- `common_failure_modes` harvested from revise/reject-step antitheses
- `calibration.mae` per task_type; `drift_warning: true` when `MAE > 0.15 ∧ n ≥ 5`
- `cot_primers_for_task_type(task_type)` feeds memory-sourced primers back into subsequent chains

### Theory update

- `docs/theory.md` §3.11a — formal specification of the Thought-Loop as the fourth optimizer layer, including chain-level prediction formula, decision rule, and calibration extension
- New diagram: `diagrams/dialectical-cot.svg` — per-step protocol flow

### Tests — 28 new, 87 total

- Math tests for `compute_predicted_correct` (bias-invariance at the formula level)
- Decision threshold tests
- Happy-path CoT run (commit-only chain)
- Revise test (antithesis forces narrower synthesis)
- Backtrack test (reject triggers branch retry)
- Backtrack-budget-exhaustion test (max_backtracks → partial terminal)
- Memory aggregation tests (task-type partitioning, calibration MAE, drift warning, failure-mode harvesting)
- Primer generation tests (empty memory, failure-mode-based primer, cross-type-leakage guard)
- Bias-invariance tests: memory does NOT affect verify_answer outcome; predicted_correct is decoupled from ground_truth access
- CLI smoke tests (graceful error when no API key / no memory)

All green: `python -m pytest scripts/ldd_trace/ -q` → 87 passed.

### Philosophical upshot

The thought-loop treats reasoning itself as an optimizable parameter space. Previous LDD layers optimize code, deliverables, and skills. v0.8.0 optimizes *how the agent reasons* for a given task-type class — with the same bias-invariance discipline that guards the lower loops. This is not "just another CoT technique"; it's the generalization of LDD's framework to the reasoning-space manifold.

## [0.7.0] — 2026-04-21

### Added — The Quantitative Dialectic (skill-first, with code plumbing)

The v0.6.0 coupling made memory feed dialectical reasoning via narrative primers. v0.7.0 makes the coupling **numeric** — not by computing gradients in Python, but by prescribing a **5-step numeric protocol** in `skills/dialectical-reasoning/SKILL.md` that the agent walks in-head during synthesis.

This is the point where "gradient via dialectic" stops being metaphor and becomes a reasoning discipline: *LDD is a skill, so the discipline lives in the skill text, not in the tool.* The Python side adds only the calibration substrate.

### The protocol (skill text)

New section in `dialectical-reasoning/SKILL.md` specifies:

- **Step 1 — Thesis** carries `predicted_Δloss` + `confidence_factor`, drawn from `project_memory.json`.
- **Step 2 — Antithesis primers** map to `{probability, impact}` pairs — each primer from `prime-antithesis` now has a numeric interpretation, not just prose.
- **Step 3 — Synthesis** computes `E[Δloss | thesis] = Σ (prob × impact) + (1 − Σprob) × predicted`.
- **Step 4 — Decision rule**: commit if `E[Δloss | thesis] < 0` AND no alternative dominates by > 0.1; reject if an alternative dominates by > 0.1 or `E[Δloss | thesis] ≥ 0`; else escalate (ambiguous).
- **Step 5 — Calibration** logs `predicted_Δloss` at commit; aggregator compares to observed `actual_Δloss` after close.

A worked example (retry-variant vs. root-cause-by-layer in a plateau scenario) walks the five steps end-to-end with actual numbers.

Five hard rules preserve the loss invariant:
1. No fabricated numbers (`n < 3` → confidence = low, prediction = unknown).
2. Prediction is advisory, not gate — agent may override with stated reasoning.
3. Calibration is mandatory — commit without `--predicted-delta` = v0.7.0 protocol was not applied.
4. No cross-project numbers (per-project memory only).
5. Within ambiguity band (|Δ| < 0.1) → user decision.

### Code support for the protocol

- `ldd_trace append --predicted-delta <float>` — new optional arg. When provided, the trace line carries `predicted_Δloss=X` AND the computed `prediction_error = predicted − actual`.
- `aggregator` — new `calibration` section in `project_memory.json`:
  - `n_predictions`, `mean_abs_error`, per-skill `mean_abs_error`
  - `drift_warning: true` when `mean_abs_error > 0.15` over `n ≥ 5` samples — explicit outer-loop signal that the agent's in-head priors are mis-calibrated
- `health` render surfaces the calibration block when predictions exist, so the user sees drift at a glance.

### Why no auto-apply anywhere

All of this is additive to the reasoning protocol. The loss function `L(θ)` is unchanged; the rubric is unchanged; the actual observed Δloss is measured exactly as before. What changes is that the agent's *search direction* is now guided by explicit, auditable, calibratable priors rather than implicit gut-feel. If calibration degrades, the aggregator tells the agent so — and `method-evolution` fires on outer loop, not a silent loss-modification.

### Tests — 8 new, 59 total

- 2 tests for `predicted_delta` field recording (with/without)
- 3 tests for `calibration` aggregation (good calibration, drift warning, empty)
- 2 tests for health rendering (with/without predictions)
- 1 CLI integration test (`append --predicted-delta` round-trips through trace.log)

All green: `python -m pytest scripts/ldd_trace/ -q` → 59 passed.

## [0.6.0] — 2026-04-21

### Added — memory × dialectical coupling (`prime-antithesis` + skill update)

v0.5.2 gave LDD a 1st-moment project memory (aggregate historical stats). v0.6.0 **couples it with 2nd-order reasoning** (the `dialectical-reasoning` skill). In SGD terms:

- **Memory (v0.5.2)** = 1st moment — average of past gradient directions (bias-guarded priors over skill-effectiveness and failure modes).
- **Dialectical (pre-0.6.0)** = 2nd moment / Hessian probing — local adversarial probing of the proposed gradient step for orthogonal directions where L reacts non-monotonically.
- **v0.6.0 coupling** = a Bayesian-style update: `confidence(action) ∝ memory_likelihood × dialectical_likelihood × prior`.

New tool: `python -m ldd_trace prime-antithesis --project . --thesis "..."`. Pulls structured primers from `project_memory.json` and formats them as **questions the antithesis must answer**, not prescriptions. Four primer sources:

| Source | Fires when |
|---|---|
| `skill_failure_mode` | Thesis names a skill with ≥ 30% regression+plateau rate (n ≥ 3) |
| `plateau_pattern` | Current in-flight task has ≥ 2 consecutive near-zero Δ |
| `similar_task` | File-overlap with a non-completed past task (jaccard ≥ 0.3) |
| `terminal_analysis` | Project-wide non-complete rate ≥ 15% (n ≥ 5 tasks) |

Skill update: `skills/dialectical-reasoning/SKILL.md` gains a new section "Memory-informed antithesis generation" that cross-references the tool + enforces three agent-contract rules:
1. Each primer becomes a required antithesis point
2. Generate ≥ 1 antithesis NOT sourced from primers (anti-groupthink guard)
3. Synthesis MUST explicitly reconcile or reject each primer

### Loss invariant preserved (no bias injection)

Primers are **evidence**, not weights:
- No auto-apply: dialectical synthesis decides, memory surfaces
- No ranking: severity ("high"/"warn"/"info") is a visibility hint, not an optimizer weight
- No filtering: memory can't suppress a primer once the statistical threshold is met
- Rubric items and scoring are unchanged; only the *considered-counter-case set* is enriched

A `TestBiasInvariant` test class verifies that primers are phrased as questions (not directives) and that no prescriptive language ("MUST", "DO NOT") appears in primer material — only in the agent contract (which is about process, not code).

### Why this closes the v0.5.2 blind spot

v0.5.2's memory can name "skill X has 40% regression rate here" — but it can't tell you *whether this task is the exception*. That requires reasoning. Without dialectical coupling, memory signals either get ignored (agent overrides) or over-applied (agent cargo-cults). The v0.6.0 contract forces both sources through a synthesis, making the decision auditable.

Concrete benefit on the three failure modes from v0.5.2:
- **Plateau**: memory names resolvers, dialectical asks "is the *parameterization* wrong or just the *attempt*?" — dialectical escalates layer when memory alone would just pivot skill
- **Local minimum**: memory can't see it (L=0 from memory's POV); dialectical IS the generalization-gap probe (layer-5 / regularizer)
- **Wrong decision**: memory gives rate, dialectical gives causal defensibility — agreement on both = commit, disagreement = investigate

### Tests — 14 new, 51 total

- 2 skill-failure-mode primer tests (fires for retry-variant, silent for root-cause-by-layer)
- 2 plateau-pattern primer tests (fires on 2-streak, silent on healthy task)
- 2 terminal-analysis primer tests (threshold boundary behavior)
- 1 combined-priming test (plateau + bad-skill = 2 primers)
- 2 formatter tests (empty + populated)
- 3 CLI integration tests (help / error-on-missing-memory / full-flow)
- 2 bias-invariant tests (evidence-not-decision, no-ranking-weights)

All green: `python -m pytest scripts/ldd_trace/ -q` → 51 passed.

## [0.5.2] — 2026-04-21

### Added — trace-based project memory (`aggregate` / `suggest` / `check` / `similar` / `health`)

v0.5.1 made per-iteration trace emission cheap. v0.5.2 makes the accumulating trace.log **useful** as a project-level memory — the agent reads historical patterns to detect plateaus and flag regressive skill-choices, without biasing the loss itself.

Five new CLI subcommands on top of the v0.5.1 tool:

```bash
python -m ldd_trace aggregate --project .          # write .ldd/project_memory.json
python -m ldd_trace health    --project .          # human-readable project state
python -m ldd_trace suggest   --project . [--top-n 5]  # empirical skill ranking
python -m ldd_trace check     --project . [--next-skill X]  # in-flight warnings
python -m ldd_trace similar   --project . --files a,b,c     # file-overlap retrieval
```

`ldd_trace close` auto-runs `aggregate` as a side effect — project_memory.json is never stale.

### Core design constraint — memory must not bias the loss

The loss function `L(θ)` (rubric violations) stays pure. Memory informs NAVIGATION (which skill next, when to escalate, where to warm-start) but NEVER redefines progress.

Four explicit bias-guards, each tested:

| Bias | Risk | Guard |
|---|---|---|
| Survivorship | "complete-only" skill stats inflate effectiveness | aggregate counts **every** terminal state; per-skill `by_terminal` breakdown exposed |
| Regression-to-mean | Skills that fire on hard bugs show trivially higher Δ | report both `delta_mean_abs` **and** `delta_mean_relative` (Δ / prev_loss) |
| Recency drift | Weighting recent heavier masks skill-version drift | both lifetime and last-30-day windows shown; caller chooses |
| Confirmation | Agent self-curation skews aggregate | aggregation is deterministic on raw trace; agent never filters |

Each guard is both documented (`bias_guards` block in `project_memory.json`) and test-enforced (`test_e2e_memory.py::TestAggregatorBiasGuards`).

### The two use cases the memory unlocks

1. **Plateau detection** — current task shows ≥ 2 consecutive near-zero Δ → `check` emits HIGH-severity warning citing historical resolvers ("past plateaus resolved by root-cause-by-layer (3) over 3 observations"). Agent sees empirical exit-path, not just "you're stuck."
2. **Wrong-decision detection** — next planned skill has ≥ 30% historical regression-rate → `check` warns before the bad step. Scoped to same project (no cross-project contamination).

Both are retrospectively validated against the narralog trace: at narralog's actual i3 (streak=1) the check correctly produces **no** warning (false-positive guard holds); at a simulated counterfactual i4 (streak=2) the check **would have** flagged the plateau and named root-cause-by-layer as the historical resolver — matching what narralog's actual i4 manually arrived at via method-evolution.

### Storage shape

```
.ldd/
  trace.log              ← v0.5.1 — append-only log of iterations + closes
  project_memory.json    ← v0.5.2 — deterministic aggregate, auto-refreshed
```

Per-project by default. No cross-project global aggregate (explicit design choice for privacy + no signal-mixing). Session state is ephemeral — recovered from trace.log at task start via `ldd_trace status`.

### Tests — 16 new, 37 total

- 5 bias-guard correctness tests (survivorship, by-terminal split, relative delta, windows, metadata)
- 3 aggregator metric tests (task_shape, retry-variant no-progress signature, plateau-pattern detection)
- 2 plateau-detection tests (triggers when streak ≥ 2; false-positive guard on healthy task)
- 2 wrong-decision tests (warns on regressive skill; no-warn on good skill)
- 1 over-budget detection test (k ≥ p95 triggers escalation warning)
- 2 retrospective-against-narralog tests (narralog i3 correctly doesn't fire; counterfactual i4 does)
- 1 skill-ranking test (workhorse skill outranks bad skill)

All green: `python -m pytest scripts/ldd_trace/ -q` → 37 passed.

## [0.5.1] — 2026-04-21

### Added — `scripts/ldd_trace/` CLI tool for per-iteration trace emission

v0.5.0 mandated per-iteration emission of the trace block (see `using-ldd/SKILL.md` § "When to emit"). v0.5.1 makes that mandate **cheap to honor**: a Python package with a five-subcommand CLI (`init` / `append` / `close` / `render` / `status`) that persists to `.ldd/trace.log` and re-renders the full block on every write.

```bash
python -m ldd_trace init   --project . --task "bug fix" --loops inner
python -m ldd_trace append --project . --loop inner --auto-k \
    --skill e2e-driven-iteration --action "what changed" \
    --loss-norm 0.333 --raw 1/3 --loss-type rate
python -m ldd_trace close  --project . --loop inner --terminal complete \
    --layer "3: contract · 5: invariant" --docs synced
```

Rendering logic was **lifted verbatim from `scripts/demo-trace-chart.py`** into `scripts/ldd_trace/renderer.py` — no behavior change versus the v0.5.0 demo output. The demo script remains as the educational reference.

### Changed — per-iteration trace emission reclassified from "should" to hard step

Empirical finding behind v0.5.1: on a real multi-iteration task (narralog, 2026-04-21), the v0.5.0 per-iteration emission mandate was silently dropped across 4 iterations despite the spec. The mandate lived only in `using-ldd/SKILL.md` § "When to emit" — the iteration-performing skills didn't cross-reference it, so the agent finished iterations without rendering the trajectory.

Method-evolution fix across three skills:

- `skills/e2e-driven-iteration/SKILL.md` — the Five-Step Iteration becomes **Six-Step**; step 6 is `Emit trace` with an explicit `python -m ldd_trace append ...` call. "Do not skip step 6" is added with a one-paragraph rationale. The red-flags list gains `"I'll emit the trace block at the end of the whole task"` → NO, per-iteration is a data-visibility requirement. The checklist grows from 7 to 8 items (step 7 = emit; step 8 = close).
- `skills/loop-driven-engineering/SKILL.md` — `Sub-Skill Dispatch` table gains two rows: `ldd_trace status` at task start (recover prior iteration state from `.ldd/trace.log`), and `ldd_trace append` at iteration close (emission contract).
- `skills/using-ldd/SKILL.md` — adds a RED FLAGS table immediately after § "When to emit" with four concrete rationalizations and the correct response for each. Adds a "bidirectional" subsection: trace.log is now READ at task start for state recovery, not just written.

### Why a tool, not just a stricter spec

v0.5.0's spec was already strict — the violation was tooling-driven. Per-iteration emission asked the agent to hand-render ~30 lines of ASCII (sparkline + chart + per-iteration info lines) on every loss measurement. Under time pressure that overhead got discounted. v0.5.1 reduces the cost to one shell command: if the agent can run `pytest`, it can run `python -m ldd_trace append ...`. Spec strictness is now matched by ergonomic strictness.

### Bidirectional trace.log

Prior to v0.5.1 the trace.log was write-only (persistence for grep / audit). v0.5.1 makes it the **source of truth** for iteration-state recovery across sessions:

- `python -m ldd_trace status --project .` → machine-readable `next_k` per loop + last `loss_norm` per loop
- `python -m ldd_trace render --project .` → full trace block reconstituted from log alone

A new session starting on an existing project reads trace.log first and resumes at the correct `k` instead of starting at `i1` again.

### Tests

- `scripts/ldd_trace/test_ldd_trace.py` — 21 unit + integration tests, pytest-driven:
  - Pure renderer functions (sparkline, trend_arrow, mini_chart) against the §"Rendering recipe" in `using-ldd/SKILL.md`
  - Store round-trip (init → append → close → render) on pytest's `tmp_path`
  - CLI subprocess tests for all five subcommands
  - Three-channel consistency: sparkline last bar + chart last marker + final iteration's loss must agree on the same number

All green: `python -m pytest scripts/ldd_trace/test_ldd_trace.py -q` → 21 passed.

## [0.5.0] — 2026-04-21

### Added — trace visualization (sparkline, mini chart, mode+info line, trend arrow)

The LDD trace block now carries four parallel channels alongside the numeric loss values, making the trajectory AND the per-iteration skill work both auditable at a glance. Closes two friction points in one release: "loss numbers on their own are hard to eyeball" (solved by sparkline + chart) and "the user can't tell which skill did what per iteration" (solved by the mandatory mode-indicator + info line).

**The four channels** (in `skills/using-ldd/SKILL.md` § Loss visualization — sparkline, mini chart, mode+info line, trend arrow):

| Channel | Mandatory at | Purpose |
|---|---|---|
| **Trajectory sparkline** (`▁▂▃▄▅▆▇█`, auto-scaled, zero → `·`) | ≥ 2 iterations | Micro-dynamics — 8-level resolution across the full run |
| **Trend arrow** (`↓` / `↑` / `→`, first-vs-last delta) | ≥ 2 iterations | Net direction at the end of the sparkline; distinct from per-step `Δ` arrows |
| **Mini ASCII loss-curve chart** (`┤` y-axis + `●` markers + labeled x-axis) | ≥ 3 iterations | Macro-trajectory with `0.25`-step snap and per-phase labels (`i1`, `r2`, `o1`) |
| **Per-iteration mode + info line** | every iteration | The iteration label carries a mode parenthetical — `(inner, reactive)`, `Phase p1 (architect, <creativity>)` with creativity ∈ {standard, conservative, inventive}, `(refine)`, or `(outer)` — so the reader can tell which discipline was active per iteration. An indented continuation line carries `*<skill-name>*` + a one-line description of what concrete change the iteration produced. Gives the user an audit trail without scrolling elsewhere |

The sparkline and chart MUST agree on the final `loss_k`. The SKILL.md section specifies a deterministic rendering recipe (sparkline indexing via `round(v/max * 7)`, chart snap via `floor(v/0.25 + 0.5) * 0.25`, trend arrow via first-vs-last delta with ±0.005 plateau band, mode-indicator grammar per loop/mode) so renders are reproducible across agents and sessions.

**Non-monotonic trajectories are first-class.** The end-to-end trend arrow is computed from `last − first`, so `0.667 → 0.833 → 0.167` (i1→i2 regression, i2→i3 recovery) still reads `↓` at the end of the sparkline — even though the per-step `Δ` arrow on i2 correctly shows `↑` locally. Sparkline arrow = net direction; per-step `Δ` arrow = local direction. The SKILL.md text calls this distinction out explicitly to prevent conflation.

**Mode-indicator grammar.** The parenthetical on each iteration line uses the four-way split: `(inner, reactive)` for default inner work, `Phase pk (architect, <creativity>)` when architect-mode replaces the inner loop (note: word `Phase` not `Iteration`, signaling the 5-phase protocol), `(refine)` for y-axis deliverable work, `(outer)` for θ-axis method work. A session that runs architect inner → hands off to reactive inner renders both in the same trace: `Phase p1..p5` followed by `Iteration i1..i<k>`.

**Why no per-iteration `█`/`░` bar** (explicit design non-choice). An earlier draft of the spec included a 20-char magnitude bar per iteration. It was removed because information density is strictly worse than the mode+info line — bars re-encode data already carried by the sparkline and chart, while the mode+info line carries *new* information (which skill, what action) the user cannot reconstruct from loss numbers alone.

### Changed — trace emission cadence: once-per-task → after every iteration (live)

Prior to v0.5.0 the rule was "emit ONE block per task; re-emit at message end if the task spans messages." The rule is now **emit after every iteration** during live task execution — the user watches the loss descend in real time rather than waiting until task close. Consecutive emissions grow monotonically by exactly one iteration (plus one sparkline char, one chart column, and a possibly-flipped trend arrow).

The per-skill-invocation anti-pattern is preserved: within one iteration multiple skills may fire (e.g. `reproducibility-first` + `root-cause-by-layer`), they still share ONE block emitted at iteration close. The rule discriminates iterations from skill-invocations, not the emission from existence.

**Post-hoc reconstruction exception** (new in v0.5.0): when the user hands you a completed task's iteration data and asks you to render the trace, emit ONE final block — there are no real iterations happening, so repeating the growing block would print the same data 3× without adding information. The `tests/fixtures/using-ldd-trace-visualization/` fixture exercises this exception (all three scenarios are post-hoc reconstructions).

**Budget trade-off acknowledged.** Per-iteration emission multiplies trace-block token cost by the iteration count. For tight-context sessions, the existing compression rule (info-lines collapsed to skill-name-only) mitigates; the visualization channels are never dropped. The audit-transparency gain was judged worth the token cost — a user who cannot see their loop's progress until close is a user who will ask "is it still running?" after 90 seconds of silence.

### Changed — trace block example in README reflects v0.5.0 format

The inline trace example in `README.md` § "Live trace — see the loop happen in real time" was replaced with a 6-iteration three-loop run rendered in full v0.5.0 format (sparkline, chart, per-iteration mode+info + `Δ` column, close). A new subsection `#### Mental model — the four visible channels` follows, explaining each granularity and the consistency rule, and linking to the authoritative SKILL.md section and the v0.5.0 fixture.

### Tests — new fixture `tests/fixtures/using-ldd-trace-visualization/`

Three RED/GREEN scenarios, captured at `deepseek/deepseek-chat-v3.1`, T=0.7, via OpenRouter (cheaper than v0.4.0's `gpt-5-mini`; total capture spend ≈ $0.05). Scored against a 4-item rubric measuring channel emission + mode-indicator grammar + per-iteration skill-info + net-direction-arrow correctness.

| Scenario | RED loss | GREEN loss | Δloss |
|---|---:|---:|---:|
| inner-three-iters | 4 / 4 | 2 / 4 | **+2** |
| all-three-loops | 4 / 4 | 0 / 4 | **+4** |
| regression-and-recovery | 4 / 4 | 0 / 4 | **+4** |

Every scenario clears the Δloss ≥ 1 release gate. Bundle-scoped normalized Δloss for this fixture: `0.833`, well above the bundle target of `≥ 0.30`. Scenario `inner-three-iters` lost 2 items in GREEN (mini chart and trend arrow not emitted — base-model rendering skip at T=0.7 on the shortest scenario); sparkline and mode+info line transferred cleanly. Scenarios 2 and 3 hit all four items; scenario 3 validates the subtlest discriminator — GREEN correctly reads the non-monotonic prompt and emits `↓` end-to-end while keeping the per-step `Δ +0.167 ↑` on i2.

### Updated

- `skills/using-ldd/SKILL.md` — new `### Loss visualization — sparkline, mini chart, mode+info line, trend arrow` subsection (4-channel mandatory thresholds, mode-indicator grammar, deterministic rendering recipe, 6-iteration reactive-inner worked example, architect→inner hand-off worked example, non-monotonic-trajectory rule, compression rule, loss-type-specific rendering)
- `README.md` — trace example block replaced with v0.5.0 format; new `#### Mental model — the four visible channels` subsection with fixture link + measurement summary
- `tests/fixtures/using-ldd-trace-visualization/` — new fixture (scenario.md + rubric.md + runs/20260421T122248Z-clean/)
- `scripts/demo-trace-chart.py` — new demo helper, renders the trace block from a hard-coded 6-iteration task with mode-indicator + info lines. Pure renderer, no skill invocations, no LLM calls; functions (`sparkline`, `mini_chart`, `trend_arrow`, `render_trace`) are directly liftable into a future renderer module under `skills/using-ldd/`
- `scripts/demo-e2e-trace.py` — new executed-demo helper. Optimizes a real Python function (`compute_average`) through all three loops (inner → refine → outer), running actual rubric checks against actual compiled code at every iteration and re-rendering the trace block after each. Supports `--fast` for piping; default pauses 0.5s per iteration for live-feel. No simulation — every loss value is computed from `exec()` + call + rubric assertion
- `scripts/README.md` — new rows for both demo helpers
- `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json`, `gemini-extension.json` — version bumped `0.4.0` → `0.5.0`

## [0.4.0] — 2026-04-21

### Added — auto-dispatch for architect-mode

The coding agent can now enter architect-mode **on its own** when the task description carries enough structural signals — without the user having to type `LDD[mode=architect]:`, invoke `/ldd-architect`, or use an explicit trigger phrase. Closes the "user described greenfield but didn't know the magic word" failure mode.

**The 6-signal scorer** (in `skills/using-ldd/SKILL.md` § Auto-dispatch for architect-mode): greenfield `+3`, names ≥ 3 new components `+2`, cross-layer scope `+2`, ambiguous requirements `+2`, explicit bugfix `−5`, single-file known-solution `−3`. Weighted sum ≥ 4 → architect-mode. Hard gate, not average; tie-break at exactly 4 goes architect.

**Creativity inference** from the same task signals: regulatory / compliance / no-new-tech / tight team+deadline cues → `conservative`; research / novelty / "invent" / "experiment" cues → `inventive`; neither → `standard` (default). Conservative beats inventive on ties. The per-task acknowledgment flow for `inventive` is unchanged — auto-dispatch proposes the level but does not bypass the ack gate; without a literal `acknowledged` reply, the run silently downgrades to `standard`.

**Explicit user triggers always win.** Precedence order (highest first): inline `LDD[mode=…]` / `LDD[creativity=…]` flags > `/ldd-architect` command arg > trigger-phrase match > auto-dispatch (this pipeline) > bundle default. `LDD[mode=reactive]:` on a task with auto-score 6 stays reactive.

### Changed — trace header extended with dispatch source

Every architect-mode trace block now carries a `Dispatched:` line naming one of `inline-flag`, `command`, `trigger-phrase: "<phrase>"`, or `auto (signals: <top-2 by absolute weight>)`. Silent auto-dispatch is a trace-integrity violation — the user must be able to see WHY architect-mode was entered and override with one follow-up message. Example:

```
│ Dispatched : auto (signals: greenfield=+3, cross-layer=+2)
│ mode: architect, creativity: standard
```

### Changed — README mental-model wiring

New subsection `Mental model — the auto-dispatch flow` under the architect-mode README block. Linked mental model per LDD's own docs-as-DoD rule: cites `skills/using-ldd/SKILL.md` (trigger table), `skills/architect-mode/SKILL.md` § creativity, `docs/ldd/convergence.md` (loss-function framing), `docs/ldd/hyperparameters.md` (precedence). Embeds an SVG of the Task → Signal-extraction → Score → {mode, creativity, ack-flow} → Trace-echo pipeline (`docs/diagrams/architect-auto-dispatch.svg`; self-contained, no `feDropShadow`, GitHub-safe).

### Tests — new fixture `tests/fixtures/architect-mode-auto-dispatch/`

Four RED/GREEN scenarios, captured at `openai/gpt-5-mini`, T=0.7, via `scripts/capture-red-green.py` (new helper — paired RED/GREEN captures with skill content as system-message on the GREEN side). Scored against a 4-item rubric measuring dispatch-correctness:

| Scenario | RED loss | GREEN loss | Δloss |
|---|---:|---:|---:|
| bugfix-skip | 1 / 4 | 0 / 4 | **+1** |
| greenfield-inventive | 4 / 4 | 0 / 4 | **+4** |
| regulated-conservative | 4 / 4 | 0 / 4 | **+4** |
| typical-standard | 4 / 4 | 0 / 4 | **+4** |

Every scenario clears the Δloss ≥ 1 release gate. Bundle-scoped normalized Δloss for this fixture: `0.813`, above the bundle target of `≥ 0.30`. Dominant driver is the trace-echo discipline (item 3) — the base model has no reason to invent a `Dispatched:` line, so this item flips RED → GREEN in every scenario.

### Updated

- `skills/using-ldd/SKILL.md` — new `## Auto-dispatch for architect-mode` section (scorer, creativity inference, precedence, worked example); trigger-table entry for architect-mode mentions the fourth path; architect trace-block example extended with `Dispatched:` line
- `skills/architect-mode/SKILL.md` — new `## Auto-dispatch by the coding agent` section summarizing the scorer and pointing at the authoritative spec in `using-ldd/SKILL.md`; description field mentions auto-dispatch
- `README.md` — new `### Mental model — the auto-dispatch flow` subsection with SVG
- `docs/diagrams/architect-auto-dispatch.svg` — new diagram, 12 KB, 820 × 940 viewBox, no `feDropShadow`, no external refs
- `tests/fixtures/architect-mode-auto-dispatch/` — new fixture (scenario.md + rubric.md + runs/20260421T002928Z-clean/)
- `scripts/capture-red-green.py` — new paired-capture helper (OpenRouter / OpenAI / Anthropic fallback, retry-once-with-30s-backoff, no `print()`)
- `.claude-plugin/plugin.json` + `.claude-plugin/marketplace.json` + `gemini-extension.json` — version 0.3.2 → 0.4.0

No breaking changes. Existing opt-in paths (inline flag / command / trigger phrases) continue to work unchanged and take precedence over the new auto-dispatch.

## [0.3.2] — 2026-04-20

### Changed — normalized loss as canonical trace form

Every LDD loss value in the trace block and `.ldd/trace.log` now displays as **normalized [0, 1] primary + raw `(N/max)` secondary**. Replaces the v0.3.1 absolute-integer form (`loss_0 = 3`, `Δloss = +3`) with `loss_0 = 0.375  (3/8 violations)`.

**Why.** Skills have different rubric-maxes: `e2e-driven-iteration` has 5 items, `architect-mode` has 10. Comparing `Δloss = +3` (e2e) to `Δloss = +6` (architect) was apples-to-oranges; `0.600` vs. `0.600` is directly comparable. The raw `(N/max)` in parens keeps actionability — the user still sees "3 of 8 items remain open."

**Three display modes**, chosen per task by the shape of the measurement, named on a new `Loss-type` header line:

- `normalized-rubric` — `loss = violations / rubric_max` → float in [0, 1] plus raw in parens (default for most skills)
- `rate` — signal already in [0, 1] (flake rate, coverage) → single float, no re-normalization
- `absolute-<unit>` — unbounded continuous signal (latency, throughput) → absolute value with unit, no normalization (normalizing an unbounded value invents a denominator and produces fake precision)

**Anti-patterns now spelled out explicitly in `skills/using-ldd/SKILL.md`:**

- Never display a normalized float without the raw denominator in parens — `loss_0 = 0.375` alone hides that it's `3/8`
- Never normalize a count that has no natural max (latency, commit counts, token usage) — those stay `absolute-<unit>`

### Changed — aggregate target simplified

`Δloss_bundle` target moves from absolute (`≥ 2.0 mean violations removed per skill`) to **normalized (`≥ 0.30`** — each skill removes ≥ 30 % of rubric violations that appear without it). Current measured: **`Δloss_bundle = 0.561`** across all 11 skills — target met with margin. Raw absolute mean (3.91, v0.3.1 form) retained in git history but no longer cited.

Per-skill normalized Δloss ranges from 0.250 (`loop-driven-engineering`, partial-contamination baseline) to 1.000 (`architect-mode`). `tests/README.md` now leads with the normalized column; raw `(N/max)` kept for audit.

### Plugin-reference conformance — final audit

Full audit against `https://code.claude.com/docs/en/plugins-reference`:

- **Manifest** — `name` required field present. All recommended optional fields present: `version`, `description`, `author` (with `url`), `homepage`, `repository`, `license`, `keywords`.
- **Marketplace** — `$schema`, `name`, `description`, `owner` (with `url`), `plugins` array with per-entry `name`, `description`, `version`, `source`, `category`, `homepage`, `author`. Matches the shape used by plugins already accepted in `claude-plugins-official`.
- **Skills** — 12 `skills/<name>/SKILL.md` files, each with `name` + `description` frontmatter; directory name matches `name` field in every case (verified via script).
- **Commands** — 7 `commands/*.md` files, each with `description` frontmatter.
- **Structure** — `.claude-plugin/` contains only `plugin.json` and `marketplace.json`; all component dirs at plugin root. Zero violations of the "components at root, not inside `.claude-plugin/`" rule.
- **No agents / hooks / MCP / LSP / monitors** — none needed for this plugin; fields omitted cleanly (all optional per reference).

### Updated

- `skills/using-ldd/SKILL.md` — trace-block spec rewritten for normalized loss + `Loss-type` header line + 3-mode spec + anti-patterns
- `skills/architect-mode/SKILL.md` — trace example updated; Phase 4 scoring cells now show `0.778 (14/18)` form
- `evaluation.md` — target reformulated to `≥ 0.30` normalized; measured `0.561`; "why normalized" section added
- `tests/README.md` — per-skill table leads with normalized Δloss column; raw `(N/max)` kept for audit
- `docs/ldd/convergence.md` — new §5 "Loss display" explaining the three modes
- `README.md` — hero badge updated to `Δloss_bundle = 0.561 (normalized)`; measured-section reframed
- `.claude-plugin/plugin.json` — `description` updated; version 0.3.1 → 0.3.2
- `.claude-plugin/marketplace.json` + `gemini-extension.json` — version 0.3.2

No breaking changes. Existing traces in `tests/e2e/v031-runs/` are historical artifacts and retain the old absolute display; all new traces emit the normalized form.

## [0.3.1] — 2026-04-20

### Added — creativity levels for architect-mode

Architect-mode gains a `creativity` sub-parameter with three discrete levels, framed consistently with LDD's neural-code-network metaphor. The levels are **three different loss functions**, not three amounts of freedom:

- **`conservative`** — `L = rubric_violations + λ · novelty_penalty`. Enterprise / no-new-tech / small team. All 3 candidates must be battle-tested; component novelty penalized; team-familiarity weighted 2× in scoring. Adds rubric item #11 (novelty penalty).
- **`standard`** (default) — `L = rubric_violations`. The current v0.3.0 architect-mode behavior, unchanged.
- **`inventive`** — `L = rubric_violations_reduced + λ · prior_art_overlap_penalty`. Research / prototype. Novelty rewarded, prior-art penalized, with mandatory experiment-validation path + fallback-to-standard baseline. Rubric items 1–2 may relax; items 5–8 replaced by invention-specific criteria (#I1 differentiation-from-prior-art, #I2 experiment-validation-path, #I3 fallback-to-baseline-named). Requires per-task user acknowledgment before running.

### Hard guards against moving-target-loss

- **No integer tuning.** Three named alternatives only — "dial up until creative" is the exact drift anti-pattern LDD fights. Discrete objectives prevent it.
- **No level-switching mid-task.** Mixing two loss functions in one gradient descent is incoherent optimization. Agent refuses and requires task restart.
- **`inventive` is per-task only.** Cannot be set as project-level default in `.ldd/config.yaml`; agent ignores and downgrades to `standard` with a trace warning if it finds one.
- **Default stays `standard`.** No behavior change for existing architect-mode users.

### Integration

- `skills/architect-mode/SKILL.md`: new §§ Creativity levels, Level-switch prohibition, Project-level config restriction, plus description updated to mention the three levels
- `docs/ldd/hyperparameters.md`: `creativity` added as 5th knob (architect-mode-only sub-parameter)
- `docs/ldd/architect.md`: new § Creativity levels
- `docs/ldd/convergence.md`: new § 7 framing creativity as loss-function selection within the ML lens
- `docs/ldd/config.example.yaml`: `creativity: standard` example + `inventive` restriction comment
- `skills/using-ldd/SKILL.md`: inline syntax `LDD[mode=architect, creativity=<level>]:`, trace-block header now shows `Loss-fn` line naming the active objective
- `commands/ldd-architect.md`: accepts positional or `creativity=<level>` argument, runs acknowledgment flow for `inventive`
- `evaluation.md`: per-level rubric variants (`R_arch_standard` / `R_arch_conservative` / `R_arch_inventive`)
- README: new "Creativity — three loss functions, not a freedom dial" sub-section; hyperparameter table extended to 5 rows; install-in-30-seconds block unchanged

### Rationale

The user asked for a "freedom dial from 1=structural to 10=new paradigms". Dialectical review rejected the 1–10 framing:

- 10 grades would not have 10 measurably distinct behaviors (grades 6 vs. 7 would blur)
- Integer knobs invite "tune until output feels creative" — the exact moving-target-loss pattern every LDD skill fights
- Creativity isn't a quantity; it's a **choice of objective**. Architecture optimizing for "minimize novelty" and architecture optimizing for "maximize differentiation from prior art" are two different problems, not two degrees of the same problem

Three discrete loss functions solve the original intent (letting the user pick between conservative / standard / inventive postures) without opening a drift attack surface.

### Version

Bumped to `0.3.1` across `plugin.json`, `marketplace.json`, `gemini-extension.json`. No breaking changes — `standard` (default) behaves identically to v0.3.0 architect-mode.

## [0.3.0] — 2026-04-20

### Added — architect mode

- **New opt-in skill `architect-mode`** (`skills/architect-mode/SKILL.md`) — flips LDD from reactive debugging into constructive architecture when the user signals design intent. Rigid 5-phase protocol: Constraint extraction → Non-goals → 3 candidates on a load-bearing axis → Scoring + dialectical pass → Deliverable (doc + compilable scaffold + failing tests per component + measurable success criteria). Explicit hand-off back to default reactive mode after Phase 5 closes.
- **10-item architect rubric** in `evaluation.md` and `tests/fixtures/architect-mode/rubric.md`.
- **Fourth hyperparameter `mode`** (`reactive` | `architect`) exposed across the existing three-path config system: inline `LDD[mode=architect]:`, `/loss-driven-development:ldd-architect` command, `.ldd/config.yaml`'s `mode` key, `/ldd-set mode=architect`. Documented in `docs/ldd/hyperparameters.md` and `docs/ldd/config.example.yaml`.
- **New slash command** `/loss-driven-development:ldd-architect` — activates architect mode for the next task, reverts to reactive after hand-off.
- **New task-type MD** `docs/ldd/architect.md` added to the dispatch table in `docs/ldd/task-types.md`.
- **Architect-variant trace block** in `skills/using-ldd/SKILL.md` — shows phases (1–5) instead of iterations, includes Mode header, emits explicit hand-off line at close.
- **Escalation protocol** for phases that cannot complete cleanly (too few constraints, fewer than 3 candidates, scoring ties within 10 %, rubric violations ≥ 3/10).
- **Trigger phrases** in `skills/using-ldd/SKILL.md` dispatch table: "design X", "architect Y", "greenfield", "from scratch", "how should I structure", "propose an architecture", "decompose this", "what's the right shape for X".

### Measured

- `architect-mode` captured clean RED + GREEN via direct API (`openai/gpt-5-mini`, T=0.7). **RED violations 10/10, GREEN violations 0/10, Δloss = +10** — **largest effect size in the bundle.** Raw artifacts at `tests/fixtures/architect-mode/runs/20260420T190302Z-clean/`.
- `Δloss_bundle` recomputed across all 11 skills: **3.91 absolute (mean per skill), 0.561 relative**. Target `≥ 2.0` met with margin (was 3.30 at n=10 in v0.2.1).

### Updated

- README hero badge: Δloss_bundle 3.30 → 3.91; skill count badge "10 + entry" → "10 + architect + entry".
- README adds an "Architect mode — Claude as designer, not just debugger (opt-in)" section with 5-phase summary, activation paths, hand-off, and effect-size citation.
- `AGENTS.md`, `GEMINI.md` extended to twelve skills.
- Hyperparameter table in README adds `mode` row.
- Version bumped to `0.3.0` across `plugin.json`, `marketplace.json`, `gemini-extension.json`.

### Rationale

LDD v0.2.x was entirely reactive — it assumed code existed and iterated on loss signals. That framing missed the input-X-to-output-Y space between problem and delivered system: decomposition, contracts, non-goals, architecture. `architect-mode` fills exactly that gap, but as **opt-in** — default behavior for routine debugging/refactoring is unchanged; the 5-phase ceremony only runs when the user signals greenfield design intent.

## [0.2.1] — 2026-04-20

### Added

- **`docs/ldd/`** — canonical methodology directory. Task-type-specific compressed MDs (`debugging.md`, `design-decisions.md`, `refactor.md`, `refinement.md`, `release.md`, `incident.md`, `method-maintenance.md`) with `task-types.md` as the dispatch table. Prevents methodology drift across README / skill bodies / user-project docs. Moved `convergence.md` and `in-awp.md` here; updated all cross-links.
- **`scripts/capture-clean-baseline.py`** — portable tool to capture RED baselines via direct LLM API (OpenRouter / OpenAI / Anthropic). Sidesteps the Claude-Code-subagent contamination problem that previously blocked `docs-as-definition-of-done` measurement.
- **Tier-3.9 E2E capture** — `tests/e2e/scenario-01-refactor/runs/20260420T164505Z/`: skills installed at `~/.claude/skills/` (not prompt-injected), subagent discovered and applied them at runtime, 7/7 rubric items, loop closed k=1/5.
- **N=3 distribution demo** — `tests/fixtures/root-cause-by-layer/runs/20260420T165603Z-clean-N3/`: 3 independent RED captures via `capture-clean-baseline.py`, all same failure mode (type-tolerance shim), stddev ≈ 0.5.
- **Second scenario** for `root-cause-by-layer` (`tests/fixtures/root-cause-by-layer/scenario-2/`): different domain (rate-limiter precondition) exercising the same skill. Partial scenario-design-bias reduction.

### Changed

- `Δloss_bundle` recomputed across all 10 skills (was 9 of 10 in v0.2.0): **3.30 absolute (mean per skill), 0.517 relative**. Target `≥ 2.0` met with margin. Previously-blocked `docs-as-definition-of-done` now clean-measured at Δloss = +2.
- `evaluation.md` reflects n=10 aggregate.
- `tests/README.md` published per-skill table updated.
- `GAPS.md` rewritten: what's actually closed, what's still open, what only adopters can close.
- Version bumped to `0.2.1` across `plugin.json`, `marketplace.json`, `gemini-extension.json`.

### Still pending

- Real tier-4 (`/plugin install` in a live Claude Code / Codex / Gemini CLI session) — needs an adopter.
- N≥10 distributions per skill — infrastructure in place; needs community runs.
- Independent (non-author) scenario design — community PRs welcome.

## [0.2.0] — 2026-04-20

### Added

- **Three-loop model.** Formalised the inner (code), refinement (deliverable), and outer (method) loops as three orthogonal optimization axes. Mental model in [`docs/ldd/convergence.md`](./docs/ldd/convergence.md).
- **Five new skills** extending v0.1's inner-loop focus:
  - `reproducibility-first` — gate before any gradient use
  - `e2e-driven-iteration` — measure-per-iteration inner-loop rhythm
  - `iterative-refinement` — y-axis SGD on deliverables
  - `method-evolution` — outer-loop θ-axis SGD on skills / rubrics
  - `drift-detection` — periodic full-repo scan for cumulative drift
- **Six diagrams** as Graphviz SVGs (GitHub-renderer-compatible, no `feDropShadow`):
  - `three-loops.svg`
  - `convergence-vs-divergence.svg`
  - `code-drift-mechanism.svg`
  - `skill-dispatch-flow.svg`
  - `mental-model-ldd.svg`
  - `skills-overview.svg`
- **Case study** [`docs/ldd/in-awp.md`](./docs/ldd/in-awp.md) — one-to-one mapping from LDD skills to their [AWP](https://github.com/veegee82/agent-workflow-protocol) origins + a concrete debugging walkthrough.
- **Optional Claude-Code tooling** under `scripts/`:
  - `drift-scan.py` — heuristic scanner for seven drift indicators
  - `evolve-skill.sh` — RED/GREEN re-run scaffolder for a skill against its fixture
  - `render-diagrams.sh` — `.dot → .svg` regenerator
- **Rubrics** for all 10 skills in [`evaluation.md`](./evaluation.md).
- **Test fixtures** scaffolded for the 5 new skills (scenario + rubric + baseline-notes per skill) in [`tests/fixtures/`](./tests/fixtures/).

### Changed

- `loop-driven-engineering` now exposes the three loops explicitly (was a single inner loop in v0.1), dispatches the 9 other skills in this plugin at the right moments, and keeps the inner-loop `K_MAX = 5` budget unchanged.
- Install instructions use real `git clone` commands with the published GitHub URL — no more `/path/to/…` placeholders.
- README reshaped for marketing-first: hero with TDD anchor, "Without LDD / With LDD" table, AWP-case-study callout, skills overview SVG replacing the earlier ASCII diagram.
- Version bumped to `0.2.0` across `plugin.json`, `marketplace.json`, and `gemini-extension.json`.

### Known gaps

See [`GAPS.md`](./GAPS.md). Headline items:

- Baselines for the 5 new skills are scaffolded, not captured — RED/GREEN execution pending in a clean environment.
- No tier-4 live-install E2E has been captured end-to-end.
- `Δloss_bundle` is defined in `evaluation.md` but not yet measured.

## [0.1.0] — 2026-04-19

### Added

- Initial 5 skills: `root-cause-by-layer`, `loss-backprop-lens`, `dialectical-reasoning`, `docs-as-definition-of-done`, `loop-driven-engineering`.
- Multi-platform distribution: `.claude-plugin/plugin.json` + `marketplace.json` (Claude Code), `gemini-extension.json` + `GEMINI.md` (Gemini CLI), `AGENTS.md` (Codex + generic).
- `evaluation.md` with per-skill rubrics for the 5 initial skills.
- `tests/fixtures/` for the 5 initial skills (with baseline-contamination caveats documented in per-fixture `baseline-notes.md`).
- `tests/e2e/scenario-01-refactor/` — starter code and task spec for a tier-4 integration run.
- `GAPS.md` honest accounting of what is not verified.
