# LDD-Trial-v1 — Pre-Registration

**Pre-registration is a hard freeze.** What is committed below is what will
be measured, tested, and published — regardless of outcome. Any deviation
is reported as a protocol violation. Changes require a new version
(`v1.1.0`, etc.) and invalidate prior runs under this document.

**Version:** v1.0.0
**Registration commit hash:** *(to be filled at freeze time — see
`scripts/trial_v1/` at that commit)*
**Method details:** [`methodology.md`](./methodology.md)

---

## 1 · Research questions

| RQ | Question | Arm contrast |
|---|---|---|
| RQ1 | Does LDD improve `test_pass@1` on SWE-bench-Verified? | `T_LDD` vs `T_baseline` |
| RQ2 | Is the effect load-bearing on the skill discipline, or a pure prompt-priming artefact of the `LDD:` token? | `T_LDD` vs `T_placebo` |
| RQ3 | Which of the 12 LDD skills contributes most to the measured effect? | `T_LDD_−skill_k` vs `T_LDD` (leave-one-out) |

---

## 2 · Hypotheses

### Primary (RQ1)

$$
\begin{aligned}
H_0 &: p_{\text{T\_LDD}} = p_{\text{T\_baseline}} \\
H_1 &: p_{\text{T\_LDD}} \neq p_{\text{T\_baseline}}
\end{aligned}
$$

Two-sided. α = 0.05. Expected direction per LDD's claim: `p_LDD > p_baseline`.

### Placebo (RQ2)

$$
\begin{aligned}
H_0 &: p_{\text{T\_LDD}} = p_{\text{T\_placebo}} \\
H_1 &: p_{\text{T\_LDD}} > p_{\text{T\_placebo}}
\end{aligned}
$$

One-sided (pre-registered direction: LDD claim implies skill discipline
beats bare prefix). α = 0.05.

### Ablation (RQ3)

For each skill *k* ∈ {twelve LDD skills}:

$$
H_0^{(k)} : p_{\text{T\_LDD} - \text{skill}_k} = p_{\text{T\_LDD}}
$$

BH-corrected across the twelve tests, α = 0.05.

---

## 3 · Primary outcome

**`test_pass@1`** — for Task `T_i` and arm *a*:

$$
y_i^{(a)} = \mathbb{1}\!\left[\text{target-test}(T_i) \text{ passes on arm}\,a\text{'s first submission}\right]
$$

Unit of analysis: Task (500 in SWE-bench-Verified). Variance-reduction:
5 seeds per Task × arm → Task-level mean used in the z-test.

**Primary test:** two-proportion z-test (pooled variance, Fleiss 1981
§3.2). **Stratified by** programming language + difficulty bucket.

---

## 4 · Secondary outcomes

Pre-registered set of five — no additions permitted post-hoc.

| # | Name | Operationalisation | Test | Direction |
|---|---|---|---|---|
| 2 | `sibling_pass_rate` | `(other-module-tests passing after) / (... before)` | Two-proportion z, BH | Higher |
| 3 | `fix_depth_high` | Blind-judge classifies fix at layer ≥ 3 (out of 5) | Proportion z, BH | Higher |
| 4 | `commit_hygiene` | `(src + tests + docs)` present when layer ≥ 3 | Proportion z, BH | Higher |
| 5 | `mutation_kill_rate ≥ 0.75` | `mutmut` on the fix file; threshold pre-registered | Proportion z, BH | Higher |
| 6 | `revert_risk_30d` | `git revert` within 30 days on a landed fix | Proportion z, BH | Lower |

BH correction across the five at α = 0.05 via `analyze.bh_correction()`.

---

## 5 · Sample size + power

**Primary anchor:**

- `p_baseline = 0.42` (SWE-bench-Verified agent baseline reference)
- Minimum-detectable effect `ε = 0.15` (pre-registered claim-floor)
- α = 0.05 two-sided, power 1 − β = 0.80
- Required N ≈ 170 per arm (pooled-variance formula)

**Chosen N:** 500 Tasks × 3 arms × 5 seeds = 7 500 runs.
Substantial over-powering for the primary contrast → secondary outcomes
have > 0.80 power even after BH correction.

Power-curve table: see [`methodology.md`](./methodology.md) § 6.

---

## 6 · Arm definitions (exact)

| Arm | Plugin loaded | `LDD:` prefix | CLAUDE.md |
|---|---|---|---|
| `T_baseline` | **No** | **No** | Dummy (length-matched) |
| `T_LDD` | Yes | Yes | Real LDD CLAUDE.md |
| `T_placebo` | **No** | Yes | Dummy (length-matched) |

Dummy CLAUDE.md text: the exact byte-content produced by
[`scripts/trial_v1/placebo_arm.py`](../../scripts/trial_v1/placebo_arm.py)
§ `pad_claude_md_to_match()`.

---

## 7 · Randomisation

Block randomisation by difficulty bucket (easy / medium / hard), equal
allocation across the three arms. Seed for the assignment RNG committed
in `scripts/trial_v1/placebo_arm.py` at the registration hash. Integrity
hash per assignment row: `sha256(task_id|seed|arm|assigned_at)[:16]`.

Post-assignment re-labelling is detectable as a hash mismatch and is a
protocol violation if found.

---

## 8 · Blinding

- **Agent blinding:** not possible (the agent's config IS the treatment).
- **Judge blinding:** enforced. Judges receive only `task_description`,
  `diff_a`, `diff_b`, `target_test_output`. No arm labels, no
  `LDD:`-stripped prompts, no commit metadata.
- **Order blinding:** `A`/`B` order randomised per pair via a hash-seeded
  RNG, reversible only in the analysis step.
- **Analyser blinding:** the analyser does NOT read arm labels until all
  judge replies are received and committed.

---

## 9 · Pre-registered exclusion criteria

Any Task / Seed / Arm meeting **at least one** of the following is
dropped from analysis; exclusion rates are reported per arm and a
> 10 % difference in exclusion rate across arms invalidates the trial.

1. Agent crash without retry capability.
2. Wall-clock runtime > 10 minutes.
3. Target-test file not found in the post-run repo state.
4. Diff adds > 1 500 lines (excluded as agent overreach).
5. Submitted patch is empty or whitespace-only.
6. Judge reply cannot be parsed after one retry with the same prompt.

No exclusion may be added post-registration without bumping the version.

---

## 10 · Analysis plan — detail

```
PRIMARY
  for arm_pair in [(T_LDD, T_baseline), (T_LDD, T_placebo)]:
      stratified z-test on test_pass@1
      report: diff, Newcombe 95 %-CI, z, p, Cohen's h
  joint verdict via analyze.verdict()

SECONDARY
  for outcome in [sibling_pass, fix_depth_high, commit_hygiene,
                  mutation_kill_rate, revert_risk_30d]:
      z-test vs T_baseline
  BH correction across 5 outcomes, α = 0.05
  report per outcome: BH-reject / not, effect size, direction

JUDGE CASCADE
  for each of 3 models:
      exact one-sided binomial on non-tie pairs
      Wilson 95 %-CI on win-rate
  majority-vote aggregate across models
  Fleiss' κ across judges as sanity check

ABLATION (RQ3)
  for each of 12 skills:
      leave-one-out z-test
  BH correction across 12, α = 0.05
  rank skills by effect-size (Cohen's h)

DRIFT-UNDER-STRESS (supplementary)
  linear regression: loss ~ task_position within session
  compare slope(T_LDD) vs slope(T_baseline) via Welch's t
```

Implementation pinned at
[`scripts/trial_v1/analyze.py`](../../scripts/trial_v1/analyze.py) under
the registration commit. Any post-hoc analysis must be labelled
"exploratory" and presented separately.

---

## 11 · Creator's pre-committed point estimates

Published BEFORE the runs start. The author of LDD commits to these point
estimates + 95 %-CIs; any primary-outcome result that lands outside the
CI is recorded as a calibration miss in the final write-up. Purpose: make
overclaiming / underclaiming detectable at publication time.

| Outcome | Creator's point estimate | Creator's 95 %-CI |
|---|---|---|
| `test_pass@1` (T_LDD) | *(to be set before freeze)* | *(…)* |
| `diff(T_LDD − T_baseline)` | *(...)* | *(...)* |
| `diff(T_LDD − T_placebo)` | *(...)* | *(...)* |

---

## 12 · Open-science contract

The following are committed at freeze time, not at publication:

- Every raw run (prompt, tool calls, diff, test output, judge replies) in
  a single versioned dataset.
- Analysis code at a pinned commit hash.
- Judge prompt (system + user template) at a pinned commit hash —
  `judge.JUDGE_SYSTEM`-hash `30db1d9f655163f6` for v1.0.0.
- MDE curve + power-analysis parameters.
- Creator's pre-committed estimates + CIs from § 11.

All results — significant, null, negative — are published. The trial has
no exit ramp for a "disappointing" outcome.

---

## 13 · Timeline

| Milestone | Date commitment |
|---|---|
| v1.0.0 freeze | *(committed at document publication)* |
| Primary RCT runs complete | ≤ 2 weeks after freeze |
| Judge cascade complete | ≤ 3 weeks after freeze |
| Analysis + publication | ≤ 4 weeks after freeze |

Slippage is reported; silent delays are a protocol violation.

---

## 14 · Signatures

*(Signed off at freeze time; pre-registration holders — plugin author +
at least one adversarial collaborator from outside the author's team.)*

Adversarial collaborator: *TBD — one reviewer who has publicly expressed
scepticism about LDD's claims.*
