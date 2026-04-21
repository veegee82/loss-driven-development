# Rubric — architect-mode auto-dispatch (4 scenarios)

Four binary dispatch-correctness items, scored **per scenario**. Each item: 0 = satisfied in the response, 1 = violated.

The rubric is intentionally narrow — it measures *dispatch-correctness*, not architecture quality. Architecture quality is covered by `tests/fixtures/architect-mode/rubric.md`.

## Items (apply to every scenario)

1. **Correct mode chosen.** The response either enters architect-mode (for scenarios 2, 3, 4) or stays reactive (for scenario 1 — bugfix-skip). "Enter architect-mode" means: the 5-phase protocol is invoked OR an explicit header / announcement names architect-mode + a creativity level. "Stay reactive" means: no mention of architect-mode, no phase-1/phase-2/phase-3 scaffolding, response treats the ask as a direct fix / direct design-doc in normal flow.

2. **Correct creativity level chosen.** For scenarios 2–4, the announced creativity matches the expected level per scenario:
   - scenario 2: `inventive` (with acknowledgment flow visible in the response)
   - scenario 3: `conservative`
   - scenario 4: `standard`

   For scenario 1 this item auto-satisfies (0) — there is no architect mode, so no creativity level is announced.

3. **Dispatch source + signals echoed in trace header.** The response includes a `Dispatched: auto (...)` line (or equivalent per-response header text) naming the top-2 signals by absolute weight, OR for scenario 1 names the skip signal (`skip: explicit-bugfix=-5` or similar). A header that says `mode: architect` without naming the dispatch source fails this item — the user must be able to see WHY architect-mode was entered.

4. **User override respected / overridable.** The response does NOT commit to architect-mode irreversibly — either because the ack flow (scenario 2) lets the user stop, OR because the trace echo (scenarios 3, 4) is visible for the user to reply "LDD[mode=reactive]:" to override. For scenario 1, this item auto-satisfies (0) — no commitment was made.

## Scoring shape

Per scenario: sum violations (0–4). `Δloss = red_loss − green_loss`.

Pass threshold for v0.4.0:

```
for each scenario: Δloss ≥ 1
```

i.e. at least one of the four items must flip RED → GREEN in every scenario. A scenario with `red_loss = 4` and `green_loss = 4` is flat — it means the skill content is not transferring, which is an LDD layer-4/5 failure (the θ parameters did not move the output); diagnose and re-capture, do not ship.

## Why these 4 items and not more

The rubric is narrow on purpose — wider rubrics measure architecture quality (covered elsewhere) and would dilute the dispatch signal we're trying to isolate. The 4 items map 1-to-1 to the four concrete changes v0.4.0 makes:

| Rubric item | v0.4.0 skill change |
|---|---|
| 1 (correct mode) | Signal scorer in `using-ldd/SKILL.md` § Auto-dispatch for architect-mode |
| 2 (correct creativity) | Creativity-inference table in the same section |
| 3 (dispatch echo) | Trace-header `Dispatched:` line in `using-ldd/SKILL.md` + `architect-mode/SKILL.md` § Auto-dispatch by the coding agent |
| 4 (overridable) | Precedence rule in `using-ldd/SKILL.md` + ack flow preserved in `architect-mode/SKILL.md` |

A RED response cannot satisfy item 3 by chance — the base model has no reason to invent a `Dispatched:` line. Items 1 and 2 the base model CAN satisfy by coincidence (e.g. RED may correctly skip architect on scenario 1 simply because LLMs don't usually scaffold a design doc for a one-line bug fix). The Δloss ≥ 1 gate is tuned so item 3 almost always flips; items 1, 2, 4 flip opportunistically.
