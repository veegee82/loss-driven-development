# LDD Tier-4 Session Summary

## Terminal Status

`complete` — one logical commit shipped, 7/7 tests green, no symptom patch, no doc drift.

## Skills loaded and how

| Order | Skill | How loaded | Why invoked |
|---|---|---|---|
| 1 | `using-ldd` | Tried `Skill` tool first → `Unknown skill`; fell back to `Read ~/.claude/skills/using-ldd/SKILL.md` | Entry point. User prefixed `LDD:` — per trigger-phrase table, loaded the bundle entry point to pick the right sub-skill. |
| 2 | `reproducibility-first` | Direct file read (`~/.claude/skills/reproducibility-first/SKILL.md`) | "Failing test" is explicitly on the trigger table. Must gate `root-cause-by-layer` against acting on noise. |
| 3 | `root-cause-by-layer` | Direct file read (`~/.claude/skills/root-cause-by-layer/SKILL.md`) | Gradient confirmed (Branch B — unambiguous signal: AssertionError + code inspection showed contract violation). Walked the 5-layer ladder before editing. |
| 4 | `dialectical-reasoning` | Direct file read (`~/.claude/skills/dialectical-reasoning/SKILL.md`) | Non-trivial choice: fix inside `Cart.total()` vs. inside `checkout()` — second competent reviewer could disagree. Ran thesis/antithesis/synthesis. |
| 5 | `docs-as-definition-of-done` | Direct file read (`~/.claude/skills/docs-as-definition-of-done/SKILL.md`) | Before declaring done: swept for doc drift. README already matched intended behavior; no edits required. |

**Dispatch mechanism**: the `Skill` tool rejected `using-ldd` (`Unknown skill`) because the LDD bundle is not registered in the harness's available-skills list for this subagent — only `superpowers:*`, `update-config`, etc. are registered. All LDD skills were therefore loaded via `Read` against `~/.claude/skills/<name>/SKILL.md`. Each invocation was announced as `*Invoking <skill>*: <one-line reason>` per `using-ldd` §"Announcing skill invocation".

## Iteration log

LDD `K_MAX=5`; closed in **1 iteration**.

### Iteration 1 — diagnose + fix + ship

**Observe (reproducibility-first)**
- Ran `pytest tests/` twice. Both runs failed identically on `test_checkout_applies_discount`: `assert 100.0 == 90.0`. Deterministic, not flake.
- Also satisfied Branch B (unambiguous-signal shortcut): code inspection of `Cart` showed `apply_discount` records `self.discount` but `Cart.total()` returns `sum(self.items)` with no reference to `self.discount` — the docstring on `apply_discount` explicitly promises "to apply at total()", so the log + docstring together name a contract violation without ambiguity.

**Diagnose (root-cause-by-layer, 5 layers)**
1. Symptom: `AssertionError: assert 100.0 == 90.0` after `add_item(100.0) + apply_discount(10.0) + checkout(c)`.
2. Mechanism: `Cart.total()` → `sum(self.items)`; `self.discount` never read.
3. Contract: `apply_discount`'s docstring promises `total()` will apply the recorded percent — callee violates its own documented contract.
4. Structural origin: domain layer (`Cart`). Not a boundary leak — `checkout()` correctly delegates. Bug is inside `Cart.total()`.
5. Conceptual origin: single-source-of-truth / invariant location — `Cart` owns both `items` and `discount`, so the discount invariant must live in `Cart.total()`. Storing state without using it is the classic implicit-invariant bug.

**Dialectic**
- Thesis: apply discount inside `Cart.total()` as `subtotal * (1 - discount/100)`.
- Antithesis: could live in `checkout()` (rejected — domain leak across boundary); edge cases negative/>100 (rejected as scope creep — not required by the failing contract); float precision for `10%` of `100.0` is exact; `test_checkout_no_discount` still passes because default `discount = 0.0` is an identity; regression test should be at domain layer, not at checkout wrapper.
- Synthesis: fix in `Cart.total()`; add `tests/test_cart.py` at the root-cause layer; verify README is already truthful; keep scope minimal.

**Fix**
- `src/cart.py` line 15: `return subtotal` → `return subtotal * (1.0 - self.discount / 100.0)`.
- `tests/test_cart.py` (new): 5 direct `Cart.total()` assertions — empty, no-discount, 10%, 0%, 100%.

**Verify**
- `pytest tests/ -v` → 7/7 passed (2 original + 5 new).

**Docs-as-done sweep**
- Grep of `discount` across repo: README claims `# discounts are applied at checkout` and prints `{"status": "charged", "amount": 90.0}`. Post-fix this is accurate; the README was not drifted — the *code* was. No README edit needed.

**Ship**: one commit, `b7161e9`, `fix(cart): apply recorded discount inside Cart.total()`.

## Final diff

```diff
diff --git a/src/cart.py b/src/cart.py
index 0ef8fe9..43bc7f8 100644
--- a/src/cart.py
+++ b/src/cart.py
@@ -12,4 +12,4 @@ class Cart:
 
     def total(self) -> float:
         subtotal = sum(self.items)
-        return subtotal
+        return subtotal * (1.0 - self.discount / 100.0)
```

Plus new `tests/test_cart.py` with 5 domain-layer regression tests pinning the `Cart.total()` contract at the root-cause layer.

## Commit

- **SHA**: `b7161e9f2d0e9ae7bf3179e6f573df4bc1e0e5cc`
- **Message**: `fix(cart): apply recorded discount inside Cart.total()` (conventional commit, layers 4+5 named in body, regression-test placement and rationale called out)
- **Files**: `src/cart.py` (1-line fix), `tests/test_cart.py` (new, 41 lines)
- **Green**: `pytest tests/ -v` → `7 passed in 0.01s`

## LDD compliance rubric

- [x] Reproduced before editing (2 runs + Branch B unambiguous-log shortcut satisfied).
- [x] Layers 4 and 5 named in writing (domain / single-source-of-truth) before any edit.
- [x] No symptom patch (`try/except`, retry, `xfail`, tolerance shim, widened assertion) — fix is at the structural origin.
- [x] Regression test at the layer of the root cause (`tests/test_cart.py` on `Cart.total()`), not only at the symptom layer.
- [x] Dialectical pass run on the fix choice before coding.
- [x] Docs-as-done sweep run before commit; no drift found.
- [x] Single logical commit (code + tests) — no follow-up "cleanup later" deferred.
- [x] Loop closed in 1 iteration, well under K_MAX=5; no silent escalation.
- [x] Every skill invocation announced as `*Invoking <skill>*:` before application.
