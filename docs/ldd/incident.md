# Incident — production fire, fast-path diagnosis

Load this when the user says: "production is down", "incident", "outage", "customers seeing errors", "on-call page", "hot-fix", "fire drill", or anything implying real users affected right now.

Incidents are the **inner loop** under hard time pressure, with a mandatory outer-loop kickoff after close. Customer impact is the loss; the [Gradient Descent for Agents](../theory.md) discipline does not relax under pressure — what changes is the mitigation-before-diagnosis rule below.

## Skill cascade (incident-compressed)

Same skills as [`debugging.md`](./debugging.md), but the budgets are tighter and one rule changes:

```
reproducibility-first  →  root-cause-by-layer (fast-path)  →  loss-backprop-lens  →  (fix OR rollback)
```

## Incident-specific rules

### Rule 1 — Mitigation before diagnosis

Customer impact is the loss function now, not the failing test. If a rollback / feature flag / circuit-break will restore service in under 5 minutes, **do that first**, then invoke `root-cause-by-layer` on the captured artifacts at leisure.

Mitigation options, in order of preference:

1. **Rollback** to the last known-good commit (cheapest, always reversible)
2. **Feature flag off** the affected code path (if the flag exists)
3. **Circuit-break** the failing call site (deny / return-cached / return-empty until fixed)
4. **Rate-limit** to reduce blast radius while you investigate

### Rule 2 — `reproducibility-first` still applies — but faster

You have less time to rerun. Accept Branch B (unambiguous log) more readily if **all three** criteria hold *and* the log is from production (which is N=many samples already, not N=1). Otherwise Branch A with 1 extra rerun, not 2.

### Rule 3 — Diagnose on the side, don't fix-under-pressure

Walking `root-cause-by-layer` to layers 4/5 in 5 minutes is hard. **Don't try.** Once mitigated, diagnose at leisure; commit the real fix when you can do it right.

**Red flag:** "let me just wrap this in try/except to stop the pager" — that's the exact overfit you just rolled back to avoid. Mitigation is structural (flag off, revert); the code fix comes after diagnosis.

### Rule 4 — The post-incident commit must close two loops

- **Inner loop:** the real fix at the root-cause layer (not at the symptom).
- **Outer loop:** if the incident pattern could recur (e.g. "we missed a null-check that was obvious in hindsight"), run `method-evolution` on the relevant skill or rubric. One incident in a month = noise; three in a month of the same shape = method is failing, evolve it.

### Rule 5 — Postmortem covers both loops

The postmortem doc names the structural origin (layer 4/5) **and** whether the method needs updating. Postmortems that only list "what we did wrong" without a method-level delta are how the same incident recurs three quarters later.

## Red flags specific to incidents

- "Just push the fix, postmortem later" — the postmortem is the outer-loop update; skip it and drift wins
- "The customer impact is done, let's just close the ticket" — the gradient is still there in the method
- "This is a one-off" (said for the 3rd time this quarter) — that's the `method-evolution` trigger
- Hotfix that does not have a test added — regression in 2 weeks guaranteed

## Close

- Incident resolved (mitigation holds)
- Real fix shipped at the root-cause layer
- Postmortem written with structural + method deltas
- Regression test added at the root-cause layer
- If pattern recurs: `method-evolution` scheduled

## Full skill references

- [`../../skills/reproducibility-first/SKILL.md`](../../skills/reproducibility-first/SKILL.md)
- [`../../skills/root-cause-by-layer/SKILL.md`](../../skills/root-cause-by-layer/SKILL.md)
- [`../../skills/loss-backprop-lens/SKILL.md`](../../skills/loss-backprop-lens/SKILL.md)
- [`../../skills/method-evolution/SKILL.md`](../../skills/method-evolution/SKILL.md) — for recurring incidents
