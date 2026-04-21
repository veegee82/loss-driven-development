---
name: using-ldd
description: Use whenever the user prefixes a message with "LDD:" or mentions LDD, loss-driven development, loss, gradient, SGD on code, drift, refinement loop, outer loop, inner loop, method evolution, or "apply LDD". Bootstrap / entry-point skill that explains how to dispatch the other LDD skills and the trigger-phrase table they respond to.
---

# Using LDD — the bundle entry-point

## Overview

Loss-Driven Development (LDD) is a ten-skill bundle that treats code changes as SGD steps and forbids overfitting to the current test. This entry-skill exists so you (the agent) know **when to reach for which LDD skill** without the user having to name each one by hand.

**Core principle:** if the user prefixes their message with `LDD:` or mentions any of the trigger phrases below, LDD discipline is explicitly requested. Match their intent to the right sub-skill and announce which one you are applying.

## Trigger phrases (user → skill mapping)

When the user's message contains any of these patterns, invoke the paired skill.

| User signal | Invoke |
|---|---|
| `LDD:` prefix, "apply LDD", "use LDD" | Enter full LDD mode — default entry = `loop-driven-engineering` unless a more specific sub-skill matches below |
| "failing test", "CI is red", "flaky", "one-off failure", "intermittent" | First `reproducibility-first`, then `root-cause-by-layer` if the failure is real |
| "bug", "error", "exception", "unexpected behavior", "why is this breaking" | `root-cause-by-layer` |
| "I've tried this 3 times", "keeps failing the same way", five fix-commits in one area | `loss-backprop-lens` (local-minimum trap) |
| "this fix works but I'm not sure it generalizes", "will this break sibling tests" | `loss-backprop-lens` (generalization check) |
| "I'm mid-debug", "is the fix done yet", before closing any fix-loop | `e2e-driven-iteration` |
| "should we ship this", "is this the right approach", design trade-off | `dialectical-reasoning` |
| "this doc/diff/output is okay but could be better", "polish this" | `iterative-refinement` |
| "same thing keeps happening across tasks", "the skill itself might be wrong" | `method-evolution` |
| "is this codebase healthy", release-candidate review, weekly check | `drift-detection` |
| "about to commit", "ready to merge", "declaring this done" | `docs-as-definition-of-done` |
| "design X", "architect Y", "greenfield", "from scratch", "how should I structure", "propose an architecture", "decompose this problem", "what's the right shape for X" | `architect-mode` (opt-in — four paths: inline `LDD[mode=architect]:` flag / `/ldd-architect` command / these trigger phrases / the auto-dispatch scorer below; see skill for the 5-phase protocol and the hand-off back to reactive) |

## Auto-dispatch for architect-mode

When the user hasn't explicitly asked for architect-mode (no `LDD[mode=architect]:` flag, no `/ldd-architect` command, no trigger phrase in the dispatch table above), the agent MAY still enter architect-mode if the task description itself carries enough structural signals. This auto-dispatch exists so greenfield design tasks don't silently degrade into reactive "just start coding" just because the user didn't know the magic phrase.

**Auto-dispatch is the fourth and lowest-priority path.** Explicit user triggers always beat it (see "Precedence" below). The agent is making a judgment call on the user's behalf; the user must be able to see it and override it trivially.

### Mode signal scorer

Score the incoming task against the 6 signals. Sum the weights. **Score ≥ 4 → architect-mode.** Otherwise stay reactive.

| Signal | Weight | Direction | Detect via |
|---|---|---|---|
| Greenfield (no existing code to modify; "from scratch", "new service", "new module", "no existing codebase") | **+3** | architect | User ask explicitly names absence of prior code, or uses one of the literal phrases |
| ≥ 3 new components / services / subsystems to build | **+2** | architect | Task ask lists three or more concrete nouns that each need design (service, store, worker, CLI, UI, scheduler, …) |
| Cross-layer or cross-package scope (≥ 2 layers or packages touched) | **+2** | architect | Ask spans data + control layers, or names ≥ 2 packages / tiers (e.g. ingestion + storage + delivery; API + DB + background worker) |
| Ambiguous requirements — no clear constraints stated; needs invention | **+2** | architect | Ask lacks concrete constraints (latency, throughput, stack, timeline); user is implicitly delegating the shape of the answer |
| Explicit bug-fix / typo / rename / one-line change | **−5** | skip | Ask literally names `"fix"`, `"typo"`, `"rename"`, `"off-by-one"`, `"one-line"`, or points at a file:line |
| Single file, no layer boundary, known-solution domain | **−3** | skip | Ask mentions one file / one function / one known pattern to apply |

Tie-break at exactly 4: go architect. The threshold is the gate, not the average.

### Creativity inference (applied only if mode = architect)

Once architect-mode is chosen, pick the creativity level from the same task signals:

| Level | Triggering signals in the task | Notes |
|---|---|---|
| `conservative` | `"regulated"`, `"compliance"`, `"HIPAA"`, `"PCI"`, `"SOC2"`, `"migration of production"`, `"existing stack only"`, `"no new tech"`, `"on-call context"`, `"tight deadline on small team"`, `"6-week deadline"` + `"team of 2"` | Any one hit → `conservative` |
| `standard` (default) | none of the other levels' signals dominate | Picked when architect-mode fires but no conservative/inventive cue is present |
| `inventive` | `"research"`, `"novel paradigm"`, `"experiment"`, `"prototype a new"`, `"invent"`, `"no known solution fits"`, `"from scratch"` + domain without known patterns | Auto-dispatch **proposes** `inventive` but the existing per-task acknowledgment flow from `architect-mode` SKILL.md § Creativity levels still runs — without literal `acknowledged`, silently downgrade to `standard` |

Conservative beats inventive on a tie (risk-averse default).

### Precedence — highest wins

```
inline LDD[mode=…] / LDD[creativity=…] flags     ← highest
    ↓
/ldd-architect [creativity] command arg
    ↓
trigger-phrase match in the dispatch table above
    ↓
auto-dispatch score ≥ 4                          ← lowest
    ↓
bundle default (mode=reactive, creativity=standard)
```

If the user wrote `LDD[mode=reactive]:` on a task whose auto-score would be 6, the agent stays reactive. If the user wrote `LDD[mode=architect, creativity=conservative]:` the agent does NOT recompute — it uses exactly what was asked for.

### Mandatory echo

When auto-dispatch fires (mode = architect was chosen without an explicit trigger), the agent MUST echo the decision in the trace header. The user needs to see it and be able to override with one follow-up message. Format:

```
dispatched: auto (signals: greenfield=+3, cross-layer=+2)
```

Use the top-2 signals by absolute weight. When the score is below 4 and the agent consciously **did not** enter architect-mode, emit:

```
dispatched: auto (skip: explicit-bugfix=-5)
```

…only if the user could reasonably have expected architect-mode to fire (greenfield-sounding ask, or prior turn in session mentioned design). Otherwise the reactive default is silent.

### Worked example

> User: *"design a webhook replay service that stores every inbound webhook and lets partners replay arbitrary subsets; ~500/min, 6-8 week timeline, team of 2"*

Scorer run:

- Greenfield (`"design … service"`, no existing code referenced): **+3**
- ≥ 3 components (intake + store + replay + CLI): **+2**
- Cross-layer (ingestion + persistence + delivery): **+2**
- Ambiguous (no stack chosen, no retention named): **+2**
- Bug-fix / rename: **0**
- Single file: **0**
- **Total: +9 → architect.**

Creativity inference:

- Conservative signals (`"regulated"` / `"compliance"` / …): none
- Inventive signals (`"research"` / `"novel"` / …): none
- → `standard`

Trace header echoes:

```
dispatched: auto (signals: greenfield=+3, components≥3=+2)
mode: architect, creativity: standard
```

### Relation to trigger phrases

The dispatch table above (with phrases like "design X" / "greenfield") already fires architect-mode when a literal phrase matches — that path stays. Auto-dispatch is for the case where **no** literal phrase matched but the task shape still warrants architect-mode. In practice the two paths overlap heavily on classic greenfield asks; auto-dispatch catches the less-verbal users and the cross-layer asks that don't use design vocabulary.

## The "LDD:" buzzword

Users who want **guaranteed** LDD activation (no reliance on auto-triggering) can prefix their message with `LDD:`. When you see this prefix:

1. Load `loop-driven-engineering` as the orchestrating skill
2. Before any code, announce in one sentence which sub-skill you are reaching for and why
3. Apply that sub-skill's discipline literally, not "in spirit"
4. Report which rubric items you satisfied at the end of the task

Example:

> User: `LDD: the checkout test is failing and I need to ship in an hour`
> You: "Invoking `reproducibility-first` first to check whether this is a real gradient or noise. [runs check] Confirmed reproducible — invoking `root-cause-by-layer` next to diagnose at layer 4/5 before editing."

### Inline hyperparameter overrides: `LDD[k=N]:`

Users can override hyperparameters for a single task by writing flags in square brackets after `LDD` and before the colon:

```
LDD[k=3]: quick exploratory fix
LDD[k=10, reproduce=4]: deep dive on this flaky test
LDD[max-refinement=1]: one polish pass on this doc, then ship
LDD[no-reproduce]: I've already confirmed reproducibility — go straight to root-cause
```

Accepted flags (full reference in [`../../docs/ldd/hyperparameters.md`](../../docs/ldd/hyperparameters.md)):

- `k=<N>` / `kmax=<N>` — inner-loop `k_max` (range 1–20)
- `reproduce=<N>` — `reproducibility-first` Branch A rerun count (0–10; 0 is allowed but warned)
- `no-reproduce` — shortcut for `reproduce=0`
- `max-refinement=<N>` — refinement-loop hard cap (1–10)
- `mode=architect` — switch to architect mode for this task (invokes the 5-phase architect protocol from `../../skills/architect-mode/SKILL.md`)
- `mode=reactive` — force reactive mode, override any auto-trigger from architect-phrases in the task description
- `creativity=<conservative|standard|inventive>` — architect-mode sub-parameter selecting the **loss function** for this task (three discrete objectives, not a continuous freedom dial). Ignored if `mode≠architect`. `inventive` triggers a one-line user-acknowledgment flow before architect work begins. Cannot be set project-level (per-task only).

Multiple flags are comma-separated. Inline flags **beat everything else** (session `/ldd-set`, `.ldd/config.yaml`, bundle defaults). When an override applies, echo it in the trace block header so the user sees what budget is actually active:

```
│ Budget : k=3/K_MAX=3 (override: inline)
```

If the user expresses a budget in prose ("budget of 3 iterations", "give me only one refinement pass"), parse the intent and apply — echo in the trace as `(parsed from prose)`. When ambiguous, ask one clarifying question rather than guessing.

### Precedence

```
inline LDD[...] flags         ← highest priority
    ↓
/ldd-set session overrides
    ↓
.ldd/config.yaml in project
    ↓
bundle defaults               ← lowest
```

Use `/loss-driven-development:ldd-config` to see the full stack with per-key provenance. Only the three knobs above are exposed — requests to tune other parameters (learning rates, loss weights, skill-enable flags) are moving-target-loss risks and are refused per `docs/ldd/hyperparameters.md` §"What is NOT exposed (by design)".

## The LDD trace — mandatory visible output

For every non-trivial LDD task, emit a **visible trace block** inline in your reply so the user can see what discipline is running, how the loss is moving, and which skill fired. The user wants to audit this in real-time; the block is part of the deliverable, not an internal monologue.

**Emit the trace block AFTER EVERY ITERATION** (not per skill invocation — within one iteration multiple skills may fire; they share ONE block emitted at iteration close). Each emission is the *full current-state block* — header + all iterations so far + sparkline + chart + per-iteration mode+info lines. The user watches the loss descend in real time; they do not wait until the task closes to see progress.

Re-emit also at the end of each message if the task spans multiple messages, and at loop close (the final block carries the Close section with terminal status + layer fix + docs-sync verdict). Consecutive emissions grow monotonically: iteration k's emission differs from iteration k−1's by exactly one new iteration appended, the sparkline extended by one char, the chart extended by one column, and the trajectory-trend-arrow possibly flipped.

**Post-hoc reconstruction exception:** when the user hands you a COMPLETED task's iteration data (losses, skill names, actions already known) and asks you to render the trace, emit ONE final block with all iterations — the per-iteration rule does not apply because no real iterations are happening; repeating the growing block 3× in sequence would just be the same data printed three times. The `tests/fixtures/using-ldd-trace-visualization/` fixture exercises this exception (all three scenarios are post-hoc).

**Budget warning:** per-iteration emission multiplies trace-block token cost by the iteration count. For tight-context sessions, the Compression rule below (info-lines collapsed to skill-name-only) mitigates this — but the visualization channels (sparkline, chart, mode indicator, trend arrow) are never dropped, they are the audit surface.

### Trace block format

```
╭─ LDD trace ─────────────────────────────────────────╮
│ Task      : <one-line description of what the user asked>
│ Loop      : inner | refinement | outer
│ Loss-type : <see "Loss-types" below — primary is normalized [0,1]>
│ Budget    : k=<current>/K_MAX=<max>     (inner loop)
│
│ Iteration 1:
│   *Invoking <skill-name-1>*
│     <1-line result — branch chosen, layer named, verdict>
│   *Invoking <skill-name-2>*
│     <1-line result>
│   loss_1 = 0.000  (0/<max> violations)
│
│ Iteration 2 (if applicable):
│   ...
│   loss_2 = 0.125  (1/8 violations)
│   Δloss_1→2 = −0.125  (regression — revert before next edit)
│
│ Close:
│   Fix at layer: <4: structural-name, 5: conceptual-name>
│   Docs synced : yes | N/A | no (BLOCKED)
│   Terminal   : complete | partial | failed | aborted
╰─────────────────────────────────────────────────────╯
```

Keep it compact. The goal is **one screenful** the user can eyeball. If the trace grows beyond ~25 lines (many iterations), collapse older iterations to one summary line each.

### Loss-types — how to display the loss number

Three display modes, chosen per task by the nature of the measurement. Pick one, name it on the `Loss-type` header line, use it consistently for the whole trace block.

| Loss-type | When it applies | Display format | Example |
|---|---|---|---|
| **`normalized [0,1] (violations / rubric_max)`** | Binary rubric items (the default for most LDD skills): count violations, divide by rubric max | **Primary:** float in [0, 1] with 3 decimals. **Secondary:** raw `(N/max violations)` in parens | `loss_0 = 0.375  (3/8 violations)` |
| **`rate (already in [0,1])`** | Ratio signals already bounded: flake rate, passing-test fraction, coverage | Single float, secondary raw optional | `loss_0 = 0.333  (3/9 runs failed)` |
| **`absolute (continuous, no natural max)`** | Unbounded signals: latency / throughput / queue depth | Absolute value **with unit**, NO normalization attempt | `loss_0 = 45.0 ms  (p99 regression)` |

**Normalization rule (primary Loss-type):**

```
loss_normalized = violations / rubric_max
Δloss           = loss_{k-1} − loss_k    # positive = progress, negative = regression
```

Normalization makes Δloss **comparable across skills** (drift-detection with 6 rubric items vs. architect-mode with 10 items become apples-to-apples). The raw `(N/max)` in parens keeps it **actionable** — the user still sees exactly which items are still open.

**Anti-pattern:** never display a normalized float without the raw denominator in parens. "`loss_0 = 0.375`" alone implies a measurement precision that isn't there — it hides the fact that it's `3/8`. Show both; the normalized form is for comparison, the raw form is for action.

**Anti-pattern:** never compute a normalized float from a count that has no natural max (commit counts, latency, token usage). Those stay absolute with units — trying to normalize them invents a denominator and produces fake precision.

### Loss visualization — sparkline, mini chart, mode+info line, trend arrow

The numeric loss per iteration gives the user the value. To make the **trajectory** auditable at a glance AND the **work done per iteration** reviewable at a glance, the trace block carries four parallel channels. Mandatory thresholds:

| Channel | When mandatory | What it is |
|---|---|---|
| **Trajectory sparkline** | ≥ 2 iterations | Single-line Unicode-block series (`▁▂▃▄▅▆▇█`), one char per iteration, auto-scaled to `max(loss_observed)`. Zero values render as `·`. Sits on a `Trajectory:` line inside the trace block. |
| **Trend arrow** | ≥ 2 iterations | Single glyph at the end of the sparkline line: `↓` net descent, `↑` net regression, `→` flat. Reflects **first-vs-last** loss delta, NOT local or majority direction. |
| **Mini ASCII loss-curve chart** | ≥ 3 iterations | Multi-line chart: y-axis auto-scaled to smallest `0.25`-step multiple `≥ max(loss)`, values snap round-half-up to the nearest gridline; x-axis labels are the iteration labels (`i1`, `r2`, `o1`, …) with label first-char aligned to the data marker column. Data marker: `●`. |
| **Per-iteration mode + info line** | every iteration | The iteration-label line names the loop AND the mode (e.g. `(inner, reactive)`, `Phase p1 (architect, inventive)`, `(refine)`, `(outer)`) so the reader can tell at a glance which discipline was active. An indented continuation line carries `*<skill-name>*` + a one-line description of what concrete change the iteration produced — so the user can follow the skill's work step-by-step without scrolling elsewhere. |

The sparkline gives **micro-dynamics** (8-level resolution — separates a converged tail where losses differ by 0.05). The mini chart gives **macro-trajectory** (tail convergence collapses to the baseline row, which is visually honest — the loss IS flat below the snap step). The mode+info line gives **audit surface** — which mode, which skill, which action, per iteration. Consistency constraint: the sparkline's last bar, the chart's last marker, and the final iteration's `loss=` value must all reflect the same number.

**Mode-indicator grammar (per iteration label):**

- Inner loop, default discipline → `Iteration i<k> (inner, reactive)`
- Inner loop replaced by architect-mode → `Phase p<k> (architect, <creativity>)` where `<creativity>` is one of `standard` / `conservative` / `inventive`. The word `Phase` (not `Iteration`) signals the 5-phase protocol is running.
- Refine loop → `Iteration r<k> (refine)` — no mode/creativity (refine is always y-axis work on a deliverable)
- Outer loop → `Iteration o<k> (outer)` — no mode/creativity (outer is always θ-axis work on a skill/rubric)

A session that fires architect-mode in the inner layer and then hands off to reactive inner iterations renders both in the same trace: `Phase p1..p5` followed by `Iteration i1..i<k>`.

**Delta column (≥ 2 iterations):** every iteration after iter 1 appends `Δ <±value> <arrow>` to its loss line, where arrow is `↓` (progress), `↑` (regression), or `→` (plateau, `|Δ| < 0.0005`). This is the *per-step* arrow — distinct from the *end-to-end* trend arrow on the sparkline line.

**Rendering recipe (deterministic — copy verbatim):**

```
sparkline char  : ▁▂▃▄▅▆▇█ indexed by round(v / max(v) * 7); v == 0 → ·
trend arrow     : ↓ if (last − first) < −0.005 · ↑ if > +0.005 · → otherwise
chart y-axis    : ylim = ceil(max(v) / 0.25) * 0.25 ; rows at 0, 0.25, 0.50, … , ylim
chart data snap : row = floor(v / 0.25 + 0.5) * 0.25    (round-half-up)
chart x-axis    : "└─" + "─".join(labels) + "→  iter"   (label first-char = col start)
mode indicator  : (<loop>, <mode>[, <creativity>])  as specified above
info line       : "  *<skill-name>* → <one-line description of change produced>"
```

**Example — inner (reactive) → refine → outer, 6 iterations:**

```
│ Trajectory : █▆▃▂··   0.500 → 0.375 → 0.125 → 0.100 → 0.000 → 0.000  ↓
│
│ Loss curve (auto-scaled, linear):
│   0.50 ┤ ●  ●
│   0.25 ┤       ●
│   0.00 ┤          ●  ●  ●
│        └─i1─i2─i3─r1─r2─o1→  iter
│        Phase prefixes: i=inner · r=refine · o=outer
│
│ Iteration i1 (inner, reactive)    loss=0.500  (4/8)
│   *reproducibility-first* + *root-cause-by-layer* → guard empty list, filter None values
│ Iteration i2 (inner, reactive)    loss=0.375  (3/8)   Δ −0.125 ↓
│   *e2e-driven-iteration* → isinstance-based filter for non-numeric types
│ Iteration i3 (inner, reactive)    loss=0.125  (1/8)   Δ −0.250 ↓
│   *loss-backprop-lens* → sibling-signature generalization check 3/3 green
│ Iteration r1 (refine)             loss=0.100  (1/10)  Δ −0.025 ↓
│   *iterative-refinement* → docstring sections + ValueError on all-invalid
│ Iteration r2 (refine)             loss=0.000  (0/10)  Δ −0.100 ↓
│   *iterative-refinement* → runtime invariants via assert
│ Iteration o1 (outer)              loss=0.000  (0/8)   Δ ±0.000 →
│   *method-evolution* → skill rubric updated; 3 sibling tasks no longer regress
```

**Example — architect (inventive) hand-off into reactive inner:**

```
│ Phase p1 (architect, inventive)   loss=0.857  (6/7)
│   constraints: 7 requirements named; 2 uncertainties flagged (consistency bound, write throughput)
│ Phase p2 (architect, inventive)   loss=0.714  (5/7)   Δ −0.143 ↓
│   non-goals: 3 concrete scope boundaries (no global consensus, no strict serializability, …)
│ Phase p3 (architect, inventive)   loss=0.429  (3/7)   Δ −0.286 ↓
│   candidates: 3/3 on partial-order axis (MPO-CRDT, version-vector-with-dominance, lattice-merge)
│ Phase p4 (architect, inventive)   loss=0.143  (1/7)   Δ −0.286 ↓
│   scoring: MPO-CRDT wins 0.778; antithesis on write amplification survived with mitigation
│ Phase p5 (architect, inventive)   loss=0.000  (0/7)   Δ −0.143 ↓
│   deliverable: arch.md + scaffold + 6 failing tests + acknowledgment accepted @ 2026-04-21T12:14Z
│ Iteration i1 (inner, reactive)    loss=0.857  (6/7)
│   *e2e-driven-iteration* → first failing scaffold test now compiles (schema bound)
```

**Non-monotonic trajectories** — the end-to-end trend arrow is computed from `last − first`, so a run that regresses in the middle but recovers below the starting loss is still `↓`. Example: `0.667 → 0.833 → 0.167` ends at `−0.500` vs. start → `↓`, even though i1→i2 is a local `↑`. The per-step `Δ` arrows on each iteration line carry the local direction; the sparkline arrow carries the net direction. Don't conflate them.

**Compression rule (tight context):** if the trace would exceed one screenful, collapse the info-lines to a single word each (the skill name), but never drop the mode indicator or the sparkline — those are load-bearing for audit. The user wants to know *which discipline* fired at *which iteration* even when full prose doesn't fit.

**Loss-type-specific rendering:**

- `normalized [0,1]` or `rate` → chart and trend arrow use `[0,1]` directly.
- `absolute (with unit)` → sparkline auto-scales to `max_observed`; put the unit in the trajectory label (`Trajectory (ms):  ▇▅▁  …`). The mini chart is omitted for absolute loss (no natural [0,1] denominator — see the anti-pattern above); sparkline + mode+info line + trend arrow remain.

**Why no per-iteration magnitude bar** — an earlier draft of this spec included a 20-character `█`/`░` bar per iteration. It was removed in favor of the mode+info line because the information density is strictly worse: the bar re-encodes data already carried by the sparkline and chart, while the mode+info line carries *new* information (which skill fired, what concrete action it produced) the user cannot reconstruct from loss numbers alone.

**Architect-mode trace-block header:** the variant block (next subsection) uses phases instead of iterations. The header carries `mode: architect, creativity: <level>` and a `Dispatched:` line explaining how architect-mode was selected. The same four visualization channels apply, with `p1`..`p5` labels in place of `i1`/`r1`/`o1`.

### Architect-mode variant of the trace block

When `mode=architect` is active, the trace uses **phases** instead of iterations. The 5 phases are prescribed by the `architect-mode` skill. Example:

```
╭─ LDD trace (mode: architect, creativity: standard) ─╮
│ Task       : design a billing service for 50M users
│ Dispatched : auto (signals: greenfield=+3, cross-layer=+2)
│ Loop       : architect (5-phase protocol)
│ Budget     : phase <k>/5, no K_MAX (phases are sequential, not iterative)
│ Loss-fn    : L = rubric_violations  (standard baseline; λ=0)
│ Loss-type  : normalized [0,1] (violations / 10)
│
│ Phase 1 — Constraints  : 7 requirements named; 2 uncertainties flagged
│ Phase 2 — Non-goals    : 3 concrete non-goals
│ Phase 3 — Candidates   : 3/3 on load-bearing axis (monolith / CQRS / event-driven)
│ Phase 4 — Scoring      : CQRS wins, 0.778 (14/18); antithesis passed
│ Phase 5 — Deliverable  : arch.md + scaffold + 6 failing tests
│
│ Final loss : 0.000  (0/10 violations — no known gaps)
│ Hand-off   : next: default LDD inner loop, loss_0 (inner) = 0.857  (6/7 integration tests failing)
╰─────────────────────────────────────────────────────╯
```

Header shows `mode: architect` and `creativity: <level>` explicitly. The `Dispatched` line shows how architect-mode was selected — one of `inline-flag`, `command`, `trigger-phrase: "<phrase>"`, or `auto (signals: <top-2>)` — so the user can verify (and override) the decision in one follow-up message. The `Loss-fn` line names the objective being minimized; the `Loss-type` line names how the loss is displayed (which of the three display modes applies for this run).

For `creativity: conservative` the `Loss-fn` line reads: `L = rubric_violations + λ · novelty_penalty`. The rubric max becomes 11 (standard 10 + novelty-penalty #11); `Loss-type : normalized [0,1] (weighted violations / 11)`. Scoring cells in Phase 4 are displayed as normalized floats too: `A: 0.667 (20.0/30.0)` instead of raw `A: 20.0/30.0` alone.

For `creativity: inventive` the `Loss-fn` line reads: `L = rubric_violations_reduced + λ · prior_art_overlap_penalty`. The inventive rubric has 7 items (1–4 retained, 5–8 replaced by #I1–#I3) plus 9 and 10 always applied — so the denominator is 9; `Loss-type : normalized [0,1] (violations / 9)`.

Phase completion is reported as it happens (the block grows as the task progresses). On close, rubric score and hand-off line are added. If `inventive` was activated, also emit a line `Acknowledgment : accepted @ <timestamp>` or `downgraded to standard (not acknowledged)` so the user can verify what ran.

### When to emit

- **Always** on any invocation triggered by `LDD:` prefix or any trigger-phrase match (initial block carries header + budget, no iterations yet)
- **After every iteration** during live task execution — re-emit the full current-state block so the user watches the loss descend in real time (per v0.5.0 rule above). **v0.5.1 hardens this**: iteration-close without a trace block is a RED FLAG, see below.
- **Always** when closing a loop (final block with Close section: terminal status + layer fix + docs-sync verdict)
- **At the end of each message** if the task spans multiple messages (re-emit current state)
- **On request** when the user types the `/ldd-trace` command or asks for the current state
- **Not** for trivial one-shot replies (file read, single grep, typo fix) where no skill fires
- **Not** per-iteration when reconstructing a post-hoc trace from completed data the user supplied (one final block suffices — repeating the same iterations 3× adds no information)

### RED FLAGS — per-iteration trace emission is load-bearing

v0.5.1 adds explicit red flags because empirical observation (`scripts/ldd_trace/test_ldd_trace.py`, narralog post-mortem) showed the v0.5.0 mandate was regularly violated under time pressure:

| Thought | Reality |
|---------|---------|
| "The iteration succeeded, I'll show the trace at the end of the task" | No — every iteration ends with a block. The user needs to see *during* convergence, not post-mortem. |
| "Rendering the chart is a lot of ASCII; I'll describe the loss in prose" | No — use `scripts/ldd_trace append ...` and let the tool render. Manual prose descriptions of loss are a rubric violation at the method layer. |
| "I re-emitted the summary, that counts" | No — the trace block has four mandated channels (sparkline, mini chart, per-iteration info line, trend arrow). A summary table is not the trace. |
| "The loss didn't change this iteration, no point re-rendering" | No — a plateau IS a signal; the `Δ ±0.000 →` row lets the user see the plateau forming. |

An iteration close without a full trace block emission is treated as a `method-evolution` trigger at the next outer-loop checkpoint.

### Persisted trace at `.ldd/trace.log` — bidirectional

**Write.** When operating in a project directory, append a structured line to `.ldd/trace.log` at the project root on every iteration close. Create the directory if needed. Format:

```
2026-04-20T17:32:10Z  meta  task="..."  loops=inner,refine
2026-04-20T17:32:45Z  inner  k=0  baseline       loss_norm=1.000  raw=5/5   loss_type=rate
2026-04-20T17:33:22Z  inner  k=1  skill=reproducibility-first  action="..."  loss_norm=0.600  raw=3/5   Δloss_norm=-0.400
2026-04-20T17:34:10Z  inner  close  terminal=complete  layer="3: ..."  docs=synced
```

One line per iteration or close event. ISO-8601 UTC first. Space-separated key=value; values with spaces are double-quoted.

**Read.** At task start (before any new iteration), **if `.ldd/trace.log` exists in the project, read the last ~10 entries** via `python -m ldd_trace status --project <root>` or by tailing. This is how LDD recovers context across sessions — you cannot know what iteration `k` you are at, or what skills have already been tried, without reading prior state.

**Tool.** `scripts/ldd_trace` (v0.5.1) is the reference implementation. Subcommands:

```bash
python -m ldd_trace init --project . --task "one-line title" --loops inner,refine
python -m ldd_trace append --project . --loop inner --auto-k \
    --skill e2e-driven-iteration --action "what concretely changed" \
    --loss-norm 0.333 --raw 2/6 --loss-type normalized-rubric
python -m ldd_trace close  --project . --loop inner --terminal complete \
    --layer "3: <contract> · 5: <invariant>" --docs synced
python -m ldd_trace render --project .        # re-print the current block
python -m ldd_trace status --project .        # machine-readable last-k per loop
```

Each `append` / `close` call prints the FULL current trace block to stdout — so running the tool IS the per-iteration emission. The single-file module lives at `scripts/ldd_trace/` in the plugin repo; copy it into `$PROJECT_ROOT/.ldd/ldd_trace/` if the plugin isn't in PYTHONPATH.

**If `.ldd/` cannot be written** (read-only filesystem, no project root), skip the persistence but still emit the inline block.

### When NOT to emit the trace block

- Pure lookups ("what does this function do") — answer directly, no trace
- Rename / typo / one-line formatting edits — no skill fires, no trace
- The user explicitly says `--no-trace` or equivalent

The trace is a **loss-visibility tool**, not a template to apply mechanically. Empty or contentless traces ("Loop: unknown, k=?") are worse than no trace — they signal LDD is not actually active.

## Announcing skill invocation

Every time you invoke an LDD skill — whether auto-triggered or via `LDD:` — **say which skill you are invoking, in one sentence, before applying it**. This is non-negotiable; it lets the user verify which discipline is in effect and override you if you picked wrong.

Format: `*Invoking <skill-name>*: <one-line reason>.`

Example: `*Invoking root-cause-by-layer*: the symptom is a contract-violation `TypeError`; walking the 5-layer ladder before proposing a fix.`

## The three loops — which one is active

LDD distinguishes three optimization loops. Name which one you're in before iterating:

| Loop | You edit | When |
|---|---|---|
| **Inner** | Code | Ordinary bug / feature / refactor |
| **Refinement** (y-axis) | A deliverable (doc, diff, design) | "Good enough, not great" — polish |
| **Outer** (θ-axis) | A skill / rubric | Same rubric violation across ≥3 tasks |

If you cannot name which loop is active, stop and ask. Running the wrong loop wastes budget and can regress the artifact.

## Minimum compliance behaviors

Even without an explicit `LDD:` prefix, if the bundle is installed you are expected to:

1. **Never ship a symptom patch** (`try/except`, `hasattr`-shim, retry loop, `xfail`) without first walking `root-cause-by-layer` to layers 4–5.
2. **Never update code based on a single failed run** without invoking `reproducibility-first`.
3. **Never declare "done"** without running `docs-as-definition-of-done` against the touched files.
4. **Never give a non-trivial recommendation** without running `dialectical-reasoning` (thesis → antithesis → synthesis).
5. **Never exceed K_MAX=5 iterations** silently — escalate per `loop-driven-engineering` § Escalation.

## When LDD is not applicable

Skip the bundle for:
- Trivial edits (rename a variable, fix a typo, delete dead code you already understand)
- Pure lookups (what does this function do — read it and answer)
- Pure factual questions with no code change involved

The bundle is for **multi-step engineering under uncertainty**, not for every keystroke.

## Discovery order for a new session

At session start, if LDD is installed:
1. Read this skill's description.
2. Note that the other nine are available.
3. Apply the trigger-phrase table above to the user's first message.
4. If the first message doesn't clearly trigger any specific skill, proceed normally — LDD discipline activates when a trigger appears later.

## Compatibility with `superpowers`

If the `superpowers` plugin is also installed:
- `loop-driven-engineering` will dispatch to `superpowers:brainstorming` / `writing-plans` / `test-driven-development` / `verification-before-completion` / `requesting-code-review` at the moments noted in its dispatch table.
- `superpowers:systematic-debugging` overlaps with `root-cause-by-layer`: prefer `root-cause-by-layer` when you want the explicit 5-layer discipline, `systematic-debugging` for broader investigation framing.

## Signal that LDD is working

A session with LDD correctly applied shows:
- At least one `*Invoking <skill>*:` announcement per non-trivial task
- Commit messages that name layers / structural origins / Δloss when relevant
- No symptom-patch constructs shipped under pressure
- Doc updates in the same logical commit as behavior changes

If none of these appear in a long session, LDD is installed but dormant — re-check the trigger-phrase table, or ask the user to prefix `LDD:` explicitly.
