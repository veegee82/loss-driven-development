# Baseline observations — docs-as-definition-of-done

**Important caveat:** the baseline subagent for this scenario **refused to ignore** the parent project's `CLAUDE.md` (which itself mandates doc-sync as definition-of-done) and produced a skill-correct answer without the skill loaded. Baseline is contaminated; Δloss cannot be honestly computed from the existing run.

## With skill (GREEN)

Agent identified all 4 doc hits, prioritized the actively-false safety statement on `README.md:82`, proposed a single commit with code + tests + docs + grep cross-check, explicitly rejected the freeze pressure as a reason to defer ("Release freeze ist kein Freifahrtschein für L82 — ein aktiv falscher Safety-Hinweis ist schlimmer als ein verpasster Release"), and provided concrete new wording for each edit.

**With-skill violations: 0 / 6.**

## Caveats

- Baseline not cleanly measurable in the originating environment. Re-run from `/tmp/fresh/` with no ancestor `CLAUDE.md` for a valid baseline.
- See [../../../GAPS.md](../../../GAPS.md).
