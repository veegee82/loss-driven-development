# LDD Thinking Levels — the step-size controller for the gradient descent

> Authoritative reference for the 5-level auto-dispatch system. Reference spec: [`../superpowers/specs/2026-04-22-ldd-thinking-levels-design.md`](../superpowers/specs/2026-04-22-ldd-thinking-levels-design.md). Implementation: [`../../scripts/level_scorer.py`](../../scripts/level_scorer.py). Skill integration: [`../../skills/using-ldd/SKILL.md`](../../skills/using-ldd/SKILL.md) § Auto-dispatch: thinking-levels.

## Where this sits in the framework

**LDD is [gradient descent across four parameter spaces](../theory.md).** Thinking-levels is the **step-size controller** for that descent — it picks how much rigor to bring to the task *before* any of the four loops (inner / refinement / outer / CoT) starts descending. It is not a fifth loop; it is a learning-rate scheduler that sets `k_max` (inner-loop budget), `reproduce_runs`, `max_refinement_iterations`, `mode` (reactive vs. architect), and the skill floor (minimum set of skills that must fire for this task).

A too-low level ships a symptom-patch on an axis that needed more iterations; a too-high level wastes tokens on a problem the reflex loop would have solved. The scorer encodes the asymmetric-loss rule "lieber ein klein wenig schlau als zu dumm" — bias upward on ties, because a missed gradient is more expensive than a wasted one.

## One-line summary

LDD picks **how hard to think** per task on a 5-step ladder (L0 reflex → L4 method), zero-config, upward-biased on ties, trivially overridable. The user types a task; the agent decides the level and announces it.

## Why levels at all

Before thinking-levels, LDD had one deliberation dial: `mode = reactive | architect`. Between "fix typo" and "design a new module" lie 95 % of real tasks — all collapsed into `reactive`. Two failure modes followed:

- **Over-deliberation on simple tasks.** A one-line fix ran the same 5-iteration loop as a multi-file refactor.
- **Under-deliberation on cross-layer bugs.** Tasks whose prompts lacked any architect trigger phrase silently stayed reactive and shipped symptom-patches.

Thinking-levels closes this gap without adding a new knob — `level` is **derived** from task signals, not configured. See [`hyperparameters.md`](./hyperparameters.md) for why adding a knob would have been moving-target-loss.

## The 5 levels

| Level | Name | `k_max` / `reproduce_runs` / `mode` | `max_refinement_iterations` | Skill floor |
|---|---|---|---|---|
| **L0** | reflex | 2 / 1 / reactive | 1 | `e2e-driven-iteration` |
| **L1** | diagnostic | 3 / 2 / reactive | 2 | + `reproducibility-first`, `root-cause-by-layer` |
| **L2** | deliberate *(default baseline)* | 5 / 2 / reactive | 3 | + `dialectical-reasoning`, `loss-backprop-lens`, `docs-as-definition-of-done` |
| **L3** | structural | 5 / 2 / **architect**/standard | 3 | + `architect-mode` (standard), `drift-detection`, `iterative-refinement` |
| **L4** | method | 8 / 3 / **architect**/inventive (ack-gated) | 5 | + `method-evolution`, `dialectical-cot`, `define-metric` |

**Skill floor is a floor, not a ceiling.** A task at L2 that benefits from `drift-detection` may still invoke it; a task at L3 may **not skip** `architect-mode`.

**Baseline is L2, not L0.** When the task text produces zero signals (empty prompt, chit-chat, ambiguous with no anchors), the agent lands at L2. This is the structural encoding of the user's asymmetric-loss rule — low-side failures are ×2 worse than high-side failures, so the default leans upward.

## The 9-signal scorer

Deterministic pure function, implemented in [`../../scripts/level_scorer.py`](../../scripts/level_scorer.py). No LLM call.

| Signal | Weight | Meaning |
|---|---|---|
| Greenfield | **+3** | `"from scratch"`, `"new service"`, `"new module"`, `"no existing code"`, `"design a new"` |
| ≥ 3 new components | **+2** | ≥ 2 matches of the components pattern, or ≥ 3 distinct `"new <noun>"` phrases |
| Cross-layer | **+2** | `"across"`, `"between … and"`, `"integrate"`, `"wire"`, `"bridge"`, `"hook into"` |
| Ambiguous requirements | **+2** | `"somehow"`, `"after my last change"`, `"I'm not sure"`, `"when … doesn't"` |
| Explicit bug-fix | **−5** | `"fix"`, `"failing"`, `"broken"`, `"off-by-one"`, `"typo"` |
| Single-file known-solution | **−3** | Exactly one file path AND (line ref OR fix verb OR `rename`/`move`/`delete`/`remove`) |
| **Layer-crossings** *(new)* | **+2** | ≥ 2 named layer / subsystem terms from the LDD/AWP vocabulary |
| **Contract / R-rule hit** *(new)* | **+2** | `R\d+`, `"schema"`, `"contract"`, `"API surface"`, `"invariant"`, named gate / field / contract |
| **Unknown-file-territory** *(new)* | **+1** | paths not seen in `.ldd/trace.log` history of the last 20 runs; 0 when log absent |

The 6 non-bold signals are inherited from the pre-thinking-levels architect-mode scorer; the 3 bold signals are new.

### Score-to-level buckets

| Summed score | Level |
|---|---|
| `score ≤ −7` | **L0** |
| `−6 ≤ score ≤ −2` | **L1** |
| `−1 ≤ score ≤ 3` | **L2** *(zero-signal baseline lands here)* |
| `4 ≤ score ≤ 7` | **L3** |
| `score ≥ 8` | **L4** |

The L0 bucket is deliberately narrow — only a task where BOTH `explicit-bugfix:-5` AND `single-file:-3` fire with nothing else (sum = −8) lands there. Any positive signal on top lifts the task into L1 or higher.

### Creativity-clamp rule (L4 ↔ L3)

When the summed score buckets L4 BUT the creativity inferrer returns `standard` (no `"novel"`, `"research"`, `"prototype"`, `"no known pattern"`), the level clamps to L3. Reason: L4's preset mandates `creativity=inventive (ack-gated)`; running L4 with `standard` would mix two loss functions into one gradient (violates `skills/architect-mode/SKILL.md` §"Cannot switch mid-task"). The dispatch header MUST show `[clamped from L4 (creativity=standard)]` when this fires. The clamp is one-directional: it cannot promote L3 → L4 when creativity would be inventive.

### Creativity inference

| Creativity | Triggering cues | Notes |
|---|---|---|
| `conservative` | `"regulated"`, `"compliance"`, `"HIPAA"`, `"PCI"`, `"SOC2"`, `"no new tech"`, `"tight deadline"`, `"team of N"` | Any one hit → `conservative` |
| `standard` (default) | none of the other levels' cues dominate | L3/L4 default when no conservative/inventive cue is present |
| `inventive` | `"novel"`, `"research"`, `"prototype"`, `"no known pattern"`, `"invent"`, `"experimental"`, `"paradigm"` | Scorer **proposes** inventive; consent required (see next section) |

Conservative beats inventive on a tie.

## Inventive consent — three paths

`creativity=inventive` uses a **different loss function** than `standard` / `conservative`. The agent is **never** allowed to activate inventive on its own. Three user-originated consent paths, by precedence:

1. **Explicit inline flag.** `LDD[creativity=inventive]:` or the `/ldd-architect inventive` command.
2. **Liberalized ack token.** When the scorer proposes inventive, the agent asks for consent. Canonical: `acknowledged`. Also accepted (bilingual): `"ack"`, `"yes"`, `"ja"`, `"go"`, `"go ahead"`, `"proceed"`, `"los"`, `"okay mach"`, `"passt"`, `"mach"`. Negatives (`"no"`, `"nein"`, `"stop"`, silence) → silent downgrade to `standard`. Ambiguous replies require the literal `acknowledged`.
3. **Implicit ack from prompt.** When the original task message already contains **≥ 2 inventive cues** AND is **≥ 100 characters long**, the prompt IS the consent. The dispatch header surfaces this: `creativity: inventive (implicit ack from ≥2 inventive cues in prompt)`.

None of these three paths allows the AGENT to select inventive unilaterally.

## Override syntax

Zero-config users do not need any of this. The scorer runs on every task and picks a level.

Users who want to override, by precedence (highest wins):

| Syntax | Effect |
|---|---|
| `LDD[level=L3]:` | Explicit level, overrides the scorer entirely. If below scorer's proposal, emits `user-override-down` warning. |
| `LDD=max:` / `"volle Kanne"` / `"full LDD"` | Clamp to L4 |
| `LDD++:` / `LDD+:` | Relative bump by 2 / 1 levels from auto |
| `"take your time"`, `"think hard"`, `"denk gründlich"`, `"sorgfältig"` etc. | Natural-language +1 (bilingual; all `+1` phrases dedup to +1 total) |
| `"really think"`, `"maximum rigor"`, `"sehr sorgfältig"` etc. | Natural-language +2 |
| (nothing) | Auto-scorer output |

Full list and semantic-dedup rule: [`../../skills/using-ldd/SKILL.md`](../../skills/using-ldd/SKILL.md) § Override syntax.

## Dispatch-header echo (mandatory)

Every non-trivial task emits exactly one of these lines in the trace header:

```
Dispatched: auto-level L<n> (signals: <signal1>=<±N>, <signal2>=<±N>)
Dispatched: auto-level L<n> (signals: ...) [clamped from L4 (creativity=standard)]
Dispatched: user-explicit L<n> (scorer proposed L<m>)
Dispatched: user-bump L<n> (scorer proposed L<m>, bump: <fragment>)
Dispatched: user-override-down L<n> (scorer proposed L<m>). User accepts loss risk.
```

When `level ∈ {L3, L4}`, a second line names the creativity:

```
mode: architect, creativity: <standard|conservative|inventive>
```

Silent dispatch is a trace-integrity violation. Without the echo, method-evolution cannot tell apart "scorer was wrong" from "user forced a bad level".

## Persisted in `.ldd/trace.log`

The scorer's decision is persisted on the `meta` line at task start:

```
2026-04-22T12:00:00Z  meta  task="fix the typo"  loops=inner  level_chosen=L0  dispatch_source=auto-level
```

The final loss is persisted on the `close` line:

```
2026-04-22T12:05:00Z  inner  close  terminal=complete  layer="1: …"  docs=synced  loss_final=0.000
```

These two fields are the input to the method-evolution trigger (see below).

## Method-evolution feedback

When the agent systematically under-scores tasks and ships symptom-patches where higher levels would have caught the structural origin, method-evolution auto-triggers. See [`../../skills/method-evolution/SKILL.md`](../../skills/method-evolution/SKILL.md) §"Automatic trigger: thinking-levels scorer weight adjustment" for the exact condition and rollback rules.

Short version: 3+ low-side regressions in the last 20 tasks → propose +1 weight adjustment to the signal most correlated with the misses → measure against the fixture suite → rollback on regression. The agent itself does not second-guess its level pick during a run; the outer loop corrects across runs.

## Fixture suite

Nine scenarios under [`../../tests/fixtures/thinking-levels/`](../../tests/fixtures/thinking-levels/):

- 5 level scenarios (`L0-reflex` … `L4-method`) — one representative task per level.
- 4 override scenarios (`override-up-from-L0`, `override-max-on-simple`, `override-natural-language`, `override-down-warning`) — one per override path.

Every scenario has a `scenario.md` with a verbatim prompt and the expected level; the top-level `rubric.md` defines 4 binary dispatch-correctness items plus suite-level asymmetric-loss weighting (low-side failures count ×2).

The scorer's unit tests in [`../../scripts/test_level_scorer.py`](../../scripts/test_level_scorer.py) include an end-to-end block that runs all 9 fixtures through `score_task` and verifies the expected level, source, and (where relevant) creativity.

## CLI

```bash
python scripts/level_scorer.py "<task prompt>"
python scripts/level_scorer.py "<task prompt>" --json   # machine-readable
echo "<task>" | python scripts/level_scorer.py -        # read from stdin
```

Output (default):

```
Dispatched: auto-level L0 (signals: explicit-bugfix=-5, single-file=-3)
```

Output (`--json`):

```json
{
  "raw_score": -8,
  "auto_level": "L0",
  "final_level": "L0",
  "creativity": "standard",
  "dispatch_source": "auto-level",
  "signals": [...],
  "dispatch_header": "..."
}
```

## Relation to architect-mode

Before thinking-levels, `architect-mode` had its own auto-dispatch scorer at `score ≥ 4 → architect`. That separate scorer is now gone — architect-mode is reached through the **L3 / L4 presets**. All six original architect-dispatch signals are retained; three new signals are added; the buckets are tuned so `score ≥ 4 → L3` (which still sets `mode=architect, creativity=standard`) and `score ≥ 8 → L4` (with the creativity-clamp). Backward-compat is preserved for every task the old scorer previously sent to architect-mode.

See the historical fixture at `tests/fixtures/architect-mode-auto-dispatch/` for the pre-thinking-levels regression baseline. It is still exercised for regression-only; the primary dispatch-correctness surface is the 9-scenario thinking-levels fixture.

## Asymmetric loss — the driving principle

Throughout this design, one rule is encoded in every tie-break:

> **lieber ein klein wenig schlau als zu dumm**

A level one rank too high wastes tokens (cost: some). A level one rank too low ships a symptom-patch that costs a full regression cycle later (cost: much more). The design is biased toward the first, cheaper error:

- Default baseline is L2, not L0.
- Tie-break on raw-score boundaries picks the higher level.
- Natural-language bumps are recognized liberally; bumps never clamp downward silently.
- Method-evolution weights proposals favor upward-biasing adjustments.
- Explicit downward overrides are honored but loud (`user-override-down` warning).
- Suite-level asymmetric-loss weighting counts low-side failures ×2 during tuning.

The agent does not second-guess the user's override — but it also does not silently under-think when left to itself.
