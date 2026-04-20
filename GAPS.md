# Known Gaps

An honest list of what is **not** verified in this bundle as shipped. New users and reviewers: read this before claiming the bundle "works."

## Evaluation gaps

### Baseline contamination

3 of 5 skill baselines were captured from a subagent that **refused to ignore** an ambient methodology `CLAUDE.md` in the parent project. That `CLAUDE.md` itself contains the source methodology this bundle distills, so the subagent produced "skill-compliant" output even without the skill loaded. The baselines for these skills are therefore **not a clean measurement** of the untrained failure mode:

- `loss-backprop-lens` — baseline contaminated.
- `docs-as-definition-of-done` — baseline contaminated.
- `dialectical-reasoning` — baseline missing for the specific dedup fixture (captured on a different scenario).

Clean baselines for `root-cause-by-layer` (mostly) and `loop-driven-engineering` (partial) were recorded. See per-fixture `baseline-notes.md` for details.

**Fix:** run the fixtures from `/tmp/fresh/` (no ancestor `CLAUDE.md`) and record results into each fixture's `baseline-notes.md`. This is tractable but was not completed in the original build session.

### No aggregate Δloss computation

`evaluation.md` defines `Δloss_bundle` formally. **No one has run it.** The bundle ships with a specified target (`Δloss_bundle ≥ 2.0`) and no measured value.

**Fix:** run all 5 fixtures RED + GREEN, score against rubrics, compute. Publish the number in `tests/README.md#current-measurements`.

### No tier-4 run (live-install E2E)

The bundle has never been installed into a running Claude Code / Codex / Gemini CLI session and driven through a multi-step task. The `tests/e2e/scenario-01-refactor/` starter code and task specification exist, but no captured run. One attempted dispatch during build hit a subagent rate limit before producing output — not a measurement.

**Fix:** you (the reader) install the bundle, point it at the E2E scenario, record what happens in `tests/e2e/scenario-01-refactor/run-<timestamp>/`.

### No tier-5 run (production, unrelated repo)

No data on whether the skills hold up in a real long-running project under real pressure. This requires time, not code.

## Distribution gaps

### Claude Code auto-trigger untested

The `description` fields are written to be discriminating, but automatic invocation (the skill firing when its `description` matches the current task, without explicit `/plugin:skill` or `Skill` tool call) has **not been verified** in a live session. It works on paper; no captured evidence.

### Codex skills directory path uncertain

`AGENTS.md` suggests `~/.agents/skills/` for a global Codex install, citing the `writing-skills` skill. The exact path may differ by Codex installation; **no one has tried it**. If your Codex version uses a different path, the per-project `AGENTS.md` approach still works.

### Gemini CLI extension format not re-verified

`gemini-extension.json` mirrors superpowers' format (`name`, `description`, `version`, `contextFileName`). If Gemini's extension schema has drifted, this manifest may need adjustment. Not test-installed.

### Aider / Cursor / Copilot CLI / Continue.dev

Documented as "reference the skills dir from your ambient instruction file." **No captured test runs on any of these.** The mechanism is standard file-loading, so it should work, but "should work" is not a measurement.

## Content gaps

### Skill word counts over superpowers' guideline

`superpowers:writing-skills` recommends `<500 words` per skill; the skills in this bundle range 1100–1600 words. Heavier skills may be skimmed rather than read under pressure. Target: trim each to ~800 words in a future pass.

### Cross-skill redundancy

Several anti-patterns (symptom patches, retry loops, "clean up later" framing) appear in both `root-cause-by-layer` and `loss-backprop-lens`. Intentional — each skill must stand alone when loaded independently — but could be tightened.

### Dispatch table uses `+optional` notation

`loop-driven-engineering` marks entries `+optional` (meaning "requires a companion plugin like superpowers"). This convention was invented for this plugin; agents may not parse it consistently. Safer to use plain prose per row.

## Methodology gaps

### TDD-for-skills ran one scenario per skill, not a suite

Writing-skills recommends testing skills against *multiple* pressure scenarios to catch rationalizations that only appear under specific framings. This bundle shipped after one scenario per skill (with one cross-skill integration scenario for the dach-skill). Future editions should run 3+ fixtures per skill before claiming coverage.

### REFACTOR phase skipped

The writing-skills TDD cycle is RED → GREEN → REFACTOR, where REFACTOR means "find new rationalizations in the green run and add counters." This bundle shipped after one GREEN run per skill. If a GREEN run surfaced a loophole, it wasn't iteratively closed.

## What this means for users

The skills are useful as they are — the GREEN runs showed strong behavior change on the scenarios measured. But "useful" is not "peer-reviewed-measured-generalizable." Treat this bundle as a v0.1 seed. If you use it and the skills don't change your agent's behavior on a specific pressure case, **open an issue** with the scenario and the (unhelpful) response. That's exactly the baseline data needed to close these gaps.
