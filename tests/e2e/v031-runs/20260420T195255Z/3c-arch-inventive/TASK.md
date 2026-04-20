# Task

`LDD[mode=architect, creativity=inventive]:` prototype a novel approach to collaborative-cursor conflict resolution for long-form scientific documents. Deliberately do **NOT** use OT (operational transforms) or CRDTs.

**Context:**
- Research lab, not production
- Authors write multi-author scientific papers (math, embedded LaTeX, figure references)
- Known patterns (OT, CRDTs, last-write-wins) are well-understood but give poor "intent preservation" — e.g. two authors rewording the same paragraph with different intents converge to text neither of them wrote
- We want a different paradigm — one where intent is preserved even at the cost of showing conflict to the user for resolution
- Prototype quality is acceptable. Production-readiness is NOT required.

Deliver under the **inventive** creativity level.

**The skill mandates an acknowledgment flow before architecture work:** emit the acknowledgment block verbatim from the skill. For the purposes of this test, assume the user replies with the literal word `acknowledged` and proceed.

After acknowledgment, emit the full LDD trace block with:
- `mode: architect, creativity: inventive` in the header
- `Loss-fn : L = rubric_violations_reduced + λ · prior_art_overlap_penalty` line
- `Acknowledgment : accepted @ <timestamp>` line
- All 5 phases reported (with inventive-adjusted rules — Phase 3 may be 2 candidates: baseline + invention; Phase 5 deliverable must include PRIOR_ART.md + EXPERIMENT.md + fallback-to-baseline path)
- Inventive rubric score (7 items: 1, 2, 3, 4, #I1 differentiation-from-prior-art, #I2 experiment-validation-path, #I3 fallback-to-baseline-named — plus items 9, 10 still apply)
- Hand-off line on close

Append trace lines to `.ldd/trace.log`. Write `run-summary.md` on close.
