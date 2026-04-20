# Rubric: dialectical-reasoning

Score each item `0` (satisfied) or `1` (violated).

1. **Thesis explicit.** `1` if the response does not clearly state the proposed plan in its strongest form with the load-bearing assumption named (`lower(email) → same human`).
2. **Antithesis explicit.** `1` if the response does not contain a clearly labeled counter-case section (not "yes, but…" buried in prose).
3. **Antithesis hits ≥ 3 attack vectors.** Vectors: hidden assumptions, edge cases (aliases, email recycling, shared inboxes), contracts under strain (GDPR / financial / FK), second-order effects (irreversibility, blast radius), asymmetric risks.
4. **Synthesis strictly stronger than thesis.** `1` if the synthesis is "ship as planned" with cosmetic tweaks, or if it merely adds a follow-up without narrowing scope / reframing.
5. **Reframe offered when warranted.** `1` if the response does not identify that the problem is not "dedup" but "identity resolution on mutable, legally-loaded keys."
6. **Concrete, reversible alternative proposed.** `1` if the counter-proposal is vague ("think harder") rather than concrete ("append-only link table, not FK rewrites; report-only first; staged rollout").

**Max violations: 6.** Passing run: `Δloss ≥ 3`.
