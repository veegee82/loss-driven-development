# docs/ldd/ — LDD methodology reference

This directory is the **canonical home for LDD methodology text** — the practitioner-facing part of the [**Gradient Descent for Agents**](../theory.md) framework. Every LDD skill links back into here; every user-project that installs LDD should reference these files rather than copying methodology into their own docs (which would drift). The long-form theory (four-loop architecture, formal loss, quantitative dialectic) lives in [`../theory.md`](../theory.md); this directory is the task-scoped practitioner cuts.

## What lives here

| File | When to read | Length |
|---|---|---|
| [`task-types.md`](./task-types.md) | **ALWAYS — the dispatch table.** Tells Claude Code which MDs to load per task type | ~1 page |
| [`getting-started.md`](./getting-started.md) | First time you encounter LDD or start an LDD-governed task | ~1 page |
| [`overview.md`](./overview.md) | Need the one-page picture of the whole bundle | ~1 page |
| [`debugging.md`](./debugging.md) | A bug, failing test, flaky run — inner loop | ~2 pages |
| [`design-decisions.md`](./design-decisions.md) | Architecture choice, ship/don't-ship call, trade-off | ~1 page |
| [`refactor.md`](./refactor.md) | Structural change, step-size calibration | ~1 page |
| [`refinement.md`](./refinement.md) | Deliverable is good-enough-not-great — y-axis loop | ~1 page |
| [`release.md`](./release.md) | Pre-commit / pre-release, drift scan | ~1 page |
| [`incident.md`](./incident.md) | Production fire, fast-path diagnosis | ~1 page |
| [`method-maintenance.md`](./method-maintenance.md) | Skill itself might be wrong — outer loop | ~1 page |
| [`convergence.md`](./convergence.md) | Formal mental model: four loops, divergence patterns, drift taxonomy | ~5 pages (heavy reference) |
| [`thinking-levels.md`](./thinking-levels.md) | Step-size controller — how the agent picks rigor per task (L0 reflex → L4 method) before any gradient descends | ~2 pages |
| [`in-awp.md`](./in-awp.md) | You want to see LDD running in a full framework (AWP) | ~3 pages |

## How Claude Code (and other agents) use this

A user project that installs LDD should have an `AGENTS.md` / `CLAUDE.md` that ends with a **Required Reading by Task Type** table pointing here. The agent consults that table first — so it loads the **minimal relevant context** for the current task rather than re-reading the whole methodology on every interaction.

See [`task-types.md`](./task-types.md) for the mapping. The skill `using-ldd` dispatches these files alongside its trigger-phrase table.

## Why this directory structure

Three properties LDD demands:

1. **Single source of truth.** Methodology text exists in exactly one place. Anywhere else (README, skill bodies, user-project docs) references back via relative link.
2. **Task-scoped loading.** A debugging session does not need `refinement.md` loaded; a release-check does not need `debugging.md`. Loading the whole methodology on every interaction wastes context.
3. **Drift resistance.** Per [`../../skills/docs-as-definition-of-done/SKILL.md`](../../skills/docs-as-definition-of-done/SKILL.md), every behavior change must be matched by exactly one doc edit in this directory — not N copies across N places that slowly diverge.

## For user-project integration

If you are LDD-installed in your project, add this snippet to your `CLAUDE.md` / `AGENTS.md`:

```markdown
## LDD — loss-driven development

This project uses the LDD methodology. When you approach a task,
select the relevant context via the dispatch table at:
  .claude/plugins/cache/.../loss-driven-development/docs/ldd/task-types.md
(or equivalent path where the plugin is installed)

Minimum-compliance behaviors are listed in:
  skills/using-ldd/SKILL.md

The `LDD:` message prefix guarantees bundle activation.
```

Replace the cache path with wherever your agent installed the plugin. For Codex: reference `AGENTS.md` of the plugin. For Gemini CLI: reference the extension's GEMINI.md.
