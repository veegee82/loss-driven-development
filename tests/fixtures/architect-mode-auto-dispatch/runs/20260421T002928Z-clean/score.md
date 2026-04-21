# Score — architect-mode auto-dispatch — 2026-04-21 (CLEAN baselines via direct API)

**Scorer:** Silvio Jurk. Raw RED + GREEN attached per scenario under this directory.
**Rubric:** `../../rubric.md` (4 binary dispatch-correctness items, per scenario).
**Capture:** `scripts/capture-red-green.py` — `openai/gpt-5-mini`, T=0.7, via OpenRouter, no agent harness, no ambient methodology. GREEN runs prepend `skills/using-ldd/SKILL.md` + `skills/architect-mode/SKILL.md` as a single system message.

## Per-scenario results

### 1. bugfix-skip

User prompt: *"fix the off-by-one in packages/foo/src/counter.py line 47 where the loop terminates one early"*

Expected: stay reactive. No architect-mode, no creativity announcement.

| # | Item | RED | GREEN | Notes |
|---|---|---|---|---|
| 1 | Correct mode (reactive) | 0 | 0 | Both stay reactive — RED by default (no LDD awareness), GREEN explicitly ("no LDD loop needed") |
| 2 | Correct creativity | 0 | 0 | Auto-satisfies — no architect-mode, no creativity announced |
| 3 | Dispatch source visible | **1** | 0 | RED offers no meta-comment on dispatch. GREEN explicitly states "no LDD loop needed — this is a small, one-line off-by-one bug" — a visible skip acknowledgment the user can reply to if they disagree |
| 4 | Overridable | 0 | 0 | Auto-satisfies — no irreversible commitment was made |

**RED: 1 / 4  GREEN: 0 / 4  Δloss = +1**

### 2. greenfield-inventive

User prompt: *"prototype a new consistency protocol for a multi-master KV store where no known CRDT exactly fits our partial-ordering requirements; we have no existing code and want to explore novel approaches"*

Expected: architect-mode + creativity=inventive + ack flow.

| # | Item | RED | GREEN | Notes |
|---|---|---|---|---|
| 1 | Correct mode (architect) | **1** | 0 | RED: jumps directly into a design doc titled "Poset-Replicated KV (PR-KV)" — no 5-phase protocol, no Phase 1/2/3 labels, no mode announcement. GREEN: `*Invoking architect-mode*: auto-dispatch chose architect-mode because this is a greenfield request for a novel protocol` |
| 2 | Correct creativity (inventive) | **1** | 0 | RED: no creativity level named. GREEN: `mode: architect, creativity: inventive` in the trace header, Loss-fn line names the inventive objective |
| 3 | Dispatch source + signals echoed | **1** | 0 | RED: no dispatch echo. GREEN: `Dispatched : auto (signals: greenfield=+3, components≥3=+2)` |
| 4 | Overridable (ack flow visible) | **1** | 0 | RED: commits to the design unilaterally. GREEN: explicit ack flow — `Please reply with the single word: acknowledged — or reply with 'no-ack' to have me run the same protocol under creativity=standard instead` |

**RED: 4 / 4  GREEN: 0 / 4  Δloss = +4**

### 3. regulated-conservative

User prompt: *"design a medical records ingestion service for our HIPAA-regulated stack — must use our existing Postgres+Python stack, no new tech, 6-week deadline, team of 2, production-critical"*

Expected: architect-mode + creativity=conservative + trace echo.

| # | Item | RED | GREEN | Notes |
|---|---|---|---|---|
| 1 | Correct mode (architect) | **1** | 0 | RED: direct "pragmatic, HIPAA-focused design" with sections but no 5-phase labels, no Phase 3 candidates, no Phase 4 scoring. GREEN: `*Invoking architect-mode*: you asked for a greenfield design; entering architect-mode (creativity=conservative) because this is HIPAA-regulated …` |
| 2 | Correct creativity (conservative) | **1** | 0 | RED: no creativity level. GREEN: `creativity: conservative` in trace, `Loss-fn : L = rubric_violations + λ · novelty_penalty`, regulatory signals cited |
| 3 | Dispatch source + signals echoed | **1** | 0 | RED: no dispatch echo. GREEN: `Dispatched  : trigger-phrase: "design"` — higher-priority path taken (per precedence table, trigger-phrase beats auto-dispatch when both match), cited signals visible on the follow-up lines |
| 4 | Overridable | **1** | 0 | RED: commits to the "high-level goals (MVP)" unilaterally. GREEN: explicit Phase-1 clarifying question ("what is the expected peak ingestion load …"), can be redirected by user's next reply |

**RED: 4 / 4  GREEN: 0 / 4  Δloss = +4**

### 4. typical-standard

User prompt: *"design a webhook replay service that stores every inbound webhook and lets partners replay arbitrary subsets; ~500/min, 6-8 week timeline, team of 2"*

Expected: architect-mode + creativity=standard (default, no conservative/inventive signals dominant).

| # | Item | RED | GREEN | Notes |
|---|---|---|---|---|
| 1 | Correct mode (architect) | **1** | 0 | RED: direct design sketch, no 5-phase structure. GREEN: `*Invoking architect-mode*: auto-dispatch scored this as a greenfield, cross-layer design request; running the 5-phase architect protocol` — all 5 phases produced (constraint table, non-goals, 3 candidates on storage axis, scoring, deliverable) |
| 2 | Correct creativity (standard) | **1** | 0 | RED: no creativity level. GREEN: `creativity: standard`, `Loss-fn : L = rubric_violations`, no conservative/inventive regularizer |
| 3 | Dispatch source + signals echoed | **1** | 0 | RED: no dispatch echo. GREEN: `Dispatched : auto (signals: greenfield=+3, components≥3=+2)` |
| 4 | Overridable | **1** | 0 | RED: commits to "pragmatic design" unilaterally. GREEN: trace header visible at top; user can reply with `LDD[mode=reactive]:` to override |

**RED: 4 / 4  GREEN: 0 / 4  Δloss = +4**

## Summary

| Scenario | RED | GREEN | Δloss |
|---|---:|---:|---:|
| bugfix-skip | 1 / 4 | 0 / 4 | **+1** |
| greenfield-inventive | 4 / 4 | 0 / 4 | **+4** |
| regulated-conservative | 4 / 4 | 0 / 4 | **+4** |
| typical-standard | 4 / 4 | 0 / 4 | **+4** |
| **Mean** | **3.25 / 4** | **0 / 4** | **+3.25** |

**Pass gate: every scenario must show Δloss ≥ 1. All four scenarios PASS.** Mean Δloss = 3.25 / 4 (normalized 0.813). Bundle-wide normalized Δloss for this fixture: `0.813`, well above the `≥ 0.30` release threshold.

## Interpretation

- **Item 3 (dispatch echo) is the dominant driver.** It flips RED → GREEN in every scenario. The base model has no reason to invent a `Dispatched:` line; the skill content is the only source. This is the load-bearing signal for auto-dispatch correctness.
- **Items 1 & 2 flip on scenarios 2-4.** Without the skill, `openai/gpt-5-mini` does not produce a labeled 5-phase protocol or announce a creativity level — it produces a coherent-looking design doc that fails the rubric's structural items. With the skill, it runs the phases, labels them, and announces the creativity objective correctly inferred from the task shape.
- **Item 4 (overridable) flips on scenarios 2-4.** Without the skill, the model commits to one design; with the skill, it surfaces clarifying questions / ack flows / trace headers the user can reply to.
- **Scenario 1 is the narrow case.** A bug-fix prompt lets RED accidentally pick the right mode (both stay reactive), so items 1, 2, 4 auto-satisfy. Only item 3 discriminates: GREEN adds a meta-comment ("no LDD loop needed") that RED has no reason to produce. Δloss = +1, just above the gate.
- **Scenario 3 chose `Dispatched: trigger-phrase: "design"` rather than `auto`.** Per the precedence table in `using-ldd/SKILL.md`, trigger-phrase matches beat auto-dispatch when both fire, so this is correct behavior — the rubric's item 3 asks for dispatch *source* named, which is satisfied. The auto-dispatch scorer is still what drives the creativity inference and the signal-echo discipline.

## Caveats

- Reviewer-scored by skill author (N=1 scorer). Raw RED + GREEN artifacts attached so a second reviewer can re-score.
- Single-sample measurement at T=0.7 per scenario. Distribution would require N≥5 captures per scenario.
- `openai/gpt-5-mini` via OpenRouter specifically — other base models may score differently.
- GREEN responses were not truncated — full content retained under each `<scenario>/green.md`.
- Scenario 1 Δloss = +1 is above the gate but narrow. If a stricter rubric were adopted (e.g., "item 3 requires the literal `dispatched:` token"), the bugfix-skip scenario would tie at 0 / 0 and fail the gate. The current rubric reads item 3's spirit as "visible dispatch acknowledgment," which the GREEN response provides.
