---
name: host-statusline
description: Use at the start of any LDD session running under Claude Code — auto-installs a permanent statusline that shows the current LDD task, loop, iteration, loss, and a Unicode loss-curve sparkline at all times, without any user action or configuration. Idempotent, merge-safe, project-local. Silently no-ops on non-Claude-Code hosts. Fires once per session in parallel with `bootstrap-userspace`.
---

# Host-StatusLine

## The Metaphor

**The heart-rate monitor on the operating table.** The surgeon does not pause to ask the anesthesiologist for vitals — they glance at the monitor beeping in the corner and keep cutting. `host-statusline` is that monitor for LDD: it shows loss descent, iteration, loop, and trend permanently in the console, without the surgeon ever having to ask for it. The user glances down, sees `LDD · fix parser · inner i3 · loss 0.125 ↓-0.250 · ▇▅▃▂ · .ldd`, and knows at a glance what the agent is doing.

## Overview

`using-ldd` renders the trace block **inside the assistant's reply** — but that block is only visible *while a reply is on screen* and *until the next screenful scrolls it away*. Between turns, during tool execution, during user edits, the loss curve is invisible. For long iteration chains this is the difference between *monitorable* and *trust-me* LDD.

This skill fixes that on Claude Code by auto-installing a **permanent statusline** rendered at the bottom of the console on every UI tick. The statusline is a one-liner; its content comes from reading either `.ldd/trace.log` (Tier 0) or the current session's JSONL transcript grepped for `⟪LDD-TRACE-v1⟫` markers (Tier 2). It reuses `bootstrap-userspace`'s store decision rather than inventing its own.

**Core principle:** the user never has to configure anything. The skill detects Claude Code, writes `.ldd/statusline.sh`, merges a single key into `.claude/settings.local.json`, and the loss curve appears at the next UI refresh. Claude Code's statusline cannot be truncated by the terminal (it is the status line) and is always on screen.

## When to Use

Invoke **once per session** alongside `bootstrap-userspace`, when:

- The user prefixes a message with `LDD:` or triggers any LDD skill, AND
- The current host is Claude Code (detect via presence of `~/.claude/projects/` and a `transcript_path` field in the usual hook stdin shape), AND
- You have not yet installed the statusline for this project in this session

Do **not** invoke when:

- The host is not Claude Code (no-op — statusline is a Claude-Code feature; other hosts have their own mechanisms, not yet covered)
- `.claude/settings.local.json` already contains a `statusLine` key whose `command` field does **not** point at `.ldd/statusline.sh` (user-owned statusline — respect it, do not overwrite)
- `.ldd/statusline.sh` already exists AND already carries the `LDD_STATUSLINE_v1` marker AND `.claude/settings.local.json` already references it (fully installed — skip)
- The working directory is read-only (no `.ldd/` can be written — fall through to inline-only; statusline is not possible)

## What gets installed

Four artifacts, all project-local:

```
<project>/.ldd/statusline.sh               ← reader script (copied from this skill)
<project>/.claude/hooks/ldd_heartbeat.sh   ← PreToolUse hook that bumps .ldd/heartbeat
<project>/.claude/settings.local.json      ← merge in statusLine + PreToolUse hook
```

Nothing global. `~/.claude/settings.json` is **never** touched — that is user-level territory and a different project may have no LDD at all.

The statusline shows two kinds of activity in one line:

- **Trace state** — task / loop / iteration / loss / sparkline, read from `.ldd/trace.log`. Updates whenever an `ldd_trace append`/`close` lands (every few minutes during real work).
- **In-flight heartbeat** — `⚡<age>s <tool>`, read from `.ldd/heartbeat`. Updates on every tool call in between (Bash/Edit/Write/Read/Grep/Glob), then auto-disappears after 60 s of stillness.

Without the heartbeat, the statusline would freeze between iteration commits, which makes it useless as a live monitor. That is why the hook is part of the standard install.

## Installation procedure

Execute in order. Every step is idempotent; a re-run on a fully-installed project is a no-op and produces no user-visible output.

### Step 1 — host detection

Check:

- `~/.claude/projects/` exists (Claude Code persists transcripts here)
- The stdin format available to `statusLine` hooks on this host is the Claude Code shape (`cwd`, `transcript_path`, `session_id`)

If either check fails → this is not Claude Code. Silently skip all subsequent steps. Log nothing. The inline trace block from `using-ldd` remains the only observation surface, as before.

### Step 2 — ensure `.ldd/` exists

If `<cwd>/.ldd/` is missing, create it (`mkdir -p`). `bootstrap-userspace` normally creates it; this step is a safety net for the case where `host-statusline` fires first.

### Step 3 — install / verify `statusline.sh`

Read the `statusline.sh` template that ships with this skill (same directory as this `SKILL.md`).

Check `<cwd>/.ldd/statusline.sh`:

- **Does not exist** → copy the template to that path; `chmod +x` it.
- **Exists AND contains the literal marker `LDD_STATUSLINE_v1`** on any of its first 5 lines → an earlier version is already installed. If byte-identical to the current template: skip. If not: overwrite (newer version of the skill shipped an updated template).
- **Exists AND does NOT contain the marker** → the user has replaced the file with a custom script. Respect it, do **not** overwrite. Continue to Step 4 (their custom script is still what settings will point to).

### Step 4 — merge `.claude/settings.local.json` (statusLine)

Create `<cwd>/.claude/` if missing (`mkdir -p`).

Read or create `<cwd>/.claude/settings.local.json`. Four cases:

1. **File missing or empty** → write:
   ```json
   {
     "statusLine": {
       "type": "command",
       "command": ".ldd/statusline.sh"
     }
   }
   ```
2. **File exists, no `statusLine` key** → merge the `statusLine` key in, preserving all other keys. Use `jq`:
   ```bash
   tmp=$(mktemp)
   jq '.statusLine = {type: "command", command: ".ldd/statusline.sh"}' \
       .claude/settings.local.json > "$tmp" && mv "$tmp" .claude/settings.local.json
   ```
3. **File exists, has `statusLine` whose `.command` is `.ldd/statusline.sh`** → already installed. Skip.
4. **File exists, has `statusLine` whose `.command` is something else** → user-owned statusline. **Do not overwrite.** Emit exactly once in the next trace block: `statusline: user-owned at <their command>, skipping auto-install`. Continue — the inline trace block remains the loss-visibility surface, statusline just isn't on LDD duty.

### Step 5 — install / verify the heartbeat hook

Create `<cwd>/.claude/hooks/` if missing (`mkdir -p`).

Read the `heartbeat.sh` template that ships with this skill (same directory as this `SKILL.md`).

Check `<cwd>/.claude/hooks/ldd_heartbeat.sh`:

- **Does not exist** → copy the template to that path; `chmod +x` it.
- **Exists AND contains the literal marker `LDD_HEARTBEAT_HOOK_v1`** on any of its first 5 lines → an earlier version is already installed. If byte-identical to the current template: skip. If not: overwrite (newer version of the skill shipped an updated template).
- **Exists AND does NOT contain the marker** → the user has replaced the file with a custom script. Respect it, do **not** overwrite. Continue.

### Step 6 — merge `.claude/settings.local.json` (PreToolUse hook)

Register the heartbeat hook as a `PreToolUse` entry in the same `.claude/settings.local.json` edited in Step 4.

Four cases, mirroring Step 4:

1. **No `hooks` key** → merge in:
   ```json
   {
     "hooks": {
       "PreToolUse": [
         {
           "matcher": "Bash|Edit|Write|Read|Grep|Glob",
           "hooks": [{"type": "command", "command": ".claude/hooks/ldd_heartbeat.sh", "timeout": 2}]
         }
       ]
     }
   }
   ```
2. **Has `hooks.PreToolUse` but no entry pointing at `.claude/hooks/ldd_heartbeat.sh`** → append a new entry to the array with the matcher and command above. Preserve other entries byte-for-byte.
3. **Has an entry pointing at `.claude/hooks/ldd_heartbeat.sh` already** → already installed. Skip.
4. **Has a user-owned entry with a different command but a matcher including `ldd_heartbeat`** → user has a custom heartbeat setup. Do **not** overwrite. Report `heartbeat: user-owned (skipped)` in the trace header suffix.

Idempotent `jq` recipe for case 2:

```bash
tmp=$(mktemp)
jq '
  .hooks = (.hooks // {}) |
  .hooks.PreToolUse = (.hooks.PreToolUse // []) |
  if any(.hooks.PreToolUse[]; .hooks[0].command == ".claude/hooks/ldd_heartbeat.sh")
  then .
  else .hooks.PreToolUse += [{
    "matcher": "Bash|Edit|Write|Read|Grep|Glob",
    "hooks": [{"type": "command", "command": ".claude/hooks/ldd_heartbeat.sh", "timeout": 2}]
  }]
  end
' .claude/settings.local.json > "$tmp" && mv "$tmp" .claude/settings.local.json
```

### Step 7 — report in the trace header

Whether the install happened, was already done, or was skipped for user-ownership: the next `Store :` line in the trace block gains one extra concise suffix, so the user knows the statusline is live (or why it isn't):

```
│ Store     : local (.ldd/trace.log)  ·  statusline: installed, heartbeat: installed
│ Store     : local (.ldd/trace.log)  ·  statusline: already live, heartbeat: already live
│ Store     : local (.ldd/trace.log)  ·  statusline: installed, heartbeat: user-owned (skipped)
│ Store     : local (.ldd/trace.log)  ·  statusline: user-owned (skipped)
│ Store     : conversation history     ·  statusline: n/a (non-Claude-Code host)
```

One suffix, two short status tokens, no dialog. The user who glances at the trace block understands in one second whether the bottom-of-screen monitor is running AND whether the heartbeat hook is feeding it mid-task activity.

## What the statusline shows

v0.11.0 format (level-aware):

```
Idle           : LDD · idle                (no .ldd/trace.log history ever)
Standby        : LDD · standby             (prior task(s) in trace.log; session gate blocks current session — awaiting `ldd_trace init` for a fresh task)
Active L0..L2  : LDD · L2/deliberate · inner k=1 · loss=0.167 · <task> · <sparkline> <trend> · <source>
Active L3/L4   : LDD · L3/structural · creativity=standard · design k=2 · loss=0.286 · <task> · <sparkline> <trend> · <source>
```

When a pre-v0.11.0 trace is read (no `L<n>/<name>` meta-line token), the statusline falls back to the legacy layout:

```
LDD · <task> · <loop> i<k> · loss <value><±delta arrow> · <sparkline> <trend> · <source>
```

Concrete post-v0.11.0 example after 3 design-phase iterations:

```
LDD · L3/structural · creativity=standard · design k=2 · loss=0.286 · design a billing service · █▆▃ ↓ · .ldd
```

Legend:

- `L<n>/<name>` — the thinking-level and its canonical name, pulled from the meta line.
- `creativity=<value>` — echoed only at L3/L4 (omitted at L0/L1/L2).
- `loop` — the loop on the most recent iteration line (`inner`, `refine`, `outer`, `design`, `cot`).
- `k=<N>` — the most recent iteration index.
- `loss=<value>` — the most recent `loss=` value (v0.11.0 field name; old `loss_norm=` is also accepted on read), formatted to 3 decimals.
- `±delta arrow` — per-step Δ with `↓` / `↑` / `→` between last two iterations. Omitted on iter 1.
- `task` — first `task="…"` string found in the trace, truncated to 40 chars.
- `sparkline` — up to the last 30 losses rendered as Unicode blocks `▁▂▃▄▅▆▇█`, auto-scaled to `max(losses)`; zero values render as `·`.
- `trend` — end-to-end first-vs-last arrow (same rule as in `using-ldd` — `↓` if `(last − first) < −0.005`).
- `source` — `.ldd` if data came from `.ldd/trace.log`, `jsonl` if it came from ⟪LDD-TRACE-v1⟫ marker grep. Tells the user which persistence tier is actually feeding the display.

When no trace is active, the statusline distinguishes two states:

```
LDD · idle        # no .ldd/trace.log yet — LDD never used here
LDD · standby     # .ldd/trace.log has prior history, session gate blocks
                  # current session (waiting for fresh `ldd_trace init`)
```

If a heartbeat fired within the last 60s, `· ⚡<age>s <Tool>` is appended to either state so the display still shows the project is live. `standby` answers the common confusion "LDD is installed, I'm actively working — why does it say idle?"; the answer is that skill invocation alone does not register a task, so the session gate cannot permit an active render. Run `./.ldd/ldd_trace init --task "<title>"` to transition from standby to active.

## Why this is safe to auto-install

**The thesis:** silently writing to `.claude/settings.local.json` and `.ldd/` is an acceptable auto-install because both paths are already project-local LDD/Claude-Code territory. `.ldd/` is LDD's own directory; `.claude/settings.local.json` is Claude Code's per-project override file (untracked by default in most repos).

**The antithesis:** (a) the user may have existing `statusLine` config we don't know about; (b) `.claude/settings.local.json` may be in version control and silently changing it leaks into a commit; (c) future Claude-Code versions may extend the statusline schema and a dumb merge could corrupt it.

**The synthesis:** (a) is handled by Step 4 case 4 — user-owned statusline is never overwritten; (b) the user can remove the key at any time; if the skill sees a non-matching command, it leaves it alone forever after; (c) the `jq` merge only writes the minimal `statusLine: {type: "command", command: "..."}` shape required by Claude Code today — any other fields added by future versions would co-exist because `jq '.statusLine = …'` only replaces that subtree, not the rest of the file. If Claude Code ever changes the statusline schema, this skill is updated in one place (template + merge shape).

No write ever touches `~/.claude/`. That is the hard isolation line.

## Anti-patterns

| Red flag thought | Reality |
|---|---|
| "I'll write `~/.claude/settings.json` so the statusline follows the user across projects" | No. LDD is task-level; user-global settings are off-limits. Project-local only. |
| "If `statusLine` already exists with a different command, I'll add mine in an array / subcommand" | No. Claude Code's statusline is a single command. Respect user-owned config and no-op. |
| "I'll probe Claude Code's statusline support by calling an API" | No. Check `~/.claude/projects/` exists; that's the fingerprint. Do not call tools to probe — silent failure. |
| "The statusline should show every iteration's raw loss" | No. One line, 80–120 chars. Sparkline for trajectory; last loss + Δ for the numbers. More → visual noise that scrolls off anyway. |
| "I'll have the statusline re-read the whole JSONL each tick" | Already does — but the tail is O(markers). For a session with 1000 messages and 20 markers this is milliseconds on `jq` + `grep`. If it ever becomes slow, shift to `.ldd/trace.log` primary path; that's 20 lines, constant-time. |
| "If the user's on Codex / Gemini / ChatGPT, show a statusline there too" | No — those hosts have no equivalent API, or a different one. This skill is Claude-Code-only by design; other hosts use the inline trace block from `using-ldd`. Cross-host parity is a future skill. |
| "Re-check / re-install every iteration in case something changed" | No. Sticky per session. The install is idempotent, but running it N times per session is churn. Fire once at first LDD trigger. |

## Interaction with `bootstrap-userspace` and `using-ldd`

`bootstrap-userspace` picks **where** the trace lives (Tier 0–4). `host-statusline` adds a **permanent display surface** for that trace. They are orthogonal:

- If `bootstrap-userspace` picked Tier 0 (`.ldd/trace.log`) → statusline reads the file directly.
- If `bootstrap-userspace` picked Tier 2 (conversation-history with ⟪LDD-TRACE-v1⟫ markers) → statusline greps the session JSONL for those markers.
- Higher tiers (artifact / canvas / memory-pointer) → statusline reads the inline markers anyway, because Claude Code's JSONL *always* contains the assistant's text, and that's where the marker lines were emitted.

`using-ldd` keeps emitting the full trace block in the reply. The statusline is not a replacement for that block — it's a **monitor**. The block is the chart; the statusline is the heartbeat. The user watches both.

## Signal that this skill is working

A session where this skill ran successfully shows:

- After the first LDD trigger in a fresh project: `.ldd/statusline.sh` and a `statusLine` key in `.claude/settings.local.json` exist and reference each other.
- Claude Code's bottom-of-screen status line reads `LDD · <task> · <loop> i<k> · loss <v><Δ> · <sparkline> <trend> · <source>` at all times while LDD is active, and `LDD · idle` / `LDD · standby` (see split above) when no task is registered for the current session.
- The `│ Store :` line inside the trace block has a concise `statusline: …` suffix.
- No user-visible dialog about statusline install (it happens silently).
- User quitting the session → statusline persists (it's saved config). Next `claude` launch in the same project → statusline already live, no re-install needed.

If the statusline shows `LDD · idle` or `LDD · standby` during an actively-running LDD task, the trace file/markers aren't being emitted upstream — `idle` means no trace.log at all, `standby` means trace.log has prior-session content but the session gate blocks because no `ldd_trace init` ran this session. Either way, debug `using-ldd` iteration emission, not this skill.
