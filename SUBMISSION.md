# Submission package — `claude-plugins-official`

Everything you need to submit LDD to Anthropic's curated plugin directory so it appears in **every Claude Code user's `/plugin > Discover`** menu without them needing the repo URL.

## Submission URL

**https://clau.de/plugin-directory-submission**

(Anthropic's official external-plugin submission form, linked from the `claude-plugins-official` marketplace README.)

## Pre-filled form answers

Paste these verbatim into the form fields (field names may vary slightly; adapt if the form asks for different labels):

### Plugin name
```
loss-driven-development
```

### One-line description (for the `/plugin > Discover` listing)
```
LDD — Gradient Descent for Agents. Twelve portable skills across four parameter spaces (code / deliverable / method / reasoning chain) that force an agent through a measured gradient-descent work loop, blocking symptom patches, local-minimum traps, and silent code drift.
```

### Longer description (for the plugin page)
```
Loss-Driven Development is Gradient Descent for Agents. Every code change, every output revision, every skill edit, every reasoning step is an SGD step on one of four parameter spaces. The bundle installs a loss function, a gradient (5-Why-by-Layer), a step-size rule (local vs. architectural edit, picked per task by the thinking-levels auto-dispatch), and regularizers (contracts, layer boundaries, docs-as-DoD) so your agent's iteration converges instead of drifts.

Twelve skills organized across four orthogonal optimization loops: inner (code, ∂L/∂code), refinement (deliverable, ∂L/∂output), outer (methodology, ∂L/∂method), CoT (reasoning chain, ∂L/∂thought, v0.8.0). Plus cross-cutting disciplines (dialectical-reasoning, docs-as-definition-of-done, define-metric v0.9.0), the opt-in architect-mode for greenfield design, and the using-ldd entry-point with a trigger-phrase table that dispatches the right skill for the task. Users prefix any message with "LDD:" to guarantee activation; the agent announces every skill invocation.

Measured Δloss_bundle = 0.561 normalized (mean fraction of rubric violations each skill removes) across all 11 discipline skills; target ≥ 0.30 met with margin. Per-skill normalized Δloss ranges 0.250 → 1.000. All RED/GREEN rubric artifacts on disk in `tests/fixtures/`; inter-reviewer sampling, tier-3.9 E2E capture, and `capture-clean-baseline.py` + `capture-red-green.py` tooling included.

Distilled from AWP (Agent Workflow Protocol), a multi-agent orchestration framework where three of the four gradients (inner, refinement, outer) run as live SGD code.
```

### Category
```
development
```

(Candidates: `development`, `testing`, `productivity`. "development" fits best — this is a general-purpose development-workflow plugin.)

### Homepage / repository URL
```
https://github.com/veegee82/loss-driven-development
```

### License
```
MIT
```

### Author name
```
Silvio Jurk
```

### Author email
```
silvio.jurk@googlemail.com
```

### Keywords / tags
```
skills, tdd, ldd, loss-driven-development, debugging, root-cause, discipline, workflow, methodology, dialectical, documentation, coding-agent, claude-code, codex, gemini-cli
```

(These match the `keywords` field of `.claude-plugin/plugin.json` so the reviewer sees consistency.)

### Install command (if the form asks)
```
/plugin install loss-driven-development@loss-driven-development-dev
```

Note: the `-dev` suffix is from the local-marketplace name (`loss-driven-development-dev`). After Anthropic approves and vendors the plugin into `claude-plugins-official`, the actual install will be `/plugin install loss-driven-development@claude-plugins-official`.

## Suggested marketplace.json entry (for the reviewer)

Two acceptable shapes — let the reviewer pick whichever fits the directory's current conventions:

### Option A — URL-sourced (lightweight, auto-tracks upstream)

```json
{
  "name": "loss-driven-development",
  "description": "LDD — the AI-era counterpart of TDD. Twelve portable skills — ten reactive disciplines (inner / refinement / outer loops) + one opt-in architect-mode for greenfield design + the using-ldd entry-point — that force an agent through a measured gradient-descent work loop, blocking symptom patches, local-minimum traps, and silent code drift.",
  "category": "development",
  "source": {
    "source": "url",
    "url": "https://github.com/veegee82/loss-driven-development.git"
  },
  "homepage": "https://github.com/veegee82/loss-driven-development",
  "author": {
    "name": "Silvio Jurk",
    "email": "silvio.jurk@googlemail.com"
  }
}
```

This is the shape used by e.g. `adlc` and `adspirer-ads-agent` in the current `claude-plugins-official` marketplace.

### Option B — Vendored (pinned SHA, lives under `external_plugins/`)

```json
{
  "name": "loss-driven-development",
  "description": "LDD — the AI-era counterpart of TDD. Twelve portable skills — ten reactive disciplines (inner / refinement / outer loops) + one opt-in architect-mode for greenfield design + the using-ldd entry-point — that force an agent through a measured gradient-descent work loop, blocking symptom patches, local-minimum traps, and silent code drift.",
  "category": "development",
  "source": "./external_plugins/loss-driven-development",
  "homepage": "https://github.com/anthropics/claude-plugins-public/tree/main/external_plugins/loss-driven-development"
}
```

This is the shape used by e.g. `playwright`, `gitlab`, `github` in the current marketplace. Requires copying the plugin contents into `external_plugins/loss-driven-development/` in the marketplace repo.

## Review-readiness checklist (pre-submit)

Verify all ticked before sending the form:

- [x] **MIT License** — see `LICENSE`
- [x] **Working `.claude-plugin/plugin.json`** — name, description, version (0.5.0), author, license, keywords
- [x] **Working `.claude-plugin/marketplace.json`** — self-hostable marketplace
- [x] **README.md** — install-in-30-seconds up top, badges, philosophy, skill list, per-agent install, usage with `LDD:` buzzword
- [x] **CHANGELOG.md** — Keep a Changelog format, SemVer, v0.1.0 through v0.5.0 entries
- [x] **CONTRIBUTING.md** — contribution guide, focused on "run LDD and tell us where it failed"
- [x] **SECURITY.md** — vulnerability reporting channel + scope + "what this plugin does not do"
- [x] **GAPS.md** — honest accounting of what is / isn't verified (stands out — most plugins don't have this)
- [x] **evaluation.md** — formal loss function + rubrics + measured Δloss_bundle = 0.561 normalized across all 11 discipline skills
- [x] **Measured artifacts on disk** — `tests/fixtures/<skill>/runs/*` with raw RED / GREEN / score files
- [x] **Twelve skills with portable-agent-skill-format frontmatter** — each `skills/<name>/SKILL.md` has `name` and `description` (10 reactive + `architect-mode` + `using-ldd`)
- [x] **Seven SVG diagrams** (no `feDropShadow` — GitHub-renderer-safe): `diagrams/{three-loops,skills-overview,convergence-vs-divergence,code-drift-mechanism,skill-dispatch-flow,mental-model-ldd}.svg` + `docs/diagrams/architect-mental-model.svg`
- [x] **`docs/ldd/`** — canonical methodology with task-type dispatch
- [x] **No secrets, no hardcoded keys, no private URLs** — scanned clean
- [x] **Drift-scan of the repo itself comes back clean** — `python scripts/drift-scan.py --repo .` only reports the intended rubric-drift warning
- [x] **Multi-agent distribution format** — `AGENTS.md` (Codex), `GEMINI.md` + `gemini-extension.json` (Gemini CLI), `.claude-plugin/` (Claude Code), README recipes for Aider / Cursor / Copilot CLI / Continue.dev
- [x] **Version coherence** — `plugin.json`, `marketplace.json`, `gemini-extension.json` all at `0.5.0`
- [x] **GitHub repo public** — https://github.com/veegee82/loss-driven-development
- [x] **Issue templates** — `.github/ISSUE_TEMPLATE/skill-failure.md` + `bug_report.md`

## While the submission is in review

Two complementary distribution channels are already active:

1. **Direct marketplace add** — `/plugin marketplace add https://github.com/veegee82/loss-driven-development.git` works today for anyone with the URL.
2. **GitHub topics / description** — set on the repo (see "GitHub repo metadata" below) so Google / GitHub search surface it.

### GitHub repo metadata (set once via the web UI)

Go to https://github.com/veegee82/loss-driven-development/settings and set:

- **Description**: `LDD — the AI-era counterpart of TDD. Twelve portable skills for any coding agent (Claude Code · Codex · Gemini CLI · …) that turn "green test = ship" into a measured discipline.`
- **Website**: (leave empty, or point at `github.com/veegee82/agent-workflow-protocol` if cross-promoting AWP)
- **Topics** (GitHub's tag system, boosts search): `claude-code-plugin`, `claude-code`, `codex`, `gemini-cli`, `coding-agent`, `llm-methodology`, `ai-pair-programming`, `tdd`, `ldd`, `loss-driven-development`, `skills`, `agent-skills`, `mcp`, `prompt-engineering`

## After approval

1. The plugin appears in every Claude Code user's `/plugin > Discover` menu automatically (they already have `claude-plugins-official` added as a marketplace by default).
2. Install becomes `/plugin install loss-driven-development@claude-plugins-official`.
3. Update this repo's README install section to use that simpler command.
4. Optional: submit to secondary community marketplaces (`obra/superpowers-marketplace`, etc.) for extra reach.

## If review surfaces issues

Common reviewer asks and where they're already addressed:

| Reviewer concern | Where it's covered |
|---|---|
| "How does this integrate with Claude Code's Skill tool?" | `skills/using-ldd/SKILL.md` has `description` that auto-triggers; README "Using LDD" section documents the `LDD:` buzzword fallback |
| "Is the Δloss number author-scored or independent?" | `tests/README.md` documents both: author-scored across 11 discipline skills, inter-reviewer sampling on 2 fixtures (direction 100%, magnitude ±2) |
| "Does it work on fresh installs?" | Tier-3.9 E2E artifacts at `tests/e2e/scenario-01-refactor/runs/20260420T164505Z/` show the skills work via runtime discovery; real tier-4 (plugin install) flagged in `GAPS.md` as adopter-verifiable |
| "Is the rubric moving-target-loss safe?" | `drift-scan.py` has a rubric-drift indicator that flags edits to `evaluation.md` without Δloss justification; `method-evolution` skill forbids the moving-target-loss anti-pattern |
| "Are the scripts safe to run?" | `SECURITY.md` + each script's header document scope. `drift-scan.py` and `render-diagrams.sh` are read-only local; `capture-clean-baseline.py` makes outbound LLM API calls using user-supplied keys; `evolve-skill.sh` is terminal-driven with no network |

---

**Done? Submit the form.** I'll update the README install section to use the simpler `@claude-plugins-official` path once approval lands.
