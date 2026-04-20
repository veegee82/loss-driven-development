# Rubric — architect-mode (webhook replay service)

Scoring matches `evaluation.md` § architect-mode. Each item binary: 0 = satisfied, 1 = violated.

1. **All stated requirements covered in a constraint table.** The ask contains 8 requirements (storage of every webhook; replay to internal consumers; re-deliver arbitrary subset; ~500/min throughput; queryability by partner / event-type / time-range; CLI-or-UI interface; 6–8 week timeline; team of 2). Every one appears in Phase 1 output.

2. **Uncertainties named.** The ask is silent on: retention period, authentication to internal consumers, replay ordering guarantees, idempotency of re-delivery, failure handling for a consumer that's still down. At least 3 of these must be flagged explicitly as "user to decide" or "assumption — flagging".

3. **≥ 3 concrete non-goals.** E.g. "not a general-purpose message broker," "not a public-facing API," "not multi-region," "not real-time streaming (batch replay is in scope, live fan-out is not)". ≥ 3 adjacent non-goals stated before design work.

4. **Exactly 3 candidates on a load-bearing axis.** Examples of load-bearing axes for this problem: storage model (relational vs. append-log vs. object-store-with-index), replay mechanism (in-service queue vs. re-publish-to-external-broker vs. synchronous HTTP retry), deployment shape (monolith vs. two-service split). Cosmetic variants (same design, different DB name) fail.

5. **Scoring table explicit.** A 3 × 6 matrix of candidates × {requirements coverage / boundary clarity / evolution paths / dependency explicitness / test strategy / rollback plan} with a per-row total. Not narrative.

6. **Real antithesis on winner.** The winning candidate gets a paragraph (thesis) + ≥ 3 concrete attack vectors (antithesis) + a sharpened synthesis. "It's the best" is not antithesis.

7. **Architecture doc has all 9 Phase-5 subsections.** Problem statement (verbatim quote of the ask); constraint table; non-goals; candidates considered + rejection rationale; chosen design + synthesis; scoring table with totals; integration contracts (every external boundary named — HTTP endpoint shape, storage schema, CLI interface); test strategy; rollback plan.

8. **Scaffold compiles.** A named directory layout with at least empty-but-syntactically-valid source files for each component. Pseudocode (`# TODO implement`) is OK for method bodies but the language / framework / build setup must be real and self-consistent.

9. **≥ 1 failing test per component.** Each named component in the scaffold has at least one failing test naming the expected behavior (e.g. `test_webhook_persisted_on_receipt`, `test_replay_filters_by_partner`, `test_replay_cli_rejects_invalid_timerange`). The failing state is explicit.

10. **Measurable success metric per requirement.** Each of the 8 stated requirements gets a concrete metric: "500 wh/min sustained for 10 min with p99 ingestion < 100 ms", "replay of 10k events completes in < 30 s", etc. Not "fast" or "scalable".

**Max violations: 10.** Passing run: `Δloss ≥ 5` (half the items flipped).
