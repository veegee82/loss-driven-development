---
description: Clear all session-level LDD hyperparameter overrides set via /ldd-set. Does NOT touch .ldd/config.yaml or bundle defaults.
---

Drop every session override accumulated this session. Respond with a table of what was cleared (key → previous session value). If no session overrides were active, say "no session overrides to clear" — do not report the project-file or bundle-default values (those are unaffected).

After reset, hint at how to inspect the now-effective config:

> Run `/loss-driven-development:ldd-config` to see which layer each value now comes from.

Do not touch `.ldd/config.yaml` or the bundle defaults. This command is session-scoped only. To change the project-level defaults, edit `.ldd/config.yaml` directly (git-committable) — see `docs/ldd/hyperparameters.md` §"Project config".
