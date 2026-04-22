#!/usr/bin/env bash
# E2E tests for hooks/ldd_install.sh preflight checks and failure modes.
#
# These complement test_install_signals.sh (which focuses on opt-in signals)
# by exercising the defensive paths that used to fail silently in pre-v0.13.1:
#
#   P1 — jq missing on PATH   → graceful abort via additionalContext; no marker
#   P2 — fresh install path   → artifacts land; marker == plugin version;
#                               reload message is prominent
#   P3 — update path          → reload message is subdued (hooks already live)
#   P4 — merge respects user  → pre-existing statusLine is NOT clobbered
#   P5 — jq rescue            → install succeeds on next run once jq is back
#
# Run:   bash tests/hooks/test_install_preflight.sh

set -euo pipefail
export LC_ALL=C

repo_root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)
hook="$repo_root/hooks/ldd_install.sh"
[[ -x "$hook" ]] || { echo "FAIL: $hook not executable"; exit 1; }

workdir=$(mktemp -d)
trap 'rm -rf "$workdir"' EXIT

# Build a clean PATH dir with all the core utils the installer + jq-preflight
# need, minus jq itself. Used to simulate jq-missing reliably.
nojq_bin="$workdir/nojq-bin"
mkdir -p "$nojq_bin"
for b in bash cat cp mv mkdir chmod rm ls mktemp awk sed grep tr tac sort cmp printf test env head tail wc dirname basename sh true false command; do
    real=$(command -v "$b" 2>/dev/null) || continue
    ln -sf "$real" "$nojq_bin/$b"
done
# Sanity: jq must be absent.
if PATH="$nojq_bin" command -v jq >/dev/null 2>&1; then
    echo "FAIL: test harness leaked jq into $nojq_bin"; exit 1
fi

pass=0; fail=0
say()  { printf '[%s] %s\n' "$1" "$2"; }
pass() { say PASS "$1"; pass=$((pass+1)); }
die()  { say FAIL "$1"; fail=$((fail+1)); }

# --- P1: jq missing → graceful abort -----------------------------------------
cwd_p1="$workdir/p1"; mkdir -p "$cwd_p1/.ldd"
out_p1=$(PATH="$nojq_bin" env CLAUDE_PLUGIN_ROOT="$repo_root" LDD_FORCE_INSTALL=1 \
    bash "$hook" <<<"{\"cwd\":\"$cwd_p1\"}" 2>&1)
exit_p1=$?
if (( exit_p1 != 0 )); then
    die "P1: installer must exit 0 when jq is missing (got $exit_p1) so SessionStart continues"
elif ! grep -q "jq.*required.*not found" <<<"$out_p1"; then
    die "P1: expected additionalContext to mention 'jq required / not found', got: $out_p1"
elif [[ -f "$cwd_p1/.ldd/.install_version" ]]; then
    die "P1: marker .ldd/.install_version must NOT be written when install aborted"
elif [[ -f "$cwd_p1/.claude/settings.local.json" ]]; then
    die "P1: .claude/settings.local.json must NOT be created when install aborted"
else
    pass "P1: jq missing → graceful abort with visible message, no marker, no settings"
fi

# --- P2: fresh install → artifacts + prominent reload message ----------------
cwd_p2="$workdir/p2"; mkdir -p "$cwd_p2/.ldd"
out_p2=$(CLAUDE_PLUGIN_ROOT="$repo_root" LDD_FORCE_INSTALL=1 \
    bash "$hook" <<<"{\"cwd\":\"$cwd_p2\"}" 2>&1)
ok=1
for f in .ldd/ldd_trace .ldd/statusline.sh .ldd/.install_version \
         .claude/hooks/ldd_heartbeat.sh .claude/hooks/ldd_stop_render.sh \
         .claude/settings.local.json; do
    [[ -f "$cwd_p2/$f" ]] || { die "P2: missing artifact $f"; ok=0; break; }
done
if (( ok == 1 )); then
    marker=$(tr -d '[:space:]' < "$cwd_p2/.ldd/.install_version")
    plugin_ver=$(jq -r '.version' "$repo_root/.claude-plugin/plugin.json")
    if [[ "$marker" != "$plugin_ver" ]]; then
        die "P2: marker '$marker' != plugin_version '$plugin_ver'"
    elif ! grep -q "Please reload" <<<"$out_p2"; then
        die "P2: fresh-install message must prominently ask for reload; got: $out_p2"
    elif ! jq -e '.hooks.PreToolUse | length >= 1' "$cwd_p2/.claude/settings.local.json" >/dev/null; then
        die "P2: PreToolUse hook not registered in settings.local.json"
    elif ! jq -e '.hooks.Stop | length >= 1' "$cwd_p2/.claude/settings.local.json" >/dev/null; then
        die "P2: Stop hook not registered in settings.local.json"
    else
        pass "P2: fresh install → all artifacts + marker + prominent reload message"
    fi
fi

# --- P3: update (marker exists) → subdued reload message --------------------
# Fake an older marker; re-run the installer; expect update path.
echo "0.0.1" > "$cwd_p2/.ldd/.install_version"
out_p3=$(CLAUDE_PLUGIN_ROOT="$repo_root" LDD_FORCE_INSTALL=1 \
    bash "$hook" <<<"{\"cwd\":\"$cwd_p2\"}" 2>&1)
if grep -q "Please reload" <<<"$out_p3"; then
    die "P3: update path should NOT emit the prominent reload message; got: $out_p3"
elif ! grep -q "updated (0.0.1" <<<"$out_p3"; then
    die "P3: update message must name the old→new version arrow; got: $out_p3"
else
    pass "P3: update → subdued reload message + version-arrow present"
fi

# --- P4: merge respects pre-existing user statusLine + hooks ----------------
cwd_p4="$workdir/p4"; mkdir -p "$cwd_p4/.ldd" "$cwd_p4/.claude"
cat > "$cwd_p4/.claude/settings.local.json" <<'JSON'
{
  "statusLine": {"type": "command", "command": "~/my-custom-statusline.sh"},
  "hooks": {
    "PreToolUse": [
      {"matcher": "Bash",
       "hooks": [{"type": "command", "command": "my-own-logger.sh", "timeout": 3}]}
    ]
  }
}
JSON
CLAUDE_PLUGIN_ROOT="$repo_root" LDD_FORCE_INSTALL=1 \
    bash "$hook" <<<"{\"cwd\":\"$cwd_p4\"}" >/dev/null 2>&1
user_sl=$(jq -r '.statusLine.command' "$cwd_p4/.claude/settings.local.json")
user_pre=$(jq -r '.hooks.PreToolUse[] | select(.matcher == "Bash") | .hooks[0].command' \
    "$cwd_p4/.claude/settings.local.json")
ldd_pre=$(jq -r '.hooks.PreToolUse[] | .hooks[] | select(.command | endswith("ldd_heartbeat.sh")) | .command' \
    "$cwd_p4/.claude/settings.local.json")
if [[ "$user_sl" != "~/my-custom-statusline.sh" ]]; then
    die "P4: user statusLine was clobbered (now: '$user_sl')"
elif [[ "$user_pre" != "my-own-logger.sh" ]]; then
    die "P4: user's PreToolUse hook was lost (now: '$user_pre')"
elif [[ -z "$ldd_pre" ]]; then
    die "P4: LDD heartbeat hook not added alongside user's hook"
else
    pass "P4: merge preserved user statusLine + user hook, added LDD heartbeat alongside"
fi

# --- P5: jq rescue — install retries automatically on next run --------------
# After P1, .ldd/ has no marker. If we re-run WITH jq on PATH, install should
# succeed on this retry (proving the "no marker written" invariant).
out_p5=$(CLAUDE_PLUGIN_ROOT="$repo_root" LDD_FORCE_INSTALL=1 \
    bash "$hook" <<<"{\"cwd\":\"$cwd_p1\"}" 2>&1)
if [[ ! -f "$cwd_p1/.ldd/.install_version" ]]; then
    die "P5: jq-rescue retry failed to install; got: $out_p5"
elif ! grep -q "installed (fresh)" <<<"$out_p5"; then
    die "P5: jq-rescue retry should run fresh-install path; got: $out_p5"
else
    pass "P5: jq-rescue — install succeeded on next run once jq was available"
fi

# --- Summary ---------------------------------------------------------------
printf '\n%d passed, %d failed\n' "$pass" "$fail"
(( fail == 0 )) || exit 1
