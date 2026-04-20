---
name: architect-mode
description: Use when the user wants an architecture, design, or structure invented from requirements — greenfield service, new module, system decomposition, or the conceptual/structural layer "between X and Y" where X is the problem and Y is the delivered system. NOT the default mode. Opt-in via `LDD[mode=architect]:` prefix, the `/ldd-architect` command, or phrases like "design", "architect", "from scratch", "greenfield", "how should I structure".
---

# Architect Mode

## Overview

LDD's default nine-skill stack is **reactive**: it measures loss on existing code and drives a gradient-descent fix-loop. Architect mode **inverts** this — the loss is computed over the **space of possible designs** for a stated problem, not over an existing artifact. The agent's role shifts from pathologist to constructor.

**Core principle:** architecture is not invented freely. It is invented under **explicit quality constraints** and delivered with **explicit non-goals**. A "free-form design doc" produced without a rubric is exactly the moving-target loss that LDD rejects everywhere else — architect mode fences this in with a 10-item rubric and a forced 3-candidate comparison.

**This is an opt-in mode.** LDD default treats the presence of code as the signal to iterate. When there is no code yet (or the existing code is scaffold-level and the user is asking "what should this system BE?"), the default mode would degrade into freewheeling. Architect mode replaces it for that one task.

## When to use

Invoke when **all** of:

- The user is asking for **structure / design / architecture** for a system, module, or subsystem — not a fix, not a refinement, not a review
- The existing code is either **absent** (greenfield) or **deliberately scoped out** ("design as if the current stuff didn't exist")
- The output the user wants is a **design artifact** (architecture doc + initial scaffold + contracts), not a working end-to-end build

Signals that trigger this mode:

- `LDD[mode=architect]:` prefix
- `/loss-driven-development:ldd-architect` command
- Phrases: "design", "architect", "from scratch", "greenfield", "how should I structure", "propose an architecture", "decompose this", "what's the right shape for X"

**Do not use** for:

- Bug fixes, feature additions to existing code → default LDD (inner loop)
- Refactor with preserved behavior → `refactor.md` task type (inner loop with step-size calibration)
- Polishing a finished design doc → `iterative-refinement` (y-axis)
- Evolving the LDD bundle itself → `method-evolution` (outer loop)

## The architect protocol

This is a rigid 5-phase protocol. Unlike the other skills which adapt, architect mode is prescriptive: when it runs, it runs in this order.

### Phase 1 — Constraint extraction

Before producing any design, enumerate the constraints. For every stated requirement X_i, extract:

- **Functional target**: what behavior the system must produce
- **Non-functional target**: latency, throughput, cost, security, compliance, team-size-to-maintain
- **Boundary**: what the system owns vs. what it integrates with
- **Uncertainty**: what the user did NOT specify (and likely left to you)

Output: a **constraint table**. One row per constraint, three columns (requirement / target / source).

**Rubric item 1 — covered:** every stated requirement X_i appears in the table.
**Rubric item 2 — discipline:** uncertainties are explicitly named, not silently filled in.

### Phase 2 — Non-goals declaration

Before proposing any design, declare **≥ 3 things the architecture will NOT do**. Non-goals bound scope and make future review/refinement tractable.

Good non-goals are concrete and fight scope creep:

- "Not multi-region replicated (single-region, DR is out of scope)"
- "Not a multi-tenant billing engine (single-tenant per deployment)"
- "Not backwards-compatible with the existing `/v1/users` endpoint (v2 is a new contract)"

Bad non-goals are empty:

- "Not perfect" (not actionable)
- "Not solving world hunger" (not adjacent to the task)

**Rubric item 3:** ≥ 3 concrete, adjacent non-goals stated before any design work.

### Phase 3 — Three candidate designs

Generate **exactly three candidate architectures** that differ on a load-bearing axis — not three cosmetic variants. Examples of load-bearing axes:

- **Monolithic vs. microservice vs. modular-monolith-with-cells**
- **Sync RPC vs. async event-driven vs. hybrid with outbox**
- **Single database vs. CQRS vs. multi-store with explicit sync**
- **Build vs. buy vs. wrap-a-library**

Each candidate gets: a one-line name, a 3-5 sentence sketch, a named trade-off vector (where it wins, where it loses).

**Rubric item 4:** three candidates on a load-bearing axis; cosmetic variants (same architecture, different names) fail the rubric.

### Phase 4 — Scoring + dialectical selection

Score each candidate against the constraints from Phase 1 plus a standard 6-dimension architectural rubric:

1. **Requirements coverage** (every constraint satisfied)
2. **Boundary clarity** (every layer/service boundary has a named contract)
3. **Evolution paths** (known future requirements have extension points)
4. **Dependency explicitness** (external systems/libraries named with version/contract)
5. **Test strategy** (how validation will happen before deploy)
6. **Rollback plan** (if deployment fails, recovery path)

Then apply `dialectical-reasoning`: for the top candidate, produce thesis (why it wins) → antithesis (what a hostile reviewer would attack) → synthesis (sharpened version, with the antithesis-forced refinements baked in).

**Rubric item 5:** scoring is explicit, not narrative. A table with 3 rows × 6 columns + a total.
**Rubric item 6:** a real antithesis was run on the winning candidate. "It's obviously best" is not an antithesis.

### Phase 5 — Deliverable: architecture doc + scaffold + contracts

The output is **one commit** containing:

1. **`docs/architecture.md`** (or equivalent) with sections:
   - Problem statement (quote the user's ask verbatim)
   - Constraint table (from Phase 1)
   - Non-goals (from Phase 2)
   - Candidates considered (Phase 3, with rejection rationale per loser)
   - Chosen design (Phase 4 winner with synthesis)
   - Scoring rubric with totals (Phase 4 table)
   - Integration contracts (every external boundary named)
   - Test strategy + rollback plan
2. **Initial scaffold** — directory structure + empty module files + one failing test per component that the real implementation must pass
3. **Measurable success criteria** — one metric per requirement, with target value

**Rubric item 7:** the architecture doc has all nine subsections (not handwaved).
**Rubric item 8:** the scaffold compiles / imports cleanly (not pseudocode).
**Rubric item 9:** at least one failing test per component exists, naming the expected behavior.
**Rubric item 10:** every requirement has a named success metric with a numeric target.

## The loss function in architect mode

```
loss_architect = Σ (rubric_item_violated_i)  over 10 items
Δloss_architect = how many violations the architecture-refinement closed
```

Target: 0/10. Real designs under pressure usually start at 3-5/10 after the first pass; iterative refinement (y-axis, using `iterative-refinement`) brings it down. Accept shipping at 1-2/10 only if each violation is explicitly acknowledged in a "known gaps" section.

## Red flags — architect mode being abused

- "Let me just write a design doc" **without going through Phases 1-4** → free-form invention, not architecture
- **Only one candidate design** considered → Phase 3 violation; real architecture is comparative
- **Non-goals section missing or vague** → scope-creep is guaranteed
- **No scoring rubric, just narrative** → rubric drift, moving-target loss on the design itself
- **"Let me sketch this out and we'll formalize later"** → deferred discipline = no discipline
- **Antithesis done against a strawman** (weak attack, easily defeated) → Phase 4 violation; rerun with a real attack

## Anti-patterns

| Pattern | Why wrong |
|---|---|
| Proposing the first architecture that comes to mind | No Phase 3; no comparison; likely biased by recent projects |
| Writing the architecture doc as prose only | No rubric scoring; no audit trail; the "did we consider X" question is unanswerable |
| Skipping non-goals ("we'll figure out scope as we go") | Scope creep becomes unbounded; refactor.md will fire in 3 months |
| Making the scaffold pseudocode | The scaffold IS the first gradient; pseudocode can't be measured |
| Treating architect mode as "LDD's smart mode" | It's one mode for one situation (greenfield). Default LDD remains reactive |

## Relation to the default stack

Architect mode is **not** a replacement for the other skills. When architect mode produces the deliverable:

- `docs-as-definition-of-done` enforces that the doc + scaffold + tests land in one commit
- `dialectical-reasoning` is used inside Phase 4 (not as a separate invocation)
- `loss-backprop-lens` applies to the candidate-scoring — a variant that wins by 1/10 is a marginal case; a variant that wins by 4/10 is decisive
- `iterative-refinement` applies to the architecture doc if the first pass has violations

The inner-loop skills (`root-cause-by-layer`, `reproducibility-first`, `e2e-driven-iteration`) do **not** apply until the scaffold becomes real code — that's when the inner loop resumes its default role.

## Escalation when a phase cannot complete cleanly

Architect mode is rigid by design — but real tasks sometimes resist clean 5-phase execution. Explicit handling:

- **Phase 1 — user gave too few constraints.** Ask ONE clarifying question covering the biggest uncertainty. If still under-specified, proceed with the top 2 uncertainties explicitly named in the table as `user to decide` — do not invent answers.
- **Phase 3 — cannot find 3 distinct candidates on a load-bearing axis.** The problem space is already narrow. Acceptable degradation: 2 candidates with explicit "space is narrow because [reason]" note. Hard floor: never 1 candidate — if you cannot generate 2, reject the task and ask the user to loosen a constraint.
- **Phase 4 — top two candidates score within 10% of each other.** This is the *signal that a hidden preference is needed from the user* — surface the tie and ask which trade-off dimension they care most about. Do not silently break the tie on aesthetics.
- **Phase 5 — architecture doc ships with N/10 rubric violations.** Acknowledge each violation by name in a "Known architectural gaps" section at the top of the doc, each with a "how/when to close" note. Shipping at ≥3/10 violations is a failed architect-mode run — re-run.

## Hand-off from architect mode to default mode

Phase 5 produces failing tests — those are the first `loss_0` for the inner loop. The transition is explicit:

1. In the final trace block, emit a **Hand-off line**:
   ```
   │ Hand-off : architect-mode closed N/10 rubric; next: default LDD inner loop
   │            loss_0 = <count of failing tests from scaffold>
   ```
2. In the reply, say to the user one line: *"architect-mode complete. To start implementation, say `LDD: begin implementation` or similar — I'll switch to reactive mode and run `reproducibility-first` + `root-cause-by-layer` against the first failing scaffold test."*
3. **Do not auto-resume.** The user must explicitly trigger the next task. This prevents architect-mode from silently consuming K_MAX iterations of inner-loop budget on its own implementation.
4. If the user replies with a resume trigger, drop `mode=architect`; all subsequent LDD flags revert to defaults unless overridden.

## Compliance checklist

- [ ] Phase 1 constraint table present, every X_i covered
- [ ] Phase 2 non-goals ≥ 3, concrete, scope-bounding
- [ ] Phase 3 exactly three candidates on a load-bearing axis
- [ ] Phase 4 scoring table (candidates × 6 dimensions + total)
- [ ] Phase 4 dialectical pass on winner (thesis/antithesis/synthesis)
- [ ] Phase 5 architecture.md with all nine subsections
- [ ] Phase 5 scaffold compiles
- [ ] Phase 5 one failing test per component
- [ ] Phase 5 measurable success criteria per requirement
- [ ] All of above committed as ONE logical commit (code + tests + docs)

## Real-world cue

If an architect-mode invocation closes with:

- Fewer than 3 candidates → `Phase 3 violation, not a real comparison`
- No non-goals section → `Phase 2 violation, scope is unbounded`
- Scaffold-only pseudocode with no failing tests → `Phase 5 violation, first gradient missing`

…then architect mode degenerated into "write me a design doc." The rubric exists to prevent this. Re-run under discipline or acknowledge the gaps in a "known architectural debts" section at the top of the doc.
