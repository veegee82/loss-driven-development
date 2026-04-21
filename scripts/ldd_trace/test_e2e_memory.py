"""End-to-end validation for the memory layer (aggregator + retrieval).

Validates three use cases the user called out in v0.5.2 design:
  1. **Plateau detection** — can memory flag a stalled iteration cycle?
  2. **Wrong-decision detection** — does memory warn when about to invoke a
     skill that historically regresses?
  3. **Retrospective against narralog** — if we had had this memory at
     iteration 3 of the narralog task, would it have flagged the plateau?

Run with:
    PYTHONPATH=scripts python -m pytest scripts/ldd_trace/test_e2e_memory.py -v
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from ldd_trace import TraceStore
from ldd_trace.aggregator import aggregate, aggregate_and_write, read_memory
from ldd_trace.retrieval import (
    check_in_flight,
    suggest_skills,
    similar_tasks,
)


# ---------------------------------------------------------------------------
# Fixture: synthetic 10-task project with known characteristics
# ---------------------------------------------------------------------------


def _populate_synthetic_project(tmp_path: Path) -> TraceStore:
    """Create 10 past tasks with deliberately varied characteristics.

    Design of the synthetic distribution:
      - 6 tasks close in 2 iterations (typical quick bugs)
      - 3 tasks close in 4 iterations (harder)
      - 1 task aborts at k=5 (plateau then timeout)
      - skill `reproducibility-first` appears 10× with Δ near 0 (it does not
        reduce loss directly — it checks reproducibility; true to its role)
      - skill `root-cause-by-layer` appears 9× with Δ ≈ -0.35 (the workhorse)
      - skill `e2e-driven-iteration` appears 9× with Δ ≈ -0.20
      - skill `retry-variant` appears 3× with Δ ≈ +0.05 (bad idea)
      - 2-plateau runs are always resolved by `root-cause-by-layer` in this
        corpus → memory should learn this pattern.
    """
    store = TraceStore(tmp_path)
    store.init(task_title="synthetic-base", loops=["inner"])

    def task(title: str, terminal: str, sequence: list[tuple[str, str, float]]) -> None:
        """Record one synthetic task.

        `sequence` items: (skill, action, loss_norm). First item is baseline.
        """
        store.init(task_title=title, loops=["inner"])
        for i, (skill, action, loss) in enumerate(sequence):
            store.append_iteration(
                loop="inner",
                k=i,
                skill=skill,
                action=action,
                loss_norm=loss,
                raw=f"{int(loss * 10)}/10",
                loss_type="rate",
                baseline=(i == 0),
            )
        store.append_close(loop="inner", terminal=terminal, layer="3: auto-gen", docs="synced")

    # 6 quick-close tasks (k=2)
    for i in range(6):
        task(
            f"quick-bug-{i}",
            "complete",
            [
                ("baseline", "scaffold", 1.0),
                ("reproducibility-first", "verified 3/3 fail", 1.0),
                ("root-cause-by-layer", "layer-4 fix", 0.0),
            ],
        )

    # 3 harder tasks (k=4)
    for i in range(3):
        task(
            f"hard-bug-{i}",
            "complete",
            [
                ("baseline", "scaffold", 1.0),
                ("reproducibility-first", "check reproduce", 1.0),
                ("e2e-driven-iteration", "first attempt", 0.6),
                ("retry-variant", "naive retry", 0.65),  # regression
                ("root-cause-by-layer", "real fix", 0.0),
            ],
        )

    # 1 aborted task — 2 plateau iterations then terminal=aborted
    task(
        "gnarly-bug-0",
        "aborted",
        [
            ("baseline", "scaffold", 1.0),
            ("reproducibility-first", "check", 1.0),
            ("e2e-driven-iteration", "patch-and-hope", 1.0),
            ("retry-variant", "another retry", 1.0),
        ],
    )

    # 2 plateau-broken-by-root-cause tasks — these exercise the plateau-
    # resolution-pattern detector: ≥ 2 consecutive plateau iterations
    # followed by a non-plateau resolver. In this synthetic distribution
    # root-cause-by-layer is always the resolver.
    for i in range(2):
        task(
            f"plateau-then-rcbl-{i}",
            "complete",
            [
                ("baseline", "scaffold", 1.0),
                ("reproducibility-first", "verify 5/5 reproduce", 1.0),
                ("e2e-driven-iteration", "naive attempt", 1.0),
                ("retry-variant", "plateau continues", 1.0),
                ("root-cause-by-layer", "real fix at layer-4", 0.0),
            ],
        )

    return store


# ---------------------------------------------------------------------------
# Test 1 — aggregator correctness (bias guards, sanity numbers)
# ---------------------------------------------------------------------------


class TestAggregatorBiasGuards:
    def test_terminal_distribution_includes_all_states(self, tmp_path: Path) -> None:
        """SURVIVORSHIP GUARD: terminal_distribution must include aborted
        tasks, not only 'complete'.

        Synthetic project has 11 complete (6 quick + 3 hard + 2 plateau-rcbl)
        and 1 aborted = 12 total.
        """
        store = _populate_synthetic_project(tmp_path)
        memory = aggregate(store)
        td = memory["terminal_distribution"]
        assert "complete" in td, f"got {td}"
        assert "aborted" in td, f"aborted task not counted: {td}"
        assert td["complete"]["count"] == 11
        assert td["aborted"]["count"] == 1

    def test_skill_stats_split_by_terminal(self, tmp_path: Path) -> None:
        """SURVIVORSHIP GUARD: per-skill stats must expose the by_terminal
        breakdown so callers can't silently select complete-only."""
        store = _populate_synthetic_project(tmp_path)
        memory = aggregate(store)
        retry = memory["skill_effectiveness"].get("retry-variant", {})
        assert "by_terminal" in retry
        # retry-variant appears in BOTH complete (hard-bug-N) and aborted paths
        assert "complete" in retry["by_terminal"]
        assert "aborted" in retry["by_terminal"]

    def test_relative_delta_computed(self, tmp_path: Path) -> None:
        """REGRESSION-TO-MEAN GUARD: relative Δ must be present alongside absolute."""
        store = _populate_synthetic_project(tmp_path)
        memory = aggregate(store)
        rcbl = memory["skill_effectiveness"]["root-cause-by-layer"]
        assert "delta_mean_abs" in rcbl
        assert "delta_mean_relative" in rcbl
        # Both should be non-zero negatives for this skill
        assert rcbl["delta_mean_abs"] < -0.1
        assert rcbl["delta_mean_relative"] < -0.1

    def test_windows_both_reported(self, tmp_path: Path) -> None:
        """RECENCY-DRIFT GUARD: both lifetime and last-30-days windows shown."""
        store = _populate_synthetic_project(tmp_path)
        memory = aggregate(store)
        assert "lifetime" in memory["window"]
        assert "last_30_days" in memory["window"]

    def test_bias_guard_metadata_present(self, tmp_path: Path) -> None:
        """Explicit bias_guards block documents what's done."""
        store = _populate_synthetic_project(tmp_path)
        memory = aggregate(store)
        guards = memory["bias_guards"]
        for key in ("survivorship", "regression_to_mean", "recency_drift", "confirmation"):
            assert key in guards, f"missing bias guard: {key}"


# ---------------------------------------------------------------------------
# Test 2 — aggregator derived metrics match expected synthetic distribution
# ---------------------------------------------------------------------------


class TestAggregatorMetrics:
    def test_task_shape_matches_design(self, tmp_path: Path) -> None:
        """6 quick (k=2) + 3 hard (k=4) + 1 aborted (k=3) + 2 plateau-rcbl (k=4)
        → 12 tasks, sum_k=35, mean_k≈2.92"""
        store = _populate_synthetic_project(tmp_path)
        memory = aggregate(store)
        shape = memory["task_shape"]["overall"]
        assert shape["n"] == 12
        assert 2.7 <= shape["mean_k"] <= 3.1

    def test_retry_variant_has_elevated_failure_signature(self, tmp_path: Path) -> None:
        """`retry-variant` is designed as the worst skill: it appears in
        hard-bug runs (Δ=+0.05 regression) AND in plateau-rcbl + aborted
        runs (Δ=0 plateau). Both regression and plateau are no-progress
        signals — combined they should show ≥ 80% no-progress rate.
        """
        store = _populate_synthetic_project(tmp_path)
        memory = aggregate(store)
        retry = memory["skill_effectiveness"]["retry-variant"]
        no_progress = retry["regression_rate"] + retry["plateau_rate"]
        assert no_progress >= 0.8, (
            f"retry-variant should have ≥80% no-progress (reg+pla); got {retry}"
        )

    def test_plateau_resolution_pattern_detected(self, tmp_path: Path) -> None:
        """Hard-bug tasks contain a plateau broken by root-cause-by-layer.
        Aggregator should identify this resolution pattern."""
        store = _populate_synthetic_project(tmp_path)
        memory = aggregate(store)
        plateau_patterns = memory["plateau_resolution_patterns"]
        # Expect at least one "after_N_consecutive_plateaus" bucket
        assert len(plateau_patterns) >= 1, (
            f"no plateau patterns detected; got {plateau_patterns}"
        )


# ---------------------------------------------------------------------------
# Test 3 — retrieval.suggest ranks sensibly
# ---------------------------------------------------------------------------


class TestSkillSuggestion:
    def test_workhorse_skill_ranks_above_bad_skill(self, tmp_path: Path) -> None:
        """root-cause-by-layer should rank above retry-variant."""
        store = _populate_synthetic_project(tmp_path)
        memory = aggregate(store)
        suggestions = suggest_skills(memory, top_n=10)
        ranked_names = [s.skill for s in suggestions if s.n_invocations >= 3]
        assert "root-cause-by-layer" in ranked_names
        assert "retry-variant" in ranked_names
        rcbl_idx = ranked_names.index("root-cause-by-layer")
        retry_idx = ranked_names.index("retry-variant")
        assert rcbl_idx < retry_idx, (
            f"root-cause-by-layer ({rcbl_idx}) should rank above "
            f"retry-variant ({retry_idx}) in: {ranked_names}"
        )


# ---------------------------------------------------------------------------
# Test 4 — plateau detection on in-flight task (THE KEY USE CASE)
# ---------------------------------------------------------------------------


class TestPlateauDetection:
    def test_in_flight_plateau_triggers_warning(self, tmp_path: Path) -> None:
        """Simulate an in-flight task with 2 consecutive plateau iterations.
        `check_in_flight` should fire a 'plateau' warning AND cite historical
        resolver skills from project memory."""
        store = _populate_synthetic_project(tmp_path)
        aggregate_and_write(store)
        memory = read_memory(store)

        # Now simulate a NEW in-flight task with a plateau pattern
        store.init(task_title="current-in-flight-task", loops=["inner"])
        store.append_iteration(
            loop="inner", k=0, skill="baseline", action="scaffold",
            loss_norm=1.0, raw="5/5", loss_type="rate", baseline=True,
        )
        store.append_iteration(
            loop="inner", k=1, skill="reproducibility-first",
            action="check reproduce", loss_norm=1.0, raw="5/5", loss_type="rate",
        )
        store.append_iteration(
            loop="inner", k=2, skill="e2e-driven-iteration",
            action="first attempt", loss_norm=1.0, raw="5/5", loss_type="rate",
        )

        current = store.current_task()
        warnings = check_in_flight(memory, current)
        kinds = [w.kind for w in warnings]
        assert "plateau" in kinds, (
            f"plateau warning should fire after 2 consecutive Δ≈0; got warnings: {warnings}"
        )
        # The warning should cite historical resolvers
        plateau_warn = next(w for w in warnings if w.kind == "plateau")
        assert "root-cause-by-layer" in plateau_warn.message.lower() or plateau_warn.severity in ("warn", "high")

    def test_healthy_task_produces_no_warnings(self, tmp_path: Path) -> None:
        """A task making progress should NOT trigger plateau warnings."""
        store = _populate_synthetic_project(tmp_path)
        aggregate_and_write(store)
        memory = read_memory(store)

        store.init(task_title="healthy-task", loops=["inner"])
        store.append_iteration(
            loop="inner", k=0, skill="baseline", action="scaffold",
            loss_norm=1.0, raw="5/5", loss_type="rate", baseline=True,
        )
        store.append_iteration(
            loop="inner", k=1, skill="reproducibility-first",
            action="verify", loss_norm=0.8, raw="4/5", loss_type="rate",
        )
        store.append_iteration(
            loop="inner", k=2, skill="root-cause-by-layer",
            action="good fix", loss_norm=0.2, raw="1/5", loss_type="rate",
        )

        current = store.current_task()
        warnings = check_in_flight(memory, current)
        plateau_warnings = [w for w in warnings if w.kind == "plateau"]
        assert not plateau_warnings, (
            f"healthy task should not trigger plateau warnings; got {warnings}"
        )


# ---------------------------------------------------------------------------
# Test 5 — wrong-decision detection
# ---------------------------------------------------------------------------


class TestWrongDecisionDetection:
    def test_regressive_next_skill_warns(self, tmp_path: Path) -> None:
        """Memory should warn when the next planned skill has a high
        historical regression rate."""
        store = _populate_synthetic_project(tmp_path)
        aggregate_and_write(store)
        memory = read_memory(store)

        store.init(task_title="new-task", loops=["inner"])
        store.append_iteration(
            loop="inner", k=0, skill="baseline", action="scaffold",
            loss_norm=1.0, raw="5/5", loss_type="rate", baseline=True,
        )
        store.append_iteration(
            loop="inner", k=1, skill="reproducibility-first",
            action="check", loss_norm=1.0, raw="5/5", loss_type="rate",
        )

        current = store.current_task()
        warnings = check_in_flight(
            memory, current, next_planned_skill="retry-variant"
        )
        kinds = [w.kind for w in warnings]
        assert "wrong_decision" in kinds, (
            f"should warn when planning a regressive skill; got {warnings}"
        )

    def test_good_next_skill_no_warn(self, tmp_path: Path) -> None:
        """Planning a well-performing skill should not produce a wrong_decision warning."""
        store = _populate_synthetic_project(tmp_path)
        aggregate_and_write(store)
        memory = read_memory(store)

        store.init(task_title="new-task-2", loops=["inner"])
        store.append_iteration(
            loop="inner", k=0, skill="baseline", action="scaffold",
            loss_norm=1.0, raw="5/5", loss_type="rate", baseline=True,
        )

        current = store.current_task()
        warnings = check_in_flight(
            memory, current, next_planned_skill="root-cause-by-layer"
        )
        wrong_decision_warns = [w for w in warnings if w.kind == "wrong_decision"]
        assert not wrong_decision_warns, (
            f"good skill should not warn; got {warnings}"
        )


# ---------------------------------------------------------------------------
# Test 6 — over-budget warning
# ---------------------------------------------------------------------------


class TestOverBudgetDetection:
    def test_over_p95_warns(self, tmp_path: Path) -> None:
        """If current k exceeds project p95_k, warn about escalation."""
        store = _populate_synthetic_project(tmp_path)
        aggregate_and_write(store)
        memory = read_memory(store)

        # Synthetic project has max k=4 (p95 ≈ 4). Task at k=5 should warn.
        store.init(task_title="overrunning-task", loops=["inner"])
        store.append_iteration(
            loop="inner", k=0, skill="baseline", action="scaffold",
            loss_norm=1.0, raw="5/5", loss_type="rate", baseline=True,
        )
        for i in range(1, 6):
            store.append_iteration(
                loop="inner", k=i, skill="e2e-driven-iteration",
                action=f"try {i}", loss_norm=max(0.2, 1.0 - 0.1 * i),
                raw=f"{int(max(1, 5 - i))}/5", loss_type="rate",
            )

        current = store.current_task()
        warnings = check_in_flight(memory, current)
        kinds = [w.kind for w in warnings]
        assert "over_budget" in kinds, (
            f"should warn when k exceeds p95; got {warnings}"
        )


# ---------------------------------------------------------------------------
# Test 7 — retrospective against narralog trace
# ---------------------------------------------------------------------------


class TestRetrospectiveNarralog:
    """Load the real narralog trace (/tmp/ldd/task_1_invention/.ldd/trace.log)
    and verify: given a hypothetical prior memory where plateau-resolvers
    are known, would memory have flagged the narralog i3 plateau?"""

    NARRALOG_TRACE_PATH = Path("/tmp/ldd/task_1_invention/.ldd/trace.log")

    def test_narralog_trace_exists(self) -> None:
        """Sanity: the narralog trace must be present from v0.5.1 session."""
        if not self.NARRALOG_TRACE_PATH.exists():
            pytest.skip(f"narralog trace not available at {self.NARRALOG_TRACE_PATH}")
        # If it exists, verify it parses
        from ldd_trace.store import TraceStore
        store = TraceStore(self.NARRALOG_TRACE_PATH.parent.parent)
        tasks = store.segment_tasks()
        assert len(tasks) >= 1, "expected at least one task in narralog trace"

    def test_narralog_at_i4_would_be_flagged(self, tmp_path: Path) -> None:
        """Retrospective: the real narralog trace hit 1 plateau at i3
        (Δ=0.000 from i2=0.031 to i3=0.031). Memory-threshold is ≥ 2
        consecutive plateaus — so i3 alone would not have warned (correct
        — one plateau is noise, not signal).

        The interesting counterfactual: *if* agent had attempted a 2nd
        iteration of the same compression-engineering approach at i4
        (instead of jumping to method-evolution), memory would have caught
        the 2nd plateau and cited historical resolvers.

        This test validates that threshold behavior: narralog's actual i3
        correctly does NOT trigger (avoid false-positive), but a simulated
        i4 continuing the plateau WOULD trigger with resolver hint.
        """
        if not self.NARRALOG_TRACE_PATH.exists():
            pytest.skip("narralog trace not available")

        # Step 1: build a prior memory with plateau patterns
        store = _populate_synthetic_project(tmp_path)
        aggregate_and_write(store)
        memory = read_memory(store)
        assert memory is not None

        # Step 2a — at narralog's real i3: only 1 plateau at tail. No warning.
        store.init(task_title="narralog-sim-i3", loops=["inner"])
        for k, (loss, skill) in enumerate([
            (0.344, "baseline"),
            (0.094, "e2e-driven-iteration"),
            (0.031, "e2e-driven-iteration"),
            (0.031, "e2e-driven-iteration"),  # first plateau at tail (streak=1)
        ]):
            store.append_iteration(
                loop="inner", k=k, skill=skill, action=f"iter {k}",
                loss_norm=loss, raw=f"{int(loss*32)}/32", loss_type="rate",
                baseline=(k == 0),
            )
        warnings = check_in_flight(memory, store.current_task())
        plateau_warnings_at_i3 = [w for w in warnings if w.kind == "plateau"]
        assert not plateau_warnings_at_i3, (
            f"at i3 streak=1, should NOT fire (false-positive guard); "
            f"got {plateau_warnings_at_i3}"
        )

        # Step 2b — simulate the counterfactual i4: agent continues same skill.
        # Now the plateau streak becomes 2 and memory must warn.
        store.init(task_title="narralog-sim-i4", loops=["inner"])
        for k, (loss, skill) in enumerate([
            (0.344, "baseline"),
            (0.094, "e2e-driven-iteration"),
            (0.031, "e2e-driven-iteration"),
            (0.031, "e2e-driven-iteration"),
            (0.031, "e2e-driven-iteration"),  # 2nd plateau → streak=2
        ]):
            store.append_iteration(
                loop="inner", k=k, skill=skill, action=f"iter {k}",
                loss_norm=loss, raw=f"{int(loss*32)}/32", loss_type="rate",
                baseline=(k == 0),
            )
        warnings = check_in_flight(memory, store.current_task())
        kinds = [w.kind for w in warnings]
        assert "plateau" in kinds, (
            f"at counterfactual i4 streak=2, memory MUST flag plateau; "
            f"got {[(w.kind, w.severity, w.message) for w in warnings]}"
        )
        # And the warning should cite at least one resolver skill name
        plateau_w = next(w for w in warnings if w.kind == "plateau")
        assert "root-cause-by-layer" in plateau_w.message, (
            f"expected plateau warning to cite root-cause-by-layer "
            f"(synthetic distribution's typical resolver); got: {plateau_w.message}"
        )


if __name__ == "__main__":
    import sys
    sys.exit(pytest.main([__file__, "-v"]))
