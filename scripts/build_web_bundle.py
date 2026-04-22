#!/usr/bin/env python3
"""
build_web_bundle.py — assemble the LDD Claude-Web skill bundle.

Reads the plugin-layout skills under ``skills/<name>/SKILL.md`` plus a curated
set of docs, rewrites cross-links to the flat ``SKILL.md + references/*``
layout Claude Web expects, and writes the result to ``dist/web-bundle/ldd/``
and a deterministic ``dist/web-bundle/ldd-skill.zip``.

Modes:
    (no args)     build into dist/web-bundle/ (overwriting existing)
    --check       build into a temp dir, diff against dist/web-bundle/,
                  exit 1 on drift (used by pre-commit / CI)
    --out DIR     override output directory (default: dist/web-bundle)

The ZIP is deterministic: sorted entries, fixed mtime, no extras. The hash
changes only when content changes — not when the build happens to run.
"""

from __future__ import annotations

import argparse
import filecmp
import os
import re
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

# Skills that become references/<name>.md. Order matters for the index.
INCLUDED_SKILLS = [
    "reproducibility-first",
    "root-cause-by-layer",
    "loss-backprop-lens",
    "e2e-driven-iteration",
    "loop-driven-engineering",
    "iterative-refinement",
    "method-evolution",
    "drift-detection",
    "dialectical-cot",
    "dialectical-reasoning",
    "docs-as-definition-of-done",
    "define-metric",
    "architect-mode",
    # Included because using-ldd delegates to it for non-filesystem hosts
    # (Claude Web's default case). Not in user's original list but load-bearing.
    "bootstrap-userspace",
]

# Claude-Code-only skills skipped from the Web bundle (they auto-no-op
# outside their host anyway; including them would just add dead weight).
EXCLUDED_SKILLS = {"host-statusline"}

# Docs bundled alongside the skills (referenced from SKILL.md and/or skills).
# Source paths relative to REPO_ROOT; all land flat in references/.
INCLUDED_DOCS = [
    "docs/theory.md",
    "docs/ldd/thinking-levels.md",
    "docs/ldd/hyperparameters.md",
    "docs/ldd/convergence.md",
]

# Reference-implementation scripts (linked from SKILL.md).
INCLUDED_SCRIPTS = [
    "scripts/level_scorer.py",
]

FIXED_MTIME = (2020, 1, 1, 0, 0, 0)

# Basenames that land in references/ — any link to a target with this
# basename (regardless of original path prefix) gets rewritten to the
# flat bundle path. Populated lazily from INCLUDED_SKILLS / INCLUDED_DOCS /
# INCLUDED_SCRIPTS the first time rewrite_links runs.
_INCLUDED_BASENAMES: set[str] = set()
_INCLUDED_SKILL_NAMES: set[str] = set()

# Patterns whose TARGET is a path we don't ship. The regex replaces the
# full markdown link with its link-text only (so `[foo](bar.svg)` → `foo`),
# or with a plain-text stub when a hint is useful.
_STRIPPED_LINK_PATTERNS = [
    # SVG diagrams anywhere in the tree, linked form
    (re.compile(r"\[([^\]]+)\]\((?:\.\./)*(?:docs/)?diagrams/[^)]+\)"), r"\1"),
    # Bare `diagrams/foo.svg` in backticks (was broken even in source)
    (re.compile(r"`(?:\.\./)*(?:docs/)?diagrams/[^`]+\.svg`"), "(diagram omitted in web bundle)"),
    # superpowers-plugin references — external to the LDD bundle
    (re.compile(r"\[([^\]]+)\]\((?:\.\./)+superpowers/[^)]+\)"), r"\1"),
    # `evaluation.md` at repo root — not bundled
    (re.compile(r"\[([^\]]+)\]\((?:\.\./)+evaluation\.md\)"), r"\1"),
    # test fixtures and test scripts — not bundled
    (re.compile(r"\[([^\]]+)\]\((?:\.\./)+tests/[^)]+\)"), r"\1"),
    (re.compile(r"\[([^\]]+)\]\((?:\.\./)+scripts/test_[^)]+\)"), r"\1"),
]


def _name_alternation(names: set[str]) -> str:
    """Safe regex alternation — longest first to avoid prefix issues."""
    return "|".join(re.escape(n) for n in sorted(names, key=len, reverse=True))


def _populate_basename_sets() -> None:
    """Lazy one-shot: compute the set of basenames that end up in references/
    (skills as `<name>.md`, docs as-is, scripts as-is) and the bare skill
    name set used for `<name>/SKILL.md`-style links."""
    if _INCLUDED_BASENAMES:
        return
    for name in INCLUDED_SKILLS:
        _INCLUDED_BASENAMES.add(f"{name}.md")
        _INCLUDED_SKILL_NAMES.add(name)
    for rel in INCLUDED_DOCS:
        _INCLUDED_BASENAMES.add(Path(rel).name)
    for rel in INCLUDED_SCRIPTS:
        _INCLUDED_BASENAMES.add(Path(rel).name)


def rewrite_links(text: str, *, in_skill_md: bool) -> str:
    """
    Rewrite relative cross-links to match the flat bundle layout.

    in_skill_md=True  → text lives at bundle root (SKILL.md). Refs go to
                        ``references/<name>.<ext>``.
    in_skill_md=False → text lives in references/<x>. Refs go to
                        ``./<name>.<ext>`` (same directory).

    A reference "back" from references/ up to SKILL.md itself
    (``using-ldd/SKILL.md``) maps to ``../SKILL.md``.
    """
    _populate_basename_sets()
    prefix = "references/" if in_skill_md else "./"

    # 1. Strip links to assets we don't ship.
    for pat, repl in _STRIPPED_LINK_PATTERNS:
        text = pat.sub(repl, text)

    # 2. `<name>/SKILL.md`-style links → flat `.md` for included skills.
    skill_alt = "|".join(re.escape(n) for n in sorted(_INCLUDED_SKILL_NAMES, key=len, reverse=True))
    if skill_alt:
        # Markdown link form: ](prefix/skillname/SKILL.md)
        text = re.sub(
            r"\]\((?:\./|(?:\.\./)+)?(?:skills/)?("
            + skill_alt
            + r")/SKILL\.md(?:\#[^)]*)?\)",
            lambda m: f"]({prefix}{m.group(1)}.md)",
            text,
        )
        # Backtick form: `prefix/skillname/SKILL.md`
        text = re.sub(
            r"`(?:\./|(?:\.\./)+)?(?:skills/)?("
            + skill_alt
            + r")/SKILL\.md`",
            lambda m: f"`{prefix}{m.group(1)}.md`",
            text,
        )

    # 3. Name-based rewrite for included docs/scripts/flat-md links.
    names_alt = "|".join(re.escape(n) for n in sorted(_INCLUDED_BASENAMES, key=len, reverse=True))
    if names_alt:
        # Covers all prefix shapes: `./`, `../`, `../../`, `docs/`,
        # `docs/ldd/`, `ldd/` (bare, as in docs/theory.md → ldd/x.md),
        # `skills/<x>/`, `scripts/`, or none.
        subdir_re = (
            r"(?:docs/(?:ldd/)?|ldd/|skills/[a-z0-9-]+/|scripts/)?"
        )
        # Markdown link form
        text = re.sub(
            r"\]\("
            r"(?:\./|(?:\.\./)+)?" + subdir_re + r"(" + names_alt + r")"
            r"(?:\#[^)]*)?\)",
            lambda m: f"]({prefix}{m.group(1)})",
            text,
        )
        # Backtick form
        text = re.sub(
            r"`"
            r"(?:\./|(?:\.\./)+)?" + subdir_re + r"(" + names_alt + r")"
            r"`",
            lambda m: f"`{prefix}{m.group(1)}`",
            text,
        )

    # 4. using-ldd/SKILL.md → the bundle's own SKILL.md
    back_to_skill_md = "](SKILL.md)" if in_skill_md else "](../SKILL.md)"
    back_to_skill_tick = "`SKILL.md`" if in_skill_md else "`../SKILL.md`"
    text = re.sub(
        r"\]\((?:\./|(?:\.\./)+)?(?:skills/)?using-ldd/SKILL\.md(?:\#[^)]*)?\)",
        back_to_skill_md,
        text,
    )
    text = re.sub(
        r"`(?:\./|(?:\.\./)+)?(?:skills/)?using-ldd/SKILL\.md`",
        back_to_skill_tick,
        text,
    )

    # 5. Excluded skills (host-statusline) — links that survived above.
    for skip in EXCLUDED_SKILLS:
        text = re.sub(
            r"\[`?" + re.escape(skip) + r"`?\]\([^)]*" + re.escape(skip) + r"[^)]*\)",
            f"`{skip}` (CLI-only, no-op on Web)",
            text,
        )

    return text


def strip_frontmatter_description(text: str) -> tuple[str, str]:
    """Return (description, body_without_frontmatter). Frontmatter is
    required on every skill file; a skill without it is a bug."""
    match = re.match(r"^---\n(.*?)\n---\n(.*)$", text, re.DOTALL)
    if not match:
        raise ValueError("missing YAML frontmatter")
    front, body = match.group(1), match.group(2)
    desc_match = re.search(
        r"^description:\s*(.+?)(?=\n[a-z_]+:|\Z)", front, re.MULTILINE | re.DOTALL
    )
    if not desc_match:
        raise ValueError("frontmatter missing 'description:'")
    description = " ".join(desc_match.group(1).strip().split())
    return description, body


def build_skill_md(using_ldd_source: Path) -> str:
    """Render the top-level SKILL.md from using-ldd, with rewritten links
    and a regenerated frontmatter that declares the flat bundle as one
    cohesive skill."""
    raw = using_ldd_source.read_text(encoding="utf-8")
    _, body = strip_frontmatter_description(raw)
    body = rewrite_links(body, in_skill_md=True)

    description = (
        "Loss-Driven Development (LDD) — Gradient Descent for Agents. "
        "Use whenever the user prefixes a message with 'LDD:' or mentions "
        "LDD, loss, gradient, SGD on code, drift, refinement loop, outer "
        "loop, inner loop, method evolution, or 'apply LDD'. Dispatcher "
        "for 14 sub-skills (reproducibility-first, root-cause-by-layer, "
        "loss-backprop-lens, e2e-driven-iteration, loop-driven-engineering, "
        "iterative-refinement, method-evolution, drift-detection, "
        "dialectical-cot, dialectical-reasoning, docs-as-definition-of-done, "
        "define-metric, architect-mode, bootstrap-userspace) loaded on "
        "demand from references/. Also triggers on: failing test, bug, "
        "error, flaky, symptom patch, design, architect, greenfield, "
        "refactor, polish, declaring done, ready to merge, release "
        "candidate, drift check."
    )

    frontmatter = f"---\nname: ldd\ndescription: {description}\n---\n"
    return frontmatter + body


def build_reference_md(skill_name: str, source: Path) -> str:
    """Render a references/<skill>.md from a plugin skill folder."""
    raw = source.read_text(encoding="utf-8")
    description, body = strip_frontmatter_description(raw)
    body = rewrite_links(body, in_skill_md=False)
    return (
        f"---\nname: {skill_name}\ndescription: {description}\n---\n{body}"
    )


def build_doc_md(source: Path) -> str:
    """Copy a doc file with link-rewriting; preserve everything else."""
    raw = source.read_text(encoding="utf-8")
    return rewrite_links(raw, in_skill_md=False)


def build_bundle(out_root: Path) -> None:
    """Assemble the full bundle at ``out_root/ldd/``. Overwrites cleanly."""
    bundle_root = out_root / "ldd"
    references = bundle_root / "references"

    if bundle_root.exists():
        shutil.rmtree(bundle_root)
    references.mkdir(parents=True)

    # 1. Top-level SKILL.md (from using-ldd)
    skill_md = build_skill_md(REPO_ROOT / "skills/using-ldd/SKILL.md")
    (bundle_root / "SKILL.md").write_text(skill_md, encoding="utf-8")

    # 2. Per-skill references
    for name in INCLUDED_SKILLS:
        src = REPO_ROOT / "skills" / name / "SKILL.md"
        if not src.exists():
            raise FileNotFoundError(f"missing skill: {src}")
        (references / f"{name}.md").write_text(
            build_reference_md(name, src), encoding="utf-8"
        )

    # 3. Docs (flattened — docs/ldd/foo.md → references/foo.md)
    for rel in INCLUDED_DOCS:
        src = REPO_ROOT / rel
        if not src.exists():
            raise FileNotFoundError(f"missing doc: {src}")
        dst_name = Path(rel).name
        (references / dst_name).write_text(
            build_doc_md(src), encoding="utf-8"
        )

    # 4. Scripts — copied verbatim, no rewrite (they're .py, not .md)
    for rel in INCLUDED_SCRIPTS:
        src = REPO_ROOT / rel
        if not src.exists():
            raise FileNotFoundError(f"missing script: {src}")
        shutil.copy2(src, references / Path(rel).name)

    # 5. Bundle README so a user who unzips can orient themselves
    (bundle_root / "README.md").write_text(bundle_readme(), encoding="utf-8")

    # 6. Deterministic ZIP
    write_deterministic_zip(bundle_root, out_root / "ldd-skill.zip")


def bundle_readme() -> str:
    return (
        "# LDD — Claude Web / Desktop Skill Bundle\n"
        "\n"
        "This folder is the flat, cross-platform export of the "
        "Loss-Driven Development skill bundle, generated from the "
        "plugin-layout source at `skills/` by `scripts/build_web_bundle.py`.\n"
        "\n"
        "## Install on Claude Web / Desktop\n"
        "\n"
        "Drag `ldd-skill.zip` onto the Skills upload area.\n"
        "\n"
        "## Install on Claude Code / Codex / Gemini CLI\n"
        "\n"
        "Use the plugin install in the project root README — the CLI agents "
        "load the native plugin layout at `skills/<name>/SKILL.md`, not this "
        "bundle. This export exists for hosts that only accept a single "
        "SKILL.md + references/ skill.\n"
        "\n"
        "## Do not edit by hand\n"
        "\n"
        "Every file here is regenerated from `skills/`, `docs/`, and "
        "`scripts/level_scorer.py` on every build. Edit the source, not the "
        "bundle. The drift-check (`python scripts/build_web_bundle.py "
        "--check`) blocks commits that ship an out-of-sync bundle.\n"
    )


def write_deterministic_zip(src_dir: Path, zip_path: Path) -> None:
    """Write a ZIP whose byte content depends only on the file contents,
    not on build time, filesystem order, or local permissions."""
    zip_path.parent.mkdir(parents=True, exist_ok=True)
    if zip_path.exists():
        zip_path.unlink()

    files = sorted(
        (p for p in src_dir.rglob("*") if p.is_file()),
        key=lambda p: p.relative_to(src_dir).as_posix(),
    )

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for path in files:
            arcname = f"ldd/{path.relative_to(src_dir).as_posix()}"
            info = zipfile.ZipInfo(filename=arcname, date_time=FIXED_MTIME)
            info.compress_type = zipfile.ZIP_DEFLATED
            # 0o100644 for regular file, 0o100755 for executable (.py scripts
            # get executable bit so the unzip preserves run-ability).
            mode = 0o755 if path.suffix == ".py" else 0o644
            info.external_attr = (0o100000 | mode) << 16
            zf.writestr(info, path.read_bytes())


def check_drift(default_out: Path) -> int:
    """Build into a temp dir, diff against the committed bundle. Exit code
    0 = clean, 1 = drift, 2 = no committed bundle."""
    if not (default_out / "ldd" / "SKILL.md").exists():
        print(
            f"[web-bundle] no committed bundle at {default_out} — run "
            "`python scripts/build_web_bundle.py` and commit the result",
            file=sys.stderr,
        )
        return 2

    with tempfile.TemporaryDirectory() as td:
        tmp_out = Path(td)
        build_bundle(tmp_out)
        diff = dir_diff(default_out, tmp_out)

    if not diff:
        print("[web-bundle] clean — dist/web-bundle/ matches source")
        return 0

    print(
        "[web-bundle] DRIFT — dist/web-bundle/ is out of sync with source.\n"
        "A skill, doc, or script changed without rebuilding. Run:\n"
        "    python scripts/build_web_bundle.py\n"
        "and commit the result in the same commit as the source change.\n\n"
        "Diff summary:",
        file=sys.stderr,
    )
    for line in diff:
        print(f"  {line}", file=sys.stderr)
    return 1


def dir_diff(a: Path, b: Path) -> list[str]:
    """Shallow-deep diff between two directories. Returns a list of human
    summary lines; empty list means identical."""
    cmp = filecmp.dircmp(a, b)
    out: list[str] = []
    _collect_diff(cmp, Path(""), out)
    return out


def _collect_diff(cmp: filecmp.dircmp, prefix: Path, out: list[str]) -> None:
    for name in cmp.left_only:
        out.append(f"only in committed:  {prefix / name}")
    for name in cmp.right_only:
        out.append(f"only in rebuilt:    {prefix / name}")
    # filecmp.dircmp.diff_files is shallow; force a byte-wise check.
    for name in cmp.common_files:
        left = Path(cmp.left) / name
        right = Path(cmp.right) / name
        if left.read_bytes() != right.read_bytes():
            out.append(f"content differs:    {prefix / name}")
    for sub_name, sub_cmp in cmp.subdirs.items():
        _collect_diff(sub_cmp, prefix / sub_name, out)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="verify committed dist/web-bundle/ matches source (exit 1 on drift)",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=REPO_ROOT / "dist" / "web-bundle",
        help="output directory (default: dist/web-bundle)",
    )
    args = parser.parse_args(argv)

    if args.check:
        return check_drift(args.out)

    build_bundle(args.out)
    print(f"[web-bundle] built {args.out}/ldd/ + {args.out}/ldd-skill.zip")
    return 0


if __name__ == "__main__":
    sys.exit(main())
