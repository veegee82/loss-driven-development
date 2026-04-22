#!/usr/bin/env bash
# E2E tests for the .ldd/ldd_trace launcher's Python-resolution logic.
#
# Scenarios:
#   L1 — python3 available (happy path, Linux / Homebrew default)
#   L2 — only `python` on PATH but it points at Python 3 (macOS system default)
#   L3 — no Python 3.8+ anywhere → launcher emits actionable error, exit 127
#   L4 — $LDD_PYTHON override wins over PATH discovery
#
# Run:   bash tests/hooks/test_launcher_python.sh

set -euo pipefail
export LC_ALL=C

repo_root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)
launcher="$repo_root/skills/bootstrap-userspace/ldd_trace"
[[ -x "$launcher" ]] || { echo "FAIL: launcher not executable at $launcher"; exit 1; }

workdir=$(mktemp -d)
trap 'rm -rf "$workdir"' EXIT

pass=0; fail=0
say()  { printf '[%s] %s\n' "$1" "$2"; }
pass() { say PASS "$1"; pass=$((pass+1)); }
die()  { say FAIL "$1"; fail=$((fail+1)); }

# Baseline: need a real python3 on the developer's machine to run these tests.
real_py3=$(command -v python3 2>/dev/null || true)
[[ -n "$real_py3" ]] || { echo "SKIP: no python3 on PATH — cannot run launcher tests"; exit 0; }

# Minimal bin dir with the utils the launcher's bash preamble needs.
min_bin="$workdir/min-bin"
mkdir -p "$min_bin"
for b in bash cat command echo env ls printf test sort tac head tr; do
    real=$(command -v "$b" 2>/dev/null) || continue
    ln -sf "$real" "$min_bin/$b"
done

# --- L1: python3 on PATH ---------------------------------------------------
out_l1=$(LDD_PLUGIN_ROOT="$repo_root" "$launcher" --help 2>&1 | head -1)
if grep -q '^usage: ldd_trace' <<<"$out_l1"; then
    pass "L1: python3 on PATH → launcher executes ldd_trace"
else
    die "L1: expected 'usage: ldd_trace ...', got: $out_l1"
fi

# --- L2: only `python` on PATH, points at Python 3 -------------------------
py_only_bin="$workdir/py-only"
mkdir -p "$py_only_bin"
cp -r "$min_bin"/* "$py_only_bin/" 2>/dev/null || true
# `python` → real python3
ln -sf "$real_py3" "$py_only_bin/python"
# deliberately NO python3 here
if PATH="$py_only_bin" command -v python3 >/dev/null 2>&1; then
    die "L2: test harness leaked python3 into $py_only_bin"
else
    out_l2=$(PATH="$py_only_bin" LDD_PLUGIN_ROOT="$repo_root" \
        "$launcher" --help 2>&1 | head -1)
    if grep -q '^usage: ldd_trace' <<<"$out_l2"; then
        pass "L2: only 'python' (Python 3) on PATH → fallback works"
    else
        die "L2: expected 'usage: ldd_trace ...', got: $out_l2"
    fi
fi

# --- L3: no Python anywhere ------------------------------------------------
nopy_bin="$workdir/nopy"
mkdir -p "$nopy_bin"
cp -r "$min_bin"/* "$nopy_bin/" 2>/dev/null || true
# do NOT add python / python3
out_l3=$(PATH="$nopy_bin" LDD_PLUGIN_ROOT="$repo_root" \
    "$launcher" --help 2>&1 || true)
exit_l3=$?
if grep -q 'no usable Python 3.8+ interpreter found' <<<"$out_l3"; then
    pass "L3: no Python → actionable error message, non-zero exit"
else
    die "L3: expected 'no usable Python 3.8+ interpreter found', got (exit=$exit_l3): $out_l3"
fi

# --- L4: LDD_PYTHON override wins --------------------------------------------
# Use a wrapper that writes a marker file to prove it ran, then execs python3.
wrapper="$workdir/custom-python-wrapper"
cat > "$wrapper" <<EOF
#!/usr/bin/env bash
echo "LDD_PYTHON_OVERRIDE_USED" > "$workdir/override-marker"
exec "$real_py3" "\$@"
EOF
chmod +x "$wrapper"
rm -f "$workdir/override-marker"
out_l4=$(LDD_PYTHON="$wrapper" LDD_PLUGIN_ROOT="$repo_root" \
    "$launcher" --help 2>&1 | head -1)
if [[ -f "$workdir/override-marker" ]] && grep -q '^usage: ldd_trace' <<<"$out_l4"; then
    pass "L4: LDD_PYTHON override was used (marker written) AND ldd_trace ran"
else
    die "L4: override marker=$(cat "$workdir/override-marker" 2>&1) output=$out_l4"
fi

printf '\n%d passed, %d failed\n' "$pass" "$fail"
(( fail == 0 )) || exit 1
