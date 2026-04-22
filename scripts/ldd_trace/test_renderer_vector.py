"""Renderer tests for the v0.13.x Fix 1 vector-loss + epoch pipeline."""
from __future__ import annotations

import pytest

from ldd_trace.renderer import (
    Iteration,
    Task,
    _pareto_arrow,
    _parse_loss_vec,
    _sparkline_with_epoch_breaks,
    _trajectory_values_with_epoch_breaks,
    has_vector_loss,
    multi_dim_trajectory,
    render_trace,
)


def _make_iter(label: str, loss: float, loss_vec: str | None = None, epoch: int = 0) -> Iteration:
    return Iteration(
        phase="inner",
        label=label,
        loss_norm=loss,
        raw_num=loss * 10,
        raw_max=10,
        skill_lines=[f"*e2e* → step {label}"],
        timestamp=f"2026-04-22T00:00:0{label[-1]}Z",
        loss_vec=loss_vec,
        epoch=epoch,
    )


class TestParseLossVec:
    def test_parse_roundtrip(self) -> None:
        parsed = _parse_loss_vec("lat:0.8,mem:0.4")
        assert parsed == {"lat": 0.8, "mem": 0.4}

    def test_parse_empty(self) -> None:
        assert _parse_loss_vec(None) == {}
        assert _parse_loss_vec("") == {}

    def test_parse_malformed_entries_skipped(self) -> None:
        assert _parse_loss_vec("lat:0.8,garbage,mem:0.4") == {"lat": 0.8, "mem": 0.4}


class TestEpochBreaks:
    def test_sparkline_with_epoch_mark(self) -> None:
        iters = [
            _make_iter("i1", 0.8, epoch=0),
            _make_iter("i2", 0.4, epoch=0),
            _make_iter("i3", 0.5, epoch=1),
            _make_iter("i4", 0.2, epoch=1),
        ]
        values = [it.loss_norm for it in iters]
        spark = _sparkline_with_epoch_breaks(iters, values)
        # One `┊` between i2 and i3 where epoch bumps 0→1, none elsewhere.
        assert spark.count("┊") == 1
        assert len(spark) == 5  # 4 bars + 1 boundary

    def test_trajectory_values_with_epoch_bar(self) -> None:
        iters = [
            _make_iter("i1", 0.5, epoch=0),
            _make_iter("i2", 0.2, epoch=0),
            _make_iter("i3", 0.4, epoch=1),
        ]
        values = [it.loss_norm for it in iters]
        out = _trajectory_values_with_epoch_breaks(iters, values)
        assert "│" in out
        assert "0.500 → 0.200" in out
        assert "0.400" in out

    def test_no_epoch_no_bar(self) -> None:
        iters = [_make_iter("i1", 0.5, epoch=0), _make_iter("i2", 0.2, epoch=0)]
        values = [it.loss_norm for it in iters]
        assert "┊" not in _sparkline_with_epoch_breaks(iters, values)
        assert "│" not in _trajectory_values_with_epoch_breaks(iters, values)


class TestParetoArrow:
    def test_strict_dominance(self) -> None:
        assert _pareto_arrow({"a": 0.8, "b": 0.6}, {"a": 0.5, "b": 0.3}) == "⇓"

    def test_regression(self) -> None:
        assert _pareto_arrow({"a": 0.5, "b": 0.3}, {"a": 0.8, "b": 0.6}) == "⇑"

    def test_non_dominated_trade_off(self) -> None:
        assert _pareto_arrow({"a": 0.5, "b": 0.8}, {"a": 0.8, "b": 0.5}) == "⇔"

    def test_equal_is_non_dominated(self) -> None:
        assert _pareto_arrow({"a": 0.5}, {"a": 0.5}) == "⇔"

    def test_empty_is_unknown(self) -> None:
        assert _pareto_arrow({}, {"a": 0.5}) == "·"


class TestHasVectorLoss:
    def test_true_when_any_iter_has_vec(self) -> None:
        iters = [_make_iter("i1", 0.5), _make_iter("i2", 0.2, loss_vec="a:0.1")]
        assert has_vector_loss(iters)

    def test_false_when_all_scalar(self) -> None:
        iters = [_make_iter("i1", 0.5), _make_iter("i2", 0.2)]
        assert not has_vector_loss(iters)


class TestMultiDimRender:
    def test_produces_per_dim_rows(self) -> None:
        iters = [
            _make_iter("i1", 0.7, "lat:0.8,mem:0.6"),
            _make_iter("i2", 0.4, "lat:0.5,mem:0.3"),
        ]
        lines = multi_dim_trajectory(iters)
        body = "\n".join(lines)
        assert "Trajectory (vector):" in body
        assert "lat" in body
        assert "mem" in body
        assert "⇓" in body  # i1→i2 strict dominance

    def test_non_dominated_renders_double_arrow(self) -> None:
        iters = [
            _make_iter("i1", 0.5, "lat:0.5,mem:0.8"),
            _make_iter("i2", 0.5, "lat:0.8,mem:0.5"),
        ]
        body = "\n".join(multi_dim_trajectory(iters))
        assert "⇔" in body

    def test_empty_without_vectors(self) -> None:
        assert multi_dim_trajectory([_make_iter("i1", 0.5)]) == []


class TestRenderTraceIntegration:
    def _task(self, iters: list[Iteration]) -> Task:
        return Task(
            title="integration",
            loops_used=["inner"],
            budgets={"inner": (len(iters), 5)},
            iterations=iters,
            terminal="complete",
        )

    def test_scalar_trace_unchanged(self) -> None:
        """Scalar-only iterations render exactly as before — no vector section."""
        iters = [
            _make_iter("i1", 0.5),
            _make_iter("i2", 0.25),
            _make_iter("i3", 0.0),
        ]
        body = render_trace(self._task(iters))
        assert "Trajectory (vector):" not in body
        assert "Trajectory :" in body

    def test_vector_trace_adds_per_dim_block(self) -> None:
        iters = [
            _make_iter("i1", 0.7, "lat:0.8,mem:0.6"),
            _make_iter("i2", 0.5, "lat:0.5,mem:0.5"),
            _make_iter("i3", 0.3, "lat:0.3,mem:0.3"),
        ]
        body = render_trace(self._task(iters))
        assert "Trajectory (vector):" in body
        assert "lat" in body and "mem" in body
        # Pareto-dominant descent across all three iterations.
        assert body.count("⇓") >= 2

    def test_epoch_boundary_suppresses_delta(self) -> None:
        iters = [
            _make_iter("i1", 0.5, epoch=0),
            _make_iter("i2", 0.2, epoch=0),
            _make_iter("i3", 0.4, epoch=1),
        ]
        body = render_trace(self._task(iters))
        # Epoch boundary replaces the scalar Δ with the "n/a" marker for i3.
        assert "n/a (epoch boundary)" in body
        assert "┊" in body  # boundary marker in sparkline
        assert "│" in body  # boundary marker in value string


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-v"]))
