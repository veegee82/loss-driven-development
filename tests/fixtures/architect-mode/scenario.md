You are the senior engineer a product team just handed a new ticket. They want to build a **webhook replay service** for their e-commerce platform. Here's what they told you, verbatim:

> "We need a service that stores every webhook we receive from our partners (Shopify, Stripe, a few smaller ones) and lets ops re-deliver any subset of them to internal consumers on demand. The main use-case is when a downstream service goes down and we need to replay the last N hours of events once it's back. Current traffic is ~500 webhooks/minute across all partners. It needs to be queryable by partner, event-type, and time-range. Ops should be able to do replays via a simple CLI or UI — doesn't have to be fancy. We'd like it to go live in 6–8 weeks. Team of two engineers owns it."

Nothing else has been scoped yet. No existing code, no preferred tech stack.

**Your task:** Produce the architecture for this service. Do not write implementation code — this is a design exercise. Deliver:

- A clear design document with sections the product team and the engineering team can both act on
- Explicit decisions about decomposition, storage, and how replay works operationally
- A scaffold of the files / directories the two engineers would start with

Keep the response focused. Aim for a doc the engineers can start implementing against on Monday.
