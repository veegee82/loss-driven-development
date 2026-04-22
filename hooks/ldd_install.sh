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

# --- Preflight: jq is required for every write-path in this installer. ------
# Without it, previous versions silently wrote an empty settings.local.json
# and marked the install as "current" — a stealth-fail the user could not
# see. Abort loudly (via SessionStart additionalContext) WITHOUT writing the
# version marker, so the next session retries once jq is on PATH.
if ! command -v jq >/dev/null 2>&1; then
    cat <<'JSON'
{
  "hookSpecificOutput": {
    "hookEventName": "SessionStart",
    "additionalContext": "LDD install aborted: `jq` is required but was not found on PATH. Install jq (Debian/Ubuntu: `sudo apt install jq`, macOS: `brew install jq`, Windows: `winget install jqlang.jq`) and reload the Claude Code session. No artifacts were written; .ldd/.install_version is unchanged so the next SessionStart will retry automatically."
  }
}
JSON
    exit 0
fi

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

# Gate: install only when at least one opt-in signal fires. The goal is
# "nachhaltig da" (present on every install/session) without the plugin
# creating `.ldd/` in unrelated projects the user happens to open.
#
# Signal A (historical default) — `.ldd/` already exists in the project.
#                                 This is how opt-in has always worked and
#                                 is how `/ldd-install` still bootstraps
#                                 (mkdir .ldd; then run this installer).
# Signal B (self-identification) — `$cwd/.claude-plugin/plugin.json` exists
#                                 AND `.name == "loss-driven-development"`.
#                                 Uniquely identifies the plugin's own dev
#                                 repo. Collision-proof; anyone forking or
#                                 vendoring under the same name wants LDD
#                                 on anyway. Complements Change 1 (repo
#                                 seed) as a safety-net when someone wipes
#                                 `.ldd/` but keeps the repo.
# Signal C (user-global opt-in) — one of:
#                                   * env   LDD_AUTO_OPTIN=1
#                                   * file  ~/.claude/settings.json with
#                                            `.ldd.auto_install == true`
#                                 Off by default. Users who run LDD in
#                                 every project flip one switch once and
#                                 never touch `/ldd-install` again.
#
# If any signal fires and `.ldd/` does not yet exist, create it here so
# the rest of this script can proceed uniformly.

signal_a=0
signal_b=0
signal_c=0

if [[ -d "$ldd_dir" ]]; then
    signal_a=1
fi

if [[ -f "$cwd/.claude-plugin/plugin.json" ]]; then
    plug_name=$(jq -r '.name // ""' "$cwd/.claude-plugin/plugin.json" 2>/dev/null || echo "")
    if [[ "$plug_name" == "loss-driven-development" ]]; then
        signal_b=1
    fi
fi

if [[ "${LDD_AUTO_OPTIN:-0}" == "1" ]]; then
    signal_c=1
elif [[ -f "$HOME/.claude/settings.json" ]]; then
    au_global=$(jq -r '.ldd.auto_install // false' "$HOME/.claude/settings.json" 2>/dev/null || echo "false")
    if [[ "$au_global" == "true" ]]; then
        signal_c=1
    fi
fi

if (( signal_a == 0 && signal_b == 0 && signal_c == 0 )); then
    echo '{}'
    exit 0
fi

# Auto-create `.ldd/` on Signal B or C (Signal A already has it).
if [[ ! -d "$ldd_dir" ]]; then
    mkdir -p "$ldd_dir"
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
    # Per-file marker-version gate — a hook/launcher whose source bumps its
    # header marker (e.g. LDD_HEARTBEAT_HOOK_v2 → v3) must re-install even
    # under patch_skip, because the marker bump signals a semantic change
    # users cannot pick up by byte-diff alone (patch_skip ignores byte diff).
    # Pattern covers all current + future markers: LDD_HEARTBEAT_HOOK_vN,
    # LDD_STATUSLINE_vN, LDD_STOP_RENDER_vN, and any LDD_<anything>_vN.
    if [[ -x "$dest" ]]; then
        dest_marker=$(grep -oE 'LDD_[A-Z_]+_v[0-9]+' "$dest" 2>/dev/null | head -1)
        tpl_marker=$(grep -oE 'LDD_[A-Z_]+_v[0-9]+' "$tpl" 2>/dev/null | head -1)
        if [[ -n "$tpl_marker" && "$dest_marker" != "$tpl_marker" ]]; then
            up_to_date=0
            any_missing=1  # treat as missing so patch_skip does not swallow it
        fi
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
# Under multi-clauding (parallel SessionStart hooks from two Claude Code
# sessions on the same project), the read-modify-write sequence below can
# race: hook-A reads, hook-B reads, hook-A writes, hook-B overwrites with a
# stale copy. jq's endswith()-dedup happens to make the merge idempotent
# when both writes land in order, but that is luck, not design. Serialise
# the critical section with flock on a dedicated lock file.
settings_file="$claude_dir/settings.local.json"
lock_file="$claude_dir/.ldd_install.lock"
[[ -f "$settings_file" ]] || echo '{}' > "$settings_file"

tmp=$(mktemp)
heartbeat_cmd='$CLAUDE_PROJECT_DIR/.claude/hooks/ldd_heartbeat.sh'
stop_render_cmd='$CLAUDE_PROJECT_DIR/.claude/hooks/ldd_stop_render.sh'
statusline_cmd='.ldd/statusline.sh'

merge_settings() {
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
}

if command -v flock >/dev/null 2>&1; then
    # util-linux flock — standard on Linux; macOS ships it via brew but not
    # by default. -w 5 = give up after 5s (well under the 15s hook timeout).
    exec 9>>"$lock_file"
    if flock -w 5 9; then
        merge_settings
        flock -u 9
    else
        # Could not acquire lock in 5s — another installer on this project
        # is almost certainly writing. Fall through without the merge; the
        # other process is doing the same work.
        :
    fi
    exec 9>&-
else
    # No flock available (older macOS without util-linux). Accept the
    # historical small race window; jq-dedup makes concurrent installers
    # idempotent in the common case.
    merge_settings
fi
rm -f "$tmp" 2>/dev/null || true

# --- Auto-enable core.hooksPath = .githooks on Signal B only ---------------
# The `.githooks/` directory at the repo root holds the drift-gate pre-commit
# hook that keeps Δloss_bundle citation sites in sync with the fixtures.
# Without `core.hooksPath`, git ignores it and commits can silently ship doc
# drift. We automate the one-line `git config` that activates it so a fresh
# clone of the LDD plugin's own source repo is "install → everything works".
#
# Hard constraints:
#   * Signal B only — this is the plugin's own dev repo. Signal A (user
#     already opted in via existing `.ldd/`) and Signal C (user-global
#     auto-opt-in) do not justify touching git config in an unrelated
#     project of the user's — that would be invasive.
#   * `.githooks/` must actually exist in the project (otherwise there is
#     nothing to activate).
#   * git must be on PATH AND `$cwd` must be a git working tree.
#   * Idempotent: if `core.hooksPath` is already `.githooks`, no-op. If it
#     is set to something ELSE, respect the user's choice and surface a
#     note — never silently overwrite.
hooks_status=""
if (( signal_b == 1 )) \
   && [[ -d "$cwd/.githooks" ]] \
   && command -v git >/dev/null 2>&1 \
   && git -C "$cwd" rev-parse --git-dir >/dev/null 2>&1
then
    existing_hooks_path=$(git -C "$cwd" config --local --get core.hooksPath 2>/dev/null || true)
    if [[ -z "$existing_hooks_path" ]]; then
        if git -C "$cwd" config --local core.hooksPath .githooks 2>/dev/null; then
            hooks_status="git core.hooksPath set to .githooks (drift-gate active)"
        fi
    elif [[ "$existing_hooks_path" == ".githooks" ]]; then
        hooks_status="git core.hooksPath already .githooks (drift-gate active)"
    else
        hooks_status="git core.hooksPath is $existing_hooks_path — not overriding; pre-commit drift-gate will NOT fire unless you add .githooks/pre-commit to that path"
    fi
fi

# --- Record version marker --------------------------------------------------
printf '%s\n' "$plugin_version" > "$marker"

# --- Notify user ------------------------------------------------------------
# For FRESH installs, the PreToolUse + Stop hooks were just added to
# settings.local.json AFTER Claude Code read the file on session start,
# so they will not fire in the current session. Make that reload the
# headline rather than a conditional footnote.
prev_version="${installed_version:-<fresh>}"
if [[ -z "$installed_version" ]]; then
    # Fresh install: reload is mandatory for hooks to activate.
    reload_note="⚠  Please reload (/ restart) the Claude Code session now — PreToolUse (heartbeat) and Stop (render) hooks were just registered and will not fire until Claude Code re-reads .claude/settings.local.json."
    verb="installed (fresh)"
else
    # Update: only artifact bytes changed; hook registrations were already
    # active from the previous install, so a reload is usually not needed.
    reload_note="(Reload the Claude Code session if hooks do not fire yet.)"
    verb="updated ($prev_version → $plugin_version)"
fi

jq -n \
    --arg v "$plugin_version" \
    --arg verb "$verb" \
    --arg reload "$reload_note" \
    --arg hooks "$hooks_status" \
'{
    hookSpecificOutput: {
        hookEventName: "SessionStart",
        additionalContext: (
            "LDD plugin artifacts " + $verb + ": "
            + ".ldd/ldd_trace (launcher), "
            + ".ldd/statusline.sh, "
            + ".claude/hooks/ldd_heartbeat.sh (PreToolUse), "
            + ".claude/hooks/ldd_stop_render.sh (Stop). "
            + "Settings merged into .claude/settings.local.json. "
            + (if $hooks == "" then "" else $hooks + ". " end)
            + $reload
        )
    }
}'
