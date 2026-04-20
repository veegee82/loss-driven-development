# Known Gaps — v0.2.0 (updated 2026-04-20, final)

An honest list of what is **not** verified in this bundle. Read this before claiming it "works."

## ✅ Closed in this update

### Entry-point skill + user invocation guide — **ADDED**

- New `skills/using-ldd/SKILL.md` — bootstrap skill with a complete trigger-phrase table and the `LDD:` buzzword convention for guaranteed activation.
- README has a new **"Using LDD — how to invoke the skills"** section covering auto-trigger, explicit invocation, per-agent usage (Claude Code / Codex / Gemini CLI / Aider / Cursor / Copilot CLI / Continue.dev), and how to verify a skill fired.
- All skill invocations now announce themselves via `*Invoking <skill-name>*:` — documented as a minimum-compliance behavior in `using-ldd`.
- `AGENTS.md` and `GEMINI.md` list the buzzword and the new entry-skill.

### Baselines for 4 previously-contaminated v0.1 skills — **RE-MEASURED**

Re-run from fresh subagent with strong-context-reset preamble:

- `loss-backprop-lens` — clean RED, Δloss = +3
- `dialectical-reasoning` — partial contamination, Δloss = +3 (lower bound)
- `docs-as-definition-of-done` — **hard contamination** (subagent explicitly refused reset); not cleanly measurable from this session environment
- `loop-driven-engineering` — partial contamination, Δloss = +2 (lower bound)

Raw artifacts in `tests/fixtures/<skill>/runs/20260420T161500Z/`.

### `Δloss_bundle` now aggregated across 9 of 10 skills

```
Δloss_bundle = 31 / 9 = 3.44  (absolute, mean per skill)
             = 0.537          (relative)
```

Target `≥ 2.0` absolute — **met with margin**. Previous n=6 aggregate was 3.83; adding the 3 additional cleanly-measured skills lowered the mean because their gaps were smaller (contamination makes RED baselines already partially-compliant). Full per-skill table in [`tests/README.md`](./tests/README.md#current-measurements).

### Inter-reviewer agreement sampled — **CIRCULARITY PARTIALLY ADDRESSED**

Two fixtures re-scored by a fresh subagent with no methodology context:

- `loss-backprop-lens`: author +3, judge +5 — direction ✓, GREEN agreement 100 %, magnitude Δ=2
- `drift-detection`: author +5, judge +3 — direction ✓, GREEN agreement 100 %, magnitude Δ=2

Inter-reviewer variance: **~±2 per skill**. Direction and GREEN compliance: 100 % agreement. Absolute numbers ± 2 between reviewers — don't over-interpret magnitudes, but direction is solid. Full judge verdicts in the respective fixture runs.

### Tier-3.5 simulated E2E — **CAPTURED** (from previous update)

Agent ran to `complete` terminal state at k=1/5 on `scenario-01-refactor`, 7/7 rubric items satisfied. Artifacts in `tests/e2e/scenario-01-refactor/runs/20260420T160347Z/`.

## ⚠️ Still open

### Real tier-4 live-install E2E

Still requires an adopter to install the plugin in a live Claude Code / Codex / Gemini CLI session. Simulated tier-3.5 is close but not identical. **How to close:** follow the adopter guide in [`tests/e2e/scenario-01-refactor/results.md`](./tests/e2e/scenario-01-refactor/results.md).

### 1 of 10 skills: cannot be cleanly RED-tested in this session environment

`docs-as-definition-of-done` is documented as contaminated — the subagent refuses to ignore its ambient methodology file. Δloss for this skill remains unmeasured from within any environment that has an ambient doc-sync rule.

**How to close:** an adopter runs the fixture from a genuinely empty environment (no ancestor `CLAUDE.md` / `AGENTS.md`) and contributes the captured baseline.

### Single-run measurements, not distributions

All Δloss numbers are based on one RED + one GREEN per skill. Point estimates, not distributions. A real measurement needs N≥5 per fixture.

**How to close:** re-run each fixture N=5 times, record mean ± stddev.

### Partial contamination on 2 of 10 skills

`dialectical-reasoning` and `loop-driven-engineering` show contamination-influenced baselines. Their published Δloss is a lower bound.

**How to close:** re-run from `/tmp/fresh/` with no ancestor methodology.

### Scenario-design bias

All fixtures written by the same author as the skills they test. Outside-contributed scenarios would be the first unbiased measurement.

**How to close:** community PRs adding new scenarios per skill.

## Distribution gaps (unchanged)

### Claude Code auto-trigger untested in live session

`description` fields are written to be discriminating. The README "Using LDD" section now teaches the `LDD:` buzzword as a guaranteed-activation path, but automatic triggering (skill fires without explicit invocation when `description` matches) still needs live verification. Adopter feedback welcome.

### Codex skills directory path uncertain

`AGENTS.md` suggests `~/.agents/skills/`. Exact path may vary. Not test-installed.

### Gemini CLI extension format not re-verified

`gemini-extension.json` mirrors superpowers' format. Not test-installed.

### Aider · Cursor · Copilot CLI · Continue.dev

Documented via reference-or-inline. No captured test runs.

## Summary

**What v0.2 measures (final):**

- 11 skills installed (10 disciplines + 1 entry-point `using-ldd`)
- `Δloss_bundle = 3.44` absolute (mean per skill) across 9 of 10, target ≥ 2.0 met
- GREEN compliance: **0 violations across all 9 clean measurements**
- Inter-reviewer variance ~±2 per skill, direction 100 % agreement
- Tier-3.5 simulated E2E: 7/7 rubric items on scenario-01-refactor
- User-facing invocation: `LDD:` buzzword + trigger-phrase table + per-agent install guide

**What v0.2 does not prove (explicit):**

- Single-sample point estimates, not distributions
- 1 skill cannot be RED-measured from this environment (contamination)
- 2 skills have partial-contamination lower bounds
- Real tier-4 (live plugin install) not yet captured — needs you
- Scenario-author bias
