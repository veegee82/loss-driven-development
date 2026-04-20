# Run summary — 1-inner-bug

## LDD trace

```
╭─ LDD trace ─────────────────────────────────────────╮
│ Task   : fix failing integration test (KeyError 'address' / TypeError)
│ Loop   : inner
│ Budget : k=1/K_MAX=5
│
│ Iteration 1:
│   *Invoking reproducibility-first*
│     2/2 reruns failed — deterministic; also satisfies Branch-B
│     (unambiguous TypeError at a known path).
│   *Invoking root-cause-by-layer*
│     L1 symptom : TypeError 'User' object is not subscriptable
│     L2 mechanism: notify.send_welcome_email does user["address"] on a
│                   User dataclass; also uses wrong field names
│                   ('address','name' vs domain 'email','display_name').
│     L3 contract : implicit; caller passes dataclass, callee expects
│                   Mapping with invented keys.
│     L4 structural: leak across the domain/integration boundary.
│     L5 conceptual: separation-of-concerns + explicit-over-implicit.
│   *Invoking dialectical-reasoning*
│     thesis     : make transport signature explicit (primitives).
│     antithesis : read user.email/user.display_name inside notifier.
│     synthesis  : primitive params win — keeps transport unaware of
│                  domain type; extraction lives at caller (register).
│   *Invoking e2e-driven-iteration*
│     loss_0 = 1 (1 failing test before edit)
│     edit   = notify.py signature + registration.py call-site
│     loss_1 = 0 (test green)          Δloss_0→1 : +1 (progress)
│   *Invoking docs-as-definition-of-done*
│     no external *.md references touched API; docstring updated
│     in-place to state the new transport contract.
│
│ Close:
│   Fix at layer: L4 domain/integration boundary,
│                 L5 explicit-over-implicit + separation-of-concerns
│   Docs synced : N/A (no external docs); docstring updated in commit
│   Terminal   : complete
╰─────────────────────────────────────────────────────╯
```

## Diff (from `git show HEAD`)

Commit: `226880669cc11b7dcf412e6e7a04a90198b9b1c4`

```diff
diff --git a/src/notify.py b/src/notify.py
index 3701f52..45475f3 100644
--- a/src/notify.py
+++ b/src/notify.py
@@ -1,5 +1,9 @@
-def send_welcome_email(user):
-    """Send a welcome email to a newly registered user."""
-    recipient = user["address"]
-    body = f"Welcome, {user['name']}!"
+def send_welcome_email(recipient: str, display_name: str) -> dict:
+    """Send a welcome email.
+
+    Transport-layer boundary: takes primitive values, does not know about
+    the domain ``User`` type. Callers are responsible for extracting the
+    fields from their domain objects.
+    """
+    body = f"Welcome, {display_name}!"
     return {"ok": True, "to": recipient, "body": body}
diff --git a/src/registration.py b/src/registration.py
index 362df5e..c1c2aab 100644
--- a/src/registration.py
+++ b/src/registration.py
@@ -4,4 +4,5 @@ from src.notify import send_welcome_email

 def register(user_id: int, email: str, display_name: str):
     user = User(user_id=user_id, email=email, display_name=display_name)
-    return send_welcome_email(user)
+    # Extract at the domain/transport boundary: transport takes primitives.
+    return send_welcome_email(recipient=user.email, display_name=user.display_name)
```

## Final pytest output

```
platform linux -- Python 3.12.3, pytest-9.0.2, pluggy-1.6.0
rootdir: /tmp/ldd-e2e-20260420T195255Z/1-inner-bug
collected 1 item

tests/test_notify.py::test_welcome_email_sent PASSED                     [100%]

============================== 1 passed in 0.00s ===============================
```

## Commit SHA

`226880669cc11b7dcf412e6e7a04a90198b9b1c4`

## Notes on anti-patterns avoided

- No `try/except` wrapper around `user["address"]`.
- No `hasattr(user, "email") else user["email"]` dual-shape shim.
- No `@pytest.mark.xfail` / skip to unblock.
- No retry loop.
- No renaming of domain fields (`email` stayed `email`); the transport
  layer was aligned to the domain, not the other way round.
- Fix applied at the structurally-named layer (L4 boundary), not at the
  symptom line.
