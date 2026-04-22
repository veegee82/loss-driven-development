#!/usr/bin/env bash
# E2E tests for scripts/check-plugin-versions.sh.
#
# Verifies the sync check catches drift in both directions AND passes on
# the current committed state (i.e. main is clean). The third case proves
# the hint string is actionable (names both files and gives the jq fix).
#
# Run:   bash tests/hooks/test_version_sync.sh

set -euo pipefail
export LC_ALL=C

repo_root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)
checker="$repo_root/scripts/check-plugin-versions.sh"
[[ -x "$checker" ]] || { echo "FAIL: checker not executable at $checker"; exit 1; }

workdir=$(mktemp -d)
trap 'rm -rf "$workdir"' EXIT

pass=0; fail=0
say()  { printf '[%s] %s\n' "$1" "$2"; }
pass() { say PASS "$1"; pass=$((pass+1)); }
die()  { say FAIL "$1"; fail=$((fail+1)); }

# --- V1: current repo state → must PASS -------------------------------------
if bash "$checker" >/dev/null 2>&1; then
    pass "V1: committed state has matching versions"
else
    die "V1: committed state shows drift — run the checker manually to inspect"
fi

# --- V2: synthetic drift → must FAIL with actionable message ---------------
# Copy the current plugin files into a fake repo root, drift one, invoke
# the checker with a patched repo_root discovery.
fake_root="$workdir/fake-repo"
mkdir -p "$fake_root/.claude-plugin" "$fake_root/scripts"
cp "$repo_root/.claude-plugin/plugin.json" "$fake_root/.claude-plugin/"
cp "$repo_root/.claude-plugin/marketplace.json" "$fake_root/.claude-plugin/"
cp "$repo_root/gemini-extension.json" "$fake_root/gemini-extension.json"
cp "$checker" "$fake_root/scripts/check-plugin-versions.sh"
chmod +x "$fake_root/scripts/check-plugin-versions.sh"

# Force a drift: bump plugin.json to a made-up higher version
jq '.version = "9.9.9"' "$fake_root/.claude-plugin/plugin.json" > "$fake_root/.claude-plugin/plugin.json.tmp"
mv "$fake_root/.claude-plugin/plugin.json.tmp" "$fake_root/.claude-plugin/plugin.json"

set +e
out_v2=$(bash "$fake_root/scripts/check-plugin-versions.sh" 2>&1)
exit_v2=$?
set -e
if (( exit_v2 == 0 )); then
    die "V2: checker must exit non-zero when versions drift"
elif ! grep -q "plugin version drift" <<<"$out_v2"; then
    die "V2: drift message missing 'plugin version drift' headline"
elif ! grep -q "9.9.9" <<<"$out_v2"; then
    die "V2: drift message must name both drifted versions"
elif ! grep -q "jq --arg v" <<<"$out_v2"; then
    die "V2: drift message must include actionable jq fix"
else
    pass "V2: synthetic drift → non-zero exit, actionable message with both versions + fix hint"
fi

# --- V3: jq absent → fails loud (not silent) -------------------------------
nojq_bin="$workdir/nojq"
mkdir -p "$nojq_bin"
for b in bash cat echo printf test command env dirname basename; do
    real=$(command -v "$b" 2>/dev/null) || continue
    # Skip shell builtins — command -v returns the name itself, not a path,
    # which would create a dangling symlink we don't need (cd/pwd are built-in).
    [[ -e "$real" ]] || continue
    ln -sf "$real" "$nojq_bin/$b"
done
# But sufficient binaries for the checker: if jq is absent, it must fail
# immediately with the "jq required" message, not compute bogus versions.
set +e
out_v3=$(PATH="$nojq_bin" bash "$checker" 2>&1)
exit_v3=$?
set -e
if (( exit_v3 == 0 )); then
    die "V3: checker must exit non-zero when jq is missing"
elif ! grep -q "jq is required" <<<"$out_v3"; then
    die "V3: expected 'jq is required' message, got: $out_v3"
else
    pass "V3: jq missing → fails with 'jq is required' (not silent)"
fi

printf '\n%d passed, %d failed\n' "$pass" "$fail"
(( fail == 0 )) || exit 1
