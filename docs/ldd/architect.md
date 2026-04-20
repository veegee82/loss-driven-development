# Architect mode — greenfield design under discipline

Load this when the user wants **structure / design / architecture invented** for a problem that has no existing code, or when they explicitly scope out existing code and ask "what should this be?". This is LDD's **opt-in constructive mode** — reactive LDD stays the default.

## When to use

- Greenfield system / new module / new service — no existing scaffold
- Architecture review of a fresh proposal ("is this the right shape?")
- Decomposition request ("how should I break this problem down?")
- Explicit phrases: "design", "architect", "from scratch", "greenfield", "propose an architecture", "how should I structure"

## When NOT to use

- Bug fix, feature addition, refactor, incident response → default reactive LDD, see [`debugging.md`](./debugging.md), [`refactor.md`](./refactor.md), [`incident.md`](./incident.md)
- "Review this finished design doc" → [`refinement.md`](./refinement.md) (y-axis polish of an existing artifact)
- "Should we rewrite X" → [`design-decisions.md`](./design-decisions.md) (`dialectical-reasoning` on a single Yes/No)

## The 5-phase protocol

Rigid. Architect mode is prescriptive by design — freeform invention is the failure mode.

| Phase | What | Gate |
|---|---|---|
| **1 — Constraints** | Extract every requirement from the user's ask into a table (requirement / target / source). Name uncertainties explicitly. | Every stated X_i is covered |
| **2 — Non-goals** | Declare ≥ 3 concrete, scope-bounding non-goals | Rubric item 3 of 10 |
| **3 — 3 candidates** | Generate exactly three architecture candidates on a **load-bearing axis** (not cosmetic variants). One-line name + 3–5 sentence sketch + trade-off vector per candidate. | Rubric item 4 |
| **4 — Scoring + dialectic** | 3 × 6 scoring table (requirements coverage / boundary clarity / evolution paths / dependency explicitness / test strategy / rollback plan). Then `dialectical-reasoning` on the winner (thesis → antithesis → synthesis). | Rubric items 5–6 |
| **5 — Deliverable** | One commit: `docs/architecture.md` (9 sections), scaffold (directory + empty modules + failing tests), measurable success criteria per requirement. | Rubric items 7–10 |

## The 10-item architect rubric

Each binary (0 = satisfied, 1 = violated):

1. All stated requirements covered in the constraint table
2. Uncertainties named (not silently invented)
3. ≥ 3 concrete non-goals declared
4. 3 candidates on a load-bearing axis (not cosmetic)
5. Scoring table explicit (rows × 6 dimensions, not narrative)
6. Antithesis against winner is real (not a strawman)
7. Architecture doc has 9 sections (per `skills/architect-mode/SKILL.md` Phase 5)
8. Scaffold compiles / imports cleanly (not pseudocode)
9. ≥ 1 failing test per component
10. Measurable success metric per requirement

Target: 0/10 violations. Acceptable to ship at ≤ 2/10 if each violation is named in a "Known architectural gaps" section at the top of the doc.

## Escalation (when a phase cannot close cleanly)

- **Too few constraints** → ask ONE clarifying question; if still thin, proceed with `user to decide` rows in the table
- **Cannot find 3 distinct candidates** → acceptable degradation to 2 with explicit "space is narrow because X"; hard floor: never 1
- **Top two candidates score within 10 %** → surface the tie, ask user which trade-off they weight higher; do not silently break the tie
- **Architecture doc ships with ≥ 3/10 violations** → failed run, re-iterate via `iterative-refinement` on the doc

## Hand-off to default LDD

Phase 5 produces failing tests — those are `loss_0` for the inner loop. The architect trace's final block emits:

```
│ Hand-off : architect closed N/10 rubric; next: reactive LDD inner loop
│            loss_0 = <count of failing tests>
```

Then the agent announces to the user: *"architect-mode complete. To start implementation, say `LDD: begin implementation` or equivalent — I'll switch to reactive mode."*

**Do not auto-resume.** User must explicitly trigger the next task. Prevents architect-mode from silently consuming inner-loop budget on its own output.

## Activation

Three opt-in paths (precedence: inline > session > project-config):

```
LDD[mode=architect]: design a billing service for 50M users
                                     ↑ inline flag, this task only

/loss-driven-development:ldd-architect          # session: flips for next task
                                                 # then auto-reverts after hand-off

# .ldd/config.yaml — project-level default (rare; only for mostly-greenfield repos)
mode: architect
```

Auto-trigger phrases (design, architect, greenfield, from scratch, decompose, structure for X) also flip the mode temporarily — the user sees `mode: architect` in the trace header whenever it's active.

## Full skill

[`../../skills/architect-mode/SKILL.md`](../../skills/architect-mode/SKILL.md) — the full 5-phase protocol with anti-pattern catalog and compliance checklist.
