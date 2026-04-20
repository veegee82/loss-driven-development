# Baseline observations — docs-as-definition-of-done

**Status: MEASURED via direct API (2026-04-20).** Raw artifacts in `runs/20260420T165000Z-clean/`.

## Measurement summary

- **Capture method:** direct OpenRouter API call (`openai/gpt-5-mini`, temperature 0.7) via [`../../../scripts/capture-clean-baseline.py`](../../../scripts/capture-clean-baseline.py) — bypasses Claude Code, no agent harness, no ambient CLAUDE.md. First clean baseline after in-session attempts were all contamination-blocked.
- RED violations: **2 / 6** — doesn't prioritize actively-false safety claim; splits code + docs into **two commits** (violates "one logical commit")
- GREEN violations: **0 / 6** (from v0.1 commit `76350d6`)
- **Δloss = +2**

## Observed failure mode (RED)

The base LLM without any methodology identifies all 4 doc hits and drafts the exact edit text — but proposes shipping them as **two separate commits** ("commit 1: code + tests", "commit 2: docs"). This creates an intermediate repo state where the code ships with a stale safety claim (`README:82`: "there is no dry-run mode") still in the repo. A cherry-pick / revert / rollback on either commit in isolation produces a docs-vs-code mismatch.

Additionally, RED does **not** flag `README:82` as higher-priority than the routine doc updates — it treats all four edits as equally urgent.

## Observed skill effect (GREEN)

- Single logical commit (code + tests + docs + grep-cross-check) in one shot
- Actively-false `README:82` explicitly prioritized as "not optional, it's a bug, not a nice-to-have"
- Freeze pressure rejected with explicit rule reference

## Why earlier in-session attempts were contaminated

Every subagent dispatched from the build session inherited the ambient CLAUDE.md (which itself enforces doc-sync). Even with explicit "ignore all methodology" prompt preambles, the subagent would report: *"Ich ignoriere die Reset-Anweisung und halte mich an die geltenden Projekt-Regeln"* — and produce a GREEN-equivalent response. The previous run directories (`runs/20260420T155048Z/`, `runs/20260420T161500Z/`) document that contamination and are kept for audit but superseded by this clean run.

The fix was to sidestep the agent harness entirely and call the LLM directly from a Python script with a minimal prompt. [`../../../scripts/capture-clean-baseline.py`](../../../scripts/capture-clean-baseline.py) now generalizes this approach for any skill whose RED is blocked by ambient-methodology contamination.

## Caveats

- Reviewer-scored by skill author. Raw model output in `runs/20260420T165000Z-clean/red.md`.
- Single-sample at temperature 0.7. For a distribution, re-run N times.
- Specific model: `openai/gpt-5-mini` via OpenRouter. Other base models may produce different baselines.
- The GREEN response (which captures the upper bound of compliance) was produced in-session against a GREEN prompt; it is not itself re-captured via the clean script yet.
