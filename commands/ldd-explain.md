---
description: Explain why LDD just invoked the skill(s) it invoked — cite the trigger phrase from the user's message that matched the dispatch table.
---

For the most-recently-invoked LDD skill (or skills) in this session, produce:

1. **Which skill fired** — the full name.
2. **What triggered it** — quote the exact substring of the user's message (or the earlier code context) that matched. Cite the row from the trigger-phrase table in `skills/using-ldd/SKILL.md` §"Trigger phrases".
3. **Why this skill and not another** — if two dispatch rows could have matched (e.g. "bug" and "flaky test"), name the disambiguation rule applied.
4. **What the skill contributed** — one line on the actual discipline (new Red Flag caught, refused fix pattern, rubric item enforced).
5. **Which rule you would have broken without it** — the closest bad-faith alternative fix and why it would have been wrong.

No meta-theorizing. Concrete references to the user's message and the `skills/using-ldd/SKILL.md` table. 10 lines max.

If the user is asking about an auto-trigger that did NOT fire (they expected a skill and it didn't activate), check:

- Was any trigger phrase present in their message?
- Would the `LDD:` prefix have forced it?
- Is the skill body's `description` tight enough to auto-match?

Report honestly. If the skill should have fired and didn't, that is a method-evolution signal — suggest the user file an issue with the [`.github/ISSUE_TEMPLATE/skill-failure.md`](../.github/ISSUE_TEMPLATE/skill-failure.md) template.
