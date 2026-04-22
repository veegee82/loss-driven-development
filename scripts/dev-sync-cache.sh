#!/usr/bin/env bash
# dev-sync-cache.sh — mirror the working repo into the Claude Code plugin
# cache so hooks/skills/scripts edited here take effect in the NEXT session
# (plus any Python-module change takes effect immediately, since the launcher
# resolves $PYTHONPATH through the cache).
#
# This is a development convenience; users installing via the marketplace get
# the cache refreshed by Claude Code itself. Running this repeatedly is safe
# (idempotent rsync).

set -euo pipefail

repo="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cache_base="$HOME/.claude/plugins/cache/loss-driven-development/loss-driven-development"
version=$(jq -r '.version' "$repo/.claude-plugin/plugin.json")
cache="$cache_base/$version"

if [[ ! -d "$cache" ]]; then
    echo "No cache directory at $cache — is the plugin installed?" >&2
    exit 1
fi

# Mirror only plugin-relevant paths. Anything user-specific (.ldd/, .git,
# .idea, pytest/hypothesis caches, virtualenvs) stays in the repo.
for sub in hooks skills commands scripts .claude-plugin .github .githooks \
           AGENTS.md CHANGELOG.md CONTRIBUTING.md GAPS.md GEMINI.md LICENSE \
           PRIVACY.md README.md SECURITY.md SUBMISSION.md evaluation.md \
           gemini-extension.json docs diagrams dist tests
do
    if [[ -e "$repo/$sub" ]]; then
        rsync -a --delete \
            --exclude='__pycache__' --exclude='*.pyc' --exclude='.pytest_cache' \
            --exclude='.hypothesis' \
            "$repo/$sub" "$cache/"
    fi
done

printf 'plugin cache synced (v%s) → %s\n' "$version" "$cache"
