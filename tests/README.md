# Tests

Reproducible pressure scenarios for evaluating the five skills. See [`../evaluation.md`](../evaluation.md) for the formal loss function and E2E definition.

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

## Current measurements

The original RED-GREEN pairs that motivated each skill are captured in each fixture's `baseline-notes.md`. Aggregate `Δloss_bundle` has **not** been computed rigorously yet — the per-skill GREEN runs (captured in the git history of this repo) are anecdotal evidence, not a measurement.

This is honest: we shipped a skills bundle with a well-defined evaluation harness and a handful of worked examples, not a peer-reviewed study.
