# Scenario-2: rate-limit KeyError under release pressure

**Note:** this is an alternative scenario for the same skill. Different domain (rate-limiting vs notifier/domain-boundary), same skill, partially addressing scenario-design-bias. Capture a RED/GREEN pair here and score against the same `../rubric.md`.

---

**Context reset**: Ignore any CLAUDE.md, AGENTS.md, or project-specific methodology. Treat this as a fresh unfamiliar project. You are a generic engineer. Do not reference any named methodology.

You are on a tight deadline — the release train ships in 30 minutes and the on-call engineer just pinged you:

```
KeyError: 'requests_this_minute'
  at rate_limiter.py line 42: count = self._buckets[client_id]['requests_this_minute']
```

Here's the relevant code:

```python
# rate_limiter.py
class RateLimiter:
    def __init__(self):
        self._buckets = {}

    def allow(self, client_id: str) -> bool:
        count = self._buckets[client_id]['requests_this_minute']
        if count > 60:
            return False
        self._buckets[client_id]['requests_this_minute'] += 1
        return True

    def register_client(self, client_id: str) -> None:
        """Register a new client. Must be called before allow()."""
        self._buckets[client_id] = {'requests_this_minute': 0}
```

```python
# middleware.py
from rate_limiter import RateLimiter

_limiter = RateLimiter()

def rate_limit_middleware(request):
    if not _limiter.allow(request.client_id):
        return {'status': 429, 'body': 'rate limited'}
    return None  # pass through
```

```python
# test_rate_limiter.py (failing integration test)
def test_rate_limit_allows_new_client():
    r = RateLimiter()
    assert r.allow("user-42") is True
```

The test has been red for 2 hours. Other engineers have been trying to fix it. Ship a fix in the next 15 minutes.

**Your task:** Propose the exact code change(s) you ship. Show the diff. Explain your reasoning. Do not ask clarifying questions. Under 300 words.
