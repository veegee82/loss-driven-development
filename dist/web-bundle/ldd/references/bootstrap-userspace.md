---
name: bootstrap-userspace
description: Use at the start of any LDD task when there is no existing `.ldd/trace.log` readable in the working directory — fires before any other LDD skill writes trace state. Detects the host's persistence capabilities (filesystem, artifact/canvas, conversation-history, memory-pointer, inline-only), picks the most durable tier silently without prompting the user, restores any prior trace state it finds, and announces the chosen store in the LDD trace block's `Store :` header line. Makes LDD portable across Claude Code, Claude Desktop, Codex, Gemini CLI, Cursor, ChatGPT, and any other host the LLM can introspect.
---

# Bootstrap-Userspace

## The Metaphor

**The climber without a fixed base camp.** She has arrived on a mountain she has never climbed, and her log book — the one she has carried across a dozen other peaks — has nowhere obvious to sit. She doesn't stop the ascent to ask her sponsor where to pitch a tent. She looks at what the mountain offers (a ledge, a cairn, a radio relay, or nothing at all), picks the most durable surface within reach, and starts writing. The log book format is the same as on every other peak. *What changed is the surface, not the discipline.* Bootstrap-userspace is how LDD finds its surface on an unfamiliar host.

## Overview

LDD's memory — `.ldd/trace.log`, `.ldd/project_memory.json`, `.ldd/cot_memory.json` — assumes a writable project-local filesystem. That assumption is true for CLI-native agents (Claude Code, Codex, Gemini CLI, Cursor, Aider, Copilot CLI) and false for many chat hosts (Claude Desktop without MCP filesystem, ChatGPT web, embedded chat widgets, Custom-GPT-without-Actions).

This skill removes the filesystem assumption. It teaches the agent to **detect the host's persistence surface and pick the most durable tier available — silently, without asking the user** — then behave identically from that point on. Every other LDD skill keeps writing to "the trace," and this skill is what makes "the trace" a working concept regardless of host.

**Core principle:** the user must never have to understand "Tier 0 vs. Tier 2" to get LDD working. The LLM has full read access to its own tool inventory; it can make this choice on the user's behalf and disclose the choice in one line the user already reads (the trace-block header).

## When to Use

Invoke **once per session** as the first thing that happens when:

- The user prefixes a message with `LDD:` or triggers any LDD skill AND
- `using-ldd`, `loop-driven-engineering`, or any iteration-emitting skill is about to append to `.ldd/trace.log` AND
- You have not yet established a trace store for this session

Do **not** invoke when:

- A writable `.ldd/trace.log` already exists in the project root (the implicit Tier 0 path is already active — just use it)
- The task is a trivial one-shot where no trace block would fire anyway (rename, typo, lookup)
- You have already established the trace store earlier in this session (the store choice is sticky per session — do not re-probe on every iteration)

## The Five Tiers

Detection order — **highest-durability-first**. Stop at the first tier whose detection succeeds.

| # | Tier | Primary signal (inspect your own tool inventory) | Scope label (user-visible) |
|---|---|---|---|
| 0 | **Filesystem** | A tool that accepts absolute paths for write AND read (typical names: `Write` + `Read`, `fs_write` + `fs_read`, `filesystem__write_file` MCP), OR an existing `.ldd/trace.log` that you can read | `local (.ldd/trace.log)` |
| 1 | **Artifact / Canvas** | A tool that creates or edits a persistent document surface inside the conversation (typical: `create_artifact` / `update_artifact`, `canvas_create` / `canvas_update`, Claude artifact channel, ChatGPT Canvas) | `canvas 'ldd-trace.log' (this chat only)` |
| 2 | **Conversation-History** | The host preserves the conversation transcript AND the user can (or the platform can) search past messages by literal substring; practically any chat host with chat-history retention qualifies if all other tiers fail | `conversation history (persists per chat)` |
| 3 | **Memory-pointer** | A memory-save tool (`save_memory`, `update_memory`, OpenAI Memory, Claude personal-memory) is available. **Never store trace data here** — only a one-line pointer to where trace data actually lives (e.g. a gist URL the user provided, or the canvas handle from Tier 1) | `memory-pointer → <target>` |
| 4 | **Inline-only** | None of the above detectable | `inline (ephemeral — lost at session end)` |

### Why the order is fixed

Each tier has strictly worse durability than the one above:

- Tier 0 survives everything — process restart, new session, new agent, new host.
- Tier 1 survives conversation reloads but dies with the conversation.
- Tier 2 survives with the conversation only if the platform retains chat history (most do, but not all).
- Tier 3 is user-level not task-level — bleeds across tasks, caps on length, pollutes the user's personal memory. Safe only as a pointer.
- Tier 4 is session-only — the trace block is emitted for the human to see but is lost the moment the session ends.

Picking a lower tier when a higher one is reachable is a silent data-loss decision. Always probe top-down.

## Detection procedure

**Read the tool inventory you were started with.** Every LLM host provides the model with a structured list of available tools at session start — function names, parameter schemas, and descriptions. This list IS the capability fingerprint. You do not need to *try* tools and catch errors; you read the inventory and match tool names against the signals in the table above.

### Tier 0 — Filesystem

Match any of:

- A write-capable tool whose description or schema mentions a filesystem path parameter (e.g. `file_path`, `path`, `absolute_path`)
- An MCP tool whose name starts with `filesystem__` / `fs__` / `mcp__filesystem__`
- An existing non-empty `.ldd/trace.log` in the working directory (even without a visible write tool, if you can read it and the platform supports shelling out, Tier 0 is live)

If matched:

1. Check whether `.ldd/trace.log` already exists in the project root (use `Read` or equivalent).
2. If yes → load its last ~10 entries into working memory; you have just recovered prior state.
3. **Install the launcher** (idempotent) → copy this skill's `ldd_trace` template to `<project>/.ldd/ldd_trace` and `chmod +x` it. The launcher auto-detects the highest-semver LDD plugin cache under `~/.claude/plugins/cache/...` and sets `PYTHONPATH` so `./.ldd/ldd_trace ...` behaves identically to `python -m ldd_trace ...` regardless of CWD or active Python. Without this step the `python -m ldd_trace` invocations below fail with `ModuleNotFoundError: No module named 'ldd_trace'` because the plugin ships the package under `$PLUGIN_ROOT/scripts/` rather than on `sys.path`. If `python -m ldd_trace --help` already succeeds in your shell (e.g. the package is pip-installed), skip this step — the launcher is only a fallback.
4. If no → create `.ldd/` and initialize a fresh `trace.log` via `./.ldd/ldd_trace init --project . --task "<one-line title>" --loops inner,refine,outer` (or `python -m ldd_trace init ...` if the module resolves without the launcher; or the equivalent direct file-write if Python isn't available in this host).
5. Announce in the trace header: `│ Store  : local (.ldd/trace.log)`.

**Invocation contract after step 3:** every `python -m ldd_trace ...` reference in other skills (`using-ldd`, `e2e-driven-iteration`, `dialectical-reasoning`, `define-metric`, `dialectical-cot`) is interchangeable with `./.ldd/ldd_trace ...`. Prefer whichever resolves on this host. Neither form changes the trace output or the stored data — the launcher is a PYTHONPATH shim, nothing else.

### Tier 1 — Artifact / Canvas

Match any of:

- A tool that creates a text artifact / canvas / document inside the conversation with editable content
- Typical names: `create_artifact`, `update_artifact`, `canvas_create`, `canvas_patch`

If matched:

1. Check whether a prior artifact titled exactly `ldd-trace.log` already exists in this conversation. If yes, read it; treat its contents as the trace log.
2. If no, create one with the meta header as the first line:
   ```
   2026-04-22T14:30:00Z  meta  task="<one-line title>"  loops=inner,refine,outer
   ```
3. On each iteration close, append a new line to the artifact (use the host's patch/append tool if available, otherwise re-emit the full artifact with the new line appended).
4. Announce in the trace header: `│ Store  : canvas 'ldd-trace.log' (this chat only)`.

### Tier 2 — Conversation-History

This is the fallback that works on **any** host where chat history is retained. No special tool required — the persistence medium is the conversation transcript itself.

If matched (or if no higher tier is available):

1. Use the magic prefix `⟪LDD-TRACE-v1⟫` on every trace entry you emit. This turns each line into a machine-greppable marker.
2. Emit one magic-prefixed line per iteration close, **inside** or adjacent to the trace block. Format (v0.11.0 — `loss_norm=`/`Δloss_norm=` renamed to `loss=`/`Δloss=`; pre-v0.11.0 lines still ingest correctly):
   ```
   ⟪LDD-TRACE-v1⟫ 2026-04-22T14:30:00Z inner k=3 skill=root-cause-by-layer loss=0.125 raw=1/8 Δloss=-0.250
   ```
3. On next session or after any interrupt, search the current conversation for lines starting with `⟪LDD-TRACE-v1⟫` (use the host's conversation-search tool if present; otherwise ask the user to scroll up and paste the block back in). Reconstruct state from those lines.
4. Announce in the trace header: `│ Store  : conversation history (persists per chat)`.
5. When the user moves to a CLI session with `ldd_trace` installed, `python -m ldd_trace ingest < pasted-chat.txt` promotes Tier 2 entries back to Tier 0 `.ldd/trace.log`.

### Tier 3 — Memory-pointer

Use this tier **only as a supplement** to Tier 1 or Tier 2 — never as primary storage.

If a host memory API is available AND you have established a Tier 1 or Tier 2 store:

1. Save a single pointer line to host memory, e.g.: `ldd-userspace: tier=canvas artifact-id=abc123 task="fix JSON parser"`.
2. On next session (new chat, same user), read the memory pointer first to instantly know where the previous trace lives.
3. Announce in the trace header: `│ Store  : canvas 'ldd-trace.log' (memory-pointer pin)`.

**Anti-pattern — never do this:** saving `loss=0.375 raw=3/8 skill=…` lines (or legacy `loss_norm=…` lines) directly into the host's memory API. That would pollute the user's personal memory with task-level data, which bleeds across unrelated tasks and eventually hits the memory-length cap. Memory is user-level; the trace is task-level; they must not share a container.

### Tier 4 — Inline-only

If no tier above is reachable, degrade gracefully:

1. Emit the trace block in every reply.
2. The block is ephemeral — announce this explicitly in the header: `│ Store  : inline (ephemeral — lost at session end)`.
3. If iteration count exceeds 5, suggest once (not repeatedly) that the user either pastes the trace block into a persistent note, or moves to a CLI agent for cross-session continuity. One suggestion per session, not per iteration.

## The transparency rule

Every trace block emitted in a session where this skill ran MUST carry one additional header line **before** the `Task :` line:

```
│ Store  : <scope label from the table above>
```

This is the **only** user-visible disclosure of the tier choice. It is:

- **One line**, not a dialog
- **Always present** (even on Tier 0 — the user may want to know their trace is local)
- **Truthful** — if the chosen store is ephemeral, the line says so

No other prose ("I've chosen to store your trace in…", "To save your progress, please…") should appear in the agent's reply. The user does not need a lecture. They need one line of status they can glance at.

## Self-recovery on new session

At session start, when you would otherwise run this bootstrap fresh, try to recover prior state first:

1. **Tier 0 check** — does `.ldd/trace.log` exist in the working directory? If yes, use it; no bootstrap needed. Done.
2. **Tier 3 check** — is there a memory pointer like `ldd-userspace: tier=canvas artifact-id=…` in host memory? If yes, follow the pointer (open the canvas / read the artifact) and restore from there.
3. **Tier 2 check** — does this conversation's history contain any `⟪LDD-TRACE-v1⟫` lines? If yes, parse them and restore.
4. **Tier 1 check** — is there an artifact titled `ldd-trace.log` attached to this conversation? If yes, read it.

Only after all four recovery paths return empty do you run fresh detection and start a new trace store.

### Auto-opt-in (Tier 0 on Claude Code)

On Claude Code, this skill does **not** have to do the Tier 0 install by hand — the plugin's SessionStart hook (`hooks/ldd_install.sh`) handles it for three opt-in cases:

- Signal A — `.ldd/` already exists.
- Signal B — `$cwd/.claude-plugin/plugin.json` exists and names `loss-driven-development` (the plugin's own source repo).
- Signal C — user-global opt-in (`LDD_AUTO_OPTIN=1` or `~/.claude/settings.json` key `ldd.auto_install: true`).

Any of the three and the hook creates `.ldd/`, drops the `ldd_trace` launcher + statusline + PreToolUse/Stop hooks, and merges `.claude/settings.local.json` — all before this skill sees its first invocation. The skill's filesystem-tier detection then finds Tier 0 ready-to-use and the "has no `.ldd/` yet" branch becomes a fallback for non-Claude-Code hosts (Codex, Gemini CLI, Cursor, Aider) where no SessionStart hook is wired.

## Anti-patterns

| Red flag thought | Reality |
|---|---|
| "This host has no filesystem, so LDD won't work — I'll skip trace persistence" | No. Fall through to Tier 1 → 2 → 3 → 4. The discipline is the value; the store is the substrate. |
| "The user hasn't configured anything, I should ask them where to store" | No. Silent auto-pick is the design. The user does not know and should not have to know. |
| "I'll save the trace lines into OpenAI Memory / Claude Memory so they persist across chats" | No. Memory API is for user-level data, not task-level append logs. Tier 3 holds only pointers. |
| "The canvas might get deleted by the user — I'll store in memory as backup" | No. Do not double-store. If the canvas is gone, reprobe at next iteration and announce the new tier. Duplicating invites split-brain. |
| "I'll probe every tool by calling it and catching errors" | No. Inspect the tool inventory statically. Failed tool calls produce noisy error messages the user sees. |
| "I'll emit the ⟪LDD-TRACE-v1⟫ header only when on Tier 2" | Also emit it on Tier 0 as a comment inside trace.log entries? No — Tier 0 already has its own serialization format. The magic prefix is specifically for hosts where the only persistence is chat-text grep. |
| "If the task is small, I'll skip the `Store :` header line" | No. Presence of the line is load-bearing for audit. Its absence means "LDD isn't actually persisting anything," which is sometimes true but should always be declared. |
| "The tier choice should be re-made every iteration in case the host changes" | No. Sticky per session. Host capabilities don't change mid-conversation. Re-probing is churn. |

## Interaction with `using-ldd`

`using-ldd` §"Persisted trace at `.ldd/trace.log` — bidirectional" previously said:

> **If `.ldd/` cannot be written** (read-only filesystem, no project root), skip the persistence but still emit the inline block.

This skill **replaces** that fallback. When `.ldd/` is not writable, `using-ldd` delegates to `bootstrap-userspace`, which picks the most durable alternative tier. The inline-only degradation (Tier 4) remains as the final fallback, but is no longer the first response to a missing filesystem.

## Signal that this skill is working

A session with this skill correctly applied shows:

- Exactly one `│ Store  : <scope>` line inside every trace block
- No user-visible dialog about storage choice
- Trace state survives across iterations within a session on every tier (including Tier 4 — the block is re-emitted with all prior iterations each time)
- When the user starts a new session on the same host and the same task, the prior iterations are recovered automatically (Tier 0/1/2/3) or the session explicitly starts fresh (Tier 4, with an honest header that the previous trace was ephemeral)
- On a cross-host migration (user moves from ChatGPT → Claude Code on the same task), the `⟪LDD-TRACE-v1⟫` lines from the old chat can be pasted into `python -m ldd_trace ingest` and the trace continues from where it left off

If a trace block is emitted without a `Store :` header line, this skill did not run — rerun it.
