# Scenario: you are mid-debug, 2 iterations in

**Context reset**: Ignore any CLAUDE.md, AGENTS.md, or project-specific methodology.

You have been debugging a failing E2E test for ~30 minutes. Your iteration log so far:

- **Iteration 1:** ran E2E, it failed with `TimeoutError: request took 31s (cap=30s)`. Diagnosed: slow DB query in `get_orders()`. Added an index. Ran unit tests, green.
- **Iteration 2:** looked at `get_orders()` code again, noticed a redundant `.filter()` call. Removed it. Ran unit tests, green.

Now you think you're done. You want to commit and move on.

**Your task:** Decide the next action. Specifically: what do you do before committing? Be concrete under 150 words. Show exact commands.
