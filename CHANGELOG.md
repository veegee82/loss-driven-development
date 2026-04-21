# Changelog

All notable changes to this plugin are documented here. Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/). This project uses [Semantic Versioning](https://semver.org/).

## [0.5.2] — 2026-04-21

### Added — trace-based project memory (`aggregate` / `suggest` / `check` / `similar` / `health`)

v0.5.1 made per-iteration trace emission cheap. v0.5.2 makes the accumulating trace.log **useful** as a project-level memory — the agent reads historical patterns to detect plateaus and flag regressive skill-choices, without biasing the loss itself.

Five new CLI subcommands on top of the v0.5.1 tool:

```bash
python -m ldd_trace aggregate --project .          # write .ldd/project_memory.json
python -m ldd_trace health    --project .          # human-readable project state
python -m ldd_trace suggest   --project . [--top-n 5]  # empirical skill ranking
python -m ldd_trace check     --project . [--next-skill X]  # in-flight warnings
python -m ldd_trace similar   --project . --files a,b,c     # file-overlap retrieval
```

`ldd_trace close` auto-runs `aggregate` as a side effect — project_memory.json is never stale.

### Core design constraint — memory must not bias the loss

The loss function `L(θ)` (rubric violations) stays pure. Memory informs NAVIGATION (which skill next, when to escalate, where to warm-start) but NEVER redefines progress.

Four explicit bias-guards, each tested:

| Bias | Risk | Guard |
|---|---|---|
| Survivorship | "complete-only" skill stats inflate effectiveness | aggregate counts **every** terminal state; per-skill `by_terminal` breakdown exposed |
| Regression-to-mean | Skills that fire on hard bugs show trivially higher Δ | report both `delta_mean_abs` **and** `delta_mean_relative` (Δ / prev_loss) |
| Recency drift | Weighting recent heavier masks skill-version drift | both lifetime and last-30-day windows shown; caller chooses |
| Confirmation | Agent self-curation skews aggregate | aggregation is deterministic on raw trace; agent never filters |

Each guard is both documented (`bias_guards` block in `project_memory.json`) and test-enforced (`test_e2e_memory.py::TestAggregatorBiasGuards`).

### The two use cases the memory unlocks

1. **Plateau detection** — current task shows ≥ 2 consecutive near-zero Δ → `check` emits HIGH-severity warning citing historical resolvers ("past plateaus resolved by root-cause-by-layer (3) over 3 observations"). Agent sees empirical exit-path, not just "you're stuck."
2. **Wrong-decision detection** — next planned skill has ≥ 30% historical regression-rate → `check` warns before the bad step. Scoped to same project (no cross-project contamination).

Both are retrospectively validated against the narralog trace: at narralog's actual i3 (streak=1) the check correctly produces **no** warning (false-positive guard holds); at a simulated counterfactual i4 (streak=2) the check **would have** flagged the plateau and named root-cause-by-layer as the historical resolver — matching what narralog's actual i4 manually arrived at via method-evolution.

### Storage shape

```
.ldd/
  trace.log              ← v0.5.1 — append-only log of iterations + closes
  project_memory.json    ← v0.5.2 — deterministic aggregate, auto-refreshed
```

Per-project by default. No cross-project global aggregate (explicit design choice for privacy + no signal-mixing). Session state is ephemeral — recovered from trace.log at task start via `ldd_trace status`.

### Tests — 16 new, 37 total

- 5 bias-guard correctness tests (survivorship, by-terminal split, relative delta, windows, metadata)
- 3 aggregator metric tests (task_shape, retry-variant no-progress signature, plateau-pattern detection)
- 2 plateau-detection tests (triggers when streak ≥ 2; false-positive guard on healthy task)
- 2 wrong-decision tests (warns on regressive skill; no-warn on good skill)
- 1 over-budget detection test (k ≥ p95 triggers escalation warning)
- 2 retrospective-against-narralog tests (narralog i3 correctly doesn't fire; counterfactual i4 does)
- 1 skill-ranking test (workhorse skill outranks bad skill)

All green: `python -m pytest scripts/ldd_trace/ -q` → 37 passed.

## [0.5.1] — 2026-04-21

### Added — `scripts/ldd_trace/` CLI tool for per-iteration trace emission

v0.5.0 mandated per-iteration emission of the trace block (see `using-ldd/SKILL.md` § "When to emit"). v0.5.1 makes that mandate **cheap to honor**: a Python package with a five-subcommand CLI (`init` / `append` / `close` / `render` / `status`) that persists to `.ldd/trace.log` and re-renders the full block on every write.

```bash
python -m ldd_trace init   --project . --task "bug fix" --loops inner
python -m ldd_trace append --project . --loop inner --auto-k \
    --skill e2e-driven-iteration --action "what changed" \
    --loss-norm 0.333 --raw 1/3 --loss-type rate
python -m ldd_trace close  --project . --loop inner --terminal complete \
    --layer "3: contract · 5: invariant" --docs synced
```

Rendering logic was **lifted verbatim from `scripts/demo-trace-chart.py`** into `scripts/ldd_trace/renderer.py` — no behavior change versus the v0.5.0 demo output. The demo script remains as the educational reference.

### Changed — per-iteration trace emission reclassified from "should" to hard step

Empirical finding behind v0.5.1: on a real multi-iteration task (narralog, 2026-04-21), the v0.5.0 per-iteration emission mandate was silently dropped across 4 iterations despite the spec. The mandate lived only in `using-ldd/SKILL.md` § "When to emit" — the iteration-performing skills didn't cross-reference it, so the agent finished iterations without rendering the trajectory.

Method-evolution fix across three skills:

- `skills/e2e-driven-iteration/SKILL.md` — the Five-Step Iteration becomes **Six-Step**; step 6 is `Emit trace` with an explicit `python -m ldd_trace append ...` call. "Do not skip step 6" is added with a one-paragraph rationale. The red-flags list gains `"I'll emit the trace block at the end of the whole task"` → NO, per-iteration is a data-visibility requirement. The checklist grows from 7 to 8 items (step 7 = emit; step 8 = close).
- `skills/loop-driven-engineering/SKILL.md` — `Sub-Skill Dispatch` table gains two rows: `ldd_trace status` at task start (recover prior iteration state from `.ldd/trace.log`), and `ldd_trace append` at iteration close (emission contract).
- `skills/using-ldd/SKILL.md` — adds a RED FLAGS table immediately after § "When to emit" with four concrete rationalizations and the correct response for each. Adds a "bidirectional" subsection: trace.log is now READ at task start for state recovery, not just written.

### Why a tool, not just a stricter spec

v0.5.0's spec was already strict — the violation was tooling-driven. Per-iteration emission asked the agent to hand-render ~30 lines of ASCII (sparkline + chart + per-iteration info lines) on every loss measurement. Under time pressure that overhead got discounted. v0.5.1 reduces the cost to one shell command: if the agent can run `pytest`, it can run `python -m ldd_trace append ...`. Spec strictness is now matched by ergonomic strictness.

### Bidirectional trace.log

Prior to v0.5.1 the trace.log was write-only (persistence for grep / audit). v0.5.1 makes it the **source of truth** for iteration-state recovery across sessions:

- `python -m ldd_trace status --project .` → machine-readable `next_k` per loop + last `loss_norm` per loop
- `python -m ldd_trace render --project .` → full trace block reconstituted from log alone

A new session starting on an existing project reads trace.log first and resumes at the correct `k` instead of starting at `i1` again.

### Tests

- `scripts/ldd_trace/test_ldd_trace.py` — 21 unit + integration tests, pytest-driven:
  - Pure renderer functions (sparkline, trend_arrow, mini_chart) against the §"Rendering recipe" in `using-ldd/SKILL.md`
  - Store round-trip (init → append → close → render) on pytest's `tmp_path`
  - CLI subprocess tests for all five subcommands
  - Three-channel consistency: sparkline last bar + chart last marker + final iteration's loss must agree on the same number

All green: `python -m pytest scripts/ldd_trace/test_ldd_trace.py -q` → 21 passed.

## [0.5.0] — 2026-04-21

### Added — trace visualization (sparkline, mini chart, mode+info line, trend arrow)

The LDD trace block now carries four parallel channels alongside the numeric loss values, making the trajectory AND the per-iteration skill work both auditable at a glance. Closes two friction points in one release: "loss numbers on their own are hard to eyeball" (solved by sparkline + chart) and "the user can't tell which skill did what per iteration" (solved by the mandatory mode-indicator + info line).

**The four channels** (in `skills/using-ldd/SKILL.md` § Loss visualization — sparkline, mini chart, mode+info line, trend arrow):

| Channel | Mandatory at | Purpose |
|---|---|---|
| **Trajectory sparkline** (`▁▂▃▄▅▆▇█`, auto-scaled, zero → `·`) | ≥ 2 iterations | Micro-dynamics — 8-level resolution across the full run |
| **Trend arrow** (`↓` / `↑` / `→`, first-vs-last delta) | ≥ 2 iterations | Net direction at the end of the sparkline; distinct from per-step `Δ` arrows |
| **Mini ASCII loss-curve chart** (`┤` y-axis + `●` markers + labeled x-axis) | ≥ 3 iterations | Macro-trajectory with `0.25`-step snap and per-phase labels (`i1`, `r2`, `o1`) |
| **Per-iteration mode + info line** | every iteration | The iteration label carries a mode parenthetical — `(inner, reactive)`, `Phase p1 (architect, <creativity>)` with creativity ∈ {standard, conservative, inventive}, `(refine)`, or `(outer)` — so the reader can tell which discipline was active per iteration. An indented continuation line carries `*<skill-name>*` + a one-line description of what concrete change the iteration produced. Gives the user an audit trail without scrolling elsewhere |

The sparkline and chart MUST agree on the final `loss_k`. The SKILL.md section specifies a deterministic rendering recipe (sparkline indexing via `round(v/max * 7)`, chart snap via `floor(v/0.25 + 0.5) * 0.25`, trend arrow via first-vs-last delta with ±0.005 plateau band, mode-indicator grammar per loop/mode) so renders are reproducible across agents and sessions.

**Non-monotonic trajectories are first-class.** The end-to-end trend arrow is computed from `last − first`, so `0.667 → 0.833 → 0.167` (i1→i2 regression, i2→i3 recovery) still reads `↓` at the end of the sparkline — even though the per-step `Δ` arrow on i2 correctly shows `↑` locally. Sparkline arrow = net direction; per-step `Δ` arrow = local direction. The SKILL.md text calls this distinction out explicitly to prevent conflation.

**Mode-indicator grammar.** The parenthetical on each iteration line uses the four-way split: `(inner, reactive)` for default inner work, `Phase pk (architect, <creativity>)` when architect-mode replaces the inner loop (note: word `Phase` not `Iteration`, signaling the 5-phase protocol), `(refine)` for y-axis deliverable work, `(outer)` for θ-axis method work. A session that runs architect inner → hands off to reactive inner renders both in the same trace: `Phase p1..p5` followed by `Iteration i1..i<k>`.

**Why no per-iteration `█`/`░` bar** (explicit design non-choice). An earlier draft of the spec included a 20-char magnitude bar per iteration. It was removed because information density is strictly worse than the mode+info line — bars re-encode data already carried by the sparkline and chart, while the mode+info line carries *new* information (which skill, what action) the user cannot reconstruct from loss numbers alone.

### Changed — trace emission cadence: once-per-task → after every iteration (live)

Prior to v0.5.0 the rule was "emit ONE block per task; re-emit at message end if the task spans messages." The rule is now **emit after every iteration** during live task execution — the user watches the loss descend in real time rather than waiting until task close. Consecutive emissions grow monotonically by exactly one iteration (plus one sparkline char, one chart column, and a possibly-flipped trend arrow).

The per-skill-invocation anti-pattern is preserved: within one iteration multiple skills may fire (e.g. `reproducibility-first` + `root-cause-by-layer`), they still share ONE block emitted at iteration close. The rule discriminates iterations from skill-invocations, not the emission from existence.

**Post-hoc reconstruction exception** (new in v0.5.0): when the user hands you a completed task's iteration data and asks you to render the trace, emit ONE final block — there are no real iterations happening, so repeating the growing block would print the same data 3× without adding information. The `tests/fixtures/using-ldd-trace-visualization/` fixture exercises this exception (all three scenarios are post-hoc reconstructions).

**Budget trade-off acknowledged.** Per-iteration emission multiplies trace-block token cost by the iteration count. For tight-context sessions, the existing compression rule (info-lines collapsed to skill-name-only) mitigates; the visualization channels are never dropped. The audit-transparency gain was judged worth the token cost — a user who cannot see their loop's progress until close is a user who will ask "is it still running?" after 90 seconds of silence.

### Changed — trace block example in README reflects v0.5.0 format

The inline trace example in `README.md` § "Live trace — see the loop happen in real time" was replaced with a 6-iteration three-loop run rendered in full v0.5.0 format (sparkline, chart, per-iteration mode+info + `Δ` column, close). A new subsection `#### Mental model — the four visible channels` follows, explaining each granularity and the consistency rule, and linking to the authoritative SKILL.md section and the v0.5.0 fixture.

### Tests — new fixture `tests/fixtures/using-ldd-trace-visualization/`

Three RED/GREEN scenarios, captured at `deepseek/deepseek-chat-v3.1`, T=0.7, via OpenRouter (cheaper than v0.4.0's `gpt-5-mini`; total capture spend ≈ $0.05). Scored against a 4-item rubric measuring channel emission + mode-indicator grammar + per-iteration skill-info + net-direction-arrow correctness.

| Scenario | RED loss | GREEN loss | Δloss |
|---|---:|---:|---:|
| inner-three-iters | 4 / 4 | 2 / 4 | **+2** |
| all-three-loops | 4 / 4 | 0 / 4 | **+4** |
| regression-and-recovery | 4 / 4 | 0 / 4 | **+4** |

Every scenario clears the Δloss ≥ 1 release gate. Bundle-scoped normalized Δloss for this fixture: `0.833`, well above the bundle target of `≥ 0.30`. Scenario `inner-three-iters` lost 2 items in GREEN (mini chart and trend arrow not emitted — base-model rendering skip at T=0.7 on the shortest scenario); sparkline and mode+info line transferred cleanly. Scenarios 2 and 3 hit all four items; scenario 3 validates the subtlest discriminator — GREEN correctly reads the non-monotonic prompt and emits `↓` end-to-end while keeping the per-step `Δ +0.167 ↑` on i2.

### Updated

- `skills/using-ldd/SKILL.md` — new `### Loss visualization — sparkline, mini chart, mode+info line, trend arrow` subsection (4-channel mandatory thresholds, mode-indicator grammar, deterministic rendering recipe, 6-iteration reactive-inner worked example, architect→inner hand-off worked example, non-monotonic-trajectory rule, compression rule, loss-type-specific rendering)
- `README.md` — trace example block replaced with v0.5.0 format; new `#### Mental model — the four visible channels` subsection with fixture link + measurement summary
- `tests/fixtures/using-ldd-trace-visualization/` — new fixture (scenario.md + rubric.md + runs/20260421T122248Z-clean/)
- `scripts/demo-trace-chart.py` — new demo helper, renders the trace block from a hard-coded 6-iteration task with mode-indicator + info lines. Pure renderer, no skill invocations, no LLM calls; functions (`sparkline`, `mini_chart`, `trend_arrow`, `render_trace`) are directly liftable into a future renderer module under `skills/using-ldd/`
- `scripts/demo-e2e-trace.py` — new executed-demo helper. Optimizes a real Python function (`compute_average`) through all three loops (inner → refine → outer), running actual rubric checks against actual compiled code at every iteration and re-rendering the trace block after each. Supports `--fast` for piping; default pauses 0.5s per iteration for live-feel. No simulation — every loss value is computed from `exec()` + call + rubric assertion
- `scripts/README.md` — new rows for both demo helpers
- `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json`, `gemini-extension.json` — version bumped `0.4.0` → `0.5.0`

## [0.4.0] — 2026-04-21

### Added — auto-dispatch for architect-mode

The coding agent can now enter architect-mode **on its own** when the task description carries enough structural signals — without the user having to type `LDD[mode=architect]:`, invoke `/ldd-architect`, or use an explicit trigger phrase. Closes the "user described greenfield but didn't know the magic word" failure mode.

**The 6-signal scorer** (in `skills/using-ldd/SKILL.md` § Auto-dispatch for architect-mode): greenfield `+3`, names ≥ 3 new components `+2`, cross-layer scope `+2`, ambiguous requirements `+2`, explicit bugfix `−5`, single-file known-solution `−3`. Weighted sum ≥ 4 → architect-mode. Hard gate, not average; tie-break at exactly 4 goes architect.

**Creativity inference** from the same task signals: regulatory / compliance / no-new-tech / tight team+deadline cues → `conservative`; research / novelty / "invent" / "experiment" cues → `inventive`; neither → `standard` (default). Conservative beats inventive on ties. The per-task acknowledgment flow for `inventive` is unchanged — auto-dispatch proposes the level but does not bypass the ack gate; without a literal `acknowledged` reply, the run silently downgrades to `standard`.

**Explicit user triggers always win.** Precedence order (highest first): inline `LDD[mode=…]` / `LDD[creativity=…]` flags > `/ldd-architect` command arg > trigger-phrase match > auto-dispatch (this pipeline) > bundle default. `LDD[mode=reactive]:` on a task with auto-score 6 stays reactive.

### Changed — trace header extended with dispatch source

Every architect-mode trace block now carries a `Dispatched:` line naming one of `inline-flag`, `command`, `trigger-phrase: "<phrase>"`, or `auto (signals: <top-2 by absolute weight>)`. Silent auto-dispatch is a trace-integrity violation — the user must be able to see WHY architect-mode was entered and override with one follow-up message. Example:

```
│ Dispatched : auto (signals: greenfield=+3, cross-layer=+2)
│ mode: architect, creativity: standard
```

### Changed — README mental-model wiring

New subsection `Mental model — the auto-dispatch flow` under the architect-mode README block. Linked mental model per LDD's own docs-as-DoD rule: cites `skills/using-ldd/SKILL.md` (trigger table), `skills/architect-mode/SKILL.md` § creativity, `docs/ldd/convergence.md` (loss-function framing), `docs/ldd/hyperparameters.md` (precedence). Embeds an SVG of the Task → Signal-extraction → Score → {mode, creativity, ack-flow} → Trace-echo pipeline (`docs/diagrams/architect-auto-dispatch.svg`; self-contained, no `feDropShadow`, GitHub-safe).

### Tests — new fixture `tests/fixtures/architect-mode-auto-dispatch/`

Four RED/GREEN scenarios, captured at `openai/gpt-5-mini`, T=0.7, via `scripts/capture-red-green.py` (new helper — paired RED/GREEN captures with skill content as system-message on the GREEN side). Scored against a 4-item rubric measuring dispatch-correctness:

| Scenario | RED loss | GREEN loss | Δloss |
|---|---:|---:|---:|
| bugfix-skip | 1 / 4 | 0 / 4 | **+1** |
| greenfield-inventive | 4 / 4 | 0 / 4 | **+4** |
| regulated-conservative | 4 / 4 | 0 / 4 | **+4** |
| typical-standard | 4 / 4 | 0 / 4 | **+4** |

Every scenario clears the Δloss ≥ 1 release gate. Bundle-scoped normalized Δloss for this fixture: `0.813`, above the bundle target of `≥ 0.30`. Dominant driver is the trace-echo discipline (item 3) — the base model has no reason to invent a `Dispatched:` line, so this item flips RED → GREEN in every scenario.

### Updated

- `skills/using-ldd/SKILL.md` — new `## Auto-dispatch for architect-mode` section (scorer, creativity inference, precedence, worked example); trigger-table entry for architect-mode mentions the fourth path; architect trace-block example extended with `Dispatched:` line
- `skills/architect-mode/SKILL.md` — new `## Auto-dispatch by the coding agent` section summarizing the scorer and pointing at the authoritative spec in `using-ldd/SKILL.md`; description field mentions auto-dispatch
- `README.md` — new `### Mental model — the auto-dispatch flow` subsection with SVG
- `docs/diagrams/architect-auto-dispatch.svg` — new diagram, 12 KB, 820 × 940 viewBox, no `feDropShadow`, no external refs
- `tests/fixtures/architect-mode-auto-dispatch/` — new fixture (scenario.md + rubric.md + runs/20260421T002928Z-clean/)
- `scripts/capture-red-green.py` — new paired-capture helper (OpenRouter / OpenAI / Anthropic fallback, retry-once-with-30s-backoff, no `print()`)
- `.claude-plugin/plugin.json` + `.claude-plugin/marketplace.json` + `gemini-extension.json` — version 0.3.2 → 0.4.0

No breaking changes. Existing opt-in paths (inline flag / command / trigger phrases) continue to work unchanged and take precedence over the new auto-dispatch.

## [0.3.2] — 2026-04-20

### Changed — normalized loss as canonical trace form

Every LDD loss value in the trace block and `.ldd/trace.log` now displays as **normalized [0, 1] primary + raw `(N/max)` secondary**. Replaces the v0.3.1 absolute-integer form (`loss_0 = 3`, `Δloss = +3`) with `loss_0 = 0.375  (3/8 violations)`.

**Why.** Skills have different rubric-maxes: `e2e-driven-iteration` has 5 items, `architect-mode` has 10. Comparing `Δloss = +3` (e2e) to `Δloss = +6` (architect) was apples-to-oranges; `0.600` vs. `0.600` is directly comparable. The raw `(N/max)` in parens keeps actionability — the user still sees "3 of 8 items remain open."

**Three display modes**, chosen per task by the shape of the measurement, named on a new `Loss-type` header line:

- `normalized-rubric` — `loss = violations / rubric_max` → float in [0, 1] plus raw in parens (default for most skills)
- `rate` — signal already in [0, 1] (flake rate, coverage) → single float, no re-normalization
- `absolute-<unit>` — unbounded continuous signal (latency, throughput) → absolute value with unit, no normalization (normalizing an unbounded value invents a denominator and produces fake precision)

**Anti-patterns now spelled out explicitly in `skills/using-ldd/SKILL.md`:**

- Never display a normalized float without the raw denominator in parens — `loss_0 = 0.375` alone hides that it's `3/8`
- Never normalize a count that has no natural max (latency, commit counts, token usage) — those stay `absolute-<unit>`

### Changed — aggregate target simplified

`Δloss_bundle` target moves from absolute (`≥ 2.0 mean violations removed per skill`) to **normalized (`≥ 0.30`** — each skill removes ≥ 30 % of rubric violations that appear without it). Current measured: **`Δloss_bundle = 0.561`** across all 11 skills — target met with margin. Raw absolute mean (3.91, v0.3.1 form) retained in git history but no longer cited.

Per-skill normalized Δloss ranges from 0.250 (`loop-driven-engineering`, partial-contamination baseline) to 1.000 (`architect-mode`). `tests/README.md` now leads with the normalized column; raw `(N/max)` kept for audit.

### Plugin-reference conformance — final audit

Full audit against `https://code.claude.com/docs/en/plugins-reference`:

- **Manifest** — `name` required field present. All recommended optional fields present: `version`, `description`, `author` (with `url`), `homepage`, `repository`, `license`, `keywords`.
- **Marketplace** — `$schema`, `name`, `description`, `owner` (with `url`), `plugins` array with per-entry `name`, `description`, `version`, `source`, `category`, `homepage`, `author`. Matches the shape used by plugins already accepted in `claude-plugins-official`.
- **Skills** — 12 `skills/<name>/SKILL.md` files, each with `name` + `description` frontmatter; directory name matches `name` field in every case (verified via script).
- **Commands** — 7 `commands/*.md` files, each with `description` frontmatter.
- **Structure** — `.claude-plugin/` contains only `plugin.json` and `marketplace.json`; all component dirs at plugin root. Zero violations of the "components at root, not inside `.claude-plugin/`" rule.
- **No agents / hooks / MCP / LSP / monitors** — none needed for this plugin; fields omitted cleanly (all optional per reference).

### Updated

- `skills/using-ldd/SKILL.md` — trace-block spec rewritten for normalized loss + `Loss-type` header line + 3-mode spec + anti-patterns
- `skills/architect-mode/SKILL.md` — trace example updated; Phase 4 scoring cells now show `0.778 (14/18)` form
- `evaluation.md` — target reformulated to `≥ 0.30` normalized; measured `0.561`; "why normalized" section added
- `tests/README.md` — per-skill table leads with normalized Δloss column; raw `(N/max)` kept for audit
- `docs/ldd/convergence.md` — new §5 "Loss display" explaining the three modes
- `README.md` — hero badge updated to `Δloss_bundle = 0.561 (normalized)`; measured-section reframed
- `.claude-plugin/plugin.json` — `description` updated; version 0.3.1 → 0.3.2
- `.claude-plugin/marketplace.json` + `gemini-extension.json` — version 0.3.2

No breaking changes. Existing traces in `tests/e2e/v031-runs/` are historical artifacts and retain the old absolute display; all new traces emit the normalized form.

## [0.3.1] — 2026-04-20

### Added — creativity levels for architect-mode

Architect-mode gains a `creativity` sub-parameter with three discrete levels, framed consistently with LDD's neural-code-network metaphor. The levels are **three different loss functions**, not three amounts of freedom:

- **`conservative`** — `L = rubric_violations + λ · novelty_penalty`. Enterprise / no-new-tech / small team. All 3 candidates must be battle-tested; component novelty penalized; team-familiarity weighted 2× in scoring. Adds rubric item #11 (novelty penalty).
- **`standard`** (default) — `L = rubric_violations`. The current v0.3.0 architect-mode behavior, unchanged.
- **`inventive`** — `L = rubric_violations_reduced + λ · prior_art_overlap_penalty`. Research / prototype. Novelty rewarded, prior-art penalized, with mandatory experiment-validation path + fallback-to-standard baseline. Rubric items 1–2 may relax; items 5–8 replaced by invention-specific criteria (#I1 differentiation-from-prior-art, #I2 experiment-validation-path, #I3 fallback-to-baseline-named). Requires per-task user acknowledgment before running.

### Hard guards against moving-target-loss

- **No integer tuning.** Three named alternatives only — "dial up until creative" is the exact drift anti-pattern LDD fights. Discrete objectives prevent it.
- **No level-switching mid-task.** Mixing two loss functions in one gradient descent is incoherent optimization. Agent refuses and requires task restart.
- **`inventive` is per-task only.** Cannot be set as project-level default in `.ldd/config.yaml`; agent ignores and downgrades to `standard` with a trace warning if it finds one.
- **Default stays `standard`.** No behavior change for existing architect-mode users.

### Integration

- `skills/architect-mode/SKILL.md`: new §§ Creativity levels, Level-switch prohibition, Project-level config restriction, plus description updated to mention the three levels
- `docs/ldd/hyperparameters.md`: `creativity` added as 5th knob (architect-mode-only sub-parameter)
- `docs/ldd/architect.md`: new § Creativity levels
- `docs/ldd/convergence.md`: new § 7 framing creativity as loss-function selection within the ML lens
- `docs/ldd/config.example.yaml`: `creativity: standard` example + `inventive` restriction comment
- `skills/using-ldd/SKILL.md`: inline syntax `LDD[mode=architect, creativity=<level>]:`, trace-block header now shows `Loss-fn` line naming the active objective
- `commands/ldd-architect.md`: accepts positional or `creativity=<level>` argument, runs acknowledgment flow for `inventive`
- `evaluation.md`: per-level rubric variants (`R_arch_standard` / `R_arch_conservative` / `R_arch_inventive`)
- README: new "Creativity — three loss functions, not a freedom dial" sub-section; hyperparameter table extended to 5 rows; install-in-30-seconds block unchanged

### Rationale

The user asked for a "freedom dial from 1=structural to 10=new paradigms". Dialectical review rejected the 1–10 framing:

- 10 grades would not have 10 measurably distinct behaviors (grades 6 vs. 7 would blur)
- Integer knobs invite "tune until output feels creative" — the exact moving-target-loss pattern every LDD skill fights
- Creativity isn't a quantity; it's a **choice of objective**. Architecture optimizing for "minimize novelty" and architecture optimizing for "maximize differentiation from prior art" are two different problems, not two degrees of the same problem

Three discrete loss functions solve the original intent (letting the user pick between conservative / standard / inventive postures) without opening a drift attack surface.

### Version

Bumped to `0.3.1` across `plugin.json`, `marketplace.json`, `gemini-extension.json`. No breaking changes — `standard` (default) behaves identically to v0.3.0 architect-mode.

## [0.3.0] — 2026-04-20

### Added — architect mode

- **New opt-in skill `architect-mode`** (`skills/architect-mode/SKILL.md`) — flips LDD from reactive debugging into constructive architecture when the user signals design intent. Rigid 5-phase protocol: Constraint extraction → Non-goals → 3 candidates on a load-bearing axis → Scoring + dialectical pass → Deliverable (doc + compilable scaffold + failing tests per component + measurable success criteria). Explicit hand-off back to default reactive mode after Phase 5 closes.
- **10-item architect rubric** in `evaluation.md` and `tests/fixtures/architect-mode/rubric.md`.
- **Fourth hyperparameter `mode`** (`reactive` | `architect`) exposed across the existing three-path config system: inline `LDD[mode=architect]:`, `/loss-driven-development:ldd-architect` command, `.ldd/config.yaml`'s `mode` key, `/ldd-set mode=architect`. Documented in `docs/ldd/hyperparameters.md` and `docs/ldd/config.example.yaml`.
- **New slash command** `/loss-driven-development:ldd-architect` — activates architect mode for the next task, reverts to reactive after hand-off.
- **New task-type MD** `docs/ldd/architect.md` added to the dispatch table in `docs/ldd/task-types.md`.
- **Architect-variant trace block** in `skills/using-ldd/SKILL.md` — shows phases (1–5) instead of iterations, includes Mode header, emits explicit hand-off line at close.
- **Escalation protocol** for phases that cannot complete cleanly (too few constraints, fewer than 3 candidates, scoring ties within 10 %, rubric violations ≥ 3/10).
- **Trigger phrases** in `skills/using-ldd/SKILL.md` dispatch table: "design X", "architect Y", "greenfield", "from scratch", "how should I structure", "propose an architecture", "decompose this", "what's the right shape for X".

### Measured

- `architect-mode` captured clean RED + GREEN via direct API (`openai/gpt-5-mini`, T=0.7). **RED violations 10/10, GREEN violations 0/10, Δloss = +10** — **largest effect size in the bundle.** Raw artifacts at `tests/fixtures/architect-mode/runs/20260420T190302Z-clean/`.
- `Δloss_bundle` recomputed across all 11 skills: **3.91 absolute (mean per skill), 0.561 relative**. Target `≥ 2.0` met with margin (was 3.30 at n=10 in v0.2.1).

### Updated

- README hero badge: Δloss_bundle 3.30 → 3.91; skill count badge "10 + entry" → "10 + architect + entry".
- README adds an "Architect mode — Claude as designer, not just debugger (opt-in)" section with 5-phase summary, activation paths, hand-off, and effect-size citation.
- `AGENTS.md`, `GEMINI.md` extended to twelve skills.
- Hyperparameter table in README adds `mode` row.
- Version bumped to `0.3.0` across `plugin.json`, `marketplace.json`, `gemini-extension.json`.

### Rationale

LDD v0.2.x was entirely reactive — it assumed code existed and iterated on loss signals. That framing missed the input-X-to-output-Y space between problem and delivered system: decomposition, contracts, non-goals, architecture. `architect-mode` fills exactly that gap, but as **opt-in** — default behavior for routine debugging/refactoring is unchanged; the 5-phase ceremony only runs when the user signals greenfield design intent.

## [0.2.1] — 2026-04-20

### Added

- **`docs/ldd/`** — canonical methodology directory. Task-type-specific compressed MDs (`debugging.md`, `design-decisions.md`, `refactor.md`, `refinement.md`, `release.md`, `incident.md`, `method-maintenance.md`) with `task-types.md` as the dispatch table. Prevents methodology drift across README / skill bodies / user-project docs. Moved `convergence.md` and `in-awp.md` here; updated all cross-links.
- **`scripts/capture-clean-baseline.py`** — portable tool to capture RED baselines via direct LLM API (OpenRouter / OpenAI / Anthropic). Sidesteps the Claude-Code-subagent contamination problem that previously blocked `docs-as-definition-of-done` measurement.
- **Tier-3.9 E2E capture** — `tests/e2e/scenario-01-refactor/runs/20260420T164505Z/`: skills installed at `~/.claude/skills/` (not prompt-injected), subagent discovered and applied them at runtime, 7/7 rubric items, loop closed k=1/5.
- **N=3 distribution demo** — `tests/fixtures/root-cause-by-layer/runs/20260420T165603Z-clean-N3/`: 3 independent RED captures via `capture-clean-baseline.py`, all same failure mode (type-tolerance shim), stddev ≈ 0.5.
- **Second scenario** for `root-cause-by-layer` (`tests/fixtures/root-cause-by-layer/scenario-2/`): different domain (rate-limiter precondition) exercising the same skill. Partial scenario-design-bias reduction.

### Changed

- `Δloss_bundle` recomputed across all 10 skills (was 9 of 10 in v0.2.0): **3.30 absolute (mean per skill), 0.517 relative**. Target `≥ 2.0` met with margin. Previously-blocked `docs-as-definition-of-done` now clean-measured at Δloss = +2.
- `evaluation.md` reflects n=10 aggregate.
- `tests/README.md` published per-skill table updated.
- `GAPS.md` rewritten: what's actually closed, what's still open, what only adopters can close.
- Version bumped to `0.2.1` across `plugin.json`, `marketplace.json`, `gemini-extension.json`.

### Still pending

- Real tier-4 (`/plugin install` in a live Claude Code / Codex / Gemini CLI session) — needs an adopter.
- N≥10 distributions per skill — infrastructure in place; needs community runs.
- Independent (non-author) scenario design — community PRs welcome.

## [0.2.0] — 2026-04-20

### Added

- **Three-loop model.** Formalised the inner (code), refinement (deliverable), and outer (method) loops as three orthogonal optimization axes. Mental model in [`docs/ldd/convergence.md`](./docs/ldd/convergence.md).
- **Five new skills** extending v0.1's inner-loop focus:
  - `reproducibility-first` — gate before any gradient use
  - `e2e-driven-iteration` — measure-per-iteration inner-loop rhythm
  - `iterative-refinement` — y-axis SGD on deliverables
  - `method-evolution` — outer-loop θ-axis SGD on skills / rubrics
  - `drift-detection` — periodic full-repo scan for cumulative drift
- **Six diagrams** as Graphviz SVGs (GitHub-renderer-compatible, no `feDropShadow`):
  - `three-loops.svg`
  - `convergence-vs-divergence.svg`
  - `code-drift-mechanism.svg`
  - `skill-dispatch-flow.svg`
  - `mental-model-ldd.svg`
  - `skills-overview.svg`
- **Case study** [`docs/ldd/in-awp.md`](./docs/ldd/in-awp.md) — one-to-one mapping from LDD skills to their [AWP](https://github.com/veegee82/agent-workflow-protocol) origins + a concrete debugging walkthrough.
- **Optional Claude-Code tooling** under `scripts/`:
  - `drift-scan.py` — heuristic scanner for seven drift indicators
  - `evolve-skill.sh` — RED/GREEN re-run scaffolder for a skill against its fixture
  - `render-diagrams.sh` — `.dot → .svg` regenerator
- **Rubrics** for all 10 skills in [`evaluation.md`](./evaluation.md).
- **Test fixtures** scaffolded for the 5 new skills (scenario + rubric + baseline-notes per skill) in [`tests/fixtures/`](./tests/fixtures/).

### Changed

- `loop-driven-engineering` now exposes the three loops explicitly (was a single inner loop in v0.1), dispatches the 9 other skills in this plugin at the right moments, and keeps the inner-loop `K_MAX = 5` budget unchanged.
- Install instructions use real `git clone` commands with the published GitHub URL — no more `/path/to/…` placeholders.
- README reshaped for marketing-first: hero with TDD anchor, "Without LDD / With LDD" table, AWP-case-study callout, skills overview SVG replacing the earlier ASCII diagram.
- Version bumped to `0.2.0` across `plugin.json`, `marketplace.json`, and `gemini-extension.json`.

### Known gaps

See [`GAPS.md`](./GAPS.md). Headline items:

- Baselines for the 5 new skills are scaffolded, not captured — RED/GREEN execution pending in a clean environment.
- No tier-4 live-install E2E has been captured end-to-end.
- `Δloss_bundle` is defined in `evaluation.md` but not yet measured.

## [0.1.0] — 2026-04-19

### Added

- Initial 5 skills: `root-cause-by-layer`, `loss-backprop-lens`, `dialectical-reasoning`, `docs-as-definition-of-done`, `loop-driven-engineering`.
- Multi-platform distribution: `.claude-plugin/plugin.json` + `marketplace.json` (Claude Code), `gemini-extension.json` + `GEMINI.md` (Gemini CLI), `AGENTS.md` (Codex + generic).
- `evaluation.md` with per-skill rubrics for the 5 initial skills.
- `tests/fixtures/` for the 5 initial skills (with baseline-contamination caveats documented in per-fixture `baseline-notes.md`).
- `tests/e2e/scenario-01-refactor/` — starter code and task spec for a tier-4 integration run.
- `GAPS.md` honest accounting of what is not verified.
