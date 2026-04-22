---
name: ldd
description: Loss-Driven Development (LDD) — Gradient Descent for Agents. Use whenever the user prefixes a message with 'LDD:' or mentions LDD, loss, gradient, SGD on code, drift, refinement loop, outer loop, inner loop, method evolution, or 'apply LDD'. Dispatcher for 14 sub-skills (reproducibility-first, root-cause-by-layer, loss-backprop-lens, e2e-driven-iteration, loop-driven-engineering, iterative-refinement, method-evolution, drift-detection, dialectical-cot, dialectical-reasoning, docs-as-definition-of-done, define-metric, architect-mode, bootstrap-userspace) loaded on demand from references/. Also triggers on: failing test, bug, error, flaky, symptom patch, design, architect, greenfield, refactor, polish, declaring done, ready to merge, release candidate, drift check.
---

# Using LDD — the bundle entry-point for **Gradient Descent for Agents**

## The Metaphor

**The conductor before the orchestra.** Twelve instruments sit ready — violins ([`reproducibility-first`](references/reproducibility-first.md)), brass ([`root-cause-by-layer`](references/root-cause-by-layer.md)), percussion ([`loss-backprop-lens`](references/loss-backprop-lens.md)), a vocalist who sings counter-arguments ([`dialectical-reasoning`](references/dialectical-reasoning.md)), a second vocalist who sings the per-step dialectic for reasoning chains ([`dialectical-cot`](references/dialectical-cot.md)). The conductor plays none of them. She picks *which* and *when* each enters, watches the composition (the loss curve), and cues the next instrument from the score (the trace). `using-ldd` is the conductor. Every other skill is an instrument on one of the four axes of the gradient descent.

## Overview

Loss-Driven Development (LDD) is **[Gradient Descent for Agents](references/theory.md)** — a twelve-skill bundle that treats code changes, output revisions, skill edits, and reasoning steps as SGD steps on four distinct parameter spaces, and forbids overfitting to the current test. This entry-skill exists so you (the agent) know **when to reach for which LDD skill** without the user having to name each one by hand. It also owns the [thinking-levels auto-dispatch](references/thinking-levels.md) (v0.10.1), the step-size controller that picks rigor (L0…L4) per task before any gradient descends.

**Core principle:** if the user prefixes their message with `LDD:` or mentions any of the trigger phrases below, LDD discipline is explicitly requested. Match their intent to the right sub-skill and announce which one you are applying. The four-loop structure is:

- **Inner** (`θ` = code, `∂L/∂code`) — [`reproducibility-first`](references/reproducibility-first.md), [`root-cause-by-layer`](references/root-cause-by-layer.md), [`loss-backprop-lens`](references/loss-backprop-lens.md), [`e2e-driven-iteration`](references/e2e-driven-iteration.md), [`loop-driven-engineering`](references/loop-driven-engineering.md)
- **Refinement** (`y` = deliverable, `∂L/∂output`) — [`iterative-refinement`](references/iterative-refinement.md)
- **Outer** (`m` = method, `∂L/∂method`) — [`method-evolution`](references/method-evolution.md), [`drift-detection`](references/drift-detection.md)
- **CoT** (`t` = reasoning chain, `∂L/∂thought`) — [`dialectical-cot`](references/dialectical-cot.md)
- **Cross-cutting** — [`dialectical-reasoning`](references/dialectical-reasoning.md), [`docs-as-definition-of-done`](references/docs-as-definition-of-done.md), [`define-metric`](references/define-metric.md)
- **Opt-in** — [`architect-mode`](references/architect-mode.md) (5-phase greenfield discipline; reached via L3/L4 preset or explicit flag)

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

## Auto-dispatch: thinking-levels

Every non-trivial task enters the LDD bundle through a **level scorer** that picks one of five thinking levels (L0..L4) and emits a mandatory dispatch-header line. The user does not need to configure anything; the scorer runs on the task text. The user also does not need to know the scorer exists — an override is a single inline token away (see §Override syntax below).

**Default is L2, not L0.** Zero-config users get a deliberate baseline — one rank above reflexive pattern-matching — because **"lieber ein klein wenig schlau als zu dumm"** (asymmetric loss: a low-side miss ships a silent symptom-patch; a high-side miss wastes tokens). The scorer is designed to bias upward on boundaries.

### The 5 levels

| Level | Name | Preset — `k_max` / `reproduce_runs` / `mode` | Skill floor (minimum set invoked) |
|---|---|---|---|
| **L0** | reflex | 2 / 1 / reactive | `e2e-driven-iteration` |
| **L1** | diagnostic | 3 / 2 / reactive | + `reproducibility-first`, `root-cause-by-layer` |
| **L2** | deliberate *(default baseline)* | 5 / 2 / reactive | + `dialectical-reasoning`, `loss-backprop-lens`, `docs-as-definition-of-done` |
| **L3** | structural | 5 / 2 / **architect**/standard | + `architect-mode` (standard), `drift-detection`, `iterative-refinement` |
| **L4** | method | 8 / 3 / **architect**/inventive (ack-gated) | + `method-evolution`, `dialectical-cot`, `define-metric` |

**Skill floor is a floor, not a ceiling.** A task at L2 that benefits from `drift-detection` may still invoke it; a task at L3 is **not allowed to skip** `architect-mode`.

Architect-mode is reached through L3 / L4 — there is no longer a separate "auto-dispatch for architect-mode" threshold. Score the task; if it lands at L3 or L4, architect-mode is active by preset.

### The 9-signal scorer

Deterministic, pure function of the task text plus (optional) history of recently-touched files. No LLM call. Reference implementation: [`references/level_scorer.py`](references/level_scorer.py).

| Signal | Weight | Detect via |
|---|---|---|
| Greenfield (`"from scratch"`, `"new service"`, `"new module"`, `"no existing code"`, `"design a new"`) | **+3** | literal phrase match |
| ≥ 3 new components (≥ 2 matches of the components pattern, or ≥ 3 distinct `"new <noun>"` phrases) | **+2** | pattern / noun count |
| Cross-layer (`"across"`, `"between … and"`, `"integrate"`, `"wire"`, `"bridge"`, `"hook into"`) | **+2** | literal phrase match |
| Ambiguous requirements (`"somehow"`, `"after my last change"`, `"I'm not sure"`, `"when … doesn't"`) | **+2** | literal phrase match |
| Explicit bug-fix (`"fix"`, `"failing"`, `"broken"`, `"off-by-one"`, `"typo"`) | **−5** | literal phrase match |
| Single-file known-solution (exactly one file path AND (line ref OR fix verb OR `rename`/`move`/`delete`/`remove`)) | **−3** | path + bounded-work signal |
| **Layer-crossings** (≥ 2 named layer / subsystem terms from the LDD/AWP vocabulary — validator, critique, delegation loop, runner, manager, orchestration, etc.) | **+2** | vocabulary count |
| **Contract / R-rule hit** (`R\d+`, `"schema"`, `"contract"`, `"API surface"`, `"invariant"`, `"confidence (field\|threshold)"`, `"critique gate"`, `"deliverable_presence"`) | **+2** | literal phrase match |
| **Unknown-file-territory** (paths not seen in `.ldd/trace.log` history of the last 20 runs; when log is empty or absent, contributes 0) | **+1** | trace-log lookup |

The three bolded signals are new in the thinking-levels design; the other six are inherited from the pre-thinking-levels architect-mode scorer.

### Score-to-level buckets (Phase-1-tuned, upward-biased)

| Summed score | Level |
|---|---|
| `score ≤ −7` (explicit-bugfix AND single-file both fire, nothing else) | **L0** |
| `−6 ≤ score ≤ −2` | **L1** |
| `−1 ≤ score ≤ 3` | **L2** *(zero-signal baseline lands here)* |
| `4 ≤ score ≤ 7` | **L3** |
| `score ≥ 8` | **L4** |

**Creativity-clamp rule (L4 ↔ L3 interaction).** When the score buckets L4 BUT the creativity inferrer returns `standard`, the level clamps to L3. Reason: L4's preset mandates `creativity=inventive (ack-gated)`; running L4 with `standard` would mix two loss functions into one gradient (violates `references/architect-mode.md` §"Cannot switch mid-task"). The dispatch header MUST show `[clamped from L4 (creativity=standard)]` when this fires. The clamp is one-directional: it cannot promote L3 → L4 when creativity would be inventive.

### Creativity inference (applied at L3 / L4)

The creativity inferrer is unchanged from the pre-thinking-levels design; it now runs at L3 and L4 only.

| Level | Triggering signals | Notes |
|---|---|---|
| `conservative` | `"regulated"`, `"compliance"`, `"HIPAA"`, `"PCI"`, `"SOC2"`, `"migration of production"`, `"existing stack only"`, `"no new tech"`, `"on-call"`, `"tight deadline"`, `"team of N"` | Any one hit → `conservative` |
| `standard` (default) | none of the other levels' signals dominate | Picked when L3/L4 fires but no conservative/inventive cue is present |
| `inventive` | `"novel"`, `"research"`, `"prototype"`, `"no known pattern"`, `"invent"`, `"experimental"`, `"paradigm"` | Scorer **proposes** `inventive`; ack-gate must pass before the inventive loss function activates (see §Inventive ack below) |

Conservative beats inventive on a tie.

### Mandatory trace-header echo

On every non-trivial task, the agent MUST emit one of these lines in the trace header before doing any work:

```
Dispatched: auto-level L<n> (signals: <signal1>=<±N>, <signal2>=<±N>)
Dispatched: auto-level L<n> (signals: ...) [clamped from L4 (creativity=standard)]
Dispatched: user-explicit L<n> (scorer proposed L<m>)
Dispatched: user-bump L<n> (scorer proposed L<m>, bump: <fragment>)
Dispatched: user-override-down L<n> (scorer proposed L<m>). User accepts loss risk.
```

Signal pairs are the top-2 by absolute weight, stable tie-break by signal name. The agent can invoke the scorer via `python scripts/level_scorer.py "<task>"` (CLI) or `from level_scorer import score_task` (library).

When the scorer output lands at L3 or L4, the creativity is additionally echoed on a second line:

```
mode: architect, creativity: <standard|conservative|inventive>
```

### Worked example

> User: *"design a webhook replay service that stores every inbound webhook and lets partners replay arbitrary subsets; ~500/min, 6-8 week timeline, team of 2"*

Scorer run (deterministic):

- greenfield (`"design … service"`): **+3**
- components≥3 (intake + store + replay + CLI): **+2**
- cross-layer (`"… and …"` spans ingestion + persistence + delivery): **+2**
- ambiguous (no stack chosen, no retention named): **+2**
- layer-crossings (no LDD/AWP vocabulary hit): 0
- contract-rule-hit (no R-rule / schema named): 0
- others: 0
- **sum: +9 → L4 bucket.**

Creativity inference: no inventive cues, no conservative cues → `standard`.

Creativity-clamp rule fires: L4 + standard → **clamp to L3**.

Trace header:

```
Dispatched: auto-level L3 (signals: greenfield=+3, components>=3=+2) [clamped from L4 (creativity=standard)]
mode: architect, creativity: standard
```

### Relation to the trigger-phrase table above

The trigger-phrase table (§Trigger phrases) still fires specific skills when literal phrases match (e.g. `"failing test"` → `reproducibility-first`). Auto-dispatch is parallel to that, not in competition: the trigger-phrase table picks **which skills to invoke inside the level's skill floor**. The scorer picks **the level**. Both run; they refine each other.

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
LDD[level=L3]: explicit level L3, overrides the auto-level scorer
```

Accepted flags (full reference in [`references/hyperparameters.md`](references/hyperparameters.md)):

- `k=<N>` / `kmax=<N>` — inner-loop `k_max` (range 1–20)
- `reproduce=<N>` — `reproducibility-first` Branch A rerun count (0–10; 0 is allowed but warned)
- `no-reproduce` — shortcut for `reproduce=0`
- `max-refinement=<N>` — refinement-loop hard cap (1–10)
- `level=<L0..L4>` — explicit thinking-level, overrides the auto-level scorer. When the explicit level is below the scorer's proposal, the dispatch header emits `user-override-down` with the "User accepts loss risk" warning. `level` is **not** a persisted hyperparameter (cannot be set in `.ldd/config.yaml` or via `/ldd-set`); it is per-task only, parsed from the inline flag.
- `mode=architect` — switch to architect mode for this task (invokes the 5-phase architect protocol from `references/architect-mode.md`). Implied by `level=L3` and `level=L4`.
- `mode=reactive` — force reactive mode. When combined with `level=L3` or `level=L4`, the combination is rejected (the level preset is architect-mandated). Error echoed in the trace.
- `creativity=<conservative|standard|inventive>` — architect-mode sub-parameter selecting the **loss function** for this task (three discrete objectives, not a continuous freedom dial). Ignored if `mode≠architect`. `inventive` triggers the one-line acknowledgment flow (see §Inventive ack below). Cannot be set project-level (per-task only).

Multiple flags are comma-separated. Inline flags **beat everything else** (session `/ldd-set`, `.ldd/config.yaml`, bundle defaults).

### Relative bumps — when the user knows they want "more"

Shortcuts for "bump one or two levels above auto-dispatch". These are category 3 in the §Precedence below — lower than `LDD[level=Lx]`, higher than natural language.

```
LDD+:  <task>      → auto-level + 1
LDD++: <task>      → auto-level + 2
LDD=max: <task>    → L4 directly (equivalent to LDD[level=L4])
```

Clamp rule: the bumped level is capped at L4. Bumping beyond L4 is a no-op. A bump of `LDD+` on a task that already auto-dispatches to L4 emits a trace note `(bump ignored — already at L4)`.

### Natural-language bumps — for users who don't know the syntax

The user does not need to know any LDD syntax. These phrases in the task text are recognized as "be more careful than the scorer said":

| Phrase fragments (case-insensitive) | Effect |
|---|---|
| `"take your time"`, `"think hard"`, `"think carefully"`, `"careful"`, `"denk gründlich"`, `"denke gründlich"`, `"sorgfältig"`, `"durchdacht"` | **+1 level** |
| `"really think"`, `"think really hard"`, `"very careful"`, `"ultra-careful"`, `"maximum rigor"`, `"think thoroughly"`, `"sehr sorgfältig"` | **+2 levels** |
| `"full LDD"`, `"use everything"`, `"maximum deliberation"`, `"volle Kanne"` | **clamp to L4** |

All `+1` phrases **dedup semantically** — `"take your time and think hard"` contributes +1 total, not +2. Both express the same "be careful" intent. A +2 bump requires an explicit strong phrase from the second row.

The natural-language path is the lowest-priority override (category 4); any explicit LDD-syntax flag above beats it.

### Dispatch-header echo for overrides

When ANY override fires (explicit flag, relative bump, or natural-language bump), the dispatch header surfaces it so the user can see what actually ran:

```
Dispatched: user-explicit L3 (scorer proposed L2)
Dispatched: user-bump L2 (scorer proposed L0, bump: LDD++)
Dispatched: user-bump L2 (scorer proposed L0, bump: "take your time")
Dispatched: user-bump L4 (scorer proposed L0, bump: LDD=max)
Dispatched: user-override-down L0 (scorer proposed L3). User accepts loss risk.
```

If the user expresses a budget in prose ("budget of 3 iterations", "give me only one refinement pass"), parse the intent and apply — echo in the trace as `(parsed from prose)`. When ambiguous, ask one clarifying question rather than guessing.

### Inventive ack — user consent to switch the loss function

`creativity=inventive` uses a **different loss function** than `standard` or `conservative` (see `references/architect-mode.md` §"The neural-code-network framing"). The agent is **never** allowed to activate inventive on its own — it can only propose, and the user consents.

Three paths to consent, in order of precedence:

1. **Explicit inline flag.** `LDD[creativity=inventive]:` or the `/ldd-architect inventive` command. Consent is carried in the flag; no further ack needed.
2. **Literal ack token.** When the scorer proposes inventive (via cues like `"novel"`, `"prototype"`, `"research"`), the agent asks the user for explicit consent. The canonical ack is the word `acknowledged`. But any of these natural-language affirmatives also count (bilingual):

   | Positive (→ inventive activates) | Negative (→ silent downgrade to `standard`) |
   |---|---|
   | `"acknowledged"`, `"ack"`, `"yes"`, `"ja"`, `"go"`, `"go ahead"`, `"proceed"`, `"los"`, `"okay mach"`, `"okay machen"`, `"passt"`, `"mach"` | `"no"`, `"nein"`, `"stop"`, `"cancel"`, `"abbruch"`, `"halt"`, or silence |

   Ambiguous replies (`"hmm"`, `"maybe"`, `"let me think"`) do NOT activate inventive — they require the literal `acknowledged` or a positive token.

3. **Implicit ack from the original task prompt.** When the user's initial message already contains **≥ 2 inventive cues** (`"novel"`, `"research"`, `"prototype"`, `"no known pattern"`, `"invent"`, `"experimental"`, `"paradigm"`) AND is **≥ 100 characters long**, the agent treats the prompt itself as consent — the user has already verbalized inventive intent in a substantive task description. The dispatch header MUST surface this explicitly:

   ```
   mode: architect, creativity: inventive (implicit ack from ≥2 inventive cues in prompt)
   ```

   If the prompt is shorter than 100 characters or contains only 1 inventive cue, fall back to path 2 (explicit ack).

Neither path 2 nor path 3 allows the AGENT to select inventive on its own. Both still require user-originated consent — path 2 via a reply, path 3 via the task text itself. The moving-target-loss protection (the user is the only authority that can set the loss function) is preserved.

### Precedence — level selection (highest wins)

```
1. LDD[level=Lx]:               explicit level              ← highest
2. LDD=max: / "volle Kanne"     literal max (→ L4)
3. LDD++: / LDD+:               relative bump
4. Natural-language phrases     "take your time" etc.
5. Auto-scorer output           9-signal scorer bucket       ← lowest
```

`LDD[level=L0]:` on a task the scorer would bucket L3 is an explicit downward override — honored, but `user-override-down` warning is emitted. No silent demotions.

### Precedence — other hyperparameters (k, reproduce, max-refinement, mode, creativity)

```
inline LDD[...] flags         ← highest priority
    ↓
/ldd-set session overrides
    ↓
.ldd/config.yaml in project
    ↓
bundle defaults               ← lowest
```

Use `/loss-driven-development:ldd-config` to see the full stack with per-key provenance. Only the knobs listed in `references/hyperparameters.md` are exposed — `level` itself is a DERIVED value (the auto-scorer's output or an explicit override), not a persisted hyperparameter. Requests to tune other parameters (learning rates, loss weights, skill-enable flags) are moving-target-loss risks and are refused per `references/hyperparameters.md` §"What is NOT exposed (by design)".

## The LDD trace — mandatory visible output

For every non-trivial LDD task, emit a **visible trace block** inline in your reply so the user can see what discipline is running, how the loss is moving, and which skill fired. The user wants to audit this in real-time; the block is part of the deliverable, not an internal monologue.

**Emit the trace block AFTER EVERY ITERATION** (not per skill invocation — within one iteration multiple skills may fire; they share ONE block emitted at iteration close). Each emission is the *full current-state block* — header + all iterations so far + sparkline + chart + per-iteration mode+info lines. The user watches the loss descend in real time; they do not wait until the task closes to see progress.

Re-emit also at the end of each message if the task spans multiple messages, and at loop close (the final block carries the Close section with terminal status + layer fix + docs-sync verdict). Consecutive emissions grow monotonically: iteration k's emission differs from iteration k−1's by exactly one new iteration appended, the sparkline extended by one char, the chart extended by one column, and the trajectory-trend-arrow possibly flipped.

**Post-hoc reconstruction exception:** when the user hands you a COMPLETED task's iteration data (losses, skill names, actions already known) and asks you to render the trace, emit ONE final block with all iterations — the per-iteration rule does not apply because no real iterations are happening; repeating the growing block 3× in sequence would just be the same data printed three times. The `tests/fixtures/using-ldd-trace-visualization/` fixture exercises this exception (all three scenarios are post-hoc).

**Budget warning:** per-iteration emission multiplies trace-block token cost by the iteration count. For tight-context sessions, the Compression rule below (info-lines collapsed to skill-name-only) mitigates this — but the visualization channels (sparkline, chart, mode indicator, trend arrow) are never dropped, they are the audit surface.

### Trace block format

```
╭─ LDD trace ─────────────────────────────────────────╮
│ Store     : <tier scope — see bootstrap-userspace>
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
│ Store      : local (.ldd/trace.log)
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

**Tool.** `scripts/ldd_trace` is the reference implementation. Subcommands:

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

**Permanent statusline on Claude Code.** When the host is Claude Code, also dispatch `host-statusline` (CLI-only, no-op on Web) once per session, in parallel with `bootstrap-userspace`. That skill auto-installs a bottom-of-screen statusline that reads `.ldd/trace.log` (or ⟪LDD-TRACE-v1⟫ markers from the session JSONL) and renders a one-line LDD monitor — task · loop · iteration · loss · Unicode sparkline · trend. Install is project-local (`.ldd/statusline.sh` + a single `statusLine` key in `.claude/settings.local.json`), idempotent, merge-safe, silent. The user never has to configure it. The `│ Store :` line in the trace block gains a `statusline: installed` suffix so they see it went live.

**If `.ldd/` cannot be written** (read-only filesystem, no project root, sandboxed chat host like Claude Desktop without MCP filesystem or ChatGPT without an Actions server) — delegate to `bootstrap-userspace`. That skill inspects the host's tool inventory and picks the most durable alternative tier silently, without prompting the user:

- **Tier 0 — Filesystem** — this bidirectional path (the default); `bootstrap-userspace` is a no-op.
- **Tier 1 — Artifact / Canvas** — maintain a persistent document titled `ldd-trace.log` inside the conversation.
- **Tier 2 — Conversation-History** — emit `⟪LDD-TRACE-v1⟫`-prefixed trace lines in the visible reply; the host's chat retention IS the persistence. A CLI session can later promote these lines to Tier 0 via `python -m ldd_trace ingest < pasted.txt`.
- **Tier 3 — Memory-pointer** — personal-memory API holds a one-line pointer to where the trace actually lives (Tier 1 or 2). Never trace data directly.
- **Tier 4 — Inline-only** — degraded fallback; trace is ephemeral, lost at session end.

The chosen tier is always disclosed in the trace block's header via a `│ Store  : <scope>` line (see format below). Full protocol: [`references/bootstrap-userspace.md`](references/bootstrap-userspace.md).

### When NOT to emit the trace block

- Pure lookups ("what does this function do") — answer directly, no trace
- Rename / typo / one-line formatting edits — no skill fires, no trace
- The user explicitly says `--no-trace` or equivalent

The trace is a **loss-visibility tool**, not a template to apply mechanically. Empty or contentless traces ("Loop: unknown, k=?") are worse than no trace — they signal LDD is not actually active.

## Announcing skill invocation

Every time you invoke an LDD skill — whether auto-triggered or via `LDD:` — **say which skill you are invoking, in one sentence, before applying it**. This is non-negotiable; it lets the user verify which discipline is in effect and override you if you picked wrong.

Format: `*Invoking <skill-name>*: <one-line reason>.`

Example: `*Invoking root-cause-by-layer*: the symptom is a contract-violation `TypeError`; walking the 5-layer ladder before proposing a fix.`

## The four loops — which one is active

LDD distinguishes **four optimization loops** across four parameter spaces (see [Gradient Descent for Agents](references/theory.md)). Name which one you're in before iterating:

| Loop | Parameter | You edit | When |
|---|---|---|---|
| **Inner** | `θ` = code | Code | Ordinary bug / feature / refactor |
| **Refinement** | `y` = deliverable | A deliverable (doc, diff, design) | "Good enough, not great" — polish |
| **Outer** | `m` = method | A skill / rubric | Same rubric violation across ≥3 tasks |
| **CoT** | `t` = reasoning chain | Reasoning steps themselves | Verifiable multi-step reasoning (math / code / logic / proofs) |

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
