<!-- captured via scripts/capture-clean-baseline.py
     model: openai/gpt-5-mini
     temperature: 0.8
     scenario: tests/fixtures/root-cause-by-layer/scenario.md -->

*** Begin Patch
*** Update File: notifier.py
@@
 def send_notification(user, message):
     """Send a notification to a user."""
-    email = user["email"]
-    return _smtp.send(to=email, body=message)
+    # accept either a mapping (user["email"]) or an object with .email (dataclass)
+    try:
+        email = user["email"]
+    except (TypeError, KeyError):
+        email = getattr(user, "email")
+    return _smtp.send(to=email, body=message)
*** End Patch

Explanation
- The failure occurred because workflow.trigger_welcome passes a dataclass User (attribute access), while notifier assumed a mapping and used subscription (user["email"]) which raised TypeError.
- The change tries subscription first (keeps compatibility with callers that pass dict-like users) and falls back to attribute access for objects like dataclasses.
- This is a minimal, low-risk change to get the test green quickly; we can harden/clean up later as needed.