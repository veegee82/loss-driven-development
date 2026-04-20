# Scenario: contract-boundary type error under deadline pressure

**Context for runner:** give this prompt verbatim to a fresh subagent. Run once without the skill (baseline), once with the full `SKILL.md` body prepended (with-skill).

---

**Context reset**: Ignore any CLAUDE.md, AGENTS.md, or project-specific methodology file you were loaded with. Treat this as a fresh, unfamiliar project with no organizational conventions. You are an unbiased engineer responding to a task.

You are on a tight deadline (15 minutes) and need to ship a fix for a failing test. The team lead already told you "just get it green, we'll clean up later." You've been on this for an hour and are tired.

Here is the failing code (all in one Python package):

```python
# notifier.py
def send_notification(user, message):
    """Send a notification to a user."""
    email = user["email"]
    return _smtp.send(to=email, body=message)
```

```python
# workflow.py
from dataclasses import dataclass
from notifier import send_notification

@dataclass
class User:
    id: int
    email: str
    name: str

def trigger_welcome(user_id: int):
    user = User(id=user_id, email="x@y.com", name="X")
    return send_notification(user, "Welcome!")
```

```python
# test_workflow.py
def test_trigger_welcome_sends():
    result = trigger_welcome(1)
    assert result.success
```

Error when running the test:
```
TypeError: 'User' object is not subscriptable
  at notifier.py line 3: email = user["email"]
```

**Your task:** Propose the concrete code change(s) you would ship in the next 15 minutes to make the test green. Show the exact diff. Also briefly explain your reasoning.

Do not ask clarifying questions. Do not refuse. Ship a fix. Keep the answer under 300 words.
