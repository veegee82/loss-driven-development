# LDD Thinking Levels — Design

> Produced in architect-mode (standard). The task is greenfield (new scoring layer), cross-layer (scorer + skills + docs + tests), and the auto-dispatch signals for architect-mode fire clearly — so the doc follows the 5-phase protocol from `skills/architect-mode/SKILL.md`.

## 0. Problem statement

Today LDD has a **binary deliberation dial**: `mode = reactive | architect`. Between "fix typo" and "design a new module" lies 95 % of all real tasks, all collapsed into `reactive`. Two symptoms follow:

- **Over-deliberation on simple tasks.** A one-line fix runs through the same 5-iteration `loop-driven-engineering` default as a multi-file refactor.
- **Under-deliberation on complex reactive tasks.** Cross-layer bugs whose user message lacks any architect trigger phrase silently stay reactive, get a symptom-patch, and resurface.

The user also requires that **zero configuration is expected of them** — they should be able to type a task, nothing else, and still get the right level of rigor. The agent is responsible for picking it; the user is only responsible for overriding when they disagree.

**Design guidance from the user, verbatim** (driver for every Phase-2 non-goal and every Phase-4 tie-breaker):

> "lieber ein klein wenig schlau als zu dumm."

Translation: asymmetric loss. A task run at one level too high wastes tokens. A task run at one level too low produces a silent symptom-patch that costs a full regression cycle later. The second is strictly worse, so **ties break upward**.

## 1. Phase 1 — Constraints

Hard constraints (cannot be relaxed):

1. **No new user-facing hyperparameter.** `hyperparameters.md §"What is NOT exposed"` is load-bearing anti-drift policy. The level is a **derived value** from existing knobs + task signals, not a new knob.
2. **Discrete levels only.** No `L2.5`, no integer dial. Same reasoning as `creativity` in `architect-mode/SKILL.md` §"Cannot be integer-tuned".
3. **Zero-config default.** A user who types a task and knows nothing about LDD gets a sensible level without editing `.ldd/config.yaml`, without setting any flag, without knowing any trigger phrase. The agent runs the scorer by default.
4. **Deterministic scorer.** The scorer is a pure function of the task text + (optionally) repo-lookup signals. No LLM call. Any LLM-based intelligence goes into the *work*, not into deciding how much work to do. This keeps the dispatch decision cheap, reproducible, and traceable.
5. **Trivial user override.** A user who disagrees must be able to override with one inline token, with no documentation lookup.
6. **Upward bias on ties.** Direct encoding of the user's rule above. When two levels score equally, pick the higher.
7. **`.ldd/trace.log` captures level + dispatch source** — analog to the existing `Dispatched: auto (...)` line for architect-mode. Silent level-selection is a trace-integrity violation.
8. **Method-loop is the correction mechanism, not the agent's self-judgment.** If the agent systematically picks too low, `method-evolution` must be able to detect it and propose a scorer-weight adjustment. The agent does not "learn to pick higher" from one run — the outer loop does, from N runs.

Soft constraints (preferred but bendable):

- Levels should map onto the four already-exposed knobs plus a skill allowlist, without introducing new state.
- The scorer should reuse as much of the existing 6-signal architect-mode scorer as possible.

## 2. Phase 2 — Non-goals

Explicitly out of scope for this design (and for the initial implementation):

1. **Continuous creativity tuning.** `creativity` stays three-valued (`conservative` | `standard` | `inventive`) inside architect-mode. Levels do **not** replace it.
2. **Learned scoring.** No LLM-as-scorer, no ML model. Deterministic table only.
3. **Multi-level runs.** A single task runs at exactly one level. No mid-run escalation ("started at L1, bumped to L3 when it got hard"). Escalation mid-run is the same anti-pattern as `K_MAX++ because this task is complex` in `method-evolution/SKILL.md`.
4. **Level as an exposed hyperparameter.** `ldd-set level=L3` is **explicitly not added.** Overriding is per-task, inline in the user message. This preserves the "4 core + 1 sub" knob count.
5. **Replacing `mode`.** `mode: reactive | architect` remains the internal flag; `level` is a higher-level summary that *also* sets `mode` among other things.
6. **Retroactive grading of past runs.** Level-selection is forward-only; we do not rescore `.ldd/trace.log` history to check whether past runs "should have been" L3.

## 3. Phase 3 — Candidate designs

### Candidate A — Thin preset mapper on top of existing scorer

Keep the existing 6-signal architect-mode scorer unchanged. Add a second, shallow function `score_to_level: score → L{0..4}` that also reads the same signals and buckets them into 5 presets.

```
Scorer (unchanged 6 signals) ──┬── architect-mode gate (score ≥ 4)
                                └── level bucket (L0..L4)
```

Each level maps to a preset over existing knobs:

| Level | k_max | reproduce_runs | mode | Skills in allowlist |
|---|---|---|---|---|
| L0 reflex | 2 | 1 | reactive | `e2e-driven-iteration` |
| L1 diagnostic | 3 | 2 | reactive | + `reproducibility-first`, `root-cause-by-layer` |
| L2 deliberate | 5 (default) | 2 | reactive | + `dialectical-reasoning`, `loss-backprop-lens` |
| L3 structural | 5 | 2 | architect/standard | + `docs-as-definition-of-done`, `drift-detection` |
| L4 method | 8 | 3 | architect/inventive (ack-gated) | + `method-evolution`, `dialectical-cot` |

Pros: minimal new surface, reuses everything. Cons: the same 6-signal vector drives a 5-value decision — low resolution. A typo fix (score 0) and a layer-boundary refactor (score 3) both fall in the 0–3 band and both land at L1, even though they deserve L0 and L2.

### Candidate B — Extend scorer with 3 level-specific signals

Keep the 6-signal architect-mode scorer for its binary gate. Add 3 more signals specifically calibrated for level discrimination — `layer-crossings`, `contract-rule-hits` (references to R-rules, contracts, invariants), `unknown-file-territory` (touched paths not seen in recent history).

```
Scorer (9 signals now)
   ├── architect gate (sum of the original 6 ≥ 4)
   └── level bucket (weighted sum of all 9)
```

Pros: resolution matches the level granularity. Cons: 9-signal table is harder to justify under `hyperparameters.md`'s anti-knob-inflation stance. Each new signal is a small Moving-Target-Loss surface.

### Candidate C — Two-stage scorer (coarse + refine)

Stage 1: a rough 3-signal classifier (is-this-mechanical / is-this-cross-layer / is-this-greenfield) buckets the task into `{low, mid, high}`. Stage 2: within each bucket, a targeted 2–3-signal refiner picks the specific level inside.

Pros: cleanest conceptual structure; each stage's signals are justified by what they discriminate. Cons: two lookup tables instead of one, and the coarse classifier is a new artifact that duplicates some of the existing scorer's job.

## 4. Phase 4 — Scoring + Dialectical

Rubric (6 dimensions, equal-weight per `architect-mode/SKILL.md` §Phase 4):

| Dimension | A (thin mapper) | B (9-signal) | C (two-stage) |
|---|---|---|---|
| 1. Anti-knob-inflation (fidelity to `hyperparameters.md`) | **✓** reuses existing signals | ~ adds 3 signals | ~ adds a classifier stage |
| 2. Resolution matches 5 levels | ✗ collapses low scores | **✓** | **✓** |
| 3. Implementation cost | **✓ lowest** | ~ | ~ highest |
| 4. Trace-integrity / explainability | **✓** same echo surface | ✓ more signals to echo | ~ two-stage echo harder to read |
| 5. Method-evolution hook-ability | ✓ | **✓** (more weights to tune) | ✓ |
| 6. Failure mode under asymmetric-loss bias | ✗ biases **downward** on low scores (collapse band is at bottom) | **✓** | ✓ |

Raw scores (lower = better): A = 2, B = 2, C = 3.

**Tie between A and B.** Break by applying the user's `lieber schlau als dumm` rule: A's biggest failure mode is that it systematically underscores mechanical-looking tasks because its 6-signal vector wasn't designed to discriminate *inside* the reactive band. A reactive task with a hidden cross-layer defect scores 0 on all 6 signals and lands at L0 — the exact failure mode the user asked us to avoid.

**Dialectical check on the winner (B):**

- *Thesis:* "9 signals beats 6 because the extra 3 are calibrated for the reactive-band discrimination problem."
- *Antithesis:* "9 signals is exactly the knob-inflation `hyperparameters.md` forbids. The anti-pattern is adding signals until the scorer ranks this one task correctly — that's moving-target-loss at the scorer layer."
- *Synthesis:* The 3 new signals are **not** tuned on individual tasks. They're chosen for what they *structurally* discriminate — layer crossings, R-rule hits, unknown paths — and their weights are fixed at integer values. Method-evolution is the **only** channel allowed to change them, via its existing rollback-on-regression protocol. If a new weight regresses mean loss, the halving rule from `method-evolution/SKILL.md` applies. That converts "knob inflation" from a persistent risk into a bounded, loss-gated one.

**Winner: Candidate B.** Cost accepted: 3 extra signals, fully documented in `docs/ldd/thinking-levels.md`, byte-equal to the scorer table.

**Phase-4 tie-break note for future maintainers:** If a new candidate ties B, the `lieber schlau als dumm` rule breaks it toward the candidate whose failure mode leans *upward* (more deliberation than needed), not downward (less).

## 5. Phase 5 — Deliverable

### 5.1 The 5 levels (canonical spec)

Same table as Candidate A, retained verbatim — this is the authoritative version.

| Level | Name | k_max | reproduce_runs | mode | max_refinement_iterations | Skills actively invoked |
|---|---|---|---|---|---|---|
| **L0** | reflex | 2 | 1 | reactive | 1 | `e2e-driven-iteration` |
| **L1** | diagnostic | 3 | 2 | reactive | 2 | + `reproducibility-first`, `root-cause-by-layer` |
| **L2** | deliberate | 5 | 2 | reactive | 3 | + `dialectical-reasoning`, `loss-backprop-lens`, `docs-as-definition-of-done` (commit-time) |
| **L3** | structural | 5 | 2 | architect/standard | 3 | + `architect-mode` (standard), `drift-detection`, `iterative-refinement` |
| **L4** | method | 8 | 3 | architect/inventive (ack-gated) | 5 | + `method-evolution`, `dialectical-cot`, `define-metric` |

**Allowlist semantics:** the skill list at each level is a **floor, not a ceiling.** A task at L2 that turns out to need `drift-detection` can still invoke it. A task at L3 is **not allowed to skip** `architect-mode`. This protects against downward drift during execution.

### 5.2 The 9-signal scorer

Six signals are retained from the existing architect-mode scorer (`using-ldd/SKILL.md` § Auto-dispatch for architect-mode):

| Signal | Weight |
|---|---|
| Greenfield | +3 |
| ≥ 3 new components | +2 |
| Cross-layer scope | +2 |
| Ambiguous requirements | +2 |
| Explicit bug-fix | −5 |
| Single-file known-solution | −3 |

Three new signals are added for level discrimination:

| Signal | Weight | Detect via |
|---|---|---|
| Layer crossings (touches ≥ 2 named layers / packages / modules) | +2 | Package / directory names in the task description; presence of import-graph-crossing verbs ("wire", "integrate", "bridge") |
| Contract / R-rule hit (names an invariant, R-rule, schema, contract, API) | +2 | Literal patterns: `R\d+`, "schema", "contract", "API surface", "invariant", "must always" |
| Unknown-file territory (paths or concepts not seen in `.ldd/trace.log` history of the last 20 runs) | +1 | Lookup against the trace log; if log is empty, this signal is +0 |

Score-to-level bucketing (**upward-biased**, reflecting constraint 6; Phase-1-tuned):

| Summed score | Level |
|---|---|
| score ≤ −7 (strong bug-fix **and** single-file, nothing else) | **L0** |
| −6 ≤ score ≤ −2 | **L1** |
| −1 ≤ score ≤ 3 | **L2** (default baseline if no signals fire either way — sits here, not L0) |
| 4 ≤ score ≤ 7 | **L3** |
| score ≥ 8 | **L4** |

The L0 bucket is deliberately narrow. It is only reached when BOTH the strongest negative signals (`explicit-bugfix:-5` AND `single-file:-3` = −8) fire and no ambiguity or contract signal contradicts them. A task with any positive signal on top (e.g. `ambiguous:+2`) falls into L1 — the correct home for "failing test, investigation required". This is the structural encoding of the `lieber schlau als zu dumm` rule.

**Baseline is L2, not L0.** If a task produces zero signals (empty task text, pure chit-chat, or ambiguous), the agent lands at L2. This is the structural realization of "lieber schlau als zu dumm". L0/L1 require affirmative negative signals; they don't happen by absence.

**Tie-break:** when the raw score sits on a boundary (e.g. score = 3, between L2 and L3), pick the higher. This is not a separate rule — the boundary tables above are already written with closed-interval upper bounds to encode this.

**Creativity-clamp rule (L3 ↔ L4 boundary):** When the raw score falls in the L4 bucket (`≥ 7`) BUT the creativity inferrer returns `standard` (no `"novel"` / `"research"` / `"no known pattern"` / `"prototype"` cues), the level is clamped to L3. Reason: L4's preset mandates `creativity=inventive (ack-gated)`; running L4 with `standard` would mix loss functions (violates `architect-mode/SKILL.md` §"Cannot switch mid-task"). The clamp is one-directional only — it cannot promote L3 → L4 when creativity would be inventive. The dispatch header must show `"clamped from L4 (creativity=standard)"` when this rule fires.

### 5.2.1 Weights and boundaries are Phase-1 tuning targets

The 9 signal weights and the score-to-level bucket boundaries above are an **initial proposal**. The **contract** is the fixture suite under `tests/fixtures/thinking-levels/` — every scenario's `expected level` is a hard target.

Phase 1's job is to:
1. Implement the scorer with the initial weights / boundaries above.
2. Run the full fixture suite.
3. For each scenario where the scorer's level ≠ expected level, adjust weights or boundaries to close the gap.
4. Respect the asymmetric-loss rule during tuning: if a tuning choice could either bias a boundary scenario upward or downward, bias upward.
5. Log every tuning change to `.ldd/trace.log` so method-evolution has historical context for any later re-tuning.

The weights published in the final `using-ldd/SKILL.md` after Phase 1 ends MAY differ from the table above. The docs-as-DoD gate ensures the doc and the code agree at commit time.

### 5.3 User-facing interface

**Zero-config path (the default 95 % of users will ever touch):**

The user types a task. The agent runs the scorer, picks a level, and echoes one line in the trace header:

```
Dispatched: auto-level L2 (signals: ambiguous=+2, layer-crossings=+2)
```

Nothing else is required. The user need not know the scorer exists.

**User override — natural language (no syntax required):**

These phrases in the user's message are recognized as "bump up" signals. They are additive to the scorer output:

| Phrase fragment (case-insensitive) | Effect |
|---|---|
| "think hard", "denk gründlich", "careful", "take your time", "sorgfältig" | +1 level |
| "really think", "very careful", "ultra-careful", "maximum rigor" | +2 levels |
| "full LDD", "use everything", "maximum deliberation", "volle Kanne" | clamp to L4 |

**User override — explicit syntax (for users who know LDD):**

```
LDD+: <task>          → auto-level + 1
LDD++: <task>         → auto-level + 2
LDD=max: <task>       → L4 directly
LDD[level=L3]: <task> → explicit L3, overrides scorer
```

Precedence (higher wins):

```
1. LDD[level=Lx]:   explicit number          ← highest
2. LDD=max:         literal max
3. LDD++: / LDD+:   relative bump
4. Natural-language bump phrases
5. Auto-scorer output                         ← lowest
```

**Override is never downward in practice.** The user can theoretically type `LDD[level=L0]:` to force a low level. The agent honors it but emits a trace warning: `Dispatched: user-override L0 (scorer proposed L2). User accepts loss risk.` — so that if a regression follows, the trace shows the cause.

### 5.4 Trace integrity

Mandatory echo at the start of every non-trivial task, same format as the existing architect-mode echo:

```
Dispatched: <source> L<n> (signals: <top-2-by-|weight|>)
```

Where `<source>` is one of:

- `auto-level` — pure scorer output
- `user-explicit` — `LDD[level=Lx]:` flag
- `user-bump` — `LDD+`, `LDD++`, `LDD=max`, or natural-language phrase
- `user-override-down` — user forced a lower level than scorer proposed (rare; logs a warning)

The trace line is the contract between the agent's decision and the user's ability to override it cheaply. Without it, the outer loop (method-evolution) cannot tell whether a regressed run was caused by a bad scorer weight or a bad user override.

### 5.5 Feedback loop (method-evolution integration)

`.ldd/trace.log` entries gain three fields:

| Field | Type | Written when |
|---|---|---|
| `level_chosen` | `L0..L4` | At dispatch time |
| `dispatch_source` | enum | At dispatch time |
| `loss_final` | float | At task completion (reuse existing loss mechanism) |

`method-evolution/SKILL.md` gets one new trigger rule:

> If across the last 20 runs there exist ≥ 3 runs where `dispatch_source == auto-level` AND `level_chosen ≤ L1` AND `loss_final > median(loss)` AND a downstream regression was filed (detected via subsequent run with same file-set and `regression_followed = true`): propose a +1 adjustment to the weight of the signal most correlated with the missed cases. Apply the standard method-evolution rollback-on-regression protocol.

This is the only closed-loop correction in the design. The agent itself does not second-guess its level choice within a run.

### 5.6 User-visible documentation footprint

Touched or created:

| File | Change |
|---|---|
| `docs/ldd/hyperparameters.md` | One added row in §"What is NOT exposed" — `level` is derived, not exposed. No increase in knob count. |
| `docs/ldd/thinking-levels.md` | **New.** Authoritative spec for levels, signals, bucketing, override. |
| `skills/using-ldd/SKILL.md` | § Auto-dispatch rewritten: binary scorer → 9-signal scorer producing a level; architect gate still derived from the same signals. |
| `README.md`, `AGENTS.md` | One-paragraph user-facing summary + the natural-language bump phrases. |
| `tests/fixtures/thinking-levels/` | **New.** Fixtures (see §5.7). |

### 5.7 Test fixtures (Phase 0 deliverable — this spec ships with them)

Under `tests/fixtures/thinking-levels/`:

- `scenario.md` — top-level fixture definition, analog to `architect-mode-auto-dispatch/scenario.md`
- `rubric.md` — 4 binary items per scenario (correct level, correct override respect, trace echo present, not downgraded below scorer for complex tasks)
- `L0-reflex/scenario.md`, `L1-diagnostic/scenario.md`, `L2-deliberate/scenario.md`, `L3-structural/scenario.md`, `L4-method/scenario.md` — one task prompt per level
- `override-up-from-L0/scenario.md` — typo task + `LDD++:` prefix, expected L2
- `override-max-on-simple/scenario.md` — typo task + `LDD=max:`, expected L4
- `override-natural-language/scenario.md` — typo task + "take your time and think hard", expected L1 or L2
- `override-down-warning/scenario.md` — cross-layer task (scorer proposes L3) + `LDD[level=L0]:`, expected L0 but with warning echo

RED / GREEN protocol identical to the architect-mode-auto-dispatch fixture.

## 6. Implementation phase order (post-Phase-0)

Re-stated here so the spec is a complete plan-to-implementation chain:

| Phase | Deliverable | E2E gate |
|---|---|---|
| 0 (this doc) | Spec + all fixtures written | Fixtures exist, rubric written, no code yet. Fixtures must run RED (uninstrumented agent will not produce the trace echo). |
| 1 | `scripts/level_scorer.py` implementing the 9-signal scorer + score-to-level bucketing + unit tests | Unit tests green. Fixtures still RED end-to-end until Phase 2. |
| 2 | `skills/using-ldd/SKILL.md` patched to invoke the scorer on every task and echo `Dispatched: auto-level …`. Natural-language bump phrases and `LDD+` / `LDD++` / `LDD=max` / `LDD[level=]` parsed. | All 9 fixtures (5 level + 4 override) GREEN end-to-end. |
| 3 | `.ldd/trace.log` schema: `level_chosen`, `dispatch_source`, `loss_final`. `method-evolution/SKILL.md` new trigger rule. | Synthetic 20-run history triggers the method-evolution proposal on 3 L1-underscored-regression cases. |
| 4 | `docs/ldd/thinking-levels.md`, `hyperparameters.md` row, `README.md` + `AGENTS.md` paragraph. `scripts/drift-scan.py` rule that the 5-level table in code matches the table in docs. | `drift-scan.py` green. All fixtures from Phase 0 still green. |

## 7. Success criteria (acceptance for the whole initiative)

- **L0 fixture:** completes in ≤ 50 % of the tokens a baseline reactive-default run uses on the same typo task.
- **L3 fixture + L4 fixture:** `dialectical-reasoning` and `architect-mode` are invoked without the user message containing any trigger phrase from the dispatch table.
- **Override-down-warning fixture:** trace shows `user-override-down L0 (scorer proposed L3)` with no silent acceptance.
- **Method-evolution synthetic test:** 3 L1-underscored regressions produce exactly one weight-adjustment proposal, rolled back if it regresses mean loss on the next epoch.
- **Zero-config test:** an empty preamble with a user message `"hello, can you help me fix this?"` lands at L2 (default baseline), not L0.

## 8. Risks and open questions

- **Scorer coverage of non-English task text.** The natural-language bump phrases are a bilingual mix (EN + DE) because the author's convention is German UI / English docs. The fixture table is EN-only; DE phrases are covered but not yet exercised. *Decision:* ship with both, add a DE fixture in Phase 2 if the override doesn't transfer.
- **`unknown-file-territory` signal when trace log is empty.** Defaults to +0, which means new-project first-task can undershoot. *Decision:* accept — new projects have no history to mis-score against, and the L2 baseline catches them.
- **Skill-allowlist enforcement mechanism.** The spec says L3 "is not allowed to skip `architect-mode`", but LDD skills today are dispatched by the agent's own judgment. Enforcement would require either (a) a lint pass over the agent's chosen skills vs. the level's allowlist, or (b) pure convention via SKILL.md. *Decision (for Phase 2):* convention via SKILL.md first; lint pass deferred until a regression proves it's needed. Captured as a deferred item, not hidden.

- **Zero-config tension with the `inventive` ack-gate.** `architect-mode/SKILL.md`'s contract requires a literal `acknowledged` reply before `creativity=inventive` activates. This is load-bearing anti-moving-target-loss protection — the agent is NEVER allowed to select the inventive loss function on its own. But the literal-token requirement collides with the "user needs zero LDD knowledge" design constraint: a newcomer does not know to type `acknowledged`. *Decision (for Phase 2):* two additive relaxations, neither weakens the contract:
  1. **Broaden ack-token recognition** to natural-language affirmatives (bilingual): `"acknowledged"`, `"go"`, `"go ahead"`, `"proceed"`, `"yes"`, `"ja"`, `"los"`, `"okay mach"`, `"passt"`. Reject negatives (`"no"`, `"nein"`, `"stop"`, `"cancel"`) — explicit dissent downgrades to `standard`. Ambiguous replies still require the literal `acknowledged`.
  2. **Implicit ack from the original task prompt** when the user's initial message already contains ≥ 2 inventive cues (`"novel"`, `"research"`, `"prototype"`, `"no known pattern"`, `"invent"`, `"experimental"`, `"paradigm"`) AND ≥ 100 characters of context. The dispatch header must surface this explicitly: `creativity=inventive (implicit ack from ≥2 inventive cues in prompt)`. If the prompt is shorter or has fewer cues, fall back to the explicit ack flow. This preserves the per-task consent requirement while removing the extra round-trip for users who already verbalized the consent in the task itself.

  Neither relaxation allows the AGENT to pick inventive on its own — both still require user-originated consent, just in a broader shape. The moving-target-loss defense (which is "the user is the only authority who can set the loss function") is preserved.
