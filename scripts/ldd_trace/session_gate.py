"""Activity gate + display-config reader for the Stop-hook.

Two artifacts live in `.ldd/`:

    session_active  — one-line "session_id=<id>" marker, rewritten on every
                      `ldd_trace init/append/close`. The Stop-hook compares
                      this with `$LDD_HOOK_SESSION_ID` (the session_id from
                      its own JSON input) to decide whether LDD was used in
                      THIS session.

    config.yaml     — optional per-project display config:

                          display:
                            verbosity: summary          # off|summary|full|debug
                            gate_on_activity: true

                      Missing file → defaults (gate ON, verbosity "summary"
                      when used from the hook).

The YAML parser here is deliberately minimal — we accept only the shapes
the `display:` block uses today (one nested level, scalar values). No
PyYAML dependency. If the file syntax is exotic, we degrade to defaults
rather than importing a library for one file.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Dict


_MARKER_BASENAME = "session_active"
_CONFIG_BASENAME = "config.yaml"


def _trace_dir(project: Path) -> Path:
    return project / ".ldd"


def _read_session_id_from_heartbeat(project: Path) -> str:
    """Pull the real Claude-Code session id out of `.ldd/heartbeat`.

    Claude Code does not expose `$CLAUDE_SESSION_ID` as a shell env var;
    the only place the id is written inside the project is by the
    PreToolUse heartbeat hook (third column of `.ldd/heartbeat`). The
    hook fires on every Bash/Edit/Write/Read/Grep/Glob call, so by the
    time `ldd_trace init|append|close` runs there is always a fresh
    heartbeat entry — the hook fires BEFORE the tool executes.
    """
    hb = _trace_dir(project) / "heartbeat"
    if not hb.is_file():
        return ""
    try:
        first_line = hb.read_text(encoding="utf-8").splitlines()[0]
    except (OSError, IndexError):
        return ""
    parts = first_line.split()
    # Line layout: `<epoch> <tool_name> <session_id>`. Older hooks wrote only
    # two columns, so tolerate both — return "" when no third column exists.
    if len(parts) < 3:
        return ""
    return parts[2]


def mark_session_active(project: Path) -> None:
    """Record that LDD was used in the current Claude-Code session.

    Writes `.ldd/session_active` with the real session id resolved by:
      1. `.ldd/heartbeat` third column (written by the PreToolUse hook;
         always populated under Claude Code)
      2. `$CLAUDE_SESSION_ID` env var (non-Claude-Code / test harness)
      3. empty string (plain shell use — legacy-allow in the gate)

    The marker is intentionally one line; the Stop-hook + statusline read
    only the first line.
    """
    session_id = _read_session_id_from_heartbeat(project)
    if not session_id:
        session_id = os.environ.get("CLAUDE_SESSION_ID", "")
    trace_dir = _trace_dir(project)
    try:
        trace_dir.mkdir(parents=True, exist_ok=True)
        (trace_dir / _MARKER_BASENAME).write_text(
            f"session_id={session_id}\n", encoding="utf-8"
        )
    except OSError:
        # Marker write is best-effort; failure must not block the trace itself.
        pass


def session_gate_allows(project: Path, hook_session_id: str) -> bool:
    """Return True iff the Stop-hook should render in this session.

    Rules:
      - no marker file                      → False  (no LDD activity seen)
      - marker present but session empty    → True   (legacy / shell use;
                                                       render to be safe)
      - marker's session_id matches hook's  → True
      - mismatch                            → False
    """
    marker = _trace_dir(project) / _MARKER_BASENAME
    if not marker.is_file():
        return False
    try:
        first_line = marker.read_text(encoding="utf-8").splitlines()[0]
    except (OSError, IndexError):
        return False
    if "=" not in first_line:
        return False
    _, _, marker_sid = first_line.partition("=")
    marker_sid = marker_sid.strip()
    # Empty on either side: fall through to "allow" so plain-shell users (no
    # $CLAUDE_SESSION_ID) and freshly-installed hooks (empty env) still see
    # the trace. The gate is a filter, not a lock.
    if not marker_sid or not hook_session_id:
        return True
    return marker_sid == hook_session_id


def load_display_config(project: Path) -> Dict[str, object]:
    """Parse `.ldd/config.yaml` display section. Defaults on any error.

    Returned dict keys (all optional):
        verbosity         : "off" | "summary" | "full" | "debug"
        gate_on_activity  : bool
    """
    path = _trace_dir(project) / _CONFIG_BASENAME
    if not path.is_file():
        return {}
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return {}

    out: Dict[str, object] = {}
    in_display = False
    for raw in lines:
        line = raw.rstrip()
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.startswith("display:"):
            in_display = True
            continue
        if not in_display:
            continue
        # Leaving the display block when a non-indented key appears.
        if line and not line.startswith((" ", "\t")):
            in_display = False
            continue
        if ":" not in stripped:
            continue
        key, _, value = stripped.partition(":")
        key = key.strip()
        # Strip inline comments + surrounding whitespace/quotes.
        value = value.split("#", 1)[0].strip().strip("\"'")
        if not key:
            continue
        if key == "verbosity" and value in {"off", "summary", "full", "debug"}:
            out["verbosity"] = value
        elif key == "gate_on_activity":
            out["gate_on_activity"] = value.lower() in {"true", "1", "yes", "on"}
    return out
