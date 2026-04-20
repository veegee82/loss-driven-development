# Task Types — the dispatch table

This is the **single source of truth for "which MDs and which skills for which task"**. The skill `using-ldd` references this file; user-project `CLAUDE.md` / `AGENTS.md` should reference it too.

## The table

| Task type | Required reading (in addition to `using-ldd`) | Primary skills | Secondary skills |
|---|---|---|---|
| **Bug / failing test / flaky run** | `debugging.md` | `reproducibility-first` → `root-cause-by-layer` → `loss-backprop-lens` → `e2e-driven-iteration` | `dialectical-reasoning` (if fix has trade-offs) |
| **Design decision / trade-off / architectural choice** | `design-decisions.md` | `dialectical-reasoning` | `loss-backprop-lens` (step size) |
| **Structural change / refactor / architectural edit** | `refactor.md` | `loss-backprop-lens` (step size) → `root-cause-by-layer` (to scope the change) | `method-evolution` (if the refactor is a recurring pattern across tasks) |
| **Polish a deliverable (doc / diff / design)** | `refinement.md` | `iterative-refinement` | `dialectical-reasoning` (if scope is uncertain) |
| **Pre-commit / pre-release / pre-merge** | `release.md` | `docs-as-definition-of-done` → `drift-detection` (if release-candidate) | `dialectical-reasoning` (final ship/don't-ship) |
| **Production incident / fast-path diagnosis** | `incident.md` | `reproducibility-first` → `root-cause-by-layer` (fast-path variant) | `loss-backprop-lens` (avoid incident-fix overfitting) |
| **Methodology maintenance (a skill isn't working)** | `method-maintenance.md` | `method-evolution` | `drift-detection` (upstream check) |
| **General / multi-step / unsure** | `overview.md` + `getting-started.md` | `loop-driven-engineering` (entry, dispatches others) | all |

## Selection rules

1. **Match on user's own words** — the trigger-phrase table in `../../skills/using-ldd/SKILL.md` maps phrases to skills. If the user says "bug" / "failing test" / "error", the task is **debugging** regardless of what else is mentioned.
2. **Load minimum required.** A debugging task does NOT need `refinement.md`. Loading the whole methodology wastes context and dilutes signal.
3. **Ambiguity → ask.** If two task types match equally (e.g. a refactor that's also a bug fix), ask the user for one sentence of clarification before loading.
4. **`LDD:` prefix overrides auto-selection.** When the user prefixes with `LDD:`, load `getting-started.md` + `using-ldd` FIRST, then apply this table to their actual message.

## What you do NOT need to load

For any task, **do not pre-load**:
- `convergence.md` — only when the user asks about the mental model explicitly
- `in-awp.md` — only when the user asks about AWP / the origin
- All skill `SKILL.md` files at once — auto-triggered by their descriptions

These are on-demand references, not session-boot reading.

## Compliance signal

If a task-type-appropriate MD was consulted, the agent should reference it once in its response (e.g. "[per `debugging.md`, starting with `reproducibility-first`]"). If no MD is referenced and the response shows no LDD discipline, LDD is dormant — re-check install or prefix `LDD:`.

## Drift-resistance

This file is the **only place** where the task-type → MD mapping lives. Every skill body that mentions a sibling skill links through this table, not around it. If you change the mapping, update only here — `drift-detection`'s doc-model-drift indicator (§4 of `convergence.md`) will flag any duplicate/stale copy elsewhere.
