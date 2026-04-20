# Baseline observations — drift-detection

**Status: NOT YET CAPTURED.** Scaffolded with v0.2.

**Hypothesized baseline:** agent proposes a qualitative "architecture review" or surveys the team. No structured scan, no concrete indicators, no list output. "Looks healthy" or "needs refactoring" — both un-actionable answers.

**Hypothesized skill-loaded behavior:** agent proposes running the seven drift indicators as a structured scan (manually or via `scripts/drift-scan.py`), collects the output as a fixable list, triages each row (immediate fix vs method-evolution signal), and sets a recurring cadence (weekly / at release candidates) rather than treating this as a one-off.
