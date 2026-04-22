# Changelog

All notable changes to this plugin are documented here. Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/). This project uses [Semantic Versioning](https://semver.org/).

## [0.14.0] — 2026-04-23

### Fixed — statusline stuck at `LDD · standby` when skills fire but task lifecycle doesn't

The `a44d634` split of `idle` / `standby` (v0.13.0) explicitly acknowledged a Layer-3 residue: "there is still no lightweight mechanism to auto-mark session active when an LDD skill is invoked without a full task lifecycle." In practice this meant any session where the agent used LDD via chat content (skill invocations + inline trace-block emission) without running `ldd_trace init` left `.ldd/sessions/<sid>` absent, the session gate correctly blocked, and the statusline read `LDD · standby` despite visible activity. Particularly jarring after v0.13.1's `using-ldd` change made inline trace-block emission the primary user-visible channel — agents now emit blocks without always running the tool.

Fix lives in two places:

- **`skills/host-statusline/heartbeat.sh` (`LDD_HEARTBEAT_HOOK_v2` → `v3`)** — the PreToolUse heartbeat now seeds `.ldd/sessions/<sid>` (and legacy `.ldd/session_active`) with a minimal `session_id=<sid>` marker when no marker exists for the current session. Semantics shift: the session marker now means "a Claude-Code tool fired in this LDD project" rather than strictly "the LDD task lifecycle ran." A later `ldd_trace init` still overwrites the seed with the real `task=` pointer; existing markers that already carry `task=` are preserved untouched (idempotent). Case-analysis matrix — fresh-session / marker-with-task / legacy-fallback — covered by the new `M6a/b/c` tests in `tests/hooks/test_multi_session.sh`.
- **`hooks/ldd_install.sh`** — the install script's `patch_skip` path used to ignore byte-diffs on hook/launcher files (to avoid re-install churn during dev iterations). That swallowed marker-version bumps silently, so a v0.14.0-aware installer that encountered a v0.13.1 `ldd_heartbeat.sh` would skip the update. New per-file marker-version gate compares the destination's `LDD_*_HOOK_v<n>` header token to the template's; a mismatch treats the file as missing and forces re-install even under patch_skip. This makes future hook-semantic bumps reach existing installs without a minor-version nudge.

Downstream behaviour change: on a project whose `.ldd/trace.log` carries prior-session entries, the statusline now renders those entries' last task after the next tool fire, rather than `standby`. If the project has no trace history at all, `LDD · idle` is unchanged.

### Added — compact inline trace format (default per-iteration)

The full 15–25-line trace block is token-expensive when emitted per iteration. A 5-iteration task previously spent ~100–125 lines of visible trace just for live progress signalling — before the Close section even landed. v0.14.0 introduces a **compact inline format** as the new default for per-iteration emission:

```
LDD i2/inner · loss=0.375 (3/8) Δ−0.125 ↓ · root-cause-by-layer
     → L4 (contract): filter ignores None; L5 (concept): implicit total-function assumption
```

- **2 lines** for `i1` and `i2` (no trajectory history yet)
- **3 lines** from `i3` onward (sparkline suffix + net-trend arrow appear once ≥ 3 data points exist)
- **Full block** still emitted at task close, on explicit `/ldd-trace` request, and for post-hoc reconstruction

Load-bearing audit signals are preserved — iteration counter / loop label / normalized-loss / raw-violations / per-step Δ with arrow / sparkline from i3 / skill name / one-line concrete action. The behavioral-fixture rubric for `using-ldd-trace-visualization` is unaffected because all three fixture scenarios are post-hoc (fall under the full-block trigger per the spec).

Spec lives in `skills/using-ldd/SKILL.md` § "Compact inline format (default per-iteration, v0.14.0+)". The existing "full trace block" section is renamed and clarified to apply to close / request / post-hoc only. RED FLAGS table extended with the "compact means I can drop the action line" case — action lines are load-bearing regardless of format.

Token saving at steady state: ≈ 1/8 the per-iteration cost, with no audit-surface loss.

## [0.13.1] — 2026-04-22

### Fixed — inline trace-block emission was ambiguous in using-ldd

`skills/using-ldd/SKILL.md` mandated "emit the trace block inline in your reply" AND documented the tool path "running `ldd_trace append` IS the per-iteration emission" — but the two statements together confused agents: Bash stdout is not part of the user-visible transcript unless the assistant explicitly surfaces it, yet the skill never said that. The in-repo `.ldd/config.yaml` sets `display.verbosity=off` to avoid duplicate rendering, which left users with **no** inline trace block in many sessions.

Fix: new `### HOW to emit — the inline block is the user-visible channel` subsection inside "When to emit". It makes the dual-channel rule explicit:

1. **Primary user-visible channel** — render the full trace block as plain ASCII text *in the assistant's reply text*. This is what the user sees in the transcript. Bash stdout is NOT a substitute.
2. **Persistence side-channel** — `ldd_trace append` writes to `.ldd/trace.log` (or the active bootstrap-userspace tier). Its stdout is optional visual confirmation for the agent; the inline block must still be in the reply.

Plus a concrete decision table for every combination of filesystem-available / tier-downgraded / tool-unavailable / user-opt-out, and two named anti-patterns (`"the Stop-hook will render it"`, `"I invoked the tool, that counts"`).

### Added — dispatch precedence when multiple trigger-table rows match

Pre-0.13.1, a message like `"bug: I've tried this 3 times"` matched both the generic `"bug"` row (→ `root-cause-by-layer`) and the specific `"I've tried this 3 times"` row (→ `loss-backprop-lens`). The skill text said nothing about precedence, so different agents dispatched differently on the same input.

`skills/using-ldd/SKILL.md` now carries a `### Precedence when multiple rows match` subsection that enforces two rules: **specificity wins** (longer / more literal triggers beat generic ones), and **table order is the tiebreaker** (upper rows first). Plus a mutual-exclusion clause: once `root-cause-by-layer` closes with a named origin, `loss-backprop-lens` cannot re-invoke on the same error (and vice versa) — preventing the ping-pong oscillation the v0.13.0 audit flagged.

### Added — concrete K_MAX=5 escalation template in loop-driven-engineering

The old `loop-driven-engineering` K_MAX-hit instruction ended at "A proposed architectural step (via loss-backprop-lens: 'the learning rate needs to be bigger')" — but `loss-backprop-lens` is diagnostic, not designer. Agents hitting K_MAX produced vague escalations like "redesign module X" that blocked human review.

Fix: `### Hard rule` now names a 5-item escalation artifact — per-iteration log, verbatim failure signal, layer-4/5 diagnosis, **one-sentence concrete architectural proposal with specific identifiers** (file paths, class names, R-rules), and an explicit user ask. Escalations without the concrete-identifier sentence get returned; the task is `architect-mode`-ready, not human-ready.

### Added — `scripts/check-skill-frontmatter.py` + CI step

Every `skills/*/SKILL.md` has a YAML frontmatter block (`name`, `description`); a malformed one silently drops the skill from Claude Code's registry or breaks Gemini CLI's `@`-import. Pre-0.13.1 had zero validation of this layer.

New `scripts/check-skill-frontmatter.py` walks `skills/*/SKILL.md`, validates the `---`-delimited block, requires non-empty `name` and `description`, asserts `name` matches the containing directory, and rejects descriptions shorter than 40 chars (too short to feed Claude Code's auto-dispatch matcher). Wired into `.github/workflows/install-hooks-check.yml` as a new `SKILL.md frontmatter validation` step; broader `skills/**` path filter so any SKILL.md edit triggers the lint.

Current run: 16/16 SKILL.md files pass.

### Fixed — `check-plugin-versions.sh` only checked 2 of 3 manifests

The v0.13.0 drift gate verified `plugin.json` against `marketplace.json` but did not include `gemini-extension.json` — which is exactly how that file was left at `0.11.0` while the other two climbed to `0.13.0`. Gemini CLI users installing during that window received the stale version with no visible warning.

Fix: `scripts/check-plugin-versions.sh` now verifies all three manifests in one pass and names each in the failure message with a sync-fix `jq` snippet. The pre-commit hook and CI job already call this script, so the expanded check lights up everywhere automatically.

### Fixed — `gemini-extension.json` stuck at 0.11.0 → bumped to 0.13.1

Silent version drift. Gemini CLI `extensions install ./loss-driven-development` reported 0.11.0 for two release cycles. Caught by the expanded drift gate above.

### Fixed — `SUBMISSION.md` pre-submit checklist still claimed 0.5.0

Lines 121 / 124 / 130 / 136 claimed version `0.5.0`, "v0.1.0 through v0.5.0 entries", and "all three manifests at 0.5.0" — wrong since every release after v0.5.0. Rewrote to current state: v0.13.1, skill-count composition (12 disciplines + 4 infrastructure = 16), and explicit mention of the Δloss_bundle citation gate + web-bundle distribution.

### Fixed — `README.md` web-bundle skill count off by one

README said "the other 13 skills become references" in the Claude Web / Desktop install section. Actual bundle carries 14 references (16 total skills, minus `using-ldd` which becomes the bundle's `SKILL.md` dispatcher, minus `host-statusline` which is Claude-Code-specific). Corrected to 14 with a parenthetical naming the excluded skill.

### Fixed — `GEMINI.md` missing `host-statusline` `@`-import

14 of 15 non-dispatcher skills imported; `host-statusline` was missing. Gemini CLI users got the full loss-monitoring discipline silently dropped. Fixed by appending the `@./skills/host-statusline/SKILL.md` line.

### Changed — `plugin.json` / `marketplace.json` description names all 16 skills

The old description said "Twelve portable skills … Plus one opt-in architect-mode and the using-ldd entry-point" — 12 + 2 = 14, not the 16 skills actually shipped. Readers could not reconcile "twelve skills" with the 16 directories under `skills/`. The description now reads "Twelve discipline skills across four parameter spaces … Plus four infrastructure skills: using-ldd dispatcher, opt-in architect-mode, bootstrap-userspace, host-statusline. Total 16 skills."

### Fixed — renderer scoped to current task (trace.log with multiple tasks)

`TraceStore.to_task()` took the FIRST `meta` line from `trace.log` and aggregated every iteration across every task ever run in the project. After one or more `init → append → close` cycles followed by a fresh `init`, the stop-hook summary kept showing the ORIGINAL task's title as `(complete)` plus the combined iteration count across all tasks — e.g. `Task: diagnose + fix ldd statusline idle-state (complete) · Loops: inner×10` long after that task closed and a new one started.

Fix: new `TraceStore.current_task_entries()` returns everything from the LAST `meta` line onwards. `to_task()`, `next_k()`, and the `close_entries` projection all use it, so the summary reflects the active task's iterations only. Historical entries stay in `trace.log` for `ingest` / `aggregate` — they just no longer pollute the current render.

Same scoping guarantees that `ldd_trace append --auto-k` restarts at `k=0` after every `init`, instead of inheriting the max-k of the prior task on disk.

### Added — multi-clauding (concurrent Claude Code sessions on one project)

LDD now isolates session-scoped state so two or more Claude Code sessions running in the same project at the same time each see their own task, their own heartbeat, and their own statusline — without one winning a singular marker and evicting the other to `standby`.

Four concrete race-paths were identified in v0.13.0 and closed:

1. **`.ldd/heartbeat`** (singular file, last-writer-wins) → **`.ldd/heartbeats/<session_id>`** (per-session file, atomic rename). Heartbeat hook writes the new per-session file AND the legacy singular so v0.13.0-era statusline copies still render correctly. Atomic rename (`tmp + mv`) protects against torn reads from concurrent statusline ticks.

2. **`.ldd/session_active`** (singular, 1 id fits) → **`.ldd/sessions/<session_id>`** (per-session marker file). Gate check becomes existence-of-file instead of equality-against-singular, so every active session passes its own gate independently. The per-session marker also carries `task=<title>` (written by `ldd_trace init`) so the statusline displays THIS session's task — shared `trace.log` notwithstanding.

3. **`ldd_trace init` from two sessions in parallel** → both now call `mark_session_active(project, task_title=...)` which writes the per-session marker with the correct task title; the append/close path passes `task_title=None` and preserves the previously-written line. Each session's statusline reads `task=` from its own marker, bypassing the shared-trace ambiguity.

4. **Installer `settings.local.json` merge race** (read-modify-write via jq) → wrapped in `flock -w 5` on `.claude/.ldd_install.lock` so parallel SessionStart hooks serialise the critical section. On macOS without `util-linux` `flock`, the historical jq-dedup fallback still keeps the merge idempotent in the common case.

**Backwards compatibility:** every pre-v0.13.1 project keeps working. The session_gate falls back to the legacy singular `.ldd/session_active` when no per-session marker is present; the statusline reads the per-session heartbeat first and the legacy singular second. No migration is required on upgrade — the first `ldd_trace init` after the install writes both new and old layouts, and the old layout stops being authoritative from then on.

### Added — multi-session E2E test suite

`tests/hooks/test_multi_session.sh` — 5 cases that ship a regression baseline for this class of bug:

- M1: parallel installers → settings.local.json stays single-copy
- M2: parallel heartbeats → both session_ids observable independently
- M3: parallel `ldd_trace init` → both per-session markers exist concurrently
- M4: per-session statusline render → A sees taskA, B sees taskB (no `standby` due to gate-loss)
- M5: 20 concurrent `ldd_trace append` calls → no corrupted trace.log lines

Wired into `.github/workflows/install-hooks-check.yml`, now running 5 jobs × (Ubuntu + macOS) = 10 gates per PR touching installer / launcher / session_gate / statusline.

### Fixed — three silent-failure modes in the SessionStart install hook

Three pre-v0.13.1 defects could leave a newly-installed plugin looking healthy while actually being half-broken, with no visible signal to the user.

1. **Missing `jq` silently corrupted the install.** The installer used `jq` for every `settings.local.json` write but had no preflight check. Without `jq` the script ran `set -uo pipefail` (without `-e`), installed the script artifacts, wrote `.ldd/.install_version`, and left `.claude/settings.local.json` as `{}`. Every subsequent SessionStart saw "marker matches plugin version, artifacts present" → `exit 0` silently, forever. User had no statusline, no heartbeat, no stop-render — with no error message.

   Fix: add a `command -v jq` preflight at the top of `hooks/ldd_install.sh`. If `jq` is missing, emit a SessionStart `additionalContext` hint naming the install command for each platform (`apt install jq`, `brew install jq`, `winget install jqlang.jq`) and exit 0 **without** writing the marker. Next SessionStart retries automatically once `jq` is available.

2. **Launcher hard-wired to `python3`.** `skills/bootstrap-userspace/ldd_trace` did `exec python3 -m ldd_trace`, which fails on macOS systems where the binary is called `python` (pointing at Python 3), on venv-activated shells where only a custom interpreter path is meaningful, and on any minimal image without `python3` in PATH — producing a cryptic `command not found: python3` instead of an actionable message.

   Fix: resolve the interpreter in order `$LDD_PYTHON` → `python3` → `python`, accepting only those where `sys.version_info >= (3, 8)`. On zero hits the launcher prints a named-candidate error and exits 127.

3. **Fresh-install reload instruction was a conditional footnote.** Hooks registered on SessionStart cannot fire in the same session — Claude Code reads `settings.local.json` before the hook runs. The installer message said "Reload the Claude Code session if hooks do not fire yet" as the last clause of a paragraph, easy to miss. Users routinely reported "statusline works but no heartbeats" for hours.

   Fix: fresh installs get a prominent `⚠ Please reload (/ restart) the Claude Code session now — PreToolUse and Stop hooks were just registered and will not fire until Claude Code re-reads .claude/settings.local.json`. Updates (where hooks are already live) keep the subdued phrasing.

### Added — plugin-version drift gate

`scripts/check-plugin-versions.sh` asserts that `.claude-plugin/plugin.json` and `.claude-plugin/marketplace.json` agree on `.version`. The SessionStart installer reads `plugin.json`; Claude Code's `/plugin install` UI reads `marketplace.json` — drift means users see one version but receive another. Wired into:
- `.githooks/pre-commit` — fails any commit that stages either file out of sync (with the fix-hint jq invocation inline).
- `.github/workflows/install-hooks-check.yml` — a new matrixed (Ubuntu + macOS) CI job that runs the full hook test suite on every PR touching the installer, launcher, templates, or version files.

### Added — E2E test suite for hooks + launcher

Three new test files under `tests/hooks/`, all runnable as plain `bash tests/hooks/*.sh`:
- `test_install_preflight.sh` — 5 cases: jq-missing abort, fresh-install artifacts + marker + prominent reload, update-path subdued reload + version-arrow, merge preserves user `statusLine` + user hooks, jq-rescue retry.
- `test_launcher_python.sh` — 4 cases: `python3` happy path, `python` fallback, no-Python actionable error, `$LDD_PYTHON` override.
- `test_version_sync.sh` — 3 cases: committed state in sync, synthetic drift caught with both versions named in the fix hint, `jq`-missing loud fail.

Current coverage: 19/19 green on Ubuntu. macOS covered via the CI matrix.

### Fixed — marketplace.json version was stale (0.11.0) vs plugin.json (0.13.0)

The commit that bumped `plugin.json` to 0.13.0 didn't update `marketplace.json`, so anyone running `/plugin install loss-driven-development@loss-driven-development` saw "0.11.0 installed" in the UI while the SessionStart hook correctly installed 0.13.0 artifacts. Synced to 0.13.0; the new pre-commit + CI gates now prevent this class of drift from recurring.

## [0.13.0] — 2026-04-22

### Changed — statusline idle-branch split into `idle` / `standby`

Prior versions collapsed three cognitively distinct states into a single `LDD · idle` label:

1. No `.ldd/trace.log` at all (LDD never used in this project)
2. `.ldd/trace.log` is empty (installed but never written)
3. `.ldd/trace.log` has prior-session history, current session's gate blocks (installed, previously used, just no `ldd_trace init` yet this session)

From 0.13.0 onward the idle-branch distinguishes (1) / (2) from (3):

```
LDD · idle                 # cases 1 and 2 — unchanged
LDD · standby · ⚡12s Bash  # case 3 — new
```

Answers the common "LDD is installed, I'm actively working — why does it say idle?" confusion: skill invocation alone does not register a task; the session gate correctly blocks the active render until `ldd_trace init` runs. The new `standby` label makes the distinction visible.

Scope is deliberately narrow — only the display vocabulary changed. The session_gate / heartbeat / stop-hook plumbing is unchanged; no new hook, no new marker file, no new config knob. The fix is one `[[ -s "$trace_file" ]]` check in `skills/host-statusline/statusline.sh`'s idle-branch.

Structural origin: Layer-4 (display-vocabulary too coarse) with an acknowledged Layer-3 residue — there is still no lightweight way to auto-mark session active when an LDD skill is invoked without a full task lifecycle. That residue is a future refinement; `standby` is the minimum-surface honest signal in the meantime.

### Added — `install.auto_update` opt-out in `.ldd/config.yaml`

Security-conscious users can fully disable the SessionStart auto-install:

```yaml
install:
  auto_update: false    # default: true
```

When `false`, the hook exits silently on **every** version transition — N-bumps, I-bumps, and missing-artifact gaps included. The user then controls the update pace entirely via `/ldd-install` (which sets `LDD_FORCE_INSTALL=1` and always installs).

Default remains `true` — upgrades Just Work for users who do not touch the config. The config key lives in the freshly-seeded `config.yaml.default` template and is documented inline.

Parser is bash-native (awk one-liner on the `install:` block), same discipline as `display:` reads in `scripts/ldd_trace/session_gate.py` — no PyYAML dep added.

### Changed — SemVer-aware auto-update policy in SessionStart install hook

Plugin versions follow `I.N.M` (major.minor.patch). From 0.13.0 onward the SessionStart install hook applies a three-way policy:

| Transition | Auto-install on SessionStart? |
|---|---|
| Exact same version | no-op |
| `M`-only bump (e.g. `0.13.3 → 0.13.4`) | **skip** — treated as dev iteration |
| `N` or `I` bump (e.g. `0.13.4 → 0.14.0`, `0.14.0 → 1.0.0`) | install |
| Any missing artifact | install (fills the gap regardless of diff class) |

Rationale: maintainers publish patch-level commits to `main` many times a day. Before 0.13.0, every such commit churned the user's `.ldd/` artifacts on the next session, which made ongoing dev work visible to users who had not opted in to it. The M-dimension is now reserved for the maintainer's own workflow; the N-dimension is the release channel.

Escape hatch: `LDD_FORCE_INSTALL=1` in the hook's environment bypasses the M-skip. The `/ldd-install` slash command sets this automatically — a user running `/ldd-install` is explicitly asking for the latest artifacts and should always get them.

Implementation: the install hook gains a `parse_version` helper (regex-tolerant to `-pre` / `+build` suffixes) and splits the idempotency check into `up_to_date` (exact match + bytes same), `patch_skip` (I.N matches, M differs), and `any_missing` (at least one artifact absent). Decision matrix documented inline in `hooks/ldd_install.sh`.

Backwards compatibility: the `.install_version` marker file format is unchanged — old v0.10.3 / v0.11.0 markers continue to parse as I.N.M (they always were). Users upgrading from any pre-0.13 version see a one-time install as `old_version → 0.13.0` (N-bump = install), after which M-bumps within the 0.13 release line stay local to the maintainer.

## [0.12.0] — 2026-04-22

### Added — per-project display config + activity-gated Stop-hook

New `.ldd/config.yaml` with a `display:` section controls what the Stop-hook renders at the end of each agent turn. Two knobs:

- **`verbosity`** — one of `off | summary | full | debug`.
    - `summary` (new default) emits a 5-7 line digest: task, loops touched, loss trajectory + sparkline, close verdict. Full trace stays reachable via `/ldd-trace` or `ldd_trace render --verbosity full`.
    - `full` restores the pre-v0.12  30+ line block.
    - `off` silences the hook entirely; statusline remains the live monitor.
- **`gate_on_activity`** — default `true`; the Stop-hook only emits a block when LDD actually fired in this session. `.ldd/session_active` (written by `ldd_trace init|append|close`) is compared against the hook's `session_id`; mismatch → no render.

The installer (`ldd_install.sh`) seeds `config.yaml` on **first** install only — an edited config is never overwritten on upgrade. Seed template lives at `skills/host-statusline/config.yaml.default` and is documented inline.

Precedence for `verbosity`: `LDD[verbosity=…]:` inline → `$LDD_VERBOSITY` → `display.verbosity` → `summary` (hook) / `full` (plain CLI) defaults.

### Added — statusline no longer shows stale state across runs / sessions

Three longstanding bugs in `skills/host-statusline/statusline.sh` that together caused the bottom-of-screen monitor to display info from a previous LDD run:

1. **Cross-task contamination**: the task-title grep used `grep -m1` (first match = oldest task in the append-only log), and `losses | tail -30` mixed loss values across all historical tasks. The sparkline and trend arrow were therefore computed over iterations that belonged to different runs.
2. **Post-close live-marker**: after `ldd_trace close` wrote a terminal line, the statusline continued to render `<loop> k=N/K_MAX` as if the run were still progressing.
3. **Session-stale state**: opening a new Claude-Code session in the same project showed the last session's closed task for hours, with no way to distinguish it from a live run.

Fix:

- `awk`-scoped parse extracts only the lines from the **last** `meta` line onward, so every read (task title, losses, meta line, last iter line) operates on the current task's section alone.
- When a `close` line exists and is the last content line of the current section, the loop label is replaced with `✓ complete` / `⚠ partial` / `✗ failed` / `✗ aborted` / `→ handoff`, and the `k=N/K_MAX` suffix is dropped.
- Session-ID gate (same policy as the Stop-hook): `.ldd/session_active` is compared against the `session_id` in the statusline's JSON input; mismatch → `LDD · idle`. Empty marker on either side falls through to "allow" so plain-shell / test-harness use is not blocked.

### Added — `.ldd/heartbeat` carries session_id in third column

`skills/host-statusline/heartbeat.sh` now writes `<epoch> <tool> <session_id>` on every PreToolUse event. This is the single source of truth for the current Claude-Code session id inside the project (Claude Code does not expose `$CLAUDE_SESSION_ID` as a shell env var), and `ldd_trace init|append|close` reads it to populate `.ldd/session_active`. Pre-v0.12 readers parse only `$1`/`$2`, so the extra column is backwards-compatible.

### Added — `render_summary()` + `render(task, verbosity)` dispatcher

`scripts/ldd_trace/renderer.py` gains a compact `render_summary()` (5-7 lines: header, one-line loop-count digest, loss trajectory with sparkline, layer/docs/terminal) and a `render(task, verbosity)` dispatcher. `render_trace()` itself is unchanged — the full block renders byte-identical to v0.11 when `verbosity=full`.

### Added — plugin-level auto-install on SessionStart + `/ldd-install`

The plugin now ships `hooks/hooks.json` which registers a SessionStart hook running `hooks/ldd_install.sh`. Claude Code merges plugin-level hooks into the user's hook registry on plugin load, so **no manual install step is needed after plugin install or update** — the installer runs at the next SessionStart.

The installer is:

- **Gated on opt-in**: skips projects that don't have `.ldd/`. First-time opt-in via the new `/ldd-install` slash command (creates `.ldd/` then runs the installer) or via `bootstrap-userspace` on first LDD skill invocation.
- **Idempotent**: compares plugin version (`plugin.json`) against `.ldd/.install_version` marker AND all installed artifacts' byte-for-byte contents; if everything matches, exits silently (empty JSON).
- **Version-gated update**: on plugin upgrade, version-marker mismatch triggers full re-install of all four artifacts (`.ldd/ldd_trace` launcher, `.ldd/statusline.sh`, `.claude/hooks/ldd_heartbeat.sh`, `.claude/hooks/ldd_stop_render.sh`).
- **Safe settings merge**: `.claude/settings.local.json` is touched via `jq` with de-duplication by endpoint path, so LDD's `PreToolUse` (heartbeat) and `Stop` (render) entries are added or refreshed without clobbering the user's other hooks, other plugins' hooks, or any custom `statusLine` / `permissions` fields.
- **Self-reporting**: emits a SessionStart `additionalContext` message naming the artifacts and (on upgrade) the `old_version → new_version` transition. Silent when no-op.

### Added — Stop-event hook renders trace block as last chat artifact

`skills/host-statusline/stop_render.sh` is a new Stop-event hook that reads `.ldd/trace.log` via `./.ldd/ldd_trace render` and returns the framed trace block through `hookSpecificOutput.additionalContext`, so Claude Code displays it **below** the agent's last message — not only embedded inside a `Bash` tool result. Installed automatically by `ldd_install.sh`. Closes the layout-contract gap where `ldd_trace close` output was buried inside the worker/tool surface instead of appearing as the final chat-level artifact of the turn.

### Added — `/ldd-install` slash command

Explicit opt-in / re-install command; creates `.ldd/` if missing and runs the plugin installer. Document-only step — described in `commands/ldd-install.md`. Useful for first-time setup in a project or after any manual `.ldd/` wipe.

### Added — statusline budget-burn + plateau/regression warnings

The `host-statusline` template gains three trailing segments so the user can see loop state at a glance without opening `trace.log`:

- **`k=N/K_MAX`** replaces the bare `iN` label. `K_MAX` comes from `$LDD_K_MAX` (default `5` per `loop-driven-engineering`). Closes the "how close am I to escalation" blind spot.
- **Elapsed label** (`43s` / `12m` / `1h5m` / `3d`) — wall time from the latest `meta` line to the latest iter line.
- **`⚠ plateau`** fires when the last 2 `|Δloss|` are each `< 0.015` with ≥ 3 samples; **`⚠ regression`** fires when `loss − prev > 0.005` with ≥ 2 samples. Gated on sample count so a fresh task with one baseline doesn't false-positive.

Thresholds use `< 0.015` rather than `<= 0.01` to absorb IEEE-754 drift on subtractions like `0.45 − 0.44` = `0.01000000000000000888`.

Backwards-compatible: old trace lines render in the same format; no existing entries or downstream tooling (aggregator, renderer, close block) reads the new labels.

### Fixed — `last_line` regex matched `close` lines, breaking `iN`

The `last_line` filter previously required `\s+k=` directly after the loop name, which failed on `baseline` iters (written as `inner  baseline  k=0  …`). The fix pipes through a secondary `grep ' k=[0-9]+'` so both `baseline` and regular iter lines match while the `close` line (`terminal=…`, no `k=`) is still excluded.

### Added — `bootstrap-userspace` ships the `ldd_trace` launcher

Tier-0 bootstrap now drops `.ldd/ldd_trace` — a Bash launcher that auto-detects the highest-semver LDD plugin cache and execs `python3 -m ldd_trace` with `PYTHONPATH` set. Before this, every skill doc reference to `python -m ldd_trace …` failed silently with `ModuleNotFoundError` because the plugin ships the `ldd_trace` package under `$PLUGIN/scripts/`, not on `sys.path`. Skill docs that reference `python -m ldd_trace …` remain valid; the new `./.ldd/ldd_trace …` form is an equivalent fallback.

## [0.11.0] — 2026-04-22

### ⚠ BREAKING — dispatch header + trace log format + override syntax

Spec: [`docs/superpowers/specs/2026-04-22-level-name-consolidation.md`](./docs/superpowers/specs/2026-04-22-level-name-consolidation.md).

Mode is a pure function of level (L0–L2 ⇒ reactive, L3/L4 ⇒ architect) and was carrying ~60 redundant characters per trace line plus a second dispatch-header line. v0.11.0 consolidates the display: level gains a canonical name (`L0/reflex` … `L4/method`), creativity stays as a real orthogonal axis at L3/L4, and `mode` is removed as a displayed/user-facing concept.

**Scorer behavior, weights, thresholds, loop budgets, skill floors — unchanged.** This is a display + storage consolidation only.

**Removed from the dispatch header:**

- The second line `mode: architect, creativity: <value>` — deleted unconditionally.
- The word `auto-level` on auto-dispatches — the auto case is now implicit (no dispatch-source keyword appears).
- The parenthetical `(creativity=standard)` inside the clamp bracket — creativity is echoed once inline, not duplicated in the clamp reason.

**New dispatch-header format (single line):**

```
Dispatched: L<n>/<name> (signals: <sig1>=<±N>, <sig2>=<±N>)
Dispatched: L<n>/<name> · creativity=<value> (signals: ...)
Dispatched: L<n>/<name> · creativity=<value> (signals: ...) [clamped from L4]
Dispatched: L<n>/<name> · creativity=<value> (user-explicit; scorer proposed L<m>)
Dispatched: L<n>/<name> (user-bump from L<m>, fragment: "<fragment>")
Dispatched: L<n>/<name> · creativity=<value> (user-override-down from L<m>). User accepts loss risk.
```

`· creativity=<value>` is emitted only at L3/L4. The level is always rendered with its canonical name.

**New trace-log meta line format:**

```
2026-04-22T02:24:45Z  meta  L4/method  creativity=inventive  dispatch=auto  task="…"  loops=design,cot,inner,refine,outer
```

Canonical field order: positional `L<n>/<name>`, then `creativity=<value>` (only at L3/L4), then `dispatch=<auto|explicit|bump|override-down>`, then `task="…"`, then `loops=…`.

**New trace-log per-iter line format:**

```
2026-04-22T02:24:45Z  design  k=0  skill=architect-mode  action="…"  loss=0.857  raw=6/7
```

- Loop column `architect` → `design` (the protocol's design phase).
- `loss_norm=` → `loss=`.
- `Δloss_norm=` → `Δloss=`.
- `loss_type=normalized-rubric` omitted when it equals the default (kept only when non-default, e.g. `loss_type=rate`).
- Per-iter `mode=` / `creativity=` fields deleted (redundant with the level on the meta line).

**Override syntax:**

- Removed: `LDD[mode=architect]:` and `LDD[mode=reactive]:` as user-facing overrides. For v0.11.0 only, the parser silently rewrites them to `LDD[level=L3]:` / `LDD[level=L2]:` and emits a trace note `deprecated: mode= is derived from level; use level= instead`. The aliases are removed entirely in v0.12.0.
- Kept: `LDD[level=Lx]:`, `LDD=max:`, `LDD++` / `LDD+`, natural-language bumps.
- Kept with new validation: `LDD[creativity=<value>]:` is now valid only at L3/L4 — at L0/L1/L2 it is ignored with a trace warning.

**Statusline format (level-aware):**

```
Idle          : LDD · idle
Active L0..L2 : LDD · L2/deliberate · inner k=1 · loss=0.167 · …
Active L3/L4  : LDD · L3/structural · creativity=standard · design k=2 · loss=0.286 · …
```

### Backward compatibility — reading old traces

`scripts/ldd_trace/store.py::_parse_line` accepts BOTH formats. A pre-v0.11.0 trace log still projects correctly:

- `loss_norm=` and `loss=` both accepted (reader prefers `loss`, falls back to `loss_norm`).
- `loss_type=normalized-rubric` may be absent or present (same semantics).
- Loop name `architect` is normalized to `design` on read.
- Per-iter `mode=` / `creativity=` fields are read and discarded.
- Meta line `level_chosen=Lx` / `dispatch_source=…` fields (v0.10.1 layout) are still parsed.

The `Phase` literal and `Iteration.mode` field in `renderer.py` stay for one release as read-compat hooks. New writes use the consolidated format.

### Trace-block header + tooling robustness

Three follow-on fixes that surface the consolidated dispatch/level/creativity metadata inside the rendered block and harden the serializer against real-world content:

- **`Store` / `Dispatched` / `Mode` header lines** — the `bootstrap-userspace` skill mandates a `│ Store :` line in every trace block, and `using-ldd` mandates a `│ Dispatched :` plus `│ Mode :` (when a creativity was chosen at L3/L4). `renderer.py` now emits all three from meta-line fields; `store.py::to_task()` projects `store` / `dispatched` / `level` / `level_name` / `creativity` onto the `Task` dataclass; `cli.py init` gains `--store`, `--level`, `--creativity`, `--dispatch`, `--dispatched` flags. When `--dispatched` is omitted but `--level` + `--dispatch` are set, a sensible header line is derived automatically (e.g. `auto-level L4/method`). Pre-v0.11.0 traces without these fields render without the new header rows (no empty stubs, no crashes).
- **`shlex.quote` serializer** — the pre-fix serializer wrapped values with naive `key="value"` formatting and silently truncated on inner double quotes, clipping e.g. a dispatch line carrying a quoted bump fragment mid-string. The new `_kv()` helper switches to :func:`shlex.quote` as soon as a value contains a quote character, so dispatch strings like `user-bump L4 (scorer proposed L3, bump: "full LDD")` round-trip losslessly.
- **Microsecond timestamps** — `_utcnow_iso()` now writes `%Y-%m-%dT%H:%M:%S.%fZ`. Tight append loops (multiple iterations within a sub-second) previously collided on the same string timestamp, causing the projection's stable sort to fall back on build order (design → inner → refine → outer → cot) and mis-position mid-task CoT detours at the end of the block. Microsecond resolution preserves narrative order without additional sort-key engineering.

### Stop-hook schema compliance

`skills/host-statusline/stop_render.sh` previously emitted a Stop / SubagentStop event wrapper of shape `{"hookSpecificOutput": {"hookEventName": "Stop", "additionalContext": "..."}}`. The Claude Code hook JSON schema reserves `additionalContext` for `UserPromptSubmit` (required) and `PostToolUse` (optional); emitting it on Stop triggers `Hook JSON output validation failed — (root): Invalid input` and suppresses the rendered block entirely. The hook now emits the block under the top-level `systemMessage` field, which is schema-valid for Stop/SubagentStop.

### Files touched

- Code: `scripts/level_scorer.py` (LEVEL_NAMES, rewritten `dispatch_header()`, deprecated-alias parsing, single-line CLI print), `scripts/ldd_trace/store.py` (new meta+iter field layout, dual-read support, loop-name aliasing, `_kv()` shlex-quoted serializer, microsecond timestamps, Store/Dispatched/Mode meta-line fields + projection onto `Task`), `scripts/ldd_trace/renderer.py` (design-phase label, Store/Dispatched/Mode header rows), `scripts/ldd_trace/aggregator.py` + `retrieval.py` (read both `loss=` and `loss_norm=`), `scripts/ldd_trace/cli.py` (loop choices, deprecated-arg help, new init flags), `scripts/ldd_trace/test_ldd_trace.py` (+4 regression tests for Store/Dispatched/Mode round-trip, inner-double-quote escape, derived dispatched-from-level, pre-v0.11 absence), `scripts/demo-*.py`.
- Docs: `skills/using-ldd/SKILL.md` (level table + Name column, dispatch-header section, trace format section, override syntax + deprecation note), `skills/architect-mode/SKILL.md` (reframed as 5-phase protocol active at L3/L4), `skills/bootstrap-userspace/SKILL.md` (magic line format update), `skills/host-statusline/SKILL.md` + `statusline.sh` + `stop_render.sh` (Stop-hook schema fix), `docs/ldd/thinking-levels.md`, `docs/ldd/architect.md`, `docs/ldd/hyperparameters.md`, `commands/ldd-architect.md`, `README.md`, `AGENTS.md`, `evaluation.md`.
- Plugin manifest: `.claude-plugin/plugin.json` bumped to `0.11.0`.

## [0.10.3] — 2026-04-22

### Added — Claude Web/Desktop skill bundle

**1. `dist/web-bundle/ldd-skill.zip` — drag-and-drop Claude Web/Desktop install.** Claude Web and Desktop accept one `SKILL.md + references/*` skill per upload, not a 14-skill plugin directory. The bundle consolidates `using-ldd` as the top-level `SKILL.md` and the other 13 skills (plus `bootstrap-userspace`) as `references/*.md` loaded on demand via progressive disclosure. The four-channel trace block (sparkline · mini chart · mode+info line · trend arrow) and its per-iteration + end-of-message emission rules are preserved byte-identically, so inline LLM traces and the final Close block render the same way as on Claude Code.

**2. `scripts/build_web_bundle.py` — deterministic bundle builder.** Reads `skills/using-ldd/SKILL.md`, the other included skills, the four referenced docs (`theory.md`, `thinking-levels.md`, `hyperparameters.md`, `convergence.md`), and `level_scorer.py`; rewrites cross-links to the flat bundle layout; emits the flat directory + a ZIP with a fixed mtime and sorted entries so the hash only changes when the content does. `--check` mode verifies the committed bundle matches the source; exit 1 on drift. `host-statusline` is excluded (Claude-Code-only).

**3. `scripts/test_build_web_bundle.py` — 21-test suite.** Covers determinism, drift detection, frontmatter validity, that every bundled skill is named in the frontmatter description (so Claude Web's auto-trigger matches), that the load-bearing trace-block rules survive the transform (per-iteration emission, final Close block, four visualization channels, deterministic rendering recipe, red flags, bootstrap-userspace fallback), that all intra-bundle links resolve to files that exist, and that the ZIP has the correct drag-and-drop shape (`ldd/SKILL.md` at archive root).

**4. `.githooks/pre-commit` — drift gate.** Blocks commits that ship an out-of-sync bundle. Activate once per clone via `git config core.hooksPath .githooks`. Only runs when a bundle-source file is staged, so unrelated commits stay fast.

**5. `.github/workflows/web-bundle-check.yml` + `release.yml` — CI + release automation.** The check workflow runs drift-check + the full test suite on every push/PR that touches a bundle-source file. The release workflow fires on `v*` tags, re-verifies the bundle, and attaches both `ldd-skill.zip` (stable-name link) and `ldd-skill-${TAG}.zip` (versioned link) to the GitHub Release so `releases/latest/download/ldd-skill.zip` is always the current build.

## [0.10.2] — 2026-04-22

### Added — CoT-loop rendering, Tier-2 persistence, two new skills

**1. CoT loop becomes first-class in the trace block.** The four-loop narrative that landed in docs in v0.10.1 is now implemented end-to-end in the renderer:

- `renderer.Iteration.phase == "cot"` renders as `(cot, dialectical)` with phase-prefix `c` (alongside the existing `i` / `r` / `o` for inner / refine / outer).
- `renderer.Iteration.timestamp` is preserved for chronological sorting across loops.
- `render_trace()` header recognizes `{inner, refine, outer, cot}` and appends `(all four fired)`; the three-loop case keeps `(all three fired)`. A run that exercises only a subset gets no parenthetical (honest display).
- `TraceStore.to_task()` reads `cot_entries` alongside the existing loop buckets.

**2. `ldd_trace ingest` — Tier-2 → Tier-0 promotion.** New CLI subcommand that scans arbitrary text (stdin or a file) for `⟪LDD-TRACE-v1⟫`-prefixed lines and appends them to the project's `.ldd/trace.log`, deduplicating against entries already present. This is how a user moves a task from a sandboxed chat host (ChatGPT, Claude Desktop without MCP filesystem) to a CLI agent: paste the chat transcript, run `python -m ldd_trace ingest --project . --input chat.txt`, keep working. Implementation: `store.ingest_magic_lines()` + `cli._cmd_ingest()`.

**3. Two new skills completing the cross-platform story.**

- `skills/bootstrap-userspace/SKILL.md` — fires at session start when `.ldd/trace.log` cannot be written (read-only filesystem, sandboxed chat host). Detects the host's persistence surface via introspection and picks the most durable tier silently — **Tier 0** (filesystem) → **Tier 1** (artifact/canvas) → **Tier 2** (conversation-history with `⟪LDD-TRACE-v1⟫` magic lines) → **Tier 3** (memory-pointer to where the trace actually lives) → **Tier 4** (inline-only, ephemeral). The chosen tier is announced via a `│ Store : <scope>` line in the trace-block header. Makes LDD work on Claude Desktop, ChatGPT, Codex Web, and any other host without the user having to configure anything.
- `skills/host-statusline/SKILL.md` — fires on Claude Code at session start in parallel with `bootstrap-userspace`. Auto-installs a permanent statusline that reads either `.ldd/trace.log` (Tier 0) or the session's JSONL transcript (Tier 2) and shows the current task / loop / iteration / loss / sparkline at the bottom of the console on every UI tick. Idempotent, merge-safe, project-local. Silently no-ops on non-Claude-Code hosts. Ships with `heartbeat.sh` and `statusline.sh`.

### Changed — documentation flattening

Three consecutive doc-only passes landed between the v0.10.1 tag and this entry — each a separate commit, all tagged under v0.10.2 for release:

- **`7f572d9`** — reframed every top-level narrative file around **"Gradient Descent for Agents"** and replaced "three loops" with "four loops" throughout the prose. 41 files; no normative change.
- **`128d391`** — four-loop cleanup pass: removed legacy version parentheticals (`(v0.5.0+)`, `(v0.7.0)`, `(v0.8.0)`, `(v0.9.0)`, `(v0.10.1)`) from non-historical prose, deleted `diagrams/three-loops.{dot,svg}` and replaced with `diagrams/four-loops.{dot,svg}` (four clusters: inner / refine / outer / CoT, each labeled with its parameter and gradient expression). The file name itself was a self-reinforcing legacy — as long as it existed, writers reflexively said "three loops."
- **`b14ea7c`** — dropped the "Rule: …" annotation from `diagrams/four-axes-gradient-descent.svg`, flushed the last three hidden version-stamp labels that only surfaced on render (in `four-axes-gradient-descent.dot`, `skills-overview.dot`, `mental-model-ldd.dot`), updated the `.claude-plugin/{marketplace,plugin}.json` descriptions that still said "three reactive loops" to the four-parameter-space framing. README.md line 112 skills-overview caption had "three code-axis loops" — fixed to name all four.

### Verification

- `pytest scripts/`: **253 passed / 3 skipped** (unchanged baseline)
- `scripts/render-diagrams.sh`: **12/12 SVGs rendered**, no errors, no `feDropShadow`
- All 11 SVG references from `.md` files resolve to existing files
- No new drift-scan findings beyond the two pre-existing ones

## [0.10.1] — 2026-04-22

### Added — Thinking-levels auto-dispatch

Every non-trivial task is now auto-scored onto a 5-step rigor ladder (L0 reflex → L1 diagnostic → L2 deliberate → L3 structural → L4 method) before any work begins. The scorer is deterministic (no LLM call), zero-config, upward-biased on boundaries, and trivially overridable per-task. Architect-mode is reached through the L3 / L4 presets — the separate "auto-dispatch for architect-mode" threshold is retired (its 6 signals are retained as a subset of the new 9-signal scorer; all prior dispatch behavior is preserved).

**New artifacts:**

- `scripts/level_scorer.py` — 9-signal deterministic scorer + 5-level bucketing + creativity-clamp + override parser + dispatch-header renderer. Pure function, CLI + library API.
- `scripts/test_level_scorer.py` — 55 unit + end-to-end tests covering per-signal detection, bucketing, creativity inference, override precedence, clamp rule, and all 9 fixture scenarios.
- `scripts/demo-thinking-levels-e2e.py` — integration walkthrough over 12 scenarios (5 level + 4 override + 3 stress); verifies scorer output matches documented contract.
- `tests/fixtures/thinking-levels/` — 9 fixture scenarios with verbatim prompts + expected-level contracts + asymmetric-loss-weighted rubric.
- `docs/ldd/thinking-levels.md` — authoritative reference for the 5 levels, 9 signals, override syntax, ack liberalization.
- `docs/superpowers/specs/2026-04-22-ldd-thinking-levels-design.md` — architect-mode 5-phase design spec.

**Integration:**

- `skills/using-ldd/SKILL.md` — § Auto-dispatch completely rewritten from binary "architect on/off" to the 5-level scorer; inline overrides extended with `LDD[level=Lx]:`; relative bumps `LDD+` / `LDD++` / `LDD=max`; natural-language bumps (bilingual, semantic dedup); precedence split into level-selection (5 categories) and other-hyperparameters blocks.
- `skills/using-ldd/SKILL.md` — new § Inventive ack documenting three paths (explicit flag / liberalized natural-language token / implicit ack from ≥2 inventive cues in prompt). The agent never selects inventive unilaterally; moving-target-loss protection preserved.
- `skills/method-evolution/SKILL.md` — new automatic trigger: 3 low-side auto-level regressions in 20 tasks → propose scorer-weight adjustment with rollback-on-regression.
- `skills/architect-mode/SKILL.md` — description updated to reference thinking-levels; auto-dispatch summary points at the 9-signal scorer and notes L3/L4 as the architect-mode path.
- `scripts/ldd_trace/store.py` — `TraceStore.init()` accepts `level_chosen` + `dispatch_source`; `append_close()` accepts `loss_final` + `regression_followed`. These persist the dispatch decision into `.ldd/trace.log` for method-evolution consumption.
- `scripts/drift-scan.py` — new `check_thinking_levels_drift` verifies bucket boundaries in `level_scorer.py` match `thinking-levels.md` and `using-ldd/SKILL.md` tables.
- `docs/ldd/hyperparameters.md` — one row added to §"What is NOT exposed": `level` is derived, never persisted.

**Design principle encoded throughout:**

> "lieber ein klein wenig schlau als zu dumm"

Asymmetric loss — low-side failures (level too low → silent symptom-patch) count ×2 more than high-side failures (level too high → wasted tokens). Encoded in: baseline L2 (not L0), tie-break on boundaries picks higher, natural-language bumps recognized liberally, fixture rubric suite-level weighting.

### Backward compatibility

- All prior architect-mode auto-dispatch behavior (`score ≥ 4 → architect`) is preserved through the L3 bucket (4 ≤ score ≤ 7) with `mode=architect`.
- The pre-existing `tests/fixtures/architect-mode-auto-dispatch/` fixture remains exercised as a regression baseline; its scenarios all still pass under the new scorer.
- No existing user-facing flag (`LDD[mode=...]`, `LDD[k=...]`, `LDD[creativity=...]`) changed semantics.

### Measurements

- Unit tests: 55 passing (scorer, override parsing, bucketing, clamp rule, fixture end-to-end)
- E2E walkthrough: 12/12 scenarios green (5 level + 4 override + 3 stress) — persisted under `tests/fixtures/thinking-levels/runs/`.
- Drift-scan: no new findings on thinking-levels artifacts.

## [0.9.1] — 2026-04-22

### Added — self-consistency release (14/15 audit findings resolved)

v0.9.1 applies LDD's own discipline to LDD's own code. The v0.9.0 audit
(docs/audit/v0-9-0-findings.md) surfaced 15 collapse/unsoundness modes.
v0.9.1 resolves 14 of them across 6 structural patterns. The remaining
finding (H7: recursive coupling / meta-calibration) is v0.10.0 scope
because it requires method-evolution-rollback infrastructure.

### P1 — Trust Boundary Layer (fixes C1, C2, H1, H4, L1)

New module `scripts/ldd_trace/trust_guard.py`:

  - `TrustGuard.guard_prior(prior)` caps at `MAX_PRIOR=0.9` (C2 fix)
  - `TrustGuard.guard_antitheses(antis, allow_empty=False)` validates
    prob ∈ [0,1] and |impact| ≤ 1; rejects empty list by default (H1, C2 fix)
  - `TrustGuard.guard_verify_fn(fn, required=True)` rejects None with
    a clear error pointing to canonicalize-then-compare (H4 fix)
  - `TrustGuard.guard_accessor(accessor, spec_name)` AST-audits for
    goodhart-identifier patterns (`lines_added`, `_by_agent`, etc.) (C1 fix)
  - `MULTILINGUAL_GAMING_PHRASES` extends phrase list to EN + DE + FR + ES (L1 fix)

Integration:
  - `MetricSpec.__post_init__` calls `TrustGuard.check_description_multilingual`
  - `CoTRunner.__init__` accepts `trust_guard` parameter; default is
    `default_trust_guard`. `require_antithesis=True` is the new default;
    old callers opt out via `require_antithesis=False`.
  - `CoTRunner._run_step` caps `thesis_prior` and validates antitheses;
    AntithesisAbsentError soft-lands with a degenerate reject step.

New exceptions:
  - `AntithesisAbsentError`, `ImpactOutOfRangeError`, `PriorTooHighError`,
    `VerifyFnMissingError`, `GoodhartAccessorError`, `TrustGuardError`

### P2 — Single Source of Truth (fixes C3, H5, M1)

- `MetricRegistry.list_names()` now returns `sorted(self._specs.keys())`,
  not `self._metrics.keys()`. API alignment — no more list_names-vs-specs
  disagreement after session reopen.
- `MetricRegistry.get(name)` raises `SpecExistsButCallableMissing` when
  the spec is on disk but the callable wasn't re-registered this session.
  Replaces the silent `None` return of v0.9.0.
- New `MetricRegistry.has_callable(name)` introspection helper.

### P3 — Multi-Statistic Gate + Rolling Window + Tri-State (fixes H2, H3, M2, M3)

`CalibrationRecord` unchanged; `Calibrator` extended:

  - `p95_error(name)` — 95th-percentile absolute error (H2 tail-risk)
  - `worst_error(name)` — max absolute error (H2 catastrophic-miss)
  - `mae_window(name, window=10)` — rolling MAE for demotion detection (M3)
  - `evaluate_state(name)` — returns tri-state+ verdict:
    `INSUFFICIENT_DATA` (n < min_n) — explicit third state (H3 fix)
    `CATASTROPHIC_OUTLIER` (worst > 0.50) — blocks promotion (H2)
    `TAIL_RISK_HIGH` (p95 > 0.30) — blocks promotion (H2)
    `DRIFTING` (mae > 0.15) — blocks promotion; enables demotion
    `LOAD_BEARING` (all gates pass)
  - `try_promote(name)` — now also DEMOTES a previously-promoted metric
    if recent-window MAE drifts above threshold (M3 monotonic-promotion fix)

`PromotionState` extended:
  - `state` field (string) — authoritative tri-state+ replaces
    binary `is_load_bearing`
  - `is_load_bearing` retained as read-only `@property` for v0.9.0 compat
  - `demoted_at`, `last_p95_error`, `last_worst_error` new audit fields

### P5 — Explicit Writer Model (fixes H6)

`Calibrator` constructor takes `writer_mode` ∈ `{"single_writer", "shared"}`:
  - `single_writer` (default): fast path, caller guarantees exclusivity
  - `shared`: wraps each append in `fcntl.flock(LOCK_EX)` so multiple
    processes / threads can safely append

The assumption becomes **contractual** rather than implicit.

### P6 — Type-Safe Composition (fixes M4)

`metric_compose` operators (`weighted_sum`, `maximum`, `minimum`) now check
that all components share the same `kind`:
  - Same kind → composes normally
  - Different kinds → raises `IncompatibleUnitsError` with a message
    explaining the user must either (a) choose same-kind components or
    (b) pass `force_incompatible=True` and attest the scale choice.

### Deferred — H7 recursive coupling (v0.10.0)

The method-evolution ↔ project_memory ↔ prime_antithesis cycle requires
a meta-calibration layer AND a skill-change-rollback mechanism. Both are
architectural v0.10.0 work — not a bugfix.

### Tests — 208 new total

  - `test_trust_guard.py` (24 tests): TrustGuard unit + integration tests
  - `test_v0_9_0_audit.py`: 4 audit tests inverted from "vulnerability" to
    "defense_in_v0_9_1" — evidence that the fixes hold
  - `test_metric.py`, `test_metric_e2e.py`: updated 1 test to use
    `force_incompatible=True` for legitimate cross-kind compositions
  - `test_cot.py`: 2 legacy tests opt out of new `require_antithesis=True`
    default via `require_antithesis=False`

All green: `python -m pytest scripts/ldd_trace/ -q` → 208 passed.

### Backward-compat notes

  - `PromotionState.is_load_bearing` is a read-only property now. Code
    that wrote to it must write to `state` instead. The one internal
    usage was updated; external callers must do the same.
  - `CoTRunner` default behavior changed: empty antithesis list → soft-land
    as `terminal=partial` + degenerate reject step. Legacy mock-LLM tests
    opt out via `require_antithesis=False`.
  - Cross-kind composition now requires `force_incompatible=True`. Legacy
    cross-kind calls will raise `IncompatibleUnitsError`.

### Dogfood — v0.9.1 built with LDD on itself

Audit-driven release: v0.9.0 audit surfaced findings → v0.9.1 closes 14
of them under LDD discipline. Trace persisted in `.ldd/trace.log`. This
is the self-consistency loop — LDD used LDD's tooling (`ldd_trace append`,
quantitative dialectic, method-evolution lens) to fix LDD's own code.

### Philosophical upshot

The v0.9.0 audit showed: LDD had weaknesses where it hadn't applied its
own discipline internally. v0.9.1 closes those gaps. When a framework
that teaches discipline internally violates the same principles, it's
not a bug — it's a credibility crisis. v0.9.1 is the credibility repair.

## [0.9.0] — 2026-04-21

### Added — Metric Algebra (extensible foundation for agent-defined losses)

v0.5.1–v0.8.0 introduced specific loss mechanisms (rubric rate, Δloss, chain correctness). v0.9.0 generalizes all of them into a **five-primitive algebra** that agents can extend without modifying LDD core.

### The five primitives

Defined in `scripts/ldd_trace/metric.py`:

| Primitive | Signature | Role |
|---|---|---|
| `Metric` | `Observation → ℝ` | Any measurable quantity (three kinds: `bounded`, `positive`, `signed`) |
| `Loss` | `θ → ℝ` | Metric bound to parameter space |
| `Signal` | `(θ_before, θ_after) → ℝ` | Observable Δ under an action |
| `Estimator` | `(Action, Context) → Prediction` | Predicts Signal before the action |
| `Calibrator` | `stream[(pred, obs)] → drift_signal` | Tracks MAE, promotes advisory → load-bearing |

Three concrete Metric classes ship: `BoundedRateMetric` (rate), `PositiveCountMetric` (count/latency/complexity), `SignedDeltaMetric` (signed Δ). Two Estimator implementations: `MeanHistoryEstimator` (v0.5.2's skill_effectiveness generalized) and `BayesianSynthesisEstimator` (v0.7.0's quantitative dialectic generalized).

### Composition algebra

Defined in `scripts/ldd_trace/metric_compose.py`:

- `weighted_sum(name, [(m₁, w₁), (m₂, w₂), ...])` → `Σ wᵢ·normalize(Lᵢ) / Σ wᵢ`
- `maximum(name, [m₁, m₂, ...])` → `max_i normalize(L_i)` (any-fail)
- `minimum(name, [m₁, m₂, ...])` → `min_i normalize(L_i)` (all-pass)

All composed metrics output ∈ [0, 1] by construction. Output-range preservation is the load-bearing property for cross-metric composition.

### Registry + Calibration gate

Defined in `scripts/ldd_trace/metric_registry.py`:

- `.ldd/metrics.json` — spec storage + promotion state (advisory vs load-bearing)
- `.ldd/metric_calibrations.jsonl` — append-only log of (metric_name, predicted, observed) pairs
- **Gate**: a metric goes from `advisory_only=True` to `is_load_bearing=True` iff `n_samples ≥ 5 AND MAE ≤ 0.15`. Until the gate passes, the metric cannot be used as a decision authority.

### Gaming-guard

`MetricSpec.__post_init__` rejects any spec whose description contains self-referential phrases (e.g., "my current action", "rewards my approach"). This prevents agents from registering metrics that game the optimizer toward their current behavior. The phrase list is tested by property-based coverage (`TestGamingGuard::test_any_self_ref_phrase_rejected`).

### New skill: `define-metric`

`skills/define-metric/SKILL.md` — the skill-level protocol. Metaphor: the apprentice at the instrument workshop — new instruments start advisory, calibration against trusted instruments promotes them. Six-step protocol: specify → accessor → register → compose (optional) → calibrate ≥5 times → auto-promote.

### CLI surface

```bash
python -m ldd_trace metric list      --project .
python -m ldd_trace metric status    --project .
python -m ldd_trace metric calibrate --project . --name X --predicted 0.3 --observed 0.28
```

### Tests — 82 new, 169 total

Evidence-based testing across three tiers:

- **Unit tests** (`test_metric.py`, 48 tests): spec validation, gaming-guard, each metric type's semantics, Loss/Signal, both Estimators, Registry, Calibrator gate behavior
- **Property-based tests** (`test_metric_properties.py`, 23 tests via hypothesis): algebraic laws — normalize bounds, normalize idempotency for bounded, weighted-sum homogeneity + commutativity, max/min idempotency + commutativity + duality, bias-invariance under registry/calibrator activity, gaming-guard phrase-coverage, distributional agreement with stdlib max/min
- **LDD E2E scenarios** (`test_metric_e2e.py`, 11 tests): realistic end-to-end workflows — agent-introduces-custom-metric, calibration-gate-promotes-after-evidence, poorly-calibrated-metric-stays-advisory, composition-drives-multi-objective-decision, bias-invariance-under-intense-registry-activity, gaming-guard-blocks-self-ref-spec, persistence-across-sessions, MeanHistoryEstimator, BayesianSynthesisEstimator-replicates-v0.7.0, full-workflow-end-to-end

All green: `python -m pytest scripts/ldd_trace/ -q` → 169 passed.

### Backward compatibility

Every prior LDD loss is now expressible in the new abstraction (test explicitly verifies this):

| Prior | Expressed as |
|---|---|
| v0.5.1 test-pass-rate | `BoundedRateMetric` |
| v0.5.2 skill Δloss_mean | `MeanHistoryEstimator` |
| v0.7.0 quantitative dialectic | `BayesianSynthesisEstimator` |
| v0.7.0 MAE drift detection | `Calibrator.can_promote` |
| v0.8.0 chain-level predicted | `weighted_sum` or custom estimator |

### Theoretical framing

`docs/theory.md` §3.11b — formal spec of the Metric Algebra with composition formulas, calibration gate, backward-compat mapping, algebraic laws. Updated §2 still shows four optimizer loops (Metric Algebra is horizontal, not a new loop).

New diagram: `diagrams/metric-algebra.svg` — the five primitives + composition + gate.

### Dogfood — built with LDD on itself

v0.9.0 was built as an LDD task on the loss-driven-development repo itself. `.ldd/trace.log` captures the iteration trace:

```
Trajectory : █▅▃·   1.000 → 0.630 → 0.408 → 0.215 → 0.000  ↓
```

Four inner-loop iterations: scaffold → core + unit tests → property tests → E2E tests → close. Loss reduced from 1.000 to 0.000 (169/169 tests green) under K_MAX=5 budget.

### Philosophical upshot

LDD was a fixed skill set for SGD on code/deliverable/skill/thought. With Metric Algebra, it becomes a **kernel**: agents define new objectives; the framework enforces the same discipline (prediction → observation → calibration → method-evolution) with bias-invariance guarantees. The framework is now **self-extensible** under hard invariants.

## [0.8.0] — 2026-04-21

### Added — Dialectical Chain-of-Thought (thought-loop, the fourth LDD optimizer layer)

v0.7.0 made the synthesis step of dialectical reasoning produce a number (`E[Δloss | thesis]`). v0.8.0 applies that machinery to each step of a multi-step reasoning chain — turning CoT from greedy-SGD-on-thoughts into **quantitative-gradient-SGD-on-thoughts** with per-chain calibration.

### The new skill: `dialectical-cot`

- `skills/dialectical-cot/SKILL.md` — full 5-step-per-step protocol specification with worked math-problem example. Metaphor: the climber who probes every step before committing weight.
- Decision thresholds: `commit ≥ 0.7`, `revise 0.4–0.7`, `reject < 0.4` (calibratable via outer loop).
- Hard rule: ≥ 1 antithesis per step MUST be independent of memory primers (anti-groupthink guard).
- Bias invariance enforced: memory/primers/synthesis NEVER modify ground-truth verification.

### Python harness

- `scripts/ldd_trace/cot.py` — data classes (`Step`, `CoTChain`, `Antithesis`), `CoTRunner`, synthesis math (`compute_predicted_correct`, `decide_from_predicted`), gather_primers bridge to v0.6.0
- `scripts/ldd_trace/cot_llm.py` — abstract `CotLLMClient` protocol; `MockCotLLMClient` (deterministic, for tests); `OpenRouterCotLLMClient` (real LLM via OpenRouter, stdlib-only HTTP, activates on `OPENROUTER_API_KEY` env var)
- `scripts/ldd_trace/cot_memory.py` — `.ldd/cot_traces.jsonl` (append-only per-chain log) + `.ldd/cot_memory.json` (per-task-type aggregate)
- CLI: `python -m ldd_trace cot run --task ... --task-type math --ground-truth ...`, `cot aggregate`, `cot health`

### Memory & calibration

Per-task-type partitioning prevents cross-type signal mixing:
- `step_decision_distribution` per task_type
- `common_failure_modes` harvested from revise/reject-step antitheses
- `calibration.mae` per task_type; `drift_warning: true` when `MAE > 0.15 ∧ n ≥ 5`
- `cot_primers_for_task_type(task_type)` feeds memory-sourced primers back into subsequent chains

### Theory update

- `docs/theory.md` §3.11a — formal specification of the Thought-Loop as the fourth optimizer layer, including chain-level prediction formula, decision rule, and calibration extension
- New diagram: `diagrams/dialectical-cot.svg` — per-step protocol flow

### Tests — 28 new, 87 total

- Math tests for `compute_predicted_correct` (bias-invariance at the formula level)
- Decision threshold tests
- Happy-path CoT run (commit-only chain)
- Revise test (antithesis forces narrower synthesis)
- Backtrack test (reject triggers branch retry)
- Backtrack-budget-exhaustion test (max_backtracks → partial terminal)
- Memory aggregation tests (task-type partitioning, calibration MAE, drift warning, failure-mode harvesting)
- Primer generation tests (empty memory, failure-mode-based primer, cross-type-leakage guard)
- Bias-invariance tests: memory does NOT affect verify_answer outcome; predicted_correct is decoupled from ground_truth access
- CLI smoke tests (graceful error when no API key / no memory)

All green: `python -m pytest scripts/ldd_trace/ -q` → 87 passed.

### Philosophical upshot

The thought-loop treats reasoning itself as an optimizable parameter space. Previous LDD layers optimize code, deliverables, and skills. v0.8.0 optimizes *how the agent reasons* for a given task-type class — with the same bias-invariance discipline that guards the lower loops. This is not "just another CoT technique"; it's the generalization of LDD's framework to the reasoning-space manifold.

## [0.7.0] — 2026-04-21

### Added — The Quantitative Dialectic (skill-first, with code plumbing)

The v0.6.0 coupling made memory feed dialectical reasoning via narrative primers. v0.7.0 makes the coupling **numeric** — not by computing gradients in Python, but by prescribing a **5-step numeric protocol** in `skills/dialectical-reasoning/SKILL.md` that the agent walks in-head during synthesis.

This is the point where "gradient via dialectic" stops being metaphor and becomes a reasoning discipline: *LDD is a skill, so the discipline lives in the skill text, not in the tool.* The Python side adds only the calibration substrate.

### The protocol (skill text)

New section in `dialectical-reasoning/SKILL.md` specifies:

- **Step 1 — Thesis** carries `predicted_Δloss` + `confidence_factor`, drawn from `project_memory.json`.
- **Step 2 — Antithesis primers** map to `{probability, impact}` pairs — each primer from `prime-antithesis` now has a numeric interpretation, not just prose.
- **Step 3 — Synthesis** computes `E[Δloss | thesis] = Σ (prob × impact) + (1 − Σprob) × predicted`.
- **Step 4 — Decision rule**: commit if `E[Δloss | thesis] < 0` AND no alternative dominates by > 0.1; reject if an alternative dominates by > 0.1 or `E[Δloss | thesis] ≥ 0`; else escalate (ambiguous).
- **Step 5 — Calibration** logs `predicted_Δloss` at commit; aggregator compares to observed `actual_Δloss` after close.

A worked example (retry-variant vs. root-cause-by-layer in a plateau scenario) walks the five steps end-to-end with actual numbers.

Five hard rules preserve the loss invariant:
1. No fabricated numbers (`n < 3` → confidence = low, prediction = unknown).
2. Prediction is advisory, not gate — agent may override with stated reasoning.
3. Calibration is mandatory — commit without `--predicted-delta` = v0.7.0 protocol was not applied.
4. No cross-project numbers (per-project memory only).
5. Within ambiguity band (|Δ| < 0.1) → user decision.

### Code support for the protocol

- `ldd_trace append --predicted-delta <float>` — new optional arg. When provided, the trace line carries `predicted_Δloss=X` AND the computed `prediction_error = predicted − actual`.
- `aggregator` — new `calibration` section in `project_memory.json`:
  - `n_predictions`, `mean_abs_error`, per-skill `mean_abs_error`
  - `drift_warning: true` when `mean_abs_error > 0.15` over `n ≥ 5` samples — explicit outer-loop signal that the agent's in-head priors are mis-calibrated
- `health` render surfaces the calibration block when predictions exist, so the user sees drift at a glance.

### Why no auto-apply anywhere

All of this is additive to the reasoning protocol. The loss function `L(θ)` is unchanged; the rubric is unchanged; the actual observed Δloss is measured exactly as before. What changes is that the agent's *search direction* is now guided by explicit, auditable, calibratable priors rather than implicit gut-feel. If calibration degrades, the aggregator tells the agent so — and `method-evolution` fires on outer loop, not a silent loss-modification.

### Tests — 8 new, 59 total

- 2 tests for `predicted_delta` field recording (with/without)
- 3 tests for `calibration` aggregation (good calibration, drift warning, empty)
- 2 tests for health rendering (with/without predictions)
- 1 CLI integration test (`append --predicted-delta` round-trips through trace.log)

All green: `python -m pytest scripts/ldd_trace/ -q` → 59 passed.

## [0.6.0] — 2026-04-21

### Added — memory × dialectical coupling (`prime-antithesis` + skill update)

v0.5.2 gave LDD a 1st-moment project memory (aggregate historical stats). v0.6.0 **couples it with 2nd-order reasoning** (the `dialectical-reasoning` skill). In SGD terms:

- **Memory (v0.5.2)** = 1st moment — average of past gradient directions (bias-guarded priors over skill-effectiveness and failure modes).
- **Dialectical (pre-0.6.0)** = 2nd moment / Hessian probing — local adversarial probing of the proposed gradient step for orthogonal directions where L reacts non-monotonically.
- **v0.6.0 coupling** = a Bayesian-style update: `confidence(action) ∝ memory_likelihood × dialectical_likelihood × prior`.

New tool: `python -m ldd_trace prime-antithesis --project . --thesis "..."`. Pulls structured primers from `project_memory.json` and formats them as **questions the antithesis must answer**, not prescriptions. Four primer sources:

| Source | Fires when |
|---|---|
| `skill_failure_mode` | Thesis names a skill with ≥ 30% regression+plateau rate (n ≥ 3) |
| `plateau_pattern` | Current in-flight task has ≥ 2 consecutive near-zero Δ |
| `similar_task` | File-overlap with a non-completed past task (jaccard ≥ 0.3) |
| `terminal_analysis` | Project-wide non-complete rate ≥ 15% (n ≥ 5 tasks) |

Skill update: `skills/dialectical-reasoning/SKILL.md` gains a new section "Memory-informed antithesis generation" that cross-references the tool + enforces three agent-contract rules:
1. Each primer becomes a required antithesis point
2. Generate ≥ 1 antithesis NOT sourced from primers (anti-groupthink guard)
3. Synthesis MUST explicitly reconcile or reject each primer

### Loss invariant preserved (no bias injection)

Primers are **evidence**, not weights:
- No auto-apply: dialectical synthesis decides, memory surfaces
- No ranking: severity ("high"/"warn"/"info") is a visibility hint, not an optimizer weight
- No filtering: memory can't suppress a primer once the statistical threshold is met
- Rubric items and scoring are unchanged; only the *considered-counter-case set* is enriched

A `TestBiasInvariant` test class verifies that primers are phrased as questions (not directives) and that no prescriptive language ("MUST", "DO NOT") appears in primer material — only in the agent contract (which is about process, not code).

### Why this closes the v0.5.2 blind spot

v0.5.2's memory can name "skill X has 40% regression rate here" — but it can't tell you *whether this task is the exception*. That requires reasoning. Without dialectical coupling, memory signals either get ignored (agent overrides) or over-applied (agent cargo-cults). The v0.6.0 contract forces both sources through a synthesis, making the decision auditable.

Concrete benefit on the three failure modes from v0.5.2:
- **Plateau**: memory names resolvers, dialectical asks "is the *parameterization* wrong or just the *attempt*?" — dialectical escalates layer when memory alone would just pivot skill
- **Local minimum**: memory can't see it (L=0 from memory's POV); dialectical IS the generalization-gap probe (layer-5 / regularizer)
- **Wrong decision**: memory gives rate, dialectical gives causal defensibility — agreement on both = commit, disagreement = investigate

### Tests — 14 new, 51 total

- 2 skill-failure-mode primer tests (fires for retry-variant, silent for root-cause-by-layer)
- 2 plateau-pattern primer tests (fires on 2-streak, silent on healthy task)
- 2 terminal-analysis primer tests (threshold boundary behavior)
- 1 combined-priming test (plateau + bad-skill = 2 primers)
- 2 formatter tests (empty + populated)
- 3 CLI integration tests (help / error-on-missing-memory / full-flow)
- 2 bias-invariant tests (evidence-not-decision, no-ranking-weights)

All green: `python -m pytest scripts/ldd_trace/ -q` → 51 passed.

## [0.5.2] — 2026-04-21

### Added — trace-based project memory (`aggregate` / `suggest` / `check` / `similar` / `health`)

v0.5.1 made per-iteration trace emission cheap. v0.5.2 makes the accumulating trace.log **useful** as a project-level memory — the agent reads historical patterns to detect plateaus and flag regressive skill-choices, without biasing the loss itself.

Five new CLI subcommands on top of the v0.5.1 tool:

```bash
python -m ldd_trace aggregate --project .          # write .ldd/project_memory.json
python -m ldd_trace health    --project .          # human-readable project state
python -m ldd_trace suggest   --project . [--top-n 5]  # empirical skill ranking
python -m ldd_trace check     --project . [--next-skill X]  # in-flight warnings
python -m ldd_trace similar   --project . --files a,b,c     # file-overlap retrieval
```

`ldd_trace close` auto-runs `aggregate` as a side effect — project_memory.json is never stale.

### Core design constraint — memory must not bias the loss

The loss function `L(θ)` (rubric violations) stays pure. Memory informs NAVIGATION (which skill next, when to escalate, where to warm-start) but NEVER redefines progress.

Four explicit bias-guards, each tested:

| Bias | Risk | Guard |
|---|---|---|
| Survivorship | "complete-only" skill stats inflate effectiveness | aggregate counts **every** terminal state; per-skill `by_terminal` breakdown exposed |
| Regression-to-mean | Skills that fire on hard bugs show trivially higher Δ | report both `delta_mean_abs` **and** `delta_mean_relative` (Δ / prev_loss) |
| Recency drift | Weighting recent heavier masks skill-version drift | both lifetime and last-30-day windows shown; caller chooses |
| Confirmation | Agent self-curation skews aggregate | aggregation is deterministic on raw trace; agent never filters |

Each guard is both documented (`bias_guards` block in `project_memory.json`) and test-enforced (`test_e2e_memory.py::TestAggregatorBiasGuards`).

### The two use cases the memory unlocks

1. **Plateau detection** — current task shows ≥ 2 consecutive near-zero Δ → `check` emits HIGH-severity warning citing historical resolvers ("past plateaus resolved by root-cause-by-layer (3) over 3 observations"). Agent sees empirical exit-path, not just "you're stuck."
2. **Wrong-decision detection** — next planned skill has ≥ 30% historical regression-rate → `check` warns before the bad step. Scoped to same project (no cross-project contamination).

Both are retrospectively validated against the narralog trace: at narralog's actual i3 (streak=1) the check correctly produces **no** warning (false-positive guard holds); at a simulated counterfactual i4 (streak=2) the check **would have** flagged the plateau and named root-cause-by-layer as the historical resolver — matching what narralog's actual i4 manually arrived at via method-evolution.

### Storage shape

```
.ldd/
  trace.log              ← v0.5.1 — append-only log of iterations + closes
  project_memory.json    ← v0.5.2 — deterministic aggregate, auto-refreshed
```

Per-project by default. No cross-project global aggregate (explicit design choice for privacy + no signal-mixing). Session state is ephemeral — recovered from trace.log at task start via `ldd_trace status`.

### Tests — 16 new, 37 total

- 5 bias-guard correctness tests (survivorship, by-terminal split, relative delta, windows, metadata)
- 3 aggregator metric tests (task_shape, retry-variant no-progress signature, plateau-pattern detection)
- 2 plateau-detection tests (triggers when streak ≥ 2; false-positive guard on healthy task)
- 2 wrong-decision tests (warns on regressive skill; no-warn on good skill)
- 1 over-budget detection test (k ≥ p95 triggers escalation warning)
- 2 retrospective-against-narralog tests (narralog i3 correctly doesn't fire; counterfactual i4 does)
- 1 skill-ranking test (workhorse skill outranks bad skill)

All green: `python -m pytest scripts/ldd_trace/ -q` → 37 passed.

## [0.5.1] — 2026-04-21

### Added — `scripts/ldd_trace/` CLI tool for per-iteration trace emission

v0.5.0 mandated per-iteration emission of the trace block (see `using-ldd/SKILL.md` § "When to emit"). v0.5.1 makes that mandate **cheap to honor**: a Python package with a five-subcommand CLI (`init` / `append` / `close` / `render` / `status`) that persists to `.ldd/trace.log` and re-renders the full block on every write.

```bash
python -m ldd_trace init   --project . --task "bug fix" --loops inner
python -m ldd_trace append --project . --loop inner --auto-k \
    --skill e2e-driven-iteration --action "what changed" \
    --loss-norm 0.333 --raw 1/3 --loss-type rate
python -m ldd_trace close  --project . --loop inner --terminal complete \
    --layer "3: contract · 5: invariant" --docs synced
```

Rendering logic was **lifted verbatim from `scripts/demo-trace-chart.py`** into `scripts/ldd_trace/renderer.py` — no behavior change versus the v0.5.0 demo output. The demo script remains as the educational reference.

### Changed — per-iteration trace emission reclassified from "should" to hard step

Empirical finding behind v0.5.1: on a real multi-iteration task (narralog, 2026-04-21), the v0.5.0 per-iteration emission mandate was silently dropped across 4 iterations despite the spec. The mandate lived only in `using-ldd/SKILL.md` § "When to emit" — the iteration-performing skills didn't cross-reference it, so the agent finished iterations without rendering the trajectory.

Method-evolution fix across three skills:

- `skills/e2e-driven-iteration/SKILL.md` — the Five-Step Iteration becomes **Six-Step**; step 6 is `Emit trace` with an explicit `python -m ldd_trace append ...` call. "Do not skip step 6" is added with a one-paragraph rationale. The red-flags list gains `"I'll emit the trace block at the end of the whole task"` → NO, per-iteration is a data-visibility requirement. The checklist grows from 7 to 8 items (step 7 = emit; step 8 = close).
- `skills/loop-driven-engineering/SKILL.md` — `Sub-Skill Dispatch` table gains two rows: `ldd_trace status` at task start (recover prior iteration state from `.ldd/trace.log`), and `ldd_trace append` at iteration close (emission contract).
- `skills/using-ldd/SKILL.md` — adds a RED FLAGS table immediately after § "When to emit" with four concrete rationalizations and the correct response for each. Adds a "bidirectional" subsection: trace.log is now READ at task start for state recovery, not just written.

### Why a tool, not just a stricter spec

v0.5.0's spec was already strict — the violation was tooling-driven. Per-iteration emission asked the agent to hand-render ~30 lines of ASCII (sparkline + chart + per-iteration info lines) on every loss measurement. Under time pressure that overhead got discounted. v0.5.1 reduces the cost to one shell command: if the agent can run `pytest`, it can run `python -m ldd_trace append ...`. Spec strictness is now matched by ergonomic strictness.

### Bidirectional trace.log

Prior to v0.5.1 the trace.log was write-only (persistence for grep / audit). v0.5.1 makes it the **source of truth** for iteration-state recovery across sessions:

- `python -m ldd_trace status --project .` → machine-readable `next_k` per loop + last `loss_norm` per loop
- `python -m ldd_trace render --project .` → full trace block reconstituted from log alone

A new session starting on an existing project reads trace.log first and resumes at the correct `k` instead of starting at `i1` again.

### Tests

- `scripts/ldd_trace/test_ldd_trace.py` — 21 unit + integration tests, pytest-driven:
  - Pure renderer functions (sparkline, trend_arrow, mini_chart) against the §"Rendering recipe" in `using-ldd/SKILL.md`
  - Store round-trip (init → append → close → render) on pytest's `tmp_path`
  - CLI subprocess tests for all five subcommands
  - Three-channel consistency: sparkline last bar + chart last marker + final iteration's loss must agree on the same number

All green: `python -m pytest scripts/ldd_trace/test_ldd_trace.py -q` → 21 passed.

## [0.5.0] — 2026-04-21

### Added — trace visualization (sparkline, mini chart, mode+info line, trend arrow)

The LDD trace block now carries four parallel channels alongside the numeric loss values, making the trajectory AND the per-iteration skill work both auditable at a glance. Closes two friction points in one release: "loss numbers on their own are hard to eyeball" (solved by sparkline + chart) and "the user can't tell which skill did what per iteration" (solved by the mandatory mode-indicator + info line).

**The four channels** (in `skills/using-ldd/SKILL.md` § Loss visualization — sparkline, mini chart, mode+info line, trend arrow):

| Channel | Mandatory at | Purpose |
|---|---|---|
| **Trajectory sparkline** (`▁▂▃▄▅▆▇█`, auto-scaled, zero → `·`) | ≥ 2 iterations | Micro-dynamics — 8-level resolution across the full run |
| **Trend arrow** (`↓` / `↑` / `→`, first-vs-last delta) | ≥ 2 iterations | Net direction at the end of the sparkline; distinct from per-step `Δ` arrows |
| **Mini ASCII loss-curve chart** (`┤` y-axis + `●` markers + labeled x-axis) | ≥ 3 iterations | Macro-trajectory with `0.25`-step snap and per-phase labels (`i1`, `r2`, `o1`) |
| **Per-iteration mode + info line** | every iteration | The iteration label carries a mode parenthetical — `(inner, reactive)`, `Phase p1 (architect, <creativity>)` with creativity ∈ {standard, conservative, inventive}, `(refine)`, or `(outer)` — so the reader can tell which discipline was active per iteration. An indented continuation line carries `*<skill-name>*` + a one-line description of what concrete change the iteration produced. Gives the user an audit trail without scrolling elsewhere |

The sparkline and chart MUST agree on the final `loss_k`. The SKILL.md section specifies a deterministic rendering recipe (sparkline indexing via `round(v/max * 7)`, chart snap via `floor(v/0.25 + 0.5) * 0.25`, trend arrow via first-vs-last delta with ±0.005 plateau band, mode-indicator grammar per loop/mode) so renders are reproducible across agents and sessions.

**Non-monotonic trajectories are first-class.** The end-to-end trend arrow is computed from `last − first`, so `0.667 → 0.833 → 0.167` (i1→i2 regression, i2→i3 recovery) still reads `↓` at the end of the sparkline — even though the per-step `Δ` arrow on i2 correctly shows `↑` locally. Sparkline arrow = net direction; per-step `Δ` arrow = local direction. The SKILL.md text calls this distinction out explicitly to prevent conflation.

**Mode-indicator grammar.** The parenthetical on each iteration line uses the four-way split: `(inner, reactive)` for default inner work, `Phase pk (architect, <creativity>)` when architect-mode replaces the inner loop (note: word `Phase` not `Iteration`, signaling the 5-phase protocol), `(refine)` for y-axis deliverable work, `(outer)` for θ-axis method work. A session that runs architect inner → hands off to reactive inner renders both in the same trace: `Phase p1..p5` followed by `Iteration i1..i<k>`.

**Why no per-iteration `█`/`░` bar** (explicit design non-choice). An earlier draft of the spec included a 20-char magnitude bar per iteration. It was removed because information density is strictly worse than the mode+info line — bars re-encode data already carried by the sparkline and chart, while the mode+info line carries *new* information (which skill, what action) the user cannot reconstruct from loss numbers alone.

### Changed — trace emission cadence: once-per-task → after every iteration (live)

Prior to v0.5.0 the rule was "emit ONE block per task; re-emit at message end if the task spans messages." The rule is now **emit after every iteration** during live task execution — the user watches the loss descend in real time rather than waiting until task close. Consecutive emissions grow monotonically by exactly one iteration (plus one sparkline char, one chart column, and a possibly-flipped trend arrow).

The per-skill-invocation anti-pattern is preserved: within one iteration multiple skills may fire (e.g. `reproducibility-first` + `root-cause-by-layer`), they still share ONE block emitted at iteration close. The rule discriminates iterations from skill-invocations, not the emission from existence.

**Post-hoc reconstruction exception** (new in v0.5.0): when the user hands you a completed task's iteration data and asks you to render the trace, emit ONE final block — there are no real iterations happening, so repeating the growing block would print the same data 3× without adding information. The `tests/fixtures/using-ldd-trace-visualization/` fixture exercises this exception (all three scenarios are post-hoc reconstructions).

**Budget trade-off acknowledged.** Per-iteration emission multiplies trace-block token cost by the iteration count. For tight-context sessions, the existing compression rule (info-lines collapsed to skill-name-only) mitigates; the visualization channels are never dropped. The audit-transparency gain was judged worth the token cost — a user who cannot see their loop's progress until close is a user who will ask "is it still running?" after 90 seconds of silence.

### Changed — trace block example in README reflects v0.5.0 format

The inline trace example in `README.md` § "Live trace — see the loop happen in real time" was replaced with a 6-iteration three-loop run rendered in full v0.5.0 format (sparkline, chart, per-iteration mode+info + `Δ` column, close). A new subsection `#### Mental model — the four visible channels` follows, explaining each granularity and the consistency rule, and linking to the authoritative SKILL.md section and the v0.5.0 fixture.

### Tests — new fixture `tests/fixtures/using-ldd-trace-visualization/`

Three RED/GREEN scenarios, captured at `deepseek/deepseek-chat-v3.1`, T=0.7, via OpenRouter (cheaper than v0.4.0's `gpt-5-mini`; total capture spend ≈ $0.05). Scored against a 4-item rubric measuring channel emission + mode-indicator grammar + per-iteration skill-info + net-direction-arrow correctness.

| Scenario | RED loss | GREEN loss | Δloss |
|---|---:|---:|---:|
| inner-three-iters | 4 / 4 | 2 / 4 | **+2** |
| all-three-loops | 4 / 4 | 0 / 4 | **+4** |
| regression-and-recovery | 4 / 4 | 0 / 4 | **+4** |

Every scenario clears the Δloss ≥ 1 release gate. Bundle-scoped normalized Δloss for this fixture: `0.833`, well above the bundle target of `≥ 0.30`. Scenario `inner-three-iters` lost 2 items in GREEN (mini chart and trend arrow not emitted — base-model rendering skip at T=0.7 on the shortest scenario); sparkline and mode+info line transferred cleanly. Scenarios 2 and 3 hit all four items; scenario 3 validates the subtlest discriminator — GREEN correctly reads the non-monotonic prompt and emits `↓` end-to-end while keeping the per-step `Δ +0.167 ↑` on i2.

### Updated

- `skills/using-ldd/SKILL.md` — new `### Loss visualization — sparkline, mini chart, mode+info line, trend arrow` subsection (4-channel mandatory thresholds, mode-indicator grammar, deterministic rendering recipe, 6-iteration reactive-inner worked example, architect→inner hand-off worked example, non-monotonic-trajectory rule, compression rule, loss-type-specific rendering)
- `README.md` — trace example block replaced with v0.5.0 format; new `#### Mental model — the four visible channels` subsection with fixture link + measurement summary
- `tests/fixtures/using-ldd-trace-visualization/` — new fixture (scenario.md + rubric.md + runs/20260421T122248Z-clean/)
- `scripts/demo-trace-chart.py` — new demo helper, renders the trace block from a hard-coded 6-iteration task with mode-indicator + info lines. Pure renderer, no skill invocations, no LLM calls; functions (`sparkline`, `mini_chart`, `trend_arrow`, `render_trace`) are directly liftable into a future renderer module under `skills/using-ldd/`
- `scripts/demo-e2e-trace.py` — new executed-demo helper. Optimizes a real Python function (`compute_average`) through all three loops (inner → refine → outer), running actual rubric checks against actual compiled code at every iteration and re-rendering the trace block after each. Supports `--fast` for piping; default pauses 0.5s per iteration for live-feel. No simulation — every loss value is computed from `exec()` + call + rubric assertion
- `scripts/README.md` — new rows for both demo helpers
- `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json`, `gemini-extension.json` — version bumped `0.4.0` → `0.5.0`

## [0.4.0] — 2026-04-21

### Added — auto-dispatch for architect-mode

The coding agent can now enter architect-mode **on its own** when the task description carries enough structural signals — without the user having to type `LDD[mode=architect]:`, invoke `/ldd-architect`, or use an explicit trigger phrase. Closes the "user described greenfield but didn't know the magic word" failure mode.

**The 6-signal scorer** (in `skills/using-ldd/SKILL.md` § Auto-dispatch for architect-mode): greenfield `+3`, names ≥ 3 new components `+2`, cross-layer scope `+2`, ambiguous requirements `+2`, explicit bugfix `−5`, single-file known-solution `−3`. Weighted sum ≥ 4 → architect-mode. Hard gate, not average; tie-break at exactly 4 goes architect.

**Creativity inference** from the same task signals: regulatory / compliance / no-new-tech / tight team+deadline cues → `conservative`; research / novelty / "invent" / "experiment" cues → `inventive`; neither → `standard` (default). Conservative beats inventive on ties. The per-task acknowledgment flow for `inventive` is unchanged — auto-dispatch proposes the level but does not bypass the ack gate; without a literal `acknowledged` reply, the run silently downgrades to `standard`.

**Explicit user triggers always win.** Precedence order (highest first): inline `LDD[mode=…]` / `LDD[creativity=…]` flags > `/ldd-architect` command arg > trigger-phrase match > auto-dispatch (this pipeline) > bundle default. `LDD[mode=reactive]:` on a task with auto-score 6 stays reactive.

### Changed — trace header extended with dispatch source

Every architect-mode trace block now carries a `Dispatched:` line naming one of `inline-flag`, `command`, `trigger-phrase: "<phrase>"`, or `auto (signals: <top-2 by absolute weight>)`. Silent auto-dispatch is a trace-integrity violation — the user must be able to see WHY architect-mode was entered and override with one follow-up message. Example:

```
│ Dispatched : auto (signals: greenfield=+3, cross-layer=+2)
│ mode: architect, creativity: standard
```

### Changed — README mental-model wiring

New subsection `Mental model — the auto-dispatch flow` under the architect-mode README block. Linked mental model per LDD's own docs-as-DoD rule: cites `skills/using-ldd/SKILL.md` (trigger table), `skills/architect-mode/SKILL.md` § creativity, `docs/ldd/convergence.md` (loss-function framing), `docs/ldd/hyperparameters.md` (precedence). Embeds an SVG of the Task → Signal-extraction → Score → {mode, creativity, ack-flow} → Trace-echo pipeline (`docs/diagrams/architect-auto-dispatch.svg`; self-contained, no `feDropShadow`, GitHub-safe).

### Tests — new fixture `tests/fixtures/architect-mode-auto-dispatch/`

Four RED/GREEN scenarios, captured at `openai/gpt-5-mini`, T=0.7, via `scripts/capture-red-green.py` (new helper — paired RED/GREEN captures with skill content as system-message on the GREEN side). Scored against a 4-item rubric measuring dispatch-correctness:

| Scenario | RED loss | GREEN loss | Δloss |
|---|---:|---:|---:|
| bugfix-skip | 1 / 4 | 0 / 4 | **+1** |
| greenfield-inventive | 4 / 4 | 0 / 4 | **+4** |
| regulated-conservative | 4 / 4 | 0 / 4 | **+4** |
| typical-standard | 4 / 4 | 0 / 4 | **+4** |

Every scenario clears the Δloss ≥ 1 release gate. Bundle-scoped normalized Δloss for this fixture: `0.813`, above the bundle target of `≥ 0.30`. Dominant driver is the trace-echo discipline (item 3) — the base model has no reason to invent a `Dispatched:` line, so this item flips RED → GREEN in every scenario.

### Updated

- `skills/using-ldd/SKILL.md` — new `## Auto-dispatch for architect-mode` section (scorer, creativity inference, precedence, worked example); trigger-table entry for architect-mode mentions the fourth path; architect trace-block example extended with `Dispatched:` line
- `skills/architect-mode/SKILL.md` — new `## Auto-dispatch by the coding agent` section summarizing the scorer and pointing at the authoritative spec in `using-ldd/SKILL.md`; description field mentions auto-dispatch
- `README.md` — new `### Mental model — the auto-dispatch flow` subsection with SVG
- `docs/diagrams/architect-auto-dispatch.svg` — new diagram, 12 KB, 820 × 940 viewBox, no `feDropShadow`, no external refs
- `tests/fixtures/architect-mode-auto-dispatch/` — new fixture (scenario.md + rubric.md + runs/20260421T002928Z-clean/)
- `scripts/capture-red-green.py` — new paired-capture helper (OpenRouter / OpenAI / Anthropic fallback, retry-once-with-30s-backoff, no `print()`)
- `.claude-plugin/plugin.json` + `.claude-plugin/marketplace.json` + `gemini-extension.json` — version 0.3.2 → 0.4.0

No breaking changes. Existing opt-in paths (inline flag / command / trigger phrases) continue to work unchanged and take precedence over the new auto-dispatch.

## [0.3.2] — 2026-04-20

### Changed — normalized loss as canonical trace form

Every LDD loss value in the trace block and `.ldd/trace.log` now displays as **normalized [0, 1] primary + raw `(N/max)` secondary**. Replaces the v0.3.1 absolute-integer form (`loss_0 = 3`, `Δloss = +3`) with `loss_0 = 0.375  (3/8 violations)`.

**Why.** Skills have different rubric-maxes: `e2e-driven-iteration` has 5 items, `architect-mode` has 10. Comparing `Δloss = +3` (e2e) to `Δloss = +6` (architect) was apples-to-oranges; `0.600` vs. `0.600` is directly comparable. The raw `(N/max)` in parens keeps actionability — the user still sees "3 of 8 items remain open."

**Three display modes**, chosen per task by the shape of the measurement, named on a new `Loss-type` header line:

- `normalized-rubric` — `loss = violations / rubric_max` → float in [0, 1] plus raw in parens (default for most skills)
- `rate` — signal already in [0, 1] (flake rate, coverage) → single float, no re-normalization
- `absolute-<unit>` — unbounded continuous signal (latency, throughput) → absolute value with unit, no normalization (normalizing an unbounded value invents a denominator and produces fake precision)

**Anti-patterns now spelled out explicitly in `skills/using-ldd/SKILL.md`:**

- Never display a normalized float without the raw denominator in parens — `loss_0 = 0.375` alone hides that it's `3/8`
- Never normalize a count that has no natural max (latency, commit counts, token usage) — those stay `absolute-<unit>`

### Changed — aggregate target simplified

`Δloss_bundle` target moves from absolute (`≥ 2.0 mean violations removed per skill`) to **normalized (`≥ 0.30`** — each skill removes ≥ 30 % of rubric violations that appear without it). Current measured: **`Δloss_bundle = 0.561`** across all 11 skills — target met with margin. Raw absolute mean (3.91, v0.3.1 form) retained in git history but no longer cited.

Per-skill normalized Δloss ranges from 0.250 (`loop-driven-engineering`, partial-contamination baseline) to 1.000 (`architect-mode`). `tests/README.md` now leads with the normalized column; raw `(N/max)` kept for audit.

### Plugin-reference conformance — final audit

Full audit against `https://code.claude.com/docs/en/plugins-reference`:

- **Manifest** — `name` required field present. All recommended optional fields present: `version`, `description`, `author` (with `url`), `homepage`, `repository`, `license`, `keywords`.
- **Marketplace** — `$schema`, `name`, `description`, `owner` (with `url`), `plugins` array with per-entry `name`, `description`, `version`, `source`, `category`, `homepage`, `author`. Matches the shape used by plugins already accepted in `claude-plugins-official`.
- **Skills** — 12 `skills/<name>/SKILL.md` files, each with `name` + `description` frontmatter; directory name matches `name` field in every case (verified via script).
- **Commands** — 7 `commands/*.md` files, each with `description` frontmatter.
- **Structure** — `.claude-plugin/` contains only `plugin.json` and `marketplace.json`; all component dirs at plugin root. Zero violations of the "components at root, not inside `.claude-plugin/`" rule.
- **No agents / hooks / MCP / LSP / monitors** — none needed for this plugin; fields omitted cleanly (all optional per reference).

### Updated

- `skills/using-ldd/SKILL.md` — trace-block spec rewritten for normalized loss + `Loss-type` header line + 3-mode spec + anti-patterns
- `skills/architect-mode/SKILL.md` — trace example updated; Phase 4 scoring cells now show `0.778 (14/18)` form
- `evaluation.md` — target reformulated to `≥ 0.30` normalized; measured `0.561`; "why normalized" section added
- `tests/README.md` — per-skill table leads with normalized Δloss column; raw `(N/max)` kept for audit
- `docs/ldd/convergence.md` — new §5 "Loss display" explaining the three modes
- `README.md` — hero badge updated to `Δloss_bundle = 0.561 (normalized)`; measured-section reframed
- `.claude-plugin/plugin.json` — `description` updated; version 0.3.1 → 0.3.2
- `.claude-plugin/marketplace.json` + `gemini-extension.json` — version 0.3.2

No breaking changes. Existing traces in `tests/e2e/v031-runs/` are historical artifacts and retain the old absolute display; all new traces emit the normalized form.

## [0.3.1] — 2026-04-20

### Added — creativity levels for architect-mode

Architect-mode gains a `creativity` sub-parameter with three discrete levels, framed consistently with LDD's neural-code-network metaphor. The levels are **three different loss functions**, not three amounts of freedom:

- **`conservative`** — `L = rubric_violations + λ · novelty_penalty`. Enterprise / no-new-tech / small team. All 3 candidates must be battle-tested; component novelty penalized; team-familiarity weighted 2× in scoring. Adds rubric item #11 (novelty penalty).
- **`standard`** (default) — `L = rubric_violations`. The current v0.3.0 architect-mode behavior, unchanged.
- **`inventive`** — `L = rubric_violations_reduced + λ · prior_art_overlap_penalty`. Research / prototype. Novelty rewarded, prior-art penalized, with mandatory experiment-validation path + fallback-to-standard baseline. Rubric items 1–2 may relax; items 5–8 replaced by invention-specific criteria (#I1 differentiation-from-prior-art, #I2 experiment-validation-path, #I3 fallback-to-baseline-named). Requires per-task user acknowledgment before running.

### Hard guards against moving-target-loss

- **No integer tuning.** Three named alternatives only — "dial up until creative" is the exact drift anti-pattern LDD fights. Discrete objectives prevent it.
- **No level-switching mid-task.** Mixing two loss functions in one gradient descent is incoherent optimization. Agent refuses and requires task restart.
- **`inventive` is per-task only.** Cannot be set as project-level default in `.ldd/config.yaml`; agent ignores and downgrades to `standard` with a trace warning if it finds one.
- **Default stays `standard`.** No behavior change for existing architect-mode users.

### Integration

- `skills/architect-mode/SKILL.md`: new §§ Creativity levels, Level-switch prohibition, Project-level config restriction, plus description updated to mention the three levels
- `docs/ldd/hyperparameters.md`: `creativity` added as 5th knob (architect-mode-only sub-parameter)
- `docs/ldd/architect.md`: new § Creativity levels
- `docs/ldd/convergence.md`: new § 7 framing creativity as loss-function selection within the ML lens
- `docs/ldd/config.example.yaml`: `creativity: standard` example + `inventive` restriction comment
- `skills/using-ldd/SKILL.md`: inline syntax `LDD[mode=architect, creativity=<level>]:`, trace-block header now shows `Loss-fn` line naming the active objective
- `commands/ldd-architect.md`: accepts positional or `creativity=<level>` argument, runs acknowledgment flow for `inventive`
- `evaluation.md`: per-level rubric variants (`R_arch_standard` / `R_arch_conservative` / `R_arch_inventive`)
- README: new "Creativity — three loss functions, not a freedom dial" sub-section; hyperparameter table extended to 5 rows; install-in-30-seconds block unchanged

### Rationale

The user asked for a "freedom dial from 1=structural to 10=new paradigms". Dialectical review rejected the 1–10 framing:

- 10 grades would not have 10 measurably distinct behaviors (grades 6 vs. 7 would blur)
- Integer knobs invite "tune until output feels creative" — the exact moving-target-loss pattern every LDD skill fights
- Creativity isn't a quantity; it's a **choice of objective**. Architecture optimizing for "minimize novelty" and architecture optimizing for "maximize differentiation from prior art" are two different problems, not two degrees of the same problem

Three discrete loss functions solve the original intent (letting the user pick between conservative / standard / inventive postures) without opening a drift attack surface.

### Version

Bumped to `0.3.1` across `plugin.json`, `marketplace.json`, `gemini-extension.json`. No breaking changes — `standard` (default) behaves identically to v0.3.0 architect-mode.

## [0.3.0] — 2026-04-20

### Added — architect mode

- **New opt-in skill `architect-mode`** (`skills/architect-mode/SKILL.md`) — flips LDD from reactive debugging into constructive architecture when the user signals design intent. Rigid 5-phase protocol: Constraint extraction → Non-goals → 3 candidates on a load-bearing axis → Scoring + dialectical pass → Deliverable (doc + compilable scaffold + failing tests per component + measurable success criteria). Explicit hand-off back to default reactive mode after Phase 5 closes.
- **10-item architect rubric** in `evaluation.md` and `tests/fixtures/architect-mode/rubric.md`.
- **Fourth hyperparameter `mode`** (`reactive` | `architect`) exposed across the existing three-path config system: inline `LDD[mode=architect]:`, `/loss-driven-development:ldd-architect` command, `.ldd/config.yaml`'s `mode` key, `/ldd-set mode=architect`. Documented in `docs/ldd/hyperparameters.md` and `docs/ldd/config.example.yaml`.
- **New slash command** `/loss-driven-development:ldd-architect` — activates architect mode for the next task, reverts to reactive after hand-off.
- **New task-type MD** `docs/ldd/architect.md` added to the dispatch table in `docs/ldd/task-types.md`.
- **Architect-variant trace block** in `skills/using-ldd/SKILL.md` — shows phases (1–5) instead of iterations, includes Mode header, emits explicit hand-off line at close.
- **Escalation protocol** for phases that cannot complete cleanly (too few constraints, fewer than 3 candidates, scoring ties within 10 %, rubric violations ≥ 3/10).
- **Trigger phrases** in `skills/using-ldd/SKILL.md` dispatch table: "design X", "architect Y", "greenfield", "from scratch", "how should I structure", "propose an architecture", "decompose this", "what's the right shape for X".

### Measured

- `architect-mode` captured clean RED + GREEN via direct API (`openai/gpt-5-mini`, T=0.7). **RED violations 10/10, GREEN violations 0/10, Δloss = +10** — **largest effect size in the bundle.** Raw artifacts at `tests/fixtures/architect-mode/runs/20260420T190302Z-clean/`.
- `Δloss_bundle` recomputed across all 11 skills: **3.91 absolute (mean per skill), 0.561 relative**. Target `≥ 2.0` met with margin (was 3.30 at n=10 in v0.2.1).

### Updated

- README hero badge: Δloss_bundle 3.30 → 3.91; skill count badge "10 + entry" → "10 + architect + entry".
- README adds an "Architect mode — Claude as designer, not just debugger (opt-in)" section with 5-phase summary, activation paths, hand-off, and effect-size citation.
- `AGENTS.md`, `GEMINI.md` extended to twelve skills.
- Hyperparameter table in README adds `mode` row.
- Version bumped to `0.3.0` across `plugin.json`, `marketplace.json`, `gemini-extension.json`.

### Rationale

LDD v0.2.x was entirely reactive — it assumed code existed and iterated on loss signals. That framing missed the input-X-to-output-Y space between problem and delivered system: decomposition, contracts, non-goals, architecture. `architect-mode` fills exactly that gap, but as **opt-in** — default behavior for routine debugging/refactoring is unchanged; the 5-phase ceremony only runs when the user signals greenfield design intent.

## [0.2.1] — 2026-04-20

### Added

- **`docs/ldd/`** — canonical methodology directory. Task-type-specific compressed MDs (`debugging.md`, `design-decisions.md`, `refactor.md`, `refinement.md`, `release.md`, `incident.md`, `method-maintenance.md`) with `task-types.md` as the dispatch table. Prevents methodology drift across README / skill bodies / user-project docs. Moved `convergence.md` and `in-awp.md` here; updated all cross-links.
- **`scripts/capture-clean-baseline.py`** — portable tool to capture RED baselines via direct LLM API (OpenRouter / OpenAI / Anthropic). Sidesteps the Claude-Code-subagent contamination problem that previously blocked `docs-as-definition-of-done` measurement.
- **Tier-3.9 E2E capture** — `tests/e2e/scenario-01-refactor/runs/20260420T164505Z/`: skills installed at `~/.claude/skills/` (not prompt-injected), subagent discovered and applied them at runtime, 7/7 rubric items, loop closed k=1/5.
- **N=3 distribution demo** — `tests/fixtures/root-cause-by-layer/runs/20260420T165603Z-clean-N3/`: 3 independent RED captures via `capture-clean-baseline.py`, all same failure mode (type-tolerance shim), stddev ≈ 0.5.
- **Second scenario** for `root-cause-by-layer` (`tests/fixtures/root-cause-by-layer/scenario-2/`): different domain (rate-limiter precondition) exercising the same skill. Partial scenario-design-bias reduction.

### Changed

- `Δloss_bundle` recomputed across all 10 skills (was 9 of 10 in v0.2.0): **3.30 absolute (mean per skill), 0.517 relative**. Target `≥ 2.0` met with margin. Previously-blocked `docs-as-definition-of-done` now clean-measured at Δloss = +2.
- `evaluation.md` reflects n=10 aggregate.
- `tests/README.md` published per-skill table updated.
- `GAPS.md` rewritten: what's actually closed, what's still open, what only adopters can close.
- Version bumped to `0.2.1` across `plugin.json`, `marketplace.json`, `gemini-extension.json`.

### Still pending

- Real tier-4 (`/plugin install` in a live Claude Code / Codex / Gemini CLI session) — needs an adopter.
- N≥10 distributions per skill — infrastructure in place; needs community runs.
- Independent (non-author) scenario design — community PRs welcome.

## [0.2.0] — 2026-04-20

### Added

- **Three-loop model.** Formalised the inner (code), refinement (deliverable), and outer (method) loops as three orthogonal optimization axes. Mental model in [`docs/ldd/convergence.md`](./docs/ldd/convergence.md).
- **Five new skills** extending v0.1's inner-loop focus:
  - `reproducibility-first` — gate before any gradient use
  - `e2e-driven-iteration` — measure-per-iteration inner-loop rhythm
  - `iterative-refinement` — y-axis SGD on deliverables
  - `method-evolution` — outer-loop θ-axis SGD on skills / rubrics
  - `drift-detection` — periodic full-repo scan for cumulative drift
- **Six diagrams** as Graphviz SVGs (GitHub-renderer-compatible, no `feDropShadow`):
  - `three-loops.svg`
  - `convergence-vs-divergence.svg`
  - `code-drift-mechanism.svg`
  - `skill-dispatch-flow.svg`
  - `mental-model-ldd.svg`
  - `skills-overview.svg`
- **Case study** [`docs/ldd/in-awp.md`](./docs/ldd/in-awp.md) — one-to-one mapping from LDD skills to their [AWP](https://github.com/veegee82/agent-workflow-protocol) origins + a concrete debugging walkthrough.
- **Optional Claude-Code tooling** under `scripts/`:
  - `drift-scan.py` — heuristic scanner for seven drift indicators
  - `evolve-skill.sh` — RED/GREEN re-run scaffolder for a skill against its fixture
  - `render-diagrams.sh` — `.dot → .svg` regenerator
- **Rubrics** for all 10 skills in [`evaluation.md`](./evaluation.md).
- **Test fixtures** scaffolded for the 5 new skills (scenario + rubric + baseline-notes per skill) in [`tests/fixtures/`](./tests/fixtures/).

### Changed

- `loop-driven-engineering` now exposes the three loops explicitly (was a single inner loop in v0.1), dispatches the 9 other skills in this plugin at the right moments, and keeps the inner-loop `K_MAX = 5` budget unchanged.
- Install instructions use real `git clone` commands with the published GitHub URL — no more `/path/to/…` placeholders.
- README reshaped for marketing-first: hero with TDD anchor, "Without LDD / With LDD" table, AWP-case-study callout, skills overview SVG replacing the earlier ASCII diagram.
- Version bumped to `0.2.0` across `plugin.json`, `marketplace.json`, and `gemini-extension.json`.

### Known gaps

See [`GAPS.md`](./GAPS.md). Headline items:

- Baselines for the 5 new skills are scaffolded, not captured — RED/GREEN execution pending in a clean environment.
- No tier-4 live-install E2E has been captured end-to-end.
- `Δloss_bundle` is defined in `evaluation.md` but not yet measured.

## [0.1.0] — 2026-04-19

### Added

- Initial 5 skills: `root-cause-by-layer`, `loss-backprop-lens`, `dialectical-reasoning`, `docs-as-definition-of-done`, `loop-driven-engineering`.
- Multi-platform distribution: `.claude-plugin/plugin.json` + `marketplace.json` (Claude Code), `gemini-extension.json` + `GEMINI.md` (Gemini CLI), `AGENTS.md` (Codex + generic).
- `evaluation.md` with per-skill rubrics for the 5 initial skills.
- `tests/fixtures/` for the 5 initial skills (with baseline-contamination caveats documented in per-fixture `baseline-notes.md`).
- `tests/e2e/scenario-01-refactor/` — starter code and task spec for a tier-4 integration run.
- `GAPS.md` honest accounting of what is not verified.
