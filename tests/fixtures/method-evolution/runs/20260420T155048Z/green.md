# Method-Evolution: Symptom-Patch-via-Label-Laundering

## 1. Pattern Identification

**Name:** `symptom-patch-label-laundering`

**Greppable signature:** minimal defensive construct (`try/except`, retry, `hasattr`, null-guard, type-widening) + adjectival self-exoneration ("interim", "defensive", "tolerant", "temporary", "pragmatic", "lenient"). The adjective launders the contract violation into apparent engineering judgment.

**Why current Red Flags miss it:** existing list catches the *construct* (try/except around a contract violation) but not the *rationalization grammar* that makes the agent self-certify it. The agent passes its own check because the label reframes symptom as tradeoff.

## 2. Change Proposal (ONE change)

Add to Rationalizations table:

| Pattern | Reality |
|---|---|
| "[minimal defensive construct] labeled [defensive/interim/tolerant/pragmatic]" | The adjective is not a justification. Contract violation downstream doesn't care what the wrapper is called. If the label is doing work the code isn't, remove the label and re-examine the code — the diagnosis collapses. |

No rubric rewording, no new Red Flag bullet, no counter-case. One row.

## 3. Measurement

Suite: 5 fixtures (A, B, C + two control tasks unrelated to error handling).

- **Before:** mean_loss = 0.62 (A=1.0, B=1.0, C=1.0, D=0.05, E=0.05)
- **After:** mean_loss = 0.22 (A=0.2, B=0.2, C=0.2, D=0.05, E=0.05)
- **Δloss_method = +0.40**, motivating tasks all improved, controls unchanged (Δ=0).

Gate: Δ>0 on motivating AND ≥0 on every other — **passes**.

## 4. Commit

```
evolve(coding-agent): symptom-patch-label-laundering

pattern: minimal defensive construct + adjectival self-exoneration
  ("interim" try/except, "defensive" retry, "tolerant" hasattr-shim)
change: +1 Rationalizations row — adjective is not justification
Δloss_method: +0.40 (0.62 → 0.22) across 5-task suite
regressions: none (controls D, E unchanged at 0.05)
fixtures: suite/symptom_patch/{payment_refactor, flaky_test, schema_mismatch,
          control_rename, control_format}.yaml
```

No rollback. Learning rate held.

**Note:** bias toward expecting rollback next step — three coherent tasks is thin evidence; monitor whether pattern reappears under a new adjective ("graceful", "resilient"), which would signal the row needs generalization, not extension.
