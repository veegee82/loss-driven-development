---
description: Switch LDD into architect mode for the next task. Runs the 5-phase protocol (Constraints → Non-goals → 3 Candidates → Scoring+Dialectical → Deliverable) from skills/architect-mode/SKILL.md. Opt-in, not default.
---

Activate `mode=architect` for the next user request in this session. Announce:

> *Architect mode active.* The next task will run under the 5-phase protocol from `skills/architect-mode/SKILL.md`. Default reactive LDD resumes after hand-off.

Wait for the user's next message describing the design task (greenfield system, new module, decomposition request). When it arrives:

1. Apply the 5-phase protocol strictly (Phase 1 Constraints → Phase 2 Non-goals ≥ 3 → Phase 3 exactly 3 candidates on a load-bearing axis → Phase 4 scoring table + dialectical on winner → Phase 5 deliverable commit).
2. Emit the architect-variant of the LDD trace block (phases, not iterations; `mode: architect` in header).
3. Score the final output against the 10-item rubric from `skills/architect-mode/SKILL.md`.
4. Hand off at the end — announce rubric score, `loss_0` count from failing tests, and drop back to `mode=reactive`.

If the user's next message is NOT an architect-suitable task (it's a bug fix, refactor, review), do not force architect mode — explain briefly and revert to default reactive mode. Do not silently run the reactive flow under the architect label; that's a trace-integrity violation.

Architect mode is **single-task scope**. After hand-off, `mode` reverts to whatever the user's persistent config + session overrides dictate.
