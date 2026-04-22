#!/usr/bin/env bash
# Verify that all three plugin manifests agree on the plugin version:
#   - .claude-plugin/plugin.json      (Claude Code — source of truth; read
#                                      by the SessionStart install hook)
#   - .claude-plugin/marketplace.json (Claude Code /plugin install UI)
#   - gemini-extension.json           (Gemini CLI extension registration)
#
# A drift between any of these means users on at least one host see one
# version while actually installing another. v0.13.x caught a silent drift
# where gemini-extension.json stayed at 0.11.0 while the other two bumped
# through 0.12.0 and 0.13.0 — this check exists so that never reoccurs.
#
# Runs:
#   - locally via .githooks/pre-commit when any manifest is staged
#   - in CI via .github/workflows/install-hooks-check.yml
#
# Exits 0 on match across all three, 1 on drift (with an actionable fix hint).

set -euo pipefail

repo_root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
plugin_json="$repo_root/.claude-plugin/plugin.json"
marketplace_json="$repo_root/.claude-plugin/marketplace.json"
gemini_json="$repo_root/gemini-extension.json"

for f in "$plugin_json" "$marketplace_json" "$gemini_json"; do
    [[ -f "$f" ]] || { echo "FAIL: missing $f" >&2; exit 1; }
done

if ! command -v jq >/dev/null 2>&1; then
    echo "FAIL: jq is required for this check but was not found on PATH." >&2
    exit 1
fi

plugin_ver=$(jq -r '.version' "$plugin_json")
market_ver=$(jq -r '.plugins[] | select(.name == "loss-driven-development") | .version' "$marketplace_json")
gemini_ver=$(jq -r '.version' "$gemini_json")

for pair in "plugin_json:$plugin_ver" "marketplace_json:$market_ver" "gemini_json:$gemini_ver"; do
    name="${pair%%:*}"
    val="${pair##*:}"
    if [[ -z "$val" || "$val" == "null" ]]; then
        echo "FAIL: could not read version from $name" >&2
        exit 1
    fi
done

if [[ "$plugin_ver" != "$market_ver" || "$plugin_ver" != "$gemini_ver" ]]; then
    cat >&2 <<EOF
FAIL: plugin version drift.

    .claude-plugin/plugin.json       : $plugin_ver   (source of truth)
    .claude-plugin/marketplace.json  : $market_ver
    gemini-extension.json            : $gemini_ver

The SessionStart install hook reads plugin.json; Claude Code's /plugin
install UI reads marketplace.json; Gemini CLI reads gemini-extension.json.
Drift on any of them means users on that host see one version while
installing another.

Fix by syncing both marketplace.json and gemini-extension.json to
plugin.json:

    ver=\$(jq -r '.version' .claude-plugin/plugin.json)
    jq --arg v "\$ver" \\
       '(.plugins[] | select(.name == "loss-driven-development") | .version) |= \$v' \\
       .claude-plugin/marketplace.json > .claude-plugin/marketplace.json.tmp \\
        && mv .claude-plugin/marketplace.json.tmp .claude-plugin/marketplace.json
    jq --arg v "\$ver" '.version = \$v' \\
       gemini-extension.json > gemini-extension.json.tmp \\
        && mv gemini-extension.json.tmp gemini-extension.json

Then stage and re-commit.
EOF
    exit 1
fi

echo "OK: plugin version in sync across all three manifests ($plugin_ver)"
