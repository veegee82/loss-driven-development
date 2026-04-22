#!/usr/bin/env bash
# LDD_HEARTBEAT_HOOK_v1 — auto-installed by the LDD host-statusline skill.
# Writes last-tool-activity timestamp to .ldd/heartbeat on every PreToolUse event
# so the permanent statusline can show "⚡ <age>s <tool>" while long tool
# sequences execute between ldd_trace append/close emissions.
#
# Do not edit in place — the skill detects this marker and reinstalls.
# Customise by overriding .claude/hooks/ldd_heartbeat.sh AND removing the
# marker line, so the skill leaves your copy alone.

set -uo pipefail

input=$(cat 2>/dev/null || echo "{}")
tool=$(jq -r '.tool_name // "unknown"' <<<"$input" 2>/dev/null || echo "unknown")

# Resolve project root: prefer explicit cwd from hook input, fall back to pwd.
cwd=$(jq -r '.cwd // empty' <<<"$input" 2>/dev/null || true)
[[ -z "$cwd" ]] && cwd="$PWD"

trace_dir="${cwd}/.ldd"
[[ -d "$trace_dir" ]] || exit 0  # no LDD in this project — silent no-op

ts=$(date -u +%s)
printf '%s %s\n' "$ts" "$tool" > "${trace_dir}/heartbeat"
exit 0
