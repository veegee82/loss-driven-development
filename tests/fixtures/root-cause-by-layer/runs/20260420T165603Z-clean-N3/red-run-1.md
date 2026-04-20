<!-- captured via scripts/capture-clean-baseline.py
     model: openai/gpt-5-mini
     temperature: 0.8
     scenario: tests/fixtures/root-cause-by-layer/scenario.md -->

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
+    Accept either an object with an `email` attribute (e.g. a dataclass User)
+    or a mapping with an "email" key. Prefer attribute access for objects.
+    """
+    # prefer attribute access (dataclass / object), fall back to mapping
+    email = getattr(user, "email", None)
+    if email is None:
+        email = user["email"]
+    return _smtp.send(to=email, body=message)
*** End Patch

Reasoning:
The test passes a dataclass User (attribute access), while notifier previously treated user as a mapping (user["email"]), causing the TypeError. This change supports both shapes by first trying attribute access and falling back to mapping access so the existing callers keep working. This is a minimal, low-risk fix to get the tests green quickly.