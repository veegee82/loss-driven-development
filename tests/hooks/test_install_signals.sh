#!/usr/bin/env bash
# Smoketest for hooks/ldd_install.sh opt-in signal logic.
#
# Covers the three signals introduced alongside the `.ldd/`-at-clone fix:
#   A — pre-existing .ldd/          (historical default)
#   B — plugin self-identification  (this repo IS the plugin)
#   C — user-global auto-opt-in     (LDD_AUTO_OPTIN=1 or ~/.claude/settings.json)
#
# Plus two negative cases:
#   N1 — no signal             → hook must no-op (no .ldd/ created)
#   N2 — wrong plugin.json name → Signal B must NOT fire
#
# The test builds a throwaway `fake-plugin-root` that satisfies the installer's
# template-path existence checks with empty stubs, then exercises the hook in
# six isolated `$cwd` directories.
#
# Run:   bash tests/hooks/test_install_signals.sh

set -euo pipefail
export LC_ALL=C

repo_root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)
hook="$repo_root/hooks/ldd_install.sh"
[[ -x "$hook" ]] || { echo "FAIL: $hook not executable"; exit 1; }

workdir=$(mktemp -d)
trap 'rm -rf "$workdir"' EXIT

# --- Build a minimal fake plugin root with all four template files ----------
fake_plugin="$workdir/fake-plugin-root"
mkdir -p \
    "$fake_plugin/.claude-plugin" \
    "$fake_plugin/skills/bootstrap-userspace" \
    "$fake_plugin/skills/host-statusline"

cat > "$fake_plugin/.claude-plugin/plugin.json" <<'JSON'
{"name":"loss-driven-development","version":"0.13.0"}
JSON

for f in \
    "$fake_plugin/skills/bootstrap-userspace/ldd_trace" \
    "$fake_plugin/skills/host-statusline/statusline.sh" \
    "$fake_plugin/skills/host-statusline/heartbeat.sh" \
    "$fake_plugin/skills/host-statusline/stop_render.sh"
do
    echo '#!/bin/sh' > "$f"
    chmod +x "$f"
done
# config.yaml.default is optional for the installer; include it so the seed path runs.
echo "display:\n  verbosity: summary" > "$fake_plugin/skills/host-statusline/config.yaml.default"

# Fake HOME so Signal C via ~/.claude/settings.json is testable without
# touching the developer's real config.
fake_home="$workdir/fake-home"
mkdir -p "$fake_home/.claude"

pass=0; fail=0
say() { printf '[%s] %s\n' "$1" "$2"; }

# --- Helper -----------------------------------------------------------------
# Runs the hook in a fresh $cwd. Arguments:
#   $1 — scenario name
#   $2 — path to $cwd (must already exist, populated with whatever the scenario needs)
#   $3 — 1 if the hook should create/retain .ldd/, else 0
#   env LDD_AUTO_OPTIN — propagated
#   env HOME           — propagated
run_case() {
    local name="$1" cwd="$2" expect_ldd="$3"
    local out
    out=$(CLAUDE_PLUGIN_ROOT="$fake_plugin" HOME="${HOME_OVERRIDE:-$HOME}" \
          LDD_AUTO_OPTIN="${LDD_AUTO_OPTIN:-}" \
          bash "$hook" <<<"{\"cwd\":\"$cwd\"}" 2>/dev/null || true)
    local have_ldd=0
    [[ -d "$cwd/.ldd" ]] && have_ldd=1
    if (( have_ldd == expect_ldd )); then
        say PASS "$name (expect_ldd=$expect_ldd, got=$have_ldd)"
        pass=$((pass+1))
    else
        say FAIL "$name (expect_ldd=$expect_ldd, got=$have_ldd)"
        say ".... hook-output: $out"
        fail=$((fail+1))
    fi
}

# --- Case A: pre-existing .ldd/ -------------------------------------------
cwd_a="$workdir/case-a"; mkdir -p "$cwd_a/.ldd"
run_case "A: pre-existing .ldd/" "$cwd_a" 1

# --- Case B: plugin self-identification ------------------------------------
cwd_b="$workdir/case-b"; mkdir -p "$cwd_b/.claude-plugin"
cat > "$cwd_b/.claude-plugin/plugin.json" <<'JSON'
{"name":"loss-driven-development","version":"0.13.0"}
JSON
run_case "B: plugin self-id → .ldd/ auto-created" "$cwd_b" 1

# --- Case C1: LDD_AUTO_OPTIN=1 env ----------------------------------------
cwd_c1="$workdir/case-c1"; mkdir -p "$cwd_c1"
LDD_AUTO_OPTIN=1 run_case "C1: LDD_AUTO_OPTIN=1 env → .ldd/ auto-created" "$cwd_c1" 1

# --- Case C2: ~/.claude/settings.json flag --------------------------------
cwd_c2="$workdir/case-c2"; mkdir -p "$cwd_c2"
cat > "$fake_home/.claude/settings.json" <<'JSON'
{"ldd":{"auto_install":true}}
JSON
HOME_OVERRIDE="$fake_home" run_case "C2: ~/.claude/settings.json ldd.auto_install=true → .ldd/ auto-created" "$cwd_c2" 1

# --- Case N1: no signal → no-op ------------------------------------------
cwd_n1="$workdir/case-n1"; mkdir -p "$cwd_n1"
# Make sure ~/.claude/settings.json is absent in the fake home
rm -f "$fake_home/.claude/settings.json"
HOME_OVERRIDE="$fake_home" LDD_AUTO_OPTIN=0 \
    run_case "N1: no signal → hook no-ops, no .ldd/" "$cwd_n1" 0

# --- Case N2: wrong plugin.json name ---------------------------------------
cwd_n2="$workdir/case-n2"; mkdir -p "$cwd_n2/.claude-plugin"
cat > "$cwd_n2/.claude-plugin/plugin.json" <<'JSON'
{"name":"some-other-plugin","version":"1.0.0"}
JSON
HOME_OVERRIDE="$fake_home" LDD_AUTO_OPTIN=0 \
    run_case "N2: plugin.json with different name → Signal B must NOT fire" "$cwd_n2" 0

# --- Case D: idempotency — running hook twice on case A is still .ldd/ -----
run_case "D: idempotent re-run on case A" "$cwd_a" 1

# ---------------------------------------------------------------------------
# Git hooks auto-enable (Signal B — drift-gate for LDD's own dev repo)
# ---------------------------------------------------------------------------
#
# On Signal B (plugin self-identification) AND a `.githooks/` dir in the
# project root, the installer should `git config core.hooksPath .githooks`
# so the pre-commit drift-gate fires without a manual setup step.
#
# Each case below builds a fresh case-b-like project with .claude-plugin +
# a .githooks/ dir, initializes a git repo there, runs the hook, and checks
# the resulting `git config core.hooksPath`.

run_git_case() {
    local name="$1" cwd="$2" expect_path="$3"
    local pre_existing="$4"   # optional: a value to set before running
    # Init a fresh git repo so `git -C $cwd config` can read/write.
    (
        cd "$cwd" \
        && git init --quiet \
        && git config user.email "test@example.com" \
        && git config user.name  "test"
    )
    if [[ -n "$pre_existing" ]]; then
        git -C "$cwd" config --local core.hooksPath "$pre_existing"
    fi
    CLAUDE_PLUGIN_ROOT="$fake_plugin" HOME="${HOME_OVERRIDE:-$HOME}" \
        LDD_AUTO_OPTIN="${LDD_AUTO_OPTIN:-}" \
        bash "$hook" <<<"{\"cwd\":\"$cwd\"}" >/dev/null 2>&1 || true
    local got_path
    got_path=$(git -C "$cwd" config --local --get core.hooksPath 2>/dev/null || echo "")
    if [[ "$got_path" == "$expect_path" ]]; then
        say PASS "$name (core.hooksPath=$got_path)"
        pass=$((pass+1))
    else
        say FAIL "$name (expected core.hooksPath=$expect_path, got='$got_path')"
        fail=$((fail+1))
    fi
}

# Build the .claude-plugin + .githooks/pre-commit stub that Signal B needs.
make_signal_b_repo() {
    local cwd="$1"
    mkdir -p "$cwd/.claude-plugin" "$cwd/.githooks"
    cat > "$cwd/.claude-plugin/plugin.json" <<'JSON'
{"name":"loss-driven-development","version":"0.13.0"}
JSON
    echo '#!/usr/bin/env bash' > "$cwd/.githooks/pre-commit"
    chmod +x "$cwd/.githooks/pre-commit"
}

# --- Case E: Signal B + unset core.hooksPath → auto-set to .githooks -------
cwd_e="$workdir/case-e"; mkdir -p "$cwd_e"; make_signal_b_repo "$cwd_e"
run_git_case "E: Signal B + unset → core.hooksPath=.githooks" "$cwd_e" ".githooks" ""

# --- Case F: Signal B + already .githooks → idempotent, still .githooks ----
cwd_f="$workdir/case-f"; mkdir -p "$cwd_f"; make_signal_b_repo "$cwd_f"
run_git_case "F: Signal B + already .githooks → idempotent" "$cwd_f" ".githooks" ".githooks"

# --- Case G: Signal B + different path → NOT overridden, stays as-is ------
cwd_g="$workdir/case-g"; mkdir -p "$cwd_g"; make_signal_b_repo "$cwd_g"
run_git_case "G: Signal B + user-custom path → not overridden" "$cwd_g" "my/custom/hooks" "my/custom/hooks"

# --- Case H: Signal A only (no Signal B) → core.hooksPath untouched -------
cwd_h="$workdir/case-h"; mkdir -p "$cwd_h/.ldd"
(
    cd "$cwd_h" \
    && git init --quiet \
    && git config user.email "t@e.com" \
    && git config user.name  "t"
)
CLAUDE_PLUGIN_ROOT="$fake_plugin" HOME="${HOME_OVERRIDE:-$HOME}" LDD_AUTO_OPTIN=0 \
    bash "$hook" <<<"{\"cwd\":\"$cwd_h\"}" >/dev/null 2>&1 || true
hooks_path_h=$(git -C "$cwd_h" config --local --get core.hooksPath 2>/dev/null || echo "")
if [[ -z "$hooks_path_h" ]]; then
    say PASS "H: Signal A only → core.hooksPath NOT auto-set (no Signal B)"
    pass=$((pass+1))
else
    say FAIL "H: Signal A only → core.hooksPath unexpectedly set to '$hooks_path_h'"
    fail=$((fail+1))
fi

# --- Summary ---------------------------------------------------------------
printf '\n%d passed, %d failed\n' "$pass" "$fail"
(( fail == 0 )) || exit 1
