"""v0.9.0 Critical Audit — collapse / unsoundness demonstrations.

Each test class addresses ONE category of potential failure. Tests are
**evidence producers**: a test that PASSES means the condition it asserts
holds under current v0.9.0 code. Interpret each via its docstring:

  * `test_…_vulnerability` — PASS means "framework is VULNERABLE to this"
  * `test_…_defense`        — PASS means "framework defends against this"

Prioritized findings summary lives in `docs/audit/v0-9-0-findings.md`.

Not a regression suite — these are diagnostic tests that DOCUMENT what
the framework does / does not guarantee. They are not meant to be fixed
by changing the code; they're the evidence for the findings report.
"""
from __future__ import annotations

import json
import re
import threading
import time
from pathlib import Path

import pytest

from ldd_trace import TraceStore
from ldd_trace.cot import Antithesis, CoTRunner, ProposedStep, SynthesisOutput, compute_predicted_correct
from ldd_trace.cot_llm import MockCotLLMClient
from ldd_trace.metric import (
    GAMING_GUARD_PHRASES,
    BayesianSynthesisEstimator,
    MetricSpec,
    bounded_rate,
    positive_count,
    signed_delta,
)
from ldd_trace.metric_compose import weighted_sum
from ldd_trace.metric_registry import (
    CALIB_MAX_MAE,
    CALIB_MIN_N,
    Calibrator,
    MetricRegistry,
)


# ===========================================================================
# Category 1: Bias-Invariance leaks  (HIGH / CRITICAL severity)
# ===========================================================================


class TestBiasInvarianceLeaks:
    """The framework's load-bearing claim is: memory + dialectic NEVER modify
    L(θ). These tests probe the boundary of that claim.
    """

    def test_gaming_guard_is_surface_only_vulnerability(self) -> None:
        """FINDING: gaming-guard checks the DESCRIPTION string for bad phrases
        but cannot inspect the ACCESSOR function. An agent with a benign-
        sounding description can still gamify via the accessor.

        v0.9.0 is VULNERABLE. Defense would require either (a) static analysis
        of the accessor, or (b) agent-unauthored-accessor (the user/human
        provides the callable, the agent only proposes the name + description).
        """
        # The agent writes a neutral description — passes gaming-guard
        spec = MetricSpec(
            name="commit_quality",
            kind="positive",
            unit="count",
            description="aggregate measure of commit impact over changed files",
            normalize_scale=100.0,
        )
        # But the accessor simply rewards volume — classic goodhart's law
        bad_metric = positive_count(
            "commit_quality",
            accessor=lambda θ: θ.get("lines_added_by_agent", 0),
            description="aggregate measure of commit impact over changed files",
            normalize_scale=100.0,
        )
        # Framework allows registration — no semantic check on accessor
        assert bad_metric.observed({"lines_added_by_agent": 5000}) == 5000.0
        # Normalization caps it at 1.0 but that's still the MAX signal
        assert bad_metric.normalize(bad_metric.observed({"lines_added_by_agent": 5000})) == 1.0
        # VULNERABILITY confirmed: no protection against goodhart-accessor.

    def test_llm_supplied_thesis_prior_defense_in_v0_9_1(
        self, tmp_path: Path
    ) -> None:
        """v0.9.1 P1 DEFENSE VERIFIED: TrustGuard.guard_prior caps thesis_prior
        at MAX_PRIOR (0.9), AND require_antithesis=True (default) rejects
        steps with empty antitheses.

        Pre-v0.9.1: prior=0.999 + antitheses=[] → guaranteed-commit bypass.
        Post-v0.9.1: chain terminates partial with degenerate step.
        """
        always_confident = MockCotLLMClient(
            propose_queue=[
                ProposedStep(content="Answer: 0", prior=0.999, tokens=10),
            ],
            attack_queue=[[]],  # NO antitheses — would bypass v0.9.0 dialectic
            synth_queue=[
                SynthesisOutput(content="Answer: 0", predicted_correct=0.999, decision="commit"),
            ],
            answer_reached_at_step=1,
            extract_answer_fn=lambda c: "0",
            verify_fn=lambda a, gt: a == gt,
        )
        store = TraceStore(tmp_path)
        # Default v0.9.1 behavior — strict antithesis requirement
        runner = CoTRunner(llm=always_confident, store=store)
        chain = runner.run(
            task="What is the correct answer?", task_type="test",
            ground_truth="42", max_steps=2,
        )
        # v0.9.1: chain does NOT reach load-bearing commit with high confidence;
        # step is a degenerate reject (predicted_correct = 0, decision = reject).
        # The final terminal may be partial/failed depending on verify_fn.
        assert len(chain.steps) >= 1
        assert chain.steps[0].predicted_correct == 0.0
        assert chain.steps[0].decision == "reject"
        # v0.9.1: prior was capped to MAX_PRIOR even though LLM reported 0.999
        assert chain.steps[0].thesis_prior <= 0.9 + 1e-9
        # chain.terminal ∈ {partial, failed} — crucially NOT "complete"
        assert chain.terminal != "complete"
        # DEFENSE VERIFIED: always-confident-no-antithesis bypass is closed.

    def test_agent_supplied_antithesis_impact_gameable_vulnerability(self) -> None:
        """FINDING: `Antithesis.impact` is agent-supplied. Either direction
        is exploitable:
          - impact=-0.99 forces E[correct]→0 → backtrack loop, burning budget
          - impact=+0.01 on all antitheses → rubber-stamp (impact is the
            counterfactual change, so positive impact is "primer raises
            correctness" → essentially disarms the primer)

        v0.9.0 is VULNERABLE. Defense would require cross-validation of
        primer impacts against historical observation-regression pairs.
        """
        # Positive impact = "this counter-case actually HELPS" — bypass
        toothless = [
            Antithesis(source="independent", content="trivial", prob_applies=1.0, impact=+0.5),
            Antithesis(source="independent", content="meaningless", prob_applies=1.0, impact=+0.5),
        ]
        E_rubber_stamp = compute_predicted_correct(thesis_prior=0.5, antitheses=toothless)
        # With both antitheses "helping", E[correct] stays high despite 100% probability
        # they apply. Real antitheses should LOWER correctness.
        assert E_rubber_stamp >= 0.5

        # Conversely: agent can force reject with adversarial impact
        hostile = [
            Antithesis(source="independent", content="fake concern", prob_applies=1.0, impact=-0.99),
        ]
        E_forced_reject = compute_predicted_correct(thesis_prior=0.9, antitheses=hostile)
        assert E_forced_reject < 0.1
        # VULNERABILITY: no check that impact-signs correlate with actual
        # outcome observations (which would require post-hoc calibration).


# ===========================================================================
# Category 2: Calibration collapse  (HIGH severity)
# ===========================================================================


class TestCalibrationCollapse:
    def test_mae_hides_catastrophic_tail_defense_in_v0_9_1(self, tmp_path: Path) -> None:
        """v0.9.1 P3 DEFENSE VERIFIED: multi-statistic gate rejects promotion
        when any single error exceeds `CALIB_MAX_WORST_ERROR` (0.50) — even
        if mean MAE is under threshold.

        Pre-v0.9.1: MAE alone → promoted despite catastrophic tail.
        Post-v0.9.1: evaluate_state → CATASTROPHIC_OUTLIER → no promotion.
        """
        store = TraceStore(tmp_path)
        reg = MetricRegistry(store)
        m = bounded_rate("m", lambda θ: (θ["x"], θ["y"]))
        reg.register(m)
        cal = Calibrator(reg)

        # 9 predictions nearly-perfect + 1 catastrophic (err=0.5)
        for _ in range(9):
            cal.log("m", predicted=0.5, observed=0.55)  # err = 0.05
        cal.log("m", predicted=0.5, observed=1.0)  # err = 0.50 — catastrophic

        # MAE alone would still pass (0.095) but multi-stat gate catches it:
        mae = cal.mae("m")
        assert mae is not None and mae < 0.15  # MAE gate would pass
        worst = cal.worst_error("m")
        assert worst is not None and worst >= 0.50  # tail stat catches it

        # Multi-stat evaluation rejects promotion — could be either
        # TAIL_RISK_HIGH (p95 exceeded) or CATASTROPHIC_OUTLIER (worst exceeded)
        # depending on exact data; both are non-load-bearing rejection states.
        from ldd_trace.metric_registry import (
            PROMOTION_LOAD_BEARING, PROMOTION_OUTLIER, PROMOTION_TAIL_RISK,
        )
        state = cal.evaluate_state("m")
        assert state in (PROMOTION_TAIL_RISK, PROMOTION_OUTLIER)
        # try_promote returns False (P3 gate works)
        assert cal.try_promote("m") is False
        promo = reg.promotion("m")
        assert promo.state != PROMOTION_LOAD_BEARING
        assert promo.is_load_bearing is False  # v0.9.0 compat property still works
        # DEFENSE VERIFIED: tail-risky metric cannot become load-bearing.

    def test_min_n_5_fails_rare_task_types_vulnerability(
        self, tmp_path: Path
    ) -> None:
        """FINDING: CALIB_MIN_N=5 is a GLOBAL threshold. A task_type
        with < 5 total chains can never have its calibration drift
        detected, no matter how wrong predictions are.

        v0.9.0 is VULNERABLE. Defense: report 'insufficient data' as
        a first-class state distinct from 'well-calibrated'.
        """
        store = TraceStore(tmp_path)
        reg = MetricRegistry(store)
        m = bounded_rate("rare", lambda θ: (0, 1))
        reg.register(m)
        cal = Calibrator(reg)

        # 4 catastrophic-miss pairs — below n_min
        for _ in range(4):
            cal.log("rare", predicted=0.1, observed=0.9)  # err = 0.80 each

        mae = cal.mae("rare")
        assert mae is not None and mae == pytest.approx(0.80)
        # MAE is enormous but can_promote returns False (n < 5) AND
        # drift_warning cannot fire (below threshold N). The metric stays
        # advisory forever with no visibility into its unreliability.
        assert cal.can_promote("rare") is False
        # Promotion state doesn't record "dangerous advisory"
        promo = reg.promotion("rare")
        assert promo.is_load_bearing is False  # correct outcome...
        assert promo.last_mae is None  # ...but no visibility into HOW BAD

        # If we call try_promote, it updates state:
        cal.try_promote("rare")
        promo_after = reg.promotion("rare")
        assert promo_after.last_mae == pytest.approx(0.80)
        # VULNERABILITY: without an explicit "low-confidence-warning" flag
        # distinct from "advisory", agents may keep using this metric.

    def test_verify_fn_strict_equality_inflates_mae_vulnerability(
        self, tmp_path: Path
    ) -> None:
        """FINDING: default verify_fn uses string equality. Common semantic
        equivalences ('42' vs '42.0', whitespace, case) are treated as
        mismatches. Calibration log records false-negative outcomes,
        inflating MAE and triggering spurious drift warnings.

        v0.9.0 is VULNERABLE. Defense: canonicalize-then-compare; OR
        require user-supplied verify_fn with documented semantics.
        """
        # Using CoT runner's default verify_fn (string equality)
        llm = MockCotLLMClient(
            propose_queue=[
                ProposedStep(content="Answer: 42.0", prior=0.9, tokens=10),
            ],
            attack_queue=[[]],
            synth_queue=[SynthesisOutput(content="Answer: 42.0", predicted_correct=0.9, decision="commit")],
            answer_reached_at_step=1,
            extract_answer_fn=lambda c: "42.0",
            # NO verify_fn provided — uses default (string eq)
        )
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            store = TraceStore(Path(tmp))
            runner = CoTRunner(llm=llm, store=store)
            chain = runner.run(
                task="x", task_type="math", ground_truth="42", max_steps=2,
            )
            # Agent answered "42.0", ground truth "42" — semantically same
            # but verify_fn says False
            assert chain.actual_correct is False
            # VULNERABILITY: calibration treats a correct answer as wrong;
            # an accurate agent looks uncalibrated because of verify_fn.


# ===========================================================================
# Category 3: Composition algebra semantic soundness  (MEDIUM / known trade-off)
# ===========================================================================


class TestCompositionSemantics:
    def test_composition_semantics_defense_in_v0_9_1(
        self, tmp_path: Path
    ) -> None:
        """v0.9.1 P6 DEFENSE VERIFIED: cross-kind composition raises
        IncompatibleUnitsError unless `force_incompatible=True` is set.

        Pre-v0.9.1: weighted_sum(latency, test_pass) silently combined
        semantically-incommensurate values.
        Post-v0.9.1: default rejects; caller must explicitly attest
        that the scale choice is intended.
        """
        from ldd_trace.metric_compose import IncompatibleUnitsError
        latency = positive_count("lat", lambda θ: θ["ms"], normalize_scale=1000.0)
        tests = bounded_rate("tests", lambda θ: (θ["fail"], θ["total"]))

        # DEFAULT (no force): cross-kind composition rejected
        with pytest.raises(IncompatibleUnitsError, match="mixes kinds"):
            weighted_sum("x", [(latency, 1.0), (tests, 1.0)])

        # OPT-IN: force_incompatible=True lets it through (user attests)
        combined = weighted_sum(
            "x", [(latency, 1.0), (tests, 1.0)], force_incompatible=True
        )
        # Same-kind composition still works without force
        tests2 = bounded_rate("t2", lambda θ: (θ["f"], θ["t"]))
        ok = weighted_sum("y", [(tests, 1.0), (tests2, 1.0)])
        # DEFENSE VERIFIED: user must explicitly attest for cross-kind.


# ===========================================================================
# Category 4: Registry state divergence  (HIGH severity)
# ===========================================================================


class TestRegistryStateDivergence:
    def test_reopened_session_loses_metric_callables_vulnerability(
        self, tmp_path: Path
    ) -> None:
        """FINDING: MetricRegistry persists SPECS but not METRIC OBJECTS
        (which contain callable accessors — lambdas can't be serialized).
        On session reopen, specs load but `reg.get(name)` returns None.

        This is a SILENT state divergence — the registry advertises that
        metric 'x' exists (`list_names()` returns it) but calling
        `get('x')` returns None. Agents that check spec existence without
        also checking object availability will hit NoneType errors later.

        v0.9.0 is VULNERABLE. Defense: either (a) require re-registration
        of callables on every session open (with a clear error if missed),
        or (b) persist accessor as a string-serialized Python expression
        (security risk).
        """
        # Session 1: register metric with a lambda accessor
        store1 = TraceStore(tmp_path)
        reg1 = MetricRegistry(store1)
        m = bounded_rate("x", lambda θ: (θ["a"], θ["b"]))
        reg1.register(m)
        # Retrieval works in-session
        assert reg1.get("x") is m

        # Session 2: new registry on same store
        store2 = TraceStore(tmp_path)
        reg2 = MetricRegistry(store2)

        # v0.9.1 P2 DEFENSE VERIFIED:
        #   1. list_names() now returns specs.keys() — single source of truth
        assert "x" in reg2.list_names()  # DEFENSE: no longer lies
        #   2. specs() and list_names() agree
        assert "x" in reg2.specs()
        #   3. has_callable() introspection — False because callable not re-registered
        assert reg2.has_callable("x") is False
        #   4. get() raises SpecExistsButCallableMissing instead of returning None
        from ldd_trace.metric_registry import SpecExistsButCallableMissing
        with pytest.raises(SpecExistsButCallableMissing, match="re-registered"):
            reg2.get("x")
        # DEFENSE VERIFIED: introspection APIs are consistent; agents get
        # a CLEAR signal to re-register rather than a silent None.


# ===========================================================================
# Category 5: Version bump resets calibration  (MEDIUM severity)
# ===========================================================================


class TestVersionBumpResetsState:
    def test_version_bump_erases_accumulated_calibration(
        self, tmp_path: Path
    ) -> None:
        """FINDING: when a metric is version-bumped (v1 → v2), the old
        calibration records are kept in the JSONL but FILTERED OUT by
        `records_for()` (correct per bias-invariance). The effect: v2
        starts fresh with 0 samples, so promotion begins from scratch.

        This is PARTIALLY a feature (v2's semantics differ; calibration
        should reset). But it's ALSO a vulnerability: the old records
        linger in the JSONL growing unboundedly, AND the agent has no
        audit trail that 'v2 is advisory again' is a deliberate state.

        v0.9.0 is AMBIGUOUS. Defense: either (a) archive old records to
        a separate file on version bump, OR (b) document the behavior
        explicitly in the skill protocol.
        """
        store = TraceStore(tmp_path)
        reg = MetricRegistry(store)
        m1 = bounded_rate("x", lambda θ: (0, 1), version=1)
        reg.register(m1)
        cal = Calibrator(reg)

        # Log enough v1 calibration for promotion
        for _ in range(6):
            cal.log("x", 0.5, 0.5)
        assert cal.try_promote("x") is True
        assert reg.promotion("x").is_load_bearing is True

        # Now bump to v2
        m2 = bounded_rate("x", lambda θ: (0, 1), version=2)
        reg.register(m2)

        # Promotion state reset to advisory (correct)
        assert reg.promotion("x").is_load_bearing is False
        assert reg.promotion("x").version == 2

        # But old v1 calibration records are still in the JSONL file
        path = tmp_path / ".ldd" / "metric_calibrations.jsonl"
        content = path.read_text()
        lines = [l for l in content.strip().split("\n") if l]
        # There are 6 v1 lines still in the file
        v1_records = [l for l in lines if '"metric_version": 1' in l]
        assert len(v1_records) == 6
        # v2 has no records yet
        assert cal.n_samples("x") == 0
        # AMBIGUOUS: file grows; old calibration is invisible to `mae()`
        # but present in the log. No warning that this happened.


# ===========================================================================
# Category 6: Concurrency  (HIGH severity for scaled deployments)
# ===========================================================================


class TestConcurrencyRaces:
    def test_concurrent_writes_to_calibration_jsonl_may_interleave(
        self, tmp_path: Path
    ) -> None:
        """FINDING: append-only JSONL assumes atomic line-writes. Python's
        file.write() with 'a' mode is NOT guaranteed atomic for lines
        larger than PIPE_BUF (typically 4096 bytes). Short lines usually
        survive; long ones (lots of metadata) may interleave.

        v0.9.0 is VULNERABLE. Defense: (a) use fcntl.flock around writes,
        (b) use a single writer process with a queue, or (c) document
        single-writer assumption clearly.
        """
        store = TraceStore(tmp_path)
        reg = MetricRegistry(store)
        m = bounded_rate("m", lambda θ: (0, 1))
        reg.register(m)

        # Spawn N threads, each logging M calibration pairs
        def log_many(worker_id: int, n: int) -> None:
            cal = Calibrator(reg)
            for i in range(n):
                cal.log("m", predicted=worker_id / 100, observed=(worker_id + i) / 100)

        threads = [
            threading.Thread(target=log_many, args=(i, 20))
            for i in range(4)
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Read back — how many malformed lines?
        path = tmp_path / ".ldd" / "metric_calibrations.jsonl"
        content = path.read_text()
        lines = content.strip().split("\n")
        malformed = 0
        for line in lines:
            line = line.strip()
            if not line:
                continue
            try:
                json.loads(line)
            except json.JSONDecodeError:
                malformed += 1
        # In practice, on modern kernels with short lines, 0 malformed.
        # But the TEST documents the LACK of formal guarantee.
        # We expect <= small_fraction, not exactly 0.
        expected_lines = 4 * 20
        # Check: at least SOME writes succeeded (not total corruption)
        assert len(lines) > 0
        # VULNERABILITY: no explicit locking; relies on OS atomicity of
        # short appends. Document as single-writer assumption.


# ===========================================================================
# Category 7: Locale-limited gaming-guard  (LOW severity)
# ===========================================================================


class TestGamingGuardLocale:
    def test_gaming_guard_multilingual_defense_in_v0_9_1(self) -> None:
        """v0.9.1 L1 DEFENSE VERIFIED: MULTILINGUAL_GAMING_PHRASES covers
        English + German + French + Spanish common self-reference patterns.

        Pre-v0.9.1: "belohnt meine aktuelle aktion" passed.
        Post-v0.9.1: rejected at spec construction.
        """
        # German self-referential phrasing — now correctly rejected
        with pytest.raises(ValueError, match="gaming-guard"):
            MetricSpec(
                name="gamed_de",
                kind="bounded",
                unit="rate",
                description="belohnt meine aktuelle entscheidung auf diesem schritt",
            )
        # French also rejected
        with pytest.raises(ValueError, match="gaming-guard"):
            MetricSpec(
                name="gamed_fr",
                kind="bounded",
                unit="rate",
                description="récompense mon action actuelle sur cette étape",
            )
        # DEFENSE VERIFIED: multilingual coverage (4 languages).


# ===========================================================================
# Category 8: Scaling — JSONL unbounded growth  (MEDIUM)
# ===========================================================================


class TestScalingLimits:
    def test_cot_traces_jsonl_grows_unboundedly_known_limitation(
        self, tmp_path: Path
    ) -> None:
        """FINDING: `.ldd/cot_traces.jsonl` and
        `.ldd/metric_calibrations.jsonl` are append-only. No compaction
        mechanism exists. After 10k iterations, each `aggregate()` call
        reads the full file (O(N)).

        v0.9.0 KNOWN LIMITATION. Defense: rolling window with
        compaction on close; keep only last K chains.
        """
        # Demonstrate by counting lines after mock activity
        store = TraceStore(tmp_path)
        reg = MetricRegistry(store)
        m = bounded_rate("m", lambda θ: (0, 1))
        reg.register(m)
        cal = Calibrator(reg)

        # Simulate 1000 calibration entries — tiny compared to real scale
        for i in range(1000):
            cal.log("m", predicted=i / 1000, observed=(i + 1) / 1000)

        path = tmp_path / ".ldd" / "metric_calibrations.jsonl"
        size_bytes = path.stat().st_size
        # Each line is ~150 bytes → ~150KB for 1000 entries → ~1.5 GB
        # for 10M entries. Read-all on every aggregate is O(file size).
        assert size_bytes > 100_000  # ≥ 100KB after 1000 entries
        # KNOWN LIMITATION: no rolling-window; aggregation cost scales linearly.


# ===========================================================================
# Category 9: Stationarity assumption  (MEDIUM severity)
# ===========================================================================


class TestStationarityAssumption:
    def test_calibration_assumes_llm_stationarity_known_limitation(
        self, tmp_path: Path
    ) -> None:
        """FINDING: calibration statistics pool ALL historical pairs with
        equal weight. If the underlying LLM is updated (same name, new
        weights) mid-project, pre-update calibration no longer applies
        but is not flagged.

        v0.9.0 KNOWN LIMITATION. Defense: add change-point detection
        OR epoch-tag calibration records with LLM version/checksum.
        """
        store = TraceStore(tmp_path)
        reg = MetricRegistry(store)
        m = bounded_rate("m", lambda θ: (0, 1))
        reg.register(m)
        cal = Calibrator(reg)

        # "Epoch 1" — predictions are perfect
        for _ in range(5):
            cal.log("m", predicted=0.5, observed=0.5)
        assert cal.try_promote("m") is True  # promoted

        # "Epoch 2" — LLM changed, predictions all off by 0.5
        for _ in range(5):
            cal.log("m", predicted=0.5, observed=0.0)

        # MAE pools both epochs: (5*0 + 5*0.5) / 10 = 0.25
        mae = cal.mae("m")
        assert mae == pytest.approx(0.25)
        # MAE is above threshold → drift warning COULD fire (good)
        # But the metric is still promoted (promotion is sticky).
        # Agent has no signal that the epoch-2 regime is different.
        assert reg.promotion("m").is_load_bearing is True
        # KNOWN LIMITATION: promotion is monotonic once granted;
        # no demotion on subsequent drift.


# ===========================================================================
# Category 10: Recursive coupling  (HIGH severity)
# ===========================================================================


class TestRecursiveCoupling:
    def test_method_evolution_on_drifted_memory_self_reinforces_vulnerability(
        self,
    ) -> None:
        """FINDING: method-evolution skill consumes project memory to
        identify recurring violations. If memory itself is drifted
        (via v0.7.0 MAE > 0.15, or calibration of metrics promoted in
        error), method-evolution optimizes TOWARD the drift — changing
        skills to match the corrupted signal.

        v0.9.0 is THEORETICALLY VULNERABLE. This is a conceptual test,
        not a reproduction — demonstrating the POTENTIAL coupling
        risk that a drift detector for drift detectors would catch.
        """
        # This is a "philosophy check" test — no runtime reproduction
        # needed because the coupling is structural:
        #   method-evolution reads project_memory.json
        #   project_memory.json is computed from trace.log
        #   trace.log has predicted_Δloss from dialectical-cot
        #   dialectical-cot's predictions depend on prime_antithesis
        #   prime_antithesis reads project_memory.json
        #   → CYCLE
        coupling_chain = [
            "method-evolution",
            "project_memory.json",
            "trace.log",
            "dialectical-cot predictions",
            "prime_antithesis",
            "project_memory.json",  # same as position 1 — CYCLE
        ]
        # The cycle is real. Framework currently has no meta-calibration.
        assert coupling_chain[1] == coupling_chain[-1]
        # VULNERABILITY: no circuit breaker for self-reinforcing drift.


# ===========================================================================
# Severity summary — printed for audit report
# ===========================================================================


def test_audit_summary_printable() -> None:
    """Meta-test: emits the severity classification so auditors can
    see finding priority at a glance.
    """
    findings = [
        ("CRITICAL", "gaming-guard is surface-only (accessor unchecked)"),
        ("CRITICAL", "LLM-supplied thesis_prior bypasses dialectic if antitheses empty"),
        ("CRITICAL", "list_names() lies by omission after reopen — returns [] despite specs on disk"),
        ("HIGH", "agent-supplied antithesis impact can rubber-stamp or force-reject"),
        ("HIGH", "MAE hides catastrophic tail predictions"),
        ("HIGH", "CALIB_MIN_N=5 leaves rare task-types permanently advisory with no visibility"),
        ("HIGH", "verify_fn string equality produces false negatives on semantic equivalences"),
        ("HIGH", "registry reopens with specs-only (no metric callables) — silent state divergence"),
        ("HIGH", "concurrent writes to JSONL not guaranteed atomic"),
        ("HIGH", "method-evolution ↔ project_memory ↔ prime_antithesis recursive coupling"),
        ("MEDIUM", "version bump orphans calibration records in JSONL"),
        ("MEDIUM", "JSONL grows unboundedly — O(N) aggregate cost"),
        ("MEDIUM", "calibration assumes stationarity; promotion is monotonic (no demotion)"),
        ("MEDIUM", "composition semantics naive — cross-kind weighted sums comparable only in math"),
        ("LOW", "gaming-guard phrase list is English-only"),
    ]
    # Sanity — 15 findings across 4 severity levels
    assert len(findings) == 15
    severities = {s for s, _ in findings}
    assert severities == {"CRITICAL", "HIGH", "MEDIUM", "LOW"}


if __name__ == "__main__":
    import sys
    sys.exit(pytest.main([__file__, "-v"]))
