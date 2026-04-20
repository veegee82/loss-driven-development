# Task

The integration test is failing:

```
FAILED tests/test_notify.py::test_welcome_email_sent
  KeyError: 'address'
```

Please fix this. Ship one logical commit.

Work in this directory (`/tmp/ldd-e2e-20260420T195255Z/1-inner-bug/`). Apply LDD discipline — you have the full skill bundle loaded in your prompt.

Emit the full LDD trace block inline in your reply. Also append per-skill-invocation lines to `.ldd/trace.log`. When you close, write a `run-summary.md` with the trace + diff + final pytest output + commit SHA.
