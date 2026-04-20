# engineering-loop

A portable skills bundle for **loss-driven engineering discipline** — works with any LLM-based coding agent (Claude Code, Codex, Gemini CLI, Aider, Cursor, Copilot CLI, Continue.dev, …). Five composable behavior-shaping skills; one repo; multiple distribution formats.

## What you get

Five TDD-verified skills (each pressure-tested with a subagent before the skill was written, re-tested with the skill loaded):

| Skill | Type | When it fires |
|---|---|---|
| **root-cause-by-layer** | discipline (rigid) | Any bug / failing test / unexpected behavior — forbids symptom patches until a 5-layer diagnosis (Symptom → Mechanism → Contract → Structural origin → Conceptual origin) is written out |
| **loss-backprop-lens** | pattern | Deciding *whether* to edit, *how big* the edit should be, *whether a fix generalizes*. Frames code changes as SGD steps and flags overfitting |
| **dialectical-reasoning** | discipline (rigid) | Any non-trivial recommendation, plan, trade-off, or review note — enforces thesis → antithesis → synthesis before shipping an opinion |
| **docs-as-definition-of-done** | discipline (rigid) | Before any commit on a behavior / API / CLI / config change — forbids "I'll update docs later" |
| **loop-driven-engineering** | pattern (dach) | Start of any non-trivial engineering task — orchestrates plan → code → gate pyramid → diagnose → repeat with a hard K_MAX=5 iteration budget, and dispatches the four skills above at the right moments |

## Philosophy — one page

Engineering is **gradient descent on code**:

- A test / CI / E2E run is a **forward pass**.
- The delta between expected and actual is the **loss**.
- Every edit is an **SGD step** — many edits are noise, not signal.
- A symptom patch that turns the current test green but violates a contract or invariant is **overfitting**: low training loss, high generalization loss. Rejected even when CI is green.
- Docs are the **regularizer**: they pin the conceptual model; letting them drift raises generalization loss silently.

The five skills implement this. `root-cause-by-layer` computes the gradient. `loss-backprop-lens` picks the step size. `dialectical-reasoning` checks the direction. `docs-as-definition-of-done` applies the regularizer. `loop-driven-engineering` runs the optimizer with a budget and an escape hatch.

## Installation

The skill content (`skills/*/SKILL.md`) is identical across platforms. Only the distribution format differs.

### Claude Code

```bash
# Register this repo as a local marketplace (one-time)
/plugin marketplace add /path/to/engineering-loop

# Install the plugin
/plugin install engineering-loop@engineering-loop-dev
```

Skills appear as `engineering-loop:<name>` and can be invoked via the `Skill` tool or triggered automatically when their `description` matches the current task. Or drop `skills/*` into `~/.claude/skills/` for a personal install without the plugin mechanism.

### Codex (OpenAI)

Codex reads `AGENTS.md` at the project root. Copy this repo (or just `AGENTS.md` + `skills/`) into your project and Codex will pick it up automatically. For a global install, place the `skills/` directory into your Codex personal-skills location.

### Gemini CLI

```bash
gemini extensions install /path/to/engineering-loop
```

`gemini-extension.json` registers the extension; `GEMINI.md` `@`-imports the five skill files.

### Aider, Cursor, Copilot CLI, Continue.dev, generic

These agents read ambient instruction files (`.cursorrules`, `.github/copilot-instructions.md`, `CONVENTIONS.md`, project system prompts). Two options:

1. **Reference the skills directory** from your agent's instruction file — a one-line pointer per skill is enough for competent agents.
2. **Inline** — copy the bodies of the SKILL.md files into your agent's instruction file.

See [AGENTS.md](./AGENTS.md) for the per-platform recipe.

## How the skills activate

Two activation modes, both supported:

1. **Automatic** — the agent reads each skill's `description` (YAML frontmatter) and invokes the skill when the triggering conditions match. Descriptions are written to be discriminating: `root-cause-by-layer` fires on "bug / failing test / unexpected behavior," `docs-as-definition-of-done` fires on "before committing or declaring done," etc.
2. **Explicit** — the user names the skill (in Claude Code: `/engineering-loop:root-cause-by-layer`; in other agents: point the agent at the file).

`loop-driven-engineering` is the entry point for multi-step work — it composes the others rather than duplicating them.

## Relation to the `superpowers` plugin

`engineering-loop` is **complementary**, not a replacement, for [`obra/superpowers`](https://github.com/obra/superpowers):

- `superpowers:brainstorming` / `writing-plans` / `executing-plans` / `test-driven-development` / `verification-before-completion` — general process skills. `engineering-loop:loop-driven-engineering` dispatches to these when they are available.
- `superpowers:systematic-debugging` overlaps with `root-cause-by-layer`. Prefer `root-cause-by-layer` when you want the explicit 5-layer ladder; prefer `systematic-debugging` for the broader "where do I even start looking" framing.

Install both. They reinforce each other.

## Design notes

Each skill in `skills/*/SKILL.md` follows the portable agent-skill format (YAML frontmatter + markdown body). The frontmatter `description` field is written to be **triggering conditions only**, never a workflow summary — per the observation in `superpowers:writing-skills` that description-as-summary causes the model to skip the body.

The rigid-discipline skills (`root-cause-by-layer`, `dialectical-reasoning`, `docs-as-definition-of-done`) each include:
- An explicit "spirit vs letter" clause
- A Red Flags list of rationalizations to self-check against
- A "Common Rationalizations → Reality" table captured from real baseline runs
- An Anti-Pattern catalog

The pattern skills (`loss-backprop-lens`, `loop-driven-engineering`) are framed as mental models with dispatch tables, not as procedures to follow mechanically.

## Testing methodology

Each skill was developed via **TDD-for-skills** (RED → GREEN → REFACTOR):

1. **RED** — a pressure scenario was run against a fresh subagent with no skill loaded. The baseline behavior (rationalizations, symptom patches, skipped counter-cases) was captured verbatim.
2. **GREEN** — the skill was written to address the specific rationalizations observed, then the scenario was re-run with the skill loaded to verify compliance.
3. **REFACTOR** — new rationalizations surfacing in the green run are folded back into the Rationalizations table and the Red Flags list.

## License

MIT — see [LICENSE](./LICENSE).

## Author

Silvio Jurk — `silvio.jurk@googlemail.com`.

## Attribution

Distilled from a real in-project `CLAUDE.md` (AWP — Agent Workflow Protocol). The loss/backprop framing and the 5-Why-by-Layer protocol originate there; the generalized, platform-agnostic form is what this bundle ships.
