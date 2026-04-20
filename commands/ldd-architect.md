---
description: Switch LDD into architect mode for the next task. Runs the 5-phase protocol (Constraints → Non-goals → 3 Candidates → Scoring+Dialectical → Deliverable) from skills/architect-mode/SKILL.md. Opt-in, not default. Accepts optional creativity argument — /ldd-architect [conservative|standard|inventive].
---

Parse any argument after the command name. Accepted forms:

- **no argument** → `creativity=standard` (default)
- **`conservative`** | **`standard`** | **`inventive`** (positional) → set creativity level
- **`creativity=<level>`** (named form) → set creativity level

Reject any other value (e.g. `creativity=experimental`, `creativity=5`) with one line pointing at `docs/ldd/hyperparameters.md` § knob 5. Do not silently clamp.

Activate `mode=architect` + the chosen `creativity` level for the next user request in this session. Announce:

> *Architect mode active* with **`creativity=<level>`**.
> Loss function for this run: `<see architect-mode skill § Creativity levels for the exact form>`.
> The next task will run under the 5-phase protocol. Default reactive LDD resumes after hand-off.

### If `creativity=inventive`, run the acknowledgment flow BEFORE waiting for the task

Emit this literal block:

> `creativity=inventive` is opt-in for research-grade work. Confirming:
>  - Prior-art overlap is *penalized* in the objective; novelty is rewarded (if validation path is explicit)
>  - Rubric coverage items 1–2 (full constraint table, uncertainty naming) may be relaxed when the problem is under-specified by design
>  - Items 5–8 are replaced with invention-specific criteria (differentiation from prior art, experiment validation path, fallback to baseline)
>  - **Output is NOT production-ready by default.** Deliverable is a research prototype + a named fallback-to-standard path
>
> Reply `acknowledged` to proceed. Any other reply downgrades this run to `creativity=standard` and the downgrade is logged in the trace header.

Only after receiving literal "acknowledged" (case-insensitive) does the agent wait for the architect task under `creativity=inventive`. On any other reply, downgrade silently to `standard` and log the downgrade.

### When the task arrives

1. Apply the 5-phase protocol strictly (Phase 1 Constraints → Phase 2 Non-goals ≥ 3 → Phase 3 candidates → Phase 4 scoring table + dialectical on winner → Phase 5 deliverable commit). Phase 3 candidate count and Phase 4 scoring weights follow the chosen creativity level per `skills/architect-mode/SKILL.md` § Creativity levels.
2. Emit the architect-variant of the LDD trace block — header shows `mode: architect, creativity: <level>`, the `Loss-fn` line names the objective, and Phase completion is reported as it happens.
3. Score the final output against the rubric variant for the active creativity level (items 1–10 for standard; 1–11 with novelty-penalty item for conservative; items 1–4 + #I1–#I3 invention items for inventive).
4. Hand off at the end — announce rubric score, `loss_0` count from failing tests, and drop back to `mode=reactive` + `creativity=standard`.

### Guards

- If the user's next message is NOT an architect-suitable task (bug fix, refactor, review), do not force architect mode — explain briefly and revert to default reactive mode without silently running the reactive flow under the architect label (trace-integrity violation).
- If the user, mid-task, says "switch to conservative" (or any other creativity change), refuse per the level-switch prohibition in `skills/architect-mode/SKILL.md`. Restart-or-don't-restart is the only valid response.
- Architect mode is **single-task scope**. After hand-off, `mode` reverts to whatever the persistent config + session overrides dictate, and `creativity` reverts to `standard`.
