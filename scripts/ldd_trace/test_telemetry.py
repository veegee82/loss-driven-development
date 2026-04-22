"""Tests for aggregator.dispatch_accuracy + meta-line `signals=` round-trip.

Covers v0.13.x Fix 2 (Scorer-Telemetrie). All tests construct a synthetic
`.ldd/trace.log` in a tmp directory via the real `TraceStore` API, then run
`dispatch_accuracy` against it and assert shape + values.
"""
from __future__ import annotations

import datetime as _dt
from pathlib import Path

import pytest

from ldd_trace.aggregator import dispatch_accuracy, _parse_signals_field
from ldd_trace.store import TraceStore


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_task(
    store: TraceStore,
    *,
    title: str,
    level: str,
    signals: str,
    loops: list[str],
    iterations: list[tuple[str, str, float, str]],  # (loop, skill, loss, raw)
    terminal: str,
    close_loop: str = "inner",
    loss_final: float | None = None,
) -> None:
    """Compose one task worth of meta → iters → close into the store."""
    store.init(
        task_title=title,
        loops=loops,
        level_chosen=level,
        dispatch_source="auto",
        creativity="standard" if level in ("L3", "L4") else None,
        signals=signals,
    )
    for i, (loop, skill, loss, raw) in enumerate(iterations):
        store.append_iteration(
            loop=loop,
            k=i,
            skill=skill,
            action=f"action-{i}",
            loss_norm=loss,
            raw=raw,
            baseline=(i == 0),
        )
    store.append_close(
        loop=close_loop,
        terminal=terminal,
        loss_final=loss_final,
    )


# ---------------------------------------------------------------------------
# signals= round-trip
# ---------------------------------------------------------------------------


class TestSignalsRoundTrip:
    def test_init_persists_signals(self, tmp_path: Path) -> None:
        store = TraceStore(tmp_path)
        store.init(
            task_title="test",
            loops=["inner"],
            level_chosen="L3",
            dispatch_source="auto",
            creativity="standard",
            signals="greenfield:+3,components>=3:+2",
        )
        text = store.trace_path.read_text()
        assert "signals=greenfield:+3,components>=3:+2" in text

    def test_read_back_signals(self, tmp_path: Path) -> None:
        store = TraceStore(tmp_path)
        store.init(
            task_title="test",
            loops=["inner"],
            level_chosen="L4",
            dispatch_source="auto",
            creativity="inventive",
            signals="greenfield:+3,cross-layer:+2,ambiguous:+2",
        )
        entry = next(e for e in store.read_all() if e.kind == "meta")
        assert entry.fields["signals"] == "greenfield:+3,cross-layer:+2,ambiguous:+2"

    def test_no_signals_emits_nothing(self, tmp_path: Path) -> None:
        store = TraceStore(tmp_path)
        store.init(task_title="test", loops=["inner"], level_chosen="L2")
        text = store.trace_path.read_text()
        assert "signals=" not in text

    def test_parse_signals_field(self) -> None:
        parsed = _parse_signals_field("greenfield:+3,components>=3:+2,explicit-bugfix:-5")
        assert parsed == {
            "greenfield": 3,
            "components>=3": 2,
            "explicit-bugfix": -5,
        }

    def test_parse_signals_empty(self) -> None:
        assert _parse_signals_field("") == {}

    def test_parse_signals_malformed_entries_skipped(self) -> None:
        # The `garbage` pair lacks `:`, the `badweight:abc` pair has a non-int
        # weight. Both are dropped; the well-formed pair survives.
        parsed = _parse_signals_field("greenfield:+3,garbage,badweight:abc")
        assert parsed == {"greenfield": 3}


# ---------------------------------------------------------------------------
# dispatch_accuracy aggregation
# ---------------------------------------------------------------------------


class TestDispatchAccuracy:
    def test_empty_store(self, tmp_path: Path) -> None:
        store = TraceStore(tmp_path)
        store.ensure_dir()
        store.trace_path.touch()
        report = dispatch_accuracy(store)
        assert report["n_tasks_total"] == 0
        assert report["n_tasks_with_level"] == 0
        assert report["overall"]["overkill_rate"] == 0.0
        assert report["overall"]["underkill_rate"] == 0.0

    def test_single_l3_complete_task(self, tmp_path: Path) -> None:
        store = TraceStore(tmp_path)
        _make_task(
            store,
            title="design a thing",
            level="L3",
            signals="greenfield:+3,components>=3:+2",
            loops=["inner"],
            iterations=[
                ("inner", "baseline", 0.500, "4/8"),
                ("inner", "root-cause-by-layer", 0.250, "2/8"),
                ("inner", "e2e-driven-iteration", 0.000, "0/8"),
            ],
            terminal="complete",
            loss_final=0.0,
        )
        report = dispatch_accuracy(store)
        l3 = report["per_level"]["L3"]
        assert l3["n"] == 1
        assert l3["complete_rate"] == 1.0
        assert l3["median_k"] == 2.0  # 2 non-baseline iterations
        assert l3["median_final_loss"] == 0.0

    def test_overkill_flag_fires(self, tmp_path: Path) -> None:
        """L4 task that closed in one iteration with loss=0 is overkill."""
        store = TraceStore(tmp_path)
        _make_task(
            store,
            title="over-scored",
            level="L4",
            signals="greenfield:+3,components>=3:+2,cross-layer:+2,ambiguous:+2",
            loops=["inner"],
            iterations=[
                ("inner", "baseline", 0.200, "1/5"),
                ("inner", "e2e-driven-iteration", 0.000, "0/5"),
            ],
            terminal="complete",
            loss_final=0.0,
        )
        report = dispatch_accuracy(store)
        assert report["per_level"]["L4"]["overkill_rate"] == 1.0
        assert report["overall"]["overkill_rate"] == 1.0

    def test_underkill_flag_fires(self, tmp_path: Path) -> None:
        """L0 task that failed after many iterations is underkill."""
        store = TraceStore(tmp_path)
        _make_task(
            store,
            title="under-scored",
            level="L0",
            signals="explicit-bugfix:-5,single-file:-3",
            loops=["inner"],
            iterations=[
                ("inner", "baseline", 1.000, "5/5"),
                ("inner", "e2e-driven-iteration", 0.800, "4/5"),
                ("inner", "e2e-driven-iteration", 0.800, "4/5"),
                ("inner", "e2e-driven-iteration", 0.800, "4/5"),
                ("inner", "e2e-driven-iteration", 0.800, "4/5"),
                ("inner", "e2e-driven-iteration", 0.800, "4/5"),
            ],
            terminal="failed",
            loss_final=0.800,
        )
        report = dispatch_accuracy(store)
        assert report["per_level"]["L0"]["underkill_rate"] == 1.0
        assert report["overall"]["underkill_rate"] == 1.0

    def test_no_flag_on_wellmatched_task(self, tmp_path: Path) -> None:
        """L2 task that completed in a normal iteration count is neither."""
        store = TraceStore(tmp_path)
        _make_task(
            store,
            title="just-right",
            level="L2",
            signals="cross-layer:+2",
            loops=["inner"],
            iterations=[
                ("inner", "baseline", 0.500, "4/8"),
                ("inner", "root-cause-by-layer", 0.250, "2/8"),
                ("inner", "e2e-driven-iteration", 0.125, "1/8"),
                ("inner", "dialectical-reasoning", 0.000, "0/8"),
            ],
            terminal="complete",
            loss_final=0.0,
        )
        report = dispatch_accuracy(store)
        assert report["per_level"]["L2"]["overkill_rate"] == 0.0
        assert report["per_level"]["L2"]["underkill_rate"] == 0.0
        assert report["per_level"]["L2"]["complete_rate"] == 1.0

    def test_top_signals_aggregated(self, tmp_path: Path) -> None:
        """Top-3 signals per level are counted correctly."""
        store = TraceStore(tmp_path)
        for i in range(3):
            _make_task(
                store,
                title=f"task-{i}",
                level="L3",
                signals="greenfield:+3,components>=3:+2",
                loops=["inner"],
                iterations=[("inner", "baseline", 0.0, "0/1")],
                terminal="complete",
                loss_final=0.0,
            )
        _make_task(
            store,
            title="task-unique",
            level="L3",
            signals="cross-layer:+2,ambiguous:+2",
            loops=["inner"],
            iterations=[("inner", "baseline", 0.0, "0/1")],
            terminal="complete",
            loss_final=0.0,
        )
        report = dispatch_accuracy(store)
        top = {s["name"]: s["n"] for s in report["per_level"]["L3"]["top_signals"]}
        # 3 tasks share greenfield+components>=3; 1 task has cross-layer+ambiguous.
        # top-3 is: greenfield=3, components>=3=3, then one of cross-layer/ambiguous=1.
        assert top.get("greenfield") == 3
        assert top.get("components>=3") == 3

    def test_window_filter(self, tmp_path: Path) -> None:
        """Very small window excludes the task whose meta timestamp is too old."""
        store = TraceStore(tmp_path)
        _make_task(
            store,
            title="fresh",
            level="L2",
            signals="cross-layer:+2",
            loops=["inner"],
            iterations=[("inner", "baseline", 0.0, "0/1")],
            terminal="complete",
            loss_final=0.0,
        )
        # Large window sees the task.
        report_wide = dispatch_accuracy(store, days=36500)
        assert report_wide["n_tasks_with_level"] == 1

        # Negative window should see nothing (cutoff is in the future).
        # We simulate this by forcing the timestamps to the distant past via
        # a fresh store writing with a manual timestamp override.
        old_trace = store.trace_path.read_text()
        # Replace ISO timestamps with a 2020-01-01 stamp (older than any
        # reasonable window).
        import re
        patched = re.sub(
            r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z",
            "2020-01-01T00:00:00Z",
            old_trace,
        )
        store.trace_path.write_text(patched)
        report_narrow = dispatch_accuracy(store, days=1)
        assert report_narrow["n_tasks_with_level"] == 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-v"]))
