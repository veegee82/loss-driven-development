# Baseline observations — iterative-refinement

**Status: NOT YET CAPTURED.** Scaffolded with v0.2 release; execution pending.

**Hypothesized baseline:** agent either rewrites from scratch (losing the usable 80%) or ships as-is ("the review will catch issues"). If it "refines," it does so without a structured gradient — polishing by gut feel toward an aesthetic prior. No budget, no stop conditions.

**Hypothesized skill-loaded behavior:** agent enumerates the 6 concrete defects, sets max-iterations ≤ 3, builds the structured gradient, runs one targeted pass at each defect, stops when the defect list is empty or time exhausted, preserves the winning iteration. Does not rewrite from scratch.
