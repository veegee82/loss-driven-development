# Loss-Driven Development (LDD) — Skills for any coding agent

Five composable skills for **loss-driven development** — the AI-era counterpart of TDD. Platform-agnostic content; multiple distribution formats so the same skills work in Claude Code, Codex, Gemini CLI, Aider, Cursor, Copilot CLI, and any agent that reads project-level instruction files.

## What this is

The skills in `skills/*/SKILL.md` follow the portable agent-skill format (YAML frontmatter with `name` + `description`, followed by a markdown body). They are **behavior-shaping** files — they tell the agent *how* to think about a failing test, a design decision, a doc-sync check — not *what* APIs to call.

Because the content is markdown, any agent that can load instructions from files in the repo can use them. The distribution format (plugin manifest, context file, ambient loader) differs per platform; the skills themselves do not.

## Loading per platform

### Claude Code

```bash
# Register as local marketplace
/plugin marketplace add /path/to/loss-driven-development

# Install
/plugin install loss-driven-development@loss-driven-development-dev
```

Skills appear as `loss-driven-development:<name>` and can be invoked via the `Skill` tool or triggered automatically when their `description` matches the task.

### Codex (OpenAI)

Codex reads `AGENTS.md` at the project root and applies it to the session. Two options:

1. **Per-project** — keep this file in your repo root. Codex picks it up automatically.
2. **Global** — copy the `skills/` directory into `~/.agents/skills/` (if your Codex installation supports personal skills). Each `SKILL.md` is then available ambient.

### Gemini CLI

Install as an extension:

```bash
gemini extensions install /path/to/loss-driven-development
```

`gemini-extension.json` declares the extension and points at `GEMINI.md`, which `@`-imports the five `SKILL.md` files.

### Aider / Cursor / Copilot CLI / Continue.dev / generic

These agents read ambient instruction files (`.cursorrules`, `.github/copilot-instructions.md`, `CONVENTIONS.md`, project-level system prompts). Two portable options:

1. **Copy the skill bodies** into your agent's instruction file. Each `SKILL.md` body stands alone.
2. **Reference the skills directory** from your agent's instruction file: `When debugging / planning / committing, consult skills/root-cause-by-layer/SKILL.md (etc.) in this repo.`

## Skill directory

Twelve skills (see [`docs/ldd/convergence.md`](./docs/ldd/convergence.md)).

| Skill | Loop | Type | Fires when |
|---|---|---|---|
| `using-ldd` | entry | bootstrap | Start of conversation; trigger-phrase table for all others |
| `loop-driven-engineering` | (dach) | pattern | Start of any non-trivial engineering task |
| `reproducibility-first` | inner | discipline | Failing test / flaky run / surprising log before treating as gradient |
| `root-cause-by-layer` | inner | discipline | Any bug / failing test / unexpected behavior |
| `loss-backprop-lens` | inner | pattern | Deciding whether/how-big an edit, or whether a fix generalizes |
| `e2e-driven-iteration` | inner | discipline | Inside a fix-loop — every iteration runs E2E and measures Δloss |
| `dialectical-reasoning` | all | discipline | Non-trivial recommendation, plan, trade-off, review note |
| `iterative-refinement` | refinement | pattern | A complete deliverable that's "good enough not great" |
| `method-evolution` | outer | pattern | Same rubric violation in 3+ distinct tasks |
| `drift-detection` | outer | pattern | Periodic full-repo scan for cumulative drift |
| `docs-as-definition-of-done` | closes every loop | discipline | Before committing any behavior / API / CLI / config change |
| `architect-mode` | **opt-in** | discipline (5-phase protocol) | Greenfield design / architecture / structural-decomposition tasks; activated via `LDD[mode=architect]:`, `/ldd-architect`, or auto-trigger phrases ("design", "architect", "from scratch", "greenfield") |

## The `LDD:` buzzword

Users can prefix any message with `LDD:` to guarantee bundle activation. The agent will announce `*Invoking <skill-name>*:` before every skill application. See `skills/using-ldd/SKILL.md` for the full trigger-phrase table.

## Principle — one page

Engineering is **gradient descent on code**. Tests are forward passes. The delta between expected and actual is the loss. Every edit is an SGD step — many are noise, not signal. A symptom patch that turns the current test green but violates a contract is **overfitting**: low training loss, high generalization loss. Rejected even when CI is green.

Docs are the **regularizer** — they pin the conceptual model; drift raises generalization loss silently.

LDD separates three optimization loops: **inner** (θ = code), **refinement** (θ = deliverable, y-axis), **outer** (θ = skills / rubrics, θ-axis). Mixing them is the single biggest cause of "iterative work that never converges." Full mental model in [`docs/ldd/convergence.md`](./docs/ldd/convergence.md); pictures in [`diagrams/`](./diagrams/).

## Methodology

Each skill was developed via **TDD-for-skills** (RED → GREEN → REFACTOR):

1. **RED:** pressure scenario run against a fresh subagent with no skill loaded — baseline rationalizations captured verbatim.
2. **GREEN:** skill written to address those specific rationalizations — scenario re-run to verify compliance.
3. **REFACTOR:** new rationalizations surfacing in the green run fold back into the skill's Red Flags and Rationalizations tables.

## License

MIT.

## Author

Silvio Jurk (`silvio.jurk@googlemail.com`).

## Attribution

Distilled from a real in-project `CLAUDE.md` (AWP — Agent Workflow Protocol). The loss/backprop framing and the 5-Why-by-Layer protocol originate there; the generalized, platform-agnostic form is what this plugin ships.
