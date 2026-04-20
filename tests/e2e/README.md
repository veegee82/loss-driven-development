# End-to-End tests

The fixtures in `../fixtures/` score **text responses** to fixed prompts. That's training loss. This directory defines **test loss**: can the bundle drive an agent through a multi-step task to a correct on-disk artifact?

## What makes a run "E2E"

Per `../../evaluation.md`, all of:

1. **Fresh project, fresh agent.** New directory, no `CLAUDE.md` / `AGENTS.md` (other than this plugin's). No prior conversation state.
2. **Unseen multi-step task.** Not present in any skill's examples.
3. **Must require ≥ 2 skills.** A task solvable with one skill is not an integration test.
4. **Real tool use.** The agent edits files, runs tests, inspects diffs — not just describes what it would do.
5. **Artifacts persisted on disk.** Transcript, proposed diff, test output. Inspected post-hoc against the rubric.
6. **Terminal status.** Exactly one of `{complete, partial, failed, aborted}`.

## Reference scenario: `scenario-01-refactor/`

See the subdirectory for the full task specification. Short version:

**Task:** a small Python package has three files. An integration test fails with a specific error. The agent is asked to "fix the bug and ship."

**What a good LDD-run looks like:**
- Iteration 1: invokes `root-cause-by-layer`, diagnoses to layer 4/5, proposes fix at the named layer — no `try/except` / `hasattr` / retry patterns in the diff.
- Iteration 2: runs tier-1 (lint/type), tier-2 (unit), then the originally-failing test. Green.
- Close: invokes `docs-as-definition-of-done`, updates the docstring/README that referenced the old behavior, commits code + test + docs as one logical unit.

**Rubric** (scored against on-disk artifacts):
1. Failing test passes after the fix.
2. No new lint / type errors introduced.
3. Fix at the right layer (inspect the diff: does it live where the 5-layer diagnosis said, or somewhere else?).
4. No symptom-patch patterns in the diff.
5. Docs updated in the same commit.
6. No TODO / "follow-up" language in the commit message.
7. Terminal status: `complete`.

## Running an E2E manually

This bundle does not ship an automated E2E harness. To run one:

1. `mkdir /tmp/ldd-e2e-$(date +%s) && cd $_`
2. Copy the scenario's starting files (see `scenario-01-refactor/starter/`) into the directory.
3. Install the bundle (per the host agent's install instructions — see `../../README.md`).
4. Start an agent session in this directory. Paste `scenario-01-refactor/task.md` as the initial user message.
5. Let the agent work to terminal status. Do **not** guide beyond answering direct clarification questions.
6. After termination: copy the git log, diff, and test output into `scenario-01-refactor/run-<timestamp>/`.
7. Score against the rubric above. Record in `scenario-01-refactor/results.md`.

## Status

No E2E runs captured yet. The scenario is specified; the harness is documentation-only. This is Tier-4 work on the test pyramid — honest acknowledgment in [`../../GAPS.md`](../../GAPS.md).
