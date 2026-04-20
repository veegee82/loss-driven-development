# Known Gaps — v0.2.0

An honest list of what is **not** verified in this bundle. New users and reviewers: read this before claiming the bundle "works."

## What changed in v0.2 vs v0.1

- Added 5 new skills: `reproducibility-first`, `e2e-driven-iteration`, `iterative-refinement`, `method-evolution`, `drift-detection`
- Added 5 Graphviz-sourced SVG diagrams covering the three-loop model
- Added `docs/convergence.md` as the normative mental-model doc
- Added `scripts/` with optional Claude-Code-targeted automation (`drift-scan.py`, `evolve-skill.sh`, `render-diagrams.sh`)
- Extended `evaluation.md` with rubrics for the 5 new skills

Known gaps carry forward from v0.1 and some new ones appear.

## Evaluation gaps (carried forward)

### Baseline contamination

3 of the original 5 skill baselines were captured from a subagent that **refused to ignore** an ambient methodology `CLAUDE.md` in the parent project. Those baselines are contaminated and not a clean measurement. Affected: `loss-backprop-lens`, `docs-as-definition-of-done`, `dialectical-reasoning`.

**Fix:** re-run from a directory with no ancestor `CLAUDE.md`.

### No baselines at all for the 5 new skills

`reproducibility-first`, `e2e-driven-iteration`, `iterative-refinement`, `method-evolution`, `drift-detection` were written without RED/GREEN baseline runs — the build session exhausted the subagent rate limit before new fixtures could be run. The skills' content is grounded in the observed failure modes from v0.1 + the AWP source, but anonymous-agent pressure tests are **not** captured.

**Fix:** each skill has a fixture directory (`tests/fixtures/<skill>/`) scaffolded; run RED/GREEN per skill in a clean environment and record results.

### No aggregate Δloss computation

`evaluation.md` defines `Δloss_bundle` formally. **No one has run it.** The bundle ships with a specified target (`Δloss_bundle ≥ 2.0`) and no measured value.

**Fix:** run all 10 fixtures RED + GREEN, score against rubrics, compute. Publish in `tests/README.md#current-measurements`.

### No tier-4 run (live-install E2E)

The bundle has never been installed into a running Claude Code / Codex / Gemini CLI session and driven through a multi-step task. `tests/e2e/scenario-01-refactor/` starter code and task spec exist; no captured run. One attempted dispatch during the v0.1 build hit a rate limit before producing output.

**Fix:** install the bundle, point it at the E2E scenario, record to `tests/e2e/scenario-01-refactor/run-<timestamp>/`.

### No tier-5 run (production, unrelated repo)

No data on whether the skills hold up in a real long-running project under real pressure. Requires time, not code.

## Distribution gaps

### Claude Code auto-trigger untested

The `description` fields are written to be discriminating, but automatic invocation (the skill firing when its `description` matches the current task, without explicit `/plugin:skill` or `Skill` tool call) has **not been verified** in a live session.

### Codex skills directory path uncertain

`AGENTS.md` suggests `~/.agents/skills/` for a global Codex install. The exact path may differ by Codex installation; **not tried**. If your Codex version uses a different path, the per-project `AGENTS.md` approach still works.

### Gemini CLI extension format not re-verified

`gemini-extension.json` mirrors superpowers' format. If Gemini's schema has drifted, the manifest may need adjustment. Not test-installed.

### Aider / Cursor / Copilot CLI / Continue.dev

Documented via reference-or-inline in the ambient instruction file. **No captured test runs** on any of these. Mechanism is standard file-loading, but "should work" is not a measurement.

## Content gaps

### Skill word counts over superpowers' guideline

`superpowers:writing-skills` recommends `<500 words`; the skills in this bundle range 1100–1800 words. Heavier skills may be skimmed under pressure. Target: trim each to ~800 words in a future pass — but some discipline skills (method-evolution, e2e-driven-iteration) are inherently denser due to protocol detail.

### Cross-skill redundancy

Several anti-patterns (symptom patches, retry loops, "clean up later") appear in multiple skills. Intentional — each skill must stand alone when loaded independently — but could be tightened.

### `+optional` / `external` notation

The sub-skill dispatch table uses prose labels (`external (superpowers)`) rather than parser-friendly symbols. Agents may or may not treat this consistently; some will fail to load the external skill and silently skip the principle.

## Methodology gaps

### TDD-for-skills ran one scenario per skill, not a suite

Writing-skills recommends testing skills against multiple pressure scenarios. This bundle has one (sometimes zero) scenario per skill. Future editions should run 3+ fixtures per skill before claiming coverage.

### REFACTOR phase skipped on v0.1 and v0.2

The writing-skills TDD cycle is RED → GREEN → REFACTOR. Both iterations of this bundle shipped after one GREEN run per skill (at best). Loopholes surfacing in GREEN were not iteratively closed.

### Script quality

`scripts/drift-scan.py` is a best-effort heuristic scanner, not a static-analysis tool. Its indicators will produce false positives (e.g. scanning its own synonym lists) and miss real drift that doesn't match its patterns. Treat its output as "candidates for review," not "findings."

### `scripts/evolve-skill.sh` is terminal-driven

The script scaffolds a RED/GREEN run but does not call any LLM API. The human operator pastes prompts into a subagent and pastes responses back. Not automation — a reproducible workflow shell.

## What this means for users

The bundle is a **v0.2 seed** with more surface area than v0.1 and the same core caveat: the skills are useful as they are, but "useful" is not "peer-reviewed-measured-generalizable." If you use it and the skills don't change your agent's behavior on a specific pressure case, **open an issue** with the scenario and the (unhelpful) response. That's the baseline data needed to close these gaps.

## What v0.3 would need

1. Clean baselines for all 10 skills (10 RED runs from `/tmp/fresh/`)
2. One captured tier-4 E2E run with artifacts
3. Measured `Δloss_bundle` published
4. Word counts trimmed to <800 per skill
5. ≥ 2 scenarios per skill (not just one)
6. Evidence of `method-evolution` actually being used: at least one entry in an outer-loop history with `Δloss_method` attached
