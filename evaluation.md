# Evaluation — Loss and E2E for LDD

This document defines what **loss** and **E2E** mean for this skills bundle. If a reviewer asks "does LDD work?", the answer is a number computed by the method below, not a qualitative impression.

## What we are evaluating

The bundle's job is to **change agent behavior** under pressure — to produce fewer symptom patches, less overfitting, more documented diagnoses, synced docs, dialectical recommendations. The evaluation must measure behavior change, not skill prose.

## Loss (per skill, per scenario)

For each skill `s` and pressure scenario `t`, run the agent **with** and **without** the skill on the scenario and score the response against a rubric `R_s` of binary items:

```
loss(s, t) = Σ rubric_violations(response, R_s)
Δloss(s, t) = loss_baseline(s, t) − loss_with_skill(s, t)
```

`Δloss > 0` means the skill reduced violations. `Δloss ≤ 0` means the skill did not help (or hurt) on that scenario. A skill that averages `Δloss ≤ 0` across its scenarios is **broken** — it must be fixed or deleted.

### Rubric per skill

Each rubric is a small fixed set of checks encoded in [`tests/fixtures/`](./tests/fixtures/). Rubric items are binary (0 = satisfied, 1 = violated).

**`root-cause-by-layer`** (rubric: `R_rcbl`)
1. Symptom quoted verbatim? *(violated if paraphrased or summarized)*
2. Mechanism named (function / branch / state transition)?
3. Contract named (explicit: whose, what shape, documented-or-not)?
4. Structural origin named (architectural layer + inside-vs-across-boundary)?
5. Conceptual origin named (design concept being misapplied)?
6. Fix proposed at the named structural layer (not higher, not lower)?
7. No `try/except` / `hasattr`-shim / widened regex / retry / `xfail` in the proposed fix?
8. No "clean up later" / "tech debt" / "interim fix" language?

**`loss-backprop-lens`** (rubric: `R_lbl`)
1. Signal-vs-noise explicit for the given data (one sample → reproduce; unambiguous log → proceed)?
2. Pattern detected (one-off vs recurring) when the commit log / history shows a pattern?
3. Step size named (local tweak vs architectural edit) matching the loss pattern?
4. Generalization checked (sibling inputs, unseen tests)?
5. Regularization named (which contract / boundary / invariant is respected)?
6. No retry/cache/"flaky LLM" as the primary response?

**`dialectical-reasoning`** (rubric: `R_dr`)
1. Thesis explicitly labeled or clearly stated, steel-manned?
2. Antithesis explicitly labeled, attacks ≥ 3 vectors (hidden assumptions, edge cases, contracts, second-order, framing, asymmetric risk, who-disagrees)?
3. Synthesis strictly stronger than thesis (narrower, more honest, or replaced)?
4. No one-sided "obviously" / "no-brainer" framing?
5. Load-bearing assumption named?

**`docs-as-definition-of-done`** (rubric: `R_ddod`)
1. All doc hits identified (via grep/scan of the given files)?
2. All doc hits actually edited in the proposed commit?
3. One logical commit proposed (code + tests + docs together, not split)?
4. No "follow-up PR" / "TODO update docs" language?
5. Actively-false statements prioritized over merely-incomplete ones?

**`loop-driven-engineering`** (rubric: `R_lde`)
1. Loop structure explicit (numbered iterations, K_MAX referenced)?
2. Test pyramid respected (don't escalate to E2E when tier-1 would catch it)?
3. Sub-skill dispatch — ≥ 2 sub-skills invoked at correct moments?
4. K_MAX escalation plan present and has the required shape (what tried / what failed / layer-4-5 diagnosis / step-size / explicit ask)?
5. Close with docs-as-DoD referenced?
6. Correct loop (inner vs refinement vs outer) chosen for the task?

**`reproducibility-first`** (rubric: `R_rf`)
1. Original observation logged verbatim (error, log, environment)?
2. Branch explicitly chosen (A = reproduce, B = unambiguous-log shortcut) with justification?
3. If Branch A: ≥ 2 additional runs executed before proposing an edit?
4. If Branch B: all three criteria (deterministic cause, complete explanation, contract match) explicitly checked?
5. No retry loop / `@flaky` / defensive `try/except` proposed as a first response to a single failure?
6. If transient (2/2 pass): no code edit proposed; incident logged and closed?

**`e2e-driven-iteration`** (rubric: `R_edi`)
1. E2E run at the *start* of each iteration (not only at the end)?
2. Loss per iteration captured as a concrete number / list of failing items?
3. Δloss compared to previous iteration and interpreted (down = progress, zero = rethink, up = revert)?
4. Pyramid respected (cheap tier used when it can reproduce, E2E only when warranted)?
5. Multiple edits batched into one iteration without re-running the E2E per edit? (violation)
6. Close gated on E2E green AND regularizers (contracts / docs) honored?

**`iterative-refinement`** (rubric: `R_ir`)
1. Scope verified: deliverable complete, "good-enough-not-great," re-run would waste?
2. Gradient built from concrete sources (named defects, gate rejections, eval deltas) — not "make it better"?
3. Budget explicit (max iterations ≤ 10, halving per iter, wall-time cap)?
4. Stop conditions named (regression / plateau / wall-time / empty-gradient)?
5. Winning iteration preserved (not just last iteration) on regression?
6. Did the skill get invoked when the right loop was refinement (not inner loop, not re-plan)?

**`method-evolution`** (rubric: `R_me`)
1. Pattern observed across ≥ 3 distinct tasks before invoking (not 1 or 2)?
2. Proposed change is ONE thing (not a rewrite)?
3. Task suite used to measure `Δloss_method`?
4. `Δloss_method > 0` on motivating case AND `≥ 0` on all others, or rollback?
5. Commit message has the canonical shape (pattern / change / Δloss / regressions)?
6. No moving-target loss (rubric edited to fit current code without Δloss justification)?

**`drift-detection`** (rubric: `R_dd`)
1. Scan run on a periodic cadence (not reactively when something broke)?
2. All seven indicators checked?
3. Report produced as a fixable list, not a "health score"?
4. Each finding triaged (immediate fix vs method-evolution candidate)?
5. Scan history logged (even when report is short)?
6. Trend over time tracked (drift shrinking / stable / growing)?

**`architect-mode`** — three rubric variants, one per `creativity` level. Applies only when `mode=architect` is active. See [`skills/architect-mode/SKILL.md`](./skills/architect-mode/SKILL.md) § Creativity levels for the full per-level spec.

### `R_arch_standard` (default — 10 items)

1. All stated requirements covered in the Phase 1 constraint table?
2. Uncertainties in the user's ask named, not silently invented?
3. ≥ 3 concrete, scope-bounding non-goals declared (Phase 2)?
4. Exactly 3 candidates on a load-bearing axis, not cosmetic variants (Phase 3)?
5. Scoring table explicit (rows × 6 dimensions), not narrative (Phase 4)?
6. Real antithesis against the winning candidate (not a strawman) (Phase 4)?
7. Architecture doc has all 9 subsections per Phase 5 of the skill?
8. Scaffold compiles / imports cleanly (not pseudocode)?
9. ≥ 1 failing test per component in the scaffold?
10. Measurable success metric per requirement, with numeric target?

### `R_arch_conservative` (11 items — standard 10 plus #11)

Same 10 items as `R_arch_standard`, with modified scoring weights in Phase 4 (team-familiarity 2×, evolution-paths 0.5×), *plus*:

11. **Novelty penalty.** Every component scores on an internal novelty scale (0 = in existing codebase, 1 = new-but-standard-for-domain, 2 = new-for-team, 3+ = new-for-industry). Target: all components ≤ 1. Any component > 1 is a rubric violation. This is the regularizer term that turns `L = rubric_violations` into `L = rubric_violations + λ · novelty_penalty`.

Phase 3 candidates must all be patterns with ≥ 5 years of track record in the user's domain. Phase 5 scaffold must use the stack already present in the user's codebase (no new language / framework / database).

### `R_arch_inventive` (7 items — relaxed standard + invention-specific)

Items 1, 2, 3, 4 retained (may score 1/1 for items 1–2 without failure if a "known unknowns" section is explicitly present). Items 5–8 of `R_arch_standard` are **replaced** by:

- **#I1.** Differentiation from prior art: a `PRIOR_ART.md` or equivalent section names what the design deliberately rejects vs. existing solutions and why. Not just "ours is different" — the rejection has to cite specific prior work.
- **#I2.** Experiment validation path: an `EXPERIMENT.md` or equivalent describes how the invention will be validated before production — what measurement, what threshold, what counts as "it works."
- **#I3.** Fallback-to-baseline path: the `standard`-equivalent baseline design (the one that would ship if the invention fails) is named and accessible. Invention is opt-in on top of a safe fallback, never a bet-the-business exclusive path.

Plus items 9, 10 retained as-is: failing tests (now for the prototype not production code) + measurable success metrics per requirement.

**Inventive total: 7 items.** Lower bar on coverage, higher bar on novelty honesty. Cannot ship at > 1 violation without explicit acknowledgment in a "known research debts" section.

### Aggregate target

Per [`tests/README.md`](./tests/README.md#current-measurements), the measured Δloss for `architect-mode` is computed on `R_arch_standard` (the default). Variant runs (`conservative`, `inventive`) have been **specified but not yet measured**; when measured, each should produce its own per-variant Δloss. Aggregate bundle Δloss uses only `R_arch_standard` until variant baselines are captured (documented adopter task in [`GAPS.md`](./GAPS.md)).

## Loss (bundle-wide)

Average Δloss across skills, weighted by the number of pressure scenarios per skill:

```
Δloss_bundle = Σ_s (Σ_t Δloss(s, t)) / (Σ_s |scenarios(s)|)
```

**Target** (v0.3.2, normalized): `Δloss_bundle ≥ 0.30` — on average, each skill removes at least 30 % of the rubric violations that appear without it. This replaces the v0.3.1 absolute target (`≥ 2.0 mean violations removed`) which was not comparable across skills with different rubric-maxes.

**Current measured value: `Δloss_bundle = 0.561`** across all 11 skills — target met with margin. The raw absolute mean (v0.3.1 form) was 3.91; dividing by each skill's rubric-max and averaging gives the normalized 0.561 — which is now the canonical aggregate.

Per-skill normalized `Δloss = violations_removed / rubric_max` ranges from **0.250** (`loop-driven-engineering`) to **1.000** (`architect-mode` standard). `docs-as-definition-of-done` and `architect-mode` were both captured via direct API (see [`scripts/capture-clean-baseline.py`](./scripts/capture-clean-baseline.py)) which sidesteps subagent-harness contamination. `architect-mode` shows the largest effect size in the bundle (normalized +1.000, 100 % of rubric items flipped). See [`tests/README.md`](./tests/README.md#current-measurements) for per-skill numbers and caveats.

### Why normalized is the canonical form

- **Cross-skill comparability.** Skills have different rubric-maxes: `e2e-driven-iteration` has 5 items, `architect-mode` has 10. `Δloss = +3 (e2e) vs Δloss = +6 (arch)` was apples-to-oranges; `0.60 vs 0.60` makes them immediately comparable.
- **Single aggregate number.** Per-skill absolute Δloss + bundle-wide absolute mean + bundle-wide relative mean was three overlapping numbers. Normalized per-skill gives one unified scale.
- **Actionable at the raw level.** Every normalized value is always shown with its raw `(N/max violations)` denominator in parens — the user still sees "3 of 8 items remain" for concrete fix-prioritization.

## E2E — what a real end-to-end run looks like

A proper E2E is **not** "the agent wrote the right text in response to a prompt." It is:

1. **Fresh project, fresh agent.** New directory, no `CLAUDE.md`, no prior conversation state.
2. **Unseen multi-step task.** A task not present in any skill's example section. Must require ≥ 2 of the 10 skills to solve well.
3. **Real tool use.** The agent must actually edit files, run tests, inspect diffs — not just describe what it would do.
4. **Artifacts persisted.** The run produces a directory: transcript, proposed diff, test output, any new files. These are inspected post-hoc.
5. **Rubric scored against the artifacts.** Not against the transcript alone. Did the diff actually land at the right layer? Did docs actually get updated? Did the commit message reflect LDD reasoning?
6. **Terminal status.** Exactly one of `{complete, partial, failed, aborted}` — did the agent close the loop?

See [`tests/e2e/README.md`](./tests/e2e/README.md) for the reference E2E scenario and runner skeleton.

## Test pyramid (cheap → expensive)

| Tier | What | Frequency |
|---|---|---|
| 0 | Markdown lint + YAML frontmatter validation | Every commit |
| 1 | Rubric smoke test on 1 fixture per skill (text-level compliance) | Every commit |
| 2 | Full rubric across all fixtures (per-skill Δloss) | Every release candidate |
| 3 | Cross-skill integration: scenarios requiring 2+ skills | Every release candidate |
| 4 | Live install in Claude Code / Codex / Gemini CLI, real multi-step task | Manual before tagging |
| 5 | Real production use in an unrelated repo, measured over ≥ 2 weeks | Manual quarterly |

Anything below tier 4 is **training loss**. Tiers 4–5 are **test loss** — the only honest measure of whether the bundle generalizes.

## Known limitations of the current evaluation

See [`GAPS.md`](./GAPS.md). Short version:

- Baselines captured in an environment with an instrumented `CLAUDE.md` loaded may be biased toward skill-like behavior even without the skill. Mitigation: the fixtures include explicit "context reset" instructions, but compliance is not perfect.
- Tier 4 (live install) has not been run by the author; waiting on the first real user.
- Tier 5 (production) requires time, not code.
- Rubric items are agent-scored by a reviewer reading the response; no automated grader yet. Known tradeoff — automated scoring tends to regress to surface-string matching, which is exactly the overfit the bundle teaches against.
