---
name: dialectical-reasoning
description: Use when making any non-trivial recommendation, analysis, plan, design decision, code-review note, or architectural trade-off — before presenting to the user or acting. Forces a thesis / antithesis / synthesis pass so first-pass conclusions cannot ship without surviving their strongest counter-case.
---

# Dialectical-Reasoning

## Overview

First-pass reasoning tends to overfit to the framing of the prompt. A proposal that has not survived its own strongest counter-case is a **symptom patch at the reasoning layer** — it will look right and fail in production, code review, or the next conversation.

**Core principle:** Every non-trivial recommendation must go through thesis → antithesis → synthesis **before** it leaves your mouth. The synthesis — not the thesis — is the admissible output.

**Violating the letter of the dialectic is violating the spirit.** "I already know the answer, I'll skip the antithesis" is the standard skip; it is forbidden. The discipline is the **externalization**, not the internalization.

## When to Use

Apply before presenting or acting on any of:

- A recommendation (ship / don't ship, choose X over Y, use library Z)
- A debugging hypothesis ("the bug is in X because Y")
- An architectural trade-off (split the service, add a cache, rewrite in language X)
- A code-review note arguing for a change
- A plan for multi-step work
- A "yes this is fine" sign-off on someone else's proposal

## When Not to Use

- Trivial mechanical tasks (rename a variable, run a test, read a file)
- Pure lookups (what does this function do? read the code)
- Answering a direct factual question where there is no judgment call

The rule: **if a second competent reviewer could disagree with your output, it needs an antithesis first.**

## The Three Moves

### 1. Thesis — state the proposal concretely

- What exactly is claimed?
- What will change?
- What is expected to hold afterwards?
- What is the load-bearing assumption?

State it in one paragraph, in its strongest form. Steel-man it, don't strawman.

### 2. Antithesis — attack it as hard as possible

Switch roles. You are now the hostile reviewer, the future maintainer, the production incident that happens six months in. **Your job is to break the thesis, not to defend it.**

At minimum, attack:

- **Hidden assumptions.** What is the thesis quietly assuming (about scale, about callers, about invariants, about the environment)?
- **Edge cases.** What input / state / timing / concurrency breaks it?
- **Contracts and invariants.** Which written or unwritten contract does it strain?
- **Second-order effects.** What does it make harder later? What does it couple?
- **Alternative framings.** Is the problem itself framed correctly, or is the thesis solving the wrong problem?
- **Asymmetric risks.** What's the cost if you're wrong? Reversible or not?
- **Who disagrees?** Name a reasonable person who would reject this, and why.

A weak antithesis ("I guess it could be slightly slower") is a failed antithesis — the thesis does not count as surviving.

### 3. Synthesis — strictly stronger than the thesis

Reconcile. The synthesis must be one of:

- **More correct** (a sharper version the antithesis forced you to)
- **More narrowly scoped** (the thesis was right for the subset the antithesis didn't break)
- **More honestly hedged** (the thesis is right under stated conditions; those conditions are explicit)
- **Replaced** (the antithesis won; the thesis is discarded)

"The thesis was right" is **only** a valid synthesis after a real antithesis — not as a replacement for one.

## Red Flags — STOP, you skipped the dialectic

These phrases, in your own draft or thinking, mean you stopped at thesis:

- "This is obviously the right call because…"
- "I think we should just…"
- "The clean solution is to…"
- "It's a simple matter of…"
- "Everyone agrees that…" (have you asked a dissenter?)
- "This is a no-brainer"
- "The tradeoff is clearly worth it" (without naming the tradeoff)
- Any recommendation without an explicit "but" / "however" / "on the other hand"
- Any plan with only happy-path assumptions named

When one fires: restart at the antithesis. Find the strongest counter-case before continuing.

## Antithesis Checklist

A good antithesis hits at least 3 of these:

- [ ] Names a load-bearing assumption and questions it
- [ ] Surfaces at least one edge case / failure mode
- [ ] Identifies a contract or invariant under strain
- [ ] Points to a second-order cost (coupling, future work, blast radius)
- [ ] Proposes an alternative framing of the problem
- [ ] Explicitly states: "A reasonable person would reject this because…"

If you can check none of these, your antithesis is cosmetic. Try again.

## The Quantitative Dialectic — gradient via dialectic (v0.7.0)

The three moves above are **qualitative**. v0.7.0 adds a **numeric protocol the agent walks in-head** during the synthesis step, turning dialectical reasoning from "I considered the alternatives" into "I computed and rejected alternative A because E[Δloss | A] > E[Δloss | B] by 0.44."

This is the point where "gradient via dialectic" is actual math — but the math is done by the agent using skill-prescribed reasoning, not by Python. LDD is a skill; the discipline lives here, not in the tool.

### When to apply the numeric layer

Apply when **all** of:

- `project_memory.json` exists (≥ 1 closed task in `.ldd/trace.log`)
- The thesis names a concrete skill / decision path with historical data
- The stakes are non-trivial (architectural, cross-layer, or high-blast-radius)

Skip when: project has no memory yet, or thesis is fully novel (no historical stats), or change is trivial.

### The 5-step numeric protocol

**Step 1 — Thesis carries predicted Δloss**

State the proposal AND its predicted Δloss, drawn from memory:

```
Thesis: apply skill X at position Y
  predicted_Δloss   = memory.skill_effectiveness[X].delta_mean_abs    = <number>
  confidence_factor = clamp(log(1+n)/log(1+10), 0, 1)                 = <number>
  source            = lifetime | last_30_days
```

Confidence scales with sample size. Below n=3, confidence → 0, predicted_Δloss becomes advisory only.

**Step 2 — Each antithesis primer carries {probability, impact}**

Instead of narrative counter-cases, each primer maps to numbers:

```
Primer [skill_failure_mode]:
  prob_applies = memory.skill[X].regression_rate + memory.skill[X].plateau_rate
  impact       = reg_rate × Δ_reg + pla_rate × 0                      # no-progress contributes 0

Primer [plateau_pattern, current streak = k]:
  prob_applies = 1.0 (we ARE in the plateau)
  impact_if_stay_same_layer  = ≈ 0  (continued plateau)
  impact_if_pivot_to_resolver = memory.skill[resolver].delta_mean_abs

Primer [terminal_analysis]:
  prob_applies = project.non_complete_rate
  impact       = Σ terminal_rate × typical_Δ_for_that_terminal
```

**Step 3 — Synthesis computes expected Δloss via Bayesian combination**

```
E[Δloss | thesis] = Σ_primer (prob_primer × impact_primer)
                  + (1 − Σ prob_primer) × thesis.predicted_Δloss
```

If alternatives exist (e.g., plateau primer suggests `root-cause-by-layer`), compute `E[Δloss | alternative]` the same way.

**Step 4 — Decision rule**

Commit the thesis when:

- `E[Δloss | thesis] < 0` (progress expected), AND
- No alternative dominates by more than 0.1 in expected Δloss (otherwise pivot)

Reject the thesis when:

- `E[Δloss | thesis] ≥ 0` (regression or plateau expected), OR
- An alternative dominates by > 0.1 (strong evidence for pivot)

Ambiguous (within 0.1): escalate to the user — the numbers don't decide, and pretending they do is false precision.

**Step 5 — Calibration at iteration close**

After running the iteration and measuring actual Δloss:

```
actual_Δloss      = observed_loss_post − observed_loss_pre
prediction_error  = predicted_Δloss − actual_Δloss
```

Log both via `python -m ldd_trace append ... --predicted-delta <value>`. Over N iterations the aggregator exposes `mean(|prediction_error|)` as calibration accuracy — if consistently poor (> 0.15), the agent's internal priors are mis-calibrated and the outer loop fires (`method-evolution`).

### Worked example

Scenario: in-flight task, streak=2 plateau, agent considering `retry-variant`.

```
[Memory context, project_memory.json]
  retry-variant        : delta_mean_abs=+0.025, reg=25%, pla=75%, n=4
  root-cause-by-layer  : delta_mean_abs=−0.42,  reg=0%,  pla=0%,  n=5
  plateau_pattern[≥2]  : resolvers=[root-cause-by-layer×3], n=3

[Step 1] Thesis: apply retry-variant
  predicted_Δloss   = +0.025                    ← EXPECTED to regress
  confidence_factor = log(5)/log(11) = 0.67

[Step 2] Primers:
  Primer 1 (skill_failure_mode, retry-variant):
    prob = 0.25 + 0.75 = 1.00                   ← always hits failure mode here
    impact = 0.25 × (+0.05) + 0.75 × 0 = +0.0125
  Primer 2 (plateau_pattern, resolver != retry-variant):
    prob = 1.00
    impact_if_stay = ≈ 0                         ← continued plateau
    impact_if_pivot = −0.42                      ← resolver's historical Δ

[Step 3] Synthesis:
  E[Δloss | thesis=retry-variant]        ≈ +0.025 (primer 1 confirms regression prior)
  E[Δloss | alternative=root-cause]      ≈ −0.42
  Δ_between                              = 0.445  (alternative dominates by > 0.1)

[Step 4] DECISION: REJECT thesis. Commit root-cause-by-layer.
  predicted_Δloss_this_iteration = −0.42

[Step 5] Post-iteration (after running):
  observed_Δloss = −0.35
  prediction_error = −0.42 − (−0.35) = −0.07     ← slight over-prediction, within ±0.15 band
  Log: ldd_trace append ... --predicted-delta -0.42 --loss-norm <post>
```

### Hard rules

1. **No fabricated numbers.** If `n < 3` for a skill, state `confidence = low, predicted_Δloss = unknown` — don't invent from prose.
2. **Prediction is advisory, not gate.** Agent may override with reasoning, but must state the exception explicitly ("this case is different because …") and log it.
3. **Calibration is mandatory.** Commit without `--predicted-delta` → v0.7.0 quantitative dialectic was not applied; log states so.
4. **No cross-project numbers.** Memory is per-project; calibration is per-project. Global averages would bias L via signal-mixing.
5. **Within-ambiguity-band → user decision.** If `|E[thesis] − E[best_alternative]| < 0.1`, the numbers don't decide. Escalate.

### Why this doesn't bias L(θ)

The numbers inform the **search direction**, not the **objective function**. The rubric still counts violations; the actual Δloss is measured post-hoc; what's different is that the agent's *proposed* direction is now guided by explicit, auditable priors rather than implicit gut-feel. Priors existed before — v0.7.0 only surfaces them, quantifies them, and calibrates them over time.

If calibration degrades (prediction error widens), v0.7.0 tells the agent explicitly: "your priors are drifting; method-evolution." That's outer-loop, not loss-modification.

## Memory-informed antithesis generation (v0.6.0)

SGD framing: dialectical reasoning is **local Hessian probing** — it discovers orthogonal directions in θ-space where the proposed gradient-step reacts non-monotonically. When a project has accumulated `.ldd/trace.log` and `.ldd/project_memory.json` (per `using-ldd` § "Persisted trace"), that memory provides **1st-moment statistical evidence** (past failure modes, plateau patterns, terminal distributions) that can sharpen antithesis generation — without biasing the loss function itself.

### How to invoke

Before running the three moves, check if project memory has signal for the thesis:

```bash
python -m ldd_trace prime-antithesis \
    --project . \
    --thesis "one-line description of the planned action" \
    [--files a.py,b.py,c.py]
```

The tool emits **structured primers** — each phrased as a *question the antithesis must answer*, not a prescription. Primers come from:

| Source | Triggers when |
|---|---|
| `skill_failure_mode` | Thesis names a skill whose historical regression + plateau rate is ≥ 30% |
| `plateau_pattern` | Current in-flight task has ≥ 2 consecutive plateau iterations |
| `similar_task` | File-overlap with a past task that terminated non-complete |
| `terminal_analysis` | Project-wide non-complete rate ≥ 15% (n ≥ 5 tasks) |

If no primers fire, run the standard dialectical pass with generic counter-cases. The tool never fabricates material.

### Agent contract when primers are present

1. **Each primer becomes a required antithesis point** — address it explicitly in the antithesis section; don't silently ignore it.
2. **Generate ≥ 1 additional antithesis NOT sourced from the primers** — guards against memory-groupthink (the agent only reasoning about past failure modes and missing novel ones).
3. **Synthesis MUST reconcile or reject each primer** — acknowledging a primer-pointed risk without addressing it is a Red Flag.
4. **Emit the trace via `ldd_trace append` at iteration close** — completing the loop: memory fed in, memory fed out.

### Why this preserves the loss-invariant

The primers are **evidence**, not weights. They do not alter L(θ). Specifically:

- Memory can flag "skill X has 40% regression rate" — but it's the dialectical synthesis that decides whether this task is the exception. The final action is chosen via reasoning, not by statistical auto-apply.
- The `check` CLI reports warnings; the `prime-antithesis` CLI reports material. Neither is enforcement.
- Rubric items are unchanged; rubric scoring is unchanged; the only thing changed is *which counter-cases the agent proactively considers*.

### When memory disagrees with dialectical

| `check` / primer | Dialectical reasons | Synthesis action |
|---|---|---|
| Statistical green | Reasoning green | High confidence commit |
| Statistical green | Reasoning identifies an unaddressed contract | Defer; fix the contract first |
| Statistical red (regression warning) | Reasoning can defend this-case-is-different | Commit with narrow scope + explicit hedge; flag for post-review |
| Statistical red | Reasoning red | Do NOT commit; pivot to alternative |

Both sources signal green = posterior very high confidence. Memory-only or reasoning-only green = medium confidence (posterior Bayesian update). Both red = highest-confidence rejection of thesis.

## Presenting to the User

Show the **synthesis** as the recommendation. Surface the antithesis only when the tension is **load-bearing** — when the user needs to see the rejected alternative to judge the trade-off themselves.

Do not perform the dialectic for its own sake. The output is a sharper decision, not a longer message. A two-sentence synthesis that survived a real antithesis beats a four-paragraph analysis that didn't.

**However:** when the stakes are high or the user is weighing options, showing the structured thesis/antithesis/synthesis makes the reasoning auditable. Know your audience.

## Common Rationalizations

| Excuse | Reality |
|---|---|
| "I already considered the counter-arguments, just didn't write them" | Internalization ≠ discipline. The externalization is the check. Write it. |
| "It's obvious, don't patronize the user" | "Obvious" is the canonical cover for skipping the antithesis. Write the counter anyway. |
| "Antithesis for every trivial decision slows me down" | Yes — that's why the "when not to use" section exists. For non-trivial, skipping is cheaper in your time but more expensive in the user's. |
| "The user wants the answer, not a debate" | The user wants the **right** answer. A sharper synthesis is shorter, not longer. |
| "Devil's advocate feels performative" | Performative antithesis (weak attacks) IS the failure mode. Attack hard. A real antithesis changes the synthesis. |
| "I can hold both sides in my head" | Maybe. But you can't prove you did unless you write them. Reviewers cannot audit a private dialectic. |

## The failure mode this skill prevents

Without an enforced dialectical shape, a response on a high-stakes design question (retries for a flaky API, dedup of user records, service split) tends to come out mono-directional — substantive but one-sided, missing the explicit "thesis / but / therefore" auditability. The hidden assumption goes unchallenged; the reviewer has no way to verify both sides were actually considered.

With this skill: the reply labels thesis, attacks ≥ 3 vectors in the antithesis (hidden assumptions, edge cases, contracts under strain, irreversibility, asymmetric risk), and produces a synthesis that is *strictly stronger* than the thesis — narrower scope, sharper conditions, or reframed problem.

Scenario + rubric + measured behavior: `tests/fixtures/dialectical-reasoning/`.

## Related

- **`root-cause-by-layer`** — the antithesis of a debugging hypothesis is "which layer did you skip?"
- **`loss-backprop-lens`** — the antithesis of a proposed fix is "does this generalize, or only pass the current test?"
- **`docs-as-definition-of-done`** — the antithesis of "done" is "what doc statement is now false?"
