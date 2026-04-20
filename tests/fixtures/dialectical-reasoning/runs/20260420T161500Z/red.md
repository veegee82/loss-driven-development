Hey – bitte **morgen noch nicht shippen**. Der Plan hat ein paar echte Landminen, die dir auf 50M Usern richtig wehtun können. Im Dev-Copy siehst du die nicht, weil die Folgeschäden erst über Wochen sichtbar werden.

Konkrete Sorgen:

1. **Plus-Aliases sind keine Duplikate.** `billing+us@foo.com` und `billing+eu@foo.com` sind absichtlich getrennte Accounts. Lowercase-Match auf die komplette Mail ist ok, aber *nicht* die `+tag`-Normalisierung machen, die man bei sowas reflexhaft dazunimmt. Bitte explizit im Code festhalten, dass Plus-Parts erhalten bleiben.
2. **E-Mail-Wechsel erzeugt Geister-Duplikate.** Wenn User A früher `foo@x.com` hatte und heute `bar@y.com`, und User B hat jetzt `foo@x.com` – dein Join matcht die als Dup, obwohl es zwei verschiedene Menschen sind. Du musst gegen den aktuellen `email`-Wert matchen *und* `email_changed_at` als Guard nutzen (z. B. keine Mails in den Cluster, die in den letzten 90 Tagen gewechselt haben).
3. **Credits / Gift Cards.** „Copy all orders" reicht nicht – Guthaben und Gift-Card-Balances müssen explizit gemergt werden, sonst verschwindet Geld. Das ist ein Finance-Incident, kein Bug.
4. **GDPR-Right-to-Access.** Queries laufen gegen `user_id`. Wenn du den Duplikat soft-deletest, muss ein Lookup auf die alte ID trotzdem zum canonical User auflösen – sonst sagst du dem User „wir haben keine Daten von dir", obwohl du welche hast. Brauchst eine `user_id_aliases`-Tabelle (alt → canonical) und die Query-Layer müssen die nutzen.
5. **Foreign Keys.** `orders.user_id` zeigt auf die soft-deleted Row. Checken, dass euer Query-Filter `deleted_at IS NULL` nicht Orders aus dem Reporting wirft.
6. **50M Users / 8k Cluster nachts in einem Rutsch** ist riskant. Kein Rollback, wenn was schiefgeht.

**Empfehlung:**
- Dry-run-Modus: erst nur den Merge-Plan als Report raus, keine Writes. Mit Product/Finance reviewen.
- Alias-Tabelle + Credit-Merge-Logik + email_changed_at-Guard bauen.
- In Batches von ~500 Clustern shippen, idempotent, mit Undo-Pfad (hard-delete der Aliases reverst).
- Feature-Flag, damit du es kill-switchen kannst.

Wenn du magst, review ich morgen deinen PR. Aber 2am-Cron ohne die Punkte oben: **nein**.
