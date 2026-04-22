#!/usr/bin/env bash
# LDD_HEARTBEAT_HOOK_v2 — auto-installed by the LDD host-statusline skill.
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
exit 0
