---
description: Show the current LDD hyperparameter config — which layer each value comes from (bundle default / project file / session override / inline) with full provenance.
---

Report the effective LDD config as a three-column table: **key**, **effective value**, **source**. The source column must name the concrete layer the value came from: `bundle-default`, `.ldd/config.yaml`, `session (/ldd-set)`, or `inline (last LDD[...])`.

Report the three exposed knobs (see `docs/ldd/hyperparameters.md`):

- `inner.k_max`
- `inner.reproduce_runs`
- `refinement.max_iterations`

Also list, below the table:
- Any `.ldd/config.yaml` path detected (or "none — using bundle defaults")
- Any active session overrides (from prior `/ldd-set` calls this session)

Then, in one line, remind the user of the precedence order:

> Precedence: inline `LDD[...]` > `/ldd-set` > `.ldd/config.yaml` > bundle defaults.

If the user asks about a knob that is NOT in the three exposed ones (e.g. "what about the learning rate"), do not invent a value. Point them at `docs/ldd/hyperparameters.md` §"What is NOT exposed (by design)" and explain why the knob is deliberately absent.

No extra text. This is a glance command, like `git config --list`.
