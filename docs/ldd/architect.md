# Architect mode — greenfield design under discipline

Load this when the user wants **structure / design / architecture invented** for a problem that has no existing code, or when they explicitly scope out existing code and ask "what should this be?". This is LDD's **opt-in constructive mode** — reactive LDD stays the default.

In the [Gradient Descent for Agents](../theory.md) frame, architect-mode is not a fifth gradient — it is a separate invocation path that computes loss over the **space of possible designs** rather than over an existing artifact. The four-axis loop structure still applies after Phase 5 hands off: the failing tests in the scaffold become `loss_0` for the inner loop; the doc is a y-axis deliverable that can be refined later; if three greenfield runs show the same rubric-violation pattern, `method-evolution` evolves architect-mode itself on the m-axis.

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

## Creativity levels — three loss functions

Architect mode has three creativity levels that select **different loss functions**, not amounts of freedom. Per LDD's neural-code-network framing (see [`convergence.md`](./convergence.md)), the optimizer is the same — the **objective** changes.

| Level | Informal loss | When to pick |
|---|---|---|
| `conservative` | `L = rubric_violations + λ · novelty_penalty` | No-new-tech policy / small team / near-zero risk tolerance / production imminent. All 3 candidates must be battle-tested patterns. Component novelty is penalized. |
| `standard` (default) | `L = rubric_violations` | 95 % of architect runs. Current 10-item rubric, 3 candidates on a load-bearing axis, dialectical pass on winner. |
| `inventive` | `L = rubric_violations_reduced + λ · prior_art_overlap_penalty` | Research / prototype / novelty genuinely required. Prior-art overlap is penalized; novelty rewarded IF validation path is explicit. Requires user acknowledgment before running. |

Hard rules:

- **Cannot be integer-tuned.** Only the three named levels. Integers would tempt moving-target-loss ("dial up until output feels creative") — the exact drift pattern LDD fights elsewhere.
- **Cannot switch mid-task.** Mixing loss functions mid-gradient is incoherent optimization. Restart the task if you need a different level.
- **`inventive` requires per-task acknowledgment**, cannot be set project-level default in `.ldd/config.yaml`.

Full per-level spec: [`../../skills/architect-mode/SKILL.md`](../../skills/architect-mode/SKILL.md) § Creativity levels. Per-level rubric variants: [`../../evaluation.md`](../../evaluation.md) § `architect-mode`.

## Activation

Four opt-in paths (precedence: inline flag > command arg > trigger-phrase > auto-dispatch > bundle default):

```
LDD[mode=architect]: design a billing service for 50M users
                                     ↑ inline flag, this task only

/loss-driven-development:ldd-architect          # session: flips for next task
                                                 # then auto-reverts after hand-off

# .ldd/config.yaml — project-level default (rare; only for mostly-greenfield repos)
mode: architect
```

Auto-trigger phrases (design, architect, greenfield, from scratch, decompose, structure for X) flip the mode temporarily — the user sees `mode: architect` in the trace header whenever it's active.

**Auto-dispatch via the thinking-levels scorer** — the coding agent scores every non-trivial task against 9 signals (the 6 original architect-dispatch signals — greenfield `+3`, ≥ 3 new components `+2`, cross-layer `+2`, ambiguous `+2`, bugfix `−5`, single-file `−3` — plus `layer-crossings +2`, `contract-rule-hit +2`, `unknown-file-territory +1`). The sum buckets into a thinking-level L0..L4; architect-mode is reached through the **L3 and L4 presets** (score ≥ 4 buckets L3 directly; score ≥ 8 buckets L4, with a creativity-clamp back to L3 when no inventive cues are present). Creativity is inferred from the same task signals (regulated → `conservative`, research / novel → `inventive`, else `standard`). The agent MUST echo `Dispatched: auto-level L<n> (signals: …)` in the trace header. Full scorer + inference table + buckets: [`../../skills/using-ldd/SKILL.md`](../../skills/using-ldd/SKILL.md) § Auto-dispatch: thinking-levels (and [`../../scripts/level_scorer.py`](../../scripts/level_scorer.py) for the deterministic implementation).

## Full skill

[`../../skills/architect-mode/SKILL.md`](../../skills/architect-mode/SKILL.md) — the full 5-phase protocol with anti-pattern catalog and compliance checklist.
