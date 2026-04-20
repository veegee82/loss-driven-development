# Tests

Reproducible pressure scenarios for evaluating the ten skills. See [`../evaluation.md`](../evaluation.md) for the formal loss function and E2E definition.

## Directory layout

```
tests/
├── README.md                    # this file
├── fixtures/                    # per-skill pressure scenarios + rubrics
│   ├── root-cause-by-layer/
│   │   ├── scenario.md          # the prompt given to the subagent
│   │   ├── rubric.md            # binary checks for scoring
│   │   └── baseline-notes.md    # what we observed WITHOUT the skill
│   ├── loss-backprop-lens/
│   ├── dialectical-reasoning/
│   ├── docs-as-definition-of-done/
│   └── loop-driven-engineering/
└── e2e/
    ├── README.md                # how to run an end-to-end test
    └── scenario-01-refactor/    # a multi-skill integration scenario
```

## How to run a fixture (manual, reviewer-scored)

For a given skill `s` and fixture `f`:

1. **Baseline (RED).** Dispatch a fresh subagent in a clean directory (no `CLAUDE.md` / `AGENTS.md` / methodology files). Paste `scenario.md` as the prompt. Save the response.
2. **With skill (GREEN).** Dispatch a second fresh subagent. Include the full `SKILL.md` body above the scenario prompt. Save the response.
3. **Score.** Read both responses against `rubric.md`. Count violations. Compute `Δloss(s, f) = violations_baseline − violations_with_skill`.

A skill that scores `Δloss ≤ 0` on average across its fixtures is broken. Raise an issue.

## Known limitations

- **Baseline contamination.** Subagents dispatched from within a project that has its own methodology `CLAUDE.md` may refuse to ignore it, producing artificially low baseline violation counts. To avoid this, run fixtures from `/tmp/` or from a fresh directory with no ambient methodology. This was **not fully achievable** for the original baselines — see [`../GAPS.md`](../GAPS.md).
- **Reviewer subjectivity.** Rubric items are scored by a human reader; interpretation of "named the contract" vs "vaguely gestured at a contract" varies. Target: ≥ 80% inter-reviewer agreement on the same response.
- **Scenario saturation.** 1–2 fixtures per skill is not enough to claim generalization; it's a smoke test. A real evaluation runs 10+ fixtures per skill across varying domains.

## Current measurements (2026-04-20, v0.3.0)

Aggregate `Δloss_bundle` now computed across **all 11 skills** (10 reactive + 1 architect-mode, opt-in). The previously-blocked skill (`docs-as-definition-of-done`) was captured via direct API (`scripts/capture-clean-baseline.py`) — bypassing the subagent harness entirely. `architect-mode` was measured in v0.3.0 via the same direct-API path.

Raw artifacts for every pair in `fixtures/<skill>/runs/<timestamp>/` (v0.2 new-skill runs at `20260420T155048Z`, v0.1 re-measured runs at `20260420T161500Z`, clean-API for `docs-as-definition-of-done` at `20260420T165000Z-clean`, clean-API for `architect-mode` at `20260420T190302Z-clean`).

### Per-skill normalized Δloss (primary form, v0.3.2 canonical)

| Skill | Δloss (normalized) | Raw | Rubric max | Status |
|---|---:|---:|---:|---|
| `root-cause-by-layer` | **0.750** | 6/8 | 8 | clean |
| `loss-backprop-lens` | **0.500** | 3/6 | 6 | clean (re-measured) |
| `reproducibility-first` | **0.333** | 2/6 | 6 | clean |
| `e2e-driven-iteration` | **0.600** | 3/5 | 5 | clean |
| `dialectical-reasoning` | **0.500** | 3/6 | 6 | partial contamination |
| `iterative-refinement` | **0.500** | 3/6 | 6 | clean |
| `method-evolution` | **0.571** | 4/7 | 7 | clean |
| `drift-detection` | **0.833** | 5/6 | 6 | clean |
| `loop-driven-engineering` | **0.250** | 2/8 | 8 | partial contamination |
| `docs-as-definition-of-done` | **0.333** | 2/6 | 6 | clean (direct API) |
| `architect-mode` (opt-in) | **1.000** | 10/10 | 10 | clean (direct API) |
| **Bundle mean (n=11)** | **0.561** | — | — | |

All GREEN runs score 0 violations, so `Δloss (normalized) = RED_violations / rubric_max`.

### Bundle-wide metric (n=11)

```
Δloss_bundle = mean(Δloss_normalized per skill)
             = (0.750 + 0.500 + 0.333 + 0.600 + 0.500 + 0.500 + 0.571 + 0.833 + 0.250 + 0.333 + 1.000) / 11
             = 0.561
```

Target from [`../evaluation.md`](../evaluation.md): `Δloss_bundle ≥ 0.30` (each skill, on average, removes ≥ 30 % of rubric violations that appear without it). **Measured 0.561 — target met with margin across all 11 skills.**

`architect-mode` is the largest effect-size skill in the bundle (**normalized 1.000, 100 % of rubric items flipped** between RED and GREEN). Consistent with its role — the gap between "agent invents whatever design feels right" and "agent runs a rigid 5-phase discipline with explicit 10-item rubric" is structurally larger than any reactive-mode skill's gap. `architect-mode` is also the only **opt-in** skill; it activates only when the user signals design intent via `LDD[mode=architect]:`, `/ldd-architect`, or a matching trigger phrase — so its contribution to the bundle-wide mean applies only in architect sessions, not every session.

### Interpretation

Per-skill normalized Δloss ranges from 0.250 (partially-contaminated skills where baselines already show strong discipline) to 1.000 (`architect-mode` standard — every rubric item flipped). The lower-bound character of the partially-contaminated measurements is explicit in their per-skill `baseline-notes.md`; their real Δloss is likely higher than recorded.

The previous v0.3.1 absolute-mean form (`Δloss_bundle = 3.91`) is retained in git history but no longer cited — it was three overlapping numbers (per-skill absolute + bundle absolute + bundle relative) where one normalized mean is clearer.

### How the clean-baseline script unblocks adopter contributions

[`../scripts/capture-clean-baseline.py`](../scripts/capture-clean-baseline.py) runs any fixture's `scenario.md` against the LLM directly — **no agent harness, no ambient methodology**. Works with OpenRouter, OpenAI, or Anthropic API keys. This is how `docs-as-definition-of-done` was finally measured cleanly, and it is the tool for:

- Re-running any fixture under different models (distribution across models)
- N=5 runs per fixture (distribution across samples)
- Running community-contributed scenarios with the same methodology
- Closing any remaining baseline-contamination problems

See [`../GAPS.md`](../GAPS.md).

### Inter-reviewer agreement (independent-judge sampling)

Two fixtures were re-scored by a fresh subagent given only the RED, GREEN, and rubric — no methodology context, no author hints.

| Fixture | Author Δloss | Judge Δloss | GREEN agreement | RED agreement (within ±1) |
|---|---:|---:|---|---|
| `loss-backprop-lens` | +3 | **+5** | 100 % (both 0/6) | ± 2 |
| `drift-detection` | +5 | **+3** | 100 % (both 0/6) | ± 2 |

**Result:** direction agreement 100 %, GREEN-clean agreement 100 %, magnitude variance ~ ±2 per skill. Both reviewers agree the skills provide real Δloss; absolute numbers are not to be over-interpreted.

Full judge verdicts (verbatim): `fixtures/loss-backprop-lens/runs/20260420T161500Z/independent-judge.md`, `fixtures/drift-detection/runs/20260420T155048Z/independent-judge.md`.

### Scoring caveats

- **Author-scored for 9 skills, independent-judge-scored for 2 as a cross-check.** Raw RED and GREEN artifacts are attached in every `runs/` directory so anyone can re-score.
- **Single run per skill.** A real distribution requires N≥5 runs per skill; the ones captured here are point estimates.
- **Scenario-design bias.** Each fixture was designed by the same author who wrote the skill it tests. Scenarios authored by outside contributors would be the first unbiased measurement (see [`../CONTRIBUTING.md`](../CONTRIBUTING.md)).
- **Two skills show partial contamination** (`dialectical-reasoning`, `loop-driven-engineering`): the subagent retained some ambient discipline despite the context reset. Their Δloss is a lower bound; a truly-clean environment would likely widen the gap.
