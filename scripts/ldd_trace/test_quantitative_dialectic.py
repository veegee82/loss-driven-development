"""Tests for the v0.7.0 quantitative-dialectic support layer.

The protocol lives in `skills/dialectical-reasoning/SKILL.md`; these tests
verify the code plumbing that feeds it:
  - `append --predicted-delta X` records the predicted Δloss
  - `prediction_error = predicted - actual` is computed and stored
  - aggregator surfaces `calibration.mean_abs_error` and `drift_warning`
  - health render includes calibration block
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from ldd_trace import TraceStore
from ldd_trace.aggregator import aggregate, aggregate_and_write, read_memory
from ldd_trace.retrieval import format_health


class TestPredictedDelta:
    def test_predicted_delta_is_recorded(self, tmp_path: Path) -> None:
        store = TraceStore(tmp_path)
        store.init(task_title="demo", loops=["inner"])
        store.append_iteration(
            loop="inner", k=0, skill="baseline", action="stub",
            loss_norm=1.0, raw="5/5", loss_type="rate", baseline=True,
        )
        entry = store.append_iteration(
            loop="inner", k=1, skill="root-cause-by-layer",
            action="fix", loss_norm=0.5, raw="2/5", loss_type="rate",
            predicted_delta=-0.4,
        )
        assert "predicted_Δloss" in entry.fields
        assert "-0.400" in entry.fields["predicted_Δloss"]
        # actual Δ = 0.5 - 1.0 = -0.5; prediction = -0.4; error = -0.4 - (-0.5) = +0.1
        assert "prediction_error" in entry.fields
        assert "+0.100" in entry.fields["prediction_error"]

    def test_omitting_predicted_delta_is_graceful(self, tmp_path: Path) -> None:
        """Existing callers that don't provide --predicted-delta should still work."""
        store = TraceStore(tmp_path)
        store.init(task_title="demo", loops=["inner"])
        entry = store.append_iteration(
            loop="inner", k=0, skill="baseline", action="stub",
            loss_norm=1.0, raw="5/5", loss_type="rate", baseline=True,
        )
        assert "predicted_Δloss" not in entry.fields
        assert "prediction_error" not in entry.fields


class TestCalibrationAggregate:
    def _build_project_with_predictions(
        self, tmp_path: Path, predictions: list[tuple[float, float]]
    ) -> TraceStore:
        """Build a project with N tasks, each having one iteration with
        (predicted_Δ, actual_Δ) = predictions[i]."""
        store = TraceStore(tmp_path)
        for i, (pred, actual) in enumerate(predictions):
            store.init(task_title=f"task-{i}", loops=["inner"])
            # Baseline at loss=1.0
            store.append_iteration(
                loop="inner", k=0, skill="baseline", action="stub",
                loss_norm=1.0, raw="5/5", loss_type="rate", baseline=True,
            )
            # Actual iteration: loss = 1.0 + actual (actual is Δ)
            store.append_iteration(
                loop="inner", k=1, skill="root-cause-by-layer",
                action="fix", loss_norm=1.0 + actual, raw="x/5",
                loss_type="rate", predicted_delta=pred,
            )
            store.append_close(
                loop="inner", terminal="complete", layer="n/a", docs="n/a",
            )
        return store

    def test_calibration_computed_when_predictions_present(self, tmp_path: Path) -> None:
        # 3 tasks with pred=-0.4, actual: -0.35, -0.50, -0.40
        # errors: +0.05, -0.10, ±0.0
        # mean|err| = (0.05 + 0.10 + 0.0) / 3 = 0.050
        store = self._build_project_with_predictions(
            tmp_path,
            [(-0.4, -0.35), (-0.4, -0.50), (-0.4, -0.40)],
        )
        memory = aggregate(store)
        calib = memory["calibration"]
        assert calib["n_predictions"] == 3
        assert 0.04 <= calib["mean_abs_error"] <= 0.06
        assert calib["drift_warning"] is False

    def test_drift_warning_fires_on_poor_calibration(self, tmp_path: Path) -> None:
        # 5 tasks with pred=-0.4, all actual=0.0 → error=-0.4 each → mean|err|=0.4
        store = self._build_project_with_predictions(
            tmp_path,
            [(-0.4, 0.0)] * 5,
        )
        memory = aggregate(store)
        calib = memory["calibration"]
        assert calib["n_predictions"] == 5
        assert calib["mean_abs_error"] > 0.15
        assert calib["drift_warning"] is True

    def test_no_predictions_produces_empty_calibration(self, tmp_path: Path) -> None:
        store = TraceStore(tmp_path)
        store.init(task_title="demo", loops=["inner"])
        store.append_iteration(
            loop="inner", k=0, skill="baseline", action="stub",
            loss_norm=1.0, raw="5/5", loss_type="rate", baseline=True,
        )
        store.append_close(loop="inner", terminal="complete", layer="x", docs="x")
        memory = aggregate(store)
        calib = memory["calibration"]
        assert calib["n_predictions"] == 0
        assert calib["mean_abs_error"] is None
        assert calib["drift_warning"] is False


class TestHealthRendersCalibration:
    def test_health_shows_calibration_block_when_predictions_exist(self, tmp_path: Path) -> None:
        store = TraceStore(tmp_path)
        for i in range(3):
            store.init(task_title=f"t-{i}", loops=["inner"])
            store.append_iteration(
                loop="inner", k=0, skill="baseline", action="stub",
                loss_norm=1.0, raw="5/5", loss_type="rate", baseline=True,
            )
            store.append_iteration(
                loop="inner", k=1, skill="root-cause-by-layer",
                action="fix", loss_norm=0.5, raw="2/5", loss_type="rate",
                predicted_delta=-0.5,
            )
            store.append_close(loop="inner", terminal="complete", layer="x", docs="x")
        aggregate_and_write(store)
        memory = read_memory(store)
        report = format_health(memory)
        assert "Calibration" in report
        assert "n=3 predictions" in report

    def test_health_hides_calibration_when_no_predictions(self, tmp_path: Path) -> None:
        store = TraceStore(tmp_path)
        store.init(task_title="demo", loops=["inner"])
        store.append_iteration(
            loop="inner", k=0, skill="baseline", action="stub",
            loss_norm=1.0, raw="5/5", loss_type="rate", baseline=True,
        )
        store.append_close(loop="inner", terminal="complete", layer="x", docs="x")
        aggregate_and_write(store)
        memory = read_memory(store)
        report = format_health(memory)
        assert "Calibration" not in report


class TestCLIPredictedDeltaArg:
    def _run(self, *args: str) -> subprocess.CompletedProcess:
        env = {"PYTHONPATH": str(Path(__file__).resolve().parent.parent)}
        return subprocess.run(
            [sys.executable, "-m", "ldd_trace", *args],
            env=env, capture_output=True, text=True, check=False,
        )

    def test_append_accepts_predicted_delta(self, tmp_path: Path) -> None:
        self._run("init", "--project", str(tmp_path),
                  "--task", "demo", "--loops", "inner")
        self._run("append", "--project", str(tmp_path),
                  "--loop", "inner", "--auto-k",
                  "--skill", "baseline", "--action", "stub",
                  "--loss-norm", "1.0", "--raw", "5/5",
                  "--loss-type", "rate", "--baseline")
        r = self._run(
            "append", "--project", str(tmp_path),
            "--loop", "inner", "--auto-k",
            "--skill", "root-cause-by-layer", "--action", "fix",
            "--loss-norm", "0.5", "--raw", "2/5", "--loss-type", "rate",
            "--predicted-delta", "-0.4",
        )
        assert r.returncode == 0, r.stderr
        # Verify trace.log contains the field
        trace_path = tmp_path / ".ldd" / "trace.log"
        content = trace_path.read_text()
        assert "predicted_Δloss=-0.400" in content
        assert "prediction_error=" in content


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
