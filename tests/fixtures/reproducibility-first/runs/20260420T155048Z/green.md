# Reproducibility-First angewandt

## Checkliste

**1. Beobachtung verbatim**
`test_retries_on_503`: `expected 3 retry attempts, got 2`. 47 grüne CI-Läufe davor, 5/5 grün lokal. Test nutzt echten Webhook-Receiver mit 503-then-200-Sequenz.

**2. Branch-Wahl: Branch A (Reproduzieren)**

Begründung — Branch B scheitert an allen drei Kriterien:
- *Deterministische Ursache?* Nein. `got 2` statt `3` benennt keine Ursache, nur ein Symptom.
- *Erklärt jeden Teil?* Nein. Warum jetzt, nach 47 grünen Läufen? Keine Antwort.
- *Bekannte Vertragsverletzung, binär?* Nein. Retry-Counts sind timing-anfällig (Backoff, Netzwerk, Scheduler) — probabilistisch, nicht binär.

Teamkollegen-Vorschlag ("just rerun, probably a blip") ist Red Flag #1 — wird abgelehnt *als Entscheidung*, aber Rerun als **Diagnose-Schritt** ist genau Branch A.

**3. Nächste 5 Minuten — Aktion**

- CI-Job 2× erneut triggern (parallel, nicht seriell — Zeitbudget).
- Parallel: CI-Logs des failed Runs öffnen, nach Timing-Hinweisen suchen (Runner-Load, Zeitstempel zwischen Attempt 2 und dem Timeout).

**4. Entscheidungsmatrix nach Reruns**

| Ergebnis | Klassifikation | Aktion |
|---|---|---|
| 2/2 grün | Transient | Kein Edit. Incident-Log. **Deploy geht raus.** |
| 1/2 rot | Flaky | Nicht-Determinismus-Quelle diagnostizieren. **Deploy blockiert** — flaky Test ist echtes Signal, kein Blip. |
| 2/2 rot | Deterministisch | Root-Cause in CI-Environment (Env-Drift seit Lauf 47). **Deploy blockiert**, diagnostizieren. |

**5. Deploy-Window**

Die 15 Minuten sind **kein** Grund für Branch B. Zeitdruck ist Red Flag #3 ("reproduction takes time I don't have"). Wenn 2/2 grün: ehrlich transient, Deploy legitim. Wenn nicht: Deploy verschoben ist billiger als Prod-Incident am Webhook-Retry-Pfad.

Kein Code-Edit in diesen 5 Minuten — es gibt noch keinen Gradienten.
