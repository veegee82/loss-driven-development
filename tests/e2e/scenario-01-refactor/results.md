# E2E scenario 01 — results

## Tier-3.9 discovery run — 2026-04-20T16:45Z (latest)

**Artifacts:** [`runs/20260420T164505Z/`](./runs/20260420T164505Z/)

### Why "tier-3.9" and not "tier-4"

Same sandbox (`/tmp/ldd-tier4-20260420T164505Z`), fresh agent, but this time the skills were installed at `~/.claude/skills/` rather than injected into the prompt. The agent was given **only** the task + a list of skill names + the sandbox path — not the skill content itself.

**Key finding:** the subagent's `Skill` tool did NOT auto-discover `~/.claude/skills/` — it returned `Unknown skill` for `using-ldd` and every LDD skill. The agent fell back to reading the skills from disk via the `Read` tool and applying them. That fallback worked cleanly: 7/7 tests green, one-line fix at `Cart.total()`, regression tests added at the root-cause (Domain) layer, loop closed at k=1 of 5.

**This is closer to tier-4 than tier-3.5** because:
- Skills were NOT in the prompt — discovered at runtime from `~/.claude/skills/`
- Agent navigated via `using-ldd`'s trigger-phrase table, not a hand-crafted skill cascade

**Still not pure tier-4** because:
- Auto-trigger via `description` matching (Claude Code's normal skill-activation path) did not fire
- `Skill` tool integration with `~/.claude/skills/` was not available in the subagent's harness

**For a real adopter using `/plugin install`**, the picture is probably different: the plugin registration registers the skills with the `Skill` tool, which should allow description-based auto-trigger. But this cannot be verified from the current session — the subagent harness does not inherit `/plugin install` state.

### Rubric (scored against on-disk artifacts)

| # | Item | Observed | Note |
|---|---|---|---|
| 1 | Failing test passes after the fix | ✅ | 7/7 tests green (original + 5 new regression tests at root-cause layer) |
| 2 | No new lint / type errors introduced | ✅ | One-line diff, type-stable |
| 3 | Fix at the right layer | ✅ | Fix in `Cart.total()` — matches layer-4 Domain diagnosis |
| 4 | No symptom-patch patterns in the diff | ✅ | No `try/except`, `hasattr`, retry, widened assertion |
| 5 | Docs updated in the same commit | N/A | README already matched intended behavior; no doc edits needed |
| 6 | No TODO / "follow-up" language in commit message | ✅ | `fix(cart): apply recorded discount inside Cart.total()` |
| 7 | Terminal status: `complete` | ✅ | k=1 of K_MAX=5 |

**Result: 7/7 satisfied.**

### Observed LDD-skill application

- `*Invoking using-ldd*` — entry-point per `LDD:` prefix
- `*Invoking reproducibility-first*` — ran pytest twice to confirm deterministic, plus Branch-B unambiguous-signal shortcut
- `*Invoking root-cause-by-layer*` — explicit 5-layer walk
- `*Invoking dialectical-reasoning*` — thesis: fix in `Cart.total()`; antithesis: fix in `checkout()`; synthesis: Cart is the state-owner, fix belongs there
- `*Invoking docs-as-definition-of-done*` — swept README + docstrings, no edits required

### What a real tier-4 adopter should do

Same as before (install via plugin, run scenario, capture artifacts) — but additionally verify:

1. Does the `Skill` tool auto-discover the LDD bundle after `/plugin install`? If not, the bundle's `description` fields might not be the trigger Claude Code uses — document the actual dispatch mechanism.
2. Do auto-trigger scenarios work without the `LDD:` prefix? Test the trigger-phrase table from `skills/using-ldd/SKILL.md`.

---

## Tier-3.5 simulated run — 2026-04-20T16:03Z

**Artifacts:** [`runs/20260420T160347Z/`](./runs/20260420T160347Z/)

### Why "tier-3.5" and not "tier-4"

Tier-4 in [`../../evaluation.md`](../../evaluation.md) requires an actual plugin-install in a live Claude Code / Codex / Gemini session. This run instead dispatched a subagent with tool access (bash, file edits, git) **given the skill content via the prompt** rather than through a real plugin install. Result: the agent exercised the skills on real files producing real artifacts, but it's not a verified plugin-install path. A genuine tier-4 run still requires you to install the plugin and repeat the run against the same scenario.

### Configuration

- Sandbox: `/tmp/ldd-e2e-sim-20260420T160347Z/` (isolated, no ancestor `CLAUDE.md`)
- Starter code: copied from `starter/` verbatim, committed as `78f0425 initial: failing discount test`
- Skills loaded: all 10 via prompt injection (skill content in-context, not via plugin system)
- Tools available: bash, file read/edit, git
- Budget: K_MAX = 5 iterations

### Scored against the rubric

Rubric in [`../README.md`](../README.md) ("What a good LDD-run looks like" section):

| # | Item | Observed | Note |
|---|---|---|---|
| 1 | Failing test passes after the fix | ✅ | `pytest -q` → 2 passed, 0 failed |
| 2 | No new lint / type errors introduced | ✅ | One-line diff, type-stable (`float * float → float`) |
| 3 | Fix at the right layer | ✅ | Fix lives in `Cart.total()` — matches layer-4 diagnosis (computation layer, state-owner) |
| 4 | No symptom-patch patterns in the diff | ✅ | No `try/except`, no `hasattr`, no retry loop, no widened assertions |
| 5 | Docs updated in the same commit | N/A | Agent correctly identified that docs already matched the *intended* behavior — the code drifted from docs, not vice versa. Zero doc edits needed |
| 6 | No TODO / "follow-up" language in commit message | ✅ | Commit message: `fix(cart): apply stored discount percentage in Cart.total()` with full root-cause rationale |
| 7 | Terminal status: `complete` | ✅ | Closed at k=1 of K_MAX=5 |

**Result: 7/7 satisfied.** Loop closed in 1 iteration.

### Observed LDD-skill application

The agent's run summary (`runs/20260420T160347Z/run-summary.md`) shows explicit application of:

- **root-cause-by-layer** — full 5-layer walk naming Symptom → Mechanism → Contract (two violated docstring / README contracts) → Structural origin (computation layer) → Conceptual origin (broken SSOT for final price)
- **dialectical-reasoning** — thesis / antithesis-A (fix in checkout()) / antithesis-B (add input validation) / synthesis (minimal formula at computation layer)
- **e2e-driven-iteration** — measured loss before edit, measured after, declared terminal state
- **docs-as-definition-of-done** — explicit check that README and docstring matched intended behavior; correctly avoided unnecessary doc edits
- **loss-backprop-lens** — explicit reasoning about why reproducibility-first doesn't demand a second run here (deterministic arithmetic, not LLM/network)

### Caveats

- Single run. Multiple runs would produce a distribution.
- Subagent may have had ambient methodology context (AWP `CLAUDE.md`) in its initial state despite the explicit "context reset" — same contamination caveat as earlier baselines.
- Scored by the skill author (circular); artifacts attached for re-scoring.
- Tier-4 (real plugin install) still pending.

### What a new adopter should do

1. Install the plugin per [README.md](../../../README.md) instructions for your agent.
2. Copy [`starter/`](./starter/) into a scratch directory.
3. Paste [`task.md`](./task.md) as your first message.
4. Let the agent run to terminal status without guiding.
5. Compare the resulting diff, commit, and transcript against the 7 rubric items above.
6. Record your run in `runs/<your-timestamp>/` and open a PR.

That converts this simulated run into a measured tier-4 data point.
