# scripts/ — optional tooling

The skills in this bundle are **portable markdown** — they work in any agent that reads instruction files. The scripts here are **optional helpers** that automate parts of the LDD workflow.

**You do not need these scripts to use LDD.** The skills work without them. Scripts exist to reduce friction on the operations that benefit most from automation.

| Script | Automates | Skill / workflow it supports |
|---|---|---|
| `drift-scan.py` | Periodic repo drift indicators (seven-indicator scan) | `drift-detection` |
| `capture-clean-baseline.py` | Capture RED baselines via direct LLM API (no agent harness) | `method-evolution`, distribution sampling, any fixture measurement |
| `capture-red-green.py` | Paired RED/GREEN captures for multi-scenario fixtures (skill content prepended as system message on GREEN) | `method-evolution`, multi-scenario fixture measurement (e.g. `architect-mode-auto-dispatch`) |
| `evolve-skill.sh` | RED/GREEN rerun of a skill against its fixture (terminal-driven) | `method-evolution` |
| `render-diagrams.sh` | Regenerate SVG from `.dot` sources | (maintenance) |

## Requirements

- `drift-scan.py` — Python 3.10+, `git`, `grep`. No third-party deps.
- `capture-clean-baseline.py` — Python 3.10+ plus one API key: `OPENROUTER_API_KEY`, `OPENAI_API_KEY`, or `ANTHROPIC_API_KEY`. Uses stdlib `urllib` — no third-party deps.
- `capture-red-green.py` — same API-key + stdlib requirements as `capture-clean-baseline.py`. Takes `--fixture` + `--skill-files` + `--scenarios` / `--scenarios-file` + `--run-dir`; writes paired `red.md` / `green.md` per scenario under `<fixture>/<run-dir>/<scenario>/`.
- `evolve-skill.sh` — `bash`, a subagent / LLM session you can paste into. No API key needed (terminal-driven workflow).
- `render-diagrams.sh` — `graphviz` (`dot`).

## Capturing distributions — quick recipe

To close the "single-run point estimate" gap for a given fixture:

```bash
export OPENROUTER_API_KEY=...   # or OPENAI_API_KEY / ANTHROPIC_API_KEY

TS=$(date -u +%Y%m%dT%H%M%SZ)
SKILL=root-cause-by-layer
mkdir -p "tests/fixtures/$SKILL/runs/${TS}-clean-N10"

for i in $(seq 1 10); do
    python scripts/capture-clean-baseline.py \
        "tests/fixtures/$SKILL/scenario.md" \
        --temperature 0.8 \
        --out "tests/fixtures/$SKILL/runs/${TS}-clean-N10/red-${i}.md"
done
```

Score each `red-*.md` against `rubric.md` and publish the distribution. Typical cost: under $1 per skill at current OpenRouter pricing.

## Philosophy

Scripts are second-class citizens. The skills are versioned and measured; the scripts are best-effort helpers. If a script becomes indispensable, that's a signal to rewrite the relevant part of the skill to make the script unnecessary — the skill should not depend on tooling the host agent may not have.

`capture-clean-baseline.py` is the one exception where the script closes a structural measurement problem (subagent-harness contamination). The skills themselves still work without it; the script is for maintainers and adopters who want clean baselines.

## Non-goals

- Not a CI pipeline. You can wire these into CI, but they're not designed for it.
- Not a test runner. They don't execute your project's tests.
- `capture-clean-baseline.py` calls LLM APIs; the other three do not.
