Ich habe den E2E-Test noch nicht erneut laufen lassen, seit ich die Fixes gemacht habe. Unit Tests grün heißt nichts — der ursprüngliche Fehler war ein Timeout im E2E, also muss ich dort auch verifizieren.

Vor dem Commit:

```bash
# 1. E2E nochmal laufen lassen (der Test, der ursprünglich fehlschlug)
pytest tests/e2e/ -k "orders" -v

# 2. Timing checken — war cap=30s, also schauen wir wie lange es jetzt dauert
pytest tests/e2e/ -k "orders" -v --durations=10

# 3. Status vor Commit ansehen
git status
git diff
```

Erst wenn der E2E grün ist, committen. Wenn er immer noch failt oder grenzwertig langsam ist (z.B. 28s), ist das Problem nicht gelöst — dann weitersuchen statt committen.

Auch kurz prüfen: habe ich beide Änderungen (Index + redundanter Filter) wirklich beide gebraucht, oder war eine schon ausreichend? Das ist aber nach dem grünen E2E, nicht davor.
