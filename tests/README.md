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

Aggregate `Δloss_bundle` has now been computed across the 6 skills with cleanly-captured RED/GREEN pairs. Raw artifacts for each pair are in `fixtures/<skill>/runs/<timestamp>/`.

### Per-skill absolute Δloss

| Skill | Rubric max | RED violations | GREEN violations | Δloss | Relative (Δloss / max) |
|---|---:|---:|---:|---:|---:|
| `root-cause-by-layer` | 8 | 6 | 0 | **+6** | 0.75 |
| `reproducibility-first` | 6 | 2 | 0 | **+2** | 0.33 |
| `e2e-driven-iteration` | 5 | 3 | 0 | **+3** | 0.60 |
| `iterative-refinement` | 6 | 3 | 0 | **+3** | 0.50 |
| `method-evolution` | 7 | 4 | 0 | **+4** | 0.57 |
| `drift-detection` | 6 | 5 | 0 | **+5** | 0.83 |
| **Total (n=6)** | **38** | **23** | **0** | **+23** | **0.605 (mean)** |

### Bundle-wide metric

```
Δloss_bundle (absolute, mean per skill) = 23 / 6  = 3.83
Δloss_bundle (relative, mean)            = 0.605   (≈ 60 % of rubric violations removed)
```

Target from [`../evaluation.md`](../evaluation.md): `Δloss_bundle ≥ 2.0` (absolute, mean-per-skill). **Measured: 3.83 — target met with margin.**

### Not measured (known gaps)

- `loss-backprop-lens`, `dialectical-reasoning`, `docs-as-definition-of-done`, `loop-driven-engineering` — four v0.1 skills still have baseline-contamination caveats; re-running them in a clean environment is pending. These are absent from the bundle mean above.

See [`../GAPS.md`](../GAPS.md) for what this means for honest generalization claims.

### Scoring caveats

- **Reviewer-scored by the skill author.** Circular — but raw RED and GREEN artifacts are attached in every `runs/` directory so the community can re-score and challenge the numbers.
- **Single run per skill.** A real distribution requires N≥5 runs per skill; the ones captured here are point estimates.
- **Scenario-design bias.** Each fixture was designed by the same author who wrote the skill it tests. Scenarios authored by outside contributors would be the first unbiased measurement (see [`../CONTRIBUTING.md`](../CONTRIBUTING.md)).
