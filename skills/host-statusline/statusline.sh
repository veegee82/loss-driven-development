#!/usr/bin/env bash
# LDD_STATUSLINE_v1 — auto-installed by the LDD host-statusline skill.
# Renders a single-line permanent LDD status: task · loop · loss · sparkline.
# Reads .ldd/trace.log (Tier 0) or falls back to current session JSONL
# grepped for ⟪LDD-TRACE-v1⟫ markers (Tier 2).
#
# Do not edit in place — the skill detects this marker and reinstalls.
# Customise the single project's statusline by overriding .ldd/statusline.sh
# AND removing the marker line, so the skill leaves your copy alone.

set -uo pipefail
export LC_ALL=C  # force '.' as decimal separator for awk + printf

BLOCKS=('▁' '▂' '▃' '▄' '▅' '▆' '▇' '█')

input=$(cat)
cwd=$(jq -r '.cwd // .workspace.current_dir // "."' <<<"$input" 2>/dev/null || echo ".")
transcript=$(jq -r '.transcript_path // empty' <<<"$input" 2>/dev/null || echo "")

trace_file="${cwd}/.ldd/trace.log"
task=""; loop=""; last_k=""; losses=""; source_tag=""

if [[ -f "$trace_file" ]]; then
    task=$(grep -m1 -oP 'task="\K[^"]+' "$trace_file" 2>/dev/null || true)
    losses=$(grep -oE 'loss_norm=[0-9.]+' "$trace_file" 2>/dev/null | sed 's/loss_norm=//' | tail -30)
    last_line=$(grep -E '^\S+[[:space:]]+(architect|inner|refine|outer|cot)[[:space:]]+k=' "$trace_file" 2>/dev/null | tail -1)
    loop=$(awk '{print $2}' <<<"$last_line")
    last_k=$(grep -oP 'k=\K[0-9]+' <<<"$last_line" | head -1)
    source_tag=".ldd"
elif [[ -n "$transcript" && -f "$transcript" ]]; then
    markers=$(jq -r 'select(.type=="assistant") | (.message.content[]?.text // empty)' "$transcript" 2>/dev/null \
        | grep '⟪LDD-TRACE-v1⟫' || true)
    if [[ -n "$markers" ]]; then
        task=$(grep -oP 'task="\K[^"]+' <<<"$markers" | head -1)
        losses=$(grep -oP 'loss_norm=\K[0-9.]+' <<<"$markers" | tail -30)
        last_line=$(tail -1 <<<"$markers")
        loop=$(grep -oE '(architect|inner|refine|outer|cot)' <<<"$last_line" | head -1)
        last_k=$(grep -oP 'k=\K[0-9]+' <<<"$last_line" | head -1)
        source_tag="jsonl"
    fi
fi

if [[ -z "$losses" ]]; then
    # No LDD trace yet — still show heartbeat if something just fired.
    idle_hb=""
    hb_file="${cwd}/.ldd/heartbeat"
    if [[ -f "$hb_file" ]]; then
        hb_line=$(cat "$hb_file" 2>/dev/null || echo "")
        hb_ts=$(awk '{print $1}' <<<"$hb_line")
        hb_tool=$(awk '{print $2}' <<<"$hb_line")
        if [[ -n "$hb_ts" ]]; then
            now=$(date -u +%s)
            age=$((now - hb_ts))
            if (( age >= 0 && age < 60 )); then
                idle_hb=$(printf " · ⚡%ss %s" "$age" "${hb_tool:-?}")
            fi
        fi
    fi
    printf "LDD · idle%s" "$idle_hb"
    exit 0
fi

max=$(awk 'BEGIN{m=0}{v=$1+0; if(v>m)m=v}END{print m}' <<<"$losses")

sparkline=""
while IFS= read -r v; do
    [[ -z "$v" ]] && continue
    if awk -v v="$v" 'BEGIN{exit !(v+0 <= 0)}'; then
        sparkline+="·"
    elif awk -v m="$max" 'BEGIN{exit !(m+0 <= 0)}'; then
        sparkline+="·"
    else
        idx=$(awk -v v="$v" -v m="$max" 'BEGIN{printf "%d", (v/m)*7 + 0.5}')
        (( idx > 7 )) && idx=7
        (( idx < 0 )) && idx=0
        sparkline+="${BLOCKS[idx]}"
    fi
done <<<"$losses"

last=$(tail -1 <<<"$losses")
prev=$(tail -2 <<<"$losses" | head -1)
first=$(head -1 <<<"$losses")

delta=""
if [[ -n "$prev" && "$prev" != "$last" ]]; then
    delta=$(awk -v a="$last" -v b="$prev" 'BEGIN{
        d = a - b
        if (d < -0.005) arrow = "↓"
        else if (d > 0.005) arrow = "↑"
        else arrow = "→"
        printf " %s%+.3f", arrow, d
    }')
fi

trend="→"
if [[ -n "$first" && "$first" != "$last" ]]; then
    trend=$(awk -v a="$last" -v b="$first" 'BEGIN{
        d = a - b
        if (d < -0.005) print "↓"
        else if (d > 0.005) print "↑"
        else print "→"
    }')
fi

task_short="${task:-untitled}"
(( ${#task_short} > 40 )) && task_short="${task_short:0:37}..."

loop_label="${loop:-?}"
k_label=""
if [[ -n "$last_k" ]]; then
    case "$loop" in
        architect) k_prefix="p" ;;
        refine)    k_prefix="r" ;;
        outer)     k_prefix="o" ;;
        cot)       k_prefix="c" ;;
        *)         k_prefix="i" ;;
    esac
    k_label=" ${k_prefix}${last_k}"
fi

last_fmt=$(awk -v v="$last" 'BEGIN{printf "%.3f", v+0}')

# Heartbeat — shows "⚡ <age>s <tool>" if a tool fired in the last 60s.
# Driven by .claude/hooks/ldd_heartbeat.sh on PreToolUse events.
hb_suffix=""
hb_file="${cwd}/.ldd/heartbeat"
if [[ -f "$hb_file" ]]; then
    hb_line=$(cat "$hb_file" 2>/dev/null || echo "")
    hb_ts=$(awk '{print $1}' <<<"$hb_line")
    hb_tool=$(awk '{print $2}' <<<"$hb_line")
    if [[ -n "$hb_ts" ]]; then
        now=$(date -u +%s)
        age=$((now - hb_ts))
        if (( age >= 0 && age < 60 )); then
            hb_suffix=$(printf " · ⚡%ss %s" "$age" "${hb_tool:-?}")
        fi
    fi
fi

printf "LDD · %s · %s%s · loss %s%s · %s %s · %s%s" \
    "$task_short" \
    "$loop_label" \
    "$k_label" \
    "$last_fmt" \
    "$delta" \
    "$sparkline" \
    "$trend" \
    "$source_tag" \
    "$hb_suffix"
