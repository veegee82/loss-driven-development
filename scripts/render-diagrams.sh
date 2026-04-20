#!/usr/bin/env bash
# render-diagrams.sh — regenerate all SVGs from .dot sources.
#
# Usage:
#   ./scripts/render-diagrams.sh
#
# Renders every diagrams/*.dot into diagrams/*.svg via graphviz.
# Skips feDropShadow-producing output by design (dot default is fine).
set -euo pipefail

if ! command -v dot >/dev/null 2>&1; then
    echo "error: 'dot' (graphviz) not found in PATH"
    echo "install: brew install graphviz | apt install graphviz | conda install graphviz"
    exit 2
fi

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT/diagrams"

rendered=0
for f in *.dot; do
    [[ -e "$f" ]] || continue
    out="${f%.dot}.svg"
    dot -Tsvg "$f" -o "$out"
    echo "rendered: $out"
    rendered=$((rendered + 1))
done

if grep -l "feDropShadow" *.svg 2>/dev/null; then
    echo "warning: feDropShadow detected — GitHub's SVG sanitizer will strip it"
    exit 1
fi

echo "done: $rendered diagram(s) rendered"
