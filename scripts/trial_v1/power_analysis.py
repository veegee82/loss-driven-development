"""Sample-size + effect-size math for LDD-Trial-v1.

Pure-Python (math-stdlib only) implementation of the classical two-proportion
power calculations used to pre-register the primary-outcome sample size:

    Primary hypothesis:
        H0: p_LDD = p_baseline
        H1: p_LDD ≠ p_baseline         (two-sided; ε = pre-specified minimum detectable effect)

    Primary outcome:
        test_pass@1 — proportion of Tasks whose target test turns green at
        first agent attempt. Binary per Task × seed; aggregated to a
        Task-level mean.

Formulas (all classical, see Fleiss 1981 ch. 3 or Cohen 1988):

    Cohen's h (arcsine-transformed effect size for two proportions):
        h = 2·arcsin(√p1) − 2·arcsin(√p2)

    Required N per arm, two-proportion z-test, equal allocation:
                 (z_{α/2} + z_β)²
        n  =  ───────────────────  · 2 · p̄ · (1 − p̄)
                   (p1 − p2)²
      where p̄ = (p1 + p2) / 2, the pooled proportion under H0.

    Interpretation of Cohen's h (Cohen 1988):
        |h| ≈ 0.20   small effect
        |h| ≈ 0.50   medium effect
        |h| ≈ 0.80   large effect

This module emits the numbers the pre-registration cites and the analysis
script consumes. Keep it dependency-free: the trial must be reproducible
from git alone, no NumPy/SciPy required.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Iterable


# Standard-normal inverse CDF values for common significance levels. Hard-
# coded rather than computed from scratch to keep the module small; these
# are the canonical 4-decimal values used in power tables.
Z_TABLE = {
    0.80: 0.8416,   # one-sided 80 %
    0.90: 1.2816,   # one-sided 90 %
    0.95: 1.6449,   # one-sided 95 %
    0.975: 1.9600,  # two-sided α=0.05
    0.99: 2.3263,   # one-sided 99 %
    0.995: 2.5758,  # two-sided α=0.01
}


def z_alpha_half(alpha: float) -> float:
    """z_{α/2} for a two-sided test."""
    tail = 1.0 - alpha / 2.0
    return _z_lookup(tail)


def z_beta(power: float) -> float:
    """z_β where β is the **power** (1 − Type-II error)."""
    return _z_lookup(power)


def _z_lookup(tail: float) -> float:
    # Exact for the handful of tails we use; interpolate if a caller asks
    # for something else, raise if it's wildly outside the table.
    if tail in Z_TABLE:
        return Z_TABLE[tail]
    keys = sorted(Z_TABLE)
    if tail < keys[0] or tail > keys[-1]:
        raise ValueError(f"z-table tail {tail} out of supported range [{keys[0]}, {keys[-1]}]")
    # Linear interpolation — accurate enough for the power curve.
    for lo, hi in zip(keys, keys[1:]):
        if lo <= tail <= hi:
            w = (tail - lo) / (hi - lo)
            return Z_TABLE[lo] * (1 - w) + Z_TABLE[hi] * w
    raise AssertionError("unreachable")  # pragma: no cover


def cohen_h(p1: float, p2: float) -> float:
    """Effect size for a difference of two proportions (arcsine-transformed)."""
    if not (0.0 <= p1 <= 1.0) or not (0.0 <= p2 <= 1.0):
        raise ValueError("proportions must be in [0, 1]")
    return 2.0 * math.asin(math.sqrt(p1)) - 2.0 * math.asin(math.sqrt(p2))


def required_n_per_arm(
    p1: float,
    p2: float,
    alpha: float = 0.05,
    power: float = 0.80,
) -> int:
    """Two-proportion z-test, equal allocation — returns ⌈n⌉ per arm.

    Uses the pooled-variance formula (Fleiss 1981 §3.2), which is the
    standard pre-registered form and the one `G*Power` emits by default
    for "Z tests — Proportions: Difference between two independent proportions".
    """
    if p1 == p2:
        raise ValueError("p1 and p2 must differ to have a detectable effect")
    z_a = z_alpha_half(alpha)
    z_b = z_beta(power)
    p_bar = (p1 + p2) / 2.0
    numerator = ((z_a + z_b) ** 2) * 2.0 * p_bar * (1.0 - p_bar)
    denominator = (p1 - p2) ** 2
    return math.ceil(numerator / denominator)


@dataclass(frozen=True)
class PowerCurvePoint:
    p2: float           # alternative proportion
    h: float            # Cohen's h
    n_per_arm: int


def power_curve(
    p1: float,
    p2_range: Iterable[float],
    alpha: float = 0.05,
    power: float = 0.80,
) -> list[PowerCurvePoint]:
    """Table of (p2, h, n_per_arm) across candidate alternative proportions.

    Used to surface the trade-off between the minimum-detectable-effect the
    pre-registration commits to (small ε → huge N) and the feasible N given
    compute budget.
    """
    out: list[PowerCurvePoint] = []
    for p2 in p2_range:
        if abs(p2 - p1) < 1e-9:
            continue
        out.append(
            PowerCurvePoint(
                p2=p2,
                h=cohen_h(p1, p2),
                n_per_arm=required_n_per_arm(p1, p2, alpha=alpha, power=power),
            )
        )
    return out


def effect_size_label(h: float) -> str:
    """Cohen's 1988 conventional labels for arcsine-transformed h."""
    a = abs(h)
    if a < 0.20:
        return "negligible"
    if a < 0.50:
        return "small"
    if a < 0.80:
        return "medium"
    return "large"
