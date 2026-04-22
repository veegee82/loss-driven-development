#!/usr/bin/env bash
# LDD_INSTALL_v1 — plugin-level SessionStart hook.
# Registered via hooks/hooks.json; Claude Code merges it into the user's
# hook registry on plugin load. Fires at the start of every session for
# every project where the LDD plugin is enabled.
#
# Contract:
#   - Gated on `.ldd/` existing in the session's project root — this makes
#     the installer a no-op for projects that haven't opted in to LDD.
#     First-time opt-in runs via `bootstrap-userspace` skill or the
#     `/ldd-install` slash command, both of which create `.ldd/` first.
#   - Idempotent: compares plugin version against `.ldd/.install_version`
#     marker and all installed artifacts' checksums; if everything matches,
#     exits silently.
#   - Version-gated: when plugin updates, version mismatch triggers full
#     re-install of artifacts from the new plugin cache (launcher,
#     statusline, heartbeat hook, stop-render hook) + merges/updates
#     `.claude/settings.local.json` hook entries.
#   - Safe merge: `.claude/settings.local.json` is touched via `jq` with
#     de-duplication by command-path so LDD's entries are added/refreshed
#     without clobbering other hooks the user or other plugins registered.
#
# Output contract:
#   Always prints JSON on stdout with a `hookSpecificOutput` wrapper so
#   Claude Code renders the install/update message below the session
#   greeting. Returns `{}` (empty) when the project opted out (no `.ldd/`)
#   or when everything is already current.

set -uo pipefail
export LC_ALL=C

input=$(cat 2>/dev/null || echo "{}")
cwd=$(jq -r '.cwd // .workspace.current_dir // empty' <<<"$input" 2>/dev/null || true)
[[ -z "$cwd" ]] && cwd="$PWD"

# The plugin root is exposed by Claude Code as ${CLAUDE_PLUGIN_ROOT}.
# Fall back to walking up from this script's own location so the installer
# is also runnable manually (for debugging or from `/ldd-install`).
plugin_root="${CLAUDE_PLUGIN_ROOT:-}"
if [[ -z "$plugin_root" ]]; then
    script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &>/dev/null && pwd)
    if [[ -f "$script_dir/../.claude-plugin/plugin.json" ]]; then
        plugin_root=$(cd -- "$script_dir/.." && pwd)
    fi
fi
if [[ -z "$plugin_root" || ! -f "$plugin_root/.claude-plugin/plugin.json" ]]; then
    echo '{}'
    exit 0
fi

plugin_version=$(jq -r '.version // "unknown"' "$plugin_root/.claude-plugin/plugin.json" 2>/dev/null || echo "unknown")

ldd_dir="$cwd/.ldd"
claude_dir="$cwd/.claude"
hooks_dir="$claude_dir/hooks"
marker="$ldd_dir/.install_version"

# Gate: skip install when the project has not opted in.
if [[ ! -d "$ldd_dir" ]]; then
    echo '{}'
    exit 0
fi

# --- Resolve template paths -------------------------------------------------
tpl_launcher="$plugin_root/skills/bootstrap-userspace/ldd_trace"
tpl_statusline="$plugin_root/skills/host-statusline/statusline.sh"
tpl_heartbeat="$plugin_root/skills/host-statusline/heartbeat.sh"
tpl_stop_render="$plugin_root/skills/host-statusline/stop_render.sh"
tpl_config="$plugin_root/skills/host-statusline/config.yaml.default"

missing=()
for f in "$tpl_launcher" "$tpl_statusline" "$tpl_heartbeat" "$tpl_stop_render"; do
    [[ -f "$f" ]] || missing+=("$(basename "$f")")
done
# tpl_config is optional for pre-v0.12 plugin builds — do not abort if missing.
if (( ${#missing[@]} > 0 )); then
    jq -n --arg v "$plugin_version" --arg m "${missing[*]}" '{
        hookSpecificOutput: {
            hookEventName: "SessionStart",
            additionalContext: ("LDD install aborted: plugin v" + $v + " is missing templates: " + $m + ". Re-install the plugin.")
        }
    }'
    exit 0
fi

# --- Idempotency check ------------------------------------------------------
up_to_date=1
if [[ -f "$marker" ]]; then
    installed_version=$(tr -d '[:space:]' < "$marker" 2>/dev/null || echo "")
    [[ "$installed_version" == "$plugin_version" ]] || up_to_date=0
else
    up_to_date=0
fi

for dest_tpl in \
    "$ldd_dir/ldd_trace|$tpl_launcher" \
    "$ldd_dir/statusline.sh|$tpl_statusline" \
    "$hooks_dir/ldd_heartbeat.sh|$tpl_heartbeat" \
    "$hooks_dir/ldd_stop_render.sh|$tpl_stop_render"
do
    dest="${dest_tpl%%|*}"
    tpl="${dest_tpl##*|}"
    if [[ ! -x "$dest" ]]; then up_to_date=0; continue; fi
    if ! cmp -s "$dest" "$tpl"; then up_to_date=0; fi
done

if (( up_to_date )); then
    echo '{}'
    exit 0
fi

# --- Install / update -------------------------------------------------------
mkdir -p "$ldd_dir" "$hooks_dir"

install_file() {
    local src="$1" dest="$2"
    cp -f "$src" "$dest"
    chmod +x "$dest"
}

install_file "$tpl_launcher"    "$ldd_dir/ldd_trace"
install_file "$tpl_statusline"  "$ldd_dir/statusline.sh"
install_file "$tpl_heartbeat"   "$hooks_dir/ldd_heartbeat.sh"
install_file "$tpl_stop_render" "$hooks_dir/ldd_stop_render.sh"

# Seed .ldd/config.yaml on FIRST install only — never overwrite a user's
# edited config. The default template turns on `verbosity: summary` and
# `gate_on_activity: true`, which matches the user-visible defaults
# `stop_render.sh` relies on.
if [[ -f "$tpl_config" && ! -f "$ldd_dir/config.yaml" ]]; then
    cp -f "$tpl_config" "$ldd_dir/config.yaml"
    chmod 0644 "$ldd_dir/config.yaml"
fi

# --- Merge .claude/settings.local.json safely -------------------------------
settings_file="$claude_dir/settings.local.json"
[[ -f "$settings_file" ]] || echo '{}' > "$settings_file"

tmp=$(mktemp)
heartbeat_cmd='$CLAUDE_PROJECT_DIR/.claude/hooks/ldd_heartbeat.sh'
stop_render_cmd='$CLAUDE_PROJECT_DIR/.claude/hooks/ldd_stop_render.sh'
statusline_cmd='.ldd/statusline.sh'

jq \
    --arg hb "$heartbeat_cmd" \
    --arg sr "$stop_render_cmd" \
    --arg sl "$statusline_cmd" \
'
    .statusLine //= {}
    | .statusLine.type //= "command"
    | (if (.statusLine.command // "") == "" then .statusLine.command = $sl else . end)
    | .hooks //= {}
    | .hooks.PreToolUse //= []
    | .hooks.Stop //= []
    | .hooks.PreToolUse |= (
        map(select(
            ((.hooks // []) | map(.command // "") | any(endswith("/ldd_heartbeat.sh"))) | not
        ))
        + [{
            matcher: "Bash|Edit|Write|Read|Grep|Glob",
            hooks: [{type: "command", command: $hb, timeout: 2}]
          }]
      )
    | .hooks.Stop |= (
        map(select(
            ((.hooks // []) | map(.command // "") | any(endswith("/ldd_stop_render.sh"))) | not
        ))
        + [{
            hooks: [{type: "command", command: $sr, timeout: 5}]
          }]
      )
' "$settings_file" > "$tmp" && mv "$tmp" "$settings_file"

# --- Record version marker --------------------------------------------------
printf '%s\n' "$plugin_version" > "$marker"

# --- Notify user ------------------------------------------------------------
prev_version="${installed_version:-<fresh>}"
verb="installed"
[[ "$prev_version" != "<fresh>" ]] && verb="updated ($prev_version → $plugin_version)"

jq -n --arg v "$plugin_version" --arg verb "$verb" '{
    hookSpecificOutput: {
        hookEventName: "SessionStart",
        additionalContext: (
            "LDD plugin artifacts " + $verb + ": "
            + ".ldd/ldd_trace (launcher), "
            + ".ldd/statusline.sh, "
            + ".claude/hooks/ldd_heartbeat.sh (PreToolUse), "
            + ".claude/hooks/ldd_stop_render.sh (Stop). "
            + "Settings merged into .claude/settings.local.json. "
            + "Reload the Claude Code session if hooks do not fire yet."
        )
    }
}'
