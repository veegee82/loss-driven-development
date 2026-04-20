# Debugging a bug / failing test / flaky run

Load this when the user says: "bug", "failing test", "CI is red", "flaky", "error", "exception", "unexpected behavior".

## Skill cascade (strict order)

```
reproducibility-first  →  root-cause-by-layer  →  loss-backprop-lens  →  e2e-driven-iteration
      (1)                       (2)                      (3)                    (4)
```

**Never skip forward.** If step 1 says "no real signal," you stop — no code edit.

## 1. reproducibility-first — is the signal real?

- **Branch A (reproduce):** run the failing case ≥2 more times. 2/2 pass → noise, no edit. 1/2 fails → flaky, real but intermittent. 2/2 fail → deterministic.
- **Branch B (unambiguous log):** only if **all three** hold: cause named in the error message, explains every part of the failure, maps to a known contract violation (binary, not probabilistic).

**Red flag:** "probably a blip, just rerun" as primary action. Rerun is a *diagnostic*, not a *decision*.

## 2. root-cause-by-layer — walk all 5 layers out loud

1. **Symptom** — verbatim error
2. **Mechanism** — which code path
3. **Contract** — whose contract, explicit or implicit
4. **Structural origin** — which architectural layer; inside or leaking-across boundary
5. **Conceptual origin** — which design concept misapplied (separation of concerns, ownership, single source of truth, explicit-over-implicit)

**You do not have a root cause until you can state layers 4 AND 5.** Fix goes at the named layer, not higher, not lower.

## 3. loss-backprop-lens — calibrate step size

| Loss pattern | Step size |
|---|---|
| One-off bug, clear contract | Local tweak at named boundary |
| Same defect recurring across ≥3 commits / tests | **Architectural edit** — redraw the boundary |
| Same fix-loop sibling-breaking 3+ times | Local-minimum trap — zoom out, don't keep patching |

**Red flag:** "5 small patches in 90 min in one function." Stop. Architectural edit next.

## 4. e2e-driven-iteration — measure every iteration

```
each iteration k:
  1. Run failing E2E → loss_k
  2. Compare to loss_{k-1} → Δloss_k (down = progress, flat = rethink, up = revert)
  3. Invoke root-cause-by-layer
  4. One focused edit at named layer
  5. Rerun E2E → loss_{k+1}
```

**Never:**
- Skip the start-of-iteration run ("last edit probably worked")
- Batch multiple edits between E2E runs (can't attribute)
- Close on unit-green alone when E2E was the failing signal

## Forbidden fix patterns (shared across skills)

- `try/except` around the failing call
- `hasattr` or duck-type shim
- Retry loop around flakiness
- `@pytest.mark.skip` / `xfail`
- Widened regex / threshold / whitelist
- Hardcoded "works for now" value
- `TODO: clean up later`

## Close

E2E green + regularizers honored (contracts, docs, layer boundaries) + regression test added at the layer of the root cause (not the symptom layer) → hand off to [`release.md`](./release.md) for the pre-commit gate (`docs-as-definition-of-done`).

## Full skill references

- [`../../skills/reproducibility-first/SKILL.md`](../../skills/reproducibility-first/SKILL.md)
- [`../../skills/root-cause-by-layer/SKILL.md`](../../skills/root-cause-by-layer/SKILL.md)
- [`../../skills/loss-backprop-lens/SKILL.md`](../../skills/loss-backprop-lens/SKILL.md)
- [`../../skills/e2e-driven-iteration/SKILL.md`](../../skills/e2e-driven-iteration/SKILL.md)
