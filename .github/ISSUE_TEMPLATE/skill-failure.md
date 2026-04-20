---
name: Skill didn't change my agent's behavior
about: A pressure scenario where LDD should have fired but didn't help. Bronze-medal baselines are the best contribution you can make at v0.2.
title: "[skill-failure] <skill-name>: short description"
labels: ["baseline", "skill-failure"]
---

## Which skill should have fired?

e.g. `root-cause-by-layer`, `iterative-refinement`, etc.

## Was the skill actually loaded?

- [ ] Yes, via `/plugin install` or equivalent
- [ ] Yes, via personal skills dir (`~/.claude/skills/` etc.)
- [ ] Yes, via `AGENTS.md` in project root
- [ ] I'm not sure

Which agent? (Claude Code · Codex · Gemini CLI · Aider · Cursor · Copilot CLI · Continue.dev · other)

## The pressure scenario

What was the task you gave the agent? Copy the prompt verbatim if possible.

```
<your prompt>
```

## What you expected

Which rubric item from the skill's `tests/fixtures/<skill>/rubric.md` (or your own expectation) should have been satisfied?

## What actually happened

The agent's response, verbatim — trim to the relevant part but do not paraphrase.

```
<agent's response>
```

## Why this is a baseline

In one or two sentences: what's the failure mode? Missing layer-4/5 analysis? Shipped a symptom patch? Skipped the antithesis? Treated a single sample as a gradient?

## Reproducibility

- [ ] I observed this once
- [ ] I reproduced it 2+ times on the same scenario
- [ ] I observed the same failure pattern on a different scenario too

Single-sample reports are still useful; reproduced ones are more actionable.

## Attached

- [ ] Transcript / log (paste or link)
- [ ] Diff / commit the agent produced (if any)

---

*Thank you. This is the kind of data that moves the bundle from v0.2 seed to v1.0 measured.*
