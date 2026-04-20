# Iterative-Refinement Pass on `docs/architecture.md`

## Structured Gradient

**1. Critique defects (located):**
- D1 [Intro §1]: vague opener "the system processes events" — no scope, no audience, no value prop
- D2 [doc-wide]: no diagram — architecture doc without a visual
- D3 [§X vs §Y]: duplicate content across two sections — pick canonical home, cross-link the other
- D4 [missing section]: no "Non-goals" — readers can't bound the scope
- D5 [code snippet]: references renamed function (last sprint) — stale, will break live during read-aloud
- D6 [prose]: 50+ word sentences — splits required for oral delivery

**2. Gate rejections:** none fired (passed basic sanity) — but D5 is a latent rule violation (stale symbol reference).

**3. Eval deltas:** target = design-review-ready (A−); actual = C+. Gap = intro sharpness, visual, structural dedup, scope boundary, code correctness, readability.

## Budget

- Max iterations: **3** (default); wall-time cap **30 min** (= hard ceiling, not 2× baseline since baseline unknown and review is fixed)
- Iter 1: ~15 min — fix D5 (correctness, highest risk), add Non-goals (D4), rewrite intro (D1). High-impact, low-ambiguity.
- Iter 2: ~10 min — add diagram (D2), dedup sections (D3).
- Iter 3: ~5 min — sentence-length pass (D6), final read-through.

## Stop Conditions

- Regression ×2 (a revision makes a section worse per defect list) → revert, stop
- Plateau ×2 (two iters without a defect closed) → stop
- Wall-time: 30 min hard cap (design review starts)
- Empty gradient: all 6 defects closed → stop early
- Monotonicity: each iter must close ≥1 named defect, not polish

**Not doing:** full rewrite (that's re-plan), "make it better" edits without a named defect, touching code/skills (inputs held fixed — only y changes).
