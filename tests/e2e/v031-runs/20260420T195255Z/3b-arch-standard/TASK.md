# Task

`LDD[mode=architect]:` design a webhook replay service.

**Requirement** (verbatim from product):
> "We need a service that stores every webhook we receive from our partners (Shopify, Stripe, a few smaller ones) and lets ops re-deliver any subset of them to internal consumers on demand. The main use-case is when a downstream service goes down and we need to replay the last N hours of events once it's back. Current traffic is ~500 webhooks/minute across all partners. It needs to be queryable by partner, event-type, and time-range. Ops should be able to do replays via a simple CLI or UI — doesn't have to be fancy. We'd like it to go live in 6–8 weeks. Team of two engineers owns it."

Nothing else scoped. No existing code. Stack-neutral — you pick.

Deliver under the **standard** creativity level (default; no explicit flag needed but also not escalating to inventive).

Emit the full LDD trace block with:
- `mode: architect, creativity: standard` in the header
- `Loss-fn : L = rubric_violations` line (the baseline; λ=0)
- All 5 phases reported
- 10-item rubric score
- Hand-off line on close

Append trace lines to `.ldd/trace.log`. Write `run-summary.md` on close.
