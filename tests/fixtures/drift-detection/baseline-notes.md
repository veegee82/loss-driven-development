# Baseline observations — drift-detection

**Status: MEASURED (2026-04-20).** Raw artifacts in `runs/20260420T155048Z/` (red.md, green.md, score.md).

## Measurement summary

- RED violations: **5 / 6** — ad-hoc metrics instead of 7-indicator framework, aggregate score instead of fixable list, no recurring cadence
- GREEN violations: **0 / 6** — all 7 indicators with tooling per row, triage matrix, quarterly cadence
- **Δloss = +5** (widest gap of the five new skills)

## Observed failure mode (RED)

The agent correctly refuses to answer the CEO's question prematurely ("Bauchgefühl" is not enough). But the evidence-gathering approach it proposes is ad-hoc — onboarding-time interviews, review-round metrics, ownership-experiment with 3 seniors — none of which map to the structural drift indicators the skill is built around. The output is "three numbers to the CEO," i.e. an *aggregate score*, which the skill explicitly forbids ("a list of findings, not a health score").

Additionally: the week-long plan is one-shot, not recurring. No quarterly cadence, no re-scan loop.

## Observed skill effect (GREEN)

- All seven indicators enumerated with specific tooling per row (grep synonym sets, AST signature scan, import graph diff against architecture.md, README-vs-`ls`, git-log rubric audit, spec-vs-tests, config defaults cross-join)
- Expected-findings table tying the symptoms to likely indicator firings
- Explicit immediate-fix vs method-evolution triage
- "Quartalsweise, nicht einmalig" cadence statement

## Caveats

- Reviewer-scored. Raw artifacts attached.
- Single run.
- Both RED and GREEN correctly refuse to answer "healthy / not healthy" without data — that's a scenario-design strength, not a skill differentiator. The skill differentiator is in *which data* is collected: indicator-framework vs. ad-hoc metrics.
