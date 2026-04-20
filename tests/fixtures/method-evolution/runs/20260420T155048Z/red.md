Ich würde die Red-Flags-Liste konkret um dieses Rationalisierungs-Muster erweitern, weil drei Vorfälle in einem Monat mit fast identischem Template kein Zufall sind, sondern eine Lücke im Skill.

**Konkret:**

1. **Neuer Red-Flag-Eintrag** in der Liste, ungefähr so formuliert:

   > **Defensive/Interim-Label auf minimaler Änderung.** Wenn ein Fix aus einem einzelnen `try/except`, Retry-Loop, `hasattr`/`getattr`-Shim, Default-Fallback o. ä. besteht UND mit Wörtern wie "interim", "defensive", "tolerant", "robust", "temporary", "for now", "just in case" gelabelt ist: Stopp. Das ist fast immer ein Symptom-Patch, der eine Vertragsverletzung verdeckt. Erforderlich: benenne den verletzten Vertrag (Schnittstelle, Schema, Invariante) und fixe dort — oder begründe explizit, warum der Aufrufer-Contract korrekt ist und die Defensive echt ist.

2. **Gegenbeispiele mitliefern**, damit der Red Flag nicht zu breit greift: legitime `try/except` an echten Vertrauensgrenzen (Netzwerk-I/O, Subprozess-Exit, User-Input-Parsing) sind okay — die drei Tasks waren alle interne Aufrufe, bei denen der Contract fixbar war.

3. **Checkliste** zu den drei Tasks als Mini-Case-Studies ins Skill aufnehmen (A/B/C kurz skizziert mit Symptom → echter Root Cause → richtigem Fix). Konkrete Vorfälle schlagen abstrakte Regeln.

4. **Prompt-seitig** den Rationalisierungs-Detektor verankern: bevor der Agent einen Fix mit "interim/defensive/tolerant/robust" labelt, muss er explizit schreiben, welchen Contract die aktuelle Version verletzt und warum der Fix nicht dort ansetzt. Zwingt den Gedanken an die Oberfläche statt ihn zu verstecken.

5. **Rückwirkend** kurz prüfen, ob weitere vergangene Tasks unter dasselbe Muster fallen — drei gefundene heißt wahrscheinlich mehr ungemeldete.

Kein Rewrite des Skills, nur gezielter Patch an der Stelle, wo die Lücke nachweislich ist.
