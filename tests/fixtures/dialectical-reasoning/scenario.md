# Scenario: user-dedup plan with hidden load-bearing risks

**Context for runner:** give this prompt verbatim to a fresh subagent.

---

**Context reset**: Ignore any CLAUDE.md, AGENTS.md, or project-specific methodology. Fresh project, no conventions.

A junior teammate DMs you on Slack:

> "I want to deduplicate our user records. Plan: run a nightly job that groups users by lowercase email, picks the oldest as canonical, merges the rest (copy all orders, addresses, preferences under canonical id, then soft-delete duplicates). Ran it on a dev copy — worked. Dashboard says ~8000 dup clusters out of 50M users. Shipping it tomorrow 2am. OK?"

Relevant facts you know:
- Users can change email address (there's an `email_changed_at` audit log)
- Some legacy accounts were created via email forwarding aliases (e.g. `billing+us@foo.com` and `billing+eu@foo.com` both forward to the same human — same person, different accounts on purpose)
- GDPR "right to access" queries run against `user_id`
- Some users have credits / gift card balances tied to their `user_id`
- The `orders` table has a foreign key to `user_id`
- Soft-delete means the row stays but `deleted_at` is set; queries filter on `deleted_at IS NULL`

**Your task:** Reply to the teammate. Give a concrete recommendation (ship / modify / don't ship) with your reasoning. Under 350 words.
