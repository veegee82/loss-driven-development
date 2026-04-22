"""Tests for the v0.13.x Fix 1 — VectorLoss + epoch-marker pipeline.

Two concerns:
  * VectorLoss itself: Pareto-dominance semantics, round-trip serde.
  * Store/CLI integration: loss_vec + epoch fields round-trip, epoch bump
    entries live in trace.log, current_epoch() advances monotonically.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from ldd_trace.store import TraceStore
from ldd_trace.vector_loss import VectorLoss, loads, mean_scalar


# ---------------------------------------------------------------------------
# VectorLoss unit tests
# ---------------------------------------------------------------------------


class TestVectorLoss:
    def test_construct_valid(self) -> None:
        v = VectorLoss(dims=("lat", "mem"), values={"lat": 0.8, "mem": 0.4})
        assert v.dims == ("lat", "mem")
        assert v.values == {"lat": 0.8, "mem": 0.4}

    def test_construct_missing_dim_raises(self) -> None:
        with pytest.raises(ValueError):
            VectorLoss(dims=("lat", "mem"), values={"lat": 0.8})

    def test_construct_extra_dim_raises(self) -> None:
        with pytest.raises(ValueError):
            VectorLoss(dims=("lat",), values={"lat": 0.8, "mem": 0.4})

    # --- Pareto-dominance semantics -----------------------------------

    def test_strict_dominance(self) -> None:
        """All dims better → self dominates."""
        a = VectorLoss(dims=("lat", "mem"), values={"lat": 0.5, "mem": 0.3})
        b = VectorLoss(dims=("lat", "mem"), values={"lat": 0.7, "mem": 0.6})
        assert a.dominates(b) is True
        assert b.dominates(a) is False

    def test_weak_dominance_one_better_others_equal(self) -> None:
        """One dim strictly better, others equal → dominates."""
        a = VectorLoss(dims=("lat", "mem"), values={"lat": 0.5, "mem": 0.5})
        b = VectorLoss(dims=("lat", "mem"), values={"lat": 0.5, "mem": 0.6})
        assert a.dominates(b) is True

    def test_incomparable_trade_off(self) -> None:
        """Self better on one dim, worse on another → None (non-dominated)."""
        a = VectorLoss(dims=("lat", "mem"), values={"lat": 0.5, "mem": 0.8})
        b = VectorLoss(dims=("lat", "mem"), values={"lat": 0.8, "mem": 0.5})
        assert a.dominates(b) is None
        assert b.dominates(a) is None

    def test_equal_vectors_are_incomparable(self) -> None:
        """Identical vectors: no strict improvement either way."""
        a = VectorLoss(dims=("lat",), values={"lat": 0.5})
        b = VectorLoss(dims=("lat",), values={"lat": 0.5})
        assert a.dominates(b) is None

    def test_dimension_mismatch_raises(self) -> None:
        a = VectorLoss(dims=("lat",), values={"lat": 0.5})
        b = VectorLoss(dims=("mem",), values={"mem": 0.5})
        with pytest.raises(ValueError):
            a.dominates(b)

    def test_dominance_arrow(self) -> None:
        prev = VectorLoss(dims=("lat", "mem"), values={"lat": 0.8, "mem": 0.6})
        better = VectorLoss(dims=("lat", "mem"), values={"lat": 0.5, "mem": 0.3})
        worse = VectorLoss(dims=("lat", "mem"), values={"lat": 0.9, "mem": 0.7})
        trade = VectorLoss(dims=("lat", "mem"), values={"lat": 0.5, "mem": 0.7})
        assert better.dominance_arrow(prev) == "⇓"
        assert worse.dominance_arrow(prev) == "⇑"
        assert trade.dominance_arrow(prev) == "⇔"

    # --- Serialization ---------------------------------------------------

    def test_dumps_format(self) -> None:
        v = VectorLoss(
            dims=("lat", "mem", "corr"),
            values={"lat": 0.800, "mem": 0.400, "corr": 0.200},
        )
        assert v.dumps() == "lat:0.800,mem:0.400,corr:0.200"

    def test_round_trip(self) -> None:
        original = VectorLoss(
            dims=("lat", "mem", "corr"),
            values={"lat": 0.8, "mem": 0.4, "corr": 0.2},
        )
        reparsed = loads(original.dumps())
        assert reparsed.dims == original.dims
        assert all(
            abs(reparsed.values[d] - original.values[d]) < 1e-6
            for d in original.dims
        )

    def test_loads_drops_malformed(self) -> None:
        vl = loads("lat:0.8,garbage,mem:0.4")
        assert list(vl.dims) == ["lat", "mem"]

    def test_mean_scalar(self) -> None:
        v = VectorLoss(dims=("a", "b", "c"), values={"a": 0.3, "b": 0.6, "c": 0.9})
        assert abs(mean_scalar(v) - 0.6) < 1e-9


# ---------------------------------------------------------------------------
# Store integration — loss_vec + epoch round-trip
# ---------------------------------------------------------------------------


class TestStoreVectorAndEpoch:
    def test_loss_vec_persisted(self, tmp_path: Path) -> None:
        store = TraceStore(tmp_path)
        store.init(task_title="t", loops=["inner"], level_chosen="L2")
        store.append_iteration(
            loop="inner", k=1, skill="e2e-driven-iteration",
            action="x", loss_norm=0.5, raw="2/4",
            loss_vec="lat:0.8,mem:0.4,corr:0.2",
        )
        text = store.trace_path.read_text()
        assert "loss_vec=lat:0.8,mem:0.4,corr:0.2" in text

    def test_epoch_field_persisted(self, tmp_path: Path) -> None:
        store = TraceStore(tmp_path)
        store.init(task_title="t", loops=["inner"], level_chosen="L2")
        store.append_iteration(
            loop="inner", k=1, skill="x", action="x",
            loss_norm=0.5, raw="2/4", epoch=3,
        )
        text = store.trace_path.read_text()
        assert "epoch=3" in text

    def test_default_epoch_zero_is_omitted(self, tmp_path: Path) -> None:
        """epoch=0 is the baseline; omitting it keeps the trace diff-minimal."""
        store = TraceStore(tmp_path)
        store.init(task_title="t", loops=["inner"], level_chosen="L2")
        store.append_iteration(
            loop="inner", k=1, skill="x", action="x",
            loss_norm=0.5, raw="2/4", epoch=0,
        )
        text = store.trace_path.read_text()
        assert "epoch=" not in text

    def test_epoch_bump_writes_entry(self, tmp_path: Path) -> None:
        store = TraceStore(tmp_path)
        store.init(task_title="t", loops=["inner"], level_chosen="L2")
        store.append_epoch_bump(
            new_epoch=1,
            reason="Byzantine adversary discovered — threat model changed",
        )
        entries = [e for e in store.read_all() if e.kind == "epoch"]
        assert len(entries) == 1
        assert entries[0].fields["epoch"] == "1"
        assert "Byzantine" in entries[0].fields["reason"]

    def test_epoch_bump_requires_reason(self, tmp_path: Path) -> None:
        store = TraceStore(tmp_path)
        with pytest.raises(ValueError):
            store.append_epoch_bump(new_epoch=1, reason="")

    def test_current_epoch_advances(self, tmp_path: Path) -> None:
        store = TraceStore(tmp_path)
        store.init(task_title="t", loops=["inner"], level_chosen="L2")
        assert store.current_epoch() == 0
        store.append_epoch_bump(new_epoch=1, reason="first shift")
        assert store.current_epoch() == 1
        store.append_epoch_bump(new_epoch=2, reason="second shift")
        assert store.current_epoch() == 2

    def test_epoch_entries_dont_start_new_task(self, tmp_path: Path) -> None:
        """Epoch entries must NOT be misread as meta → new TaskSlice."""
        store = TraceStore(tmp_path)
        store.init(task_title="single-task", loops=["inner"], level_chosen="L2")
        store.append_iteration(
            loop="inner", k=0, skill="baseline", action="x",
            loss_norm=0.5, raw="1/2", baseline=True,
        )
        store.append_epoch_bump(new_epoch=1, reason="rubric change")
        store.append_iteration(
            loop="inner", k=1, skill="fix", action="x",
            loss_norm=0.1, raw="0/2", epoch=1,
        )
        store.append_close(loop="inner", terminal="complete", loss_final=0.1)
        slices = store.segment_tasks()
        assert len(slices) == 1
        assert slices[0].meta.fields["task"] == "single-task"
        # The close+two iterations must all live in that one slice.
        assert len(slices[0].iterations) == 2
        assert slices[0].is_closed


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-v"]))
