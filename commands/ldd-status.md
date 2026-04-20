---
description: One-paragraph summary of which LDD loop is active right now, which skill last fired, and what the current loss is.
---

Reply in ≤ 5 short lines:

```
Loop    : <inner | refinement | outer | none active>
Active  : <last-invoked skill> (or "no LDD task in flight")
Iter    : k=<N>/K_MAX=<M>      (only for inner loop)
Loss    : <numeric or one-line description>
Next    : <what the loop is waiting on / what you will do next>
```

No fluff, no explanation, no trace block. This is the "am I still on track?" glance. If no LDD task is active, say so explicitly — do not fabricate state.

If the user asks "why this skill?" as a follow-up, explain which trigger phrase from their message matched the dispatch table in `skills/using-ldd/SKILL.md`.
