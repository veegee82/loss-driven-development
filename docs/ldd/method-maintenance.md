# Method maintenance — when the skill itself is the bug

Load this when the user says: "the skill isn't catching this", "this pattern keeps happening", "maybe our approach is wrong", "three tickets with the same root cause", "should we change the rubric".

## Skill

Primary: [`method-evolution`](../../skills/method-evolution/SKILL.md) — the **outer loop** (`∂L/∂method`), SGD on `m = skills / rubrics / prompts`. One of the [four gradients](../theory.md) LDD optimizes across; this one is triggered when the same rubric violation recurs across 3+ distinct tasks (inner loops won't help — the bug is in the method, not in any single task). Secondary: [`drift-detection`](../../skills/drift-detection/SKILL.md) (upstream check for whether the method itself has drifted). The outer loop is also the channel that handles violations of the reasoning-chain axis — if [`dialectical-cot`](../../skills/dialectical-cot/SKILL.md)'s chain-level calibration emits `drift_warning: true`, `method-evolution` is the corrective channel (adjust thresholds, regenerate primers, retune the step-evaluator skill).

## When it's the right loop — all of

- The same rubric violation / symptom-patch / escalation has happened in **≥3 distinct tasks across different domains**
- The method's current Red Flags / rules don't cover this case
- Patching each task individually won't prevent the next occurrence
- You have a **task suite** (≥5 tasks, varied) to measure `Δloss_method`

Missing any → wrong loop. Edit tasks individually via the inner loop; wait for the pattern to accumulate evidence.

## The evolution step

Rigid 4-step protocol. Treat as an experiment, not a refactor.

### 1. Name the pattern (greppable)

> In tasks T1 (domain A), T2 (domain B), T3 (domain C), the agent bypassed rubric item R via the rationalization phrase P. The skill's Red Flags list does not currently cover P.

Specific enough that a reader can grep for the phrase in future runs.

### 2. Propose ONE change

Not a rewrite. One thing:

- Add a Red Flag phrase to the skill's list
- Add a Rationalization → Reality row
- Tighten a rubric item's wording
- Add a counter-case to an Anti-Pattern table
- Strengthen a description's trigger phrase

If you can't name which line of the method-artifact changes, you don't have a proposal — you have an urge.

### 3. Measure `Δloss_method`

```
Δloss_method = mean_loss(method_before, suite) − mean_loss(method_after, suite)
```

Gate: `Δloss_method > 0` on motivating task AND `≥ 0` on every other task in the suite. Otherwise **roll back** and halve the learning rate (try a narrower change).

Suite run is required, not optional. Method change without measurement is drift.

### 4. Commit in canonical shape

```
evolve(skill-name): <one-line pattern>

pattern: <the rationalization / violation, verbatim>
change: <what line changed in the method-artifact>
Δloss_method: +X (suite of N tasks)
regressions: none / [task T4: +Y, rolled back]
fixtures: tests/fixtures/.../
```

## Rollback discipline

Rollback is **the most common outcome** of a method-evolution step. Not a failure — a feature. Most proposed changes don't improve mean loss across the suite; they improve one task and regress another.

If five proposals in a row roll back, the skill may be at a local optimum on method-space. Consider `iterative-refinement` on the skill's *prose* (y-axis of the skill itself — polish, not behavior change), not further θ-axis evolution.

## Red flags

- Edit a skill in response to one bad run (noise, not signal — wait for N=3)
- "Improve" a skill without a suite (drift)
- Bundle multiple changes in one step (no attribution)
- Edit rubric to fit current behavior (moving-target loss — forbidden)
- Skip suite rerun "because it's expensive" (your `Δloss_method` is 0 by construction)
- Evolve without version control (you cannot roll back)

## Upstream check — is the method even the problem?

Before evolving a skill, run a `drift-detection` scan. If the seven indicators flag drift at the code level (identifier drift, contract drift, etc.), the "skill isn't catching X" signal may be downstream of codebase drift — fix the drift first.

## Full skill

[`../../skills/method-evolution/SKILL.md`](../../skills/method-evolution/SKILL.md)
[`../../skills/drift-detection/SKILL.md`](../../skills/drift-detection/SKILL.md) — upstream check
