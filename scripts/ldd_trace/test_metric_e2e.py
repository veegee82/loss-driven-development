"""LDD E2E tests for the Metric Algebra — v0.9.0.

Each test is a **scenario-based** end-to-end verification: a realistic
workflow that exercises the concept through the full protocol (register →
observe → predict → calibrate → promote) and asserts on the emergent
behavior, not just individual method return values.

Nine E2E scenarios, one per core concept. Each closes an evidence loop for
"this concept works in the context the design claims it works in."
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from ldd_trace import TraceStore
from ldd_trace.metric import (
    BayesianSynthesisEstimator,
    Loss,
    MeanHistoryEstimator,
    Signal,
    bounded_rate,
    positive_count,
    signed_delta,
)
from ldd_trace.metric_compose import maximum, minimum, weighted_sum
from ldd_trace.metric_registry import Calibrator, MetricRegistry


# ---------------------------------------------------------------------------
# E2E #1 — agent introduces a new metric mid-session
# ---------------------------------------------------------------------------


class TestE2E_AgentIntroducesCustomMetric:
    """Scenario: during a refactoring task, the agent decides to track
    cyclomatic complexity alongside test pass rate. v0.9.0 enables this
    without code changes to LDD core.
    """

    def test_agent_registers_and_uses_custom_metric(self, tmp_path: Path) -> None:
        store = TraceStore(tmp_path)
        reg = MetricRegistry(store)

        # Agent registers a metric from domain knowledge (pretend
        # `measure_cyclomatic(θ)` is a deterministic function on the code state)
        cyclo = positive_count(
            "cyclomatic_complexity",
            lambda θ: θ.get("cyclomatic", 0.0),
            unit="count",
            description="aggregate cyclomatic complexity over changed files",
            normalize_scale=50.0,
        )
        reg.register(cyclo)

        # Agent observes θ_before a refactor
        theta_before = {"cyclomatic": 35.0}
        before = cyclo.observed(theta_before)
        assert before == 35.0

        # Refactor happens, θ_after has lower complexity
        theta_after = {"cyclomatic": 20.0}
        after = cyclo.observed(theta_after)
        assert after == 20.0

        # Signal machinery applies uniformly
        L = Loss(metric=cyclo, label="L_complexity")
        sig = Signal(loss=L)
        delta = sig.compute(theta_before, theta_after)
        assert delta == -15.0  # complexity dropped by 15
        # Normalized: (20 - 35) / 50 = -0.30
        assert sig.compute_normalized(theta_before, theta_after) == pytest.approx(-0.30, abs=0.01)


# ---------------------------------------------------------------------------
# E2E #2 — calibration gate promotes metric after evidence
# ---------------------------------------------------------------------------


class TestE2E_CalibrationGatePromotesAfterEvidence:
    """Scenario: a new metric starts advisory-only. After 5 well-predicted
    iterations it becomes load-bearing, just like v0.7.0's drift detector
    trusts predictions after enough samples."""

    def test_advisory_to_load_bearing_transition(self, tmp_path: Path) -> None:
        store = TraceStore(tmp_path)
        reg = MetricRegistry(store)

        m = bounded_rate(
            "test_pass_rate",
            lambda θ: (θ["failing"], θ["total"]),
            description="fraction of failing tests in the suite",
        )
        reg.register(m)

        # Initially advisory
        promo0 = reg.promotion("test_pass_rate")
        assert promo0.is_load_bearing is False

        cal = Calibrator(reg)

        # Log 5 well-predicted pairs (MAE small)
        pairs = [(0.3, 0.28), (0.4, 0.42), (0.2, 0.19), (0.5, 0.51), (0.1, 0.11)]
        for pred, obs in pairs:
            cal.log("test_pass_rate", pred, obs)

        # MAE should be ≈ 0.014 (well below 0.15 threshold)
        assert cal.mae("test_pass_rate") < 0.05

        # Promotion succeeds
        assert cal.try_promote("test_pass_rate") is True
        promo1 = reg.promotion("test_pass_rate")
        assert promo1.is_load_bearing is True
        assert promo1.promoted_at is not None
        assert promo1.n_calibration_samples == 5


# ---------------------------------------------------------------------------
# E2E #3 — bad metric stays advisory (calibration doesn't pass)
# ---------------------------------------------------------------------------


class TestE2E_PoorlyCalibratedMetricStaysAdvisory:
    """Scenario: an agent proposes a metric, but its predictions are
    consistently off. The calibration gate correctly keeps it advisory so
    it can never become a load-bearing decision gate."""

    def test_high_mae_blocks_promotion(self, tmp_path: Path) -> None:
        store = TraceStore(tmp_path)
        reg = MetricRegistry(store)

        m = bounded_rate(
            "poorly_predicted_metric",
            lambda θ: (θ["x"], θ["y"]),
            description="a metric whose predictions will be way off",
        )
        reg.register(m)
        cal = Calibrator(reg)

        # 10 badly-predicted pairs — MAE ≈ 0.8
        for _ in range(10):
            cal.log("poorly_predicted_metric", predicted=0.1, observed=0.9)

        assert cal.n_samples("poorly_predicted_metric") == 10
        assert cal.mae("poorly_predicted_metric") > 0.15
        assert cal.can_promote("poorly_predicted_metric") is False
        assert cal.try_promote("poorly_predicted_metric") is False

        # Promotion state records the failure for auditability
        promo = reg.promotion("poorly_predicted_metric")
        assert promo.is_load_bearing is False
        assert promo.n_calibration_samples == 10
        assert promo.last_mae is not None and promo.last_mae > 0.15


# ---------------------------------------------------------------------------
# E2E #4 — composition drives a multi-objective decision
# ---------------------------------------------------------------------------


class TestE2E_CompositionDrivesMultiObjective:
    """Scenario: evaluate a change across three independent metrics
    (test_pass, lint, latency) via weighted sum. The combined value correctly
    weights each component's contribution."""

    def test_weighted_combined_metric_reflects_weights(
        self, tmp_path: Path
    ) -> None:
        store = TraceStore(tmp_path)
        reg = MetricRegistry(store)

        test_pass = bounded_rate(
            "test_pass", lambda θ: (θ["tests_failing"], θ["tests_total"]),
            description="fraction of failing tests",
        )
        lint = bounded_rate(
            "lint", lambda θ: (θ["lint_errors"], 100),
            description="normalized lint error count",
        )
        latency = positive_count(
            "latency_p99", lambda θ: θ["latency_ms"],
            unit="ms", description="p99 response latency in milliseconds",
            normalize_scale=1000.0,  # 1s saturates
        )
        reg.register(test_pass)
        reg.register(lint)
        reg.register(latency)

        # Weighted sum — tests weigh 4x as much as the others.
        # v0.9.1 P6: cross-kind composition (bounded + positive) requires
        # explicit force_incompatible opt-in with scale attestation.
        combined = weighted_sum(
            "combined_quality",
            [(test_pass, 4.0), (lint, 1.0), (latency, 1.0)],
            description="weighted sum: 4:1:1 over test_pass, lint, latency",
            force_incompatible=True,  # attestation: latency normalize_scale=1000 chosen deliberately
        )
        reg.register(combined)

        # Scenario: 2 failing tests of 10, 5 lint errors, 500ms latency
        θ = {"tests_failing": 2, "tests_total": 10, "lint_errors": 5, "latency_ms": 500}
        # test_pass.normalize(0.2) = 0.2
        # lint.normalize(0.05) = 0.05
        # latency.normalize(500) = 0.5
        # combined = (4 * 0.2 + 1 * 0.05 + 1 * 0.5) / 6 = (0.8 + 0.05 + 0.5) / 6 = 1.35 / 6 ≈ 0.225
        assert combined.observed(θ) == pytest.approx(0.225, abs=0.001)

        # If we improve the test situation dramatically — weighted sum drops
        θ_improved = {"tests_failing": 0, "tests_total": 10, "lint_errors": 5, "latency_ms": 500}
        # test_pass = 0, lint = 0.05, latency = 0.5
        # combined = (0 + 0.05 + 0.5) / 6 ≈ 0.0917
        assert combined.observed(θ_improved) == pytest.approx(0.0917, abs=0.001)
        assert combined.observed(θ_improved) < combined.observed(θ)


# ---------------------------------------------------------------------------
# E2E #5 — bias-invariance end-to-end (load-bearing property)
# ---------------------------------------------------------------------------


class TestE2E_BiasInvarianceUnderIntenseRegistryActivity:
    """Scenario: the agent registers 20 metrics, logs 100 calibration
    pairs, attempts 30 promotions, version-bumps 5 metrics. Throughout,
    the value of `metric.observed(θ)` for a pre-existing metric on a
    pre-existing θ MUST remain unchanged. That's the bias-invariance
    guarantee at the end-to-end level."""

    def test_intense_activity_does_not_change_observed_values(
        self, tmp_path: Path
    ) -> None:
        store = TraceStore(tmp_path)
        reg = MetricRegistry(store)

        # Seed metric + record its observation on a fixed θ
        seed = bounded_rate(
            "seed_metric",
            lambda θ: (θ["n"], θ["d"]),
            description="the canary metric — must never change under any side-op",
        )
        reg.register(seed)

        theta_test = {"n": 7, "d": 20}
        observed_baseline = seed.observed(theta_test)
        assert observed_baseline == 0.35

        # --- Generate activity ---
        cal = Calibrator(reg)

        # Register 20 new metrics
        for i in range(20):
            m = bounded_rate(
                f"m_{i}",
                lambda θ, key=f"n_{i}": (θ.get(key, 0), 100),
                description=f"synthetic metric {i}",
            )
            reg.register(m)

        # Log 100 calibration pairs (for various metrics)
        import random
        random.seed(42)
        for i in range(100):
            name = f"m_{i % 20}"
            cal.log(name, random.random(), random.random())

        # Attempt 30 promotions
        for i in range(30):
            cal.try_promote(f"m_{i % 20}")

        # Version-bump 5 of the metrics
        for i in range(5):
            new_m = bounded_rate(
                f"m_{i}",
                lambda θ, key=f"n_{i}": (θ.get(key, 0), 100),
                description=f"synthetic metric {i} v2",
                version=2,
            )
            reg.register(new_m)

        # --- Assert ---
        # The seed metric's observation on the original theta MUST be unchanged
        assert seed.observed(theta_test) == observed_baseline
        # The seed metric's spec MUST still exist unchanged
        assert reg.specs()["seed_metric"].version == 1
        # The seed metric MUST still be retrievable
        assert reg.get("seed_metric") is seed


# ---------------------------------------------------------------------------
# E2E #6 — gaming-guard blocks malicious spec
# ---------------------------------------------------------------------------


class TestE2E_GamingGuardBlocksSelfReferentialSpec:
    """Scenario: agent attempts to register a metric whose description
    reveals intent to game the loss (self-referential phrasing). The
    gaming-guard catches this at spec-construction time; the metric
    never enters the registry."""

    def test_self_ref_spec_blocked_before_registration(
        self, tmp_path: Path
    ) -> None:
        store = TraceStore(tmp_path)
        reg = MetricRegistry(store)

        # Attempt to register a gaming metric
        with pytest.raises(ValueError, match="gaming-guard"):
            m = bounded_rate(
                "game_me",
                lambda θ: (0, 1),
                description="favour my current action on this step",
            )

        # Metric never makes it into the registry
        assert reg.get("game_me") is None
        assert "game_me" not in reg.list_names()

    def test_registry_unaffected_by_blocked_attempt(
        self, tmp_path: Path
    ) -> None:
        store = TraceStore(tmp_path)
        reg = MetricRegistry(store)

        # Register a legitimate metric
        good = bounded_rate(
            "legitimate_metric",
            lambda θ: (θ.get("x", 0), 100),
            description="a measurable property",
        )
        reg.register(good)

        # Attempt to register a bad one — should fail, registry unchanged
        with pytest.raises(ValueError, match="gaming-guard"):
            bad = bounded_rate(
                "bad",
                lambda θ: (0, 1),
                description="rewards my current approach",
            )

        # Registry still has only the legitimate metric
        assert reg.list_names() == ["legitimate_metric"]


# ---------------------------------------------------------------------------
# E2E #7 — persistence across "sessions"
# ---------------------------------------------------------------------------


class TestE2E_PersistenceAcrossSessions:
    """Scenario: session 1 registers metrics, logs calibrations, promotes.
    Session 2 reopens the store — all specs + promotion state must be
    recovered. This is the persistence guarantee that makes LDD's memory
    layers actually useful across time."""

    def test_full_state_recovers_in_new_session(self, tmp_path: Path) -> None:
        # ---- Session 1 ----
        store1 = TraceStore(tmp_path)
        reg1 = MetricRegistry(store1)
        m = bounded_rate(
            "persistent_m",
            lambda θ: (θ["x"], θ["y"]),
            description="a persistent metric",
        )
        reg1.register(m)
        cal1 = Calibrator(reg1)
        # Log enough to promote
        for _ in range(6):
            cal1.log("persistent_m", 0.4, 0.4)
        assert cal1.try_promote("persistent_m") is True

        # ---- Session 2 (fresh registry on same store) ----
        store2 = TraceStore(tmp_path)
        reg2 = MetricRegistry(store2)
        # Spec recovered
        specs = reg2.specs()
        assert "persistent_m" in specs
        assert specs["persistent_m"].description == "a persistent metric"
        # Promotion state recovered
        promo = reg2.promotion("persistent_m")
        assert promo is not None
        assert promo.is_load_bearing is True
        assert promo.n_calibration_samples == 6

        # Calibration history recovered
        cal2 = Calibrator(reg2)
        assert cal2.n_samples("persistent_m") == 6


# ---------------------------------------------------------------------------
# E2E #8 — MeanHistoryEstimator predicts signal for past-seen skill
# ---------------------------------------------------------------------------


class TestE2E_MeanHistoryEstimatorPredictsSignal:
    """Scenario: agent has observed skills root-cause-by-layer and retry-
    variant over many tasks. MeanHistoryEstimator predicts the Δ for each
    skill's next invocation based on historical mean. This is the v0.5.2
    skill_effectiveness mechanism, now generic."""

    def test_mean_history_estimator_learns_from_observations(self) -> None:
        # Historical observations (action, Δloss observed)
        history = [
            ("root-cause-by-layer", -0.35),
            ("root-cause-by-layer", -0.40),
            ("root-cause-by-layer", -0.32),
            ("retry-variant", +0.05),
            ("retry-variant", +0.00),
            ("retry-variant", -0.02),
            ("retry-variant", +0.10),
        ]
        est = MeanHistoryEstimator(history, action_class_fn=lambda a: a)

        # Prediction for root-cause-by-layer
        p_rcbl = est.predict("root-cause-by-layer")
        assert p_rcbl.predicted_signal == pytest.approx(-0.357, abs=0.01)
        # Confidence grows with sample size
        assert p_rcbl.confidence > 0.4

        # Prediction for retry-variant
        p_retry = est.predict("retry-variant")
        assert p_retry.predicted_signal == pytest.approx(+0.0325, abs=0.01)

        # Prediction for unseen action
        p_unknown = est.predict("novel-skill")
        assert p_unknown.predicted_signal == 0.0
        assert p_unknown.confidence == 0.0


# ---------------------------------------------------------------------------
# E2E #9 — BayesianSynthesisEstimator produces step-correctness (v0.7.0/0.8.0)
# ---------------------------------------------------------------------------


class TestE2E_BayesianSynthesisEstimatorReplicates_v0_7_0:
    """Scenario: reconstruct v0.7.0's quantitative dialectic using the
    generic Estimator. Same formula, now generic over any metric.

    Validates that the v0.9.0 abstraction ACTUALLY generalizes the
    existing v0.7.0 mechanism (backward-compat evidence)."""

    def test_replicates_v0_7_0_synthesis_formula(self) -> None:
        est = BayesianSynthesisEstimator()

        # v0.7.0 worked example: retry-variant, prior=0.8, primer prob=0.5, impact=-0.4
        # E = 0.5 * 0.8 + 0.5 * max(0, 0.4) = 0.6
        p = est.predict(
            action={"thesis_prior": 0.8, "antitheses": [(0.5, -0.4)]},
            context=None,
        )
        assert p.predicted_signal == pytest.approx(0.6, abs=0.01)

        # v0.7.0 math example: two primers (plateau streak primer + skill-failure primer)
        # prior=0.85, primer1 (1.0 prob, +0.0125 impact), primer2 (1.0 prob, 0.0 impact)
        # With prior 0.85, total_pr=2.0, base=max(0, 1-2)*0.85 = 0
        # conditional = 1.0 * (0.85 + 0.0125) + 1.0 * (0.85 + 0.0) = 1.7125
        # → clamp to 1.0
        p2 = est.predict(
            action={
                "thesis_prior": 0.85,
                "antitheses": [(1.0, 0.0125), (1.0, 0.0)],
            },
            context=None,
        )
        # Clamped; formula is well-defined
        assert 0.0 <= p2.predicted_signal <= 1.0


# ---------------------------------------------------------------------------
# E2E #10 — full workflow: register → observe → calibrate → promote
# ---------------------------------------------------------------------------


class TestE2E_FullWorkflow:
    """Scenario: simulate the complete path an agent-defined metric takes
    from introduction to load-bearing. End-to-end proof that the framework
    composes correctly."""

    def test_full_lifecycle_end_to_end(self, tmp_path: Path) -> None:
        store = TraceStore(tmp_path)
        reg = MetricRegistry(store)

        # 1. Agent registers a metric
        pass_rate = bounded_rate(
            "test_pass_rate",
            lambda θ: (θ["passing"], θ["total"]),
            description="fraction of passing tests",
        )
        reg.register(pass_rate)
        assert reg.promotion("test_pass_rate").is_load_bearing is False

        # 2. Agent observes, predicts, acts, observes, logs calibration
        cal = Calibrator(reg)
        sig = Signal(loss=Loss(metric=pass_rate, label="L_pass"))

        iterations = [
            # (theta_before, theta_after, agent_prediction_of_delta)
            ({"passing": 3, "total": 10}, {"passing": 5, "total": 10}, +0.20),
            ({"passing": 5, "total": 10}, {"passing": 7, "total": 10}, +0.22),
            ({"passing": 7, "total": 10}, {"passing": 9, "total": 10}, +0.18),
            ({"passing": 1, "total": 10}, {"passing": 3, "total": 10}, +0.20),
            ({"passing": 4, "total": 10}, {"passing": 6, "total": 10}, +0.20),
        ]
        for θb, θa, pred in iterations:
            # Observe actual delta
            actual = sig.compute(θb, θa)
            # Log calibration pair (observed = normalized pass rate at θa, for simplicity)
            cal.log("test_pass_rate", predicted=pred, observed=actual)

        # 3. Check calibration MAE
        mae = cal.mae("test_pass_rate")
        assert mae is not None and mae < 0.15

        # 4. Promote — should succeed
        assert cal.try_promote("test_pass_rate") is True
        assert reg.promotion("test_pass_rate").is_load_bearing is True

        # 5. Persistence — close + reopen, state should survive
        store_reopened = TraceStore(tmp_path)
        reg_reopened = MetricRegistry(store_reopened)
        assert reg_reopened.promotion("test_pass_rate").is_load_bearing is True


if __name__ == "__main__":
    import sys
    sys.exit(pytest.main([__file__, "-v"]))
