---
description: Explicitly install or re-install the LDD plugin's project-local artifacts (.ldd/ldd_trace launcher, statusline, heartbeat + stop-render hooks, settings merge). Idempotent; version-gated; safe to re-run. Required once per project as the opt-in step; afterwards the plugin's SessionStart hook maintains everything automatically on every session start and every plugin update.
---

Install / refresh the LDD plugin's per-project artifacts for the current working directory.

## What this does

1. Create `.ldd/` in the project root if it doesn't exist (this is the opt-in marker — the plugin's SessionStart hook only touches projects that have `.ldd/`).
2. Execute the plugin's installer at `${CLAUDE_PLUGIN_ROOT}/hooks/ldd_install.sh`, which drops:
   - `.ldd/ldd_trace` — trace CLI launcher
   - `.ldd/statusline.sh` — permanent loss-curve statusline renderer
   - `.claude/hooks/ldd_heartbeat.sh` — PreToolUse heartbeat writer
   - `.claude/hooks/ldd_stop_render.sh` — Stop-event trace-block auto-renderer
3. Safely merge entries into `.claude/settings.local.json` (statusLine pointer + PreToolUse + Stop hooks) without clobbering any other hooks the user or other plugins have registered.
4. Write `.ldd/.install_version` so subsequent SessionStart runs can detect version drift and self-update on plugin upgrade.

## How to invoke

```bash
mkdir -p .ldd
bash "${CLAUDE_PLUGIN_ROOT}/hooks/ldd_install.sh" <<<"{\"cwd\": \"$PWD\"}"
```

Report back what the installer printed — the `hookSpecificOutput.additionalContext` field states whether this was a fresh install, an update (`0.X.Y → 0.A.B`), or a no-op (already current). If the installer says "Reload the Claude Code session if hooks do not fire yet", relay that instruction to the user — fresh hook registrations require a session restart to be picked up by Claude Code's hook registry.

## When users reach for this

- First time using LDD in a project (required once)
- After a plugin upgrade if the automatic SessionStart re-install has not run yet
- When a `.ldd/` directory was wiped or migrated
- When `.claude/settings.local.json` is missing LDD's `statusLine`, `PreToolUse` (heartbeat), or `Stop` (render) entries

After this command runs once, the plugin's `hooks/hooks.json`-registered SessionStart hook keeps everything in sync on every subsequent session start — no further manual steps required.
