# Security Policy

## Reporting a vulnerability

If you believe you have found a security issue with Loss-Driven Development (LDD) — in the plugin manifests, scripts, install instructions, or the methodology content itself (e.g. a rule that could lead a compliant agent into a security failure) — please **do not** open a public GitHub issue.

Instead, email **silvio.jurk@googlemail.com** with:

- A clear description of the issue
- Steps to reproduce (for scripts) or the specific skill + scenario (for methodology issues)
- Your assessment of severity and blast radius

You should expect an initial acknowledgement within 7 days.

## Scope

- `scripts/*.py` and `scripts/*.sh` — arbitrary code execution is the main risk class; if any script can be induced to execute unintended code, report it.
- `.claude-plugin/plugin.json`, `marketplace.json`, `gemini-extension.json` — manifest integrity issues (e.g. a crafted entry that misleads an agent about install paths).
- `skills/*/SKILL.md` — rules that could lead a compliant agent into a security failure (e.g. a rule that implies bypassing an authentication check under time pressure would be an issue).
- `docs/ldd/*.md` — same.

Out of scope: general agent-safety concerns unrelated to LDD-specific guidance, and security issues in host agents (Claude Code, Codex, Gemini CLI) themselves — report those to the respective vendors.

## Supported versions

The `main` branch is the only supported version. There is no LTS. Security fixes go on `main` and are released as patch bumps (`0.2.x`).

## Disclosure

Once a vulnerability is fixed, a CHANGELOG entry describes the class of issue at a level that does not re-enable exploitation. Detailed writeups may be shared with the reporter on request.

## What this plugin does NOT do

For transparency:

- LDD does not execute network calls during normal skill invocation — all skills are behavior-shaping markdown text, not tools
- `scripts/capture-clean-baseline.py` does make outbound HTTP to LLM providers (OpenRouter / OpenAI / Anthropic) using the user's own API key; no data is sent elsewhere
- `scripts/drift-scan.py` reads the local repo only; no network
- `scripts/evolve-skill.sh` is terminal-driven; no network
- The plugin manifests do not declare MCP servers, hooks, or commands that would run arbitrary code on install

This is by design. If LDD ever needs a capability beyond markdown, the scope change will be audited and documented.
