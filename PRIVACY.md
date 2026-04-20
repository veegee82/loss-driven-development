# Privacy Policy

Effective date: 2026-04-20

## Short version

**Loss-Driven Development (LDD) does not collect, transmit, or store any user data.** The plugin is entirely markdown and small scripts running locally on your machine. There is no telemetry, no phone-home, no analytics, no account, no cloud component operated by LDD.

## What the plugin is

LDD is a bundle of:

- **Skills** (`skills/*/SKILL.md`) — behavior-shaping markdown text the agent reads as context. No code execution, no I/O.
- **Methodology docs** (`docs/ldd/*.md`) — reference text. Read-only.
- **Plugin manifests** (`.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json`, `gemini-extension.json`) — static JSON describing the plugin.
- **Four optional scripts** under `scripts/`. Each is explicitly scoped below.

None of these artifacts call home, send telemetry, or log user activity anywhere.

## What the optional scripts do

| Script | Network activity | Data collected / sent |
|---|---|---|
| `scripts/drift-scan.py` | **None** — local-only `git` / `grep` over your repo | None |
| `scripts/evolve-skill.sh` | **None** — prints prompts to the terminal for you to paste into a session manually | None |
| `scripts/render-diagrams.sh` | **None** — runs Graphviz locally | None |
| `scripts/capture-clean-baseline.py` | **Outbound only**, to an LLM provider of your choice (OpenRouter, OpenAI, or Anthropic), using an API key **you** supply via environment variable | The prompt in the fixture file you pass; the provider's response |

`capture-clean-baseline.py` sends your chosen scenario prompt to the provider whose API key you supplied. LDD itself does not see, cache, or store any of that traffic. The provider's own privacy policy governs what happens to your prompt and the response:

- OpenRouter: <https://openrouter.ai/privacy>
- OpenAI: <https://openai.com/policies/privacy-policy/>
- Anthropic: <https://www.anthropic.com/legal/privacy>

If you do not run `scripts/capture-clean-baseline.py`, the plugin makes no network calls whatsoever.

## What the skills make the agent do

The skills instruct your coding agent (Claude Code, Codex, Gemini CLI, Aider, etc.) on **how to think** — they do not instruct it to exfiltrate data, phone home, or share your code with any third party. A skill is a block of markdown text the agent reads as context.

If you believe a skill's prose could induce an agent into a privacy-affecting behavior, please report it per [`SECURITY.md`](./SECURITY.md).

## Data we (the maintainer) see

GitHub issues, PRs, and discussions posted on <https://github.com/veegee82/loss-driven-development> are public and visible to everyone including me. GitHub's own privacy policy applies to that data: <https://docs.github.com/en/site-policy/privacy-policies/github-general-privacy-statement>.

If you open an issue using [`.github/ISSUE_TEMPLATE/skill-failure.md`](./.github/ISSUE_TEMPLATE/skill-failure.md), you may voluntarily paste agent responses / transcripts. Do not paste anything you consider private or proprietary. I will use submitted material only to improve LDD (e.g. as new baseline fixtures or method-evolution inputs) and will note in any derived work that the source was a community-submitted issue.

## Third-party dependencies

- The plugin itself has zero runtime dependencies beyond what your host agent provides.
- `scripts/drift-scan.py` uses only the Python standard library (`argparse`, `json`, `os`, `re`, `subprocess`, `sys`, `pathlib`, `urllib.request`).
- `scripts/capture-clean-baseline.py` uses only the Python standard library.
- No package downloads at install time. No `pip install` required to use the plugin.

## Changes to this policy

Any material change (e.g. if LDD ever adds telemetry, analytics, or any data-collecting feature — currently not planned) will be reflected in this file AND listed in [`CHANGELOG.md`](./CHANGELOG.md) under a clearly-labeled privacy-impact entry.

## Contact

Questions about this policy: **silvio.jurk@googlemail.com**.

For security-impacting privacy concerns: see [`SECURITY.md`](./SECURITY.md) for the disclosure channel.
