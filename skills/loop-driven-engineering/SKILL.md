---
name: loop-driven-engineering
description: Use at the start of any non-trivial engineering task (feature, bugfix touching more than one file, refactor with observable behavior change, incident response). Orchestrates the plan → code → fast-gate → expensive-gate → diagnose → repeat loop with a hard iteration budget, and composes root-cause-by-layer, loss-backprop-lens, dialectical-reasoning, and docs-as-definition-of-done as sub-skills.
---

# Loop-Driven-Engineering

## Overview

Engineering is a **loop**, not a pipeline. You plan, you try, you measure, you diagnose, you try again. The thing that separates good engineering from flailing is **budget discipline** (how many iterations before you stop), **test-pyramid discipline** (cheap gates before expensive ones), and **sub-skill discipline** (using the right thinking tool at the right moment).

**Core principle:** The loop closes when applicable gates are green **and** the doc-level mental model is current. Not when one test passes. Not when "it looks right." Not when the LLM sounds confident.

This skill is a **flexible pattern**, not a rigid procedure. Use judgment; adapt the structure to the task. But the budget and escalation rule are hard.

## When to Use

Invoke at the **start** of any non-trivial engineering task:

- Feature touching ≥2 files or ≥1 public surface
- Bugfix where the cause is not yet identified
- Refactor with observable behavior change (even if spec-preserving)
- Incident response
- Plan-driven work (a multi-step design under time pressure)
- Any work where you are tempted to "just start coding"

Do **not** use for:
- Trivial edits (rename a variable, fix a typo, delete dead code)
- Pure lookups or explanations
- Tasks already framed by a written plan you're executing verbatim

## The Loop

```
read context (CLAUDE.md / README / relevant docs — only what the task needs)
  ↓
plan (brainstorm → thesis/antithesis/synthesis → concrete next step)
  ↓
loop(k ≤ K_MAX = 5):
    code (one focused change, smallest coherent unit)
    ↓
    fast gates (lint, type, unit, schema validation — cheap, deterministic)
    ↓
    expensive gates if and only if warranted (integration, E2E, full build)
    ↓
    if green AND task-complete: break
    if failed: diagnose (root-cause-by-layer) → decide step size (loss-backprop-lens) → next iteration
    ↓
    if k == K_MAX: STOP — escalate with a written diagnosis, do not keep grinding
  ↓
close: docs-as-definition-of-done → commit
```

## The Budget: K_MAX = 5

**Five iterations per task, default.** If the loop has not closed after five, stop, write what failed and why, and escalate (to the user, to a colleague, to a different skill).

Why five: below that, you haven't explored; above it, you're flailing. Each extra iteration beyond five is a ~linear increase in sunk-cost bias and a ~geometric decrease in probability the next iteration will converge without a structural rethink.

**Hard rule:** when k hits K_MAX, produce:
1. Summary of what was tried each iteration
2. The specific gate / test / symptom that kept failing
3. The causal story at layer 4–5 (via root-cause-by-layer)
4. A proposed architectural step (via loss-backprop-lens: "the learning rate needs to be bigger")
5. Explicit ask for redirection — do **not** silently try a 6th iteration

## The Test Pyramid (cheap → expensive)

Run gates in order of cost. Only escalate when the current tier is green.

| Tier | Examples | When to run |
|---|---|---|
| 0. **Local thought** | Read the code you're changing; grep for callers; skim docs | Always, before any edit |
| 1. **Schema / lint / type** | `ruff`, `tsc --noEmit`, JSON / YAML schema validation | After every code edit |
| 2. **Unit tests** | `pytest tests/unit`, `npm run test:unit` | After tier-1 green |
| 3. **Integration** | Hits a DB / filesystem / fake HTTP server | After tier-2 green, for changes crossing module boundaries |
| 4. **E2E** | Real external services, full-stack, long runtime | Only when tier-3 green AND the change warrants it (behavior change, pre-release, public-surface delta) |
| 5. **Live / production-like** | Canary, shadow traffic, staged rollout | Only after tier-4, only for high-blast-radius changes |

**Anti-pattern:** running E2E to catch a typo. It would have been caught by tier 1 in 2 seconds. Know your pyramid.

**Anti-pattern:** skipping tiers 1–3 because "E2E will catch everything." It won't, and when it fails you will have no idea at which layer it broke.

## Sub-Skill Dispatch

This is a composition skill. Use these at the specific moments below:

| Moment in the loop | Sub-skill | Why |
|---|---|---|
| Planning or making a non-trivial recommendation | `superpowers:brainstorming` or `dialectical-reasoning` | Force the counter-case before committing to an approach |
| Designing a multi-step plan on paper | `superpowers:writing-plans` | Externalize the plan so the loop has a shape |
| Writing a test before the code | `superpowers:test-driven-development` | Red → green discipline for implementation work |
| Debugging a failing gate / test / run | `root-cause-by-layer` | Find the structural origin, not the surface symptom |
| Deciding whether one failure is signal, or whether to refactor vs. local-fix | `loss-backprop-lens` | Signal-vs-noise, step-size calibration |
| Asking "is this the right approach?" before shipping | `dialectical-reasoning` | Surface load-bearing assumptions |
| Before committing / pushing / declaring done | `docs-as-definition-of-done` | Sync docs to current behavior |
| Before declaring "success" / "it's fixed" | `superpowers:verification-before-completion` | Evidence before assertion |
| Before merging | `superpowers:requesting-code-review` | Second set of eyes |

You are **not** required to invoke all of them on every task. Pick what the loop actually needs at this step. But you **are** required to invoke the right one at the right moment — skipping `root-cause-by-layer` on a debug, or skipping `docs-as-definition-of-done` on a behavior change, is a process failure.

## Red Flags — STOP, the loop is broken

- "I've tried this same fix 3 times, let me try a 4th variant" → you are in a local-minimum trap, invoke `loss-backprop-lens`, consider architectural step
- "I'll run E2E to see what breaks" (skipping tiers 1–3) → pyramid violation
- "I'll just commit and iterate in follow-ups" → budget discipline failure; write a plan instead
- "The LLM / build / test was flaky, let me retry" → invoke `loss-backprop-lens`, check for signal
- "This is iteration 6, one more should do it" → K_MAX violation; stop and escalate
- "Docs are fine for now, behavior change is subtle" → invoke `docs-as-definition-of-done`
- "I don't need a plan, it's a small change" → "small" is the most common rationalization for no-plan
- Same gate rejecting with the same reason ≥ 2 iterations → stagnation; abort, diagnose, restart with a fix at the structural origin

## Escalation on Non-Convergence

When you can't close the loop, the productive response is **not** to try harder — it's to communicate. The right escalation has:

- **What was tried** — concrete, per iteration.
- **What kept failing** — the gate, test, or symptom, verbatim.
- **The layer-4/5 diagnosis** (via root-cause-by-layer).
- **The step-size recommendation** (via loss-backprop-lens): is this a local-fix problem that needs fresh eyes, or a structural problem that needs a different design?
- **The explicit ask** — what input do you need to proceed?

A well-escalated non-convergence beats a silently-limping sixth iteration every time.

## How to Apply — checklist

1. **Context read** — only what the task needs. If the project has a `CLAUDE.md` / `AGENTS.md`, load it. Load the relevant docs. Do **not** read the whole repo.
2. **Plan** — one paragraph, run it through `dialectical-reasoning` if non-trivial. For multi-step work, write it out (`superpowers:writing-plans`).
3. **Enter loop.** k = 0, K_MAX = 5.
4. **For each iteration:** smallest coherent code change → fast gates → diagnose failures via sub-skills → decide step size.
5. **Close** — run docs-as-definition-of-done, verify completion (`superpowers:verification-before-completion`), commit as one logical unit.
6. **If K_MAX hit** — escalate with the checklist above.

## Counter-Examples — when this skill is overkill

- You're renaming a local variable. Just rename it.
- You're fixing a typo in a README. Fix it, commit.
- You're answering a factual lookup question. Read and answer.

The skill is for **multi-step engineering under uncertainty**, not for every interaction.

## Real-World Shape

Good loop (feature: add `--dry-run` to `myapp deploy`):
1. Read `cli.py`, `deploy.py`, relevant README sections. (1 min)
2. Plan: dialectical pass — "thesis: add a flag, gate execution on it; antithesis: dry-run could leak partial state if deploy has side effects in plan-phase; synthesis: separate `plan()` from `execute()`, flag only skips `execute()`." (3 min)
3. k=1: refactor `plan()`/`execute()` split, unit tests for both. Tier-1+2 green. (15 min)
4. k=2: add flag, test dry-run path. Tier-1+2+3 green. (10 min)
5. Close: `docs-as-definition-of-done` — README L82 safety note, cli-reference table, user-guide preview section. (5 min)
6. Commit as one logical unit. Done in 2 iterations, budget to spare.

Bad loop (same task, no discipline):
1. Start coding the flag. k=1: works, but broke side-effect ordering. k=2: patch the ordering, broke a different test. k=3: patch that, broke idempotency. k=4: flaky. k=5: ship with retry. k=6: "one more fix." k=7: push through freeze window with TODO on README. Two weeks later, incident.

## Related / Composed

- **`root-cause-by-layer`** — for debugging (the structural 5-layer ladder)
- **`loss-backprop-lens`** — for edit-size calibration and signal-vs-noise
- **`dialectical-reasoning`** — for planning and recommendations
- **`docs-as-definition-of-done`** — for the close of the loop
- **`superpowers:brainstorming`** — for open-ended problem framing
- **`superpowers:writing-plans`** — for externalized multi-step plans
- **`superpowers:test-driven-development`** — for red-green discipline when writing code
- **`superpowers:verification-before-completion`** — for evidence before success claims
- **`superpowers:systematic-debugging`** — overlaps with root-cause-by-layer; prefer root-cause-by-layer for the explicit 5-layer ladder, use systematic-debugging when you need the broader investigation framing
