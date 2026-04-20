# Drift-Scan: Health Assessment

**Antwort auf die CEO-Frage: Nein — grüne CI misst Symptome, nicht strukturelle Gesundheit. Alle vier genannten Beobachtungen sind klassische Drift-Indikatoren.**

## Scan-Plan (7 Indikatoren, mechanisch)

| # | Indikator | Tool | Was gemessen wird |
|---|---|---|---|
| 1 | Identifier-Drift | `grep` Synonym-Sets (User/Account/Principal, Job/Task/Work) | Namens-Varianten pro Konzept |
| 2 | Contract-Drift | AST-Scan: Signaturen pro Funktionsname | Gleiche Funktion, abweichende Argumente |
| 3 | Layer-Drift | Import-Graph vs. `docs/architecture.md` | Kanten, die deklarierte Grenzen kreuzen |
| 4 | Doc-Model-Drift | README-Diagramm-Knoten vs. `ls packages/` | Phantom- / fehlende Module |
| 5 | Rubric-Drift | `git log` auf Rubric/Eval-Dateien, filter fehlendes Δloss | Ungerechtfertigte Edits |
| 6 | Test/Spec-Drift | Spec "MUST"-Klauseln vs. Test-IDs | Normative Promises ohne Test |
| 7 | Defaults-Drift | Config-Keys in README/code/migrations cross-joinen | Divergente Defaults |

## Erwartete Findings (aus Symptom-Signal abgeleitet)

- **#1 hoch**: "drei Namen in einer Woche" + der "zweifach umbenannte" Bug — systematischer Identifier-Drift.
- **#3 mittel-hoch**: PR-Ownership-Disput = Layer-Grenzen sind nicht mehr mit Code kongruent.
- **#4 sicher**: 9 Monate alter README → Diagramm falsifiziert.
- **#2 wahrscheinlich**: Onboarding-Langsamkeit korreliert mit Contract-Divergenz.
- **#5–7**: zunächst unbekannt, Scan entscheidet.

## Triage

| Klasse | Aktion |
|---|---|
| **Immediate fix** (Einzelinstanz) | Alten Namen im Modul X löschen, README-Diagramm regenerieren, Defaults angleichen — Tickets, diese Woche |
| **Method-evolution** (Muster) | Identifier-Drift zeigt fehlende Glossar/Rename-Disziplin → Pre-Commit-Synonym-Linter einführen. Layer-Drift zeigt fehlenden Import-Boundary-Gate → CI-Check aufsetzen |

## Red-Flag-Check

Leerer Scan → rerun. Keine "fix later"-Liste — jede Zeile bekommt Owner+Datum, sonst compoundet es. Kadenz: quartalsweise, nicht einmalig.

**Status an CEO:** CI grün, Struktur erodiert messbar. Wir haben jetzt die Liste; in 2 Wochen Re-Scan zur Verifikation.
