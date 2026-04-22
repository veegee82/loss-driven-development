---
description: Pre-grant, list, check, or revoke autonomy acks so architect-mode's `creativity=inventive` can fire in autonomous runs (loops, cron, remote agents) without a synchronous human ack. HMAC-signed, scoped to a task family, short-TTL by default.
---

Manage the autonomy ack-cache (v0.13.x Fix 3). Each grant is a signed, scoped, short-lived permission for a specific task family.

## Subcommands

```bash
# Grant — default scope=inventive, default ttl=30d
/ldd-autonomy-ack grant --family billing-schema-changes --ttl 30

# List all grants + validity
/ldd-autonomy-ack list

# Check without activating
/ldd-autonomy-ack check --family billing-schema-changes

# Revoke (immediate; no grace window)
/ldd-autonomy-ack revoke --family billing-schema-changes
```

Under the hood these wrap `python -m ldd_trace ack {grant,revoke,list,check}`.

## What the architect-mode skill does with a valid grant

On autonomous runs where no human can ack, `architect-mode` checks the cache for the current task's family before degrading `inventive → standard`. A valid grant means the inventive loss function activates; an expired, missing, or tampered grant means silent fallback to `standard`, logged in the trace header as `creativity=standard (fallback: no valid ack)`.

## Security properties

- Grants are signed with an HMAC-SHA256 key auto-created at `~/.claude/ldd-acks/.key` (mode 0600). The key never leaves that directory; losing it invalidates **all** grants, which is the intended fail-closed behavior.
- The HMAC covers `family`, `family_hash`, `scope`, `granted_at`, and `ttl_days`. Mutating the on-disk grant (e.g. extending `ttl_days`) breaks the signature and the next `check` fails.
- Grants are scoped to one task family at a time. No global "allow everything" switch exists by design.

## When NOT to use this

- Interactive sessions — a literal-ack reply (`acknowledged`, `ja`, `okay mach`) is cheaper and leaves no persistent state.
- Short-lived tasks inside one session — the inline flag `LDD[creativity=inventive]:` already works without the cache.

The cache is for **unattended** inventive runs only.
