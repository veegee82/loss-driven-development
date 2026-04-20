# Getting started with LDD

One page. Read this if (a) you're a user about to install LDD, or (b) you're an agent encountering LDD for the first time.

## For the user

After [install](../../README.md#installation), try the bundle on a real task:

### Option 1 — explicit activation (recommended first time)

Prefix your message with `LDD:`:

```text
LDD: the checkout test is failing and I need to ship in an hour
```

The agent will announce which skill it is invoking:

> *Invoking `reproducibility-first`*: one failure is one sample; checking reproducibility before treating this as a gradient.

If you do not see an `*Invoking <skill>*:` line, LDD is installed but dormant — re-check install per [`../../README.md#verifying-ldd-is-active`](../../README.md#verifying-ldd-is-active).

### Option 2 — trust auto-trigger

Just describe your task naturally:

```text
I've tried fixing this flaky test three times and it keeps breaking different tests
```

The agent should auto-invoke `loss-backprop-lens` (local-minimum trap trigger). If it doesn't, fall back to Option 1.

### Option 3 — name the skill

```text
Use root-cause-by-layer on this TypeError
```

Works in Claude Code (`/loss-driven-development:root-cause-by-layer`), Codex (names in AGENTS.md), Gemini CLI (GEMINI.md imports).

## For the agent

You are in a project that has LDD available. On every non-trivial task:

1. **Check [`task-types.md`](./task-types.md)** — pick the task type matching the user's message.
2. **Load only the MDs that task type requires.** Do not pre-load the whole methodology.
3. **Announce invocations** — `*Invoking <skill-name>*: <one-line reason>.` before applying each skill.
4. **Respect minimum-compliance behaviors** (from `../../skills/using-ldd/SKILL.md`):
   - No symptom patches without 5-layer diagnosis
   - No code edit on single-sample failure without reproduction
   - No "done" without docs synced
   - No non-trivial recommendation without dialectical pass
   - No silent iteration 6

## The shortest possible summary

**LDD = SGD on code. If your edit is not a real gradient step (reproducible signal + honest diagnosis + right step size + regularizers intact), it's noise injected into the codebase.**

That sentence is the whole bundle. Everything else is scaffolding to keep the sentence honest under pressure.

## Five-minute installed-and-working checklist

You'll know LDD is working when:

- [ ] `*Invoking <skill>*:` lines appear in agent responses to non-trivial tasks
- [ ] Commit messages name layers, Δloss, or structural origins when relevant
- [ ] Agent pushes back on "just rerun" / "try/except wrapper" / "I'll update docs later"
- [ ] Design recommendations include explicit thesis / antithesis / synthesis

None of these happen? Check:

- Is the plugin actually installed? (`/plugin list` in Claude Code)
- Is the skill directory discoverable? (see install per your agent)
- Did you try the `LDD:` prefix?

Still not working? Open an issue with [`.github/ISSUE_TEMPLATE/skill-failure.md`](../../.github/ISSUE_TEMPLATE/skill-failure.md).
