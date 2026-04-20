# Loss-Driven Development (LDD)

> **LDD is to AI-era coding what TDD is to human coding.** Five portable skills for any coding agent (Claude Code · Codex · Gemini CLI · Aider · Cursor · Copilot CLI · Continue.dev).

In TDD, a red test is your ground truth — no line of code ships without a falsifiable check. In LDD, a **loss signal** (a failing test, a rejected gate, a stale doc, an unreviewed assumption) is the ground truth — and the edit is only admissible if it's an honest step down the gradient, not an overfit to the nearest symptom.

## The five skills

Each skill was developed via TDD-for-skills (RED → GREEN → REFACTOR) with baseline pressure scenarios run against fresh subagents. See [`evaluation.md`](./evaluation.md) for the formal loss function and E2E definition, and [`tests/`](./tests/) for reproducible pressure scenarios.

| Skill | Type | When it fires |
|---|---|---|
| **root-cause-by-layer** | discipline (rigid) | Any bug / failing test / unexpected behavior — forbids symptom patches until a 5-layer diagnosis (Symptom → Mechanism → Contract → Structural origin → Conceptual origin) is written out |
| **loss-backprop-lens** | pattern | Deciding *whether* to edit, *how big* the edit should be, *whether a fix generalizes*. Frames code changes as SGD steps; flags overfitting |
| **dialectical-reasoning** | discipline (rigid) | Any non-trivial recommendation, plan, trade-off, or review note — enforces thesis → antithesis → synthesis before shipping an opinion |
| **docs-as-definition-of-done** | discipline (rigid) | Before any commit on a behavior / API / CLI / config change — forbids "I'll update docs later" |
| **loop-driven-engineering** | pattern (dach) | Start of any non-trivial engineering task — orchestrates plan → code → gate pyramid → diagnose → repeat with a hard K_MAX=5 iteration budget, and dispatches the four skills above at the right moments |

## One-page philosophy

Engineering is **gradient descent on code**:

- A test / CI / E2E run is a **forward pass**.
- The delta between expected and actual is the **loss**.
- Every edit is an **SGD step** — many edits are noise, not signal.
- A symptom patch that turns the current test green but violates a contract or invariant is **overfitting**: low training loss, high generalization loss. **Rejected even when CI is green.**
- Docs are the **regularizer**: they pin the conceptual model; letting them drift raises generalization loss silently.

The five skills implement this. `root-cause-by-layer` computes the gradient. `loss-backprop-lens` picks the step size. `dialectical-reasoning` checks the direction. `docs-as-definition-of-done` applies the regularizer. `loop-driven-engineering` runs the optimizer with a budget and an escape hatch.

## Installation

The skill content (`skills/*/SKILL.md`) is identical across platforms. Only the distribution format differs.

### Claude Code

```bash
# Register as local marketplace (one-time)
/plugin marketplace add /path/to/loss-driven-development

# Install
/plugin install loss-driven-development@loss-driven-development-dev
```

Skills appear as `loss-driven-development:<name>` and can be invoked via the `Skill` tool or triggered automatically when their `description` matches the task. Or drop `skills/*` into `~/.claude/skills/` for a personal install without the plugin mechanism.

### Codex (OpenAI)

Codex reads `AGENTS.md` at the project root — copy this repo (or just `AGENTS.md` + `skills/`) into your project. For a global install, place `skills/` into your Codex personal-skills directory.

### Gemini CLI

```bash
gemini extensions install /path/to/loss-driven-development
```

`gemini-extension.json` registers the extension; `GEMINI.md` `@`-imports the five skill files.

### Aider · Cursor · Copilot CLI · Continue.dev · generic

These read ambient instruction files (`.cursorrules`, `.github/copilot-instructions.md`, `CONVENTIONS.md`, project system prompts). Either reference the skills directory from your agent's instruction file, or copy the SKILL.md bodies inline. See [`AGENTS.md`](./AGENTS.md) for per-platform recipes.

## How the skills activate

1. **Automatic** — the agent reads each skill's `description` (YAML frontmatter) and invokes when triggers match. Descriptions are written to be discriminating.
2. **Explicit** — the user names the skill (Claude Code: `/loss-driven-development:root-cause-by-layer`; other agents: point at the file).

`loop-driven-engineering` is the entry point for multi-step work; it composes the others rather than duplicating them.

## Relation to `superpowers`

Complementary, not a replacement, for [`obra/superpowers`](https://github.com/obra/superpowers):

- `superpowers:brainstorming` / `writing-plans` / `test-driven-development` / `verification-before-completion` — process skills. `loop-driven-engineering` dispatches to these when available.
- `superpowers:systematic-debugging` overlaps with `root-cause-by-layer`: prefer `root-cause-by-layer` for the explicit 5-layer discipline, `systematic-debugging` for the broader "where do I start" framing.

Install both.

## Design notes

Each skill follows the portable agent-skill format (YAML frontmatter + markdown body). The `description` field is **triggering conditions only**, never a workflow summary — summary-as-description lets agents skip the body.

Rigid discipline skills (`root-cause-by-layer`, `dialectical-reasoning`, `docs-as-definition-of-done`) each include: a spirit-vs-letter clause, a Red Flags list of rationalizations, a Rationalizations → Reality table from real baselines, and an Anti-Pattern catalog.

Pattern skills (`loss-backprop-lens`, `loop-driven-engineering`) are mental models with dispatch tables, not procedures.

## What's tested, what's not

Honestly documented in [`GAPS.md`](./GAPS.md). TL;DR: each skill has a RED-GREEN baseline captured (with caveats on baseline contamination when run from an AWP-instrumented environment). The bundle has **not** been installed into a live Claude Code session end-to-end; that's the Tier-5 gate you close when you try it.

## License

MIT — see [LICENSE](./LICENSE).

## Author

Silvio Jurk — `silvio.jurk@googlemail.com`.

## Attribution

Distilled from an in-project `CLAUDE.md` (AWP — Agent Workflow Protocol). The loss/backprop framing and the 5-Why-by-Layer protocol originate there; the generalized, platform-agnostic form is what this bundle ships.
