"""Tests for dialectical chain-of-thought — v0.8.0.

Uses the deterministic MockCotLLMClient so tests are hermetic (no API calls).
Validates:
  - 5-step protocol runs per step (thesis → antithesis → synthesis → decide → log)
  - Decision thresholds (commit ≥ 0.7, revise 0.4-0.7, reject < 0.4) apply
  - Backtracking works and is budget-capped
  - Chain-level predicted_correct is product of per-step predicteds
  - cot_memory.json correctly aggregates per task-type
  - Calibration MAE + drift_warning fire on mis-predicted chains
  - Bias invariance: memory/primers never modify verify_answer outcome
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from ldd_trace import TraceStore
from ldd_trace.cot import (
    Antithesis,
    CoTChain,
    CoTRunner,
    ProposedStep,
    Step,
    SynthesisOutput,
    compute_predicted_correct,
    decide_from_predicted,
)
from ldd_trace.cot_llm import MockCotLLMClient
from ldd_trace.cot_memory import (
    _aggregate,
    append_chain_trace,
    cot_primers_for_task_type,
    read_chain_traces,
    read_cot_memory,
    update_cot_memory,
)


# ---------------------------------------------------------------------------
# Pure math — synthesis computation
# ---------------------------------------------------------------------------


class TestPredictedCorrectMath:
    def test_no_antitheses_returns_prior(self) -> None:
        assert compute_predicted_correct(0.8, []) == pytest.approx(0.8)

    def test_zero_impact_antithesis_does_not_change_prior(self) -> None:
        # Antithesis with impact=0 shouldn't alter expected correctness
        a = Antithesis(source="independent", content="spurious", prob_applies=0.5, impact=0.0)
        assert compute_predicted_correct(0.8, [a]) == pytest.approx(0.8)

    def test_negative_impact_lowers_expected_correctness(self) -> None:
        # prob=0.5 antithesis with impact=-0.4 should lower correctness
        a = Antithesis(
            source="independent", content="strong counter", prob_applies=0.5, impact=-0.4
        )
        result = compute_predicted_correct(0.8, [a])
        # E = 0.5 × 0.8 + 0.5 × max(0, 0.8 + -0.4) = 0.5×0.8 + 0.5×0.4 = 0.60
        assert result == pytest.approx(0.60, abs=0.01)

    def test_result_clamped_to_0_1(self) -> None:
        # Huge negative impact should clamp
        a = Antithesis(source="independent", content="catastrophic", prob_applies=1.0, impact=-2.0)
        assert compute_predicted_correct(0.5, [a]) == pytest.approx(0.0)

    def test_prob_clipped_when_sum_exceeds_1(self) -> None:
        # Two primers each with prob=0.7; total_pr > 1. Function should handle
        # without negative 'base' weight.
        primers = [
            Antithesis(source="primer", content="a", prob_applies=0.7, impact=-0.3),
            Antithesis(source="primer", content="b", prob_applies=0.7, impact=-0.3),
        ]
        result = compute_predicted_correct(0.8, primers)
        # Must be in [0, 1]
        assert 0.0 <= result <= 1.0


class TestDecisionThresholds:
    def test_commit_threshold(self) -> None:
        assert decide_from_predicted(0.95) == "commit"
        assert decide_from_predicted(0.70) == "commit"

    def test_revise_band(self) -> None:
        assert decide_from_predicted(0.69) == "revise"
        assert decide_from_predicted(0.40) == "revise"

    def test_reject_threshold(self) -> None:
        assert decide_from_predicted(0.39) == "reject"
        assert decide_from_predicted(0.0) == "reject"


# ---------------------------------------------------------------------------
# CoTRunner — happy path
# ---------------------------------------------------------------------------


def _make_llm_for_happy_path(
    n_steps: int = 3,
    answer: str = "42",
) -> MockCotLLMClient:
    """A scripted LLM that proposes `n_steps` confident steps with no antitheses."""
    proposed = [
        ProposedStep(content=f"Step {i}: intermediate reasoning", prior=0.9, tokens=10)
        for i in range(n_steps)
    ]
    # Last step contains the answer
    proposed[-1] = ProposedStep(
        content=f"Final answer: {answer}", prior=0.9, tokens=10
    )

    return MockCotLLMClient(
        propose_queue=proposed,
        attack_queue=[[] for _ in range(n_steps)],  # no antitheses
        synth_queue=[
            SynthesisOutput(content=p.content, predicted_correct=p.prior, decision="commit")
            for p in proposed
        ],
        answer_reached_at_step=n_steps,
        extract_answer_fn=lambda chain: answer,
        verify_fn=lambda ans, gt: ans == gt,
    )


class TestCoTRunnerHappyPath:
    def test_happy_path_3_steps_correct(self, tmp_path: Path) -> None:
        store = TraceStore(tmp_path)
        llm = _make_llm_for_happy_path(n_steps=3, answer="42")
        # v0.9.1 — legacy tests use empty antitheses; opt-out of strict requirement
        runner = CoTRunner(llm=llm, store=store, require_antithesis=False)
        chain = runner.run(
            task="test task", task_type="math", ground_truth="42", max_steps=10
        )
        assert chain.terminal == "complete"
        assert len(chain.steps) == 3
        assert chain.final_answer == "42"
        assert chain.actual_correct is True
        # predicted_chain_correct = 0.9^3 = 0.729
        assert chain.predicted_chain_correct == pytest.approx(0.729, abs=0.01)

    def test_trace_file_written(self, tmp_path: Path) -> None:
        store = TraceStore(tmp_path)
        llm = _make_llm_for_happy_path(n_steps=2, answer="x")
        # v0.9.1 — legacy tests use empty antitheses; opt-out of strict requirement
        runner = CoTRunner(llm=llm, store=store, require_antithesis=False)
        runner.run(task="t", task_type="test", ground_truth="x")
        traces_path = tmp_path / ".ldd" / "cot_traces.jsonl"
        assert traces_path.exists()
        content = traces_path.read_text().strip()
        assert content
        chain_dict = json.loads(content.split("\n")[-1])
        assert chain_dict["terminal"] == "complete"

    def test_memory_file_written(self, tmp_path: Path) -> None:
        store = TraceStore(tmp_path)
        llm = _make_llm_for_happy_path(n_steps=2, answer="x")
        # v0.9.1 — legacy tests use empty antitheses; opt-out of strict requirement
        runner = CoTRunner(llm=llm, store=store, require_antithesis=False)
        runner.run(task="t", task_type="test", ground_truth="x")
        mem_path = tmp_path / ".ldd" / "cot_memory.json"
        assert mem_path.exists()


# ---------------------------------------------------------------------------
# CoTRunner — antithesis-driven revision
# ---------------------------------------------------------------------------


class TestRevise:
    def test_step_revised_when_predicted_in_revise_band(self, tmp_path: Path) -> None:
        """If antitheses lower E[step correct] to 0.4-0.7, synthesis revises."""
        store = TraceStore(tmp_path)
        # Step 0: prior 0.8, one antithesis with prob=0.5 impact=-0.5 → E ≈ 0.5 → revise
        # Step 1: clean → commit
        proposed = [
            ProposedStep(content="Initial attempt", prior=0.8, tokens=10),
            ProposedStep(content="Answer: X", prior=0.9, tokens=10),
        ]
        antitheses = [
            [Antithesis(source="independent", content="maybe wrong direction",
                        prob_applies=0.5, impact=-0.5)],
            [],
        ]
        synth = [
            SynthesisOutput(content="Revised attempt", predicted_correct=0.5, decision="revise"),
            SynthesisOutput(content="Answer: X", predicted_correct=0.9, decision="commit"),
        ]
        llm = MockCotLLMClient(
            propose_queue=proposed,
            attack_queue=antitheses,
            synth_queue=synth,
            answer_reached_at_step=2,
            extract_answer_fn=lambda c: "X",
            verify_fn=lambda a, gt: True,
        )
        # v0.9.1 — legacy tests use empty antitheses; opt-out of strict requirement
        runner = CoTRunner(llm=llm, store=store, require_antithesis=False)
        chain = runner.run(task="t", task_type="logic", ground_truth="X")
        assert len(chain.steps) == 2
        assert chain.steps[0].decision == "revise"
        assert chain.steps[0].synthesis == "Revised attempt"
        assert chain.steps[1].decision == "commit"


# ---------------------------------------------------------------------------
# CoTRunner — backtracking
# ---------------------------------------------------------------------------


class TestBacktrack:
    def test_backtrack_on_rejected_step(self, tmp_path: Path) -> None:
        """Low E[step correct] (<0.4) triggers backtrack."""
        store = TraceStore(tmp_path)
        # First attempt: prior 0.5, antithesis prob=0.9 impact=-0.6 → E ≈ 0 → reject
        # Retry: prior 0.85, no antitheses → commit
        # Then: answer step
        proposed = [
            ProposedStep(content="Bad branch", prior=0.5, tokens=10),
            ProposedStep(content="Good branch", prior=0.85, tokens=10),
            ProposedStep(content="Answer: Y", prior=0.9, tokens=10),
        ]
        antitheses = [
            [Antithesis(source="independent", content="branch is wrong",
                        prob_applies=0.9, impact=-0.5)],
            [],
            [],
        ]
        synth = [
            SynthesisOutput(content="Bad", predicted_correct=0.05, decision="reject"),
            SynthesisOutput(content="Good", predicted_correct=0.85, decision="commit"),
            SynthesisOutput(content="Answer: Y", predicted_correct=0.9, decision="commit"),
        ]
        llm = MockCotLLMClient(
            propose_queue=proposed,
            attack_queue=antitheses,
            synth_queue=synth,
            answer_reached_at_step=2,
            extract_answer_fn=lambda c: "Y",
            verify_fn=lambda a, gt: True,
        )
        # v0.9.1 — legacy tests use empty antitheses; opt-out of strict requirement
        runner = CoTRunner(llm=llm, store=store, require_antithesis=False)
        chain = runner.run(task="t", task_type="logic", ground_truth="Y")
        assert chain.backtrack_count >= 1
        assert chain.terminal == "complete"
        assert chain.final_answer == "Y"

    def test_backtrack_budget_terminates_chain(self, tmp_path: Path) -> None:
        """Excess backtracks → chain terminates as partial."""
        store = TraceStore(tmp_path)
        # Every proposed step is terrible → every step rejected → backtrack cap
        proposed = [
            ProposedStep(content=f"Bad {i}", prior=0.1, tokens=10)
            for i in range(20)
        ]
        antitheses = [
            [Antithesis(source="independent", content="always wrong",
                        prob_applies=1.0, impact=-0.5)]
            for _ in range(20)
        ]
        synth = [
            SynthesisOutput(content=f"Bad {i}", predicted_correct=0.05, decision="reject")
            for i in range(20)
        ]
        llm = MockCotLLMClient(
            propose_queue=proposed,
            attack_queue=antitheses,
            synth_queue=synth,
        )
        runner = CoTRunner(llm=llm, store=store, max_backtracks=2, require_antithesis=False)
        chain = runner.run(task="t", task_type="hard", ground_truth=None, max_steps=10)
        assert chain.terminal == "partial"
        assert chain.backtrack_count > 2


# ---------------------------------------------------------------------------
# Chain-memory aggregation
# ---------------------------------------------------------------------------


class TestCotMemory:
    def _make_chain_dict(
        self,
        task_type: str,
        terminal: str,
        predicted: float,
        actual: bool,
        n_steps: int = 3,
        failure_mode: str = None,
    ) -> dict:
        """Synthesize a chain trace dict for aggregator testing."""
        steps = []
        for i in range(n_steps):
            step = {
                "k": i,
                "task_type": task_type,
                "thesis": f"step {i}",
                "thesis_prior": 0.8,
                "antitheses": [],
                "synthesis": f"step {i}",
                "predicted_correct": 0.8,
                "decision": "commit",
                "tokens": 10,
                "timestamp": "2026-04-21T00:00:00Z",
            }
            if failure_mode and i == n_steps - 1:
                # Simulate a revise step with failure-mode antithesis
                step["decision"] = "revise"
                step["antitheses"] = [
                    {
                        "source": "independent",
                        "content": failure_mode,
                        "prob_applies": 0.5,
                        "impact": -0.3,
                        "provenance": "llm",
                    }
                ]
            steps.append(step)
        return {
            "task": "synthetic",
            "task_type": task_type,
            "ground_truth": None,
            "steps": steps,
            "final_answer": "X",
            "predicted_chain_correct": predicted,
            "actual_correct": actual,
            "total_tokens": 30,
            "backtrack_count": 0,
            "terminal": terminal,
            "started_at": "2026-04-21T00:00:00Z",
            "ended_at": "2026-04-21T00:00:01Z",
        }

    def test_aggregate_empty(self) -> None:
        mem = _aggregate([])
        assert mem["n_chains"] == 0
        assert mem["by_task_type"] == {}

    def test_aggregate_partitions_by_task_type(self) -> None:
        traces = [
            self._make_chain_dict("math", "complete", 0.8, True),
            self._make_chain_dict("math", "complete", 0.7, True),
            self._make_chain_dict("code", "complete", 0.9, True),
        ]
        mem = _aggregate(traces)
        assert "math" in mem["by_task_type"]
        assert "code" in mem["by_task_type"]
        assert mem["by_task_type"]["math"]["n_chains"] == 2
        assert mem["by_task_type"]["code"]["n_chains"] == 1

    def test_calibration_mae_computed(self) -> None:
        # predicted=0.8 actual=1.0 → err=0.2
        # predicted=0.6 actual=0.0 → err=0.6
        # predicted=0.9 actual=1.0 → err=0.1
        # MAE = (0.2+0.6+0.1)/3 = 0.30
        traces = [
            self._make_chain_dict("math", "complete", 0.8, True),
            self._make_chain_dict("math", "failed", 0.6, False),
            self._make_chain_dict("math", "complete", 0.9, True),
        ]
        mem = _aggregate(traces)
        calib = mem["by_task_type"]["math"]["calibration"]
        assert calib["n_predictions"] == 3
        assert calib["mae"] == pytest.approx(0.30, abs=0.01)

    def test_drift_warning_fires(self) -> None:
        # 5 chains all mis-predicted by > 0.15
        traces = [
            self._make_chain_dict("math", "failed", 0.9, False)  # err=0.9 each
            for _ in range(5)
        ]
        mem = _aggregate(traces)
        calib = mem["by_task_type"]["math"]["calibration"]
        assert calib["drift_warning"] is True

    def test_drift_warning_silent_below_n(self) -> None:
        # Only 3 chains — below COT_DRIFT_MIN_N=5
        traces = [
            self._make_chain_dict("math", "failed", 0.9, False)
            for _ in range(3)
        ]
        mem = _aggregate(traces)
        calib = mem["by_task_type"]["math"]["calibration"]
        assert calib["drift_warning"] is False

    def test_failure_modes_harvested(self) -> None:
        traces = [
            self._make_chain_dict("math", "complete", 0.8, True,
                                  failure_mode="off-by-one error")
            for _ in range(3)
        ]
        mem = _aggregate(traces)
        failures = mem["by_task_type"]["math"]["common_failure_modes"]
        assert len(failures) >= 1
        assert "off-by-one error" in failures[0]["pattern"]
        assert failures[0]["count"] == 3


# ---------------------------------------------------------------------------
# Primer generation from cot_memory
# ---------------------------------------------------------------------------


class TestCotPrimers:
    def test_empty_memory_returns_no_primers(self, tmp_path: Path) -> None:
        store = TraceStore(tmp_path)
        primers = cot_primers_for_task_type(store, task_type="math")
        assert primers == []

    def test_failure_mode_becomes_primer(self, tmp_path: Path) -> None:
        store = TraceStore(tmp_path)
        # Write synthetic traces with failure modes
        for _ in range(3):
            chain_dict = TestCotMemory._make_chain_dict(
                TestCotMemory(), "math", "complete", 0.8, True,
                failure_mode="sign-error-in-substitution"
            )
            traces_path = store.trace_dir / "cot_traces.jsonl"
            store.ensure_dir()
            with traces_path.open("a") as f:
                f.write(json.dumps(chain_dict) + "\n")
        update_cot_memory(store)

        primers = cot_primers_for_task_type(store, task_type="math")
        assert any("sign-error" in p.content for p in primers)
        assert all(p.source == "primer" for p in primers)

    def test_no_cross_task_type_leakage(self, tmp_path: Path) -> None:
        """Primers from task_type=math must NOT feed into task_type=code queries."""
        store = TraceStore(tmp_path)
        # Seed memory with math failure modes
        for _ in range(3):
            chain_dict = TestCotMemory._make_chain_dict(
                TestCotMemory(), "math", "complete", 0.8, True,
                failure_mode="math-specific-error"
            )
            traces_path = store.trace_dir / "cot_traces.jsonl"
            store.ensure_dir()
            with traces_path.open("a") as f:
                f.write(json.dumps(chain_dict) + "\n")
        update_cot_memory(store)

        primers_for_code = cot_primers_for_task_type(store, task_type="code")
        assert primers_for_code == [], (
            f"code task should not get math primers; got {primers_for_code}"
        )


# ---------------------------------------------------------------------------
# Bias-invariance — memory never modifies verify_answer outcome
# ---------------------------------------------------------------------------


class TestBiasInvariance:
    def test_memory_does_not_affect_verification(self, tmp_path: Path) -> None:
        """Even with rich memory, verify_answer stays pure — the correct
        answer is determined by ground_truth alone."""
        store = TraceStore(tmp_path)

        # Seed with memory that might bias toward one answer
        for _ in range(5):
            chain_dict = TestCotMemory._make_chain_dict(
                TestCotMemory(), "test", "complete", 0.95, True,
                failure_mode="whatever"
            )
            traces_path = store.trace_dir / "cot_traces.jsonl"
            store.ensure_dir()
            with traces_path.open("a") as f:
                f.write(json.dumps(chain_dict) + "\n")
        update_cot_memory(store)

        # Now run a chain that produces a WRONG final answer.
        # The memory suggests high confidence — but verification must be based
        # ONLY on ground truth.
        llm = MockCotLLMClient(
            propose_queue=[ProposedStep(content="Final answer: wrong", prior=0.9, tokens=10)],
            attack_queue=[[]],
            synth_queue=[SynthesisOutput(content="Final answer: wrong", predicted_correct=0.9, decision="commit")],
            answer_reached_at_step=1,
            extract_answer_fn=lambda c: "wrong",
            verify_fn=lambda ans, gt: ans == gt,  # strict equality
        )
        # v0.9.1 — legacy tests use empty antitheses; opt-out of strict requirement
        runner = CoTRunner(llm=llm, store=store, require_antithesis=False)
        chain = runner.run(
            task="t", task_type="test", ground_truth="correct", max_steps=3
        )
        # Despite the rich memory, verification must return False
        assert chain.actual_correct is False
        assert chain.terminal == "failed"

    def test_predicted_correct_decoupled_from_ground_truth_access(
        self, tmp_path: Path
    ) -> None:
        """predicted_chain_correct must depend ONLY on step-level predictions,
        not on the eventual outcome."""
        store = TraceStore(tmp_path)
        llm = MockCotLLMClient(
            propose_queue=[
                ProposedStep(content="Answer: A", prior=0.8, tokens=10),
            ],
            attack_queue=[[]],
            synth_queue=[
                SynthesisOutput(content="Answer: A", predicted_correct=0.8, decision="commit"),
            ],
            answer_reached_at_step=1,
            extract_answer_fn=lambda c: "A",
            verify_fn=lambda ans, gt: False,  # force wrong
        )
        # v0.9.1 — legacy tests use empty antitheses; opt-out of strict requirement
        runner = CoTRunner(llm=llm, store=store, require_antithesis=False)
        chain = runner.run(task="t", task_type="x", ground_truth="B", max_steps=3)
        # predicted should be the per-step compute, independent of the (wrong) actual
        assert chain.predicted_chain_correct == pytest.approx(0.8, abs=0.01)
        assert chain.actual_correct is False


# ---------------------------------------------------------------------------
# CLI — smoke tests (invocation, error messaging)
# ---------------------------------------------------------------------------


class TestCoTCLISmoke:
    def _run(self, *args: str) -> subprocess.CompletedProcess:
        env = {"PYTHONPATH": str(Path(__file__).resolve().parent.parent)}
        return subprocess.run(
            [sys.executable, "-m", "ldd_trace", *args],
            env=env, capture_output=True, text=True, check=False,
        )

    def test_cot_subcommand_in_help(self) -> None:
        r = self._run("--help")
        assert r.returncode == 0
        assert " cot " in r.stdout or "cot\n" in r.stdout

    def test_cot_run_without_api_key_errors_gracefully(self, tmp_path: Path) -> None:
        """Without OPENROUTER_API_KEY, `cot run` should fail with a clear message,
        not crash."""
        r = subprocess.run(
            [
                sys.executable, "-m", "ldd_trace", "cot", "run",
                "--project", str(tmp_path),
                "--task", "t",
            ],
            env={"PYTHONPATH": str(Path(__file__).resolve().parent.parent)},
            capture_output=True, text=True, check=False,
        )
        assert r.returncode == 1
        assert "OPENROUTER_API_KEY" in r.stderr

    def test_cot_health_without_traces_errors_gracefully(self, tmp_path: Path) -> None:
        r = self._run("cot", "health", "--project", str(tmp_path))
        assert r.returncode == 1
        assert "cot_memory" in r.stderr or "cot run" in r.stderr


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
