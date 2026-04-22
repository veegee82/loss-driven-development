"""Tests for Tier-2 magic-header helpers — ⟪LDD-TRACE-v1⟫ emit / parse / ingest.

These back the bootstrap-userspace skill: the same trace entry that
appears as a line in .ldd/trace.log on a CLI host can be emitted with
a magic prefix for chat-history retention and round-tripped back into
trace.log on a CLI host later.

Run:
    python -m pytest scripts/ldd_trace/test_bootstrap_userspace.py -v
"""
from __future__ import annotations

import tempfile
from pathlib import Path

from ldd_trace import (
    MAGIC_PREFIX,
    TraceEntry,
    TraceStore,
    emit_magic_line,
    ingest_magic_lines,
    parse_magic_lines,
)


def _sample_iter_entry() -> TraceEntry:
    return TraceEntry(
        timestamp="2026-04-22T14:30:00Z",
        loop="inner",
        kind="iter",
        fields={
            "k": "3",
            "skill": "root-cause-by-layer",
            "action": "split contract check",
            "loss_norm": "0.125",
            "raw": "1/8",
            "loss_type": "normalized-rubric",
            "Δloss_norm": "-0.250",
        },
    )


def _sample_close_entry() -> TraceEntry:
    return TraceEntry(
        timestamp="2026-04-22T14:45:00Z",
        loop="inner",
        kind="close",
        fields={"terminal": "complete", "layer": "4: contract", "docs": "synced"},
    )


class TestEmitMagicLine:
    def test_starts_with_magic_prefix(self) -> None:
        line = emit_magic_line(_sample_iter_entry())
        assert line.startswith(MAGIC_PREFIX + " ")

    def test_no_trailing_newline(self) -> None:
        line = emit_magic_line(_sample_iter_entry())
        assert "\n" not in line

    def test_carries_all_fields(self) -> None:
        line = emit_magic_line(_sample_iter_entry())
        assert "skill=root-cause-by-layer" in line
        assert "loss_norm=0.125" in line
        assert "k=3" in line

    def test_action_with_spaces_is_quoted(self) -> None:
        line = emit_magic_line(_sample_iter_entry())
        # action="split contract check" has a space — must be double-quoted
        assert 'action="split contract check"' in line


class TestParseMagicLines:
    def test_round_trip_single_entry(self) -> None:
        original = _sample_iter_entry()
        line = emit_magic_line(original)
        parsed = parse_magic_lines(line)
        assert len(parsed) == 1
        p = parsed[0]
        assert p.timestamp == original.timestamp
        assert p.loop == original.loop
        assert p.kind == original.kind
        assert p.fields.get("skill") == "root-cause-by-layer"
        assert p.fields.get("k") == "3"

    def test_ignores_non_magic_lines(self) -> None:
        text = "This is some chat prose.\nNo magic here.\n> a blockquote"
        assert parse_magic_lines(text) == []

    def test_finds_magic_inside_prose(self) -> None:
        line = emit_magic_line(_sample_iter_entry())
        text = f"Here's what the agent logged:\n\n  {line}\n\nHope that helps."
        parsed = parse_magic_lines(text)
        assert len(parsed) == 1
        assert parsed[0].fields.get("k") == "3"

    def test_multiple_entries_preserved_order(self) -> None:
        a = _sample_iter_entry()
        b = TraceEntry(
            timestamp="2026-04-22T14:32:00Z",
            loop="inner",
            kind="iter",
            fields={"k": "4", "skill": "loss-backprop-lens", "loss_norm": "0.0", "raw": "0/8"},
        )
        text = "\n".join([emit_magic_line(a), emit_magic_line(b)])
        parsed = parse_magic_lines(text)
        assert [e.fields.get("k") for e in parsed] == ["3", "4"]

    def test_close_entry_round_trip(self) -> None:
        close = _sample_close_entry()
        line = emit_magic_line(close)
        parsed = parse_magic_lines(line)
        assert len(parsed) == 1
        assert parsed[0].kind == "close"
        assert parsed[0].fields.get("terminal") == "complete"

    def test_malformed_magic_line_skipped_not_raised(self) -> None:
        # A line with the magic prefix but no payload should not crash
        text = f"{MAGIC_PREFIX}\n{MAGIC_PREFIX}   \nfoo bar"
        assert parse_magic_lines(text) == []


class TestIngestMagicLines:
    def test_appends_new_entries_to_fresh_store(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            store = TraceStore(Path(td))
            store.init(task_title="test task", loops=["inner"])
            line = emit_magic_line(_sample_iter_entry())
            appended = ingest_magic_lines(store, line)
            assert appended == 1
            # Verify it actually landed in the store
            entries = store.read_all()
            iter_entries = [e for e in entries if e.kind == "iter"]
            assert len(iter_entries) == 1
            assert iter_entries[0].fields.get("skill") == "root-cause-by-layer"

    def test_idempotent_second_ingest_skips_duplicate(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            store = TraceStore(Path(td))
            store.init(task_title="test task", loops=["inner"])
            line = emit_magic_line(_sample_iter_entry())
            first = ingest_magic_lines(store, line)
            second = ingest_magic_lines(store, line)
            assert first == 1
            assert second == 0
            # Store still contains exactly one iteration entry
            iter_entries = [e for e in store.read_all() if e.kind == "iter"]
            assert len(iter_entries) == 1

    def test_partial_overlap_only_new_entries_appended(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            store = TraceStore(Path(td))
            store.init(task_title="test task", loops=["inner"])
            a = _sample_iter_entry()
            b = TraceEntry(
                timestamp="2026-04-22T14:35:00Z",
                loop="inner",
                kind="iter",
                fields={"k": "4", "skill": "e2e-driven-iteration", "loss_norm": "0.0", "raw": "0/8"},
            )
            ingest_magic_lines(store, emit_magic_line(a))
            # Second ingest contains a (duplicate) + b (new)
            text = emit_magic_line(a) + "\n" + emit_magic_line(b)
            appended = ingest_magic_lines(store, text)
            assert appended == 1
            iter_entries = [e for e in store.read_all() if e.kind == "iter"]
            assert {e.fields.get("k") for e in iter_entries} == {"3", "4"}

    def test_empty_text_returns_zero(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            store = TraceStore(Path(td))
            store.init(task_title="test task", loops=["inner"])
            assert ingest_magic_lines(store, "") == 0
            assert ingest_magic_lines(store, "some prose without magic") == 0

    def test_ingest_on_non_initialized_store_creates_dir(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            store = TraceStore(Path(td))
            # No init() call — directory doesn't exist yet
            line = emit_magic_line(_sample_iter_entry())
            appended = ingest_magic_lines(store, line)
            assert appended == 1
            assert store.trace_path.exists()
