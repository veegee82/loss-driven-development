"""Metric composition algebra — v0.9.0, extended in v0.9.1 with
P6 type-safe composition (fix for audit finding M4).

v0.9.1 change: when composing metrics of different `kind`, the operator
raises `IncompatibleUnitsError` unless caller passes `force_incompatible=True`
with an attestation that the scale choice is semantically intended.


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


class IncompatibleUnitsError(ValueError):
    """Raised by composition operators when components have different
    `kind` (bounded/positive/signed) without explicit opt-in. v0.9.1 P6
    fix for audit finding M4.
    """


def _check_kind_compatibility(
    components: List,
    force_incompatible: bool,
) -> None:
    """Verify all components share the same kind, unless force_incompatible."""
    kinds = {c[0].spec.kind if isinstance(c, tuple) else c.spec.kind for c in components}
    if len(kinds) > 1 and not force_incompatible:
        raise IncompatibleUnitsError(
            f"composition mixes kinds {sorted(kinds)}. "
            f"Pass force_incompatible=True and ensure `normalize_scale` is "
            f"chosen so components map to semantically comparable [0,1] values. "
            f"(Audit finding M4: cross-kind weighted sums are math-only sound.)"
        )


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
    force_incompatible: bool = False,
) -> WeightedSumMetric:
    """Build a weighted-sum metric from (metric, weight) pairs.

    The resulting metric is kind='bounded' (output ∈ [0,1] by construction).

    v0.9.1 P6 — cross-kind composition raises `IncompatibleUnitsError`
    unless `force_incompatible=True` is set explicitly. See audit M4.
    """
    _check_kind_compatibility(components, force_incompatible)
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
    force_incompatible: bool = False,
) -> MaxMetric:
    _check_kind_compatibility(components, force_incompatible)
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
    force_incompatible: bool = False,
) -> MinMetric:
    _check_kind_compatibility(components, force_incompatible)
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
