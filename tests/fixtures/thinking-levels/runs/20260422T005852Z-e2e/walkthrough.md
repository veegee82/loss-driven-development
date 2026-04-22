# Thinking-levels E2E walkthrough

Deterministic system-level verification that the scorer + preset table + 
clamp rule + override parsing agree with `docs/ldd/thinking-levels.md` 
and `skills/using-ldd/SKILL.md` § Auto-dispatch: thinking-levels.

No LLM call; the scorer is deterministic. 12 scenarios — 5 level, 4 override, 3 stress.
## Summary

**12 / 12 scenarios passed.**

| Category | Passed | Total |
|---|---|---|
| level | 5 | 5 |
| override | 4 | 4 |
| stress | 3 | 3 |

All scenarios green. The dispatch system is consistent end-to-end.


### L0-reflex — ✅ PASS

**Category:** level
**Prompt:**
> fix the typo in README.md line 12: "Agent Worklow" should be "Agent Workflow"

**Scorer output:**
- Raw score: `-8`
- Signals fired: `explicit-bugfix=-5, single-file=-3`
- Auto-level: `L0`
- Final level: `L0` *(expected: L0 — ✓)*
- Dispatch source: `auto-level` *(expected: auto-level — ✓)*
- Creativity: `standard`
- Clamp reason: `none`
- Override fragment: `none`

**Dispatch header emitted:**
```
Dispatched: auto-level L0 (signals: explicit-bugfix=-5, single-file=-3)
```

**Skill floor invoked (minimum):**
- `e2e-driven-iteration`

**Notes:** Pure mechanical typo fix. Minimum skill floor.


### L1-diagnostic — ✅ PASS

**Category:** level
**Prompt:**
> the unit test test_parser_handles_empty_input in packages/awp-core/tests/test_parser.py is failing after my last change; help me fix it

**Scorer output:**
- Raw score: `-6`
- Signals fired: `explicit-bugfix=-5, single-file=-3, ambiguous=+2`
- Auto-level: `L1`
- Final level: `L1` *(expected: L1 — ✓)*
- Dispatch source: `auto-level` *(expected: auto-level — ✓)*
- Creativity: `standard`
- Clamp reason: `none`
- Override fragment: `none`

**Dispatch header emitted:**
```
Dispatched: auto-level L1 (signals: explicit-bugfix=-5, single-file=-3)
```

**Skill floor invoked (minimum):**
- `e2e-driven-iteration`
- `reproducibility-first`
- `root-cause-by-layer`

**Notes:** Failing test + ambiguous origin → reproducibility-first is mandatory.


### L2-deliberate — ✅ PASS

**Category:** level
**Prompt:**
> bump the confidence threshold default from 0.5 to 0.6 in the validator, and update any tests that expect the old value

**Scorer output:**
- Raw score: `2`
- Signals fired: `contract-rule-hit=+2`
- Auto-level: `L2`
- Final level: `L2` *(expected: L2 — ✓)*
- Dispatch source: `auto-level` *(expected: auto-level — ✓)*
- Creativity: `standard`
- Clamp reason: `none`
- Override fragment: `none`

**Dispatch header emitted:**
```
Dispatched: auto-level L2 (signals: contract-rule-hit=+2)
```

**Skill floor invoked (minimum):**
- `e2e-driven-iteration`
- `reproducibility-first`
- `root-cause-by-layer`
- `dialectical-reasoning`
- `loss-backprop-lens`
- `docs-as-definition-of-done`

**Notes:** Magic-number change on a contract → dialectical pass mandatory.


### L3-structural — ✅ PASS

**Category:** level
**Prompt:**
> we need to add a new critique gate for repair-fixpoint detection between the existing critique and deliverable_presence gates in the delegation loop; it should hook into the same R35 mechanism

**Scorer output:**
- Raw score: `6`
- Signals fired: `contract-rule-hit=+2, cross-layer=+2, layer-crossings=+2`
- Auto-level: `L3`
- Final level: `L3` *(expected: L3 — ✓)*
- Dispatch source: `auto-level` *(expected: auto-level — ✓)*
- Creativity: `standard` *(expected: standard — ✓)*
- Clamp reason: `none`
- Override fragment: `none`

**Dispatch header emitted:**
```
Dispatched: auto-level L3 (signals: contract-rule-hit=+2, cross-layer=+2)
mode: architect, creativity: standard
```

**Skill floor invoked (minimum):**
- `e2e-driven-iteration`
- `reproducibility-first`
- `root-cause-by-layer`
- `dialectical-reasoning`
- `loss-backprop-lens`
- `docs-as-definition-of-done`
- `architect-mode (standard)`
- `drift-detection`
- `iterative-refinement`

**Notes:** Cross-layer additive work, architect/standard.


### L4-method — ✅ PASS

**Category:** level
**Prompt:**
> design a new autonomy sublevel between A2 and A3 for manager-led recursive delegation with shared memory; greenfield, no known pattern fits directly, we want to prototype novel mechanisms

**Scorer output:**
- Raw score: `11`
- Signals fired: `greenfield=+3, ambiguous=+2, components>=3=+2, cross-layer=+2, layer-crossings=+2`
- Auto-level: `L4`
- Final level: `L4` *(expected: L4 — ✓)*
- Dispatch source: `auto-level` *(expected: auto-level — ✓)*
- Creativity: `inventive` (implicit ack from ≥2 inventive cues in prompt) *(expected: inventive — ✓)*
- Clamp reason: `none`
- Override fragment: `none`

**Dispatch header emitted:**
```
Dispatched: auto-level L4 (signals: greenfield=+3, ambiguous=+2)
mode: architect, creativity: inventive (implicit ack from ≥2 inventive cues in prompt)
```

**Skill floor invoked (minimum):**
- `e2e-driven-iteration`
- `reproducibility-first`
- `root-cause-by-layer`
- `dialectical-reasoning`
- `loss-backprop-lens`
- `docs-as-definition-of-done`
- `architect-mode (inventive, ack-gated)`
- `drift-detection`
- `iterative-refinement`
- `method-evolution`
- `dialectical-cot`
- `define-metric`

**Notes:** Greenfield + novel + prototype → inventive, ack-gated.


### override-up-from-L0 — ✅ PASS

**Category:** override
**Prompt:**
> LDD++: fix the typo in README.md line 12

**Scorer output:**
- Raw score: `-8`
- Signals fired: `explicit-bugfix=-5, single-file=-3`
- Auto-level: `L0`
- Final level: `L2` *(expected: L2 — ✓)*
- Dispatch source: `user-bump` *(expected: user-bump — ✓)*
- Creativity: `standard`
- Clamp reason: `none`
- Override fragment: `LDD++`

**Dispatch header emitted:**
```
Dispatched: user-bump L2 (scorer proposed L0, bump: LDD++)
```

**Skill floor invoked (minimum):**
- `e2e-driven-iteration`
- `reproducibility-first`
- `root-cause-by-layer`
- `dialectical-reasoning`
- `loss-backprop-lens`
- `docs-as-definition-of-done`

**Notes:** Scorer would say L0; user explicitly asked for +2.


### override-max-on-simple — ✅ PASS

**Category:** override
**Prompt:**
> LDD=max: fix the typo in README.md line 12

**Scorer output:**
- Raw score: `-8`
- Signals fired: `explicit-bugfix=-5, single-file=-3`
- Auto-level: `L0`
- Final level: `L4` *(expected: L4 — ✓)*
- Dispatch source: `user-bump` *(expected: user-bump — ✓)*
- Creativity: `standard`
- Clamp reason: `none`
- Override fragment: `LDD=max`

**Dispatch header emitted:**
```
Dispatched: user-bump L4 (scorer proposed L0, bump: LDD=max)
mode: architect, creativity: standard
```

**Skill floor invoked (minimum):**
- `e2e-driven-iteration`
- `reproducibility-first`
- `root-cause-by-layer`
- `dialectical-reasoning`
- `loss-backprop-lens`
- `docs-as-definition-of-done`
- `architect-mode (inventive, ack-gated)`
- `drift-detection`
- `iterative-refinement`
- `method-evolution`
- `dialectical-cot`
- `define-metric`

**Notes:** Clamp-to-L4 regardless of scorer.


### override-natural-language — ✅ PASS

**Category:** override
**Prompt:**
> take your time and think hard about this: rename the variable `foo` to `bar` in packages/awp-core/src/awp/cli.py

**Scorer output:**
- Raw score: `-3`
- Signals fired: `single-file=-3`
- Auto-level: `L1`
- Final level: `L2` *(expected: L1 or L2 — ✓)*
- Dispatch source: `user-bump` *(expected: user-bump — ✓)*
- Creativity: `standard`
- Clamp reason: `none`
- Override fragment: `"take your time" + "think hard"`

**Dispatch header emitted:**
```
Dispatched: user-bump L2 (scorer proposed L1, bump: "take your time" + "think hard")
```

**Skill floor invoked (minimum):**
- `e2e-driven-iteration`
- `reproducibility-first`
- `root-cause-by-layer`
- `dialectical-reasoning`
- `loss-backprop-lens`
- `docs-as-definition-of-done`

**Notes:** "take your time" + "think hard" dedup to +1 → L2 (L1 also acceptable).


### override-down-warning — ✅ PASS

**Category:** override
**Prompt:**
> LDD[level=L0]: we need to add a new critique gate for repair-fixpoint detection between the existing critique and deliverable_presence gates in the delegation loop; it should hook into the same R35 mechanism

**Scorer output:**
- Raw score: `6`
- Signals fired: `contract-rule-hit=+2, cross-layer=+2, layer-crossings=+2`
- Auto-level: `L3`
- Final level: `L0` *(expected: L0 — ✓)*
- Dispatch source: `user-override-down` *(expected: user-override-down — ✓)*
- Creativity: `standard`
- Clamp reason: `none`
- Override fragment: `LDD[level=L0]:`

**Dispatch header emitted:**
```
Dispatched: user-override-down L0 (scorer proposed L3). User accepts loss risk.
```

**Skill floor invoked (minimum):**
- `e2e-driven-iteration`

**Notes:** User explicit L0 on a cross-layer task → "loss risk" warning fires.


### stress-inventive-implicit-ack — ✅ PASS

**Category:** stress
**Prompt:**
> design a novel consistency protocol for a multi-master KV store where no known pattern fits our partial-ordering requirements; we want to prototype experimental mechanisms and research the design space

**Scorer output:**
- Raw score: `7`
- Signals fired: `greenfield=+3, ambiguous=+2, components>=3=+2`
- Auto-level: `L3`
- Final level: `L3` *(expected: L3 or L4 — ✓)*
- Dispatch source: `auto-level` *(expected: auto-level — ✓)*
- Creativity: `inventive` (implicit ack from ≥2 inventive cues in prompt) *(expected: inventive — ✓)*
- Clamp reason: `none`
- Override fragment: `none`

**Dispatch header emitted:**
```
Dispatched: auto-level L3 (signals: greenfield=+3, ambiguous=+2)
mode: architect, creativity: inventive (implicit ack from ≥2 inventive cues in prompt)
```

**Skill floor invoked (minimum):**
- `e2e-driven-iteration`
- `reproducibility-first`
- `root-cause-by-layer`
- `dialectical-reasoning`
- `loss-backprop-lens`
- `docs-as-definition-of-done`
- `architect-mode (standard)`
- `drift-detection`
- `iterative-refinement`

**Notes:** ≥2 inventive cues + ≥100 chars → implicit ack path. Both L3 and L4 are GREEN: L4 if raw-score signals push the bucket there, L3 + creativity=inventive otherwise (same architect-mode + inventive loss function, smaller budget). This encodes orthogonality of level (rigor) and creativity (objective).


### stress-zero-signal-baseline — ✅ PASS

**Category:** stress
**Prompt:**
> hello, can you help me out with this

**Scorer output:**
- Raw score: `0`
- Signals fired: `(none)`
- Auto-level: `L2`
- Final level: `L2` *(expected: L2 — ✓)*
- Dispatch source: `auto-level` *(expected: auto-level — ✓)*
- Creativity: `standard`
- Clamp reason: `none`
- Override fragment: `none`

**Dispatch header emitted:**
```
Dispatched: auto-level L2 (signals: )
```

**Skill floor invoked (minimum):**
- `e2e-driven-iteration`
- `reproducibility-first`
- `root-cause-by-layer`
- `dialectical-reasoning`
- `loss-backprop-lens`
- `docs-as-definition-of-done`

**Notes:** Zero-signal chit-chat → baseline L2, not L0. Encodes "lieber schlau als zu dumm".


### stress-L4-clamp-on-high-score-standard — ✅ PASS

**Category:** stress
**Prompt:**
> design a new service integration across the orchestration layer and the observability layer, covering the runner, scorer, and manager; wire it into the delegation loop and honor R17

**Scorer output:**
- Raw score: `9`
- Signals fired: `greenfield=+3, contract-rule-hit=+2, cross-layer=+2, layer-crossings=+2`
- Auto-level: `L3`
- Final level: `L3` *(expected: L3 — ✓)*
- Dispatch source: `auto-level` *(expected: auto-level — ✓)*
- Creativity: `standard` *(expected: standard — ✓)*
- Clamp reason: `clamped from L4 (creativity=standard)`
- Override fragment: `none`

**Dispatch header emitted:**
```
Dispatched: auto-level L3 (signals: greenfield=+3, contract-rule-hit=+2) [clamped from L4 (creativity=standard)]
mode: architect, creativity: standard
```

**Skill floor invoked (minimum):**
- `e2e-driven-iteration`
- `reproducibility-first`
- `root-cause-by-layer`
- `dialectical-reasoning`
- `loss-backprop-lens`
- `docs-as-definition-of-done`
- `architect-mode (standard)`
- `drift-detection`
- `iterative-refinement`

**Notes:** Raw score ≥ 8 (L4 bucket) BUT no inventive cues → creativity-clamp fires back to L3.
