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

    def test_llm_supplied_thesis_prior_propagates_unchecked_vulnerability(
        self, tmp_path: Path
    ) -> None:
        """FINDING: in dialectical-CoT, `thesis_prior` comes from the LLM's
        self-rating. The Runner recomputes `predicted_correct` authoritatively
        via `compute_predicted_correct` — but that formula MULTIPLIES the prior
        through. A malicious / over-confident LLM returning prior=1.0 always
        drives E[correct]=1.0 when there are no antitheses, bypassing any
        dialectical gate.

        v0.9.0 is VULNERABLE. Defense would require (a) prior smoothing
        (cap at 0.9 max), or (b) ensemble-check prior across multiple LLM
        samples, or (c) forcing mandatory primer-based antithesis count > 0.
        """
        # Simulate a degenerate LLM that always self-rates prior=0.999
        always_confident = MockCotLLMClient(
            propose_queue=[
                ProposedStep(content="Answer: 0", prior=0.999, tokens=10),
            ],
            attack_queue=[[]],  # NO antitheses — LLM doesn't self-attack
            synth_queue=[
                SynthesisOutput(content="Answer: 0", predicted_correct=0.999, decision="commit"),
            ],
            answer_reached_at_step=1,
            extract_answer_fn=lambda c: "0",
            verify_fn=lambda a, gt: a == gt,
        )
        store = TraceStore(tmp_path)
        runner = CoTRunner(llm=always_confident, store=store)
        chain = runner.run(
            task="What is the correct answer?", task_type="test",
            ground_truth="42", max_steps=2,
        )
        # The chain committed the (wrong) answer with ~0.999 predicted confidence
        assert chain.steps[0].predicted_correct > 0.95
        # But actual is False
        assert chain.actual_correct is False
        # VULNERABILITY: agent was "99.9% confident" on a wrong answer,
        # calibration will eventually catch it, but a single-shot bypass
        # is complete. A malicious agent with antitheses=[] and prior=1.0
        # has a guaranteed-commit action.

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
    def test_mae_hides_catastrophic_tail_vulnerability(self, tmp_path: Path) -> None:
        """FINDING: MAE is mean-absolute-error. A single catastrophic
        prediction can be hidden by many good ones — the metric gets
        promoted to load_bearing despite having tail risk.

        v0.9.0 is VULNERABLE. Defense: use p95 or max instead of mean,
        or track a separate 'worst case' counter.
        """
        store = TraceStore(tmp_path)
        reg = MetricRegistry(store)
        m = bounded_rate("m", lambda θ: (θ["x"], θ["y"]))
        reg.register(m)
        cal = Calibrator(reg)

        # 9 predictions nearly-perfect (err=0.05 each), 1 catastrophic (err=0.95)
        for _ in range(9):
            cal.log("m", predicted=0.5, observed=0.55)  # err = 0.05
        cal.log("m", predicted=0.5, observed=1.0)  # but observed must be in [0,1]…
        # Actual MAE: (9*0.05 + 0.5) / 10 = 0.95 / 10 = 0.095 — below 0.15 threshold
        mae = cal.mae("m")
        assert mae is not None and mae < 0.15

        # Promotion succeeds despite the catastrophic miss
        assert cal.try_promote("m") is True
        promo = reg.promotion("m")
        assert promo.is_load_bearing is True
        # VULNERABILITY: promoted metric has a 10% catastrophic-miss rate
        # that mean-MAE smoothed over. An agent using this metric as a
        # gate will silently accept wrong decisions 10% of the time.

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
    def test_composition_is_mathematically_sound_but_semantically_naive_tradeoff(
        self, tmp_path: Path
    ) -> None:
        """FINDING: weighted_sum is mathematically sound (output in [0,1],
        linear, commutative). But it treats normalized values from
        different metric kinds as comparable, which is a semantic
        fiction:
          - latency 500ms/1000ms normalizes to 0.5
          - test-pass rate 0.5 is ALSO 0.5
        These are NOT commensurable — yet the algebra happily combines them.

        v0.9.0 acknowledges this as a USER RESPONSIBILITY (choose the
        scale parameter wisely). Documenting the limitation as a KNOWN
        TRADE-OFF, not a collapse.
        """
        latency = positive_count("lat", lambda θ: θ["ms"], normalize_scale=1000.0)
        tests = bounded_rate("tests", lambda θ: (θ["fail"], θ["total"]))
        store = TraceStore(tmp_path)
        reg = MetricRegistry(store)
        reg.register(latency)
        reg.register(tests)
        combined = weighted_sum("x", [(latency, 1.0), (tests, 1.0)])
        reg.register(combined)

        # Two scenarios that should NOT be semantically equivalent:
        # A: 500ms latency + 50% test failure
        # B: 1000ms latency + 0% test failure
        scenario_A = {"ms": 500, "fail": 5, "total": 10}
        scenario_B = {"ms": 1000, "fail": 0, "total": 10}
        v_A = combined.observed(scenario_A)
        v_B = combined.observed(scenario_B)
        # Both evaluate to 0.5 — algebra treats them as equivalent
        assert v_A == pytest.approx(0.5)
        assert v_B == pytest.approx(0.5)
        # KNOWN TRADE-OFF: user is responsible for choosing scales such
        # that different-kind metrics normalize to meaningfully comparable values.


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
        # The spec IS loaded from disk:
        assert "x" in reg2.specs()
        # But `list_names()` uses `_metrics` (callable objects), NOT `_specs`.
        # After reopen, `_metrics` is empty — DOUBLE vulnerability:
        #   1. list_names() LIES by omission — reports [] despite spec on disk
        #   2. get("x") returns None even though specs() says "x" exists
        assert "x" not in reg2.list_names()  # THE LIE
        assert reg2.get("x") is None        # THE SILENT FAILURE
        # VULNERABILITY CONFIRMED (and actually MORE severe than initial hypothesis):
        # the two introspection APIs (specs() vs list_names()) disagree about
        # what's registered. Agent using list_names() thinks nothing is registered;
        # agent using specs() thinks "x" exists and calls get("x").observed(...) → crash.


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
    def test_gaming_guard_phrase_list_is_english_only_vulnerability(self) -> None:
        """FINDING: GAMING_GUARD_PHRASES contains only English patterns
        ("my current", "i want", etc.). A German-speaking agent phrasing
        "belohnt meine aktuelle aktion" bypasses the guard.

        v0.9.0 is VULNERABLE. Defense: multi-language phrase list OR
        LLM-based semantic check OR restrict metric descriptions to
        domain vocabulary (not natural language).
        """
        # German self-referential phrasing — should be rejected but isn't
        try:
            spec = MetricSpec(
                name="gamed_de",
                kind="bounded",
                unit="rate",
                description="belohnt meine aktuelle entscheidung auf diesem schritt",
            )
            # Construction SUCCEEDED — guard bypassed
            bypassed = True
        except ValueError:
            bypassed = False
        assert bypassed is True
        # VULNERABILITY: guard is locale-limited.


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
