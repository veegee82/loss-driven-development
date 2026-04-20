# engineering-loop

A Claude Code plugin that installs five composable skills for **loss-driven engineering discipline** across any codebase. Project-agnostic. Works the same in a fresh repo and in one with its own conventions.

## What you get

Five skills, one plugin. Each skill is TDD-verified (pressure-tested with a subagent before the skill was written, re-tested with the skill loaded).

| Skill | Type | When it fires |
|---|---|---|
| **root-cause-by-layer** | discipline (rigid) | Any bug / failing test / unexpected behavior — forbids symptom patches until 5-layer diagnosis (Symptom → Mechanism → Contract → Structural origin → Conceptual origin) is written out |
| **loss-backprop-lens** | pattern | Deciding *whether* to edit, *how big* the edit should be, *whether a fix generalizes*. Frames code changes as SGD steps and flags overfitting |
| **dialectical-reasoning** | discipline (rigid) | Any non-trivial recommendation, plan, trade-off, or review note — enforces thesis → antithesis → synthesis before shipping an opinion |
| **docs-as-definition-of-done** | discipline (rigid) | Before `git commit` on any behavior / API / CLI / config change — forbids "I'll update docs later" |
| **loop-driven-engineering** | pattern (dach) | Start of any non-trivial engineering task — orchestrates plan → code → gate pyramid → diagnose → repeat with a hard K_MAX=5 iteration budget, dispatches the four skills above at the right moments |

## Philosophy — one page

Engineering is **gradient descent on code**:

- A test / CI / E2E run is a **forward pass**.
- The delta between expected and actual is the **loss**.
- Every edit is an **SGD step** — which means many edits are noise, not signal.
- A symptom patch that turns the current test green but violates a contract or invariant is **overfitting**: low training loss, high generalization loss. Rejected even when CI is green.
- Docs are the **regularizer**: they pin the conceptual model. Letting them drift raises generalization loss silently.

The five skills implement this. `root-cause-by-layer` computes the gradient. `loss-backprop-lens` picks the step size. `dialectical-reasoning` checks the direction. `docs-as-definition-of-done` applies the regularizer. `loop-driven-engineering` runs the optimizer with a budget and an escape hatch.

## Installation

This plugin is distributed as a local marketplace. From any project:

```bash
# Option A: register the local dir as a marketplace (one-time)
/plugin marketplace add /home/shumway/projects/claude-engineering-loop

# Then install the plugin
/plugin install engineering-loop@engineering-loop-dev
```

After install, skills appear as `engineering-loop:<name>` and can be invoked with the `Skill` tool or picked up automatically when their `description` matches the task.

For development: you can also symlink the plugin dir into `~/.claude/plugins/cache/` if you prefer an always-current link.

## How to invoke

Skills activate in two ways:

1. **Automatic** — the model reads each skill's `description` and invokes it when the triggering conditions match. The descriptions are written to be discriminating: `root-cause-by-layer` fires on "bug / failing test / unexpected behavior," `docs-as-definition-of-done` fires on "before committing or declaring done," etc.
2. **Explicit** — the user types `/engineering-loop:root-cause-by-layer` (or similar) to force-load a skill.

The dach-skill `loop-driven-engineering` is the entry point for multi-step work. It composes the others rather than duplicating them.

## Relation to the `superpowers` plugin

`engineering-loop` is **complementary**, not a replacement, for `obra/superpowers`:

- `superpowers:brainstorming` / `writing-plans` / `executing-plans` / `test-driven-development` / `verification-before-completion` — general process skills. `engineering-loop` composes these via `loop-driven-engineering`.
- `superpowers:systematic-debugging` overlaps with `root-cause-by-layer`; prefer `root-cause-by-layer` when you want the explicit 5-layer ladder, and `systematic-debugging` for the broader investigation framing.

Install both. They reinforce each other.

## Design notes

Each skill in `skills/*/SKILL.md` follows the standard agent-skill format (YAML frontmatter + markdown body). The frontmatter `description` field is written to be **triggering conditions only**, never a workflow summary — per the observation in `superpowers:writing-skills` that description-as-summary causes the model to skip the body.

The rigid-discipline skills (`root-cause-by-layer`, `dialectical-reasoning`, `docs-as-definition-of-done`) include:
- An explicit "spirit vs letter" clause
- A Red Flags list of rationalizations to self-check against
- A "Common Rationalizations → Reality" table captured from real baseline runs
- An Anti-Pattern catalog

The pattern skills (`loss-backprop-lens`, `loop-driven-engineering`) are framed as mental models with dispatch tables, not as procedures to follow mechanically.

## Testing methodology

Each skill was developed via **TDD-for-skills** (RED → GREEN → REFACTOR):

1. **RED:** a pressure scenario was run against a fresh subagent with no skill loaded. The baseline behavior (rationalizations, symptom patches, skipped counter-cases) was captured.
2. **GREEN:** the skill was written to address the specific rationalizations observed, then the scenario was re-run with the skill loaded to verify compliance.
3. **REFACTOR:** new rationalizations surfacing in the green run are folded back into the Rationalizations table and Red Flags list.

The `tests/` directory (not yet shipped) will hold the pressure scenarios so the skills can be re-verified when edited.

## License

MIT — see `LICENSE`.

## Author

Silvio Jurk — `silvio.jurk@googlemail.com`

## Attribution

Distilled from a real in-project `CLAUDE.md` (AWP — Agent Workflow Protocol) whose specific vocabulary was stripped to make the skills work in any codebase. The loss/backprop framing and the 5-Why-by-Layer protocol originate there; the generalized, project-agnostic form is what this plugin ships.
