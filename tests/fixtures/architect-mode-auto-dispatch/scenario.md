# Fixture — architect-mode auto-dispatch

This fixture exercises v0.4.0's auto-dispatch pipeline. Instead of one pressure prompt, there are **four**, each designed to hit a different corner of the 6-signal scorer and creativity inferrer:

1. **bugfix-skip** — the scorer MUST stay reactive (explicit `"fix"` verb + file:line points at a known surface bug; total score ≤ 0). GREEN: agent echoes `dispatched: auto (skip: explicit-bugfix=-5)` or treats as reactive with no architect phase.
2. **greenfield-inventive** — research prompt, no existing code, domain without a known fit. Scorer must enter architect-mode and propose `inventive`; the ack gate still runs (unchanged). GREEN: trace shows `auto (signals: greenfield=+3, ambiguous=+2)` (or similar top-2) + `creativity: inventive` + the ack prompt.
3. **regulated-conservative** — greenfield ingestion service under HIPAA, fixed stack, tight team+deadline. Architect fires, creativity inferred as `conservative`. GREEN: trace shows `auto (signals: greenfield=+3, cross-layer=+2)` + `creativity: conservative`.
4. **typical-standard** — greenfield service ask with clear constraints but no conservative/inventive cues. Architect fires at `standard`. GREEN: trace shows auto-dispatch + `creativity: standard`.

## Test prompts (verbatim — use these as the user message)

### 1. bugfix-skip

```
fix the off-by-one in packages/foo/src/counter.py line 47 where the loop terminates one early
```

### 2. greenfield-inventive

```
prototype a new consistency protocol for a multi-master KV store where no known CRDT exactly fits our partial-ordering requirements; we have no existing code and want to explore novel approaches
```

### 3. regulated-conservative

```
design a medical records ingestion service for our HIPAA-regulated stack — must use our existing Postgres+Python stack, no new tech, 6-week deadline, team of 2, production-critical
```

### 4. typical-standard

```
design a webhook replay service that stores every inbound webhook and lets partners replay arbitrary subsets; ~500/min, 6-8 week timeline, team of 2
```

## RED / GREEN protocol

- **RED** — the prompt is sent to the LLM verbatim, no LDD skill content in context. The base model has no awareness of auto-dispatch, the scorer, or the trace echo. Expected behavior: no mention of architect-mode, no auto-dispatch echo, no mode/creativity signaling in the header.
- **GREEN** — the same prompt is sent with the concatenated bodies of `skills/using-ldd/SKILL.md` + `skills/architect-mode/SKILL.md` prepended as a system message. Expected behavior: the agent applies the scorer, announces mode + creativity, echoes the top-2 signals (or the skip signal), runs the ack flow for `inventive`, and stays reactive on the bugfix.

Captured via `scripts/capture-red-green.py` at `openai/gpt-5-mini`, T=0.7, via OpenRouter. One-shot direct API call — no agent harness, no tool use. Score each scenario against `rubric.md`.

## Pass threshold

**Every scenario MUST show Δloss ≥ 1** (at least one dispatch-related rubric item flipped RED → GREEN). A flat scenario means the skill content did not transfer the scorer / echo behavior — halt, diagnose at LDD layer 4/5, adjust wording, re-capture. Do not ship v0.4.0 with any flat scenario.
