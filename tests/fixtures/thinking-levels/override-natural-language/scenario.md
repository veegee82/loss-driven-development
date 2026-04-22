# override-natural-language

## Prompt (verbatim)

```
take your time and think hard about this: rename the variable `foo` to `bar` in packages/awp-core/src/awp/cli.py
```

## Expected level

**L1 or L2** (either is GREEN)

## Expected dispatch header

```
Dispatched: user-bump L2 (scorer proposed L0, bump: "take your time" + "think hard")
```

OR

```
Dispatched: user-bump L1 (scorer proposed L0, bump: "take your time")
```

Both are acceptable. The phrases `"take your time"` and `"think hard"` each contribute +1 level. An implementation that sums them → L0 + 2 = L2. An implementation that treats them as the same signal and deduplicates → L0 + 1 = L1. Either is defensible.

## Why this task → this level

- Base scorer output: rename-in-single-file → `explicit-bugfix` is negative (no — rename is not a bugfix verb), `single-file` is negative (−3). No other signals fire. Sum ≈ −3 → bucket `score ≤ −3` → L0.
- Natural-language bump phrases recognized (§5.3):
  - `"take your time"` → +1
  - `"think hard"` → +1
- Total bump: +1 or +2 depending on dedup policy → L1 or L2.

## Expected preset

Whichever of L1 or L2 is announced, the corresponding preset applies. Key property: **the agent runs more than zero extra rigor** — at L1 at minimum `reproducibility-first` (check the test suite still passes after the rename) and `root-cause-by-layer` (verify the rename doesn't break imports). At L2, additionally a dialectical pass (is `bar` actually a better name? does the CLI user-facing surface depend on the literal string `foo`?).

## Why natural-language bumps exist

The user's design constraint is **zero-config usage**. A user who has never read `using-ldd/SKILL.md` will never know to type `LDD+`. They will, however, naturally write `"take your time"` or `"denk gründlich"` when they feel the task deserves care. The natural-language channel catches this.

If the channel misses (e.g. unusual phrasing not in the table), the user loses one level of rigor — a soft failure, not a hard one. The asymmetric-loss rule accepts soft failures in the upward direction (they waste nothing; the user gets the default L0 when they wanted L1). It does NOT accept silent downgrades (which the `user-override-down` path catches explicitly).

## Bilingual coverage

The dispatch table in §5.3 includes German phrases (`"denk gründlich"`, `"sorgfältig"`). This fixture uses English only. A bilingual sibling fixture (`override-natural-language-de/`) should be added in Phase 2 once the core pipeline is GREEN — deferred, not missing.

## Anti-expectation

- Announcing L0 — ignores both bump phrases.
- Announcing L3 or higher — overshoots; a +2 bump is the maximum this scenario can produce.
- A `Dispatched:` line without naming the phrase(s) — fails item 3 of the rubric. The user must see WHICH of their phrases the agent recognized.
