# Contributing

Thanks for considering a contribution. This plugin is early (v0.2 seed). The most valuable contributions right now are **not code** — they're baselines.

## The single highest-leverage thing you can do

**Use the plugin on a real task and tell us whether the skills changed your agent's behavior.**

If the skills helped, great — an issue saying "here's what I was doing, here's what the agent did, skill X caught it" is gold for future evolution.

If the skills didn't help — even better. An issue saying "here's the pressure scenario, here's the unhelpful response, here's the skill I expected to fire" gives us the baseline data we need to close [`GAPS.md`](./GAPS.md) items and run `method-evolution` properly (see that skill for why measured skill changes beat imagined ones).

Use the issue template at [`.github/ISSUE_TEMPLATE/skill-failure.md`](./.github/ISSUE_TEMPLATE/skill-failure.md) for "the skill didn't change behavior" reports.

## Second-most-valuable: captured baselines

Each fixture under [`tests/fixtures/<skill>/`](./tests/fixtures/) has a `scenario.md` + `rubric.md` + `baseline-notes.md`. The `baseline-notes.md` for most skills currently says "NOT YET CAPTURED" — because the original build sessions were run from an environment where the subagent refused to ignore an ambient methodology file and produced skill-compliant output even without the skill loaded.

To contribute a clean baseline:

1. Open a subagent session in an empty `/tmp/` directory (no ancestor `CLAUDE.md` / `AGENTS.md`).
2. Paste the fixture's `scenario.md` verbatim. Record the response.
3. In a second fresh session, prepend the skill's `SKILL.md` body and re-run. Record the response.
4. Score both against `rubric.md`, compute `Δloss`.
5. Open a PR adding the run artifacts to `tests/fixtures/<skill>/runs/<timestamp>/` and updating `baseline-notes.md`.

[`scripts/evolve-skill.sh`](./scripts/evolve-skill.sh) scaffolds steps 1–3 if you're on Claude Code.

## Code contributions

For changes to skill prose, the bar is **`method-evolution`-compliant**: you need at least 3 distinct tasks where the current skill failed in the same way, a specific proposed change (not a rewrite), and a measurement plan. See [`skills/method-evolution/SKILL.md`](./skills/method-evolution/SKILL.md) for the protocol.

For changes to scripts, diagrams, evaluation harness: standard PR flow. Open an issue first for anything non-trivial (>50 lines of change).

## Language and tone

- Skill content is English. No other languages in committed files.
- Doc style is sharp and specific; avoid "feels better" framing without a measurement.
- If a change to a skill is a judgment call (rubric wording, red flag phrasing), **cite the baseline or pressure scenario it's derived from** in the PR description.

## License

By contributing, you agree your contributions are licensed under [MIT](./LICENSE).
