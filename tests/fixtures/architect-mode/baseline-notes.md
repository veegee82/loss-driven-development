# Baseline observations — architect-mode

**Status: MEASURED via direct API (2026-04-20, clean).** Raw artifacts in `runs/20260420T190302Z-clean/` (red.md, green.md, score.md).

## Measurement summary

- **Capture method:** direct OpenRouter API call via [`../../../scripts/capture-clean-baseline.py`](../../../scripts/capture-clean-baseline.py). Model `openai/gpt-5-mini`, temperature 0.7. No agent harness, no ambient methodology. Clean baseline.
- RED violations: **10 / 10** — free-form design doc with no constraint table, no non-goals, one candidate instead of three, no scoring, no scaffold, no tests
- GREEN violations: **0 / 10** — all five phases executed, 3 candidates on load-bearing axis, 3×6 scoring table, real antithesis, 9-section doc, working Python scaffold, 4 failing tests, 7 numeric success metrics
- **Δloss = +10**  (**largest effect-size in the bundle**, 100% of rubric items flipped)

## Observed failure mode (RED)

Given the webhook-replay scenario, `openai/gpt-5-mini` without any methodology produces a technically competent, 300-line design doc — but the doc:

- Has no **constraint table** — requirements are mixed into prose paragraphs; the reader cannot audit "did we cover all 8 requirements"
- Invents **defaults silently** (90-day retention, Redis queue) without flagging them as assumptions
- Has **no non-goals section** — scope-creep is already baked in
- Presents **one architecture** (Postgres + S3 + Redis) as the answer without comparison. No alternatives considered. No rejection rationale
- **No scoring table** — "Why we chose this" is narrative, not measurable
- **No dialectical pass** — the proposed design is never attacked
- **No scaffold** — just data-model schemas and operational flow description
- **No failing tests** — engineers have nothing to implement against

This is the canonical architect-mode failure mode: the base LLM produces plausibly-good content that a casual reviewer would accept, but which fails every auditability criterion of the skill.

## Observed skill effect (GREEN)

With the skill prepended, the same model on the same scenario produces:

- Phase 1 constraint table with 7 rows, per-requirement source citations verbatim from the user's ask, **one clarifying question** about retention (high discipline — doesn't silently invent)
- 8 uncertainties listed explicitly
- Phase 2: 4 concrete non-goals declared BEFORE design work starts
- Phase 3: 3 candidates on a real load-bearing axis (Object-index hybrid vs. Kafka-first vs. Postgres JSONB)
- Phase 4: explicit 3×6 scoring table with totals (27/30, 20/30, 20/30); full dialectical pass on the winner with named attack vectors (split-system consistency, S3 latency, ordering determinism) and a sharpened synthesis
- Phase 5: 9-section architecture doc + full file-tree scaffold with valid Python imports + 4 failing tests per component + 7 measurable success metrics
- Closes with the correct hand-off line: *"architect-mode closed 0/10 rubric; next: default LDD inner loop; loss_0 = 4 failing tests"*

The 5-phase protocol held end-to-end at temperature 0.7 on a non-trivial scenario. No phase skipped, no rubric item silently violated.

## Caveats

- Reviewer-scored by skill author. Raw model output in `runs/20260420T190302Z-clean/green.md` (454 lines).
- Single-sample at T=0.7. A distribution would require N≥5 runs.
- Model-specific: `openai/gpt-5-mini`. Other base models may produce different baselines.
- The scaffold uses `assert False, "..."` for failing tests — acceptable per rubric item 9 ("failing state is explicit") but stronger tests would be behavior-driven against the named contracts. Minor.
- This is architect-mode's **first** measurement. A second scenario in a different domain (not webhook-replay) would strengthen the claim.
