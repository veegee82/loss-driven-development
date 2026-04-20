# Known Gaps — v0.2.1 (updated 2026-04-20, final)

An honest list of what is **not** verified in this bundle. Read this before claiming it "works."

## ✅ Closed in this update

### All 10 skills cleanly measured

The previously-contamination-blocked `docs-as-definition-of-done` baseline is now captured via [`scripts/capture-clean-baseline.py`](./scripts/capture-clean-baseline.py) — direct LLM API call, no Claude Code, no agent harness, no ambient CLAUDE.md. Raw run in [`tests/fixtures/docs-as-definition-of-done/runs/20260420T165000Z-clean/`](./tests/fixtures/docs-as-definition-of-done/runs/20260420T165000Z-clean/).

**`Δloss_bundle = 3.30` absolute (mean per skill) across all 10**. Target ≥ 2.0 met with margin. Per-skill table in [`tests/README.md`](./tests/README.md#current-measurements).

### Tier-3.9 discovery run captured

New E2E run at [`tests/e2e/scenario-01-refactor/runs/20260420T164505Z/`](./tests/e2e/scenario-01-refactor/runs/20260420T164505Z/). Skills were installed at `~/.claude/skills/` rather than injected into the prompt. The subagent discovered them at runtime via the trigger-phrase table in `using-ldd`, read the SKILL.md files from disk, and applied the discipline. 7/7 rubric items satisfied, loop closed at k=1 of 5.

**Finding:** the subagent's `Skill` tool did NOT auto-discover `~/.claude/skills/` (returned `Unknown skill`). Fallback via direct `Read` worked. This is closer to tier-4 than tier-3.5 but still not the pure-plugin-install path — see [`tests/e2e/scenario-01-refactor/results.md`](./tests/e2e/scenario-01-refactor/results.md) for the honest caveats.

### N=3 distribution demonstrated on one skill

[`tests/fixtures/root-cause-by-layer/runs/20260420T165603Z-clean-N3/`](./tests/fixtures/root-cause-by-layer/runs/20260420T165603Z-clean-N3/) — 3 independent RED captures via `capture-clean-baseline.py` at temperature 0.8. All 3 produced type-tolerance-shim variants — same failure mode, tight distribution (stddev ≈ 0.5 on violation count). Proof that the distribution-sampling infrastructure works; a proper N≥10 distribution is cheap to run ($0.01–0.05 per call × 10 runs × 10 skills ≈ $1–5 total).

### Scenario-design bias partially addressed

Second scenario added for `root-cause-by-layer` ([`tests/fixtures/root-cause-by-layer/scenario-2/`](./tests/fixtures/root-cause-by-layer/scenario-2/)) — different domain (rate-limiter precondition contract vs. notifier boundary leak), same skill. Two scenarios from one author reduces single-point-of-failure risk without eliminating author bias.

### docs/ldd/ structure — drift resistance

Methodology text now lives in exactly one place: [`docs/ldd/`](./docs/ldd/). Task-specific compressed MDs (`debugging.md`, `design-decisions.md`, `refactor.md`, `refinement.md`, `release.md`, `incident.md`, `method-maintenance.md`) with [`task-types.md`](./docs/ldd/task-types.md) as the dispatch table. Prevents methodology drift between README / skill bodies / user-project docs. User-project `CLAUDE.md` references `task-types.md` rather than copying methodology inline.

## ⚠️ Still open (honestly)

### Real tier-4 plugin-install E2E still pending

The tier-3.9 run showed that the subagent's `Skill` tool in my build environment does not auto-discover `~/.claude/skills/`. Whether this is a subagent-harness limitation or a general-adopter issue is **not yet known**. Real tier-4 requires `/plugin install` in a live Claude Code session, which can only be tested by an adopter.

**How to close:** follow the adopter guide in [`tests/e2e/scenario-01-refactor/results.md`](./tests/e2e/scenario-01-refactor/results.md).

### Distribution at N≥10 per skill not run

N=3 was demonstrated on one skill; all other skills are point estimates. A proper distribution claim needs N≥10 across multiple models.

**How to close:** community runs `scripts/capture-clean-baseline.py` N times per fixture. Infrastructure is in place. Estimated cost: $1–5 for the whole bundle at current pricing. This is an adopter task, not a developer task, because distribution needs **independent** re-runs.

### Author scenario-design bias remains

Two scenarios for `root-cause-by-layer`; one scenario each for the other 9 skills. All authored by the skill author. Cannot be closed without community contributions.

**How to close:** PRs adding community-authored scenarios. Template: clone an existing `fixtures/<skill>/scenario.md`, adapt to your domain, run through `capture-clean-baseline.py`, publish.

### GREEN side not re-captured via clean API

RED baselines are now clean (all 10 skills); GREEN responses still come from in-session subagent runs where ambient methodology may have contributed. The GREEN side defines the compliance *upper bound*, so ambient contamination there *reduces* measured Δloss (RED moves toward GREEN, not away) — the measured values are therefore lower bounds on the skill's true effect. Re-capturing GREEN via the clean API with the skill body prepended would firm up the upper bound but is cosmetic at this point.

## Distribution gaps (unchanged across v0.2.x)

### Claude Code auto-trigger behavior

The README "Using LDD" section documents the `LDD:` buzzword as the guaranteed-activation path. Automatic description-based triggering works on paper but has not been verified in a live Claude Code session. If an adopter installs and finds auto-trigger unreliable, the buzzword path is the fallback.

### Codex personal-skills path uncertain

`AGENTS.md` suggests `~/.agents/skills/`. Exact path varies by Codex version.

### Gemini CLI extension schema may have drifted

`gemini-extension.json` mirrors superpowers' format. Not re-verified against current Gemini docs.

### Aider · Cursor · Copilot CLI · Continue.dev

Documented via reference-or-inline. No captured test runs on any.

## Summary

**What v0.2.1 measures:**

- All 10 skills cleanly measured. `Δloss_bundle = 3.30` absolute across all 10, target ≥ 2.0 met
- Tier-3.9 E2E capture (skills discovered at runtime, not prompt-injected), 7/7 rubric
- Inter-reviewer variance sampling (±2 per skill, direction 100%)
- N=3 distribution demo on one skill (tight, stddev ≈ 0.5)
- Two scenarios for one skill (partial bias reduction)
- `scripts/capture-clean-baseline.py` portable across OpenRouter / OpenAI / Anthropic

**What v0.2.1 does not prove:**

- Real tier-4 (live plugin install) — adopter task
- N≥10 distributions per skill — adopter task (infrastructure in place)
- Scenario-author neutrality — community task
- Live auto-trigger on Claude Code / Codex / Gemini — adopter task
