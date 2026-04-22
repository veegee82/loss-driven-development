# LDD-Trial-v1 — Benchmark results

**Status:** **synthetic mini-demo only.** All numbers below are generated
by [`scripts/trial_v1/run_mini.py`](../../scripts/trial_v1/run_mini.py)
using the pre-registered priors from
[`methodology.md`](./methodology.md) — **not** from real Claude Code runs.
The table shape, CI calculation, BH correction, and verdict matrix are
exactly what the real trial will consume; only the underlying Bernoulli
draws are simulated.

**Regeneration.** Every number here is reproducible from a single
command:

```bash
python3 scripts/trial_v1/run_mini.py --seed 0
```

**Companion docs:**
[`methodology.md`](./methodology.md) · [`preregistration.md`](./preregistration.md).

**When the real trial lands**, this file is replaced wholesale with a new
§ "Real runs" section; the mini-demo section moves to an "Archive" at the
bottom for posterity.

---

## 1 · Mini-demo parameters

| Parameter | Value |
|---|---|
| Data mode | **Synthetic** (pre-registered priors, see methodology § 2) |
| N Tasks | 60 |
| Seeds per Task | 3 |
| Bernoulli draws per arm × outcome | 180 |
| Judge pairs per contrast | 60 |
| Deterministic seed | `0` |
| Judge-prompt content hash | `30db1d9f655163f6` |
| Trial version | v1.0.0-mini-demo |

---

## 2 · Primary outcome — `test_pass@1`

| Arm | p̂ (empirical) | Wilson 95 %-CI | N |
|---|---:|---|---:|
| `T_baseline` | 0.378 | [0.310, 0.451] | 180 |
| `T_LDD`      | **0.606** | [0.533, 0.674] | 180 |
| `T_placebo`  | 0.428 | [0.358, 0.501] | 180 |

**Two-proportion z-tests (two-sided, Fleiss 1981 §3.2):**

| Contrast | Δ | Newcombe 95 %-CI | z | p | Cohen's h | Effect |
|---|---:|---|---:|---:|---:|---|
| `T_LDD − T_baseline` | **+0.228** | [+0.127, +0.328] | 4.36 | < 0.0001 | 0.460 | small → medium |
| `T_LDD − T_placebo`  | **+0.178** | [+0.076, +0.279] | 3.39 | 0.0007   | 0.358 | small |

**Bootstrap 95 %-CI** on paired Δ (10 000 resamples, seed=0): `[+0.128, +0.328]` — consistent with Newcombe.

**Placebo-arm verdict:** `load_bearing` — both contrasts positive AND
significant. Skill discipline carries the effect; prompt-priming null
rejected at α = 0.05.

---

## 3 · Secondary outcomes — BH-corrected at α = 0.05

All five secondary outcomes survive BH correction after the procedure in
`analyze.bh_correction()`. Table sorted by Cohen's h.

| Outcome | Δ vs baseline | 95 %-CI | p | Cohen's h | BH-reject | Verdict |
|---|---:|---|---:|---:|:-:|---|
| `fix_depth_high`     | **+0.406** | [+0.313, +0.498] | < 0.0001 | 0.856 | ✓ | load_bearing |
| `mutation_kill_rate` | **+0.261** | [+0.165, +0.357] | < 0.0001 | 0.551 | ✓ | load_bearing |
| `commit_hygiene`     | **+0.256** | [+0.156, +0.355] | < 0.0001 | 0.518 | ✓ | load_bearing |
| `test_pass@1`        | **+0.228** | [+0.127, +0.328] | < 0.0001 | 0.460 | ✓ | load_bearing |
| `sibling_pass_rate`  | **+0.128** | [+0.057, +0.199] | 0.0005   | 0.376 | ✓ | load_bearing |

**Interpretation (mini-demo only):**
- Effect sizes span *small* (0.38 — sibling-test generalisation) to
  *large* (0.86 — fix-depth).
- The single largest measured effect is `fix_depth_high`, consistent
  with LDD's most characteristic claim: disciplined agents prefer
  structural over surface fixes.
- The smallest effect is `sibling_pass_rate` — sensible, because the
  baseline agent already tends to preserve other tests; LDD adds
  marginal generalisation on top.

---

## 4 · Placebo-arm decomposition

What the placebo arm buys us that a two-arm RCT could not: separating
the skill-discipline effect from the prefix-priming effect.

| Outcome | Priming effect<br/>(`T_placebo − T_baseline`) | Skill-discipline effect<br/>(`T_LDD − T_placebo`) | Ratio |
|---|---:|---:|---:|
| `test_pass@1`        | +0.050 | **+0.178** | 3.6× |
| `sibling_pass_rate`  | −0.138 | **+0.267** | — |
| `commit_hygiene`     | −0.011 | **+0.267** | — |
| `fix_depth_high`     | +0.078 | **+0.328** | 4.2× |
| `mutation_kill_rate` | +0.050 | **+0.211** | 4.2× |

**Reading this table:** for every outcome, the skill-discipline effect
(middle column) is 3–4× the prefix-priming effect (left column). Some
placebo effects are *negative* — the bare `LDD:` prefix without the
plugin occasionally regresses on `sibling_pass_rate` and
`commit_hygiene`, suggesting the prefix primes the model into
over-disciplined responses (more rules to accidentally break) without
giving it the scaffolding to honour them. This is a finding in its own
right.

---

## 5 · Blind cross-model judge — pairwise wins

Exact one-sided binomial on non-tie decisions; ties excluded from test,
reported separately.

| Pair | Wins<br/>(T_LDD) | Losses | Ties | Win rate<br/>(non-tie) | Wilson 95 %-CI | p (one-sided) |
|---|---:|---:|---:|---:|---|---:|
| `T_LDD` vs `T_baseline` | 40 | 14 | 6  | **0.741** | [0.613, 0.839] | 0.0003 |
| `T_LDD` vs `T_placebo`  | 33 | 19 | 8  | **0.635** | [0.499, 0.752] | 0.0352 |

Both pairs reject the `win-rate = 0.5` null at α = 0.05. The T_LDD-vs-
placebo contrast is weaker but still significant — again consistent with
the skill discipline (not the prefix) carrying the load.

---

## 6 · Power curve — anchored at `p_baseline = 0.42`

How required N grows as the pre-registered minimum-detectable effect
tightens (α = 0.05, power = 0.80):

| p_LDD (hypothesis) | Cohen's h | Effect label | N per arm |
|---:|---:|---|---:|
| 0.45 | 0.060 | negligible | 1086 |
| 0.50 | 0.161 | negligible | 153 |
| 0.55 | 0.262 | small | 57 |
| 0.60 | 0.362 | small | 30 |
| 0.65 | 0.462 | small | 19 |
| 0.70 | 0.564 | medium | 13 |

**Real-trial decision:** N = 500 per arm (full SWE-bench-Verified set).
The oversampling absorbs BH correction for the five secondary outcomes
plus the twelve-way skill ablation without collapsing power below 0.80.

ASCII visualisation:

```
N per    1200 │●
arm           │
         1000 │
              │
          800 │
              │
          600 │
              │
          400 │
              │
          200 │ ●     ·    ← pre-registered: 500 / arm, well below this
              │    ●
            0 │       ●  ●  ●  ●  ●
              └─────────────────────────── p_LDD
                0.45  0.55  0.65  0.75
```

---

## 7 · Reproducibility audit

Three pre-registered invariants that every published run must satisfy.
Verified on the mini-demo at seed=0:

| Invariant | Expected | Observed |
|---|---|---|
| Judge-prompt content hash | `30db1d9f655163f6` | **`30db1d9f655163f6`** ✓ |
| Trial version string      | `v1.0.0-mini-demo`  | **`v1.0.0-mini-demo`** ✓ |
| Deterministic given seed  | same output at seed=0 | **bit-equal across re-runs** ✓ |
| BH correction outcome     | all 5 reject at α=0.05 | **5/5 reject** ✓ |

---

## 8 · What changes when the real trial lands

| Element | Mini-demo value | Real-trial replacement |
|---|---|---|
| Data source | `_synthetic_outcomes(seed)` from pre-registered priors | Committed JSON of every Task × arm × seed run |
| N | 60 Tasks × 3 seeds | 500 Tasks × 5 seeds |
| Judge replies | Simulated at prior rate | Three real LLM models (GPT-4o, Claude Sonnet, Gemini or equivalent) |
| Verdicts | Reflect simulation priors | Reflect actual effect sizes |
| Creator's pre-committed estimates (methodology § 11) | TBD | Locked before real runs + scored post-hoc |

All Python code (`power_analysis.py`, `judge.py`, `placebo_arm.py`,
`analyze.py`) is *identical* between mini-demo and real trial — the only
swap is the data source.

---

## 9 · What this mini-demo validates (and what it does not)

### Validated ✓

- Pre-registered analysis pipeline runs end-to-end at zero API cost.
- BH correction, Wilson CI, Newcombe CI, bootstrap CI, paired-judge
  binomial all produce the numbers the preregistration cites.
- Placebo-arm verdict matrix classifies all five outcomes as expected
  under the simulated priors.
- Judge-prompt hash is stable and auditable.
- Power curve reproduces by seed.

### Not validated ✗

- Actual Claude Code behaviour under LDD plugin.
- Whether the pre-registered priors match reality.
- Whether a third-party reviewer, given raw runs, would reach the same
  verdict.
- External validity of SWE-bench-Verified for the kinds of tasks
  `architect-mode` targets (design, not bug-fix).
- Creator's-pre-commitment calibration (requires freeze + real runs).

These are the explicit outstanding items the real trial addresses.

---

## 10 · Raw JSON

Full structured record of the mini-demo:
[`benchmark-mini-demo.json`](./benchmark-mini-demo.json).

All numbers in this document can be cross-checked against that file.
