"""Pre-registered analysis for LDD-Trial-v1.

Pure-Python (random + math stdlib). All tests + CIs produced here are
deterministic given a seed — reviewers can re-run from committed JSON to
reproduce every number in `docs/trial-v1/benchmark.md`.

Implemented tests (all pre-registered):

    primary_proportion_test    Two-proportion z-test (Fleiss 1981 §3.2),
                               pooled-variance form. Returns z, p, CI.
    wilson_ci                  Wilson score confidence interval for a
                               single proportion — robust near p∈{0,1}.
    bootstrap_ci               Nonparametric percentile bootstrap CI,
                               N_resamples=10 000 (pre-registered).
    cohen_h_from_counts        Arcsine effect size from raw counts.
    bh_correction              Benjamini–Hochberg multiple-comparison
                               adjustment for the five secondary outcomes.
    paired_judge_test          Binomial test on judge pair-wins, excluding
                               ties; returns exact p via the cumulative
                               binomial PMF.

No external dependencies so the whole trial is reproducible from git alone.
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass
from typing import List, Optional, Sequence


# ---------------------------------------------------------------------------
# Proportion CIs + two-proportion z-test
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ProportionResult:
    p_hat: float
    n: int
    ci_low: float
    ci_high: float
    label: str = ""

    def as_row(self) -> str:
        return (
            f"{self.label:<24}  "
            f"{self.p_hat:.3f}  "
            f"[{self.ci_low:.3f}, {self.ci_high:.3f}]  "
            f"(n={self.n})"
        )


def wilson_ci(successes: int, n: int, alpha: float = 0.05) -> tuple[float, float]:
    """Wilson score interval — preferred over normal-approx at p near 0/1."""
    if n == 0:
        return (0.0, 1.0)
    z = 1.9600 if abs(alpha - 0.05) < 1e-9 else _z_two_sided(alpha)
    p = successes / n
    denom = 1.0 + (z * z) / n
    centre = (p + (z * z) / (2 * n)) / denom
    halfwidth = (z / denom) * math.sqrt(p * (1 - p) / n + (z * z) / (4 * n * n))
    return (max(0.0, centre - halfwidth), min(1.0, centre + halfwidth))


def _z_two_sided(alpha: float) -> float:
    # Small fallback table; the trial only uses α=0.05.
    table = {0.01: 2.5758, 0.05: 1.9600, 0.10: 1.6449}
    return table.get(round(alpha, 4), 1.9600)


@dataclass(frozen=True)
class TwoProportionResult:
    p1: float
    p2: float
    n1: int
    n2: int
    z: float
    p_value: float
    diff: float
    diff_ci_low: float
    diff_ci_high: float
    cohen_h: float
    label: str = ""

    def significant(self, alpha: float = 0.05) -> bool:
        return self.p_value < alpha


def primary_proportion_test(
    s1: int, n1: int,
    s2: int, n2: int,
    alpha: float = 0.05,
    label: str = "",
) -> TwoProportionResult:
    """Two-sided two-proportion z-test with pooled variance.

    `s1/n1` is the treatment arm (T_LDD); `s2/n2` is the control arm
    (T_baseline). The sign of the returned `diff` and `z` is positive when
    T_LDD outperforms T_baseline.
    """
    p1 = s1 / n1 if n1 else 0.0
    p2 = s2 / n2 if n2 else 0.0
    if n1 == 0 or n2 == 0:
        return TwoProportionResult(
            p1, p2, n1, n2, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, label
        )
    p_pool = (s1 + s2) / (n1 + n2)
    se = math.sqrt(p_pool * (1 - p_pool) * (1.0 / n1 + 1.0 / n2))
    z = (p1 - p2) / se if se > 0 else 0.0
    p_value = 2.0 * (1.0 - _phi(abs(z)))
    # Unpooled SE for the CI on the difference (Newcombe 1998 method 10).
    se_unpooled = math.sqrt(
        (p1 * (1 - p1) / n1) + (p2 * (1 - p2) / n2)
    ) if n1 and n2 else 0.0
    z_half = _z_two_sided(alpha)
    diff = p1 - p2
    ci_low = diff - z_half * se_unpooled
    ci_high = diff + z_half * se_unpooled
    h = 2 * math.asin(math.sqrt(p1)) - 2 * math.asin(math.sqrt(p2))
    return TwoProportionResult(
        p1=p1, p2=p2, n1=n1, n2=n2, z=z, p_value=p_value,
        diff=diff, diff_ci_low=ci_low, diff_ci_high=ci_high,
        cohen_h=h, label=label,
    )


def _phi(z: float) -> float:
    """Standard-normal CDF via erf."""
    return 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))


def cohen_h_from_counts(s1: int, n1: int, s2: int, n2: int) -> float:
    if n1 == 0 or n2 == 0:
        return 0.0
    p1 = s1 / n1
    p2 = s2 / n2
    return 2 * math.asin(math.sqrt(p1)) - 2 * math.asin(math.sqrt(p2))


# ---------------------------------------------------------------------------
# Bootstrap CI
# ---------------------------------------------------------------------------


def bootstrap_ci(
    values: Sequence[float],
    statistic=lambda v: sum(v) / len(v) if v else 0.0,
    n_resamples: int = 10000,
    alpha: float = 0.05,
    seed: Optional[int] = 0,
) -> tuple[float, float]:
    """Percentile bootstrap CI; deterministic when `seed` is fixed."""
    if not values:
        return (0.0, 0.0)
    rng = random.Random(seed)
    n = len(values)
    resampled: List[float] = []
    for _ in range(n_resamples):
        sample = [values[rng.randrange(n)] for _ in range(n)]
        resampled.append(statistic(sample))
    resampled.sort()
    lo_idx = int((alpha / 2.0) * n_resamples)
    hi_idx = int((1.0 - alpha / 2.0) * n_resamples) - 1
    return (resampled[lo_idx], resampled[max(0, hi_idx)])


# ---------------------------------------------------------------------------
# Benjamini–Hochberg
# ---------------------------------------------------------------------------


def bh_correction(
    p_values: Sequence[float], alpha: float = 0.05,
) -> List[bool]:
    """BH procedure. Returns a bool per p-value: True = reject H0."""
    m = len(p_values)
    if m == 0:
        return []
    indexed = sorted(enumerate(p_values), key=lambda kv: kv[1])
    reject = [False] * m
    for rank, (orig_idx, p) in enumerate(indexed, start=1):
        threshold = rank / m * alpha
        if p <= threshold:
            for i in range(rank):
                reject[indexed[i][0]] = True
    return reject


# ---------------------------------------------------------------------------
# Judge-pair binomial test
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class JudgePairResult:
    wins: int           # times T_LDD patch was picked
    losses: int         # times T_baseline (or T_placebo) was picked
    ties: int
    p_value_one_sided: float
    win_rate: float
    win_rate_ci_low: float
    win_rate_ci_high: float


def paired_judge_test(wins: int, losses: int, ties: int) -> JudgePairResult:
    """Exact one-sided binomial test on the non-tie pairs only.

    Ties are excluded from the test (pre-registered) but reported alongside.
    Null: wins / (wins + losses) = 0.5. Alt: > 0.5.
    """
    n_decided = wins + losses
    if n_decided == 0:
        return JudgePairResult(wins, losses, ties, 1.0, 0.0, 0.0, 0.0)
    # P(X >= wins | n_decided, p=0.5) via cumulative binomial.
    p_value = sum(
        _binom_pmf(k, n_decided, 0.5) for k in range(wins, n_decided + 1)
    )
    rate = wins / n_decided
    lo, hi = wilson_ci(wins, n_decided)
    return JudgePairResult(
        wins=wins, losses=losses, ties=ties,
        p_value_one_sided=p_value,
        win_rate=rate, win_rate_ci_low=lo, win_rate_ci_high=hi,
    )


def _binom_pmf(k: int, n: int, p: float) -> float:
    return math.comb(n, k) * (p ** k) * ((1 - p) ** (n - k))


# ---------------------------------------------------------------------------
# Interpretation matrix — the placebo vs. real-skill decision
# ---------------------------------------------------------------------------


PLACEBO_VERDICTS = {
    "load_bearing":     "T_LDD > T_baseline AND T_LDD > T_placebo",
    "prompt_priming":   "T_LDD > T_baseline BUT T_LDD ≈ T_placebo",
    "no_effect":        "T_LDD ≈ T_baseline",
    "placebo_wins":     "T_placebo > T_LDD (negative result — investigate)",
}


def verdict(
    t_ldd_vs_baseline: TwoProportionResult,
    t_ldd_vs_placebo: TwoProportionResult,
    alpha: float = 0.05,
) -> str:
    """Classify the trio of arms using the pre-registered interpretation matrix."""
    sig_base = t_ldd_vs_baseline.significant(alpha) and t_ldd_vs_baseline.diff > 0
    sig_plac = t_ldd_vs_placebo.significant(alpha) and t_ldd_vs_placebo.diff > 0
    if t_ldd_vs_baseline.diff < 0 and t_ldd_vs_baseline.significant(alpha):
        return "placebo_wins"
    if not sig_base:
        return "no_effect"
    if sig_base and sig_plac:
        return "load_bearing"
    return "prompt_priming"
