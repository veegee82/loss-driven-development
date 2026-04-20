---
description: Set a session-level LDD hyperparameter override. Syntax — /ldd-set key=value. Non-persisted; clears on session end or via /ldd-reset.
---

Parse the argument as `key=value`. Accepted keys (from `docs/ldd/hyperparameters.md`):

- `k_max` (alias: `k`, `kmax`) — integer 1–20
- `reproduce_runs` (alias: `reproduce`) — integer 0–10 (0 is allowed but will be echoed with a warning)
- `max_refinement_iterations` (alias: `max_refinement`, `refinement`) — integer 1–10

Validate:

1. Key is one of the three exposed knobs. If not, reject with one line pointing at `docs/ldd/hyperparameters.md` §"What is NOT exposed (by design)" — do not silently accept unknown keys.
2. Value parses as a positive integer in range.
3. If value is out of range, reject with the allowed range and no silent clamping.

On acceptance, store the override in session state and respond with exactly:

```
session override set: <canonical-key> = <value>
precedence: this beats .ldd/config.yaml and bundle defaults, loses to inline LDD[...] flags.
```

Session overrides persist until the end of this Claude Code session or until `/loss-driven-development:ldd-reset` is invoked.

If the user runs `/ldd-set` with no argument or just a key, dump the current session overrides (same format as `/ldd-config`'s "session overrides" section).
