#!/usr/bin/env bash
# evolve-skill.sh — RED/GREEN rerun helper for the method-evolution skill.
#
# Platform note: this script is agent-agnostic in what it produces (plain
# prompts on stdout, plain responses on stdin) but assumes YOU have access to
# a subagent / session you can paste prompts into. It works with any coding
# agent that supports a fresh conversational session: Claude Code, Codex,
# Gemini CLI, a bare Anthropic/OpenAI API playground, etc.
#
# Usage:
#   ./scripts/evolve-skill.sh <skill-name>
#
# What it does:
#   1. Prints the RED prompt (baseline: skill NOT loaded) from the fixture's
#      scenario.md — for you to paste into a fresh session.
#   2. Waits for you to paste the response, saves it as red.md.
#   3. Prints the GREEN prompt (skill loaded) — the skill's SKILL.md prepended
#      to the same scenario.md.
#   4. Waits for you to paste the response, saves it as green.md.
#   5. Prints instructions for scoring against rubric.md. Scoring is
#      reviewer-done — the script does NOT call an LLM API.
#
# Requirements: bash, nothing else. No Python, no API key.
set -euo pipefail

if [[ $# -ne 1 ]]; then
    echo "usage: $0 <skill-name>"
    echo "  example: $0 root-cause-by-layer"
    exit 2
fi

SKILL="$1"
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SKILL_FILE="$REPO_ROOT/skills/$SKILL/SKILL.md"
FIXTURE_DIR="$REPO_ROOT/tests/fixtures/$SKILL"
SCENARIO="$FIXTURE_DIR/scenario.md"
RUBRIC="$FIXTURE_DIR/rubric.md"

if [[ ! -f "$SKILL_FILE" ]]; then
    echo "error: skill not found: $SKILL_FILE"
    exit 2
fi
if [[ ! -f "$SCENARIO" ]]; then
    echo "error: fixture scenario not found: $SCENARIO"
    exit 2
fi
if [[ ! -f "$RUBRIC" ]]; then
    echo "error: fixture rubric not found: $RUBRIC"
    exit 2
fi

RUN_DIR="$FIXTURE_DIR/runs/$(date -u +%Y%m%dT%H%M%SZ)"
mkdir -p "$RUN_DIR"

cat <<EOF
===================================================================
 method-evolution helper — RED/GREEN for skill: $SKILL
===================================================================

Run directory: $RUN_DIR
Skill file:    $SKILL_FILE
Scenario:      $SCENARIO
Rubric:        $RUBRIC

STEP 1 / RED (baseline, NO skill).
Open a fresh subagent. Paste the contents of $SCENARIO verbatim.
When you have the response, paste it below, then Ctrl-D.
-------------------------------------------------------------------
EOF

cat "$SCENARIO"
echo
echo "--- paste RED response below (Ctrl-D when done) ---"
cat > "$RUN_DIR/red.md"

cat <<EOF

===================================================================
STEP 2 / GREEN (with skill loaded).
Open a fresh subagent. Paste the following (skill + scenario).
-------------------------------------------------------------------
EOF

cat "$SKILL_FILE"
echo
echo '---'
echo
cat "$SCENARIO"
echo
echo "--- paste GREEN response below (Ctrl-D when done) ---"
cat > "$RUN_DIR/green.md"

cat <<EOF

===================================================================
STEP 3 / Score.
Read $RUN_DIR/red.md and $RUN_DIR/green.md against the rubric at
$RUBRIC. Count violations (0 = satisfied, 1 = violated) per side.
Record the score in $RUN_DIR/score.md using this shape:

    # Score — $SKILL — \$(date -u +%Y-%m-%d)
    Baseline violations (RED):   X / N
    With-skill violations (GREEN): Y / N
    Δloss = X − Y = Z

If Δloss ≤ 0 for the motivating case, the skill did not help on this
scenario. Investigate before committing a method-evolution step.

Artifacts: $RUN_DIR/
===================================================================
EOF
