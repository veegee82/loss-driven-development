"""Standard unit tests for the Metric Algebra — v0.9.0.

Covers:
  - MetricSpec validation + gaming-guard
  - BoundedRateMetric / PositiveCountMetric / SignedDeltaMetric semantics
  - Loss / Signal computation
  - Estimator predictions (MeanHistory + BayesianSynthesis)
  - Composition operators (WeightedSum / Max / Min)
  - Registry: register + get + reject duplicates / missing components
  - Calibrator: log, MAE, can_promote, try_promote gate

Property-based tests (hypothesis) live in test_metric_properties.py.
LDD E2E scenarios live in test_metric_e2e.py.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import pytest

from ldd_trace import TraceStore
from ldd_trace.metric import (
    BayesianSynthesisEstimator,
    BoundedRateMetric,
    Loss,
    MeanHistoryEstimator,
    MetricSpec,
    PositiveCountMetric,
    Prediction,
    Signal,
    SignedDeltaMetric,
    bounded_rate,
    positive_count,
    signed_delta,
)
from ldd_trace.metric_compose import (
    MaxMetric,
    MinMetric,
    WeightedSumMetric,
    maximum,
    minimum,
    weighted_sum,
)
from ldd_trace.metric_registry import (
    CALIB_MAX_MAE,
    CALIB_MIN_N,
    Calibrator,
    MetricRegistry,
)


# ---------------------------------------------------------------------------
# MetricSpec — validation + gaming-guard
# ---------------------------------------------------------------------------


class TestMetricSpec:
    def test_valid_spec(self) -> None:
        s = MetricSpec(name="test_pass_rate", kind="bounded", unit="rate")
        assert s.name == "test_pass_rate"
        assert s.kind == "bounded"
        assert s.advisory_only is True

    def test_frozen(self) -> None:
        """Specs are immutable (frozen dataclass)."""
        s = MetricSpec(name="x", kind="bounded", unit="rate")
        with pytest.raises(Exception):  # FrozenInstanceError in 3.10+
            s.name = "y"  # type: ignore

    def test_invalid_name_rejected(self) -> None:
        with pytest.raises(ValueError, match="alphanumeric"):
            MetricSpec(name="has spaces", kind="bounded", unit="rate")

    def test_invalid_kind_rejected(self) -> None:
        with pytest.raises(ValueError, match="invalid kind"):
            MetricSpec(name="x", kind="weird", unit="rate")  # type: ignore

    def test_gaming_guard_rejects_self_ref(self) -> None:
        with pytest.raises(ValueError, match="gaming-guard"):
            MetricSpec(
                name="game_me",
                kind="bounded",
                unit="rate",
                description="rewards my current action on this step",
            )

    def test_gaming_guard_allows_normal_descriptions(self) -> None:
        # Should not raise
        MetricSpec(
            name="latency_p99",
            kind="positive",
            unit="ms",
            description="99th percentile response latency from prometheus",
        )


# ---------------------------------------------------------------------------
# BoundedRateMetric
# ---------------------------------------------------------------------------


class TestBoundedRateMetric:
    def test_observed_computes_rate(self) -> None:
        m = bounded_rate("tpr", lambda o: (o["failed"], o["total"]))
        assert m.observed({"failed": 3, "total": 10}) == 0.3

    def test_zero_denominator_returns_zero(self) -> None:
        m = bounded_rate("tpr", lambda o: (o["failed"], o["total"]))
        assert m.observed({"failed": 0, "total": 0}) == 0.0

    def test_normalize_is_identity_for_in_range(self) -> None:
        m = bounded_rate("tpr", lambda o: (o, 1))
        assert m.normalize(0.3) == 0.3

    def test_normalize_clamps_out_of_range(self) -> None:
        m = bounded_rate("tpr", lambda o: (o, 1))
        assert m.normalize(-0.5) == 0.0
        assert m.normalize(1.5) == 1.0

    def test_wrong_kind_rejected(self) -> None:
        spec = MetricSpec(name="x", kind="positive", unit="rate")
        with pytest.raises(ValueError, match="kind='bounded'"):
            BoundedRateMetric(spec, lambda o: (0, 1))


# ---------------------------------------------------------------------------
# PositiveCountMetric
# ---------------------------------------------------------------------------


class TestPositiveCountMetric:
    def test_observed_passes_through(self) -> None:
        m = positive_count("lat_ms", lambda o: o, normalize_scale=1000.0)
        assert m.observed(200) == 200.0

    def test_normalize_saturates_at_scale(self) -> None:
        m = positive_count("lat", lambda o: o, normalize_scale=1000.0)
        assert m.normalize(500) == 0.5
        assert m.normalize(1000) == 1.0
        assert m.normalize(5000) == 1.0  # saturates

    def test_negative_observation_rejected(self) -> None:
        m = positive_count("x", lambda o: o, normalize_scale=100.0)
        with pytest.raises(ValueError, match="negative"):
            m.observed(-5)

    def test_scale_zero_rejected(self) -> None:
        m = positive_count("x", lambda o: o, normalize_scale=0.0)
        with pytest.raises(ValueError, match="normalize_scale"):
            m.normalize(5.0)


# ---------------------------------------------------------------------------
# SignedDeltaMetric
# ---------------------------------------------------------------------------


class TestSignedDeltaMetric:
    def test_observed_passes_through_signed(self) -> None:
        m = signed_delta("delta", lambda o: o)
        assert m.observed(-0.3) == -0.3
        assert m.observed(0.5) == 0.5

    def test_normalize_is_sigmoid(self) -> None:
        m = signed_delta("delta", lambda o: o)
        assert m.normalize(0.0) == pytest.approx(0.5)
        assert m.normalize(-100) == pytest.approx(0.0, abs=1e-6)
        assert m.normalize(100) == pytest.approx(1.0, abs=1e-6)


# ---------------------------------------------------------------------------
# Loss + Signal
# ---------------------------------------------------------------------------


class TestLoss:
    def test_loss_evaluates_metric(self) -> None:
        m = bounded_rate("tpr", lambda o: (o["f"], o["t"]))
        L = Loss(metric=m, label="L_test")
        assert L.evaluate({"f": 2, "t": 8}) == 0.25

    def test_loss_normalized(self) -> None:
        m = positive_count("lat", lambda o: o, normalize_scale=1000.0)
        L = Loss(metric=m)
        assert L.evaluate_normalized(500) == 0.5


class TestSignal:
    def test_signal_is_difference(self) -> None:
        m = bounded_rate("tpr", lambda o: (o["f"], o["t"]))
        L = Loss(metric=m)
        sig = Signal(loss=L)
        theta0 = {"f": 5, "t": 10}  # L = 0.5
        theta1 = {"f": 2, "t": 10}  # L = 0.2
        assert sig.compute(theta0, theta1) == pytest.approx(-0.3)


# ---------------------------------------------------------------------------
# Estimators
# ---------------------------------------------------------------------------


class TestMeanHistoryEstimator:
    def test_returns_mean_for_matching_class(self) -> None:
        history = [("skill_A", -0.2), ("skill_B", +0.1), ("skill_A", -0.4)]
        est = MeanHistoryEstimator(history, action_class_fn=lambda a: a)
        p = est.predict("skill_A")
        assert p.predicted_signal == pytest.approx(-0.3)

    def test_zero_confidence_when_no_history(self) -> None:
        est = MeanHistoryEstimator([], action_class_fn=lambda a: a)
        p = est.predict("x")
        assert p.predicted_signal == 0.0
        assert p.confidence == 0.0

    def test_confidence_grows_with_sample_size(self) -> None:
        hist = [("s", 0.1)] * 10
        est = MeanHistoryEstimator(hist, action_class_fn=lambda a: a)
        p = est.predict("s")
        assert p.confidence > 0.9


class TestBayesianSynthesisEstimator:
    def test_no_antitheses_returns_prior(self) -> None:
        est = BayesianSynthesisEstimator()
        p = est.predict({"thesis_prior": 0.8, "antitheses": []}, None)
        assert p.predicted_signal == 0.8

    def test_negative_impact_lowers_expectation(self) -> None:
        est = BayesianSynthesisEstimator()
        # Prior 0.8, single antithesis with prob=0.5, impact=-0.4
        # E = 0.5*0.8 + 0.5*max(0, 0.4) = 0.40 + 0.20 = 0.60
        p = est.predict(
            {"thesis_prior": 0.8, "antitheses": [(0.5, -0.4)]}, None
        )
        assert p.predicted_signal == pytest.approx(0.6, abs=0.01)


# ---------------------------------------------------------------------------
# Composition — WeightedSum
# ---------------------------------------------------------------------------


class TestWeightedSum:
    def test_two_components_equal_weights_averages(self) -> None:
        m1 = bounded_rate("a", lambda o: (o["a"], 1))
        m2 = bounded_rate("b", lambda o: (o["b"], 1))
        ws = weighted_sum("combined", [(m1, 1.0), (m2, 1.0)])
        # obs a=0.4, b=0.8 → mean = 0.6
        assert ws.observed({"a": 0.4, "b": 0.8}) == pytest.approx(0.6)

    def test_unequal_weights(self) -> None:
        m1 = bounded_rate("a", lambda o: (o["a"], 1))
        m2 = bounded_rate("b", lambda o: (o["b"], 1))
        ws = weighted_sum("combined", [(m1, 3.0), (m2, 1.0)])
        # (3 * 0.4 + 1 * 0.8) / 4 = 2.0 / 4 = 0.5
        assert ws.observed({"a": 0.4, "b": 0.8}) == pytest.approx(0.5)

    def test_empty_components_rejected(self) -> None:
        spec = MetricSpec(
            name="x", kind="bounded", unit="rate", composition="weighted_sum"
        )
        with pytest.raises(ValueError, match="at least one"):
            WeightedSumMetric(spec, [])

    def test_negative_weight_rejected(self) -> None:
        m1 = bounded_rate("a", lambda o: (0, 1))
        with pytest.raises(ValueError, match="non-negative"):
            weighted_sum("x", [(m1, -1.0)])

    def test_zero_total_weight_rejected(self) -> None:
        m1 = bounded_rate("a", lambda o: (0, 1))
        with pytest.raises(ValueError, match="sum of component weights"):
            weighted_sum("x", [(m1, 0.0)])

    def test_output_bounded_0_1(self) -> None:
        m1 = bounded_rate("a", lambda o: (1, 1))  # → 1.0
        m2 = bounded_rate("b", lambda o: (1, 1))  # → 1.0
        ws = weighted_sum("x", [(m1, 1.0), (m2, 1.0)])
        assert 0.0 <= ws.observed({}) <= 1.0


# ---------------------------------------------------------------------------
# Composition — Max, Min
# ---------------------------------------------------------------------------


class TestMaxMin:
    def test_max_takes_highest_normalized(self) -> None:
        m1 = bounded_rate("a", lambda o: (o["a"], 1))
        m2 = bounded_rate("b", lambda o: (o["b"], 1))
        mx = maximum("any_fail", [m1, m2])
        assert mx.observed({"a": 0.2, "b": 0.7}) == pytest.approx(0.7)

    def test_min_takes_lowest_normalized(self) -> None:
        m1 = bounded_rate("a", lambda o: (o["a"], 1))
        m2 = bounded_rate("b", lambda o: (o["b"], 1))
        mn = minimum("all_pass", [m1, m2])
        assert mn.observed({"a": 0.2, "b": 0.7}) == pytest.approx(0.2)


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------


class TestRegistry:
    def test_register_and_get(self, tmp_path: Path) -> None:
        store = TraceStore(tmp_path)
        reg = MetricRegistry(store)
        m = bounded_rate("x", lambda o: (o, 1))
        reg.register(m)
        assert reg.get("x") is m
        assert "x" in reg.list_names()

    def test_duplicate_registration_rejected(self, tmp_path: Path) -> None:
        store = TraceStore(tmp_path)
        reg = MetricRegistry(store)
        m1 = bounded_rate("x", lambda o: (o, 1))
        m2 = bounded_rate("x", lambda o: (o, 1))
        reg.register(m1)
        with pytest.raises(ValueError, match="already registered"):
            reg.register(m2)

    def test_version_bump_allowed(self, tmp_path: Path) -> None:
        store = TraceStore(tmp_path)
        reg = MetricRegistry(store)
        m1 = bounded_rate("x", lambda o: (o, 1), version=1)
        m2 = bounded_rate("x", lambda o: (o, 1), version=2)
        reg.register(m1)
        reg.register(m2)  # version bump — OK
        assert reg.specs()["x"].version == 2

    def test_version_downgrade_rejected(self, tmp_path: Path) -> None:
        store = TraceStore(tmp_path)
        reg = MetricRegistry(store)
        m1 = bounded_rate("x", lambda o: (o, 1), version=2)
        m2 = bounded_rate("x", lambda o: (o, 1), version=1)
        reg.register(m1)
        with pytest.raises(ValueError, match="must be >"):
            reg.register(m2)

    def test_composition_requires_components_registered(
        self, tmp_path: Path
    ) -> None:
        store = TraceStore(tmp_path)
        reg = MetricRegistry(store)
        m1 = bounded_rate("a", lambda o: (o, 1))
        m2 = bounded_rate("b", lambda o: (o, 1))
        ws = weighted_sum("ab", [(m1, 1.0), (m2, 1.0)])
        # m1 and m2 not yet registered
        with pytest.raises(ValueError, match="unregistered component"):
            reg.register(ws)

    def test_composition_accepts_registered_components(
        self, tmp_path: Path
    ) -> None:
        store = TraceStore(tmp_path)
        reg = MetricRegistry(store)
        m1 = bounded_rate("a", lambda o: (o["a"], 1))
        m2 = bounded_rate("b", lambda o: (o["b"], 1))
        reg.register(m1)
        reg.register(m2)
        ws = weighted_sum("ab", [(m1, 1.0), (m2, 1.0)])
        reg.register(ws)  # should work
        assert reg.get("ab") is ws

    def test_persists_to_disk(self, tmp_path: Path) -> None:
        store = TraceStore(tmp_path)
        reg = MetricRegistry(store)
        m = bounded_rate("x", lambda o: (o, 1))
        reg.register(m)
        path = tmp_path / ".ldd" / "metrics.json"
        assert path.exists()
        data = json.loads(path.read_text())
        assert any(s["name"] == "x" for s in data["specs"])

    def test_reloads_specs_from_disk(self, tmp_path: Path) -> None:
        store = TraceStore(tmp_path)
        reg1 = MetricRegistry(store)
        m = bounded_rate("x", lambda o: (o, 1))
        reg1.register(m)
        # Fresh registry on same store
        reg2 = MetricRegistry(store)
        assert "x" in reg2.specs()


# ---------------------------------------------------------------------------
# Calibrator
# ---------------------------------------------------------------------------


class TestCalibrator:
    def _reg_with_metric(self, tmp_path: Path, name: str = "m") -> MetricRegistry:
        store = TraceStore(tmp_path)
        reg = MetricRegistry(store)
        m = bounded_rate(name, lambda o: (o, 1))
        reg.register(m)
        return reg

    def test_log_records_pair(self, tmp_path: Path) -> None:
        reg = self._reg_with_metric(tmp_path)
        cal = Calibrator(reg)
        cal.log("m", predicted=0.3, observed=0.28)
        assert cal.n_samples("m") == 1
        assert cal.mae("m") == pytest.approx(0.02)

    def test_mae_across_samples(self, tmp_path: Path) -> None:
        reg = self._reg_with_metric(tmp_path)
        cal = Calibrator(reg)
        for pred, obs in [(0.3, 0.28), (0.5, 0.6), (0.2, 0.15)]:
            cal.log("m", pred, obs)
        # MAE = (0.02 + 0.10 + 0.05) / 3 = 0.0567
        assert cal.mae("m") == pytest.approx((0.02 + 0.10 + 0.05) / 3, abs=0.001)

    def test_cant_promote_below_min_n(self, tmp_path: Path) -> None:
        reg = self._reg_with_metric(tmp_path)
        cal = Calibrator(reg)
        for _ in range(4):  # below CALIB_MIN_N=5
            cal.log("m", 0.5, 0.5)
        assert cal.can_promote("m") is False
        assert cal.try_promote("m") is False

    def test_cant_promote_if_mae_too_high(self, tmp_path: Path) -> None:
        reg = self._reg_with_metric(tmp_path)
        cal = Calibrator(reg)
        for _ in range(5):
            cal.log("m", 0.8, 0.0)  # err=0.8 each → MAE=0.8
        assert cal.can_promote("m") is False
        assert cal.try_promote("m") is False

    def test_promotes_when_gate_passes(self, tmp_path: Path) -> None:
        reg = self._reg_with_metric(tmp_path)
        cal = Calibrator(reg)
        for _ in range(5):
            cal.log("m", 0.5, 0.5)  # err=0 each
        assert cal.can_promote("m") is True
        assert cal.try_promote("m") is True
        promo = reg.promotion("m")
        assert promo is not None
        assert promo.is_load_bearing is True
        assert promo.promoted_at is not None

    def test_promote_is_idempotent(self, tmp_path: Path) -> None:
        reg = self._reg_with_metric(tmp_path)
        cal = Calibrator(reg)
        for _ in range(5):
            cal.log("m", 0.5, 0.5)
        cal.try_promote("m")
        # Call again — should be idempotent no-op
        assert cal.try_promote("m") is True

    def test_calibrations_persist(self, tmp_path: Path) -> None:
        reg = self._reg_with_metric(tmp_path)
        cal = Calibrator(reg)
        cal.log("m", 0.3, 0.28)
        path = tmp_path / ".ldd" / "metric_calibrations.jsonl"
        assert path.exists()
        content = path.read_text().strip()
        d = json.loads(content.split("\n")[0])
        assert d["metric_name"] == "m"
        assert d["predicted"] == 0.3


if __name__ == "__main__":
    import sys
    sys.exit(pytest.main([__file__, "-v"]))
