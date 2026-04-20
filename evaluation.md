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

## Loss (bundle-wide)

Average Δloss across skills, weighted by the number of pressure scenarios per skill:

```
Δloss_bundle = Σ_s (Σ_t Δloss(s, t)) / (Σ_s |scenarios(s)|)
```

Target: `Δloss_bundle ≥ 2.0` (on average, the skill removes two rubric violations per scenario). Current measured value: see [`tests/README.md`](./tests/README.md#current-measurements).

## E2E — what a real end-to-end run looks like

A proper E2E is **not** "the agent wrote the right text in response to a prompt." It is:

1. **Fresh project, fresh agent.** New directory, no `CLAUDE.md`, no prior conversation state.
2. **Unseen multi-step task.** A task not present in any skill's example section. Must require ≥ 2 of the 5 skills to solve well.
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
