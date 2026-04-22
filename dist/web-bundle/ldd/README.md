# LDD — Claude Web / Desktop Skill Bundle

This folder is the flat, cross-platform export of the Loss-Driven Development skill bundle, generated from the plugin-layout source at `skills/` by `scripts/build_web_bundle.py`.

## Install on Claude Web / Desktop

Drag `ldd-skill.zip` onto the Skills upload area.

## Install on Claude Code / Codex / Gemini CLI

Use the plugin install in the project root README — the CLI agents load the native plugin layout at `skills/<name>/SKILL.md`, not this bundle. This export exists for hosts that only accept a single SKILL.md + references/ skill.

## Do not edit by hand

Every file here is regenerated from `skills/`, `docs/`, and `scripts/level_scorer.py` on every build. Edit the source, not the bundle. The drift-check (`python scripts/build_web_bundle.py --check`) blocks commits that ship an out-of-sync bundle.
