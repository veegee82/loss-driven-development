# Baseline observations — e2e-driven-iteration

**Status: NOT YET CAPTURED.** See `../reproducibility-first/baseline-notes.md` for the capture workflow.

**Hypothesized baseline:** agent commits based on unit-test green, does not rerun the original failing E2E, does not compute Δloss between iterations. Ships, and either (a) CI catches it on PR, or (b) the fix is partial and the E2E fails again on the next run.

**Hypothesized skill-loaded behavior:** agent explicitly reruns the E2E that was the original signal, notices whether iter-1 alone (index) or iter-2 alone (filter removal) was sufficient, and closes only when the E2E is green AND regularizers are honored.
