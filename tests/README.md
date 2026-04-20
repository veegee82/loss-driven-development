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

## Current measurements (2026-04-20)

Aggregate `Δloss_bundle` computed across the 9 skills with meaningful RED/GREEN separation. One skill (`docs-as-definition-of-done`) is counted as **contaminated/unmeasured** — the subagent explicitly refused the context reset; see its `baseline-notes.md` for details.

Raw artifacts for every pair in `fixtures/<skill>/runs/<timestamp>/` (v0.2 new-skill runs at `20260420T155048Z`, v0.1 re-measured runs at `20260420T161500Z`).

### Per-skill absolute Δloss

| Skill | Rubric max | RED violations | GREEN violations | Δloss | Relative | Status |
|---|---:|---:|---:|---:|---:|---|
| `root-cause-by-layer` | 8 | 6 | 0 | **+6** | 0.750 | clean |
| `loss-backprop-lens` | 6 | 3 | 0 | **+3** | 0.500 | clean (re-measured) |
| `reproducibility-first` | 6 | 2 | 0 | **+2** | 0.333 | clean |
| `e2e-driven-iteration` | 5 | 3 | 0 | **+3** | 0.600 | clean |
| `dialectical-reasoning` | 6 | 3 | 0 | **+3** | 0.500 | partial contamination |
| `iterative-refinement` | 6 | 3 | 0 | **+3** | 0.500 | clean |
| `method-evolution` | 7 | 4 | 0 | **+4** | 0.571 | clean |
| `drift-detection` | 6 | 5 | 0 | **+5** | 0.833 | clean |
| `loop-driven-engineering` | 8 | 2 | 0 | **+2** | 0.250 | partial contamination |
| **Total (n=9)** | **58** | **31** | **0** | **+31** | **0.537 (mean)** | |
| `docs-as-definition-of-done` | 6 | — | — | — | — | **contaminated, not counted** |

### Bundle-wide metric (n=9)

```
Δloss_bundle (absolute, mean per skill) = 31 / 9  = 3.44
Δloss_bundle (relative, mean)            = 0.537   (≈ 54 % of rubric violations removed)
```

Target from [`../evaluation.md`](../evaluation.md): `Δloss_bundle ≥ 2.0` (absolute, mean per skill). **Measured: 3.44 — target met with margin.**

### Interpretation

Absolute per-skill Δloss ranges from +2 (partially-contaminated skills where baselines already show strong discipline) to +6 (`root-cause-by-layer` — the largest clean gap). The lower-bound character of the partially-contaminated measurements is explicit in their per-skill `baseline-notes.md`; their real Δloss is likely higher than recorded.

### Not cleanly measurable (documented gap)

- `docs-as-definition-of-done` — the subagent in this session environment cannot be coerced to produce a clean RED baseline; its ambient methodology file overrides the explicit context reset. Adopter contributions welcome (run the fixture in a truly empty environment and PR the artifacts).

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
