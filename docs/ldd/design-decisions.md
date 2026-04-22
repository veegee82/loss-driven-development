# Design decision / trade-off / architectural choice

Load this when the user says: "should we...", "is X the right approach", "ship or don't ship", "A vs B", "worth it?", trade-off questions, design reviews.

## Skill

Primary: [`dialectical-reasoning`](../../skills/dialectical-reasoning/SKILL.md) — cross-cutting discipline that applies on every one of the [four gradients](../theory.md). Secondary: [`loss-backprop-lens`](../../skills/loss-backprop-lens/SKILL.md) for step-size calibration.

## The protocol — thesis → antithesis → synthesis

Every non-trivial recommendation, out loud, in labeled form.

### 1. Thesis

State the proposal in its strongest form. Name the **load-bearing assumption** (what must be true for this proposal to work).

### 2. Antithesis — attack it hard

Hit at least 3 of these vectors:

- **Hidden assumptions** — what is the thesis quietly assuming about scale, callers, environment?
- **Edge cases** — what input / state / timing / concurrency breaks it?
- **Contracts under strain** — which written or unwritten contract does it violate or stretch?
- **Second-order effects** — what does it make harder later? What does it couple?
- **Alternative framings** — is the problem itself framed correctly?
- **Asymmetric risks** — what's the cost if wrong? Reversible?
- **Who would reject this** — name a reasonable person who would say no and why

A weak antithesis (one edge case, no re-framing, no risk analysis) means the thesis has not been tested — redo.

### 3. Synthesis — strictly stronger than thesis

- **More correct** (sharper version the antithesis forced)
- OR **more narrowly scoped** (the thesis was right for a subset)
- OR **more honestly hedged** (thesis right under stated conditions)
- OR **replaced** (antithesis won)

"The thesis was right" is only valid AFTER a real antithesis — not in place of one.

## Red flags — STOP, you stopped at thesis

- "This is obviously the right call because…"
- "It's a simple matter of…"
- "No-brainer"
- "Everyone agrees that…" (have you asked a dissenter?)
- Any recommendation without an explicit "but" / "however"
- Happy-path-only reasoning

## Step-size note (if decision involves a code edit)

Apply `loss-backprop-lens`: does the recommended change match the *loss pattern* you are addressing?

- One observed failure → local change
- Recurring pattern → architectural change, even at more lines today
- Don't trade training loss against generalization loss ("it fixes the current test but breaks siblings" = overfit)

## Presentation

Show the synthesis as your recommendation. Surface the antithesis only when the tension is **load-bearing** — user needs to see the rejected alternative to judge. A two-sentence synthesis that survived a real antithesis beats a four-paragraph analysis that didn't.

## Full skill

[`../../skills/dialectical-reasoning/SKILL.md`](../../skills/dialectical-reasoning/SKILL.md)
