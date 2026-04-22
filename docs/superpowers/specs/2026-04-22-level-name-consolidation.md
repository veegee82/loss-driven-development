# LDD Level+Name Consolidation — `mode=` Removal Spec

**Date:** 2026-04-22
**Status:** accepted, ready for execution
**Target release:** v0.11.0 (breaking trace format change)
**Supersedes within:** `docs/superpowers/specs/2026-04-22-ldd-thinking-levels-design.md` §Dispatch header + §Trace format

## Motivation (one paragraph)

Today the dispatch header and trace log carry three coupled fields — `level` (L0..L4), `mode` (reactive / architect), and `creativity` (conservative / standard / inventive) — even though `mode` is a **pure function of `level`** (L0–L2 ⇒ reactive, L3–L4 ⇒ architect). This is a refactor residue from the pre-thinking-levels design where architect-mode had its own auto-dispatch path. The redundancy costs ~60 characters per trace line, forces a second header line at L3/L4, and makes the user believe `mode=` is a separate user-facing axis when it is not. Creativity, by contrast, is genuinely orthogonal (three values at L3/L4) and stays. This spec removes the redundancy, adds the level-name to the primary axis, and consolidates the display.

## The rule

| Axis | Status after this change |
|---|---|
| **Level (L0..L4)** | Primary. Always displayed with name: `L3/structural`. |
| **Creativity** | Second axis, **only at L3/L4**. Echoed inline in header when applicable. |
| **Mode** | **Derived, no longer displayed, no longer user-facing.** L0–L2 ⇒ reactive, L3–L4 ⇒ architect. |

## Level name mapping (normative)

| Level | Name |
|---|---|
| L0 | `reflex` |
| L1 | `diagnostic` |
| L2 | `deliberate` |
| L3 | `structural` |
| L4 | `method` |

These names are already in use in the SKILL.md prose — this spec lifts them to first-class display.

## Dispatch header — new format

### Auto-dispatch, L0..L2 (creativity not applicable)

```
Dispatched: L2/deliberate (signals: contract-rule-hit=+2, layer-crossings=+2)
```

### Auto-dispatch, L3/L4 (creativity echoed inline)

```
Dispatched: L3/structural · creativity=standard (signals: greenfield=+3, components>=3=+2)
```

### Auto-dispatch with clamp (creativity caused the clamp)

```
Dispatched: L3/structural · creativity=standard (signals: greenfield=+3, components>=3=+2) [clamped from L4]
```

The bracketed reason collapses from `[clamped from L4 (creativity=standard)]` to `[clamped from L4]` — the creativity is already in the main body.

### User-explicit

```
Dispatched: L3/structural · creativity=standard (user-explicit; scorer proposed L2)
```

### User-bump

```
Dispatched: L2/deliberate (user-bump from L0, fragment: "take your time")
```

### User-override-down

```
Dispatched: L0/reflex (user-override-down from L3). User accepts loss risk.
```

### What disappears

- The second line `mode: architect, creativity: standard` — **deleted unconditionally**.
- The word `auto-level` — the auto case is implicit when no dispatch-source keyword appears.
- `(signals: ...)` for non-auto dispatches where signals are not the reason — replaced by the `user-explicit` / `user-bump` / `user-override-down` phrase.

## Trace-log format — new format

### Meta line (task open)

**Before:**
```
2026-04-22T02:24:45Z  meta  task="…"  loops=cot,inner,refine,outer
```
(plus optional `level_chosen=`, `dispatch_source=` from v0.10.1)

**After:**
```
2026-04-22T02:24:45Z  meta  L4/method  creativity=inventive  dispatch=auto  task="…"  loops=design,cot,inner,refine,outer
```

Fields on the meta line (new canonical order):
1. `L<n>/<name>` — positional, unquoted (e.g. `L4/method`)
2. `creativity=<value>` — **only at L3/L4**, omitted otherwise
3. `dispatch=<auto|explicit|bump|override-down>` — short form of the dispatch source
4. `task="…"` — task title
5. `loops=…` — comma-separated loop list

### Per-iteration line

**Before:**
```
2026-04-22T02:24:45Z  architect  k=0  skill=architect-mode  action="…"  loss_norm=0.857  raw=6/7  loss_type=normalized-rubric  mode=architect  creativity=conservative
```

**After:**
```
2026-04-22T02:24:45Z  design  k=0  skill=architect-mode  action="…"  loss=0.857  raw=6/7
```

Per-line changes:
- Loop column `architect` → `design` (it's the protocol's design phase, not a fictional "architect loop")
- `mode=…` — **deleted**
- `creativity=…` — **deleted** (on meta line once, not per iter)
- `loss_type=normalized-rubric` — deleted when it equals the default (kept only when non-default, e.g. `loss_type=rate`)
- `loss_norm=` → `loss=` (shorter, unambiguous)
- `Δloss_norm=` → `Δloss=` (shorter)

### Close line

**Before:**
```
2026-04-22T02:24:56Z  outer  close  terminal=complete  layer="…"  docs=synced
```

**After:** unchanged. Loop name stays (`outer`), no redundant fields.

## Statusline format — new format

`skills/host-statusline/statusline.sh` currently shows minimal info when idle and doesn't surface the thinking-level at all. New format:

- Idle: `LDD · idle` (unchanged)
- Active, L0..L2: `LDD · L2/deliberate · inner k=1 · loss=0.167`
- Active, L3/L4: `LDD · L3/structural · creativity=standard · design k=2 · loss=0.286`

## Override syntax — what changes

### Removed

- `LDD[mode=architect]:` — **removed**. Use `LDD[level=L3]:` instead.
- `LDD[mode=reactive]:` — **removed**. Use `LDD[level=L2]:` instead.

### Kept

- `LDD[level=Lx]:` — explicit level (unchanged)
- `LDD[creativity=<value>]:` — explicit creativity, **only valid at L3/L4** (emits `ignored (level=L<n> does not accept creativity)` trace warning otherwise)
- `LDD=max:` — sugar for `LDD[level=L4]:`
- `LDD++` / `LDD+` — bump by 2 / 1
- Natural-language bumps (`"take your time"`, `"volle Kanne"`, …) — unchanged

### Deprecation handling

For v0.11.0: parse `LDD[mode=architect]:` and `LDD[mode=reactive]:` as **silent** aliases mapping to `LDD[level=L3]:` and `LDD[level=L2]:` respectively, plus a single trace-header note `deprecated: mode= is derived from level; use level= instead`. Remove the alias entirely in v0.12.0.

## Backward compatibility — reading old traces

`scripts/ldd_trace/store.py::_parse_line` must accept BOTH formats:
- `loss_norm=` and `loss=` (prefer new; accept old)
- `loss_type=normalized-rubric` absent OR present (both mean the same)
- Loop name `architect` OR `design` (both normalize to phase=`design` internally)
- Per-iter `mode=` / `creativity=` — **read and discard** (no error; they were redundant and are derivable from the meta line)

The `Phase` literal and `Iteration.mode` field in `renderer.py` stay for one release as a read-compat hook. Internal code stops **setting** them (new writes use the consolidated format), but existing logs are still renderable.

## Scope of mechanical edits (subagent work)

### Code (logic)
- `scripts/level_scorer.py` — add `LEVEL_NAMES`, rewrite `dispatch_header()`, update CLI conditional second-line print (drop it)
- `scripts/ldd_trace/store.py` — new meta+iter field layout; dual-read support; loop-name aliasing
- `scripts/ldd_trace/renderer.py` — new header string; keep `Iteration.mode` for read-compat only
- `scripts/ldd_trace/aggregator.py` — map `architect` loop reads to `design` phase
- `scripts/ldd_trace/cli.py` — update any print paths
- `scripts/ldd_trace/retrieval.py` — update queries on loop names if present
- `scripts/demo-trace-chart.py`, `scripts/demo-e2e-trace.py`, `scripts/demo-thinking-levels-e2e.py` — regenerate with new format

### Docs
- `skills/using-ldd/SKILL.md` — level table gets Name column; rewrite §Dispatch header, §Trace format, §Override syntax; add deprecation note for `mode=`
- `skills/architect-mode/SKILL.md` — reframe as "the 5-phase protocol active at L3/L4"; remove `mode=architect` self-invocation; point to `LDD[level=L3]:`
- `skills/bootstrap-userspace/SKILL.md` — update if it references the old trace format
- `skills/host-statusline/SKILL.md` + `statusline.sh` — new display format
- `docs/ldd/thinking-levels.md` — mirror SKILL.md changes
- `docs/ldd/architect.md` — reframe
- `docs/ldd/hyperparameters.md` — note `mode` and `creativity` derivation status
- `commands/ldd-architect.md` — reword as sugar for `LDD[level=L3]:`; note it does not become a separate axis
- `README.md`, `AGENTS.md`, `evaluation.md` — update any trace examples
- `CHANGELOG.md` — v0.11.0 entry with breaking-change banner

### Tests
- `scripts/test_level_scorer.py` — update expected dispatch-header strings
- `scripts/ldd_trace/test_ldd_trace.py` — update expected serialization
- `scripts/ldd_trace/test_e2e_memory.py`, `test_dialectical_prime.py`, `test_quantitative_dialectic.py`, `test_metric.py`, `test_bootstrap_userspace.py` — update fixtures
- `tests/fixtures/using-ldd-trace-visualization/**` — regenerate expected traces
- `tests/fixtures/architect-mode-auto-dispatch/**` — keep but update expected outputs, OR rename to `tests/fixtures/l3-l4-dispatch/**` (mechanical rename)
- `tests/fixtures/thinking-levels/**` — regenerate expected headers
- `tests/e2e/v031-runs/**` — regenerate expected run-summaries

### Regenerated artifacts (not hand-edited)
- `dist/web-bundle/**` — rebuilt by `scripts/build_web_bundle.py` after all sources updated

## Validation

After all edits:

1. `python -m pytest scripts/ tests/ -x` — all tests green
2. `python scripts/level_scorer.py "design a new payment service with novel protocol"` — emits single-line L4 header
3. `python scripts/level_scorer.py "fix typo in README.md line 12"` — emits single-line L0 header (no creativity)
4. Manual read of `.ldd/trace.log` on a regenerated demo — confirm format matches §Trace-log format above
5. `bash .ldd/statusline.sh` from a project with an active task — shows `L<n>/<name>` prefix
6. `python scripts/build_web_bundle.py && pytest scripts/test_build_web_bundle.py` — web bundle still valid

## Non-goals

- **No change to the 9-signal scorer logic.** Weights, thresholds, creativity inference — all unchanged.
- **No change to loop budgets, skill floors, or any other LDD semantics.** This is a display+storage consolidation only.
- **No change to the architect-mode 5-phase protocol.** The protocol is unchanged; only its *label* ("architect-mode" remains the skill's name) and its *trigger mechanism* (derived from L3/L4, not a separate `mode=` axis) are reframed.
- **No change to `/ldd-architect` command semantics.** It becomes documented sugar for `LDD[level=L3]:`; behaviorally identical.

## Rollout

1. Land all code + doc + test edits in one commit: `feat(v0.11.0)!: consolidate level+name; remove mode axis`.
2. Bump plugin manifest version to v0.11.0.
3. Rebuild web bundle.
4. Update `CHANGELOG.md` with a BREAKING section listing: removed fields, removed overrides, deprecation window for `mode=`.
5. Do not regenerate the LDD project's own `.ldd/trace.log` — let the next real task write the first v0.11.0 entries.
