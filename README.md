# Loss-Driven Development (LDD)

> **LDD is to AI-era coding what TDD was to human coding.**
> Ten portable skills for any coding agent — **Claude Code · Codex · Gemini CLI · Aider · Cursor · Copilot CLI · Continue.dev** — that turn "the test is green, ship it" into a *measured* discipline where symptom patches, local-minimum traps, and silent code drift can't hide.

> 📦 **Where this came from:** distilled from [**AWP — Agent Workflow Protocol**](https://github.com/veegee82/agent-workflow-protocol) ([`pip install awp-agents`](https://pypi.org/project/awp-agents/)), an open standard for multi-agent orchestration where all three LDD loops — inner, refinement, outer — are implemented as live SGD code, not metaphor. See [**LDD in AWP**](./docs/ldd-in-awp.md) for the one-to-one mapping, a concrete debugging case study, and how to try the framework itself.

![Three loops](./diagrams/three-loops.svg)

## The one-sentence pitch

Every code change is an SGD step. Most agents optimize training loss (the visible test) and drive generalization loss (everything else) through the roof. **LDD installs a loss function, a gradient, a step-size rule, and a regularizer — so your agent's iteration converges instead of drifts.**

## Why you want this

| Without LDD | With LDD |
|---|---|
| Agent adds `try/except` around the failing line and ships | Agent walks 5 layers of causation and fixes at the boundary |
| "It was flaky, just retry" | One sample is noise; reproduce before gradient |
| Five 3-line patches in one function this morning | Step size mismatch detected; architectural edit proposed |
| "I'll update the docs later" | Code + tests + docs land in one commit, or the work isn't done |
| Same rubric violation across tasks; nobody notices | Outer-loop `method-evolution`: the skill itself is the bug |
| README describes a system that no longer exists | Periodic `drift-detection` scan finds it before onboarding does |

## The 10 skills

![LDD skills overview — ten skills across three optimization loops, connected to the loop-driven-engineering entry-point and closed by docs-as-definition-of-done](./diagrams/skills-overview.svg)

| Skill | Type | What it catches |
|---|---|---|
| **loop-driven-engineering** | pattern (dach) | "Just start coding" without a plan or a budget |
| **reproducibility-first** | discipline | Updates on a single noisy sample |
| **root-cause-by-layer** | discipline | Symptom patches (try/except, shims, xfail, …) |
| **loss-backprop-lens** | pattern | Local-minimum traps, overfitting, wrong step size |
| **e2e-driven-iteration** | discipline | "I'll run the E2E at the end" — lost gradient |
| **dialectical-reasoning** | discipline | One-sided recommendations that skip the counter-case |
| **iterative-refinement** | pattern | Re-running from scratch when refinement is cheaper |
| **method-evolution** | pattern | Patching individual tasks when the method itself is the bug |
| **drift-detection** | pattern | Cumulative drift that no single commit introduced |
| **docs-as-definition-of-done** | discipline | "I'll update docs in a follow-up PR" |

## The philosophy in 60 seconds

Engineering is **gradient descent on code**:

- A test / CI / E2E is a **forward pass**.
- The delta between expected and actual is the **loss**.
- Every edit is an **SGD step** — most are noise if you don't check them.
- A symptom patch is **overfitting**: low training loss, high generalization loss. Rejected even when CI is green.
- Docs are the **regularizer** — keep them in sync or generalization loss rises silently.
- Budget (`K_MAX=5`) prevents descending past local minima into drift.

Full mental model in [`docs/convergence.md`](./docs/convergence.md). The convergence conditions, the five divergence patterns, the drift taxonomy — all formally stated.

## Three loops, not one

Most "iterate on code" advice treats all edits the same. LDD separates three orthogonal optimization axes:

| Loop | You edit | When |
|---|---|---|
| **Inner** | The code | Every ordinary bug / feature / refactor |
| **Refinement** (y-axis) | The deliverable (doc, diff, design) | "Good enough, not great" — polish with a real gradient |
| **Outer** (θ-axis) | The skills / rubrics themselves | Same rubric violation across 3+ tasks |

Mixing them is the single biggest reason "iterate on the problem" never converges. LDD forces the question *which parameter am I changing*. Pictures in [`diagrams/`](./diagrams/).

## Installation

Skill content (`skills/*/SKILL.md`) is identical across platforms. Only the distribution format differs.

### Claude Code (primary target)

Two install paths depending on your Claude Code version:

**Option A — via the marketplace command** (works with any version that supports `/plugin marketplace add`):

```bash
# Inside a Claude Code session:
/plugin marketplace add https://github.com/veegee82/loss-driven-development.git

# Then install from the newly-registered marketplace:
/plugin install loss-driven-development@loss-driven-development-dev
```

Skills appear as `loss-driven-development:<name>` and trigger automatically when their `description` matches the current task. Explicit invocation: `/loss-driven-development:<skill-name>`.

**Option B — personal install, no plugin mechanism** (works in every Claude Code version):

```bash
# In your shell:
git clone https://github.com/veegee82/loss-driven-development.git
mkdir -p ~/.claude/skills
cp -r loss-driven-development/skills/* ~/.claude/skills/
```

Skills now appear in every Claude Code session, any project. No namespace prefix.

### Codex (OpenAI)

Codex reads `AGENTS.md` at the project root:

```bash
git clone https://github.com/veegee82/loss-driven-development.git
# Per-project install — copy AGENTS.md + skills/ into your project root:
cp -r loss-driven-development/AGENTS.md loss-driven-development/skills your-project/

# OR global install — if your Codex version supports a personal skills dir:
mkdir -p ~/.agents/skills
cp -r loss-driven-development/skills/* ~/.agents/skills/
```

### Gemini CLI

```bash
git clone https://github.com/veegee82/loss-driven-development.git
gemini extensions install ./loss-driven-development
```

`gemini-extension.json` registers the extension; `GEMINI.md` `@`-imports the ten skills.

### Aider · Cursor · Copilot CLI · Continue.dev · generic

Read ambient instruction files (`.cursorrules`, `.github/copilot-instructions.md`, `CONVENTIONS.md`, project system prompts). Either reference the skills directory from your agent's instruction file, or copy the SKILL.md bodies inline. See [`AGENTS.md`](./AGENTS.md) for per-platform recipes.

## Optional Claude-Code tooling

`scripts/` contains three optional helpers (not required, not part of the skills):

- `scripts/drift-scan.py` — runs the seven drift indicators over a repo, produces a Markdown report
- `scripts/evolve-skill.sh` — scaffolds a RED/GREEN re-run for a skill against its fixture
- `scripts/render-diagrams.sh` — regenerates SVGs from the `.dot` sources

Run them manually, wire them into CI, or ignore them. The skills don't depend on them.

## Relation to `superpowers`

Complementary, not a replacement, for [`obra/superpowers`](https://github.com/obra/superpowers):

- `superpowers:brainstorming` / `writing-plans` / `test-driven-development` / `verification-before-completion` — process skills. `loop-driven-engineering` dispatches to these when available.
- `superpowers:systematic-debugging` overlaps with `root-cause-by-layer`: prefer `root-cause-by-layer` for the explicit 5-layer ladder, `systematic-debugging` for the broader "where do I start looking" framing.

Install both.

## How the skills were built (TDD-for-skills)

Each skill was developed via **RED → GREEN → REFACTOR**:

1. **RED** — pressure scenario run against a fresh subagent with no skill loaded. Baseline rationalizations captured verbatim.
2. **GREEN** — skill written to address those specific rationalizations; scenario re-run with the skill loaded to verify compliance.
3. **REFACTOR** — new rationalizations surfacing in the GREEN run fold back into the skill's Red Flags and Rationalizations tables.

Formal loss function, per-skill rubrics, and E2E definition in [`evaluation.md`](./evaluation.md). Reproducible pressure scenarios in [`tests/fixtures/`](./tests/fixtures/). An integration scenario starter in [`tests/e2e/scenario-01-refactor/`](./tests/e2e/scenario-01-refactor/).

## What's verified, what isn't

Honest accounting in [`GAPS.md`](./GAPS.md).

**Measured (2026-04-20):**

- 6 of 10 skills have clean RED/GREEN runs with artifacts on disk.
- **`Δloss_bundle = 3.83` absolute** (mean per skill, rubric violations removed) across those 6 — target `≥ 2.0` met with margin. Per-skill numbers and raw artifacts in [`tests/README.md`](./tests/README.md#current-measurements) and per-fixture `runs/` directories.
- **Tier-3.5 simulated E2E captured:** an agent with tool access closed the `scenario-01-refactor` loop at iteration 1/5 with 7/7 rubric items satisfied. Fix diff + commit + summary in [`tests/e2e/scenario-01-refactor/runs/20260420T160347Z/`](./tests/e2e/scenario-01-refactor/runs/20260420T160347Z/).

**Still pending:**

- 4 of 10 skills still have baseline-contamination caveats (v0.1 skills measured in an environment with ambient methodology files the subagents refused to ignore). Their GREEN behavior is shown; their RED baseline isn't clean.
- **Real tier-4** (live `/plugin install` + multi-step run against the scenario) — that's the gate you close as an early adopter. The simulated tier-3.5 is close but not identical.
- Single-run point estimates, not distributions (N=1 per skill).
- Reviewer-scored by the author; raw artifacts attached so the community can re-score.
- Word counts exceed `<500`-per-skill guidance; discipline-heavy skills are inherently denser.

Treat this as **v0.2 measured seed**. If a skill doesn't change your agent's behavior on a real pressure case, open an issue using the [`.github/ISSUE_TEMPLATE/skill-failure.md`](./.github/ISSUE_TEMPLATE/skill-failure.md) template — that's the baseline data that moves us from v0.2 measured to v0.3 generalized.

## License

MIT — see [LICENSE](./LICENSE).

## Author

Silvio Jurk — `silvio.jurk@googlemail.com` · [github.com/veegee82](https://github.com/veegee82)

## The bigger picture — AWP

LDD is the portable, platform-agnostic **discipline**. [**AWP — Agent Workflow Protocol**](https://github.com/veegee82/agent-workflow-protocol) is the full **runtime** this discipline came from — an open standard for multi-agent orchestration with two execution engines (DAG + delegation-loop), 36 normative rules, and **all three LDD loops implemented as live SGD code**:

- **Inner loop** → AWP's budget-bounded work loop (`K_MAX = 5`, test pyramid, escalation)
- **Refinement loop** → AWP's `awp refine <seed_run_dir>` — y-axis SGD on deliverables with critique-derived gradients
- **Outer loop** → AWP's `awp optimize --with-textgrad` — θ-axis SGD on prompt artifacts with TextGrad as LLM-as-optimizer, rollback on regression

If LDD as discipline makes sense to you, AWP is what it looks like when the whole framework is built around it. Read [**LDD in AWP**](./docs/ldd-in-awp.md) for the one-to-one concept mapping, a concrete debugging case study, and install instructions.

```bash
pip install awp-agents && python -m awp studio
```

⭐ Star [`veegee82/agent-workflow-protocol`](https://github.com/veegee82/agent-workflow-protocol) if LDD helped you — that's where the methodology is being pushed forward.
