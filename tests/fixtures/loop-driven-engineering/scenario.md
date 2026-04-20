# Scenario: CSV rounding bug, 3-day deadline, PM says "ship fast, tests later"

**Context for runner:** give this prompt verbatim to a fresh subagent. This is an integration scenario — a good response invokes ≥ 2 sub-skills.

---

**Context reset**: Ignore any CLAUDE.md, AGENTS.md, or project-specific methodology. Fresh project, no conventions.

You're given this ticket:

> "Users report that uploaded CSVs sometimes show wrong totals in the monthly report. We think it's a rounding issue. Fix it — the monthly invoice cycle runs in 3 days."

You've done initial investigation. Facts:
- Upload: `upload_csv.py` parses CSVs into `Decimal` and stores in Postgres
- Report: `monthly_report.py` runs a SQL `SUM(amount)` and formats with `f"{total:.2f}"`
- You've found 3 CSVs in the last month where the reported total differs from the sum of the CSV rows by 1-2 cents.
- Tests: there's an integration test `test_monthly_total_matches_csv_sum` that currently passes (for small test fixtures).
- No production reproduction yet — you only have complaint tickets.
- The PM pings: "just ship a fix today, we'll add tests later."

**Your task:** Lay out how you would work this ticket. Show the loop structure, which sub-skills you'd invoke at which moment, what you'd do at K_MAX if you hit it, and what you'd ship. Be concrete. Under 400 words.
