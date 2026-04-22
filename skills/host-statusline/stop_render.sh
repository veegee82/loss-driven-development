#!/usr/bin/env bash
# LDD_STOP_RENDER_v1 — Stop-event hook that renders the current `.ldd/trace.log`
# as a framed LDD trace block, so the block appears as the LAST visible artifact
# of every agent turn — even if the agent forgot to emit it explicitly or buried
# it inside a nested tool call.
#
# Installed by bootstrap-userspace alongside the statusline + heartbeat hook.
# Fires on the Stop and SubagentStop events (registered in
# .claude/settings.local.json). Output is returned via the top-level
# `systemMessage` field — the Claude Code hook schema permits that for
# Stop/SubagentStop, whereas `hookSpecificOutput.additionalContext` is
# reserved for UserPromptSubmit / PostToolUse and fails schema validation
# when emitted at Stop.
#
# No-ops silently when:
#   - there is no .ldd/trace.log (no LDD task active in this project)
#   - the launcher `.ldd/ldd_trace` is missing or non-executable
#   - `ldd_trace render` exits non-zero (corrupt trace, etc.)
# A silent no-op is always preferable to emitting a half-rendered block.

set -uo pipefail
export LC_ALL=C

input=$(cat 2>/dev/null || echo "{}")
cwd=$(jq -r '.cwd // .workspace.current_dir // empty' <<<"$input" 2>/dev/null || true)
[[ -z "$cwd" ]] && cwd="$PWD"
session_id=$(jq -r '.session_id // empty' <<<"$input" 2>/dev/null || true)

trace_file="${cwd}/.ldd/trace.log"
launcher="${cwd}/.ldd/ldd_trace"

if [[ ! -f "$trace_file" || ! -x "$launcher" ]]; then
    echo '{}'
    exit 0
fi

# Activity gate + verbosity are enforced inside `ldd_trace render`:
#   - --respect-config  reads .ldd/config.yaml (`display.verbosity`,
#     `display.gate_on_activity`); both have safe defaults if the file is
#     missing ("summary", gate=true).
#   - --activity-gate   is a belt-and-suspenders: even without a config file,
#     the hook refuses to render when LDD was not active in this session.
#   - LDD_HOOK_SESSION_ID is the id we got from the hook input, compared
#     against .ldd/session_active (written by ldd_trace init/append/close).
#   - LDD_VERBOSITY       is a session-level env override (set via /ldd-set)
#     that beats the config file but not an explicit --verbosity flag.
#
# Summary is the rendered default so the user gets a compact 6-line digest
# when LDD is active, and silence on turns where no iteration was recorded.
block=$(LDD_HOOK_SESSION_ID="$session_id" "$launcher" render \
    --project "$cwd" \
    --respect-config \
    --activity-gate \
    --quiet-missing \
    2>/dev/null || true)
if [[ -z "$block" ]]; then
    echo '{}'
    exit 0
fi

# Emit the block as a top-level `systemMessage`. The Claude Code hook API
# rejects `hookSpecificOutput.additionalContext` on Stop/SubagentStop
# events (that field is reserved for UserPromptSubmit / PostToolUse);
# `systemMessage` is the schema-valid channel for turn-boundary text.
# JSON-escape via jq -Rs (read as single string).
jq -Rs --arg prefix $'\n\n' '{systemMessage: ($prefix + .)}' <<<"$block"
