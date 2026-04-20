# Score — drift-detection — 2026-04-20

**Scorer:** Silvio Jurk (skill author — circular, raw artifacts attached for re-scoring)
**Rubric:** `../../rubric.md` (6 binary items)

| # | Item | RED | GREEN | Notes |
|---|---|---|---|---|
| 1 | Scan proposed, not vibe-check | 0 | 0 | Both propose structured data-gathering |
| 2 | Specific indicators named (seven-indicator framework) | **1** | 0 | RED proposes ad-hoc metrics (onboarding time, review rounds, ownership experiment); GREEN enumerates all 7 drift indicators with tooling per row |
| 3 | Output is fixable list, not health score | **1** | 0 | RED: "three numbers to CEO" — aggregate score, not fixable list. GREEN: expected findings table + triage matrix |
| 4 | Each finding triaged (fix vs method-evolution) | **1** | 0 | RED: "priorisierter Fix-Vorschlag" mentioned but not structured. GREEN: explicit "Immediate fix vs Method-evolution" matrix |
| 5 | Periodic cadence set | **1** | 0 | RED: one-week plan, one-shot. GREEN: "quartalsweise, nicht einmalig" |
| 6 | No reactive timing (scheduled, not fire-driven) | **1** | 0 | RED: triggered by CEO question, not recurring. GREEN: acknowledges reactive trigger but proposes recurring cadence going forward |

**Baseline violations (RED):   5 / 6**
**With-skill violations (GREEN): 0 / 6**
**Δloss = 5 − 0 = +5**

Widest gap of the five. The scenario's shape (a tech lead triggered by a CEO question) strongly invites ad-hoc evidence-gathering; without the skill, the RED response collapses the drift question into general "codebase health investigation" with no structural framework. With the skill: seven indicators, named tooling per indicator, triage matrix, recurring cadence.
