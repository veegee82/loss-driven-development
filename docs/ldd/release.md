# Release — pre-commit / pre-merge / pre-release discipline

Load this when the user says: "ready to commit", "commit this", "ready to merge", "ship it", "declare done", "push this", "release candidate", "cut a release".

This closes **every** loop — release-gating is cross-cutting in the [Gradient Descent for Agents](../theory.md) frame: whichever of the four gradients you just descended, you don't ship until the regularizer holds (docs synced, no cumulative drift, ship/don't-ship counter-case heard).

## Skills

Primary: [`docs-as-definition-of-done`](../../skills/docs-as-definition-of-done/SKILL.md) (every commit — cross-cutting). Secondary: [`drift-detection`](../../skills/drift-detection/SKILL.md) (release candidate / weekly / version bump — outer-loop upstream check). Tertiary: [`dialectical-reasoning`](../../skills/dialectical-reasoning/SKILL.md) (for ship/don't-ship final call — cross-cutting).

## Per-commit gate — `docs-as-definition-of-done`

A code change is **not done** until every documentation statement that the change invalidated has been updated **in the same logical task**.

Before `git commit`:

1. Run `git status` and `git diff --stat`
2. For each public-surface change (signature, flag, config key, default, behavior, error message), grep docs for the old symbol / text
3. Update every hit **now** — staged in the same commit as the code

### Sync checklist

| Change | Check and update |
|---|---|
| Renamed / moved / deleted symbol | Docs referencing old symbol / path |
| Signature change | Docstrings, API docs, examples |
| CLI flag / command change | README usage, help output, cli-reference, tutorials |
| Config schema / default change | README quickstart, schema, example configs |
| Error / log message change | Troubleshooting, FAQ, examples |
| Behavior change under named condition | Section naming that condition |
| Exception raised change | Docstring `Raises:`, caller try/except examples |
| Security / privacy / compliance change | Security, policy docs, customer promises |
| Architecture / ownership change | Architecture docs, CODEOWNERS |

## Red flags — STOP, about to ship stale docs

- "I'll do the docs in a follow-up PR"
- "Release freeze, I'll catch up tomorrow" *(doc edit is 30s; wrong safety claim in prod is bigger)*
- "Tests pass, that's what matters"
- Committing with only code/test files staged when docs reference the changed behavior
- `TODO: update docs` as the doc update

## Release-candidate gate — `drift-detection` (periodic, not per commit)

Every release candidate / weekly / before version bump: run the 7-indicator scan ([`../../scripts/drift-scan.py`](../../scripts/drift-scan.py) or manually):

1. Identifier drift
2. Contract drift
3. Layer drift
4. Doc-model drift
5. Rubric drift
6. Test/spec drift
7. Defaults drift

Output is a **list of findings, not a health score**. Each row triaged: immediate fix vs `method-evolution` candidate.

## Final ship/don't-ship call — `dialectical-reasoning`

When the release is non-trivial (new public surface, schema migration, behavior change to a documented flow), run a final thesis/antithesis/synthesis pass. The antithesis is the 30-sec rollback cost vs. the 2-week incident cost of shipping a stale safety claim or an unnoticed drift.

## Close

`git commit` as one logical unit (code + tests + docs), push, tag the release. If a drift-scan found non-trivial issues, do NOT ship — the scan is a hard gate before releases, a soft gate between them.

## Full skill references

- [`../../skills/docs-as-definition-of-done/SKILL.md`](../../skills/docs-as-definition-of-done/SKILL.md)
- [`../../skills/drift-detection/SKILL.md`](../../skills/drift-detection/SKILL.md)
- [`../../skills/dialectical-reasoning/SKILL.md`](../../skills/dialectical-reasoning/SKILL.md)
