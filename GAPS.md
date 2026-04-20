# Known Gaps — v0.2.0 (updated 2026-04-20)

An honest list of what is **not** verified in this bundle. Read this before claiming the bundle "works."

## ✅ Closed in this update

### Baselines for the 5 new skills — **MEASURED**

All 5 v0.2 skills now have RED/GREEN runs captured on disk (`tests/fixtures/<skill>/runs/20260420T155048Z/`). Measured Δloss per skill:

| Skill | Δloss | % rubric violations removed |
|---|---:|---:|
| `reproducibility-first` | +2 | 33 % |
| `e2e-driven-iteration` | +3 | 60 % |
| `iterative-refinement` | +3 | 50 % |
| `method-evolution` | +4 | 57 % |
| `drift-detection` | +5 | 83 % |

Full scoring methodology, rubric items, and raw RED/GREEN artifacts in each fixture directory.

### `Δloss_bundle` — **MEASURED**

Across the 6 skills with cleanly-captured RED/GREEN pairs (the 5 new + `root-cause-by-layer` from v0.1):

```
Δloss_bundle = 23 / 6 = 3.83  (absolute, mean per skill)
             = 0.605          (relative, mean fraction of violations removed)
```

Target per `evaluation.md` was `≥ 2.0` absolute — **met with margin**. Full numbers and caveats in [`tests/README.md`](./tests/README.md#current-measurements).

### Tier-3.5 simulated E2E — **CAPTURED**

A subagent with tool access (bash, file edits, git) and all 10 skills in-prompt was run against the `scenario-01-refactor` sandbox. Result: terminal status `complete` at iteration k=1 of K_MAX=5, all 7 E2E rubric items satisfied. Raw artifacts in [`tests/e2e/scenario-01-refactor/runs/20260420T160347Z/`](./tests/e2e/scenario-01-refactor/runs/20260420T160347Z/); scoring in [`tests/e2e/scenario-01-refactor/results.md`](./tests/e2e/scenario-01-refactor/results.md).

This is **simulated** tier-4 (via prompt-injected skills + tool access), not **real** tier-4 (via `/plugin install` in a live agent session).

## ⚠️ Still open

### Real tier-4 live-install E2E

Real tier-4 requires an adopter to `/plugin install loss-driven-development` (or equivalent) in a live Claude Code / Codex / Gemini CLI session, point the agent at the same scenario, let it run, and compare artifacts. That's not doable from a build environment — it needs you.

**What this bundle can promise:** the tier-3.5 captured run shows the skills *can* drive the loop to terminal state with structurally correct output on realistic starter code.

**What real tier-4 adds:** proof that the skills activate automatically (via `description`-based triggering) when loaded through the host agent's plugin system, not only when hand-injected into a prompt.

**How you close it:** follow the "What a new adopter should do" section of [`tests/e2e/scenario-01-refactor/results.md`](./tests/e2e/scenario-01-refactor/results.md) and open a PR with your run.

### 4 of 10 skills: still no clean baseline

The v0.1 skills `loss-backprop-lens`, `dialectical-reasoning`, `docs-as-definition-of-done`, and `loop-driven-engineering` have baseline-contamination caveats (documented in each `baseline-notes.md`) — the original measurement environment had an ambient methodology CLAUDE.md that subagents refused to ignore. Their rubric-compliance *with the skill loaded* has been shown (GREEN runs), but the *without-skill* baselines aren't clean.

**What this means for the aggregate:** `Δloss_bundle = 3.83` is computed over 6 skills, not all 10. The other 4 are neither disproved nor confirmed at the bundle level.

**How to close:** re-run RED baselines for these 4 in a `/tmp/` directory with no ancestor methodology file. Contribution guide in [`CONTRIBUTING.md`](./CONTRIBUTING.md).

### Single-run measurements

Each Δloss above is based on one RED + one GREEN run per skill. Point estimates, not distributions. LLM output variance means a distribution of N≥5 runs is the honest measurement.

**How to close:** re-run each fixture N times, record a distribution, publish mean ± stddev.

### Reviewer-scoring is circular

All scores above were assigned by the skill author reading responses against rubrics. The artifacts are on disk, so anyone can re-score, but the published numbers are author-graded.

**How to close:** a second reviewer (human or LLM) scores the same artifacts independently. Inter-reviewer agreement quantifies rubric reliability.

### Scenario-design bias

Each fixture was written by the same author as the skill it tests. Scenarios from outside contributors would be the first bias-free measurement.

**How to close:** community PRs adding new scenarios per skill, scored by anyone.

## Distribution gaps (unchanged from v0.1)

### Claude Code auto-trigger untested

`description` fields are written to be discriminating, but automatic invocation (skill fires when `description` matches, without explicit `/plugin:skill`) is **not verified** in a live session.

### Codex skills directory path uncertain

`AGENTS.md` suggests `~/.agents/skills/` for Codex global install. Exact path may differ by Codex version. Not test-installed.

### Gemini CLI extension format not re-verified

`gemini-extension.json` mirrors superpowers' format. If Gemini's schema drifted, manifest may need adjustment. Not test-installed.

### Aider · Cursor · Copilot CLI · Continue.dev

Documented via reference-or-inline from the ambient instruction file. No captured test runs on any of these.

## Content gaps (unchanged from v0.1)

### Skill word counts over superpowers' guideline

Writing-skills recommends `<500 words`; this bundle ranges 1100–1800. Heavier skills may be skimmed under pressure. Future pass target: trim to ≤800 while keeping discipline-enforcement coverage.

### Cross-skill redundancy

Some anti-patterns (symptom patches, retry loops) appear in multiple skills. Intentional for standalone loading, but tightenable.

## Summary

**What v0.2 measures:** 6 of 10 skills have reviewer-scored single-run RED/GREEN data; bundle-wide `Δloss_bundle = 3.83` absolute (target ≥ 2.0 met); one tier-3.5 simulated E2E captured with 7/7 rubric satisfaction.

**What v0.2 does not prove:** generalization across distributions, independence from author bias, behavior under real plugin-install (tier-4), coverage of the 4 v0.1 skills with contaminated baselines.

**What v0.3 would need:**
1. Clean baselines for the 4 v0.1 skills (RED runs from `/tmp/fresh/`)
2. ≥ 5 runs per fixture for distributions, not point estimates
3. ≥ 1 captured real tier-4 run with artifacts
4. Independent reviewer scoring
5. At least one community-authored scenario per skill
