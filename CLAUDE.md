# CLAUDE.md — project-level directives for agents working on LDD

This file is loaded automatically by Claude Code (and compatible agents) when a session starts in this repository. It contains **project-specific** conventions that override defaults. General LDD methodology lives in `docs/ldd/` and the skill bodies under `skills/` — not here.

## Δloss_bundle — update policy (load-bearing)

`Δloss_bundle` is this plugin's single measured-effect number (currently `0.561`; target `≥ 0.30`). The bundle value is cited in five places (`README.md`, `evaluation.md`, `tests/README.md`, `.claude-plugin/plugin.json`, `SUBMISSION.md`) and must always match what the fixtures actually produce. Definition + reproduction command are in [`README.md` § What Δloss_bundle means](./README.md#what-%CE%94loss_bundle-means).

### Two hard rules

1. **Every commit that touches an input or a citation site must pass the drift gate.** The pre-commit hook at `.githooks/pre-commit` enforces this. A commit that changes any of the following files is blocked unless `python3 scripts/check-loss-bundle-docs.py` passes:
   - `tests/fixtures/*/runs/*/score.md` (raw RED/GREEN scoring)
   - `tests/fixtures/loss-bundle-manifest.json` (which skills count, which run is canonical)
   - `tests/fixtures/aggregate.json` (the snapshot the pre-commit compares against)
   - Any citation site: `README.md`, `evaluation.md`, `tests/README.md`, `.claude-plugin/plugin.json`, `SUBMISSION.md`
   - The scripts themselves: `scripts/compute-loss-bundle.py`, `scripts/check-loss-bundle-docs.py`

   If the check fails, fix the citation site (or revert the fixture change) **in the same commit**. No "fix the docs in a follow-up" exception.

2. **After every major step, recompute and persist the snapshot.** A "major step" is any of:
   - A skill's rubric changes (items added / removed / reworded that affect the count)
   - A fixture's RED or GREEN baseline is recaptured
   - A new skill joins the measurement-eligible set (edit the manifest)
   - A release candidate is being prepared (version bump on `.claude-plugin/plugin.json`)

   In each of those cases, run:

   ```bash
   python3 scripts/compute-loss-bundle.py --write     # refresh tests/fixtures/aggregate.json
   python3 scripts/check-loss-bundle-docs.py          # verify all citations agree
   ```

   If the computed number changed, update the five citation sites to the new value, then commit all of it together (fixtures + aggregate + citation updates) as one logical change. Document the recomputation trigger in the commit message — the `docs-as-definition-of-done` skill applies.

### What NOT to do

- **Don't** hand-edit `tests/fixtures/aggregate.json` to "fix" a drift warning. The snapshot is generated; editing it hides the real problem from the gate. Regenerate via `--write`.
- **Don't** bypass the gate with `git commit --no-verify` to land a mismatched number. If a commit is genuinely exempt (e.g. README typo unrelated to the number), the gate already ignores it — it only fires when a triggering file is staged.
- **Don't** add new citation sites without adding a parser to `scripts/check-loss-bundle-docs.py`. A silently-unchecked citation site is the worst form of drift.
- **Don't** aggregate `architect-mode-auto-dispatch`, `thinking-levels`, or `using-ldd-trace-visualization` into the bundle. Those are behavioral fixtures, not measurement-eligible skills. The manifest is the allow-list.

### Why the rules bite this hard

The plugin's honest-accounting story (`GAPS.md`, `evaluation.md`) rests on the bundle number being real, reproducible, and deliberately updated. A plugin whose README cites `0.561` while the fixtures actually produce `0.412` would silently lie to every adopter who reads it. The gate exists so that lie cannot ship.

## General conventions (not Δloss_bundle specific)

- Skill bodies under `skills/*/SKILL.md` are the user-visible disciplines; keep them concise (`~500` words guidance; dense skills can exceed it with comment).
- Methodology text has one canonical home: `docs/ldd/`. Don't duplicate it into skill bodies or README.
- The web-bundle at `dist/web-bundle/` is generated from the skills; a pre-commit hook already blocks drift there. Run `python3 scripts/build_web_bundle.py` after editing any SKILL.md.
- Pre-commit hooks live in `.githooks/`. **Auto-activated by the plugin's SessionStart hook** (via `core.hooksPath=.githooks` set during the Signal-B install path for the LDD-plugin's own source repo) — you do not need to run `git config core.hooksPath .githooks` manually. If you have your own `core.hooksPath` already set to something else, the installer respects that choice and surfaces a note; in that case add `.githooks/pre-commit` to your own hooks path or fall back to the manual command. Never bypass hooks via `--no-verify` without an explicit reason in the commit message.
