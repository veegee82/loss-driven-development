# Skill-Anwendung: E2E-Driven-Iteration

Walk durch die fünf Schritte:

1. **Run E2E → loss_k**: FEHLT. Nach Iteration 1 (Index) kein E2E gelaufen. Nach Iteration 2 (filter-Entfernung) kein E2E gelaufen. Nur Unit-Tests.
2. **Compare Δloss_k**: Unmöglich. loss_1 und loss_2 wurden nie gemessen.
3. **Diagnose**: ungültig — basiert auf Code-Inspektion, nicht auf frischem Loss-Signal.
4. **Fix**: zwei Edits gebatched ohne Attribution. Welcher half? Unbekannt.
5. **Rerun E2E → loss_{k+1}**: FEHLT.

## Red Flags getroffen
- "Last edit probably worked, don't need to re-run" — Iteration 1 → 2 ohne E2E
- "Let me batch 3 fixes and run once" — Index + filter zusammen, keine Attribution
- "Unit test green = done" — Unit deckt TimeoutError nicht ab (das ist ein Laufzeit-/Integrations-Symptom)

## Entscheidung: NICHT committen

E2E muss JETZT laufen, bevor irgendetwas festgeschrieben wird. Gradient ist verloren, aber der aktuelle Zustand (beide Edits drin) ist messbar.

## Exakte Kommandos

```bash
pytest tests/e2e/ -k "get_orders" -v --tb=short --durations=5
```

Dann je nach Ergebnis:

```bash
# Wenn grün: Regularizer prüfen, dann commit
# (docs / contracts / layer boundaries unverändert durch diese Edits)

# Wenn rot: nicht committen, Δloss diagnostizieren
git stash   # filter-Edit raus
pytest tests/e2e/ -k "get_orders" -v  # isoliert Index-Effekt
```

Close erst wenn E2E grün **und** Regularizer (Contracts, Docs, Layer-Boundaries) honoriert.
