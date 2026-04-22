---
name: dialectical-cot
description: Use when a reasoning task requires a multi-step Chain-of-Thought (CoT) AND the task is verifiable (grounded answer, testable code, derivable proof). Forbids greedy step-by-step commitment — every step in the chain goes through thesis/antithesis/synthesis BEFORE entering the chain, using memory-primed antitheses to attack the proposed step. Produces a calibrated predicted-correctness per step and per chain. Applies SGD-on-thoughts in the same way `dialectical-reasoning` applies SGD-on-actions.
---

# Dialectical-CoT — the fourth axis of [Gradient Descent for Agents](./theory.md)

## The Metaphor

**The mountain climber who probes every step before committing weight.** Standard CoT is the reckless climber: each step is the locally-most-plausible direction, full weight committed, no second thought. One bad step cascades into a slide down the slope. The dialectical climber has a different rhythm: *probe the ground with a stick* (thesis), *listen for the hollow echo* (antithesis — does the rock sound solid?), *shift weight only after the echo confirms* (synthesis). If the echo is ambiguous, the climber backtracks or pivots. The chain of steps still reaches the summit — more slowly, but without the slides.

A climber without the probe-listen-commit rhythm is not faster than one with it. She just *falls more often* and is only visibly faster on the paths that happen not to have hollow spots. Complex reasoning tasks have many hollow spots.

## Overview

**This skill is the fourth gradient.** Inner-loop skills (`reproducibility-first`, `root-cause-by-layer`, `loss-backprop-lens`, `e2e-driven-iteration`) compute `∂L/∂code`. [`iterative-refinement`](./iterative-refinement.md) computes `∂L/∂output`. [`method-evolution`](./method-evolution.md) computes `∂L/∂method`. This skill — `dialectical-cot` — computes **`∂L/∂thought`**: the parameter is the reasoning chain itself, and the loss is per-step dialectical-synthesis error measured against ground truth. Same discipline (thesis / antithesis / synthesis / calibration) as every other LDD gradient, applied to a different parameter space.

A Chain-of-Thought (CoT) is a trajectory in reasoning-space: `t_0 → t_1 → ... → t_N` where each `t_k` is the partial reasoning state after step `k`. Standard CoT is greedy-SGD on this trajectory — each step maximizes local plausibility, no gradient-check.

Dialectical-CoT applies the LDD quantitative-dialectic protocol at *every step* in the chain. Each step:

1. **Thesis** — the LLM proposes the next reasoning move + a `predicted_step_correctness`
2. **Antithesis** — primers from chain memory + forced-independent counter-cases probe orthogonal failure modes
3. **Synthesis** — computes `E[step correct] = 1 − Σ Pr(antithesis applies) × impact(antithesis)`
4. **Decision** — commit if `E[step correct] ≥ threshold`; revise if below; backtrack if fundamentally different branch dominates
5. **Log** — step-level trace for chain-level calibration; aggregator learns per-task-type patterns

This is how "gradient via dialectic" applied to actions becomes applicable to *thoughts*: the synthesis step produces a number the agent can act on and that can be validated post-hoc against ground truth.

## When to Use

Apply when **all** of:

- Task requires **≥ 3 reasoning steps** (trivial one-shot tasks don't benefit)
- Task is **verifiable** (math with known answer, code with tests, proof with formal checker, logic puzzle with ground truth) — without verifiability, calibration cannot close
- Budget tolerates **3–5× token cost** vs. greedy CoT
- Task domain has an **external antithesis source** (memory of prior failures, domain-specific common-error catalog, or a second-LLM adversary) — pure self-attack invites groupthink

## When NOT to Use

- Single-step tasks ("translate this", "summarize that") — dialectic overhead not worth it
- Unverifiable / subjective tasks (creative writing, opinion analysis, stylistic refactors) — the calibration loop has no anchor
- Ultra-low-latency contexts (real-time agents, interactive UIs) — the 3–5× latency is load-bearing
- Tasks where the LLM is the only antithesis source AND memory has < 5 similar completed chains — primers are empty, groupthink dominates

## The Chain Protocol

For a task `T` with target length `max_steps`, initialize `chain = []` and iterate:

```
for k = 0 ... max_steps:
    # Step 1 — Thesis
    thesis = llm.propose_step(T, chain)
    # The LLM emits: the proposed next reasoning move + its self-rated correctness prior
    # predicted_step_correctness_prior = llm.estimate(step=thesis | chain)

    # Step 2 — Antithesis (primed)
    primers = ldd_trace.prime_antithesis(
        thesis=thesis,
        context=chain,                  # chain-so-far feeds memory retrieval
        task_type=detected_task_type    # primes from per-task-type failure modes
    )
    independent = llm.attack_step(thesis, skip_primers=True)
    # forced: at least ONE antithesis NOT sourced from primers (anti-groupthink)
    antitheses = primers + independent

    # Step 3 — Synthesis
    # E[step correct] = 1 − Σ Pr_i × impact_i + remainder × thesis_prior
    predicted_correct = quant_synthesis(thesis, antitheses)

    # Step 4 — Decision
    if predicted_correct >= 0.7:        # commit threshold (calibratable)
        synthesis = thesis               # or lightly-revised if antithesis forced a narrowing
        chain.append(Step(k, thesis, antitheses, synthesis, predicted_correct, "commit"))
    elif predicted_correct >= 0.4:       # revise
        synthesis = llm.revise(thesis, antitheses)
        chain.append(Step(k, thesis, antitheses, synthesis, predicted_correct, "revise"))
    else:                                # reject → backtrack or pivot
        backtrack_to = find_branch_point(chain, antitheses)
        chain = chain[:backtrack_to]
        continue                          # retry from earlier state

    # Step 5 — Log
    cot_trace.append_step(...)            # for aggregator

    if llm.is_answer_reached(chain):
        break

# Chain-level calibration
predicted_chain_correct = ∏ step.predicted_correct for step in chain
actual_correct = verify(chain.final_answer, ground_truth)
cot_trace.log_outcome(predicted_chain_correct, actual_correct)
```

### Step-level decision thresholds (calibratable, not magic)

| `E[step correct]` | Decision | Action |
|---|---|---|
| `≥ 0.7` | **commit** | append thesis to chain as-is |
| `0.4 – 0.7` | **revise** | synthesize a narrower version addressing the antitheses |
| `< 0.4` | **reject / backtrack** | step is structurally bad; return to an earlier chain state |

Thresholds are defaults. They ARE themselves calibratable via the outer loop — if `drift_warning` fires on the chain-level calibration (predicted ≠ observed), the thresholds are the first thing to examine.

## Memory Integration — per-task-type priming

Dialectical-CoT extends LDD's project memory with a **task-type-aware layer** (`.ldd/cot_memory.json`):

- `step_effectiveness_by_type[task_type][step_type]` — historical success rate per (task_type, step_type) pair (e.g., for `task_type=math`, `step_type=algebraic_manipulation` might have 0.85 success rate; `step_type=numeric_approximation` might have 0.52)
- `common_failure_modes[task_type]` — top-N failure patterns observed in prior chains of the same type (e.g., `math` commonly fails via `off_by_one`, `sign_error`, `unit_confusion`)
- `calibration[task_type]` — MAE of predicted vs actual chain correctness per task-type; `drift_warning: true` if `MAE > 0.15` over `n ≥ 5`

The `prime-antithesis` tool is extended to accept `--task-type` and `--chain-context` — it now surfaces:

1. **Step-effectiveness primers**: "this step type has 0.52 success rate in math chains — what failure mode is most likely here?"
2. **Failure-mode primers**: "last 3 chains of this type failed via `sign_error` — is this step susceptible?"
3. **Calibration primers**: "the predicted-correctness estimator drifts by 0.2 in this task type — your confidence may be inflated"

## Bias Invariance — Load-Bearing

The dialectical-CoT layer MUST satisfy:

$$
\forall \text{chain}, \text{ground\_truth} : L(\text{chain}, \text{gt}) \text{ is determined by } \text{gt} \text{ alone}
$$

In plain terms:

- **Memory cannot turn an incorrect chain into a correct one**. The final answer is verified against external ground truth; no primer/memory/synthesis modifies that verification.
- **Antitheses are evidence, not gates**. They influence WHICH chain gets constructed; they do not change WHAT answers are graded correct.
- **Calibration adjusts predictions, not outcomes**. Post-hoc drift detection changes the threshold for commit/revise/reject; it does NOT relabel past answers.
- **No cross-task-type contamination**. Memory is per-(project, task-type); primers for math tasks never feed code-generation chains. Signal-mixing risk.

The test module `test_cot.py::TestBiasInvariance` enforces this at code level — the verify-correctness function is isolated from memory; any memory-modification path that reaches it is a test failure.

## Cost Model

| Standard CoT | Dialectical-CoT (without backtrack) | Dialectical-CoT (with backtracks) |
|---|---|---|
| `N` LLM calls | `~3N` LLM calls | `~3N + b × (steps to backtrack point)` where `b` = backtrack count |

For `N=10` and `b=2` backtracks of 3 steps each: `30 + 6 = 36` calls vs 10 for greedy. **3.6× cost.**

Break-even condition: dialectical-CoT is cheaper than greedy-CoT-with-retry when:

$$
\text{dial\_success\_rate} \cdot \text{dial\_cost} < \text{greedy\_success\_rate} \cdot \text{greedy\_cost\_per\_try} + (1 - \text{greedy\_success\_rate}) \cdot \text{retry\_cost\_amortized}
$$

Empirically: if greedy CoT has < 70% success on a task type, dialectical-CoT likely net-saves tokens via fewer retries. Above 85% greedy success, it doesn't pay.

## Red Flags — STOP, the protocol is degrading

- "I'll skip antithesis on this step, it looks obvious" → *"looks obvious"* is exactly when confirmation bias is strongest; antithesis IS the confirmation-bias guard
- "Synthesis is cosmetic — let's just run thesis" → v0.7.0 applies: without a computed `E[step correct]`, the step isn't dialectical; it's rationalized
- "Memory has no primers, skip them" → correct action is **no primers + force ≥ 1 independent antithesis**, not skip the antithesis altogether
- "Backtracking takes too long, let me continue on this branch and hope" → greedy-recovery; if `E[step correct] < 0.4` there is structural evidence the branch is wrong; hope is not a strategy
- "Ground truth isn't available, I'll calibrate on plausibility" → that IS the moving-target-loss trap; without external ground truth, dialectical-CoT's calibration loop is unanchored — USE greedy CoT instead
- "3–5× cost is too high, let me do dialectical only on 'hard' steps" → adaptive dialectic is fine AS LONG AS the classifier deciding "hard" vs "easy" is itself calibrated; otherwise you'll skip dialectic exactly where it was needed

## Worked Example — Math Word Problem

Task: "A train leaves A at 10:00 travelling 60 km/h; another leaves B at 10:30 travelling 90 km/h. A and B are 300 km apart. When and where do they meet?" (Ground truth: 12:00 at 120 km from A.)

```
[Memory context — task_type=math, from project_memory.json]
  step_effectiveness[math][setup_equation]     = 0.88 (n=12)
  step_effectiveness[math][unit_conversion]    = 0.71 (n=9)
  common_failure_modes[math] = [off_by_half_hour, sign_error, wrong_reference_frame]

--- Step 1 ---
Thesis: "Let t = time after 10:00 when they meet. Train A's position = 60·t.
         Train B's position = 300 − 90·(t − 0.5)."
predicted_prior = 0.85

Primers from memory:
  [common_failure_modes/off_by_half_hour] — is the 0.5h offset correctly applied to B only?
  [step_effectiveness/unit_conversion=0.71] — are the units (km, h) consistent?
Independent antithesis:
  What if trains are moving in same direction?

Synthesis:
  Primer 1: correctly applied (B starts 0.5h later). Pr=0.15, impact=0 (no bug found).
  Primer 2: units consistent (km·h→km). Pr=0.10, impact=0.
  Independent: problem says "A to B 300 km apart" → opposite direction. Pr=0.05, impact=−0.3 (rule out).
  E[step correct] = 0.85 × (1 − 0.30) + 0 = 0.85 (no change)
  → COMMIT.

--- Step 2 ---
Thesis: "Setting positions equal: 60t = 300 − 90(t − 0.5). Solve for t."
predicted_prior = 0.90

Primers: [off_by_half_hour] — is the '−0.5' on the correct train?
Independent: is the '=' correctly applied?

Synthesis: equation is correctly set up; predicted_correct = 0.90.
  → COMMIT.

--- Step 3 ---
Thesis: "60t + 90t − 45 = 300  ⟹  150t = 345  ⟹  t = 2.3 hours"
predicted_prior = 0.88

Primers: [sign_error] — the '−45' comes from distributing '+90' × '−0.5'. Sign?
Independent: is 2.3 plausible (trains meet 2.3h after 10:00 = 12:18)?

Synthesis:
  Primer (sign): +90·(−0.5) = −45 ✓ correct
  Independent: 2.3 × 60 = 138 km (train A position). Plausible but let's double-check.
  E[step correct] = 0.88 → COMMIT.

--- Step 4 ---
Thesis: "Meeting time = 12:18. Position = 60 × 2.3 = 138 km from A."
predicted_prior = 0.88

[Verify: expected answer is 12:00 at 120 km. Our chain got 12:18 at 138 km. WRONG.]
```

### Post-chain calibration

```
predicted_chain_correct = 0.85 × 0.90 × 0.88 × 0.88 ≈ 0.59
actual_correct = False (wrong answer)
log: cot_traces.jsonl → calibration_error for this chain
```

After N=5 similar chains: aggregator emits `math.calibration.MAE=0.28` → `drift_warning`. Agent sees: "predicted-correctness estimator for math chains is inflated by ~0.28; either tighten the threshold or invoke `method-evolution` on the step-evaluator skill."

The chain got a wrong answer (in this case because the setup equation had a subtle error — `90(t − 0.5)` should be `90(t − 0.5)` IFF B starts later, but the sign of the displacement needs the reference direction). Dialectical-CoT *didn't catch it* this time — but the calibration loop now knows the predictor is over-confident for this class of problem, and next time will lower the threshold or re-examine the step-evaluator.

The key insight: dialectical-CoT doesn't *guarantee* correctness. It *makes errors visible in the calibration layer* so the protocol itself can evolve.

## Hard Rules

1. **Every step in every non-trivial chain goes through the 5-step protocol**. Skipping on "obvious" steps is the canonical failure mode.
2. **≥ 1 antithesis per step must be independent of memory primers** (anti-groupthink).
3. **`predicted_step_correctness` must be computed, not hand-waved**. If you can't put a number on it, you're not applying this skill.
4. **Ground truth verification runs unchanged**. No memory, no primer, no synthesis modifies the external correctness check.
5. **Calibration is mandatory post-chain**. `cot_trace.log_outcome(predicted, actual)` — without this, future chains can't learn.
6. **No cross-task-type priming**. Primers from `task_type=math` never feed a `task_type=code` chain.
7. **Backtracking is allowed but budget-capped**. `K_MAX_BACKTRACKS = 3` per chain; after that, terminate and log as `partial`.

## Relation to Prior Work

| Concept | Source | This skill's contribution |
|---|---|---|
| Chain of Thought | Wei et al. 2022 | Add per-step dialectical gate |
| Tree of Thoughts | Yao et al. 2023 | Dialectical branch selection, bias-invariant |
| Self-Consistency | Wang et al. 2022 | Orthogonal: self-consistency samples trajectories; dialectical refines each |
| Chain-of-Verification | Dhuliawala et al. 2023 | Extends: per-step (not only post-hoc) + calibration loop |
| Reasoning-as-Planning / MCTS | Hao et al. 2023 | Bias-invariance + memory-primed antithesis as search heuristic |
| v0.7.0 quantitative dialectic | LDD | Applied to CoT: same `E[Δloss]` synthesis, but step-wise |

## Tooling

- `python -m ldd_trace cot run --task "..." --task-type <type> --ground-truth "..."` — runs a dialectical-CoT on a task; logs to `.ldd/cot_traces.jsonl` and `.ldd/cot_memory.json`
- `python -m ldd_trace cot aggregate` — recompute per-task-type stats
- `python -m ldd_trace cot health` — show per-task-type effectiveness + calibration

See `scripts/ldd_trace/cot.py` for the harness, `scripts/ldd_trace/test_cot.py` for the protocol test cases, and `./theory.md` §3.12 for the theoretical framing.
