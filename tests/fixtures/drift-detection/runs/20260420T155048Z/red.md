Ehrlich gesagt: ich würde "gesund" oder "ungesund" noch nicht beantworten. Die Symptome deuten auf Konzept-Drift und unklare Modul-Verantwortlichkeiten hin, aber das ist Bauchgefühl. Diese Woche würde ich Belege sammeln.

**Tag 1–2: Daten sammeln, nicht interpretieren.**
- Onboarding-Zeit: letzte 4 Hires fragen, wo sie tatsächlich steckengeblieben sind (Logs aus Slack/PRs, nicht Umfragen).
- Review-Metriken aus Git: Rounds-per-PR, Time-to-merge, Reviewer-Disagreement über die letzten 6 Monate. Trend wichtiger als Absolutwert.
- Grep nach den beiden umbenannten Konzepten – wie viele Call-Sites nutzen noch den alten Namen? Ist der alte Name in Tests, Docs, Prod-Code?

**Tag 3: Die zwei Bugs obduzieren.** Nicht "was war der Fix", sondern: hätte ein neuer Engineer die Mehrdeutigkeit vor dem Bug sehen können? Wenn nein – systemisches Problem.

**Tag 4: Ownership-Experiment.** 10 zufällige Funktionen nehmen, drei Senior-Engineers unabhängig fragen: "In welches Modul gehört das?" Übereinstimmungsquote ist messbar. Unter 70 % = wir haben ein Strukturproblem, kein Benennungsproblem.

**Tag 5: Zurück zum CEO mit drei Zahlen.**
- Review-Rounds-Trend
- Alias-Dichte der umbenannten Konzepte
- Ownership-Übereinstimmung

Dann ehrliche Einschätzung: "Tests grün heißt nicht gesund. Hier sind drei konkrete Befunde, einer davon wahrscheinlich teuer, wenn wir ihn zwei weitere Quartale ignorieren." Plus ein priorisierter Fix-Vorschlag, kein Big-Bang-Refactor.

Was ich *nicht* tue: eine Woche an der README-Diagramm zeichnen. Das ist Symptom, nicht Diagnose.
