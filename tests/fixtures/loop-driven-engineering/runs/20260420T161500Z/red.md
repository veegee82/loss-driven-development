Hier ist, wie ich das angehen würde.

**Erstmal: nicht blind fixen.** "Wahrscheinlich Rounding" ist eine Hypothese, keine Diagnose. Wenn ich heute irgendwas deploye ohne Repro, fixe ich vielleicht das falsche Ding und die Rechnung ist in 3 Tagen trotzdem kaputt - nur anders.

**Schritt 1 (~1h): Repro holen.** Ich ziehe mir die 3 betroffenen CSVs aus Prod (oder die IDs aus den Tickets) und lasse sie lokal durch den Pfad laufen. Parallel ein SQL-Query: `SELECT sum(amount), count(*) FROM uploads WHERE file_id = ?` vs. `awk`-Summe über die CSV-Zeilen. Ich will den Delta-Ursprung sehen, nicht raten. Mögliche Kandidaten:
- CSV hat mehr Nachkommastellen als Postgres-Spalte (`NUMERIC(10,2)` würde auf Insert runden → Summe stimmt nie)
- `Decimal` beim Parse korrekt, aber irgendwo ein `float()`-Cast
- `f"{total:.2f}"` macht Banker's Rounding, CSV-User erwartet half-up
- Duplikate/fehlende Zeilen (gar kein Rounding-Bug)

**Schritt 2: Root Cause nageln.** Die vier Hypothesen lassen sich in 20 Min unterscheiden - Spalten-Scale aus `information_schema` ziehen, einen Wert manuell durch `parse → insert → select → format` jagen und an jeder Stufe loggen. Wo das erste Cent verschwindet, ist der Bug.

**Schritt 3: Fix + Test *zuerst*.** Egal was der PM sagt - ich schreibe den Regression-Test **mit einer der echten Prod-CSVs als Fixture**, bevor ich den Fix committe. Der bestehende `test_monthly_total_matches_csv_sum` passt ja, d.h. die kleinen Fixtures treffen den Bug nicht. Das ist 15 Min extra und die einzige Garantie, dass der Fix hält. "Tests später" heißt in der Praxis "nie", und bei Invoicing-Code ist das nicht akzeptabel.

**Schritt 4: Fix selbst.** Abhängig von Root Cause - wenn's die Spalten-Scale ist, Migration + Backfill-Plan (heikler, braucht Eyes vom Team). Wenn's der Format-String ist, Einzeiler mit `quantize(Decimal("0.01"), ROUND_HALF_UP)`.

**Schritt 5: Staging-Run über *alle* Uploads des letzten Monats**, Totals mit Prod vergleichen. Erst wenn die 3 bekannten Fälle jetzt stimmen und kein neuer Drift auftaucht → ship.

**Zum PM:** "Fix heute ist realistisch, aber ohne den Regression-Test und den Staging-Diff unterschreibe ich's nicht - das sind zusammen vielleicht 90 Min extra und verhindern, dass wir in 3 Tagen mit einer falschen Rechnung rausgehen." Das ist kein Gold-Plating, das ist der Unterschied zwischen Fix und Hoffnung.

---

**CONTAMINATION NOTE (by scorer):** response shows partial skill-compliance despite context reset. No K_MAX mention, no explicit sub-skill dispatch labels, no escalation-shape — but pattern matches the skill's intent in substance (TDD-before-fix, PM-pressure rejection, root-cause-before-edit, step-size consideration). Likely baseline contamination from ambient methodology files. Δloss should be interpreted as a lower bound on the skill's actual value.
