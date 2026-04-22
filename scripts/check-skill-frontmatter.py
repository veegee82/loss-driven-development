#!/usr/bin/env python3
"""Validate SKILL.md YAML frontmatter across all skills/*/SKILL.md.

A malformed frontmatter (missing `---` delimiters, missing `name`, missing
`description`, empty values) silently breaks plugin registration on several
hosts — Claude Code just drops the skill, Gemini CLI logs a warning but
continues. This check fails CI fast when the frontmatter drifts.

Exit codes:
  0  — every SKILL.md has valid frontmatter
  1  — one or more SKILL.md files failed validation
  2  — no SKILL.md files found (repo layout changed)
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SKILLS_DIR = REPO_ROOT / "skills"

FRONTMATTER_DELIMITER = re.compile(r"^---\s*$")
KEY_RE = re.compile(r"^([A-Za-z_][A-Za-z0-9_-]*)\s*:\s*(.*)$")

REQUIRED_KEYS = ("name", "description")
MIN_DESCRIPTION_LEN = 40  # one short sentence minimum


def parse_frontmatter(path: Path) -> tuple[dict[str, str] | None, str | None]:
    """Return (frontmatter_dict, error_message).

    frontmatter_dict is None when parsing failed; error_message names why.
    """
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except Exception as exc:
        return None, f"unreadable: {exc}"

    if not lines or not FRONTMATTER_DELIMITER.match(lines[0]):
        return None, "missing opening '---' delimiter on line 1"

    end = None
    for idx in range(1, len(lines)):
        if FRONTMATTER_DELIMITER.match(lines[idx]):
            end = idx
            break
    if end is None:
        return None, "missing closing '---' delimiter"

    data: dict[str, str] = {}
    current_key: str | None = None
    for raw in lines[1:end]:
        line = raw.rstrip()
        if not line.strip():
            current_key = None
            continue
        match = KEY_RE.match(line)
        if match:
            current_key = match.group(1)
            data[current_key] = match.group(2).strip()
        elif current_key and (line.startswith(" ") or line.startswith("\t")):
            # Continuation of previous value (rare; YAML folded scalars).
            data[current_key] = (data[current_key] + " " + line.strip()).strip()
    return data, None


def validate(path: Path) -> list[str]:
    data, err = parse_frontmatter(path)
    if data is None:
        return [err or "unknown parse error"]

    errors: list[str] = []
    for key in REQUIRED_KEYS:
        if key not in data:
            errors.append(f"missing required key '{key}'")
            continue
        if not data[key]:
            errors.append(f"key '{key}' is empty")

    desc = data.get("description", "")
    if desc and len(desc) < MIN_DESCRIPTION_LEN:
        errors.append(
            f"description too short ({len(desc)} chars, need >= {MIN_DESCRIPTION_LEN}); "
            "the harness uses description for auto-dispatch"
        )

    expected_name = path.parent.name
    actual_name = data.get("name", "")
    if actual_name and actual_name != expected_name:
        errors.append(
            f"name='{actual_name}' does not match containing dir '{expected_name}'"
        )

    return errors


def main() -> int:
    if not SKILLS_DIR.is_dir():
        print(f"error: {SKILLS_DIR} not found", file=sys.stderr)
        return 2

    skill_files = sorted(SKILLS_DIR.glob("*/SKILL.md"))
    if not skill_files:
        print(f"error: no SKILL.md files found under {SKILLS_DIR}", file=sys.stderr)
        return 2

    failed = 0
    for path in skill_files:
        errors = validate(path)
        rel = path.relative_to(REPO_ROOT)
        if errors:
            failed += 1
            print(f"FAIL {rel}")
            for err in errors:
                print(f"  - {err}")
        else:
            print(f"ok   {rel}")

    print()
    print(f"checked {len(skill_files)} SKILL.md files, {failed} failed")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
