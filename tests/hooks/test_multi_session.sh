#!/usr/bin/env bash
# E2E: multi-session ("multi-clauding") race + isolation tests.
#
# A user may run two or more Claude Code sessions simultaneously in the same
# project (two terminals, CLI + IDE, etc.). Each session has its own
# session_id and fires its own hooks. This suite asserts that session state
# stays isolated where it must and shared where it should.
#
# Scenarios:
#   M1 — parallel installers on the same project: settings.local.json stays
#        single-copy (no duplicated LDD hook entries).
#   M2 — parallel heartbeats from session A and B: both session_ids are
#        observable; neither is overwritten by the other.
#   M3 — parallel `ldd_trace init` from A and B: both become gate-active
#        simultaneously (per-session marker, not singular).
#   M4 — statusline renders PER SESSION: A sees A's task, B sees B's task;
#        neither falls back to 'standby' due to the other's session_id
#        winning a singular marker slot.
#   M5 — concurrent `ldd_trace append` from A and B: no trace.log line
#        corruption (atomic appends under flock).
#
# Run:   bash tests/hooks/test_multi_session.sh

set -uo pipefail
export LC_ALL=C

repo_root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)
hook="$repo_root/hooks/ldd_install.sh"
launcher_src="$repo_root/skills/bootstrap-userspace/ldd_trace"
heartbeat_src="$repo_root/skills/host-statusline/heartbeat.sh"
statusline_src="$repo_root/skills/host-statusline/statusline.sh"
[[ -x "$hook" && -x "$launcher_src" ]] || { echo "FAIL: missing installer or launcher"; exit 1; }

workdir=$(mktemp -d)
trap 'rm -rf "$workdir"' EXIT

SID_A="aaaaaaaa-0000-0000-0000-sessionA00000"
SID_B="bbbbbbbb-0000-0000-0000-sessionB00000"

pass=0; fail=0
say()  { printf '[%s] %s\n' "$1" "$2"; }
pass() { say PASS "$1"; pass=$((pass+1)); }
die()  { say FAIL "$1"; fail=$((fail+1)); }

# Bootstrap the project with a fresh install (single-session init, then we
# simulate the second session joining).
proj="$workdir/proj"
mkdir -p "$proj/.ldd"
CLAUDE_PLUGIN_ROOT="$repo_root" LDD_FORCE_INSTALL=1 \
    bash "$hook" <<<"{\"cwd\":\"$proj\",\"session_id\":\"$SID_A\"}" >/dev/null 2>&1

# --- M1: parallel installers don't duplicate settings entries ---------------
# Same project, two Claude Code sessions starting simultaneously. The hook
# runs once per session. After both: exactly 1 LDD PreToolUse + 1 LDD Stop
# entry (idempotency must survive concurrency).
(CLAUDE_PLUGIN_ROOT="$repo_root" bash "$hook" \
    <<<"{\"cwd\":\"$proj\",\"session_id\":\"$SID_A\"}" >/dev/null 2>&1) &
(CLAUDE_PLUGIN_ROOT="$repo_root" bash "$hook" \
    <<<"{\"cwd\":\"$proj\",\"session_id\":\"$SID_B\"}" >/dev/null 2>&1) &
wait
pre_count=$(jq -r '[.hooks.PreToolUse[]? | .hooks[]? | select(.command | endswith("ldd_heartbeat.sh"))] | length' \
    "$proj/.claude/settings.local.json")
stop_count=$(jq -r '[.hooks.Stop[]? | .hooks[]? | select(.command | endswith("ldd_stop_render.sh"))] | length' \
    "$proj/.claude/settings.local.json")
if [[ "$pre_count" == "1" && "$stop_count" == "1" ]]; then
    pass "M1: parallel installers → settings stays single-copy (1 PreToolUse, 1 Stop)"
else
    die "M1: settings duplicated after parallel install (PreToolUse=$pre_count, Stop=$stop_count)"
fi

# --- M2: parallel heartbeats from both sessions remain observable ----------
# The heartbeat hook must record EACH session's activity in isolation.
# Post-refactor: .ldd/heartbeats/<sid> per session. Legacy: .ldd/heartbeat
# (singular, last-writer-wins) — a failure mode this test is designed to
# expose.
HB="$proj/.claude/hooks/ldd_heartbeat.sh"
(echo "{\"session_id\":\"$SID_A\",\"tool_name\":\"Bash\",\"cwd\":\"$proj\"}" | bash "$HB") &
(echo "{\"session_id\":\"$SID_B\",\"tool_name\":\"Read\",\"cwd\":\"$proj\"}" | bash "$HB") &
wait
# Pass if per-session heartbeat files exist with the correct session_id each.
if [[ -d "$proj/.ldd/heartbeats" ]] \
   && grep -q "$SID_A" "$proj/.ldd/heartbeats/$SID_A" 2>/dev/null \
   && grep -q "$SID_B" "$proj/.ldd/heartbeats/$SID_B" 2>/dev/null; then
    pass "M2: per-session heartbeats — both sessions tracked independently"
else
    die "M2: heartbeat tracking is singular. \
.ldd/heartbeats/<sid> is missing — sessions overwrite each other."
fi

# --- M3: both sessions can become gate-active simultaneously ---------------
# After ldd_trace init from both, each session's marker file must exist.
# With a singular .ldd/session_active the second init wins and the first
# gets booted.
(CLAUDE_SESSION_ID="$SID_A" "$proj/.ldd/ldd_trace" init --project "$proj" \
    --task "taskA-feature" --loops inner >/dev/null 2>&1
 CLAUDE_SESSION_ID="$SID_A" "$proj/.ldd/ldd_trace" append --project "$proj" \
    --loop inner --auto-k --skill testharness --action "A-setup" \
    --loss-norm 0.5 --raw "4/8" >/dev/null 2>&1) &
(CLAUDE_SESSION_ID="$SID_B" "$proj/.ldd/ldd_trace" init --project "$proj" \
    --task "taskB-bugfix" --loops inner >/dev/null 2>&1
 CLAUDE_SESSION_ID="$SID_B" "$proj/.ldd/ldd_trace" append --project "$proj" \
    --loop inner --auto-k --skill testharness --action "B-setup" \
    --loss-norm 0.3 --raw "2/8" >/dev/null 2>&1) &
wait
if [[ -f "$proj/.ldd/sessions/$SID_A" && -f "$proj/.ldd/sessions/$SID_B" ]]; then
    pass "M3: both sessions have per-session markers (gate-active concurrently)"
else
    die "M3: .ldd/sessions/<sid> missing for one or both; singular marker wins"
fi

# --- M4: statusline renders the correct session's task -----------------
# A's render must show taskA, B's must show taskB. Neither may collapse to
# 'standby' due to the other winning a singular marker.
out_a=$(bash "$proj/.ldd/statusline.sh" \
    <<<"{\"session_id\":\"$SID_A\",\"workspace\":{\"current_dir\":\"$proj\"}}")
out_b=$(bash "$proj/.ldd/statusline.sh" \
    <<<"{\"session_id\":\"$SID_B\",\"workspace\":{\"current_dir\":\"$proj\"}}")
a_ok=0; b_ok=0
grep -q "taskA-feature" <<<"$out_a" && a_ok=1
grep -q "taskB-bugfix"  <<<"$out_b" && b_ok=1
grep -q "standby\|idle" <<<"$out_a" && a_ok=0
grep -q "standby\|idle" <<<"$out_b" && b_ok=0
if (( a_ok == 1 && b_ok == 1 )); then
    pass "M4: both statuslines render own task (A→taskA, B→taskB)"
else
    die "M4: per-session rendering broken. A: $out_a | B: $out_b"
fi

# --- M5: concurrent append doesn't corrupt trace.log -----------------------
# Launch N parallel appends from each session. Each append writes one
# iteration line. After all jobs exit: every expected line must be present
# and no line may be malformed (mangled prefix / merged records).
N=10
for i in $(seq 1 "$N"); do
    (CLAUDE_SESSION_ID="$SID_A" "$proj/.ldd/ldd_trace" append \
        --project "$proj" --loop inner --auto-k \
        --skill testharness --action "A-iter-$i" \
        --loss-norm 0.1 --raw "$i/10" >/dev/null 2>&1) &
    (CLAUDE_SESSION_ID="$SID_B" "$proj/.ldd/ldd_trace" append \
        --project "$proj" --loop inner --auto-k \
        --skill testharness --action "B-iter-$i" \
        --loss-norm 0.2 --raw "$i/10" >/dev/null 2>&1) &
done
wait
malformed=$(grep -cvE '^(#|$|[0-9]{4}-)' "$proj/.ldd/trace.log" || true)
a_lines=$(grep -c "A-iter-" "$proj/.ldd/trace.log" || true)
b_lines=$(grep -c "B-iter-" "$proj/.ldd/trace.log" || true)
# A-iter-1..N and B-iter-1..N may individually be deduped by the store, but
# NO line should be corrupted. This test focuses on corruption, not count.
if (( malformed == 0 )) && (( a_lines >= 1 )) && (( b_lines >= 1 )); then
    pass "M5: $((N*2)) concurrent appends — no malformed lines (A=$a_lines, B=$b_lines)"
else
    die "M5: trace.log has $malformed malformed line(s); A=$a_lines B=$b_lines"
fi

# --- M6: heartbeat seeds the session-gate marker ---------------------------
# Before v0.13.2 the session marker was written only by `ldd_trace init`,
# leaving a session that used LDD via chat content (skill invocations, inline
# trace blocks) without a `.ldd/sessions/<sid>` entry — the statusline then
# rendered `standby` despite obvious activity. v3 heartbeat hook seeds the
# marker on the first tool fire. Idempotent: a pre-existing marker that
# carries a `task=` line (from `ldd_trace init`) must NOT be overwritten.
proj6="$workdir/proj6"
mkdir -p "$proj6/.ldd"
HB6="$repo_root/skills/host-statusline/heartbeat.sh"
SID_C="cccccccc-0000-0000-0000-sessionC00000"

# Case 1: fresh session, no prior marker — heartbeat must seed it.
rm -rf "$proj6/.ldd/sessions" "$proj6/.ldd/session_active"
echo "{\"session_id\":\"$SID_C\",\"tool_name\":\"Bash\",\"cwd\":\"$proj6\"}" | bash "$HB6"
if [[ -f "$proj6/.ldd/sessions/$SID_C" ]] \
   && grep -q "^session_id=$SID_C$" "$proj6/.ldd/sessions/$SID_C" \
   && ! grep -q '^task=' "$proj6/.ldd/sessions/$SID_C"; then
    pass "M6a: heartbeat seeds minimal session marker (no task= line) when absent"
else
    die "M6a: heartbeat failed to seed session marker for $SID_C"
fi

# Case 2: marker already has a task= line (placed by prior ldd_trace init).
# Heartbeat must NOT overwrite it — the richer task pointer wins.
rm -f "$proj6/.ldd/sessions/$SID_C"
printf 'session_id=%s\ntask=preserved-task-title\n' "$SID_C" > "$proj6/.ldd/sessions/$SID_C"
echo "{\"session_id\":\"$SID_C\",\"tool_name\":\"Read\",\"cwd\":\"$proj6\"}" | bash "$HB6"
if grep -q '^task=preserved-task-title$' "$proj6/.ldd/sessions/$SID_C"; then
    pass "M6b: heartbeat preserves existing task= line (idempotent seed)"
else
    die "M6b: heartbeat clobbered the task= line written by ldd_trace init"
fi

# Case 3: legacy singular marker is ALSO seeded when absent (for legacy readers).
rm -f "$proj6/.ldd/session_active"
rm -rf "$proj6/.ldd/sessions"
echo "{\"session_id\":\"$SID_C\",\"tool_name\":\"Bash\",\"cwd\":\"$proj6\"}" | bash "$HB6"
if [[ -f "$proj6/.ldd/session_active" ]] \
   && grep -q "^session_id=$SID_C$" "$proj6/.ldd/session_active"; then
    pass "M6c: legacy singular marker seeded alongside per-session marker"
else
    die "M6c: legacy .ldd/session_active not seeded"
fi

printf '\n%d passed, %d failed\n' "$pass" "$fail"
(( fail == 0 )) || exit 1
