# Changelog

All notable changes to this plugin are documented here. Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/). This project uses [Semantic Versioning](https://semver.org/).

## [0.2.0] — 2026-04-20

### Added

- **Three-loop model.** Formalised the inner (code), refinement (deliverable), and outer (method) loops as three orthogonal optimization axes. Mental model in [`docs/convergence.md`](./docs/convergence.md).
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
- **Case study** [`docs/ldd-in-awp.md`](./docs/ldd-in-awp.md) — one-to-one mapping from LDD skills to their [AWP](https://github.com/veegee82/agent-workflow-protocol) origins + a concrete debugging walkthrough.
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
