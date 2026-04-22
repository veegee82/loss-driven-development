#!/usr/bin/env bash
# LDD_HEARTBEAT_HOOK_v3 — auto-installed by the LDD host-statusline skill.
# Writes last-tool-activity timestamp on every PreToolUse event so the
# permanent statusline can show "⚡ <age>s <tool>" while long tool sequences
# execute between ldd_trace append/close emissions.
#
# Multi-clauding-safe since v0.13.1:
#   .ldd/heartbeats/<session_id>  — per-session file (primary)
#   .ldd/heartbeat                — legacy singular file (kept for backwards
#                                   compatibility with v0.13.0-era statusline/
#                                   session_gate readers)
#
# v3 (v0.13.2): also seeds the session-gate marker when a tool fires.
# Rationale — before v3 the session marker was written ONLY by `ldd_trace
# init`, so a session that used LDD skills via chat content (skill-invocation,
# inline trace blocks) without running the explicit task lifecycle left
# `.ldd/sessions/<sid>` absent and the statusline stuck at `LDD · standby`
# despite visible activity. v3 treats "a Claude-Code tool fired in an LDD
# project" as sufficient evidence that the session is LDD-aware; the marker
# is minimal (no `task=` line), so a later `ldd_trace init` still overwrites
# it with the real task pointer. See git log a44d634 for the L5-conceptual
# residue this closes.
#
# Do not edit in place — the skill detects this marker and reinstalls.

set -uo pipefail

input=$(cat 2>/dev/null || echo "{}")
tool=$(jq -r '.tool_name // "unknown"' <<<"$input" 2>/dev/null || echo "unknown")
sid=$(jq -r '.session_id // empty' <<<"$input" 2>/dev/null || echo "")

# Resolve project root: prefer explicit cwd from hook input, fall back to pwd.
cwd=$(jq -r '.cwd // empty' <<<"$input" 2>/dev/null || true)
[[ -z "$cwd" ]] && cwd="$PWD"

trace_dir="${cwd}/.ldd"
[[ -d "$trace_dir" ]] || exit 0  # no LDD in this project — silent no-op

ts=$(date -u +%s)
line="$ts $tool $sid"

# Per-session file — primary write, keeps each Claude Code session's
# activity isolated from the others under multi-clauding.
if [[ -n "$sid" ]]; then
    mkdir -p "${trace_dir}/heartbeats"
    # Write atomically: temp file + rename. Protects against torn reads from
    # concurrent statusline renders.
    tmp="${trace_dir}/heartbeats/.${sid}.tmp.$$"
    printf '%s\n' "$line" > "$tmp" && mv -f "$tmp" "${trace_dir}/heartbeats/${sid}"
fi

# Legacy singular file — still written so pre-v0.13.1 statusline.sh copies
# and the old session_gate fallback continue to work. Last-writer-wins here
# is the historical behaviour; the per-session file above is what matters.
printf '%s\n' "$line" > "${trace_dir}/heartbeat"

# Session-gate marker seed (v3) — see header comment. We write a MINIMAL
# marker (one line, `session_id=<sid>`, no `task=`) so that `ldd_trace init`
# can later overwrite it with the real task pointer. Idempotent: existing
# markers with a `task=` line are preserved untouched — we only seed when
# the marker is absent. The singular `.ldd/session_active` is seeded under
# the same condition for the legacy-reader fallback path.
if [[ -n "$sid" ]]; then
    sessions_dir="${trace_dir}/sessions"
    marker="${sessions_dir}/${sid}"
    if [[ ! -f "$marker" ]]; then
        mkdir -p "$sessions_dir"
        tmp="${sessions_dir}/.${sid}.tmp.$$"
        printf 'session_id=%s\n' "$sid" > "$tmp" && mv -f "$tmp" "$marker"
    fi
    # Seed legacy singular marker only when no prior marker exists at all
    # (an `ldd_trace init` run would have written one). If a legacy marker
    # points at a DIFFERENT session, do not overwrite — that session may
    # still be gating validly; the per-session marker above is what the
    # current session needs.
    legacy="${trace_dir}/session_active"
    if [[ ! -f "$legacy" ]]; then
        tmp="${trace_dir}/.session_active.tmp.$$"
        printf 'session_id=%s\n' "$sid" > "$tmp" && mv -f "$tmp" "$legacy"
    fi
fi
exit 0
