---
name: architect-mode
description: The 5-phase design protocol that is active at thinking-levels L3 and L4. NOT a separate mode — it is the discipline the level preset pulls in. Opt-in via four paths — inline `LDD[level=L3]:` (or `LDD[level=L4]:`) prefix, the `/ldd-architect` command, trigger phrases like "design" / "architect" / "from scratch" / "greenfield", or the thinking-levels auto-dispatch landing at L3 / L4 (9-signal scorer; see `../using-ldd/SKILL.md` § Auto-dispatch: thinking-levels). Supports three creativity levels (`conservative` | `standard` | `inventive`) that change the loss function, not the amount of structure.
---

# Architect Mode — opt-in discipline, orthogonal to the four loops

## The Metaphor

**The city planner before the first brick.** The mason lays walls well — straight, plumb, mortar set. But the mason does not decide where the streets go, where the market belongs, which districts connect to the harbour. That is the city planner's work: constraints survey → exclusions map (non-goals) → three alternative plans on a load-bearing axis → scoring → chosen plan → initial scaffold that proves the plan can be built. Build without a plan and the city is a maze. LDD's reactive stack is the mason; architect-mode is the city planner — opt-in, five rigid phases, creativity as a choice of loss function not an amount of permissiveness.

## Overview

In [Gradient Descent for Agents](./theory.md), architect-mode is **not a fifth loop** — it is a separate invocation path that computes loss over the **space of possible designs** rather than over an existing artifact. The four-axis structure (code / output / method / thought) still applies *after* architect-mode closes: Phase 5 hands the failing tests to the inner loop (`θ = code`), the architecture doc becomes a candidate for refinement (`y = output`) later, and if three greenfield runs repeat the same rubric violation pattern, `method-evolution` evolves architect-mode itself (`m = method`).

LDD's default stack is **reactive**: it measures loss on existing code and drives a gradient-descent fix-loop. Architect mode **inverts** this — the loss is computed over the **space of possible designs** for a stated problem, not over an existing artifact. The agent's role shifts from pathologist to constructor.

**Core principle:** architecture is not invented freely. It is invented under **explicit quality constraints** and delivered with **explicit non-goals**. A "free-form design doc" produced without a rubric is exactly the moving-target loss that LDD rejects everywhere else — architect mode fences this in with a phased protocol and a rubric. The rubric's **shape** depends on the chosen creativity level (see below); the discipline itself is never optional.

**This is an opt-in mode.** LDD default treats the presence of code as the signal to iterate. When there is no code yet — or the existing code is scaffold-level and the user is asking "what should this system BE?" — the default mode would degrade into freewheeling. Architect mode replaces it for that one task.

## The neural-code-network framing — creativity as loss-function choice

LDD's core framing (see [`./convergence.md`](./convergence.md)) treats every work session as gradient descent on code:

```
θ_{k+1} = θ_k  −  η · ∇L(θ_k)  +  regularizer(θ_k)
```

**Architect-mode creativity levels are three discrete choices of `L` — not three amounts of optimization.** The optimizer is the same; the *objective* changes. This framing matters because it prevents the "freedom dial" from being a moving-target: you don't tune continuously between levels, you commit to one objective per task.

| Level | Loss function (informal) | Regularizer | Rubric shape |
|---|---|---|---|
| `conservative` | `L = rubric_violations + λ · novelty_penalty` | Novelty itself is a cost | Standard 10 items + `team-familiarity` weighted 2× in scoring; all 3 candidates must be battle-tested |
| `standard` (default) | `L = rubric_violations` | Contracts + layer boundaries | Standard 10 items as-is; 3 candidates on a load-bearing axis |
| `inventive` | `L = rubric_violations_reduced + λ · prior_art_overlap_penalty` | Novelty is *rewarded*, prior-art overlap is penalized — but an experiment-validation path is mandatory | Items 1–2 may be relaxed; items 5–8 replaced with invention-specific criteria (novelty, fallback path, validation experiment) |

**Consequences of this framing:**

1. **No "grade 7" or "grade 3.5"** — the levels are discrete and named. Integers tempt tuning-until-it-feels-right, which is the exact drift pattern LDD fights.
2. **Level-switch is task-scoped.** You cannot drop from `inventive` to `standard` halfway through a task — that would mix two loss functions into one gradient, which is incoherent optimization. Start over if you need a different level.
3. **Each level has its own Pass/Fail criteria.** A `conservative` run that invents a new pattern fails rubric item #11 (novelty-penalty). An `inventive` run that produces a boring well-known design fails rubric item #I3 (differentiation from prior art). Levels are not ranked "less strict → more strict" — they're orthogonal objectives.
4. **Default stays `standard`.** `conservative` and `inventive` require explicit opt-in. `inventive` additionally requires a user acknowledgment (see below).

## Creativity levels — detailed behavior

### Level 1: `conservative`

**When to pick it.** Enterprise repos with strict "no new tech" policy. Team has shallow experience with unfamiliar patterns. Risk tolerance is near zero. Production ship is weeks away on a small team. Regulatory or on-call context makes convention-breaks expensive.

**What it changes:**
- **Phase 2 non-goals** must include ≥ 1 explicit "not a new pattern / language / framework" declaration
- **Phase 3 candidates** must all be patterns with ≥ 5 years of track record in the user's domain. Cosmetic variants are even more tightly rejected — all three differ on proven axes (monolith / modular-monolith / service-decomposition, not "novel CRDT variants")
- **Phase 4 scoring** weighting: `team-familiarity` dimension weighted **2×**; `evolution-paths` weighted **0.5×** (far-future optionality is deprioritized)
- **Phase 5 scaffold** must use the stack the user's codebase already uses (or explicitly names). Introducing a new language / framework / database fails the rubric
- **Extra rubric item #11:** `novelty-penalty` — any component scoring > 1 on an internal novelty scale (0 = existing in codebase, 1 = new-but-standard, 2 = new-for-team, 3+ = new-for-industry) triggers rubric violation. Target: zero components above 1

### Level 2: `standard` (default)

**When to pick it.** Any architect-mode task without a specific reason for one of the other two levels. This IS the default architect behavior — the current 10-item rubric, 3 candidates on a load-bearing axis, dialectical pass on the winner, 9-section deliverable. No behavior change from the v0.3.0 architect-mode.

**This level is the neutral objective** — `L = rubric_violations` with no extra regularizer beyond LDD's baseline (contracts / layer boundaries / docs-as-DoD).

### Level 3: `inventive`

**When to pick it.** Research contexts. Greenfield with no legacy constraint. Prototype / proof-of-concept. User explicitly wants a novel paradigm or pattern. Problem is one where known solutions demonstrably do not fit.

**Requires explicit user acknowledgment before architecture work begins.** The agent asks, exactly once:

> `creativity=inventive` is opt-in for research-grade work. Confirming:
>  - Prior-art overlap is *penalized* in the objective; novelty is rewarded (if validation path is explicit)
>  - Rubric coverage items 1–2 (full constraint table, uncertainty naming) may be relaxed when the problem is under-specified by design
>  - Items 5–8 are replaced with invention-specific criteria (see below)
>  - **Output is NOT production-ready by default.** Deliverable is a research prototype + fallback-to-baseline path
>
> Reply `acknowledged` to proceed. Otherwise the run downgrades to `standard`.

Without the literal acknowledgment, the agent silently downgrades to `standard` and announces the downgrade in the trace.

**What it changes on acknowledgment:**
- **Phase 2 non-goals** may declare "not necessarily following existing industry patterns"; explicit "known unknowns" section replaces full uncertainty-naming
- **Phase 3 candidates** may be 2 instead of 3: one baseline (the `standard`-equivalent answer, serving as fallback) + one invention. A third candidate is optional, not required
- **Phase 4 scoring** new dimensions replacing items 5–8: `differentiation from prior art` (how new is this really?), `experiment-validation path` (how do we know it works before production?), `failure-mode-acceptable` (what breaks if the invention fails? what's the cost of the fallback?)
- **Phase 5 deliverable** scaffold may be a prototype (not production-grade code). Must include: a `PRIOR_ART.md` section listing what the design deliberately rejects and why; an `EXPERIMENT.md` validation plan; a pointer to the baseline fallback
- **Rubric items #I1–#I3** replace items #5–#8: differentiation from prior art, validation-path explicit, fallback-to-baseline path named

**Default target: 0 violations.** But `inventive` explicitly tolerates known-unknowns in the constraint table — so rubric items 1 and 2 may score 1/1 and still not be failures if the "known unknowns" section is present and honest.

## Level-switch prohibition

**You cannot change creativity levels during a single architect task.** The levels are three different objective functions; mixing them mid-gradient produces incoherent optimization.

If the user, mid-task, says "actually, switch to conservative", the agent responds:

> Creativity level is task-scoped and cannot be changed mid-run — doing so would mix two loss functions into the same gradient descent. To run this task under a different level, acknowledge this run as aborted and re-submit the task with the new level.

Aborting and restarting is the only valid path. This is not about user friction; it is about preventing the exact moving-target-loss failure that the level-discretization was designed to prevent.

## Project-level config restriction

`.ldd/config.yaml` may set `creativity: conservative` or `creativity: standard` as the project-wide default (for repos that are entirely one or the other). **It may NOT set `creativity: inventive`** — research-grade work must be a per-task acknowledgment, not a persistent default. If a config file contains `creativity: inventive`, the agent ignores it and logs a warning in the trace header.

## When to use architect mode (any level)

Invoke when **all** of:

- The user is asking for **structure / design / architecture** for a system, module, or subsystem — not a fix, not a refinement, not a review
- The existing code is either **absent** (greenfield) or **deliberately scoped out** ("design as if the current stuff didn't exist")
- The output the user wants is a **design artifact** (architecture doc + initial scaffold + contracts), not a working end-to-end build

Signals that trigger this mode:

- `LDD[level=L3]:` or `LDD[level=L4]:` (optionally combined with `LDD[creativity=<level>]:`) — explicit level override
- `/loss-driven-development:ldd-architect` command (accepts optional `creativity` arg) — documented sugar for `LDD[level=L3]:`
- Phrases: "design", "architect", "from scratch", "greenfield", "how should I structure", "propose an architecture", "decompose this", "what's the right shape for X"
- Additional auto-trigger for `inventive`: "invent", "novel paradigm", "research", "experiment", "prototype a new" — the agent asks for acknowledgment per the inventive-level spec before proceeding
- **Deprecated (v0.11.0, removed in v0.12.0):** `LDD[mode=architect]:` is a silent alias for `LDD[level=L3]:`. `mode` is a pure function of level (L0–L2 ⇒ reactive, L3/L4 ⇒ architect) and is no longer a user-facing axis.

**Do not use** for:

- Bug fixes, feature additions to existing code → default LDD (inner loop)
- Refactor with preserved behavior → `refactor.md` task type (inner loop with step-size calibration)
- Polishing a finished design doc → `iterative-refinement` (y-axis)
- Evolving the LDD bundle itself → `method-evolution` (outer loop)

## Auto-dispatch by the coding agent

The agent MAY enter the architect-mode protocol on its own — without an explicit `LDD[level=L3]:` flag, `/ldd-architect` command, or trigger-phrase match — when the task description carries enough structural signals that the thinking-level scorer buckets the task at L3 or L4. This covers the case where a user describes a greenfield design without using the dispatch vocabulary (`"design"`, `"architect"`, `"greenfield"`); the signals in the task shape itself are enough to warrant the 5-phase discipline.

**Full scorer + creativity-inference table + precedence rule live in [`../SKILL.md`](../SKILL.md) § Auto-dispatch: thinking-levels** (and the deterministic implementation at [`./level_scorer.py`](./level_scorer.py)). Summary here:

- **Score ≥ 4 → L3, score ≥ 8 → L4** (weighted sum of 9 signals). At L3 and L4 the architect-mode 5-phase protocol is active automatically — there is no separate `mode=architect` axis to set, and no separate threshold. Dominant positive signals are greenfield (+3), ≥ 3 new components (+2), cross-layer scope (+2), ambiguous requirements (+2), layer-crossings (+2), contract/R-rule hit (+2). Negatives: explicit bug-fix (−5), single-file known-solution (−3). One small positive: unknown-file-territory (+1).
- **Creativity is inferred from the same task signals:** regulatory / no-new-tech / tight-team-deadline cues → `conservative`; research / novelty / experiment cues → `inventive`; neither → `standard`.
- **Explicit user triggers always win** (inline `LDD[level=Lx]:` flag > command > trigger phrase > auto-dispatch > bundle default). If the user wrote `LDD[level=L2]:` on a task with auto-score 6, the level stays L2 (reactive) and the architect-mode protocol does not run.
- **The `inventive` acknowledgment flow is unchanged.** Auto-dispatch can *propose* `inventive`, but without the literal `acknowledged` reply the run silently downgrades to `standard`. The scorer is allowed to nominate; the ack gate is not.

### Mandatory trace echo when auto-dispatch fires

When the scorer buckets a task at L3 or L4, the agent MUST echo the single-line dispatch header before any work begins. The user gets to see and override the agent's judgment with one follow-up:

```
Dispatched: L3/structural · creativity=standard (signals: greenfield=+3, cross-layer=+2)
```

Without the echo, the user cannot distinguish "I asked for L3/L4" from "the agent chose L3/L4 on my behalf" — and the audit trail for the decision is lost. Silent auto-dispatch is a trace-integrity violation.

The auto case is implicit — no `auto-level` keyword. When the header carries `user-explicit` / `user-bump` / `user-override-down` in the parenthetical, the dispatch came from an inline flag / command / trigger phrase / natural-language bump. See [`../SKILL.md`](../SKILL.md) § "Design-phase (L3/L4) variant of the trace block" for the full format.

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
4. If the user replies with a resume trigger, drop back to the scorer's default (typically L2/deliberate); all subsequent LDD flags revert to defaults unless overridden. The architect-mode 5-phase protocol is no longer active because the level is no longer L3/L4 — same outcome as if the user had explicitly said `LDD[level=L2]:`.

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
