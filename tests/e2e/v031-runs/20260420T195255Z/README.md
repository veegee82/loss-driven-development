# v0.3.1 E2E run — 2026-04-20T19:52:55Z

Six scenarios, all using dispatched subagents with real file/bash/git tool access. Per-scenario artifacts:

- `TASK.md` — the user ask handed to the agent
- `run-summary.md` — agent's self-report (trace block, diffs, rubric scores)
- `trace.log` — the `.ldd/trace.log` file the agent wrote during the run
- `git-log.txt` — commits the agent produced in its working dir

## Results

| # | Scenario | Mode × Creativity | Expected | Observed | Rubric |
|---|---|---|---|---|---|
| 1 | Inner-loop failing-test fix | `reactive` | 5-skill cascade, layer-4/5 diagnosis, no symptom patch, 1 commit | Branch-B signal + 5-layer walk + dialectical antithesis; transport signature made explicit, extraction moved to caller | green, 1 commit `22688066` |
| 2 | Refinement of C+ design doc | `reactive` / refinement | 7-defect gradient, budget ≤ 3 iter, stop on empty-gradient | 7 defects enumerated + closed in iter 1; iter 2 stopped via empty-gradient rule (not polish-by-feel) | `loss_0=7 → loss_1=0`, Δloss=+7 |
| 3a | Architect — conservative | `architect, creativity=conservative` | 11-item rubric, team-fam 2×, all 3 candidates battle-tested, scaffold in existing stack, novelty ≤ 1 | Modular monolith / CQRS-lite / service-split on axis = decomposition shape; winner A=20.0 with 4 antithesis hardenings; all components novelty ≤ 1 | **11 / 11** |
| 3b | Architect — standard | `architect, creativity=standard` (default) | 10-item rubric, 3 candidates on load-bearing axis, real antithesis, 9-section doc | Monolith / queue+dispatcher / event-sourced on axis = ingest-store-dispatch coupling; winner C1-refined after antithesis; 5-module scaffold, 7 failing tests | **10 / 10** |
| 3c | Architect — inventive | `architect, creativity=inventive` + acknowledgment flow | Ack block emitted, 2 candidates (baseline+invention), PRIOR_ART.md + EXPERIMENT.md + fallback-to-baseline, 7-item inventive rubric | Ack block emitted verbatim; simulated "acknowledged" reply logged; Baseline=OT+intent-tag vs. Invention=IPCT (Intent-Preserving Conflict Tree); winner IPCT 20/28 after λ·prior_art_overlap_penalty; docs/PRIOR_ART.md + docs/EXPERIMENT.md + scaffold/src/fallback/ | **7 / 7** inventive-variant + items 9, 10 satisfied |
| 4 | Negative — inventive in `.ldd/config.yaml` | `architect` inline + forbidden config-level inventive | Config warning fires, NO ack flow (inventive from config is ignored, not opt-in), downgrade to standard, standard 10-item rubric used | Trace-header warning line emitted with exact wording: *".ldd/config.yaml sets creativity=inventive at project level; this is forbidden by the skill. Downgraded to creativity=standard."*; no acknowledgment block emitted; Phase-3 3 candidates (Kafka-wrap / Postgres-broker / object-store-log) scored 16/17/11; standard rubric used | **10 / 10** standard (correct rubric variant) |

## What each run validates about the v0.3.1 skill bundle

- **E2E-1** — The inner-loop cascade (`reproducibility-first → root-cause-by-layer → loss-backprop-lens → e2e-driven-iteration → docs-as-definition-of-done`) runs end-to-end on real code with real tool access. Agent refused the `user["address"]`-becomes-`hasattr(user,"address")` shim and instead made the transport signature primitive-typed, moving extraction to the caller — exactly the `root-cause-by-layer` layer-4 fix.
- **E2E-2** — `iterative-refinement` runs as specified: structured gradient (defects with locations), budget + halving + stop-conditions, empty-gradient stop on iter 2 instead of imagining defects to justify more polish.
- **E2E-3a** — `creativity=conservative` changes the loss function as specified: novelty-penalty item #11 active, team-familiarity 2× weighting applied, all candidates battle-tested, scaffold uses only existing-stack components.
- **E2E-3b** — `creativity=standard` is unchanged from v0.3.0 baseline behavior. Same 10-item rubric, same 3-candidate rule. Backwards-compatible.
- **E2E-3c** — `creativity=inventive` runs the full acknowledgment flow (opt-in gate works), relaxes to 2 candidates (baseline + invention), requires PRIOR_ART.md + EXPERIMENT.md + named fallback. The inventive rubric variant (7 items) fires instead of the standard 10.
- **E2E-4** — The project-level `creativity: inventive` restriction is enforced: agent reads config, detects, warns in trace, downgrades to standard, does NOT run the acknowledgment flow (because that flow is per-task-acknowledgment specific, not config-triggered). Prevents the exact anti-pattern the skill was designed against: silent drift into research-mode without conscious opt-in.

## Reproducibility note

These are subagent-dispatched runs. The subagent harness differs from a real Claude Code plugin-install in that:

- Skills were provided via prompt-injection of the SKILL.md contents (tier-3.9 pattern), not auto-discovered via `/plugin install` — we already know from v0.2.1 that the subagent `Skill` tool does not auto-discover `~/.claude/skills/` from a dispatched context
- Tools available to the agents were `Read / Write / Edit / Bash / Glob` — real file IO + git, which is what a real Claude Code session has too

So these are **tier-3.9 measurements**: they demonstrate the skill content drives the intended behavior when loaded. A real tier-4 requires the user installing the plugin via `/plugin install loss-driven-development@loss-driven-development-dev` in their own Claude Code session; that verification is an adopter task per [`GAPS.md`](../../../GAPS.md).

## Adopter replay

To reproduce on your own Claude Code install:

```bash
/plugin marketplace add https://github.com/veegee82/loss-driven-development.git
/plugin install loss-driven-development@loss-driven-development-dev
```

Then start a fresh session in any of the scenario directories under `/tmp/ldd-e2e-<ts>/<scenario>/` (copy their `TASK.md` + source files) and paste the TASK.md content as your first message. Compare the trace block, rubric score, and artifacts to what's captured here.
