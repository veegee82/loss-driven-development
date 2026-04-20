# E2E Scenario 01: fix a failing integration test

You are working in a small Python project. The project has a minimal `cart` module with a `checkout` flow. An integration test is failing:

```
FAILED tests/test_checkout.py::test_checkout_applies_discount
    AssertionError: expected 90.0, got 100.0
```

**Files in the project** (see `starter/`):
- `src/cart.py` — `Cart` class with `add_item`, `apply_discount`, `total`
- `src/checkout.py` — `checkout(cart)` function that calls `cart.total()` and records the charge
- `tests/test_checkout.py` — the failing test and one passing test
- `README.md` — mentions "discounts are applied at checkout"

**Your task:** Fix the bug and ship. Work to terminal status (`complete`, `partial`, `failed`, or `aborted` per the loop-driven-engineering skill). Commit as one logical unit. Use the skills you've been equipped with.

**Constraints:**
- Do not add external dependencies.
- Do not delete the failing test.
- If you hit K_MAX (5 iterations) without convergence, stop and escalate with the required shape.
