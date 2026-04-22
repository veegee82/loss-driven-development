"""Unit + integration tests for ldd_trace (v0.5.1).

Run with:
    cd scripts && python -m pytest ldd_trace/test_ldd_trace.py -v

or (from repo root):
    python -m pytest scripts/ldd_trace/test_ldd_trace.py -v
"""
from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

from ldd_trace import TraceStore, render_trace
from ldd_trace.renderer import Iteration, Task, mini_chart, sparkline, trend_arrow


# ---------------------------------------------------------------------------
# renderer — pure functions, no I/O
# ---------------------------------------------------------------------------


class TestSparkline:
    def test_empty(self) -> None:
        assert sparkline([]) == ""

    def test_single_nonzero(self) -> None:
        # max==v, ratio=1 → idx=7 → '█'
        assert sparkline([0.5]) == "█"

    def test_zero_renders_dot(self) -> None:
        assert sparkline([0.0]) == "·"
        assert "·" in sparkline([1.0, 0.0])

    def test_descending_length(self) -> None:
        out = sparkline([1.0, 0.5, 0.25, 0.0])
        assert len(out) == 4
        assert out.endswith("·")

    def test_monotonic_mapping(self) -> None:
        """Higher values map to higher block indices."""
        values = [0.1, 0.3, 0.5, 0.7, 1.0]
        out = sparkline(values)
        # Each char is >= the previous in the block sequence
        ordering = "·▁▂▃▄▅▆▇█"
        idx = [ordering.index(c) for c in out]
        assert idx == sorted(idx)


class TestTrendArrow:
    def test_short_series(self) -> None:
        assert trend_arrow([]) == "·"
        assert trend_arrow([0.5]) == "·"

    def test_descending(self) -> None:
        assert trend_arrow([1.0, 0.0]) == "↓"

    def test_ascending(self) -> None:
        assert trend_arrow([0.0, 1.0]) == "↑"

    def test_plateau_within_band(self) -> None:
        assert trend_arrow([0.5, 0.5001]) == "→"
        assert trend_arrow([0.5, 0.503]) == "→"
        assert trend_arrow([0.5, 0.506]) == "↑"

    def test_non_monotonic_net_down(self) -> None:
        """Mid-run regression still reads ↓ if net is down (load-bearing)."""
        assert trend_arrow([0.667, 0.833, 0.167]) == "↓"


class TestMiniChart:
    def test_produces_axis_line(self) -> None:
        iters = [
            Iteration(phase="inner", label="i1", loss_norm=0.5, raw_num=4, raw_max=8),
            Iteration(phase="inner", label="i2", loss_norm=0.25, raw_num=2, raw_max=8),
            Iteration(phase="inner", label="i3", loss_norm=0.0, raw_num=0, raw_max=8),
        ]
        lines = mini_chart(iters)
        assert any("i1" in l and "i2" in l and "i3" in l for l in lines)
        # ylim = ceil(0.5/0.25)*0.25 = 0.5 → rows at 0.00, 0.25, 0.50
        assert sum(1 for l in lines if "┤" in l) == 3


# ---------------------------------------------------------------------------
# store — persistence + projection
# ---------------------------------------------------------------------------


class TestTraceStore:
    def test_init_creates_trace_log(self, tmp_path: Path) -> None:
        store = TraceStore(tmp_path)
        assert not store.exists()
        store.init(task_title="demo", loops=["inner"])
        assert store.exists()
        assert store.trace_path.read_text().count("meta") == 1

    def test_init_idempotent_same_task(self, tmp_path: Path) -> None:
        store = TraceStore(tmp_path)
        store.init(task_title="demo", loops=["inner"])
        store.init(task_title="demo", loops=["inner"])
        assert store.trace_path.read_text().count("meta") == 1

    def test_next_k_empty(self, tmp_path: Path) -> None:
        store = TraceStore(tmp_path)
        assert store.next_k("inner") == 0

    def test_next_k_monotonic(self, tmp_path: Path) -> None:
        store = TraceStore(tmp_path)
        store.init(task_title="demo", loops=["inner"])
        store.append_iteration(
            loop="inner", k=0, skill="s", action="a",
            loss_norm=1.0, raw="5/5", baseline=True,
        )
        assert store.next_k("inner") == 1
        store.append_iteration(
            loop="inner", k=1, skill="s", action="a",
            loss_norm=0.2, raw="1/5",
        )
        assert store.next_k("inner") == 2

    def test_delta_computed_on_second_entry(self, tmp_path: Path) -> None:
        store = TraceStore(tmp_path)
        store.init(task_title="demo", loops=["inner"])
        store.append_iteration(
            loop="inner", k=0, skill="s", action="a",
            loss_norm=0.5, raw="2/4", baseline=True,
        )
        e2 = store.append_iteration(
            loop="inner", k=1, skill="s", action="a",
            loss_norm=0.25, raw="1/4",
        )
        # v0.11.0: the per-iter delta field is `Δloss` (shorter, unambiguous).
        assert "Δloss" in e2.fields
        assert "-0.250" in e2.fields["Δloss"]

    def test_projection_to_task(self, tmp_path: Path) -> None:
        store = TraceStore(tmp_path)
        store.init(task_title="demo", loops=["inner", "refine"])
        store.append_iteration(
            loop="inner", k=0, skill="scaffold", action="empty",
            loss_norm=1.0, raw="3/3", baseline=True,
        )
        store.append_iteration(
            loop="inner", k=1, skill="e2e-driven-iteration",
            action="impl", loss_norm=0.333, raw="1/3",
        )
        store.append_iteration(
            loop="inner", k=2, skill="root-cause-by-layer",
            action="edge case", loss_norm=0.0, raw="0/3",
        )
        store.append_close(
            loop="inner", terminal="complete",
            layer="3: contract for empty · 5: never-raise",
            docs="synced",
        )
        task = store.to_task()
        assert task.title == "demo"
        assert len(task.iterations) == 3
        assert task.terminal == "complete"
        assert "contract" in task.fix_layer_4
        assert "never-raise" in task.fix_layer_5

    def test_meta_header_store_dispatched_mode(self, tmp_path: Path) -> None:
        """v0.11.x: bootstrap-userspace + using-ldd mandated header lines
        must survive the init → serialize → read → project → render round trip.
        """
        store = TraceStore(tmp_path)
        store.init(
            task_title="header demo",
            loops=["design", "inner"],
            level_chosen="L4",
            creativity="inventive",
            dispatch_source="user-bump",
            store_scope="local (.ldd/trace.log)",
            dispatched='user-bump L4 (scorer proposed L3, bump: "all levels")',
        )
        store.append_iteration(
            loop="design", k=0, skill="architect-mode",
            action="constraints", loss_norm=0.8, raw="4/5",
        )
        task = store.to_task()
        assert task.store == "local (.ldd/trace.log)"
        assert 'user-bump L4' in task.dispatched
        assert task.level == "L4"
        assert task.level_name == "method"
        assert task.creativity == "inventive"

        from ldd_trace.renderer import render_trace
        block = render_trace(task)
        assert "│ Store      : local (.ldd/trace.log)" in block
        assert "│ Dispatched : user-bump L4" in block
        assert "│ Mode       : architect, inventive" in block

    def test_meta_header_absent_when_unset(self, tmp_path: Path) -> None:
        """Backward compat: pre-v0.11.x traces (no level/store/dispatched on
        meta) render without Store/Dispatched/Mode header lines — no empty
        stub rows, no crashes.
        """
        store = TraceStore(tmp_path)
        store.init(task_title="legacy", loops=["inner"])
        store.append_iteration(
            loop="inner", k=0, skill="x", action="y",
            loss_norm=0.5, raw="1/2",
        )
        from ldd_trace.renderer import render_trace
        block = render_trace(store.to_task())
        assert "Store" not in block
        assert "Dispatched" not in block
        assert "Mode       :" not in block

    def test_meta_dispatched_survives_inner_double_quotes(self, tmp_path: Path) -> None:
        """Regression: pre-fix serializer wrapped fields with double-quotes
        and silently truncated on inner double-quotes, clipping the
        Dispatched line mid-string. The shlex-based serializer must round-
        trip a value containing both spaces and double-quotes losslessly.
        """
        tricky = 'user-bump L4 (scorer proposed L3, bump: "alle level triggern")'
        store = TraceStore(tmp_path)
        store.init(
            task_title="quote round-trip",
            loops=["inner"],
            level_chosen="L4",
            creativity="inventive",
            dispatch_source="user-bump",
            dispatched=tricky,
        )
        task = store.to_task()
        assert task.dispatched == tricky

    def test_meta_dispatched_derived_from_level(self, tmp_path: Path) -> None:
        """When --dispatched is omitted but --level + --dispatch are given,
        the projection derives a sensible Dispatched line automatically."""
        store = TraceStore(tmp_path)
        store.init(
            task_title="derived",
            loops=["inner"],
            level_chosen="L2",
            dispatch_source="auto",
        )
        task = store.to_task()
        assert task.dispatched == "auto-level L2/deliberate"

    def test_close_line_parses(self, tmp_path: Path) -> None:
        store = TraceStore(tmp_path)
        store.init(task_title="demo", loops=["inner"])
        store.append_close(
            loop="inner", terminal="complete",
            layer="3: foo · 5: bar", docs="synced",
        )
        entries = store.read_all()
        close_entries = [e for e in entries if e.kind == "close"]
        assert len(close_entries) == 1
        assert close_entries[0].fields["terminal"] == "complete"


# ---------------------------------------------------------------------------
# CLI — subprocess end-to-end
# ---------------------------------------------------------------------------


class TestCLI:
    """Invoke `python -m ldd_trace` as a subprocess and check output."""

    def _run(self, *args: str, cwd: Path = None) -> subprocess.CompletedProcess:
        env = {"PYTHONPATH": str(Path(__file__).resolve().parent.parent)}
        return subprocess.run(
            [sys.executable, "-m", "ldd_trace", *args],
            cwd=cwd,
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )

    def test_help(self) -> None:
        result = self._run("--help")
        assert result.returncode == 0
        assert "init" in result.stdout
        assert "append" in result.stdout
        assert "close" in result.stdout
        assert "render" in result.stdout
        assert "status" in result.stdout

    def test_full_cycle_init_append_close_render(self, tmp_path: Path) -> None:
        # init
        r = self._run(
            "init", "--project", str(tmp_path),
            "--task", "reverse_string test", "--loops", "inner",
        )
        assert r.returncode == 0, r.stderr
        assert (tmp_path / ".ldd" / "trace.log").exists()

        # append 3 iterations (baseline + 2)
        r = self._run(
            "append", "--project", str(tmp_path),
            "--loop", "inner", "--auto-k",
            "--skill", "scaffold", "--action", "empty",
            "--loss-norm", "1.0", "--raw", "3/3",
            "--loss-type", "rate", "--baseline",
        )
        assert r.returncode == 0, r.stderr
        assert "Trajectory" in r.stdout or "single data point" in r.stdout

        r = self._run(
            "append", "--project", str(tmp_path),
            "--loop", "inner", "--auto-k",
            "--skill", "e2e-driven-iteration",
            "--action", "slice reversal",
            "--loss-norm", "0.333", "--raw", "1/3",
            "--loss-type", "rate",
        )
        assert r.returncode == 0, r.stderr
        assert "Δ −0.667 ↓" in r.stdout or "Δ -0.667" in r.stdout

        r = self._run(
            "append", "--project", str(tmp_path),
            "--loop", "inner", "--auto-k",
            "--skill", "root-cause-by-layer",
            "--action", "empty-string edge case",
            "--loss-norm", "0.0", "--raw", "0/3",
            "--loss-type", "rate",
        )
        assert r.returncode == 0, r.stderr
        # With 3 iterations, mini chart should appear
        assert "Loss curve" in r.stdout

        # close
        r = self._run(
            "close", "--project", str(tmp_path),
            "--loop", "inner", "--terminal", "complete",
            "--layer", "3: contract for empty · 5: never-raise",
            "--docs", "synced",
        )
        assert r.returncode == 0, r.stderr
        assert "Terminal    : complete" in r.stdout

        # render again, same output
        r = self._run("render", "--project", str(tmp_path))
        assert r.returncode == 0, r.stderr
        assert "Terminal    : complete" in r.stdout

        # status
        r = self._run("status", "--project", str(tmp_path))
        assert r.returncode == 0, r.stderr
        assert "iterations: 3" in r.stdout


# ---------------------------------------------------------------------------
# render_trace consistency rule: sparkline last bar, chart last marker, and
# the final iteration's loss must all reflect the same number
# ---------------------------------------------------------------------------


class TestVisualizationConsistency:
    def test_all_three_channels_agree_on_last_value(self) -> None:
        task = Task(
            title="consistency probe",
            loops_used=["inner"],
            budgets={"inner": (3, 5)},
            iterations=[
                Iteration(phase="inner", label="i1", loss_norm=1.0, raw_num=4, raw_max=4),
                Iteration(phase="inner", label="i2", loss_norm=0.5, raw_num=2, raw_max=4),
                Iteration(phase="inner", label="i3", loss_norm=0.0, raw_num=0, raw_max=4),
            ],
        )
        output = render_trace(task)
        # Last iteration line contains loss=0.000
        assert "loss=0.000" in output
        # Sparkline ends with · (zero)
        spark_line = [l for l in output.splitlines() if l.startswith("│ Trajectory")][0]
        assert "·" in spark_line.split("   ")[0]
        # Chart has a ● on the 0.00 row in the rightmost column
        chart_lines = [l for l in output.splitlines() if "0.00 ┤" in l]
        assert chart_lines, "expected a 0.00 grid row"
        assert any("●" in l for l in chart_lines), (
            f"expected ● on 0.00 row; got {chart_lines!r}"
        )


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
