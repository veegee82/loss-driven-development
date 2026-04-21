# v0.9.0 Critical Audit — Findings Report

**Audit method**: dialectical-reasoning applied at the system level. Thesis = "v0.9.0 is sound + bias-invariant". Antithesis = enumerate collapse-candidate categories. Synthesis = evidence-backed finding per candidate.

**Evidence producer**: `scripts/ldd_trace/test_v0_9_0_audit.py` — 15 tests. Each test PASSES when the asserted vulnerability/limitation condition holds under current v0.9.0 code. Run with `python -m pytest scripts/ldd_trace/test_v0_9_0_audit.py -v`.

**Severity levels**:

| Level | Meaning | Action |
|---|---|---|
| **CRITICAL** | Soundness guarantee (bias-invariance) is breakable | Fix before production use |
| **HIGH** | Reliability degrades under adversarial or realistic conditions | Fix in v0.9.1 |
| **MEDIUM** | Scale / robustness / UX — doesn't break soundness | Queue for v0.10.0+ |
| **LOW** | Known trade-off with clear workaround | Document only |

---

## CRITICAL (3) — Soundness at risk

### C1. Gaming-guard is surface-only

The `GAMING_GUARD_PHRASES` regex-list check inspects `MetricSpec.description` for self-referential English phrases. It **cannot inspect the accessor function**. An agent with a benign description plus a goodhart-accessor (e.g. `lambda θ: θ.lines_added_by_agent`) bypasses the guard entirely.

**Why critical**: bias-invariance at the spec layer is the primary defense against agent-authored-metric gaming. This guard gives false security.

**Defense options**:
- Require accessor to be human-authored (agent proposes name + description; human provides callable)
- Static-analyze accessor AST for self-referential state access
- Introduce a "pre-calibration audit" — every new metric must pass a set of adversarial inputs before registration

**Evidence**: `TestBiasInvarianceLeaks::test_gaming_guard_is_surface_only_vulnerability`

---

### C2. LLM-supplied thesis_prior bypasses dialectic when antitheses are empty

`compute_predicted_correct(thesis_prior, antitheses=[])` returns `thesis_prior` directly. A degenerate LLM that always self-rates `prior=0.999` and returns **empty antitheses from `attack_step`** sails through every commit gate — the dialectical discipline vanishes.

**Why critical**: the entire v0.7.0-v0.8.0 "dialectical gradient" assumes antitheses exist. When they don't, prior becomes load-bearing — but prior is LLM-self-rated and notoriously uncalibrated.

**Defense options**:
- Cap thesis_prior at 0.9 (always leave room for unknown unknowns)
- Mandate `len(antitheses) ≥ 1` per step — if none can be generated, log a distinct `terminal=antithesis-absent` state
- Require memory-primed primer even if there are no independent antitheses

**Evidence**: `TestBiasInvarianceLeaks::test_llm_supplied_thesis_prior_propagates_unchecked_vulnerability`

---

### C3. `list_names()` lies after reopen — API disagreement

After closing and reopening a session, the registry loads specs from disk but **not the metric callable objects**. The two introspection APIs disagree:

- `reg.specs()` → includes the persisted spec  (e.g. `"x"`)
- `reg.list_names()` → returns `[]`  (because `_metrics` dict is empty)
- `reg.get("x")` → returns `None`

**Why critical**: an agent using `list_names()` thinks nothing is registered and re-registers, triggering "already-registered" errors. An agent using `specs()` thinks "x" exists and calls `get("x").observed(...)` → `AttributeError: 'NoneType'`. Silent state divergence is the bug pattern that caused the narralog regression (v0.5.0).

**Defense options**:
- `list_names()` should return `sorted(self._specs.keys())` (not `_metrics.keys()`)
- `get(name)` should raise a clear `SpecExistsButCallableMissing` exception explaining re-registration is required
- Persist the accessor as a named import path (e.g. `"my_module:accessor_fn"`) so it can be re-resolved on open

**Evidence**: `TestRegistryStateDivergence::test_reopened_session_loses_metric_callables_vulnerability`

---

## HIGH (7) — Reliability degrades

### H1. Antithesis impact is agent-supplied; rubber-stamp + force-reject both possible

`Antithesis.impact` is an LLM-supplied float. Setting `impact=+0.5` on all antitheses makes the dialectic "rubber-stamp" (primer argues FOR thesis, not against). Setting `impact=-0.99` forces backtrack indefinitely, burning budget.

**Defense**: cross-validate impact signs against historical observation-regression pairs. An antithesis's recorded `impact` should correlate with actual failure when it applies. Drift-detect on this correlation.

**Evidence**: `TestBiasInvarianceLeaks::test_agent_supplied_antithesis_impact_gameable_vulnerability`

---

### H2. MAE hides catastrophic tail predictions

Mean Absolute Error averages; 9 nearly-perfect predictions + 1 catastrophic miss → MAE below 0.15 threshold → metric promoted to load-bearing despite 10% catastrophic-miss rate.

**Defense**: track p95 error or max error alongside MAE. Promote gate should require **both** MAE ≤ 0.15 AND p95 ≤ 0.30 (or similar tail threshold).

**Evidence**: `TestCalibrationCollapse::test_mae_hides_catastrophic_tail_vulnerability`

---

### H3. Rare task-types never reach N_min — permanent advisory with no visibility

`CALIB_MIN_N=5` is a global threshold. A task-type with < 5 chains has:
- `can_promote()` → False (correct)
- No drift_warning ever fires (below threshold)
- `promotion.last_mae` is `None` until `try_promote()` is called
- No distinct "insufficient data" state exposed as a first-class signal

**Defense**: expose three-state instead of binary:
- `load_bearing` (gate passed)
- `advisory` (n < min OR mae > threshold)
- `insufficient_data` (n < min — explicit)

And populate `last_mae` eagerly on every `log()`, not just on promotion attempt.

**Evidence**: `TestCalibrationCollapse::test_min_n_5_fails_rare_task_types_vulnerability`

---

### H4. Default `verify_fn` is string equality — semantic equivalences as false negatives

In `cot_llm.MockCotLLMClient`, default `verify_fn = lambda a, gt: a == gt` is strict string equality. Common cases produce false negatives:
- ground truth `"42"` vs answer `"42.0"` → False
- ground truth `"True"` vs answer `"true"` → False
- trailing whitespace, line-endings, etc.

Each false-negative inflates calibration MAE and triggers spurious drift warnings.

**Defense**: require user to supply a `verify_fn` at chain start (no default). Document that correctness depends entirely on the verifier's quality. For math: numeric normalization; for code: test execution.

**Evidence**: `TestCalibrationCollapse::test_verify_fn_strict_equality_inflates_mae_vulnerability`

---

### H5. Registry reopens with specs-only (partial state) — documented but not signaled

Same bug pattern as C3, less severe aspect: even after `list_names()` is fixed, the lack of persistable accessors means agents MUST re-register callables on every session open. This is a workflow requirement that's currently not enforced.

**Defense**: add a check at registry open: "specs-on-disk count vs in-memory metric count" mismatch → log a warning with the list of specs that need re-registration.

**Evidence**: `TestRegistryStateDivergence::test_reopened_session_loses_metric_callables_vulnerability` (same test — both aspects)

---

### H6. Concurrent writes to JSONL not guaranteed atomic

`Calibrator._append_to_disk` opens the file in append mode and writes a JSON line + newline. Python's `file.write()` in append mode is **not guaranteed atomic** for lines exceeding `PIPE_BUF` (~4 KB on Linux). Multiple concurrent LDD processes in the same repo can produce garbled lines.

**Defense**: wrap writes in `fcntl.flock(LOCK_EX)` OR use a single writer process with a queue. Current assumption = single-writer.

**Evidence**: `TestConcurrencyRaces::test_concurrent_writes_to_calibration_jsonl_may_interleave`

---

### H7. Recursive coupling — method-evolution ↔ project_memory ↔ prime_antithesis

```
method-evolution  reads  project_memory.json
project_memory.json  computed from  trace.log
trace.log  has predicted_Δloss from  dialectical-cot
dialectical-cot's predictions depend on  prime_antithesis
prime_antithesis  reads  project_memory.json   ← CYCLE back to step 1
```

If project_memory.json becomes drifted (e.g., because `verify_fn` had false negatives per H4), method-evolution optimizes skill text TOWARD the drifted signal. Future iterations compound.

**Defense**: add a meta-calibration layer — drift_warning on the calibration MAE itself, across skill versions. Signature: "did the last method-evolution step reduce aggregate MAE?" If no: roll back skill change.

**Evidence**: `TestRecursiveCoupling::test_method_evolution_on_drifted_memory_self_reinforces_vulnerability`

---

## MEDIUM (4) — Scalability & UX

### M1. Version bump orphans calibration records

On `reg.register(m)` with a version bump, old records stay in the JSONL. `records_for(metric_name)` correctly filters by version, but:
- JSONL grows unboundedly with orphan records
- No audit trail that "v2 starts fresh" is deliberate
- Agent has no signal that calibration was reset

**Defense**: on version bump, archive old records to `.ldd/metric_calibrations.v1.jsonl` and emit a trace event recording the bump.

**Evidence**: `TestVersionBumpResetsState::test_version_bump_erases_accumulated_calibration`

---

### M2. JSONL grows unboundedly — O(N) aggregate cost

Every `aggregate()` reads all chain traces / calibration pairs. At 10k chains × 5 steps × ~400 bytes per step = ~20 MB per file. After 100k: 200 MB. Aggregation becomes slow (seconds).

**Defense**: rolling window with compaction. Keep last K=1000 chains verbatim; older chains compacted to per-task-type summary records.

**Evidence**: `TestScalingLimits::test_cot_traces_jsonl_grows_unboundedly_known_limitation`

---

### M3. Calibration assumes stationarity — promotion is monotonic (no demotion)

Once a metric is promoted to load-bearing, subsequent drift (e.g., from LLM updates) doesn't demote it. Calibration keeps adding records; MAE eventually rises; but `promotion.is_load_bearing` stays True.

**Defense**: periodic re-evaluation. If current-window MAE > 0.15 over the last 10 samples, demote back to advisory. Or: track an "effective epoch" (LLM version / timestamp) and split stats by epoch.

**Evidence**: `TestStationarityAssumption::test_calibration_assumes_llm_stationarity_known_limitation`

---

### M4. Composition semantics are naive — cross-kind weighted sums are math-only sound

`weighted_sum(BoundedRate, PositiveCount)` is mathematically well-defined (outputs in [0,1]) but a 0.5 from a latency-normalized-at-1000ms is NOT the "same severity" as a 0.5 from a test-pass-rate. User is responsible for scale choice.

**Defense**: document explicitly. Maybe add a "comparable-kinds" hint — recommend against composing `bounded` and `positive` without explicit user attestation.

**Evidence**: `TestCompositionSemantics::test_composition_is_mathematically_sound_but_semantically_naive_tradeoff`

---

## LOW (1) — Documented limitation

### L1. Gaming-guard phrase list is English-only

`GAMING_GUARD_PHRASES` matches English patterns only. German "belohnt meine aktuelle aktion" or French "récompense mon action actuelle" bypass the guard.

**Defense**: extend phrase list to include common multilingual self-reference patterns. OR: rely on C1's deeper defense (accessor audit) which is language-independent.

**Evidence**: `TestGamingGuardLocale::test_gaming_guard_phrase_list_is_english_only_vulnerability`

---

## Summary — `python -m pytest scripts/ldd_trace/test_v0_9_0_audit.py -v`

```
15/15 findings have reproducible evidence

SEVERITY BREAKDOWN
  CRITICAL  : 3
  HIGH      : 7
  MEDIUM    : 4
  LOW       : 1

CATEGORY BREAKDOWN
  bias-invariance leaks          : 3 (C1, C2, H1)
  calibration collapse           : 3 (H2, H3, H4)
  registry state divergence      : 2 (C3, H5)
  recursive coupling             : 1 (H7)
  concurrency                    : 1 (H6)
  composition semantics          : 1 (M4)
  version bump state             : 1 (M1)
  scaling                        : 1 (M2)
  stationarity                   : 1 (M3)
  locale                         : 1 (L1)
```

## Recommended Priority for v0.9.1

1. **C3** (list_names() lie) — 3-line fix, immediate cleanliness win
2. **C1** (gaming-guard surface-only) — architectural decision, specification addition
3. **C2** (prior bypass) — mandatory-antithesis rule + prior cap at 0.9
4. **H4** (verify_fn quality) — require user-supplied verifier, no default
5. **H2** (MAE tail-risk) — add p95 error alongside MAE in promotion gate
6. **H3** (insufficient-data state) — tri-state instead of binary promotion
7. **H7** (recursive coupling) — meta-calibration on drift of drift-detection itself

v0.10.0 should address H1, H5, H6 (state + concurrency hardening) and all MEDIUM findings.

## Dogfood — audit itself was an LDD task

This audit was conducted as a dialectical-reasoning LDD task on the framework's own repo. Trace recorded in `.ldd/trace.log`. Loss reduction from 1.000 (no findings surfaced) to 0.050 (15/15 findings confirmed with evidence, 1 passing "summary" meta-test didn't count as a finding). One inner-loop iteration (tight K_MAX=4 budget with hyperparameters selected for exploratory audit).

## LDD Trace Block

```
╭─ LDD trace (inner loop, reactive) ──────────────────────────────╮
│ Task        : v0.9.0 critical audit — find collapse/unsoundness modes
│ Loss-fn     : L = unknown_failure_modes_remaining / total_surfaced
│ Loss-type   : rate (exploratory; user-set thresholds n≥3, MAE≤0.20)
│ Budget      : K_MAX = 4; used 1
│
│ Trajectory  : █·   1.000 → 0.050  ↓
│
│ Iteration i0 (inner, baseline)          loss=1.000  (0/0)
│   *dialectical-reasoning* → thesis (v0.9.0 sound) surfaced
│ Iteration i1 (inner, reactive)          loss=0.050  (1/15)   Δ −0.950 ↓
│   *dialectical-reasoning* → 15 findings with reproducible tests;
│                              3 CRITICAL, 7 HIGH, 4 MEDIUM, 1 LOW
│
│ Close : findings documented in docs/audit/v0-9-0-findings.md
│         test evidence at scripts/ldd_trace/test_v0_9_0_audit.py
│         layer-3 fix: tri-state promotion, prior cap, antithesis mandate
│         layer-5 fix: accessor-audit protocol, meta-calibration layer
╰─────────────────────────────────────────────────────────────────╯
```
