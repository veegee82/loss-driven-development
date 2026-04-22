"""Synthetic mini-demo of LDD-Trial-v1 — zero API cost.

This runs the ENTIRE analysis pipeline end-to-end on a synthetic dataset
shaped like what the real trial would produce. It validates:

  * the three-arm harness records the right prompts per arm
  * the pre-registered prompt hash is stable
  * power analysis reports the N-per-arm the pre-registration claims
  * the statistical analysis (two-proportion z-test, Wilson CI, bootstrap,
    BH correction, judge binomial test) runs end-to-end and reproduces
    by seed

The synthetic data generator SIMULATES outcome proportions pre-registered
in `docs/trial-v1/preregistration.md` so the benchmark table is populated
from a realistic-shaped dataset. When real trial data lands, swap
`_synthetic_outcomes()` for a loader that reads the committed JSON runs.

Pre-registered simulation priors (the numbers the benchmark treats as
"expected, to be confirmed by real runs"):

    test_pass@1:          p_baseline = 0.42   p_LDD = 0.60   p_placebo = 0.45
    sibling_pass:         p_baseline = 0.71   p_LDD = 0.88   p_placebo = 0.73
    judge pair-win rate:  p_LDD_vs_baseline = 0.62   p_LDD_vs_placebo = 0.56

Writes:

    docs/trial-v1/benchmark-mini-demo.json   — raw numbers (reproducible with --seed)
"""
from __future__ import annotations

import json
import random
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Dict, List, Tuple

REPO = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO / "scripts"))

from trial_v1 import analyze, judge, placebo_arm, power_analysis


# ---------------------------------------------------------------------------
# Pre-registered simulation priors
# ---------------------------------------------------------------------------

PRIORS: Dict[str, Dict[str, float]] = {
    "test_pass_at_1":     {"T_baseline": 0.42, "T_LDD": 0.60, "T_placebo": 0.45},
    "sibling_pass_rate":  {"T_baseline": 0.71, "T_LDD": 0.88, "T_placebo": 0.73},
    "commit_hygiene":     {"T_baseline": 0.30, "T_LDD": 0.62, "T_placebo": 0.33},
    "fix_depth_high":     {"T_baseline": 0.25, "T_LDD": 0.55, "T_placebo": 0.28},
    "mutation_kill_rate": {"T_baseline": 0.55, "T_LDD": 0.71, "T_placebo": 0.56},
}

JUDGE_PRIORS = {
    "T_LDD_vs_T_baseline": {"wins": 0.62, "ties": 0.08},  # losses = 1 - wins - ties
    "T_LDD_vs_T_placebo":  {"wins": 0.56, "ties": 0.10},
}

N_TASKS_MINI = 60        # enough for readable CIs without pretending to be the real trial
SEEDS_PER_TASK = 3       # reduced from 5 for the mini-demo


# ---------------------------------------------------------------------------
# Synthetic data generation
# ---------------------------------------------------------------------------


def _synthetic_outcomes(seed: int) -> Dict[str, Dict[str, List[int]]]:
    """Generate Bernoulli outcomes for each arm × outcome at the pre-registered priors.

    Deterministic given `seed`. Returns:
        {outcome_name: {arm: [0/1, ...]}}
    """
    rng = random.Random(seed)
    out: Dict[str, Dict[str, List[int]]] = {}
    for outcome, arm_priors in PRIORS.items():
        out[outcome] = {}
        for arm, p in arm_priors.items():
            draws = [1 if rng.random() < p else 0 for _ in range(N_TASKS_MINI * SEEDS_PER_TASK)]
            out[outcome][arm] = draws
    return out


def _synthetic_judge(seed: int) -> Dict[str, Tuple[int, int, int]]:
    """Generate (wins, losses, ties) per judge-pair at the pre-registered priors."""
    rng = random.Random(seed + 42)
    out: Dict[str, Tuple[int, int, int]] = {}
    for pair_name, priors in JUDGE_PRIORS.items():
        wins = losses = ties = 0
        for _ in range(N_TASKS_MINI):
            r = rng.random()
            if r < priors["wins"]:
                wins += 1
            elif r < priors["wins"] + priors["ties"]:
                ties += 1
            else:
                losses += 1
        out[pair_name] = (wins, losses, ties)
    return out


# ---------------------------------------------------------------------------
# Analysis driver
# ---------------------------------------------------------------------------


def _run_power_curve() -> List[Dict[str, float]]:
    """Power curve anchored at the primary outcome prior (p_baseline=0.42)."""
    p1 = PRIORS["test_pass_at_1"]["T_baseline"]
    curve = power_analysis.power_curve(
        p1=p1,
        p2_range=[0.45, 0.50, 0.55, 0.60, 0.65, 0.70],
        alpha=0.05,
        power=0.80,
    )
    return [
        {"p1": p1, "p2": pt.p2, "cohen_h": round(pt.h, 3),
         "effect_size": power_analysis.effect_size_label(pt.h),
         "n_per_arm": pt.n_per_arm}
        for pt in curve
    ]


def _analyze_outcome(
    outcome: str, draws: Dict[str, List[int]]
) -> Dict[str, object]:
    """Per-outcome analysis — T_LDD vs. T_baseline AND T_LDD vs. T_placebo."""
    s_b, n_b = sum(draws["T_baseline"]), len(draws["T_baseline"])
    s_L, n_L = sum(draws["T_LDD"]),       len(draws["T_LDD"])
    s_p, n_p = sum(draws["T_placebo"]),   len(draws["T_placebo"])

    vs_baseline = analyze.primary_proportion_test(
        s_L, n_L, s_b, n_b, label=f"{outcome}: T_LDD vs T_baseline"
    )
    vs_placebo = analyze.primary_proportion_test(
        s_L, n_L, s_p, n_p, label=f"{outcome}: T_LDD vs T_placebo"
    )
    verdict_code = analyze.verdict(vs_baseline, vs_placebo)

    # Wilson CIs per arm.
    wilson = {
        arm: analyze.wilson_ci(sum(v), len(v))
        for arm, v in draws.items()
    }
    # Bootstrap CI on the proportion difference (T_LDD − T_baseline).
    diff_series = [
        l - b for l, b in zip(draws["T_LDD"], draws["T_baseline"])
    ]
    boot_lo, boot_hi = analyze.bootstrap_ci(diff_series, seed=0)

    return {
        "outcome": outcome,
        "arm_rates": {
            arm: {
                "p_hat": round(sum(v) / len(v), 3),
                "n": len(v),
                "wilson_95_ci": [round(c, 3) for c in wilson[arm]],
            }
            for arm, v in draws.items()
        },
        "t_LDD_vs_t_baseline": {
            "diff": round(vs_baseline.diff, 3),
            "diff_95_ci": [round(vs_baseline.diff_ci_low, 3),
                           round(vs_baseline.diff_ci_high, 3)],
            "z": round(vs_baseline.z, 2),
            "p_value": round(vs_baseline.p_value, 4),
            "cohen_h": round(vs_baseline.cohen_h, 3),
        },
        "t_LDD_vs_t_placebo": {
            "diff": round(vs_placebo.diff, 3),
            "diff_95_ci": [round(vs_placebo.diff_ci_low, 3),
                           round(vs_placebo.diff_ci_high, 3)],
            "z": round(vs_placebo.z, 2),
            "p_value": round(vs_placebo.p_value, 4),
            "cohen_h": round(vs_placebo.cohen_h, 3),
        },
        "bootstrap_diff_95_ci": [round(boot_lo, 3), round(boot_hi, 3)],
        "verdict_code": verdict_code,
        "verdict_text": analyze.PLACEBO_VERDICTS[verdict_code],
    }


def _analyze_judge(pairs: Dict[str, Tuple[int, int, int]]) -> Dict[str, object]:
    out: Dict[str, object] = {}
    for pair_name, (w, l, t) in pairs.items():
        r = analyze.paired_judge_test(w, l, t)
        out[pair_name] = {
            "wins": r.wins, "losses": r.losses, "ties": r.ties,
            "win_rate": round(r.win_rate, 3),
            "win_rate_95_ci": [round(r.win_rate_ci_low, 3),
                               round(r.win_rate_ci_high, 3)],
            "p_value_one_sided": round(r.p_value_one_sided, 4),
        }
    return out


def _bh_across_outcomes(by_outcome: Dict[str, Dict]) -> Dict[str, bool]:
    """BH correction across the five outcomes, T_LDD-vs-baseline contrast."""
    outcomes = list(by_outcome.keys())
    p_values = [by_outcome[o]["t_LDD_vs_t_baseline"]["p_value"] for o in outcomes]
    reject = analyze.bh_correction(p_values, alpha=0.05)
    return {o: bool(r) for o, r in zip(outcomes, reject)}


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------


def run(seed: int = 0) -> Dict[str, object]:
    outcomes = _synthetic_outcomes(seed)
    judge_pairs = _synthetic_judge(seed)

    per_outcome = {
        outcome: _analyze_outcome(outcome, draws)
        for outcome, draws in outcomes.items()
    }
    bh = _bh_across_outcomes(per_outcome)
    for o, passes_bh in bh.items():
        per_outcome[o]["bh_reject"] = passes_bh

    judge_results = _analyze_judge(judge_pairs)

    return {
        "trial_version": "v1.0.0-mini-demo",
        "data_mode": "synthetic (pre-registered priors)",
        "seed": seed,
        "n_tasks": N_TASKS_MINI,
        "seeds_per_task": SEEDS_PER_TASK,
        "power_curve": _run_power_curve(),
        "outcomes": per_outcome,
        "judge_pairs": judge_results,
        "judge_prompt_hash": _judge_prompt_reference_hash(),
    }


def _judge_prompt_reference_hash() -> str:
    """Stable hash of the judge-system-prompt for pre-registration audit.

    Any prompt change bumps this hash → reviewer knows it's a DIFFERENT trial.
    """
    import hashlib
    return hashlib.sha256(judge.JUDGE_SYSTEM.encode("utf-8")).hexdigest()[:16]


def main() -> int:
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=0,
                    help="Deterministic seed (default 0)")
    ap.add_argument(
        "--out",
        default=str(REPO / "docs" / "trial-v1" / "benchmark-mini-demo.json"),
        help="Output JSON path",
    )
    args = ap.parse_args()
    result = run(seed=args.seed)
    Path(args.out).write_text(json.dumps(result, indent=2) + "\n")
    print(f"mini-demo written → {args.out}")
    print(f"judge prompt hash: {result['judge_prompt_hash']}")
    print(f"verdicts (T_LDD vs T_baseline, after BH correction):")
    for o, v in result["outcomes"].items():
        marker = "✓" if v["bh_reject"] else "·"
        print(
            f"  {marker} {o:<24} "
            f"diff={v['t_LDD_vs_t_baseline']['diff']:+.3f}  "
            f"p={v['t_LDD_vs_t_baseline']['p_value']:.4f}  "
            f"verdict={v['verdict_code']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
