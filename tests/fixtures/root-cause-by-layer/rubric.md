# Rubric: root-cause-by-layer

Score each item as `0` (satisfied) or `1` (violated). `Δloss = baseline_violations − with_skill_violations`.

## Rubric items

1. **Symptom quoted verbatim.** `1` if the response paraphrases the error instead of copying it.
2. **Mechanism named.** `1` if the response does not identify the specific code path (`user["email"]` on a dataclass) that produced the error.
3. **Contract named.** `1` if the response does not state whose contract was violated and whether it was explicit or implicit (e.g., "`send_notification` has an implicit mapping-style input contract; `workflow` delivers a dataclass — two implicit contracts collide").
4. **Structural origin named.** `1` if the response does not identify the architectural layer boundary (domain ↔ integration / transport).
5. **Conceptual origin named.** `1` if the response does not name the design concept being violated (separation-of-concerns, explicit-over-implicit, ownership, …).
6. **Fix at the named layer.** `1` if the fix is at a different layer than the diagnosis (e.g., diagnosis says "boundary leak" but the fix is a local `try/except` in `notifier.py`).
7. **No symptom-patch patterns.** `1` if the fix uses any of: `try/except`, `hasattr`-or-subscript shim, widened regex/whitelist, retry loop, `@pytest.mark.skip` / `xfail`, duck-typing compat shim.
8. **No deferred-cleanup language.** `1` if the response contains "clean up later," "tech debt," "interim fix," "follow-up PR," "TODO: refactor," or equivalent.

**Max violations: 8.** A passing run (`Δloss ≥ 4`) halves the violation count.
