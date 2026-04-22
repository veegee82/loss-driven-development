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

# --- Idempotency + SemVer-aware auto-update policy --------------------------
#
# Version scheme (project-specific, differs from stock SemVer):
#
#     I.N.M   — I=major (reserved), N=release (public), M=dev-iteration
#
#   - Bumping N (or I) is a "release": plugin artifacts auto-update on the
#     next SessionStart, same as before.
#   - Bumping ONLY M is a "dev iteration": auto-update is SUPPRESSED so
#     users are not churned by every mid-release patch commit.
#   - Missing artifacts still force an install (the hook cannot leave a
#     project in a half-installed state, ever).
#   - LDD_FORCE_INSTALL=1 in the hook's environment bypasses the M-skip —
#     the `/ldd-install` slash command sets it, so users can force an
#     install on demand.
#
# Examples:
#     0.12.3 → 0.12.4   dev iteration → skip (unless forced / artifact missing)
#     0.12.9 → 0.13.0   release       → install, bump marker to 0.13.0
#     0.13.0 → 1.0.0    major         → install, bump marker to 1.0.0

parse_version() {
    # Usage: parse_version "0.12.4" → prints "0 12 4" on stdout; empty on parse fail.
    # Accepts optional trailing "-pre" / "+build" suffix (stripped silently).
    local v="$1"
    if [[ "$v" =~ ^([0-9]+)\.([0-9]+)\.([0-9]+)([-.+][A-Za-z0-9.-]+)?$ ]]; then
        printf '%s %s %s' "${BASH_REMATCH[1]}" "${BASH_REMATCH[2]}" "${BASH_REMATCH[3]}"
    fi
}

up_to_date=1
patch_skip=0          # set when only M differs between marker and plugin
force_install="${LDD_FORCE_INSTALL:-0}"
installed_version=""

# --- User opt-out: .ldd/config.yaml `install.auto_update: false` ------------
# Strict security mode — user wants zero automatic installs, N-bump included.
# LDD_FORCE_INSTALL=1 still wins (that's the `/ldd-install` manual path).
#
# Parse the `install:` block inline — no PyYAML dep, matching the
# `display:` reader in scripts/ldd_trace/session_gate.py. We accept only
# the documented shape (one-level nesting, scalar bool values).
auto_update=1
user_config="$ldd_dir/config.yaml"
if [[ -f "$user_config" ]]; then
    au_value=$(awk '
        /^[[:space:]]*install:[[:space:]]*$/ { in_blk = 1; next }
        # Leave the install: block as soon as a non-indented key appears.
        in_blk && /^[^[:space:]#]/          { in_blk = 0 }
        in_blk && /^[[:space:]]+auto_update[[:space:]]*:/ {
            sub(/.*auto_update[[:space:]]*:[[:space:]]*/, "")
            sub(/[[:space:]]*#.*$/, "")  # strip trailing comment
            gsub(/["'\'']/, "")          # strip quotes
            gsub(/[[:space:]]/, "")      # strip whitespace
            print tolower($0)
            exit
        }
    ' "$user_config" 2>/dev/null)
    case "$au_value" in
        false|0|no|off) auto_update=0 ;;
    esac
fi

if [[ -f "$marker" ]]; then
    installed_version=$(tr -d '[:space:]' < "$marker" 2>/dev/null || echo "")
    if [[ "$installed_version" != "$plugin_version" ]]; then
        up_to_date=0
        # Only treat as "patch-skip" when both versions parse AND I + N agree.
        read -r p_maj p_min _p_patch <<< "$(parse_version "$plugin_version")"
        read -r i_maj i_min _i_patch <<< "$(parse_version "$installed_version")"
        if [[ -n "$p_maj" && -n "$i_maj" \
              && "$p_maj" == "$i_maj" && "$p_min" == "$i_min" ]]; then
            patch_skip=1
        fi
    fi
else
    up_to_date=0
fi

# Check artifact presence + byte-identity. When patch_skip is 1, a byte-diff
# alone does NOT invalidate the skip (dev iterations change the payload by
# definition); only MISSING artifacts force the install to fill the gap.
any_missing=0
for dest_tpl in \
    "$ldd_dir/ldd_trace|$tpl_launcher" \
    "$ldd_dir/statusline.sh|$tpl_statusline" \
    "$hooks_dir/ldd_heartbeat.sh|$tpl_heartbeat" \
    "$hooks_dir/ldd_stop_render.sh|$tpl_stop_render"
do
    dest="${dest_tpl%%|*}"
    tpl="${dest_tpl##*|}"
    if [[ ! -x "$dest" ]]; then
        up_to_date=0
        any_missing=1
        continue
    fi
    if (( patch_skip == 0 )); then
        if ! cmp -s "$dest" "$tpl"; then up_to_date=0; fi
    fi
done

# Decision matrix:
#   up_to_date=1                         → silent no-op (exact match, all bytes same)
#   patch_skip=1 AND any_missing=0
#              AND force_install=0       → silent no-op (dev iteration)
#   auto_update=0 AND force_install=0    → silent no-op (user opt-out)
#   otherwise                            → fall through to install
if (( up_to_date )); then
    echo '{}'
    exit 0
fi
if (( patch_skip == 1 && any_missing == 0 && force_install == 0 )); then
    echo '{}'
    exit 0
fi
if (( auto_update == 0 && force_install == 0 )); then
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
