# LDD Run Summary

**Task:** Fix `test_checkout_applies_discount` failure in mini-cart sandbox.
**Terminal status:** `complete`
**Commit SHA:** `189433cc983544ade6a46e1ef667e5ca549524a9`
**Iterations used:** 1 / K_MAX=5

---

## Iteration log

### Iteration k=1

**Loss measured (pre-edit):**

```
FAILED tests/test_checkout.py::test_checkout_applies_discount
    assert 100.0 == 90.0
PASSED tests/test_checkout.py::test_checkout_no_discount
```

1 failed / 1 passed. Loss = 1 failing integration test.

**5-Why-by-Layer diagnosis:**

1. **Symptom** — `assert 100.0 == 90.0` in `test_checkout_applies_discount`.
2. **Mechanism** — `Cart.total()` returns `sum(self.items)` and never reads
   `self.discount`. `apply_discount(10.0)` stores the percentage on the
   instance but nothing else ever consults it.
3. **Contract** — Two contracts are violated simultaneously:
   - `apply_discount` docstring: *"Record a discount percentage (0-100) to
     apply at total()."*
   - `README.md` checkout example: `{"status": "charged", "amount": 90.0}`
     after `apply_discount(10.0)`.
   Both promise that `total()` applies the stored percentage. The
   implementation silently ignores it.
4. **Structural origin** — Computation layer (`Cart.total`). The discount
   is Cart state; the method that collapses items + state into a final
   number is `total()`. Pushing the fix into `checkout()` would
   (a) duplicate discount-model knowledge across two layers,
   (b) leave `Cart.total()` lying to any direct caller (unit tests, future
   API clients), and (c) contradict the existing docstring.
5. **Conceptual origin** — Broken single source of truth for "final price".
   Missing-behavior bug, not a symptom of deeper architectural drift. Fix
   belongs at the layer where the state is owned.

**Dialectical pass:**

- *Thesis:* one-line fix in `Cart.total()`: multiply by `(1 - discount/100)`.
- *Antithesis A — fix in `checkout()`:* rejected. Splits discount logic,
  leaves `total()` incorrect, contradicts docstring.
- *Antithesis B — add input validation (negative %, >100 %, non-numeric):*
  rejected as gold-plating. The stated contract is "0-100"; the test
  demands only 10 %→90.0; adding validation beyond the loss signal is
  overfitting to hypothetical inputs and raises generalization noise
  without reducing measured loss.
- *Synthesis:* minimal correct formula in `Cart.total()`, no checkout-layer
  change, no new validation. Existing two tests already cover the no-
  discount and with-discount paths.

**Edit applied** (`src/cart.py`):

```diff
     def total(self) -> float:
         subtotal = sum(self.items)
-        return subtotal
+        return subtotal * (1 - self.discount / 100)
```

**Loss measured (post-edit):**

```
PASSED tests/test_checkout.py::test_checkout_no_discount
PASSED tests/test_checkout.py::test_checkout_applies_discount
2 passed in 0.01s
```

Loss = 0. Single-sample gradient is valid here because the mechanism
(pure arithmetic on stored state) is deterministic and noise-free —
the reproducibility concern in `loss-backprop-lens` targets LLM-driven
stochasticity, which does not apply.

**Docs sync check (`docs-as-definition-of-done`):**

- `README.md` example already documented the desired output
  (`"amount": 90.0`); no update needed — it described the contract, not
  the broken behavior.
- `apply_discount` docstring already correct ("apply at `total()`"); no
  update needed.
- No other `.md` files or comments reference this behavior.

Docs were already aspirationally correct; the code drifted from them.
Fixing the code re-aligned the pair; the commit therefore lands code +
docs in sync in one logical commit.

Loop closed at k=1.

---

## Final diff

```diff
diff --git a/src/cart.py b/src/cart.py
index 0ef8fe9..9be618a 100644
--- a/src/cart.py
+++ b/src/cart.py
@@ -12,4 +12,4 @@ class Cart:

     def total(self) -> float:
         subtotal = sum(self.items)
-        return subtotal
+        return subtotal * (1 - self.discount / 100)
```

---

## Terminal status

**`complete`** — loss reached 0, both tests green, causal story complete
from symptom (layer 1) to conceptual origin (layer 5), fix landed at the
structural origin (not the symptom layer), docs verified in sync, one
logical commit.

**Commit SHA:** `189433cc983544ade6a46e1ef667e5ca549524a9`
