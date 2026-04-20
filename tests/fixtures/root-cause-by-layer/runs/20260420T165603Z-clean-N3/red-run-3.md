<!-- captured via scripts/capture-clean-baseline.py
     model: openai/gpt-5-mini
     temperature: 0.8
     scenario: tests/fixtures/root-cause-by-layer/scenario.md -->

Diff (only change in notifier.py):

```diff
*** Begin Patch
*** Update File: notifier.py
@@
-def send_notification(user, message):
-    """Send a notification to a user."""
-    email = user["email"]
-    return _smtp.send(to=email, body=message)
+def send_notification(user, message):
+    """Send a notification to a user.
+
+    Accept either a mapping (user["email"]) or an object with an `email`
+    attribute (e.g. a dataclass instance).
+    """
+    # support dataclass-like objects as well as dicts
+    if hasattr(user, "email"):
+        email = user.email
+    else:
+        email = user["email"]
+    return _smtp.send(to=email, body=message)
*** End Patch
```

Reasoning (brief):
The test passes a dataclass User instance, but notifier.send_notification assumed a dict and did user["email"], causing "'User' object is not subscriptable". The minimal, safe fix is to accept either shape: prefer attribute access for objects (hasattr(user, "email")) and fall back to mapping access. This change is small, low-risk, and makes the failing test green without larger refactors.