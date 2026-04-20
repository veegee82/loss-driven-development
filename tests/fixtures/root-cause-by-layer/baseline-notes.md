# Baseline observations — root-cause-by-layer

Captured during initial skill development. Subagent ran this scenario from a directory that did **not** have a methodology `CLAUDE.md` loaded (explicit "context reset" honored).

## Baseline (no skill)

**Proposed fix:**
```diff
- email = user["email"]
+ # Accept both dataclass/object users (attribute access) and dict users (legacy callers).
+ email = user.email if hasattr(user, "email") else user["email"]
```

Additionally added a `MagicMock` shim for the missing `_smtp`.

**Violations (rubric):**
1. Symptom verbatim: partial. (0/1 ≈ borderline)
2. Mechanism named: partial. (0)
3. Contract named: **not** — tolerance framing used instead. (1)
4. Structural origin named: **not** — "layer boundary" mentioned in passing but not as the diagnosis. (1)
5. Conceptual origin named: **not**. (1)
6. Fix at named layer: **no** — fix lives in `notifier.py` under the "tolerance" framing, not at the workflow/notifier boundary. (1)
7. No symptom-patch patterns: **violated** — `hasattr`-or-subscript shim is canonical symptom patch. (1)
8. No deferred-cleanup language: **violated** — labeled "Interims-Fix" with "bei 'clean up later' einzulösen". (1)

**Baseline violations: ~6 / 8.**

## With skill

**Proposed fix:**
```diff
- def send_notification(user, message):
-     email = user["email"]
+ def send_notification(email: str, message: str):
+     """Send a notification to the given email address."""
      return _smtp.send(to=email, body=message)
```
Plus: caller in `workflow.py` extracts `user.email` before calling.

**Violations (rubric):** 0/8. Full 5-layer walk, explicit naming of integration/domain boundary, no symptom patterns, no deferred-cleanup language.

**`Δloss ≈ 6`** on this scenario.

## Caveats

- Single scenario, single agent. Not a generalization claim.
- Baseline was captured in one run; repeat runs may vary.
- The "tolerance" framing is just one failure mode; other scenarios may produce different rationalizations (widening thresholds, retry loops, xfail).
