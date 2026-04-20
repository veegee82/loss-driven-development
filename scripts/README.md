# scripts/ — optional Claude-Code tooling

The skills in this bundle are **portable markdown** — they work in any agent that reads instruction files. The scripts in this directory are **optional helpers** that automate parts of the LDD workflow, targeted at Claude Code users.

**You do not need these scripts to use LDD.** The skills work without them. The scripts exist to reduce friction on the two loops that benefit most from automation:

| Script | Automates | Skill it supports |
|---|---|---|
| `drift-scan.py` | Periodic repo drift indicators | `drift-detection` |
| `evolve-skill.sh` | RED/GREEN rerun of a skill against its fixture | `method-evolution` |
| `render-diagrams.sh` | Regenerate SVG from `.dot` sources | (maintenance) |

## Requirements

- `drift-scan.py` — Python 3.10+, `git`, `grep`. No third-party deps.
- `evolve-skill.sh` — `bash`, access to a Claude Code session (the script prints prompts for you to paste).
- `render-diagrams.sh` — `graphviz` (`dot`).

## Philosophy

Scripts are second-class citizens here. The skills are versioned and tested; the scripts are best-effort helpers. If a script becomes indispensable, that's a signal to rewrite the relevant part of the skill to make the script unnecessary — the skill should not depend on tooling the host agent may not have.

## Non-goals

- Not a CI pipeline. You can wire these into CI, but they're not designed for it.
- Not a test runner. They don't execute your project's tests.
- Not Claude-API-specific. They use local `git` / `grep` / file IO.
