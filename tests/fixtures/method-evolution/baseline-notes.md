# Baseline observations — method-evolution

**Status: MEASURED (2026-04-20).** Raw artifacts in `runs/20260420T155048Z/` (red.md, green.md, score.md).

## Measurement summary

- RED violations: **4 / 7** — bundles 5 changes, no measurement plan, no rollback, no commit shape
- GREEN violations: **0 / 7** — one change, full suite measurement, rollback bias, canonical commit
- **Δloss = +4**

## Observed failure mode (RED)

The agent correctly identifies the pattern (adjective-laundered symptom patches) and proposes the right structural fix *direction* (Red Flag addition). But it *can't help itself* from proposing four additional changes in the same step: counter-examples, mini-case-studies, prompt-side detector, retrospective review. Five changes bundled means no attribution of which change drove the improvement and no rollback granularity if it regresses.

This is the canonical method-evolution anti-pattern: ambitious multi-change proposals without a measurement plan.

## Observed skill effect (GREEN)

- Exactly ONE change (a Rationalizations table row)
- Named pattern (`symptom-patch-label-laundering`) — greppable
- 5-task suite with before/after mean_loss table, controls unchanged check
- Canonical commit message shape with pattern / change / Δloss / regressions / fixtures
- Forward-looking rollback bias ("expect rollback next step")

## Caveats

- Reviewer-scored. Raw artifacts attached.
- GREEN cites fictional mean_loss numbers (0.62 → 0.22). These are plausible but not actually measured against a real suite — the agent is walking the protocol, not running it. In a real method-evolution step, the suite run would produce actual numbers.
- Single scenario. A varied-domain scenario suite would stress this skill harder.
