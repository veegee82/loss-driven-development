# Fixture — LDD thinking-levels auto-dispatch

This fixture exercises the level-selection pipeline from the design doc at
`docs/superpowers/specs/2026-04-22-ldd-thinking-levels-design.md`.

Nine scenarios cover the full dispatch surface:

- **Five level scenarios** (`L0-reflex` … `L4-method`) — one representative task per level. GREEN must show the single-line `Dispatched: L<n>/<name>[ · creativity=<value>] (signals: …)` (v0.11.0 format) matching the expected level.
- **Four override scenarios** covering every override path:
  1. `override-up-from-L0` — simple task + `LDD++:` prefix → L2.
  2. `override-max-on-simple` — simple task + `LDD=max:` prefix → L4.
  3. `override-natural-language` — simple task + `"take your time and think hard"` → L1 or L2.
  4. `override-down-warning` — cross-layer task (scorer proposes L3) + `LDD[level=L0]:` → honors L0 but logs a `user-override-down` warning in the trace header.

## Why these 9 scenarios

The five-level scenarios are the canonical positive-case coverage — one per bucket. The four override scenarios directly map to the four paths in the precedence rule from the spec §5.3 (explicit > max > relative-bump > natural-language > auto). Together they verify:

| Property | Covered by |
|---|---|
| Scorer buckets are not collapsed | 5 level scenarios |
| Natural-language bumps are recognized (no syntax needed) | `override-natural-language` |
| Explicit relative bump beats auto | `override-up-from-L0` |
| Clamp-to-max works | `override-max-on-simple` |
| Downward override is honored but not silent | `override-down-warning` |

## Test prompts (verbatim — use these as the user message)

### 1. L0-reflex

```
fix the typo in README.md line 12: "Agent Worklow" should be "Agent Workflow"
```

Expected: `Dispatched: L0/reflex (signals: explicit-bugfix=-5, single-file=-3)`.

### 2. L1-diagnostic

```
the unit test test_parser_handles_empty_input in packages/awp-core/tests/test_parser.py is failing after my last change; help me fix it
```

Expected: `Dispatched: L1/diagnostic (signals: explicit-bugfix=-5, single-file=-3)` OR an equivalent negative-weighted top-2 with level L1. (The `explicit-bugfix` signal is weaker here than in L0 because the scope is a test-fix, not a typo — one layer above pure mechanical.)

### 3. L2-deliberate

```
add a confidence threshold to the validator: agents below 0.6 should trigger a repair subtask
```

Expected: `Dispatched: L2/deliberate (signals: contract-rule-hit=+2, layer-crossings=+2)` or similar. No explicit trigger phrases; default baseline-plus-one.

### 4. L3-structural

```
we need to add a new critique gate for repair-fixpoint detection between the existing critique and deliverable_presence gates in the delegation loop; it should hook into the same R35 mechanism
```

Expected: `Dispatched: L3/structural · creativity=standard (signals: cross-layer=+2, contract-rule-hit=+2)`. Raw score +6 lands directly in the L3 bucket (4..7); no clamp needed here. The clamp rule itself is verified by `scripts/test_level_scorer.py` against a synthetic higher-score prompt.

### 5. L4-method

```
design a new autonomy sublevel between A2 and A3 for manager-led recursive delegation with shared memory; greenfield, no known pattern fits directly, we want to prototype novel mechanisms
```

Expected: `Dispatched: L4/method · creativity=inventive (signals: greenfield=+3, components≥3=+2)` followed by the standard `inventive` acknowledgment flow.

### 6. override-up-from-L0

```
LDD++: fix the typo in README.md line 12
```

Expected: `Dispatched: L2/deliberate (user-bump from L0, fragment: "LDD++")`. The `LDD++` bumps two levels from L0 → L2.

### 7. override-max-on-simple

```
LDD=max: fix the typo in README.md line 12
```

Expected: `Dispatched: L4/method · creativity=inventive (user-bump from L0, fragment: "LDD=max")`. Clamped to L4 regardless of scorer output.

### 8. override-natural-language

```
take your time and think hard about this: rename the variable `foo` to `bar` in packages/awp-core/src/awp/cli.py
```

Expected: `Dispatched: L1/diagnostic (user-bump from L0, fragment: "take your time")` or `L2/deliberate (user-bump from L0, fragment: "…")`. The phrase `"take your time"` and `"think hard"` are both recognized; either alone triggers +1, together +2 is also acceptable. The rubric accepts L1 or L2 as GREEN.

### 9. override-down-warning

```
LDD[level=L0]: we need to add a new critique gate for repair-fixpoint detection between the existing critique and deliverable_presence gates in the delegation loop; it should hook into the same R35 mechanism
```

Expected: `Dispatched: L0/reflex (user-override-down from L3). User accepts loss risk.` The agent honors L0 but MUST emit the warning — silent acceptance is a trace-integrity violation.

## RED / GREEN protocol

- **RED** — the prompt is sent to the LLM verbatim, no LDD skill content in context. Expected behavior: no `Dispatched:` line, no level awareness, no signal echo. The base model will just start working at whatever depth it defaults to.
- **GREEN** — the same prompt is sent with the concatenated bodies of `skills/using-ldd/SKILL.md` (post-Phase-2 version) + the level-scorer spec prepended as a system message. Expected: the agent computes the score, announces the level, echoes the dispatch source + top-2 signals, and respects any override.

Captured via `scripts/capture-red-green.py` (same pattern as architect-mode-auto-dispatch), `openai/gpt-5-mini`, T=0.7, via OpenRouter. One-shot direct API call — no agent harness, no tool use. Score each scenario against `rubric.md`.

## Pass threshold

**Every scenario MUST show Δloss ≥ 1** (at least one of the 4 rubric items flipping RED → GREEN). A flat scenario means the scorer content did not transfer — halt, diagnose at LDD layer 4/5, adjust, re-capture. Do not ship this change with any flat scenario.

**Additionally, the asymmetric-loss rule applies**: a scenario that fails by choosing a level too LOW counts as a harder failure than one that fails by choosing too high. If the 9-scenario suite shows k low-side failures and k high-side failures with equal Δloss, the low-side failures must be fixed first. This encodes `lieber ein klein wenig schlau als zu dumm` at the test-suite level.

## Relation to the architect-mode-auto-dispatch fixture

This fixture **supersedes** the architect-mode-auto-dispatch fixture for the 4 scenarios where they overlap (scenario 1 bugfix-skip ≈ L0-reflex, scenarios 2/3/4 ≈ L3/L4 with creativity). After Phase 2 lands, the architect-mode-auto-dispatch fixture can be kept for regression-only, with this fixture as the primary source of dispatch-correctness signal.
