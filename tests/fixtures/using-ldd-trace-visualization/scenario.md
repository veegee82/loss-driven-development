# Fixture — using-ldd trace visualization

This fixture exercises v0.5.0's trace-visualization enhancement. Three scenarios, each giving the agent a completed LDD task with explicit per-iteration loss data. The agent must emit the full trace block. The rubric measures whether the response includes the four visualization channels made normative in v0.5.0's `skills/using-ldd/SKILL.md` § Loss visualization — sparkline, mini chart, per-iteration bars, trend arrow.

The scenarios are shaped so the base model (RED) has no coincidental reason to emit Unicode block sparklines, axis-ruled mini charts, `█`/`░` per-iteration bars, or `↓`/`↑`/`→` trend arrows — these are only produced when the v0.5.0 skill content is in context (GREEN).

## Test prompts (verbatim — use these as the user message)

### 1. inner-three-iters

```
LDD: I walked a 3-iteration inner loop to fix the test_parse_timestamp_utc flake. The rubric was 7 items (timezone correctness, DST handling, naive-datetime guard, regression tests for 4 sibling parsers). Per-iteration results:

- i1: reproducibility-first + root-cause-by-layer (layer 4: input-contract). Loss = 4/7.
- i2: e2e-driven-iteration. Loss = 2/7.
- i3: loss-backprop-lens sibling check. Loss = 0/7.

Close: fix at layer 4 (input-contract), docs-as-DoD synced. Terminal: complete. Emit the full LDD trace block for this completed inner loop.
```

### 2. all-three-loops

```
LDD: apply-LDD end-to-end to a recurring JSON-parser bug that hit 3 sibling functions. I closed all three optimizer loops:

- inner (rubric 8 items): i1 loss=6/8, i2 loss=3/8, i3 loss=1/8
- refine (rubric 10 items): r1 loss=1/10, r2 loss=0/10
- outer (rubric 8 items): o1 loss=0/8 — skill rubric updated, numeric-input-validation checklist added to prevent regression on 3 sibling tasks

Close: fix at layer 4 (input-contract + method-rubric coverage), layer 5 (deterministic-before-LLM invariant), docs-as-DoD synced on SKILL.md + rubric. Terminal: complete. Emit the full LDD trace block for the full three-loop run.
```

### 3. regression-and-recovery

```
LDD: I'm optimizing worker process startup time. The rubric is 6 items (p50 < 500 ms, p99 < 800 ms, no zombie threads, no stale caches, warmup deterministic, cold-start <= 1200 ms). Per-iteration loss:

- i1: 4/6 violations after first optimization pass (loss = 0.667).
- i2: 5/6 — REGRESSION: I cached the wrong object, p99 got worse (loss = 0.833).
- i3: 1/6 — reverted the bad cache, different approach, almost there (loss = 0.167).

The trajectory is NOT monotonic: it regresses from i1 to i2, then recovers from i2 to i3. End-to-end net direction is descent (0.667 → 0.167). Emit the full LDD trace block showing the regression and recovery.
```

## RED / GREEN protocol

- **RED** — the user prompt is sent verbatim to the LLM with no LDD skill content in context. The base model has no awareness of v0.5.0's visualization channels. Expected behavior: may produce a trace table or prose summary; will NOT spontaneously emit a Unicode-block sparkline, an axis-ruled mini chart, `█`/`░` per-iteration bars, or an explicit trend arrow.
- **GREEN** — the same prompt is sent with the full body of `skills/using-ldd/SKILL.md` prepended as a system message. Expected behavior: the agent emits all four visualization channels (trajectory sparkline, mini loss-curve chart, per-iteration magnitude bars, trend arrow) consistent with the iteration data in the prompt.

Captured via `scripts/capture-red-green.py` at `deepseek/deepseek-chat-v3.1`, T=0.7, via OpenRouter. One-shot direct API call — no agent harness, no tool use. Score each scenario against `rubric.md`.

## Pass threshold

**Every scenario MUST show Δloss ≥ 1** (at least one of the four visualization items flipped RED → GREEN). **Bundle-normalized Δloss (mean / 4) MUST be ≥ 0.30**. A flat scenario means the v0.5.0 skill wording did not transfer the visualization discipline — halt, diagnose the skill wording at LDD layer 4/5, adjust, re-capture. Do not ship v0.5.0 with any flat scenario.
