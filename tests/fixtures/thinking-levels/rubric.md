# Rubric — LDD thinking-levels auto-dispatch (9 scenarios)

Four binary dispatch-correctness items, scored **per scenario**. Each item: 0 = satisfied in the response, 1 = violated.

The rubric is intentionally narrow — it measures *dispatch-correctness*, not work-quality. Work-quality at each level is the next layer down (Phase 1 unit tests + Phase 2 integration runs).

## Items (apply to every scenario)

1. **Correct level chosen.** The response announces a level that matches the scenario's expected level. "Announce a level" means an explicit `Dispatched: L<n>/<name> …` line (v0.11.0 format) OR an unambiguous natural-language equivalent (e.g. `"running at level L2/deliberate"`). For `override-natural-language`, both L1 and L2 are GREEN. For `override-down-warning`, L0 is GREEN as long as item 3 is also satisfied (see below).

2. **Dispatch source named.** The response includes a dispatch-source phrase matching one of: (auto — implicit, no keyword required in v0.11.0), `user-explicit`, `user-bump`, `user-override-down`. Per scenario:
   - Scenarios 1–5 (the L0–L4 level scenarios): auto-dispatch (implicit — no dispatch-source phrase in the parenthetical means auto).
   - Scenario 6, 7: `user-bump`.
   - Scenario 8 (`override-natural-language`): `user-bump`.
   - Scenario 9 (`override-down-warning`): `user-override-down`.

3. **Top-2 signals echoed (or user-override-down warning emitted).** For auto-dispatch scenarios: the trace header names the top-2 signals by absolute weight that produced the level. For `user-bump` scenarios: the header names the phrase or flag that triggered the bump (e.g. `fragment: "LDD++"`, `fragment: "take your time"`). For `user-override-down`: the header contains the literal substring `"from L"` naming the scorer's proposal and some form of "user accepts" / "loss risk" / "override" warning language — silent downgrade is an automatic item-3 violation.

4. **Upward-bias compliance.** The response must not drift downward from the scorer's proposal without the `user-override-down` marker. Specifically:
   - If the scorer would produce L2 or higher, the response must not silently announce L0 or L1.
   - A response that announces L0 on scenario 3 (L2-deliberate) or scenario 4 (L3-structural) fails this item even if no explicit override was requested.
   - For scenarios 6, 7, 8 the user's bump direction is UP — the response must not clamp the bump back down (e.g. `LDD++: fix typo` must not announce L0 "because the task looks simple").

## Scoring shape

Per scenario: sum violations (0–4). `Δloss = red_loss − green_loss`.

Pass threshold:

```
for each scenario: Δloss ≥ 1
```

i.e. at least one of the four items must flip RED → GREEN in every scenario.

## Asymmetric-loss weighting at the suite level

Individual scenarios use equal-weight binary items. But at the **suite level**, the pass/fail summary applies an asymmetric weight to the direction of failure, encoding the user's `lieber schlau als zu dumm` rule:

| Failure direction | Weight | Example |
|---|---|---|
| Chose level too LOW (e.g. expected L2, got L1) | **×2** | L3-structural scored L1 |
| Chose level too HIGH (e.g. expected L2, got L3) | ×1 | L1-diagnostic scored L2 |
| Chose correct level but missed an item (2, 3, or 4) | ×1 | L2 chosen, signals not echoed |

Suite-level score = Σ (item_violations × direction_weight). The asymmetric weighting does NOT change per-scenario pass/fail — it only ranks which failures to fix first during Phase-1/Phase-2 iteration.

## Why these 4 items and not more

The rubric maps 1-to-1 to the four concrete artifacts the spec introduces:

| Rubric item | Spec artifact |
|---|---|
| 1 (correct level) | 9-signal scorer + score-to-level table (§5.2) |
| 2 (dispatch source) | 4-valued `<source>` enum (§5.4) |
| 3 (signals/bump phrase echoed) | Trace-header format (§5.4) + override-down warning (§5.3) |
| 4 (no silent downgrade) | Upward-bias rule (§1 constraint 6, §5.2 tie-break) |

A RED response cannot satisfy items 2, 3, 4 by chance — the base model has no reason to invent a `Dispatched:` line, a source token, or a "user accepts loss risk" warning. Item 1 CAN be satisfied by coincidence on scenarios where the base model happens to spend roughly the right amount of effort. The Δloss ≥ 1 gate is tuned so items 2, 3 almost always flip; items 1 and 4 flip opportunistically.

## Why the override-down scenario is not optional

`override-down-warning` is the only scenario where the user actively asks for LESS rigor than the scorer proposes. It exists to prove that:

- The system respects user authority even when it disagrees (item 1 passes with L0).
- The system refuses to be silent about the disagreement (item 3 demands the warning).

Removing it would let the system ship with a "silent user-override-down" bug, which is exactly the class of trace-integrity violation the spec is meant to prevent.
