# Loss-Driven Development (LDD) — Skills for any coding agent

**Twelve composable skills** for **loss-driven development** — the AI-era counterpart of TDD. Platform-agnostic content; multiple distribution formats so the same skills work in Claude Code, Codex, Gemini CLI, Aider, Cursor, Copilot CLI, and any agent that reads project-level instruction files.

**The metaphor in one paragraph**: imagine a climber on a cloud-shrouded mountain (the codebase). She can't see the summit (`L = 0`) — only her altimeter, the local slope, her log book of past climbs, and a fellow climber asking hostile questions. LDD encodes those four instruments as a reasoning discipline: *measure before every step* (inner loop), *probe the slope from a hostile angle* (dialectical reasoning), *consult the log book for patterns* (project memory), and *calibrate predictions against observations* (drift detection). Full theory with metaphor → high-level → formulas: [`docs/theory.md`](./docs/theory.md).

## What this is

The skills in `skills/*/SKILL.md` follow the portable agent-skill format (YAML frontmatter with `name` + `description`, followed by a markdown body). They are **behavior-shaping** files — they tell the agent *how* to think about a failing test, a design decision, a doc-sync check — not *what* APIs to call.

Because the content is markdown, any agent that can load instructions from files in the repo can use them. The distribution format (plugin manifest, context file, ambient loader) differs per platform; the skills themselves do not.

**Thinking-levels auto-dispatch (v0.10.1+):** every non-trivial task is auto-scored onto a 5-step rigor ladder (L0 reflex → L4 method). The scorer is deterministic (no LLM call), reads the task text, and announces `Dispatched: auto-level L<n> (signals: …)` in the trace header. Zero-config by default; overridable with a single inline token (`LDD+`, `LDD++`, `LDD=max`, `LDD[level=Lx]`) or natural-language bump phrases (`"take your time"`, `"denk gründlich"`). Upward-biased on ties. Full reference: [`docs/ldd/thinking-levels.md`](./docs/ldd/thinking-levels.md). Implementation: [`scripts/level_scorer.py`](./scripts/level_scorer.py).

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
| `bootstrap-userspace` | entry | discipline | First LDD task in a session when `.ldd/trace.log` is not writable. Silently picks the most durable persistence tier (filesystem / artifact / conversation-history / memory-pointer / inline) and announces it via `│ Store : <scope>` in the trace-block header. Makes LDD portable to Claude Desktop, ChatGPT, and other sandboxed hosts without user configuration |
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
| `architect-mode` | **opt-in** | discipline (5-phase protocol) | Greenfield design / architecture / structural-decomposition tasks; reached through the L3 / L4 presets of the thinking-levels auto-dispatch (see [`docs/ldd/thinking-levels.md`](./docs/ldd/thinking-levels.md)), or explicitly via inline `LDD[mode=architect]:` flag / `/ldd-architect` command / trigger phrases. Agent echoes the dispatch source and level in the trace header |
| `dialectical-cot` | **thought** (4th loop, v0.8.0) | discipline | Verifiable multi-step reasoning tasks (math, code, logic, proofs). Applies the v0.7.0 quantitative dialectic at every step of a chain-of-thought. Uses per-task-type memory (`.ldd/cot_memory.json`) for primer generation. Requires ground-truth verification to close the calibration loop |
| `define-metric` | **extensible foundation** (v0.9.0) | discipline | Introduce a new agent-defined metric (complexity, latency, custom rubric) as a first-class loss component. Registration → advisory-only → calibration (n≥5, MAE≤0.15) → load-bearing. Enforces gaming-guard (self-referential descriptions rejected) and bias-invariance (metric observations never modified by registry/calibrator activity) |

## The `LDD:` buzzword

Users can prefix any message with `LDD:` to guarantee bundle activation. The agent will announce `*Invoking <skill-name>*:` before every skill application. See `skills/using-ldd/SKILL.md` for the full trigger-phrase table.

## Principle — one page

Engineering is **gradient descent on code**. Tests are forward passes. The delta between expected and actual is the loss. Every edit is an SGD step — many are noise, not signal. A symptom patch that turns the current test green but violates a contract is **overfitting**: low training loss, high generalization loss. Rejected even when CI is green.

Docs are the **regularizer** — they pin the conceptual model; drift raises generalization loss silently.

LDD separates **four** optimization loops: **inner** (θ = code), **refinement** (θ = deliverable, y-axis), **outer** (θ = skills / rubrics, θ-axis), **thought** (θ = reasoning chain, v0.8.0). Mixing them is the single biggest cause of "iterative work that never converges." Three navigational instruments layer on top without modifying the loss function:

- **Project memory** (v0.5.2) — per-project aggregate at `.ldd/project_memory.json`; first-moment statistical priors over skill effectiveness
- **Memory × dialectical coupling** (v0.6.0) — `prime-antithesis` surfaces memory-derived primers for the dialectical synthesis step; Bayesian-style `confidence(action) ∝ memory × dialectical × prior`
- **Quantitative dialectic** (v0.7.0) — the synthesis step computes `E[Δloss | thesis]`, logs the prediction, and the aggregator computes `MAE` vs. observed Δloss; `drift_warning` when `MAE > 0.15` over `n ≥ 5`

Full mental model: [`docs/ldd/convergence.md`](./docs/ldd/convergence.md) (practitioner-facing) and [`docs/theory.md`](./docs/theory.md) (paper-style). Diagrams in [`diagrams/`](./diagrams/) — start with `three-loops.svg`, then `gradient-via-dialectic.svg`, `memory-dialectical-coupling.svg`, `calibration-feedback-loop.svg`.

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
