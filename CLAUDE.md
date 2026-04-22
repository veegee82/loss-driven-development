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

## `dist/` — must be up-to-date on every push to `main` and every release (load-bearing)

Everything under `dist/` is **generated from the skills, docs, and scripts**. It is also what **end users download and install** — `dist/web-bundle/ldd-skill.zip` is the single-file artifact for Claude Web / Claude Desktop, and the GitHub release workflow attaches it verbatim. A `dist/` that is out of sync with source means the release ships stale skill bodies while `git log` shows the newer ones; adopters then run a version the repo cannot reproduce.

### Two hard rules

1. **Every push to `main` must land with `dist/` in sync.** Before `git commit` on any change that touches files `dist/` is derived from — `skills/**/SKILL.md`, `docs/ldd/**`, `scripts/level_scorer.py`, or the build script itself — run:

   ```bash
   python3 scripts/build_web_bundle.py
   ```

   and stage the regenerated `dist/web-bundle/` in the same commit. The pre-commit hook at `.githooks/pre-commit` blocks any commit that leaves `dist/web-bundle/` drifted (`test_build_web_bundle.py::test_check_passes_after_fresh_build` runs on every CI PR as a second gate). A `git push origin main` with drift is a protocol failure — never bypass with `--no-verify`.

2. **Every release (tag + GitHub release) must rebuild `dist/` from scratch immediately before the tag commit.** Run the full regeneration sequence as the **last** step of the release prep, after version bumps and CHANGELOG updates:

   ```bash
   python3 scripts/build_web_bundle.py                # rebuild dist/web-bundle/ + ldd-skill.zip
   python3 -m pytest scripts/test_build_web_bundle.py # confirm no drift vs. source
   git diff --stat dist/                              # inspect what changed
   ```

   Only then create the release commit. If `dist/` changed and the release tag was already cut, the tag is invalid — delete it locally, rebuild, retag. A GitHub release whose attached `ldd-skill.zip` does not byte-match the tagged `dist/web-bundle/ldd-skill.zip` is a silent lie to every user who downloads it.

### Why the rules bite this hard

The web-bundle is the **primary install path for Claude Web and Claude Desktop users** — they cannot use the CLI plugin format. For those users, `dist/web-bundle/ldd-skill.zip` *is* the product. If `dist/` drifts behind `skills/`, those users get a different plugin than the one the CHANGELOG and README describe, and cannot reproduce the `Δloss_bundle = 0.561` number that the plugin's honest-accounting story relies on. The two gates above exist so that drift cannot ship.

### What NOT to do

- **Don't** hand-edit files under `dist/web-bundle/`. The build script is the source of truth; manual edits will be wiped on the next rebuild and a commit that edits `dist/` directly without editing source is a `method-evolution` trigger (the build pipeline has a gap the agent is routing around).
- **Don't** skip the rebuild "because only one SKILL.md changed." The bundle carries cross-references; a single skill edit can reshape references in others.
- **Don't** cut a release without running `scripts/build_web_bundle.py` even if CI passed — CI validates the pre-push snapshot, not the release-tag snapshot. The two can diverge if the release workflow bumps `plugin.json` after CI ran.
- **Don't** assume `git status` being clean implies `dist/` is in sync — a `dist/` rebuild that produces identical bytes shows nothing in `git status`. Run the pytest check explicitly when in doubt.

## Promotional Gist — must stay in sync with the repo (load-bearing)

The project ships a **six-file promotional Gist** at [gist.github.com/veegee82/3b9fc46107905ec4c369de71c68efc84](https://gist.github.com/veegee82/3b9fc46107905ec4c369de71c68efc84) that acts as the single shareable entry-point for new users. It is linked from the top of `README.md` and from the author's GitHub profile pin. Drift between Gist and repo means every social-media / HN / Reddit visitor who lands on the Gist first gets stale facts about a plugin that has since moved on.

**Files in the Gist (narrative order; renames break cross-anchors, don't rename without updating all `#file-*` links):**

| # | Filename | What it carries |
|---|---|---|
| 01 | `01-README.md` | Overview, the 16-skill composition, cross-links to the other five files |
| 02 | `02-LDD-IN-60-SECONDS.md` | TL;DR pitch + Before/After worked example |
| 03 | `03-INSTALL.md` | Per-host install commands (Claude Code, Web/Desktop ZIP, Codex, Gemini CLI, Aider/Cursor/…) |
| 04 | `04-TRIGGER-PHRASES.md` | Literal trigger table, thinking-levels scorer, inline + natural-language overrides |
| 05 | `05-PHILOSOPHY.md` | The "gradient descent for agents" framing, four parameter spaces, hyperparameters, regularizers |
| 06 | `06-EVIDENCE.md` | `Δloss_bundle = 0.561` reproduction command, per-skill breakdown, falsifiability statement |

### The hard rule

Any commit that changes a fact cited in the Gist must land with a matching Gist update in the same work session — not a follow-up commit, not a next-week TODO. The Gist is **not** a cached copy you can let drift; it is an external distribution surface with its own readership.

A fact "cited in the Gist" is any of:

1. **The version number** (`v0.13.1` appears in `01-README.md` and `06-EVIDENCE.md`). Bump in `plugin.json`/`marketplace.json`/`gemini-extension.json` ⇒ bump in both Gist files.
2. **The skill count** (`16 skills` = `12 disciplines + 4 infrastructure`, cited across all six Gist files). Adding or removing a skill from `skills/` ⇒ update every mention.
3. **`Δloss_bundle = 0.561`** (cited in `01-README.md` and `06-EVIDENCE.md`). Any fixture recapture that shifts the number ⇒ Gist update is mandatory, same commit-window as the repo's five other citation sites.
4. **The reproduction command** (`python3 scripts/compute-loss-bundle.py`, expected-output block in `06-EVIDENCE.md`). If the script's CLI / output format changes ⇒ refresh the expected-output block verbatim.
5. **The trigger-phrase table** (mirrored in `04-TRIGGER-PHRASES.md`). Any edit to the table in `skills/using-ldd/SKILL.md` § "Trigger phrases" ⇒ update the Gist.
6. **Install commands per host** (`03-INSTALL.md`). Any change to the plugin's install story, new host, deprecated host ⇒ update.
7. **The 9-signal scorer** (summarized in `04-TRIGGER-PHRASES.md`). Rebalancing weights or renaming signals in `scripts/level_scorer.py` or `skills/using-ldd/SKILL.md` ⇒ update the Gist's summary.
8. **The four-loop model** (`05-PHILOSOPHY.md`). Adding or renaming a parameter axis ⇒ update.

### How to update

The Gist is a Git repo. One-shot flow:

```bash
cd /tmp && rm -rf ldd-gist-work
git clone https://gist.github.com/3b9fc46107905ec4c369de71c68efc84.git ldd-gist-work
cd ldd-gist-work
# edit the relevant files (preserve the numeric prefixes — they set the display order)
git add -A
git commit -m "sync to repo <short-sha> — <what changed>"
git push
```

For a single-file tweak, `gh gist edit 3b9fc46107905ec4c369de71c68efc84 -f <filename> < local-file.md` is the shortcut; confirm with `gh gist view 3b9fc46107905ec4c369de71c68efc84 --files`.

### What NOT to do

- **Don't** delete and recreate the Gist on every version bump. The URL is pinned on the GitHub profile and linked from `README.md`; a new URL silently breaks both. Always edit in place.
- **Don't** rename the `NN-Title.md` files without updating every `#file-NN-title-md` cross-anchor in the other files (nine links exist across the six files; they are how the "Start here" navigation in `01-README.md` works).
- **Don't** paste raw skill bodies into the Gist. The Gist is promotional summary with links back to the repo — never duplication. A Gist that carries full `SKILL.md` content is a second source of truth that will drift; the only permitted skill content in the Gist is the composition table in `01-README.md` and the trigger-phrase summary in `04-TRIGGER-PHRASES.md`, both of which are short and deliberately de-normalized.
- **Don't** forget the `Δloss_bundle` citation when bumping the number in repo. It is the single number most likely to silently diverge between repo and Gist, because it lives in the README (×5), `evaluation.md`, `tests/README.md`, `.claude-plugin/plugin.json`, `SUBMISSION.md` — plus `01-README.md` and `06-EVIDENCE.md` in the Gist. All eight must move together.

### Why the rule bites this hard

The Gist is the project's **first impression**. It is what Hacker News, Reddit, Discord, and X traffic land on when someone shares the URL. If the Gist says "16 skills · Δloss_bundle = 0.561" while the repo now ships 17 skills at 0.584, the visitor's first read of LDD is a lie — and they will usually not open the repo to find out. Every missed update erodes the honest-accounting story the repo spends real infrastructure (`GAPS.md`, `evaluation.md`, the pre-commit drift gate, the five-site citation check) to protect.

## General conventions (not `Δloss_bundle`, `dist/`, or Gist-sync specific)

- Skill bodies under `skills/*/SKILL.md` are the user-visible disciplines; keep them concise (`~500` words guidance; dense skills can exceed it with comment).
- Methodology text has one canonical home: `docs/ldd/`. Don't duplicate it into skill bodies or README.
- Pre-commit hooks live in `.githooks/`. **Auto-activated by the plugin's SessionStart hook** (via `core.hooksPath=.githooks` set during the Signal-B install path for the LDD-plugin's own source repo) — you do not need to run `git config core.hooksPath .githooks` manually. If you have your own `core.hooksPath` already set to something else, the installer respects that choice and surfaces a note; in that case add `.githooks/pre-commit` to your own hooks path or fall back to the manual command. Never bypass hooks via `--no-verify` without an explicit reason in the commit message.
