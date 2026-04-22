# LDD hyperparameters

LDD exposes a **deliberately small** set of hyperparameters. In the [Gradient Descent for Agents](./theory.md) frame, every knob we add is one more dimension along which the loss function itself can drift (moving-target loss). The bias is "no knob unless the measured value of exposing it outweighs the method-evolution risk." Note that per-task **rigor** (how much of the apparatus to spin up) is *not* a knob — it is picked by the [thinking-levels](./thinking-levels.md) scorer, which derives the level deterministically from the task text. The knobs below tune individual axes' budgets, not the decision of which axes to activate.

> **Warning — anti-pattern:** the easiest way to make LDD look good on your current task is to tune hyperparameters until the rubric passes. That is **moving-target loss** (`./method-evolution.md` §"Red Flags"). Changing a knob to fit the current run is drift, not optimization. If you find yourself repeatedly tweaking `K_MAX` upward because "this task is complex," the problem is the task decomposition, not the budget.

## The exposed knobs (four core + one architect-mode sub-parameter)

The bundle deliberately exposes **four core knobs** that apply to every LDD run (`k_max`, `reproduce_runs`, `max_refinement_iterations`, `mode`) plus **one architect-mode-only sub-parameter** (`creativity`). Adding more opens the moving-target-loss surface that every skill here is built to resist.

## The core knobs

### 1. `k_max` — inner loop iteration budget

- **Default:** `5`
- **Range:** `1` to `20` (hard cap; above 20 the inner loop is not the right tool — see `docs/ldd/refactor.md`)
- **What it controls:** maximum iterations in the fix-loop before `loop-driven-engineering` §Escalation fires
- **When to change:**
  - Reduce to `2` or `3` for exploratory / throwaway work where you would rather restart than grind
  - Increase to `8` or `10` ONLY if individual iterations are very short and the task is well-localized (e.g. many quick unit-test cycles)
  - Do NOT increase to avoid escalation — escalation is the signal that the loop isn't converging and something structural is wrong

### 2. `reproduce_runs` — reproducibility-first Branch A reruns

- **Default:** `2` (additional runs beyond the initial failure)
- **Range:** `1` to `10`
- **What it controls:** how many times `reproducibility-first` re-runs the failing case before concluding deterministic / flaky / transient
- **When to change:**
  - Reduce to `1` for very slow tests (e.g. 20-min E2E) where the budget cost outweighs the noise risk
  - Increase to `4` or `5` for tests known to have low flake rates where you need higher confidence before editing
  - Do NOT set to `0` — that defeats the skill

### 3. `max_refinement_iterations` — y-axis budget

- **Default:** `3`
- **Range:** `1` to `10` (hard cap)
- **What it controls:** maximum refinement passes in `iterative-refinement` before stopping regardless of remaining gradient
- **When to change:**
  - Reduce to `1` or `2` for time-critical polish
  - Increase cautiously — refinement is asymptotic; past iteration 5 the returns are typically indistinguishable from noise

### 4. `mode` — reactive vs. architect

- **Default:** `reactive`
- **Values:** `reactive` | `architect`
- **What it controls:** whether LDD operates as a debugger / fixer over existing code (`reactive`) or as an architect generating structure from requirements (`architect`). See [`./architect-mode.md`](./architect-mode.md) for the full 5-phase protocol.
- **When to change:**
  - Switch to `architect` when starting a greenfield system, proposing a new module, or when the user explicitly asks for "architecture" / "design" / "structure for X"
  - Stay on `reactive` for bug fixes, feature additions, refactors, incident response — the default 95 % of the time
  - Architect mode is strictly opt-in; an auto-trigger on phrases like "design" / "architect" / "greenfield" / "from scratch" flips it temporarily for that one task, then reverts. As of the thinking-levels design, the coding agent auto-dispatches a **thinking level (L0..L4)** via a 9-signal scorer (the 6 original architect-dispatch signals plus `layer-crossings +2`, `contract-rule-hit +2`, `unknown-file-territory +1`). Architect-mode is reached through the **L3 / L4 presets** — there is no separate architect-only threshold anymore. The agent echoes `Dispatched: auto-level L<n> (signals: …)` in the trace header so you always see what's active and can override with one reply. Full scorer + CLI + buckets: [`../SKILL.md`](../SKILL.md) § Auto-dispatch: thinking-levels (and [`./level_scorer.py`](./level_scorer.py) for the deterministic implementation).

### 5. `creativity` — architect-mode loss-function selection

**Only meaningful when `mode=architect`.** Ignored otherwise.

- **Default:** `standard`
- **Values:** `conservative` | `standard` | `inventive`
- **What it controls:** which **loss function** the architect optimizer minimizes over the space of designs. Levels are **three discrete objectives**, not a continuous freedom dial. Each has its own rubric shape and its own Pass/Fail criteria — they are orthogonal, not ranked.

| Level | Informal loss | Use when |
|---|---|---|
| `conservative` | `L = rubric_violations + λ · novelty_penalty` | Enterprise with "no new tech", small team, near-zero risk tolerance, production ship soon |
| `standard` | `L = rubric_violations` (LDD baseline) | Every architect task without a specific reason for one of the others — 95 % of architect runs |
| `inventive` | `L = rubric_violations_reduced + λ · prior_art_overlap_penalty` | Research / prototype; known patterns demonstrably don't fit; user explicitly wants novelty |

**Restrictions:**
- **Cannot be integer-tuned.** No "creativity=5" — three named levels only. Discrete objectives prevent moving-target-loss ("turn it up until the output feels creative" is exactly the anti-pattern).
- **Cannot switch mid-task.** Changing mid-gradient mixes loss functions into incoherent optimization. Agent refuses; restart the task if you want a different level.
- **`inventive` requires per-task user acknowledgment.** Cannot be set as project-level default in `.ldd/config.yaml` — if found there, the agent ignores it and downgrades to `standard` with a trace warning. This forces research-grade work to be consciously re-opted-into each time.
- **Auto-trigger on "invent" / "novel" / "research" / "experimental" / "paradigm"** flips level to `inventive`, but then the acknowledgment flow still runs.

Full per-level spec (what changes in Phase 2 non-goals / Phase 3 candidates / Phase 4 scoring / Phase 5 deliverable) lives in [`./architect-mode.md`](./architect-mode.md) § Creativity levels.

## What is NOT exposed (by design)

| Knob we considered | Why not exposed |
|---|---|
| **Loss weights per rubric item** | Direct gateway to moving-target loss. Rubric items are intentionally equal-weight — if one item seems more important in your context, that's a scenario-design issue, not a weight-tuning issue |
| **`K_MAX` learning-rate multiplier** | Method-evolution rollback uses a fixed halving. Exposing it invites "just try it a few more times" — that's the anti-pattern the halving exists to prevent |
| **`min_occurrences` for method-evolution** | Fixed at 3. Lower = noise-driven skill changes. Higher = issues take too long to surface |
| **Drift-scan indicator subset** | All 7 indicators are the scan. Subsetting would encourage "only check what's currently clean" theater |
| **Temperature / top-p / sampling params** | Host-agent concerns, not LDD concerns. The bundle is behavior-shaping markdown; sampling is orthogonal |
| **Skill enable/disable flags** | Unused skills have no cost; disabling them hides capability without measurable benefit. Better path: don't invoke them (they won't fire without matching triggers) |
| **`level` (thinking-level L0..L4)** | **Derived, not configured.** The level is the scorer's output (see [`./thinking-levels.md`](./thinking-levels.md)), overridable per-task via `LDD[level=Lx]:` but never persisted as a project default or session override. Exposing it as a `/ldd-set` key would invite "set level=L4 because this feels hard today" — the exact moving-target-loss pattern the scorer exists to prevent. The override channel is per-task only, inline in the user message. |

## Three ways to set hyperparameters

### A. Inline on the `LDD:` prefix — per-task override

Highest priority. Wins over file + session settings for THIS task only.

```
LDD[k=3]: quick exploratory fix
LDD[k=10, reproduce=4]: deep dive on this flaky test
LDD[max-refinement=1]: one polish pass on this doc, then ship
LDD[no-reproduce]: I've already confirmed reproducibility — go straight to root-cause
```

Syntax:
- `k=<N>` or `kmax=<N>` — override `k_max`
- `reproduce=<N>` — override `reproduce_runs`
- `max-refinement=<N>` — override `max_refinement_iterations`
- `no-reproduce` — shortcut for `reproduce=0` with the explicit caveat that you are asserting Branch-B-level evidence
- `mode=architect` — switch to architect mode for this task (see architect-mode skill)
- `mode=reactive` — force reactive mode even if the task description looks architect-flavored (override auto-trigger)
- `creativity=conservative|standard|inventive` — architect-mode sub-parameter selecting the loss function for this task. `inventive` triggers an acknowledgment flow before architecture work begins.

Multiple flags comma-separated. Agent echoes the applied values in the trace block (`Budget : k=3/K_MAX=3 (override)`).

### B. Project config — `.ldd/config.yaml`

Persisted, git-committable, team-shared. Wins over bundle defaults, loses to inline overrides.

```yaml
# .ldd/config.yaml — optional; omit any key to use the bundle default

inner:
  k_max: 5
  reproduce_runs: 2

refinement:
  max_iterations: 3
```

Any key you omit falls through to the bundle default. The agent reports the effective config at the start of each LDD session; if it ever uses a default, that is explicit in the trace.

### C. Session override — slash commands

Non-persisted. Wins over file + bundle, loses to inline.

- `/loss-driven-development:ldd-config` — show the effective config (bundle / file / session / inline layers, visibly stacked)
- `/loss-driven-development:ldd-set <key>=<value>` — set a session-level override (e.g. `/loss-driven-development:ldd-set k_max=8`)
- `/loss-driven-development:ldd-reset` — clear session overrides

## Precedence

```
inline `LDD[...]` flags      ← wins
    ↓
/ldd-set session overrides
    ↓
.ldd/config.yaml in project root
    ↓
bundle defaults              ← loses
```

### Extra precedence layer for `mode` (architect vs. reactive)

The `mode` key has two additional value-sources on top of the generic chain above, both sitting BELOW inline flags and /ldd-set and ABOVE bundle defaults. Full chain:

```
inline LDD[mode=…] flag
    ↓
/ldd-architect command arg / /ldd-set mode=…
    ↓
.ldd/config.yaml
    ↓
trigger-phrase match in the dispatch table ("design" / "architect" / "greenfield" / …)
    ↓
auto-dispatch scorer (score ≥ 4)     ← v0.4.0; lowest before default
    ↓
bundle default (mode=reactive)
```

Same ordering for `creativity`: inline flag → command → session → config → trigger-phrase → auto-inferred-from-task-signals → bundle default (`standard`). `inventive` additionally requires per-task user acknowledgment regardless of which layer proposed it.

## Natural-language override

If the user writes in prose ("LDD: fix this, use a budget of 3 iterations"), the agent should parse the intent and apply the override — then echo the structured flag in the trace (`Budget : k=3/K_MAX=3 (parsed from prose)`) so the user can see what was inferred.

Natural-language parsing is best-effort. If ambiguous, the agent asks one clarifying question rather than guessing.

## Config discovery

The agent discovers config in this order, once per session:

1. Read `.ldd/config.yaml` if present in project root
2. Otherwise, bundle defaults
3. Session overrides accumulate from `/ldd-set` calls
4. Per-task inline overrides apply only to the current invocation

The effective config is reported in every trace block's header when any override is active, so users never wonder "did my setting stick?"

## Reference: starter config

Copy this to `.ldd/config.yaml` in your project root if you want team-shared defaults. Every key is optional.

```yaml
# LDD hyperparameters — all optional
# See docs/ldd/hyperparameters.md for what each does.

inner:
  k_max: 5              # inner-loop iteration budget
  reproduce_runs: 2     # reproducibility-first Branch A reruns

refinement:
  max_iterations: 3     # iterative-refinement hard cap
```

Drop this file in, commit it, and every team member's LDD sessions share the same budgets.
