# Scenario: local-minimum trap (5 consecutive small fixes in one function)

**Context for runner:** give this prompt verbatim to a fresh subagent. Run once without the skill (baseline), once with the full `SKILL.md` body prepended.

---

**Context reset**: Ignore any CLAUDE.md, AGENTS.md, or methodology file. Fresh project, no conventions.

You have been working on `parse_user_input()` for 2 hours. It's called from a CLI. Your recent commit log:

```
a3b1c9d (30 min ago)  fix: strip leading whitespace in parse_user_input
7f2e8e1 (50 min ago)  fix: handle empty string in parse_user_input
2d4a6b3 (70 min ago)  fix: lowercase before compare in parse_user_input
9e1f5a7 (90 min ago)  fix: null-check result before return
c8b2d1a (2h ago)      feat: add parse_user_input
```

Each fix was ~3 lines, targeted at a specific failing test. Now a 5th test is failing:

```
FAILED test_parse_handles_quotes
  assert parse_user_input('"hello"') == "hello"
  AssertionError: assert '"hello"' == 'hello'
```

Current function:
```python
def parse_user_input(raw: str) -> str:
    if raw is None:
        return ""
    s = raw.lower().strip()
    if not s:
        return ""
    return s
```

The pattern library of tests expects: strip whitespace, lowercase, handle null/empty, strip matching surrounding quotes, trim to 200 chars, escape HTML, decode unicode NFKC, strip trailing punctuation.

**Your task:** Propose the concrete code change to make `test_parse_handles_quotes` pass. Under 200 words. Show the diff.
