"""Persistence layer — read/write `.ldd/trace.log` in a project directory.

Line format (one entry per line, space-separated key=value pairs):

    2026-04-21T17:30:00Z  inner  k=4  skill=method-evolution  action="..."  \
        loss_norm=0.000  raw=0/33  loss_type=rate  Δloss_norm=-0.031

Special event lines:
    2026-04-21T15:30:00Z  meta  task="..."  loops=inner,refine,outer
    2026-04-21T17:38:00Z  inner  close  terminal=complete  layer="..."  docs=synced

Values that may contain spaces MUST be double-quoted; the parser re-assembles
them across whitespace splits.
"""
from __future__ import annotations

import datetime as _dt
import shlex
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

from ldd_trace.renderer import Iteration, Task


TRACE_DIR_NAME = ".ldd"
TRACE_FILE_NAME = "trace.log"


def _utcnow_iso() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


@dataclass
class TraceEntry:
    """One parsed line from `.ldd/trace.log`."""

    timestamp: str
    loop: str                                  # "inner" | "refine" | "outer" | "architect" | "meta"
    kind: str                                  # "iter" | "close" | "meta"
    fields: Dict[str, str] = field(default_factory=dict)

    def get_float(self, key: str, default: float = 0.0) -> float:
        v = self.fields.get(key)
        if v is None:
            return default
        try:
            return float(v)
        except ValueError:
            return default

    def get_int(self, key: str, default: int = 0) -> int:
        v = self.fields.get(key)
        if v is None:
            return default
        try:
            return int(v)
        except ValueError:
            return default


def _parse_line(line: str) -> Optional[TraceEntry]:
    line = line.strip()
    if not line or line.startswith("#"):
        return None
    try:
        tokens = shlex.split(line, posix=True)
    except ValueError:
        return None
    if not tokens:
        return None
    timestamp = tokens[0]
    rest = tokens[1:]
    if not rest:
        return None
    loop = rest[0]
    fields: Dict[str, str] = {}
    has_close = False
    has_baseline = False
    for tok in rest[1:]:
        if tok == "close":
            has_close = True
            continue
        if tok == "baseline":
            has_baseline = True
            continue
        if "=" in tok:
            k, _, v = tok.partition("=")
            fields[k] = v
    if has_close:
        kind = "close"
    elif has_baseline:
        kind = "iter"
        fields.setdefault("k", "0")
        fields.setdefault("baseline", "true")
    elif loop == "meta":
        kind = "meta"
    else:
        kind = "iter"
    return TraceEntry(timestamp=timestamp, loop=loop, kind=kind, fields=fields)


def _serialize_entry(entry: TraceEntry) -> str:
    parts = [entry.timestamp, entry.loop]
    if entry.kind == "close":
        parts.append("close")
    elif entry.kind == "iter" and entry.fields.get("baseline") == "true":
        parts.append("baseline")
    for k, v in entry.fields.items():
        if k == "baseline":
            continue
        if any(c in v for c in (" ", "\t")):
            parts.append(f'{k}="{v}"')
        else:
            parts.append(f"{k}={v}")
    return "  ".join(parts)


class TraceStore:
    """Append-only log at `<project>/.ldd/trace.log`.

    All writes are append-newline-flush; no partial lines. Reads are
    whole-file every time (the log is expected to stay small — hundreds
    of lines is typical per task).
    """

    def __init__(self, project_root: Path) -> None:
        self.project_root = Path(project_root).resolve()
        self.trace_dir = self.project_root / TRACE_DIR_NAME
        self.trace_path = self.trace_dir / TRACE_FILE_NAME

    # --- lifecycle -----------------------------------------------------

    def exists(self) -> bool:
        return self.trace_path.exists()

    def ensure_dir(self) -> None:
        self.trace_dir.mkdir(parents=True, exist_ok=True)

    def init(self, task_title: str, loops: List[str]) -> TraceEntry:
        """Create trace.log with a meta header. Idempotent per-task — if a
        meta entry already exists with the same title, reuse it.
        """
        self.ensure_dir()
        if self.exists():
            for entry in self.read_all():
                if entry.kind == "meta" and entry.fields.get("task") == task_title:
                    return entry
        entry = TraceEntry(
            timestamp=_utcnow_iso(),
            loop="meta",
            kind="meta",
            fields={"task": task_title, "loops": ",".join(loops)},
        )
        self._append(entry)
        return entry

    # --- read ----------------------------------------------------------

    def read_all(self) -> List[TraceEntry]:
        if not self.exists():
            return []
        entries: List[TraceEntry] = []
        with self.trace_path.open("r", encoding="utf-8") as f:
            for line in f:
                parsed = _parse_line(line)
                if parsed is not None:
                    entries.append(parsed)
        return entries

    def iterations(self) -> List[TraceEntry]:
        return [e for e in self.read_all() if e.kind == "iter"]

    def next_k(self, loop: str) -> int:
        """Next iteration index for `loop`, derived from existing entries."""
        max_k = -1
        for e in self.iterations():
            if e.loop != loop:
                continue
            k = e.get_int("k", -1)
            if k > max_k:
                max_k = k
        return max_k + 1

    # --- write ---------------------------------------------------------

    def append_iteration(
        self,
        loop: str,
        k: int,
        skill: str,
        action: str,
        loss_norm: float,
        raw: str,
        loss_type: str = "normalized-rubric",
        mode: Optional[str] = None,
        creativity: Optional[str] = None,
        baseline: bool = False,
        notes: Optional[str] = None,
    ) -> TraceEntry:
        prev_same_loop = [e for e in self.iterations() if e.loop == loop]
        delta: Optional[float] = None
        if prev_same_loop and not baseline:
            prev_loss = prev_same_loop[-1].get_float("loss_norm", 0.0)
            delta = loss_norm - prev_loss
        fields: Dict[str, str] = {
            "k": str(k),
            "skill": skill,
            "action": action,
            "loss_norm": f"{loss_norm:.3f}",
            "raw": raw,
            "loss_type": loss_type,
        }
        if mode:
            fields["mode"] = mode
        if creativity:
            fields["creativity"] = creativity
        if baseline:
            fields["baseline"] = "true"
        if delta is not None:
            sign = "-" if delta < 0 else ("+" if delta > 0 else "±")
            fields["Δloss_norm"] = f"{sign}{abs(delta):.3f}" if sign != "±" else "±0.000"
        if notes:
            fields["notes"] = notes
        entry = TraceEntry(
            timestamp=_utcnow_iso(),
            loop=loop,
            kind="iter",
            fields=fields,
        )
        self._append(entry)
        return entry

    def append_close(
        self,
        loop: str,
        terminal: str,
        layer: str = "",
        docs: str = "",
        notes: Optional[str] = None,
    ) -> TraceEntry:
        fields: Dict[str, str] = {"terminal": terminal}
        if layer:
            fields["layer"] = layer
        if docs:
            fields["docs"] = docs
        if notes:
            fields["notes"] = notes
        entry = TraceEntry(
            timestamp=_utcnow_iso(),
            loop=loop,
            kind="close",
            fields=fields,
        )
        self._append(entry)
        return entry

    def _append(self, entry: TraceEntry) -> None:
        self.ensure_dir()
        with self.trace_path.open("a", encoding="utf-8") as f:
            f.write(_serialize_entry(entry) + "\n")

    # --- projection ----------------------------------------------------

    def to_task(self) -> Task:
        """Project the log into a `Task` instance ready for `render_trace`."""
        meta_entry = next(
            (e for e in self.read_all() if e.kind == "meta"), None
        )
        title = (
            meta_entry.fields.get("task", "(no title)")
            if meta_entry is not None
            else "(no trace.log)"
        )
        loops_decl = (
            meta_entry.fields.get("loops", "").split(",")
            if meta_entry is not None
            else []
        )
        loops_decl = [l for l in loops_decl if l]

        iteration_entries = self.iterations()
        architect_entries = [
            e for e in iteration_entries if e.loop == "architect"
        ]
        inner_entries = [e for e in iteration_entries if e.loop == "inner"]
        refine_entries = [e for e in iteration_entries if e.loop == "refine"]
        outer_entries = [e for e in iteration_entries if e.loop == "outer"]

        iterations: List[Iteration] = []
        for e in architect_entries:
            k = e.get_int("k", 0)
            iterations.append(
                Iteration(
                    phase="inner",
                    label=f"p{k}",
                    loss_norm=e.get_float("loss_norm"),
                    raw_num=_raw_num(e.fields.get("raw", "0/1")),
                    raw_max=_raw_max(e.fields.get("raw", "0/1")),
                    skill_lines=[f"*{e.fields.get('skill', '')}* → {e.fields.get('action', '')}"],
                    mode="architect",
                    creativity=e.fields.get("creativity", "standard"),
                )
            )
        for loop_entries, prefix, phase in (
            (inner_entries, "i", "inner"),
            (refine_entries, "r", "refine"),
            (outer_entries, "o", "outer"),
        ):
            for e in loop_entries:
                k = e.get_int("k", 0)
                iterations.append(
                    Iteration(
                        phase=phase,
                        label=f"{prefix}{k}",
                        loss_norm=e.get_float("loss_norm"),
                        raw_num=_raw_num(e.fields.get("raw", "0/1")),
                        raw_max=_raw_max(e.fields.get("raw", "0/1")),
                        skill_lines=[
                            f"*{e.fields.get('skill', '(baseline)')}* → {e.fields.get('action', '')}"
                        ],
                        mode="reactive",
                    )
                )

        # Close block, if any close entry exists
        close_entries = [e for e in self.read_all() if e.kind == "close"]
        terminal = close_entries[-1].fields.get("terminal", "") if close_entries else "in-progress"
        layer = close_entries[-1].fields.get("layer", "") if close_entries else ""
        docs = close_entries[-1].fields.get("docs", "") if close_entries else ""

        budgets = {}
        if inner_entries:
            budgets["inner"] = (len(inner_entries), 5)
        if refine_entries:
            budgets["refine"] = (len(refine_entries), 3)
        if outer_entries:
            budgets["outer"] = (len(outer_entries), 1)

        loops_used = []
        if architect_entries or inner_entries:
            loops_used.append("inner")
        if refine_entries:
            loops_used.append("refine")
        if outer_entries:
            loops_used.append("outer")

        # Layer string is stored as one blob; split on the first "·" only so
        # we can render `4:... · 5:...` patterns the caller may have provided.
        layer_parts = [p.strip() for p in layer.split("·", 1)] if layer else ["", ""]
        layer_4 = layer_parts[0] if len(layer_parts) >= 1 else ""
        layer_5 = layer_parts[1] if len(layer_parts) >= 2 else ""

        return Task(
            title=title,
            loops_used=loops_used,
            budgets=budgets,
            iterations=iterations,
            fix_layer_4=layer_4,
            fix_layer_5=layer_5,
            docs_synced=docs,
            terminal=terminal,
        )


def _raw_num(raw: str) -> float:
    if not raw:
        return 0.0
    num_part = raw.split("/")[0].strip()
    if num_part == "½":
        return 0.5
    try:
        return float(num_part)
    except ValueError:
        return 0.0


def _raw_max(raw: str) -> int:
    if "/" not in raw:
        return 1
    try:
        return int(raw.split("/", 1)[1])
    except ValueError:
        return 1


# ---------------------------------------------------------------------------
# Task segmentation — v0.5.2
# ---------------------------------------------------------------------------

@dataclass
class TaskSlice:
    """One task's worth of trace entries: meta → iterations → optional close.

    A trace.log accumulates multiple tasks over time; the aggregator operates
    on completed slices, the current-task detector operates on the last slice
    (which may lack a close entry if the task is still in flight).
    """

    meta: TraceEntry
    iterations: List[TraceEntry] = field(default_factory=list)
    close: Optional[TraceEntry] = None

    @property
    def is_closed(self) -> bool:
        return self.close is not None

    @property
    def terminal(self) -> Optional[str]:
        return self.close.fields.get("terminal") if self.close else None

    @property
    def k_count(self) -> int:
        """Number of non-baseline iterations."""
        return sum(1 for e in self.iterations if e.fields.get("baseline") != "true")

    @property
    def loops_used(self) -> List[str]:
        out: List[str] = []
        for e in self.iterations:
            if e.loop not in out:
                out.append(e.loop)
        return out

    def loss_series(self, loop: str) -> List[float]:
        return [e.get_float("loss_norm") for e in self.iterations if e.loop == loop]


def segment_tasks(entries: List[TraceEntry]) -> List[TaskSlice]:
    """Partition a flat entry list into task slices.

    Rules:
        meta   → starts a new task slice (closes the previous if any)
        iter   → appended to current slice
        close  → attached to current slice (does not close the slice reference —
                 a future meta may still follow; the close marks `is_closed`)

    Tolerance rule (v0.5.2): if the first entry is an iteration without a
    preceding meta (legacy/hand-written trace.log), a synthetic meta is
    created so the orphan iterations form a valid slice. This is pragmatic
    — trace.log files from before v0.5.2 may skip the meta header.
    """
    slices: List[TaskSlice] = []
    current: Optional[TaskSlice] = None
    for e in entries:
        if e.kind == "meta":
            if current is not None:
                slices.append(current)
            current = TaskSlice(meta=e)
        elif current is None:
            # Legacy/hand-written trace: synthesize a meta so iteration
            # entries are not silently dropped.
            synthetic_meta = TraceEntry(
                timestamp=e.timestamp,
                loop="meta",
                kind="meta",
                fields={"task": "(legacy-trace, no meta header)", "loops": ""},
            )
            current = TaskSlice(meta=synthetic_meta)
            if e.kind == "iter":
                current.iterations.append(e)
            elif e.kind == "close":
                current.close = e
        elif e.kind == "iter":
            current.iterations.append(e)
        elif e.kind == "close":
            current.close = e
    if current is not None:
        slices.append(current)
    return slices


# add segmentation helpers to TraceStore as methods by monkey-patching
# (keeps the class tightly scoped above; helpers below are pure on entries)

def _ts_segment_tasks(self: "TraceStore") -> List[TaskSlice]:
    return segment_tasks(self.read_all())


def _ts_current_task(self: "TraceStore") -> Optional[TaskSlice]:
    slices = self.segment_tasks()
    return slices[-1] if slices else None


def _ts_completed_tasks(self: "TraceStore") -> List[TaskSlice]:
    return [s for s in self.segment_tasks() if s.is_closed]


TraceStore.segment_tasks = _ts_segment_tasks  # type: ignore[attr-defined]
TraceStore.current_task = _ts_current_task  # type: ignore[attr-defined]
TraceStore.completed_tasks = _ts_completed_tasks  # type: ignore[attr-defined]
