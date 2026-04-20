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
| "design X", "architect Y", "greenfield", "from scratch", "how should I structure", "propose an architecture", "decompose this problem", "what's the right shape for X" | `architect-mode` (opt-in — temporarily flips `mode=architect`; see skill for the 5-phase protocol and the hand-off back to reactive) |

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

**Emit ONE block per task** (not per skill invocation — that would clutter). Update it as the loop progresses; if the task spans multiple messages, re-emit the current state of the trace at the end of each message.

### Trace block format

```
╭─ LDD trace ─────────────────────────────────────────╮
│ Task   : <one-line description of what the user asked>
│ Loop   : inner | refinement | outer
│ Budget : k=<current>/K_MAX=<max>     (inner loop)
│                                                     
│ Iteration 1:                                        
│   *Invoking <skill-name-1>*                         
│     <1-line result — branch chosen, layer named, verdict>
│   *Invoking <skill-name-2>*                         
│     <1-line result>                                 
│   loss_1: <count of failing items / rubric rejections>
│                                                     
│ Iteration 2 (if applicable):                        
│   ...                                               
│   loss_2: <...>      Δloss_1→2: +X (progress) | 0 (no-op) | -X (regression)
│                                                     
│ Close:                                              
│   Fix at layer: <4: structural-name, 5: conceptual-name>
│   Docs synced : yes | N/A | no (BLOCKED)            
│   Terminal   : complete | partial | failed | aborted
╰─────────────────────────────────────────────────────╯
```

Keep it compact. The goal is **one screenful** the user can eyeball. If the trace grows beyond ~25 lines (many iterations), collapse older iterations to one summary line each.

### Architect-mode variant of the trace block

When `mode=architect` is active, the trace uses **phases** instead of iterations. The 5 phases are prescribed by the `architect-mode` skill. Example:

```
╭─ LDD trace (mode: architect, creativity: standard) ─╮
│ Task       : design a billing service for 50M users
│ Loop       : architect (5-phase protocol)
│ Budget     : phase <k>/5, no K_MAX (phases are sequential, not iterative)
│ Loss-fn    : L = rubric_violations  (standard baseline; λ=0)
│
│ Phase 1 — Constraints  : 7 requirements named; 2 uncertainties flagged
│ Phase 2 — Non-goals    : 3 concrete non-goals
│ Phase 3 — Candidates   : 3/3 on load-bearing axis (monolith / CQRS / event-driven)
│ Phase 4 — Scoring      : CQRS wins 14/18, dialectical antithesis passed
│ Phase 5 — Deliverable  : arch.md + scaffold + 6 failing tests
│
│ Rubric     : 10/10 (no known gaps) | 9/10 ("evolution paths" thin — noted)
│ Hand-off   : next: default LDD inner loop, loss_0 = 6 failing tests
╰─────────────────────────────────────────────────────╯
```

Header shows `mode: architect` and `creativity: <level>` explicitly. The `Loss-fn` line names the objective being minimized so the user can audit that the right loss function is in effect.

For `creativity: conservative` the `Loss-fn` line reads: `L = rubric_violations + λ · novelty_penalty`. For `creativity: inventive` it reads: `L = rubric_violations_reduced + λ · prior_art_overlap_penalty`.

Phase completion is reported as it happens (the block grows as the task progresses). On close, rubric score and hand-off line are added. If `inventive` was activated, also emit a line `Acknowledgment : accepted @ <timestamp>` or `downgraded to standard (not acknowledged)` so the user can verify what ran.

### When to emit

- **Always** on any invocation triggered by `LDD:` prefix or any trigger-phrase match
- **Always** when closing a loop (final block with terminal status)
- **On request** when the user types the `/ldd-trace` command or asks for the current state
- **Not** for trivial one-shot replies (file read, single grep, typo fix) where no skill fires

### Persisted trace at `.ldd/trace.log`

When you are operating in a project directory (as opposed to answering an abstract question), also append a compact single-line trace entry to `.ldd/trace.log` at the project root. Create the directory if needed. Format:

```
2026-04-20T17:32:10Z  inner  k=1  skill=reproducibility-first    verdict=deterministic    loss_0=1
2026-04-20T17:32:45Z  inner  k=1  skill=root-cause-by-layer      layer4=domain-boundary   loss_0=1
2026-04-20T17:33:22Z  inner  k=1  close                          terminal=complete        loss_1=0   Δloss=+1
```

One line per skill invocation or close event. ISO-8601 UTC timestamp first. Space-separated key=value pairs. The user can `tail -f .ldd/trace.log` in a second terminal to watch the loop in real time, or grep the file for post-hoc audit.

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
