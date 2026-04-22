"""Activity gate + display-config reader for the Stop-hook.

Three artifacts live in `.ldd/` (v0.13.1+ layout):

    sessions/<session_id>  — one marker file per active Claude-Code session
                             (multi-clauding-safe). Existence is the gate.
    heartbeats/<session_id> — one heartbeat file per session, written by the
                              PreToolUse hook. Freshest mtime identifies the
                              current session when `ldd_trace` is invoked
                              without an explicit session id in the env.
    config.yaml            — optional per-project display config:

                                 display:
                                   verbosity: summary   # off|summary|full|debug
                                   gate_on_activity: true

Legacy (pre-v0.13.1) singular files `.ldd/session_active` and
`.ldd/heartbeat` are still read as a fallback so projects initialised
under v0.13.0 continue to render until their next `ldd_trace init`.

The YAML parser here is deliberately minimal — we accept only the shapes
the `display:` block uses today (one nested level, scalar values). No
PyYAML dependency.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Dict


_LEGACY_MARKER = "session_active"
_LEGACY_HEARTBEAT = "heartbeat"
_SESSIONS_DIR = "sessions"
_HEARTBEATS_DIR = "heartbeats"
_CONFIG_BASENAME = "config.yaml"


def _trace_dir(project: Path) -> Path:
    return project / ".ldd"


def _read_session_id_from_heartbeat(project: Path) -> str:
    """Pull the real Claude-Code session id out of a heartbeat file.

    Claude Code does not expose `$CLAUDE_SESSION_ID` as a shell env var;
    the only place the id is written inside the project is by the
    PreToolUse heartbeat hook. The hook fires on every
    Bash/Edit/Write/Read/Grep/Glob call, so by the time
    `ldd_trace init|append|close` runs there is always a fresh entry.

    Resolution order:
      1. Per-session `.ldd/heartbeats/<sid>` — pick the newest-mtime file.
         Under multi-clauding this identifies the session whose tool-call
         just triggered this `ldd_trace` invocation.
      2. Legacy singular `.ldd/heartbeat` — tolerated for projects that
         have not yet upgraded their installer.
    """
    trace_dir = _trace_dir(project)

    per_session = trace_dir / _HEARTBEATS_DIR
    if per_session.is_dir():
        try:
            files = [p for p in per_session.iterdir() if p.is_file()]
            if files:
                newest = max(files, key=lambda p: p.stat().st_mtime)
                # File name IS the session_id (the heartbeat hook names it so);
                # content is `<epoch> <tool_name> <session_id>` for diagnostics.
                try:
                    line = newest.read_text(encoding="utf-8").splitlines()[0]
                    parts = line.split()
                    if len(parts) >= 3:
                        return parts[2]
                except (OSError, IndexError):
                    pass
                return newest.name
        except OSError:
            pass

    hb = trace_dir / _LEGACY_HEARTBEAT
    if not hb.is_file():
        return ""
    try:
        first_line = hb.read_text(encoding="utf-8").splitlines()[0]
    except (OSError, IndexError):
        return ""
    parts = first_line.split()
    if len(parts) < 3:
        return ""
    return parts[2]


def mark_session_active(project: Path, task_title: str | None = None) -> None:
    """Record that LDD was used in the current Claude-Code session.

    Multi-clauding-safe: writes a per-session marker at
    `.ldd/sessions/<session_id>` with a two-line payload:

        session_id=<sid>
        task=<task_title>

    The statusline reads `task=` from this file (not from `trace.log`) so
    each session sees ITS own task even when several sessions share one
    trace file. `task=` is written only when the caller passes a fresh
    title (i.e. from `ldd_trace init`); `append` / `close` pass
    task_title=None and the line is preserved from the previous write.

    The legacy singular `.ldd/session_active` is ALSO written for
    backwards-compatibility with projects whose statusline / stop-hook
    still read the old path.

    Session id resolution:
      1. `$CLAUDE_SESSION_ID` env var — explicit override / test harness
      2. Newest `.ldd/heartbeats/<sid>` — per-session hook layout
      3. Third column of legacy `.ldd/heartbeat` — pre-v0.13.1 fallback
      4. empty string (plain-shell use; gate allows on empty per contract)
    """
    session_id = os.environ.get("CLAUDE_SESSION_ID", "") \
        or _read_session_id_from_heartbeat(project)
    trace_dir = _trace_dir(project)
    try:
        trace_dir.mkdir(parents=True, exist_ok=True)
        if session_id:
            sessions_dir = trace_dir / _SESSIONS_DIR
            sessions_dir.mkdir(exist_ok=True)
            marker_path = sessions_dir / session_id
            # Preserve existing task= line when caller did not supply a new one
            # (append / close path). Fresh init always supplies task_title.
            existing_task = ""
            if task_title is None and marker_path.is_file():
                for ln in marker_path.read_text(encoding="utf-8").splitlines():
                    if ln.startswith("task="):
                        existing_task = ln.partition("=")[2]
                        break
            effective_task = task_title if task_title is not None else existing_task
            payload = [f"session_id={session_id}"]
            if effective_task:
                payload.append(f"task={effective_task}")
            marker_path.write_text("\n".join(payload) + "\n", encoding="utf-8")
        # Legacy singular marker — keep writing so v0.13.0-era readers still work.
        (trace_dir / _LEGACY_MARKER).write_text(
            f"session_id={session_id}\n", encoding="utf-8"
        )
    except OSError:
        # Marker write is best-effort; failure must not block the trace itself.
        pass


def session_gate_allows(project: Path, hook_session_id: str) -> bool:
    """Return True iff the Stop-hook / statusline should render for this session.

    New (v0.13.1+) layout — existence check on the per-session marker:
      - `.ldd/sessions/<hook_session_id>` exists → True

    Legacy fallback — singular `.ldd/session_active`:
      - missing                             → False (no LDD activity seen)
      - marker's session_id empty OR
        hook's session_id empty             → True  (plain-shell / freshly
                                                     installed; gate is a
                                                     filter, not a lock)
      - match / mismatch                    → equality
    """
    trace_dir = _trace_dir(project)

    # Per-session marker — multi-clauding-correct path.
    if hook_session_id:
        if (trace_dir / _SESSIONS_DIR / hook_session_id).is_file():
            return True

    # Legacy singular marker — keeps v0.13.0-era installs rendering.
    marker = trace_dir / _LEGACY_MARKER
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
