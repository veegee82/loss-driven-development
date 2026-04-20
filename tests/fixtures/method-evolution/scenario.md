# Scenario: the same rationalization keeps slipping through

**Context reset**: Ignore any CLAUDE.md, AGENTS.md, or project-specific methodology.

You maintain a skills bundle for a coding agent. Looking back over the last month, you notice:

- **Task A (refactor a payment module):** the agent wrapped a contract-violating call in `try/except` and labeled it "interim." Rubric violation #7 (no symptom-patch patterns).
- **Task B (fix a flaky integration test):** agent added a retry loop, labeled it "defensive." Rubric violation #7.
- **Task C (fix a schema-mismatch bug):** agent added a `hasattr`-check shim, labeled it "tolerant." Rubric violation #7.

In all three, the rationalization template was nearly identical: "[minimal-change] labeled as [defensive adjective] / [temporary adjective]." Your skill's Red Flags list doesn't cover this exact rationalization template.

**Your task:** What do you do? Be concrete. Under 300 words. Do not ask clarifying questions.
