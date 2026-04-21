"""Metric composition algebra — v0.9.0.

Operators that take metrics and produce new metrics:

  L_combined  = Σ_i w_i × normalize(L_i)        (WeightedSumMetric)
  L_any_fail  = max_i normalize(L_i)             (MaxMetric)
  L_all_pass  = min_i normalize(L_i)             (MinMetric)
  L_scaled    = c × L                             (via WeightedSumMetric with single component)

Algebraic laws enforced by test_metric_properties.py (hypothesis):
  - WeightedSum is linear in weights
  - Max/Min are idempotent:          max(L, L) ≡ L
  - Max/Min are commutative:         max(L1, L2) ≡ max(L2, L1)
  - WeightedSum with equal weights = Mean
  - Composition preserves normalize(·) output range [0, 1]

Bias-invariance: composed metrics carry a derived spec with `composition`
field set. The registry validates that all components are registered before
allowing composition to register a new metric.
"""
from __future__ import annotations

from dataclasses import replace
from typing import List, Tuple

from ldd_trace.metric import Metric, MetricSpec


def _clamp01(x: float) -> float:
    return max(0.0, min(1.0, x))


# ---------------------------------------------------------------------------
# Weighted sum
# ---------------------------------------------------------------------------


class WeightedSumMetric:
    """L_combined(θ) = Σ_i w_i · normalize_i(observed_i(θ)) / Σ w_i

    Output is always in [0, 1] because each component's normalize returns
    [0, 1] and the weighted average preserves [0, 1].
    """

    def __init__(
        self,
        spec: MetricSpec,
        components: List[Tuple[Metric, float]],
    ) -> None:
        if spec.composition != "weighted_sum":
            raise ValueError(
                f"WeightedSumMetric requires spec.composition='weighted_sum', "
                f"got {spec.composition!r}"
            )
        if not components:
            raise ValueError("WeightedSumMetric requires at least one component")
        for _, w in components:
            if w < 0:
                raise ValueError(f"weights must be non-negative, got {w}")
        if sum(w for _, w in components) <= 0:
            raise ValueError("sum of component weights must be > 0")
        self.spec = spec
        self.components = components

    def observed(self, obs) -> float:
        total_weight = sum(w for _, w in self.components)
        weighted = sum(
            m.normalize(m.observed(obs)) * w for m, w in self.components
        )
        return weighted / total_weight

    def normalize(self, value: float) -> float:
        return _clamp01(value)


# ---------------------------------------------------------------------------
# Max (any-fail semantics — OR)
# ---------------------------------------------------------------------------


class MaxMetric:
    """L_any_fail(θ) = max_i normalize_i(observed_i(θ))

    Semantics: if ANY component is high (bad), the combined metric is high.
    Useful for "any test failure fails the composite" rubrics.
    """

    def __init__(self, spec: MetricSpec, components: List[Metric]) -> None:
        if spec.composition != "max":
            raise ValueError(
                f"MaxMetric requires spec.composition='max', got {spec.composition!r}"
            )
        if not components:
            raise ValueError("MaxMetric requires at least one component")
        self.spec = spec
        self.components = components

    def observed(self, obs) -> float:
        return max(m.normalize(m.observed(obs)) for m in self.components)

    def normalize(self, value: float) -> float:
        return _clamp01(value)


# ---------------------------------------------------------------------------
# Min (all-pass semantics — AND)
# ---------------------------------------------------------------------------


class MinMetric:
    """L_all_pass(θ) = min_i normalize_i(observed_i(θ))

    Semantics: the combined value is only low (good) when ALL components are low.
    Dual of MaxMetric.
    """

    def __init__(self, spec: MetricSpec, components: List[Metric]) -> None:
        if spec.composition != "min":
            raise ValueError(
                f"MinMetric requires spec.composition='min', got {spec.composition!r}"
            )
        if not components:
            raise ValueError("MinMetric requires at least one component")
        self.spec = spec
        self.components = components

    def observed(self, obs) -> float:
        return min(m.normalize(m.observed(obs)) for m in self.components)

    def normalize(self, value: float) -> float:
        return _clamp01(value)


# ---------------------------------------------------------------------------
# Factory helpers
# ---------------------------------------------------------------------------


def weighted_sum(
    name: str,
    components: List[Tuple[Metric, float]],
    *,
    description: str = "",
    version: int = 1,
    advisory_only: bool = True,
) -> WeightedSumMetric:
    """Build a weighted-sum metric from (metric, weight) pairs.

    The resulting metric is kind='bounded' (output ∈ [0,1] by construction).
    """
    spec = MetricSpec(
        name=name,
        kind="bounded",
        unit="rate",
        description=description,
        version=version,
        advisory_only=advisory_only,
        composition="weighted_sum",
        components=tuple((m.spec.name, w) for m, w in components),
    )
    return WeightedSumMetric(spec, components)


def maximum(
    name: str,
    components: List[Metric],
    *,
    description: str = "",
    version: int = 1,
    advisory_only: bool = True,
) -> MaxMetric:
    spec = MetricSpec(
        name=name,
        kind="bounded",
        unit="rate",
        description=description,
        version=version,
        advisory_only=advisory_only,
        composition="max",
        components=tuple((m.spec.name, 1.0) for m in components),
    )
    return MaxMetric(spec, components)


def minimum(
    name: str,
    components: List[Metric],
    *,
    description: str = "",
    version: int = 1,
    advisory_only: bool = True,
) -> MinMetric:
    spec = MetricSpec(
        name=name,
        kind="bounded",
        unit="rate",
        description=description,
        version=version,
        advisory_only=advisory_only,
        composition="min",
        components=tuple((m.spec.name, 1.0) for m in components),
    )
    return MinMetric(spec, components)
