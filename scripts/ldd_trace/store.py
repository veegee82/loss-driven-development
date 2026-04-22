"""Persistence layer — read/write `.ldd/trace.log` in a project directory.

Line format after v0.11.0 (one entry per line, space-separated key=value):

    2026-04-22T02:24:45Z  design  k=0  skill=architect-mode  action="..."  \
        loss=0.857  raw=6/7

    2026-04-22T02:24:45Z  inner  k=4  skill=method-evolution  action="..."  \
        loss=0.000  raw=0/33  loss_type=rate  Δloss=-0.031

Meta line (task open) — carries the thinking-level on the meta line, so
per-iteration lines no longer repeat `mode=`/`creativity=`:

    2026-04-22T02:24:45Z  meta  L4/method  creativity=inventive  dispatch=auto  \
        task="..."  loops=design,cot,inner,refine,outer

Close lines are unchanged:
    2026-04-21T17:38:00Z  inner  close  terminal=complete  layer="..."  docs=synced

Backward compatibility (read-only): `_parse_line` accepts BOTH formats.
`loss_norm=` and `loss=` are both accepted on read; `loss_type=normalized-rubric`
may be absent or present; the loop name `architect` is accepted as an alias
for `design`; stray `mode=`/`creativity=` fields on iter lines are read and
discarded (they were redundant with the level on the meta line).

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

# Magic prefix for Tier-2 (conversation-history) persistence — see
# skills/bootstrap-userspace/SKILL.md. Any line starting with this exact
# 12-char sequence is a machine-readable LDD trace entry that can be
# ingested back into .ldd/trace.log by parse_magic_lines / `ldd_trace
# ingest`. Do not change without a version bump to v2 — existing pasted
# chat transcripts rely on the literal.
MAGIC_PREFIX = "⟪LDD-TRACE-v1⟫"


def _utcnow_iso() -> str:
    # Microsecond precision so sequential appends always have strictly
    # increasing timestamps. Without this, a tight loop of appends collides
    # in the same second and the projection falls back to stable-sort build
    # order (design → inner → refine → outer → cot), which mis-orders
    # narrative events like a mid-task CoT detour. Legacy second-precision
    # entries still parse and sort correctly (`.` < `Z` lexically keeps
    # legacy-second entries ordered before any same-second fractional entries).
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


# Local copies of the normative mappings. `level_scorer.LEVEL_NAMES` is the
# single source of truth, but importing it at module load would create a
# cross-package coupling (scripts/ld_trace lives outside scripts/). These
# dicts mirror the spec §Level name mapping table verbatim.
_LEVEL_NAMES = {
    "L0": "reflex",
    "L1": "diagnostic",
    "L2": "deliberate",
    "L3": "structural",
    "L4": "method",
}

_DISPATCH_SHORT = {
    "auto-level": "auto",
    "user-explicit": "explicit",
    "user-bump": "bump",
    "user-override-down": "override-down",
}


def _level_name_for(code: str) -> str:
    return _LEVEL_NAMES.get(code, "")


def _dispatch_short_for(source: str) -> str:
    """Translate the legacy long dispatch-source string to its short form.

    Already-short values (``auto`` / ``explicit`` / ``bump`` / ``override-down``)
    pass through unchanged so the method can be called on either convention.
    """
    if source in _DISPATCH_SHORT:
        return _DISPATCH_SHORT[source]
    return source


@dataclass
class TraceEntry:
    """One parsed line from `.ldd/trace.log`.

    The ``loop`` field for iteration entries is normalized on read: the legacy
    ``architect`` loop name from pre-v0.11.0 traces is rewritten to ``design``
    so downstream consumers only see the new name. Writers always emit the
    new name.
    """

    timestamp: str
    loop: str                                  # "inner" | "refine" | "outer" | "design" | "cot" | "meta"
    kind: str                                  # "iter" | "close" | "meta"
    fields: Dict[str, str] = field(default_factory=dict)

    def get_float(self, key: str, default: float = 0.0) -> float:
        v = self.fields.get(key)
        if v is None:
            # Backward-compat: accept the old `loss_norm` spelling when `loss`
            # is requested, and vice versa.
            if key == "loss":
                v = self.fields.get("loss_norm")
            elif key == "loss_norm":
                v = self.fields.get("loss")
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


_LEVEL_LABEL_RE = __import__("re").compile(r"^L([0-4])/([a-z]+)$")


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
    # Normalize legacy loop name `architect` → `design` (v0.11.0). Writers emit
    # `design`; readers accept both so pre-v0.11.0 traces still project.
    if loop == "architect":
        loop = "design"
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
        # v0.11.0 meta line carries the level as a positional, unquoted token
        # `L<n>/<name>` (e.g. `L4/method`). Recognized only on meta lines.
        if loop == "meta":
            m = _LEVEL_LABEL_RE.match(tok)
            if m:
                fields["level"] = f"L{m.group(1)}"
                fields["level_name"] = m.group(2)
                # Keep a back-compat alias so callers that still read
                # `level_chosen` (the v0.10.1 field) continue to work.
                fields.setdefault("level_chosen", f"L{m.group(1)}")
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
    elif loop == "epoch":
        # v0.13.x Fix 1 — epoch boundary marker; not a meta (does NOT start a
        # new task slice) and not an iteration (no k / skill / loss). Its own
        # kind so segment_tasks can route it to the slice's epoch list.
        kind = "epoch"
    else:
        kind = "iter"
    return TraceEntry(timestamp=timestamp, loop=loop, kind=kind, fields=fields)


# Meta-line canonical field order (v0.11.0, spec §Trace-log format):
#   1. level label (positional `L<n>/<name>`, unquoted)
#   2. creativity=<value>  (only at L3/L4)
#   3. dispatch=<auto|explicit|bump|override-down>
#   4. signals=<sig1:±w1,sig2:±w2,…>  (v0.13.x — telemetry baseline; optional)
#   5. task="…"
#   6. loops=…
_META_FIELD_ORDER = (
    "creativity",
    "dispatch",
    "dispatched",
    "signals",
    "store",
    "task",
    "loops",
)

# Fields that are synthesized by the reader and must NOT be written back to
# the log (they appear in `TraceEntry.fields` only as parser artifacts).
_META_READER_ONLY = {"level", "level_name", "level_chosen"}


def _kv(k: str, v: str) -> str:
    """Serialize ``key=value`` safe for round-trip through :func:`shlex.split`.

    Plain values (no whitespace, no quote characters) pass through as
    ``key=value``. Anything containing whitespace or a quote character is
    shlex-quoted — this keeps the `key="` prefix for backward-compatible
    eyeballing when possible, but switches to :func:`shlex.quote` (which
    emits single quotes) whenever the value itself contains a double
    quote. Pre-v0.11.x traces used a naive ``f'{k}="{v}"'`` that silently
    truncated on inner double quotes; the new form is lossless.
    """
    if not any(c in v for c in (" ", "\t", '"', "'")):
        return f"{k}={v}"
    if '"' not in v:
        return f'{k}="{v}"'
    return f"{k}={shlex.quote(v)}"


def _serialize_entry(entry: TraceEntry) -> str:
    parts = [entry.timestamp, entry.loop]
    if entry.kind == "close":
        parts.append("close")
    elif entry.kind == "iter" and entry.fields.get("baseline") == "true":
        parts.append("baseline")

    # Meta lines use the new canonical positional+ordered field layout.
    if entry.kind == "meta":
        # Positional level label — prefer the exploded `level` + `level_name`,
        # fall back to legacy `level_chosen` if only that is set.
        level = entry.fields.get("level") or entry.fields.get("level_chosen")
        level_name = entry.fields.get("level_name")
        if level and level_name:
            parts.append(f"{level}/{level_name}")
        for key in _META_FIELD_ORDER:
            if key in entry.fields:
                parts.append(_kv(key, entry.fields[key]))
        # Any additional meta fields not in the canonical order (forward-compat
        # extensibility) get appended after, skipping reader-only + already-
        # emitted keys and legacy duplicates we translated above.
        legacy_skip = {"dispatch_source"} if "dispatch" in entry.fields else set()
        for k, v in entry.fields.items():
            if k in _META_FIELD_ORDER or k in _META_READER_ONLY or k in legacy_skip:
                continue
            parts.append(_kv(k, v))
        return "  ".join(parts)

    for k, v in entry.fields.items():
        if k == "baseline":
            continue
        parts.append(_kv(k, v))
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

    def init(
        self,
        task_title: str,
        loops: List[str],
        level_chosen: Optional[str] = None,
        dispatch_source: Optional[str] = None,
        creativity: Optional[str] = None,
        store_scope: Optional[str] = None,
        dispatched: Optional[str] = None,
        signals: Optional[str] = None,
    ) -> TraceEntry:
        """Create trace.log with a meta header. Idempotent per-task — if a
        meta entry already exists with the same title, reuse it.

        v0.11.0 layout (spec 2026-04-22-level-name-consolidation):
        the meta line carries the thinking-level as a positional `L<n>/<name>`
        token, an optional `creativity=<value>` (only at L3/L4), and a short
        `dispatch=<auto|explicit|bump|override-down>` field — so per-iter
        lines no longer need to repeat `mode=`/`creativity=`.

        Inputs:
            level_chosen: one of ``L0``..``L4`` (back-compat name; new callers
                may still pass the short code — the name is resolved from
                :data:`level_scorer.LEVEL_NAMES` when available).
            dispatch_source: legacy long form (``auto-level`` / ``user-explicit``
                / ``user-bump`` / ``user-override-down``); translated to the
                short ``dispatch=`` form on write.
            creativity: ``conservative`` / ``standard`` / ``inventive`` — only
                persisted at L3/L4.
        """
        self.ensure_dir()
        if self.exists():
            for entry in self.read_all():
                if entry.kind == "meta" and entry.fields.get("task") == task_title:
                    return entry
        fields: Dict[str, str] = {}
        if level_chosen is not None:
            fields["level"] = level_chosen
            fields["level_name"] = _level_name_for(level_chosen)
        if creativity is not None and level_chosen in ("L3", "L4"):
            fields["creativity"] = creativity
        if dispatch_source is not None:
            fields["dispatch"] = _dispatch_short_for(dispatch_source)
        if dispatched is not None:
            fields["dispatched"] = dispatched
        if signals is not None and signals.strip():
            fields["signals"] = signals.strip()
        if store_scope is not None:
            fields["store"] = store_scope
        fields["task"] = task_title
        fields["loops"] = ",".join(loops)
        entry = TraceEntry(
            timestamp=_utcnow_iso(),
            loop="meta",
            kind="meta",
            fields=fields,
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

    def current_task_entries(self) -> List[TraceEntry]:
        """Return the slice of entries belonging to the CURRENT task only.

        A trace.log can accumulate multiple tasks over its lifetime —
        every `ldd_trace init` appends a new `meta` line, potentially
        after a prior task closed with `terminal=...`. The renderer +
        next-k accounting must scope to the latest task; otherwise a
        fresh task inherits the old task's iteration count and closing
        marker, producing the stale "diagnose + fix ldd statusline
        idle-state (complete) · inner×10" display even after an `init`
        for a brand-new task.

        Returns: [last_meta, iter*, close?] — everything from the last
        meta entry to end-of-file, inclusive of the meta itself.
        """
        all_entries = self.read_all()
        last_meta_idx = -1
        for i, e in enumerate(all_entries):
            if e.kind == "meta":
                last_meta_idx = i
        if last_meta_idx < 0:
            return []
        return all_entries[last_meta_idx:]

    def next_k(self, loop: str) -> int:
        """Next iteration index for `loop`, scoped to the CURRENT task.

        Scoping to the current task (entries after the last `meta` line)
        means `ldd_trace init; append --loop inner` always starts at
        k=0, even if a prior task on the same trace.log closed at k=4.

        The v0.11.0 loop rename `architect → design` is honored on read:
        callers asking for `next_k("architect")` also see pre-rename entries
        and vice versa (the reader normalizes on parse).
        """
        if loop == "architect":
            loop = "design"
        max_k = -1
        for e in self.current_task_entries():
            if e.kind != "iter" or e.loop != loop:
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
        predicted_delta: Optional[float] = None,
        loss_vec: Optional[str] = None,
        epoch: Optional[int] = None,
    ) -> TraceEntry:
        # v0.11.0: the legacy loop name `architect` collapses to `design`
        # (the protocol's design phase). Writers always emit the new name.
        if loop == "architect":
            loop = "design"
        # `mode` is derived from level and no longer persisted; `creativity`
        # is carried once on the meta line, not per iter. The keyword args
        # are kept in the signature for backward-compatible call sites
        # (scripts/demo-*, tests) but are silently ignored on write.
        _ = mode
        _ = creativity
        prev_same_loop = [e for e in self.iterations() if e.loop == loop]
        delta: Optional[float] = None
        if prev_same_loop and not baseline:
            prev_loss = prev_same_loop[-1].get_float("loss", 0.0)
            delta = loss_norm - prev_loss
        fields: Dict[str, str] = {
            "k": str(k),
            "skill": skill,
            "action": action,
            "loss": f"{loss_norm:.3f}",
            "raw": raw,
        }
        # `loss_type` is persisted only when it differs from the default
        # `normalized-rubric` — the default is implicit in the absence of
        # the field, matching the new v0.11.0 per-iter format.
        if loss_type and loss_type != "normalized-rubric":
            fields["loss_type"] = loss_type
        if baseline:
            fields["baseline"] = "true"
        if delta is not None:
            sign = "-" if delta < 0 else ("+" if delta > 0 else "±")
            fields["Δloss"] = f"{sign}{abs(delta):.3f}" if sign != "±" else "±0.000"
        if predicted_delta is not None:
            # v0.7.0 calibration — log predicted Δloss from the dialectical pass
            p_sign = "-" if predicted_delta < 0 else ("+" if predicted_delta > 0 else "±")
            fields["predicted_Δloss"] = (
                f"{p_sign}{abs(predicted_delta):.3f}" if p_sign != "±" else "±0.000"
            )
            # Also compute prediction_error if we have an actual delta
            if delta is not None:
                err = predicted_delta - delta
                e_sign = "-" if err < 0 else ("+" if err > 0 else "±")
                fields["prediction_error"] = (
                    f"{e_sign}{abs(err):.3f}" if e_sign != "±" else "±0.000"
                )
        if notes:
            fields["notes"] = notes
        # v0.13.x Fix 1 — vector loss + epoch pass-through. Writers that pass
        # loss_vec also keep the scalar loss=…; the scalar is a convenience
        # mean that the renderer falls back to when the caller is not
        # vector-aware. Readers prefer loss_vec when both are present.
        if loss_vec is not None and loss_vec.strip():
            fields["loss_vec"] = loss_vec.strip()
        if epoch is not None and epoch != 0:
            # Default epoch is 0 → omit to keep the trace diff-minimal
            fields["epoch"] = str(epoch)
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
        loss_final: Optional[float] = None,
        regression_followed: Optional[bool] = None,
    ) -> TraceEntry:
        """Close a loop with terminal status.

        Thinking-levels integration (v0.10.1+): `loss_final` persists the
        task's final normalized loss so method-evolution can detect
        low-side level misses across tasks. `regression_followed` is set
        retroactively (by a later task closing in the same area with a
        higher loss) and marks this task as a candidate for
        scorer-weight re-tuning.
        """
        fields: Dict[str, str] = {"terminal": terminal}
        if layer:
            fields["layer"] = layer
        if docs:
            fields["docs"] = docs
        if notes:
            fields["notes"] = notes
        if loss_final is not None:
            fields["loss_final"] = f"{loss_final:.3f}"
        if regression_followed is not None:
            fields["regression_followed"] = "true" if regression_followed else "false"
        entry = TraceEntry(
            timestamp=_utcnow_iso(),
            loop=loop,
            kind="close",
            fields=fields,
        )
        self._append(entry)
        return entry

    def append_epoch_bump(
        self,
        new_epoch: int,
        reason: str,
    ) -> TraceEntry:
        """Record an epoch boundary — a deliberate rubric/scope shift.

        Epoch semantics (v0.13.x Fix 1):
            Δloss is comparable **within** an epoch. Cross-epoch comparison is
            meaningless because the measurement frame changed. Writers that
            hit a rubric update, a mid-task bedrohungsmodell shift, or any
            moving-target-loss event should call this BEFORE emitting
            iterations under the new frame. The next iteration's `epoch=N`
            must match ``new_epoch``; the renderer draws a boundary marker.

        Anti-abuse guard:
            Frequent epoch bumps (more than one per 5 iterations within a
            task) are surface-level evidence of moving-target-loss; the
            drift-detection skill reads these lines and warns.
        """
        if not reason.strip():
            raise ValueError("epoch bump requires a non-empty reason")
        fields = {
            "epoch": str(new_epoch),
            "reason": reason.strip(),
        }
        entry = TraceEntry(
            timestamp=_utcnow_iso(),
            loop="epoch",
            kind="epoch",
            fields=fields,
        )
        self._append(entry)
        return entry

    def current_epoch(self) -> int:
        """Latest epoch number written to the trace, or 0 if none."""
        latest = 0
        for e in self.read_all():
            if e.kind == "epoch":
                try:
                    latest = max(latest, int(e.fields.get("epoch", "0")))
                except ValueError:
                    continue
        return latest

    def _append(self, entry: TraceEntry) -> None:
        self.ensure_dir()
        with self.trace_path.open("a", encoding="utf-8") as f:
            f.write(_serialize_entry(entry) + "\n")

    # --- projection ----------------------------------------------------

    def to_task(self) -> Task:
        """Project the CURRENT task (latest meta onwards) for `render_trace`.

        A trace.log may hold multiple historical tasks; scope to the last
        meta line so the rendered summary / sparkline reflects the task
        the user is working on NOW, not the aggregate since day one.
        """
        current = self.current_task_entries()
        meta_entry = current[0] if current else None
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

        iteration_entries = [e for e in current if e.kind == "iter"]
        # `design` is the new canonical name for what v0.10.x called the
        # `architect` loop. `_parse_line` already normalizes on read, so a
        # trace log mixing both spellings projects cleanly here.
        design_entries = [e for e in iteration_entries if e.loop == "design"]
        inner_entries = [e for e in iteration_entries if e.loop == "inner"]
        refine_entries = [e for e in iteration_entries if e.loop == "refine"]
        outer_entries = [e for e in iteration_entries if e.loop == "outer"]
        cot_entries = [e for e in iteration_entries if e.loop == "cot"]

        # Pull the meta-line creativity once (if present) so design iterations
        # inherit it for rendering — per-iter `creativity=` is no longer written.
        meta_creativity = (
            meta_entry.fields.get("creativity", "standard") if meta_entry else "standard"
        )

        iterations: List[Iteration] = []
        for e in design_entries:
            k = e.get_int("k", 0)
            iterations.append(
                Iteration(
                    phase="inner",
                    label=f"p{k}",
                    loss_norm=e.get_float("loss"),
                    raw_num=_raw_num(e.fields.get("raw", "0/1")),
                    raw_max=_raw_max(e.fields.get("raw", "0/1")),
                    skill_lines=[f"*{e.fields.get('skill', '')}* → {e.fields.get('action', '')}"],
                    # `mode` is kept on Iteration for one release as a read-compat
                    # hook; "architect" is only the renderer's phase-label cue.
                    mode="architect",
                    creativity=e.fields.get("creativity", meta_creativity),
                    timestamp=e.timestamp,
                    loss_vec=e.fields.get("loss_vec"),
                    epoch=e.get_int("epoch", 0),
                )
            )
        for loop_entries, prefix, phase in (
            (inner_entries, "i", "inner"),
            (refine_entries, "r", "refine"),
            (outer_entries, "o", "outer"),
            (cot_entries, "c", "cot"),
        ):
            for e in loop_entries:
                k = e.get_int("k", 0)
                iterations.append(
                    Iteration(
                        phase=phase,
                        label=f"{prefix}{k}",
                        loss_norm=e.get_float("loss"),
                        raw_num=_raw_num(e.fields.get("raw", "0/1")),
                        raw_max=_raw_max(e.fields.get("raw", "0/1")),
                        skill_lines=[
                            f"*{e.fields.get('skill', '(baseline)')}* → {e.fields.get('action', '')}"
                        ],
                        mode="reactive",
                        timestamp=e.timestamp,
                        loss_vec=e.fields.get("loss_vec"),
                        epoch=e.get_int("epoch", 0),
                    )
                )

        iterations.sort(key=lambda it: it.timestamp)

        # Close block, if any close entry exists
        # Scope close entries to the current task only — a historical close
        # from a prior task on the same trace.log must not leak into the
        # render of a freshly-init'd task.
        close_entries = [e for e in current if e.kind == "close"]
        terminal = close_entries[-1].fields.get("terminal", "") if close_entries else "in-progress"
        layer = close_entries[-1].fields.get("layer", "") if close_entries else ""
        docs = close_entries[-1].fields.get("docs", "") if close_entries else ""

        budgets = {}
        if design_entries:
            budgets["design"] = (len(design_entries), 5)
        if inner_entries:
            budgets["inner"] = (len(inner_entries), 5)
        if refine_entries:
            budgets["refine"] = (len(refine_entries), 3)
        if outer_entries:
            budgets["outer"] = (len(outer_entries), 1)
        if cot_entries:
            budgets["cot"] = (len(cot_entries), 8)

        loops_used = []
        if design_entries:
            loops_used.append("design")
        if inner_entries:
            loops_used.append("inner")
        if refine_entries:
            loops_used.append("refine")
        if outer_entries:
            loops_used.append("outer")
        if cot_entries:
            loops_used.append("cot")

        # Layer string is stored as one blob; split on the first "·" only so
        # we can render `4:... · 5:...` patterns the caller may have provided.
        layer_parts = [p.strip() for p in layer.split("·", 1)] if layer else ["", ""]
        layer_4 = layer_parts[0] if len(layer_parts) >= 1 else ""
        layer_5 = layer_parts[1] if len(layer_parts) >= 2 else ""

        # Meta-line header fields (v0.11.x) — bootstrap-userspace + using-ldd
        # carry Store + Dispatched + Mode indicator through the meta line so
        # the renderer can surface them without a separate sidecar file.
        meta_fields = meta_entry.fields if meta_entry is not None else {}
        store_scope = meta_fields.get("store", "")
        dispatched_raw = meta_fields.get("dispatched", "")
        level = meta_fields.get("level", "")
        level_name = meta_fields.get("level_name", "")
        creativity = meta_fields.get("creativity", "")

        # Derive a default Dispatched line when the caller only supplied
        # level + dispatch-source, so a trace initialized with just level=L4 /
        # dispatch=auto still renders a useful header line.
        if not dispatched_raw and level:
            dispatch_short = meta_fields.get("dispatch", "")
            level_label = f"{level}/{level_name}" if level_name else level
            dispatch_long = {
                "auto": "auto-level",
                "explicit": "user-explicit",
                "bump": "user-bump",
                "override-down": "user-override-down",
            }.get(dispatch_short, dispatch_short)
            if dispatch_long:
                dispatched_raw = f"{dispatch_long} {level_label}"

        return Task(
            title=title,
            loops_used=loops_used,
            budgets=budgets,
            iterations=iterations,
            fix_layer_4=layer_4,
            fix_layer_5=layer_5,
            docs_synced=docs,
            terminal=terminal,
            store=store_scope,
            dispatched=dispatched_raw,
            level=level,
            level_name=level_name,
            creativity=creativity,
        )


def emit_magic_line(entry: TraceEntry) -> str:
    """Render `entry` as a single conversation-history-safe line.

    Prefixes the canonical serialization with `MAGIC_PREFIX` so the line
    is greppable inside arbitrary chat transcripts. Used by Tier-2
    (conversation-history) persistence from `bootstrap-userspace`:
    the agent emits these lines in its visible reply, the platform
    retains the conversation, and a later session (possibly in a
    different host) can scan the transcript for the magic prefix to
    reconstruct the trace.
    """
    return f"{MAGIC_PREFIX} {_serialize_entry(entry)}"


def parse_magic_lines(text: str) -> List[TraceEntry]:
    """Extract all `MAGIC_PREFIX`-marked trace entries from arbitrary text.

    Ignores non-magic lines and lines that fail to parse. The magic
    prefix may appear anywhere on the line — leading whitespace and
    embedding inside quoted blocks are tolerated, so pasted chat text
    with surrounding prose still yields the entries.
    """
    entries: List[TraceEntry] = []
    for raw_line in text.splitlines():
        idx = raw_line.find(MAGIC_PREFIX)
        if idx < 0:
            continue
        rest = raw_line[idx + len(MAGIC_PREFIX):].strip()
        if not rest:
            continue
        parsed = _parse_line(rest)
        if parsed is not None:
            entries.append(parsed)
    return entries


def _entry_key(entry: TraceEntry) -> tuple:
    """Identity tuple for deduplication during ingest.

    Two entries are considered duplicates when they share timestamp,
    loop, kind, AND the `k` / `terminal` disambiguator (so a meta and
    a k=0 baseline at the same second don't collide).
    """
    disambig = entry.fields.get("k") or entry.fields.get("terminal") or entry.fields.get("task") or ""
    return (entry.timestamp, entry.loop, entry.kind, disambig)


def ingest_magic_lines(store: "TraceStore", text: str) -> int:
    """Append magic-prefixed entries from `text` to `store`, skipping duplicates.

    Returns the number of entries actually appended. A magic line whose
    identity tuple already exists in the store is silently skipped —
    this makes the ingest operation idempotent, so re-pasting the same
    chat transcript twice never double-counts.
    """
    new_entries = parse_magic_lines(text)
    if not new_entries:
        return 0
    existing_keys = {_entry_key(e) for e in store.read_all()}
    appended = 0
    for entry in new_entries:
        if _entry_key(entry) in existing_keys:
            continue
        store._append(entry)
        existing_keys.add(_entry_key(entry))
        appended += 1
    return appended


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
        # `get_float("loss")` auto-falls-back to the legacy `loss_norm` spelling,
        # so this call works on both pre- and post-v0.11.0 traces.
        if loop == "architect":
            loop = "design"
        return [e.get_float("loss") for e in self.iterations if e.loop == loop]


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
