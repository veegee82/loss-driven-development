# Changelog

All notable changes to this plugin are documented here. Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/). This project uses [Semantic Versioning](https://semver.org/).

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
