"""Metric Algebra — core protocols and concrete instances. v0.9.0.

Generalizes v0.5.1–v0.8.0's specific loss/gradient mechanisms into a reusable
algebra of five primitives:

  1. Metric      — Observation → ℝ  (anything that can be measured)
  2. Loss        — Metric over θ (parameter state) → ℝ, usually bounded or positive
  3. Signal      — Δ between two θ-states under an Action
  4. Estimator   — predicts Signal before the Action happens (Bayesian-ish)
  5. Calibrator  — tracks (predicted, observed) over time → drift signal

Every v0.5.1+ loss is an instance of these abstractions. New metrics can be
registered by agents or users WITHOUT modifying LDD core (see MetricRegistry).

The load-bearing bias-invariance principle is preserved:
  - Metric specs are immutable after registration (changes require version bump)
  - A metric is `advisory_only=True` by default; calibration must pass (n≥5, MAE<0.15)
    before it can become `load_bearing=True`
  - `observed()` is deterministic and read-only w.r.t. θ

See `skills/define-metric/SKILL.md` for the skill-level protocol and
`docs/theory.md` §4 for the formal specification.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field, replace
from typing import Any, Callable, List, Literal, Optional, Protocol, Tuple, runtime_checkable


MetricKind = Literal["bounded", "positive", "signed"]


# ---------------------------------------------------------------------------
# MetricSpec — serializable description of a metric
# ---------------------------------------------------------------------------

# Phrases that, if present in a metric description, indicate the metric may be
# self-referential and could be gamed by the agent. Gaming-guard rejects these.
GAMING_GUARD_PHRASES = (
    "current action",
    "last action",
    "my decision",
    "the action i took",
    "the action just taken",
    "my current",
    "i want",
    "i prefer",
)


@dataclass(frozen=True)
class MetricSpec:
    """Serializable spec of a metric. Stored in .ldd/metrics.json.

    Frozen so registrations are immutable. Changing a metric's behavior
    requires a NEW spec with incremented `version`.
    """

    name: str
    kind: MetricKind
    unit: str
    description: str = ""
    version: int = 1
    advisory_only: bool = True
    normalize_scale: float = 1.0                 # for PositiveCountMetric
    composition: Optional[str] = None            # "weighted_sum" | "max" | "min" | None
    components: Optional[Tuple[Tuple[str, float], ...]] = None  # ((name, weight), ...)

    def __post_init__(self) -> None:
        # Name validation
        if not self.name:
            raise ValueError("metric name is required")
        if not all(c.isalnum() or c in "_-." for c in self.name):
            raise ValueError(
                f"metric name must be alphanumeric + [_-.]: got {self.name!r}"
            )
        # Kind validation
        if self.kind not in ("bounded", "positive", "signed"):
            raise ValueError(f"invalid kind: {self.kind}")
        # Gaming-guard — the bias-invariance check at the spec level
        desc_lower = (self.description or "").lower()
        for phrase in GAMING_GUARD_PHRASES:
            if phrase in desc_lower:
                raise ValueError(
                    f"gaming-guard: spec description contains self-referential "
                    f"phrase {phrase!r} (spec must describe WHAT is measured, "
                    f"not reward the agent's current behavior)"
                )

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "kind": self.kind,
            "unit": self.unit,
            "description": self.description,
            "version": self.version,
            "advisory_only": self.advisory_only,
            "normalize_scale": self.normalize_scale,
            "composition": self.composition,
            "components": (
                [{"name": n, "weight": w} for n, w in self.components]
                if self.components
                else None
            ),
        }


# ---------------------------------------------------------------------------
# Metric protocol + three concrete instances
# ---------------------------------------------------------------------------


@runtime_checkable
class Metric(Protocol):
    """Core primitive. Maps an observation to a scalar.

    Contract:
      - `observed(obs)` is pure / deterministic (no side effects on θ)
      - `normalize(value)` maps to [0, 1] for cross-metric composition
      - `spec` is the metric's immutable description
    """

    spec: MetricSpec

    def observed(self, obs: Any) -> float: ...
    def normalize(self, value: float) -> float: ...


class BoundedRateMetric:
    """Bounded rate metric — observed() ∈ [0, 1] directly.

    Canonical example: failing_tests / total_tests. The accessor returns
    (numerator, denominator); rate is computed safely (0/0 → 0.0).
    """

    def __init__(
        self,
        spec: MetricSpec,
        accessor: Callable[[Any], Tuple[float, float]],
    ) -> None:
        if spec.kind != "bounded":
            raise ValueError(
                f"BoundedRateMetric requires kind='bounded', got {spec.kind}"
            )
        self.spec = spec
        self._accessor = accessor

    def observed(self, obs: Any) -> float:
        num, denom = self._accessor(obs)
        return num / denom if denom > 0 else 0.0

    def normalize(self, value: float) -> float:
        return max(0.0, min(1.0, value))


class PositiveCountMetric:
    """Positive unbounded metric — observed() ∈ [0, ∞).

    Canonical examples: latency_ms, vulnerability_count, cyclomatic_complexity.
    Normalization saturates at `spec.normalize_scale`: values ≥ scale → 1.0.
    """

    def __init__(
        self,
        spec: MetricSpec,
        accessor: Callable[[Any], float],
    ) -> None:
        if spec.kind != "positive":
            raise ValueError(
                f"PositiveCountMetric requires kind='positive', got {spec.kind}"
            )
        self.spec = spec
        self._accessor = accessor

    def observed(self, obs: Any) -> float:
        v = self._accessor(obs)
        if v < 0:
            raise ValueError(
                f"PositiveCountMetric observed negative value {v}; kind='positive' "
                "requires non-negative observations (use SignedDeltaMetric for signed data)"
            )
        return float(v)

    def normalize(self, value: float) -> float:
        scale = self.spec.normalize_scale
        if scale <= 0:
            raise ValueError("normalize_scale must be > 0 for PositiveCountMetric")
        return min(1.0, max(0.0, value) / scale)


class SignedDeltaMetric:
    """Signed metric — observed() ∈ ℝ.

    Canonical example: Δloss between two θ-states. Normalization is a
    shifted sigmoid: 0 → 0.5 (no change), −∞ → 0.0, +∞ → 1.0.
    """

    def __init__(
        self,
        spec: MetricSpec,
        accessor: Callable[[Any], float],
    ) -> None:
        if spec.kind != "signed":
            raise ValueError(
                f"SignedDeltaMetric requires kind='signed', got {spec.kind}"
            )
        self.spec = spec
        self._accessor = accessor

    def observed(self, obs: Any) -> float:
        return float(self._accessor(obs))

    def normalize(self, value: float) -> float:
        # Sigmoid centered at 0: 0 → 0.5
        # Steepness controlled by normalize_scale (default 1.0)
        scale = self.spec.normalize_scale
        if scale <= 0:
            raise ValueError("normalize_scale must be > 0 for SignedDeltaMetric")
        return 1.0 / (1.0 + math.exp(-value / scale))


# ---------------------------------------------------------------------------
# Loss — a Metric evaluated on a θ-state
# ---------------------------------------------------------------------------


@dataclass
class Loss:
    """A Metric bound to a label. The metric's `observed()` is the loss value.

    L(θ) := metric.observed(θ)

    Loss inherits the metric's kind. Most LDD optimization expects bounded
    losses ∈ [0, 1] (rate-typed), but positive (latency, counts) and signed
    (Δloss) are supported too for custom agent-defined objectives.
    """

    metric: Metric
    label: str = "L"

    def evaluate(self, theta: Any) -> float:
        return self.metric.observed(theta)

    def evaluate_normalized(self, theta: Any) -> float:
        return self.metric.normalize(self.metric.observed(theta))


# ---------------------------------------------------------------------------
# Signal — Δ between two θ-states under an action
# ---------------------------------------------------------------------------


@dataclass
class Signal:
    """Observed Δ in loss between two θ-states.

    S(a, θ) = L(θ ⊕ a) − L(θ)

    This is the v0.5.1 per-iteration Δloss generalized to any Loss.
    """

    loss: Loss

    def compute(self, theta_before: Any, theta_after: Any) -> float:
        return self.loss.evaluate(theta_after) - self.loss.evaluate(theta_before)

    def compute_normalized(self, theta_before: Any, theta_after: Any) -> float:
        return (
            self.loss.evaluate_normalized(theta_after)
            - self.loss.evaluate_normalized(theta_before)
        )


# ---------------------------------------------------------------------------
# Estimator — predicts Signal before the action
# ---------------------------------------------------------------------------


@dataclass
class Prediction:
    """Output of an Estimator.

    `predicted_signal` is the expected Δ in the Loss. `confidence` ∈ [0, 1]
    reflects sample size / prior strength. Feeds the Calibrator to compute
    prediction_error once the action is executed.
    """

    predicted_signal: float
    confidence: float = 0.5


@runtime_checkable
class Estimator(Protocol):
    def predict(self, action: Any, context: Any) -> Prediction: ...


class MeanHistoryEstimator:
    """First-moment estimator: mean past Signal for a given action class.

    This is v0.5.2's skill_effectiveness generalized. The action_class_fn
    maps an action to a key (e.g., skill name); the estimator returns the
    mean observed Signal for that key from the history.
    """

    def __init__(
        self,
        history: List[Tuple[Any, float]],
        action_class_fn: Callable[[Any], str],
    ) -> None:
        self._history = history
        self._action_class_fn = action_class_fn

    def predict(self, action: Any, context: Any = None) -> Prediction:
        cls = self._action_class_fn(action)
        matching = [s for (a, s) in self._history if self._action_class_fn(a) == cls]
        if not matching:
            return Prediction(predicted_signal=0.0, confidence=0.0)
        mean = sum(matching) / len(matching)
        # Confidence via log-scaled sample size
        n = len(matching)
        confidence = min(1.0, math.log(1 + n) / math.log(1 + 10))
        return Prediction(predicted_signal=mean, confidence=confidence)


class BayesianSynthesisEstimator:
    """v0.7.0's quantitative-dialectic estimator, generalized.

    Given a thesis-prior and a list of (prob_applies, impact) pairs,
    returns:
        E[S | thesis] = (1 - Σ Pr_i) × prior + Σ Pr_i × (prior + impact_i)

    This is the exact formula used for step-level predicted correctness
    in v0.8.0 dialectical-CoT.
    """

    def predict(self, action: Any, context: Any) -> Prediction:
        """`action`: dict with keys thesis_prior, antitheses=[(prob, impact)].
        `context`: ignored (primers baked into action.antitheses).
        """
        prior = float(action.get("thesis_prior", 0.5))
        antis = action.get("antitheses", [])
        if not antis:
            return Prediction(predicted_signal=prior, confidence=0.5)
        total_pr = sum(a[0] for a in antis)
        base = max(0.0, 1.0 - total_pr) * prior
        conditional = sum(
            a[0] * max(0.0, min(1.0, prior + a[1])) for a in antis
        )
        predicted = max(0.0, min(1.0, base + conditional))
        # Confidence: higher with more antitheses (more Hessian-probing done)
        confidence = min(1.0, 0.3 + 0.1 * len(antis))
        return Prediction(predicted_signal=predicted, confidence=confidence)


# ---------------------------------------------------------------------------
# Convenience: factory helpers for the three canonical metric kinds
# ---------------------------------------------------------------------------


def bounded_rate(
    name: str,
    accessor: Callable[[Any], Tuple[float, float]],
    *,
    unit: str = "rate",
    description: str = "",
    version: int = 1,
) -> BoundedRateMetric:
    spec = MetricSpec(
        name=name, kind="bounded", unit=unit,
        description=description, version=version,
    )
    return BoundedRateMetric(spec, accessor)


def positive_count(
    name: str,
    accessor: Callable[[Any], float],
    *,
    unit: str = "count",
    description: str = "",
    version: int = 1,
    normalize_scale: float = 100.0,
) -> PositiveCountMetric:
    spec = MetricSpec(
        name=name, kind="positive", unit=unit, description=description,
        version=version, normalize_scale=normalize_scale,
    )
    return PositiveCountMetric(spec, accessor)


def signed_delta(
    name: str,
    accessor: Callable[[Any], float],
    *,
    unit: str = "dimensionless",
    description: str = "",
    version: int = 1,
    normalize_scale: float = 1.0,
) -> SignedDeltaMetric:
    spec = MetricSpec(
        name=name, kind="signed", unit=unit, description=description,
        version=version, normalize_scale=normalize_scale,
    )
    return SignedDeltaMetric(spec, accessor)
