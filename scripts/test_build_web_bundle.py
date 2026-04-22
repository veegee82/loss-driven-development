"""Tests for build_web_bundle.

Run with:
    python -m pytest scripts/test_build_web_bundle.py -v

Covers:
    - Deterministic build (same bytes across two runs, fixed mtime)
    - Drift-check: clean after build, failing after source edit
    - SKILL.md shape: YAML frontmatter, name, description
    - Bundle carries the full trace-block specification from using-ldd
      (per-iteration emission, final Close block, four visualization
      channels, rendering recipe, red flags — the audit surface users
      need for inline + end-of-task trace rendering to work)
    - All intra-bundle links resolve to files that actually exist
    - ZIP archive contains the expected files, with fixed mtime
    - host-statusline and other excluded assets are cleanly stubbed
"""
from __future__ import annotations

import hashlib
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = REPO_ROOT / "scripts" / "build_web_bundle.py"
BUNDLE_DIR = REPO_ROOT / "dist" / "web-bundle"
FLAT_BUNDLE = BUNDLE_DIR / "ldd"
ZIP_PATH = BUNDLE_DIR / "ldd-skill.zip"


# --- helpers --------------------------------------------------------------


def run_build(out_dir: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--out", str(out_dir)],
        capture_output=True, text=True, check=True,
    )


def run_check(out_dir: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--check", "--out", str(out_dir)],
        capture_output=True, text=True,
    )


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


# --- fixtures -------------------------------------------------------------


@pytest.fixture(scope="module")
def fresh_bundle(tmp_path_factory) -> Path:
    """Build the bundle once into a temp dir; tests read from it read-only."""
    tmp = tmp_path_factory.mktemp("web-bundle")
    run_build(tmp)
    return tmp


@pytest.fixture(scope="module")
def skill_md_text(fresh_bundle: Path) -> str:
    return (fresh_bundle / "ldd" / "SKILL.md").read_text(encoding="utf-8")


# --- determinism + drift --------------------------------------------------


def test_build_is_deterministic(tmp_path):
    """Two consecutive builds must produce byte-identical ZIPs. Without
    this, every build is a spurious git diff — breaks the drift gate."""
    out_a = tmp_path / "a"
    out_b = tmp_path / "b"
    run_build(out_a)
    run_build(out_b)
    assert sha256(out_a / "ldd-skill.zip") == sha256(out_b / "ldd-skill.zip")


def test_check_passes_after_fresh_build():
    """The committed bundle under dist/web-bundle/ must match the source."""
    result = run_check(BUNDLE_DIR)
    assert result.returncode == 0, f"drift vs. committed bundle:\n{result.stderr}"


def test_check_detects_source_drift(tmp_path, monkeypatch):
    """Flip a bundled source file → check must exit 1. Guards the gate
    itself — a gate that never fails is worse than no gate."""
    shadow = tmp_path / "shadow-repo"
    shutil.copytree(REPO_ROOT, shadow, ignore=shutil.ignore_patterns(
        ".git", "__pycache__", ".pytest_cache", "node_modules"
    ))
    skill = shadow / "skills" / "using-ldd" / "SKILL.md"
    skill.write_text(
        skill.read_text() + "\n\n<!-- drift injection -->\n", encoding="utf-8"
    )
    result = subprocess.run(
        [sys.executable, str(shadow / "scripts" / "build_web_bundle.py"),
         "--check", "--out", str(shadow / "dist" / "web-bundle")],
        capture_output=True, text=True,
    )
    assert result.returncode == 1
    assert "DRIFT" in result.stderr


def test_zip_has_fixed_mtime():
    """All ZIP entries must carry the pinned mtime (2020-01-01). A wall-clock
    mtime leak produces a new hash on every build and defeats determinism."""
    with zipfile.ZipFile(ZIP_PATH) as zf:
        for info in zf.infolist():
            assert info.date_time == (2020, 1, 1, 0, 0, 0), (
                f"{info.filename} has mtime {info.date_time}"
            )


# --- frontmatter + dispatcher --------------------------------------------


def test_skill_md_has_valid_frontmatter(skill_md_text: str):
    match = re.match(r"^---\n(.+?)\n---\n", skill_md_text, re.DOTALL)
    assert match, "SKILL.md missing YAML frontmatter"
    front = match.group(1)
    assert re.search(r"^name:\s*ldd\s*$", front, re.MULTILINE)
    assert re.search(r"^description:\s*.+", front, re.MULTILINE | re.DOTALL)


def test_description_names_all_included_skills(skill_md_text: str):
    """The frontmatter description is what Claude Web's auto-trigger
    matches against. If a bundled skill isn't named, it won't fire."""
    desc = re.search(r"description:\s*(.+?)\n---", skill_md_text, re.DOTALL)
    assert desc is not None
    desc_text = desc.group(1)
    for name in [
        "reproducibility-first", "root-cause-by-layer", "loss-backprop-lens",
        "e2e-driven-iteration", "loop-driven-engineering", "iterative-refinement",
        "method-evolution", "drift-detection", "dialectical-cot",
        "dialectical-reasoning", "docs-as-definition-of-done", "define-metric",
        "architect-mode", "bootstrap-userspace",
    ]:
        assert name in desc_text, f"skill '{name}' missing from frontmatter description"


# --- trace-block spec preservation ---------------------------------------
# These are the load-bearing rules: without them, Claude Web will NOT
# emit inline per-iteration traces or the final close block.


def test_per_iteration_emission_rule_present(skill_md_text: str):
    assert "AFTER EVERY ITERATION" in skill_md_text, (
        "Per-iteration emission rule missing — inline traces won't render"
    )


def test_final_close_block_rule_present(skill_md_text: str):
    # "at loop close" + "Close section" + "final block"
    assert "loop close" in skill_md_text.lower()
    assert "Close section" in skill_md_text
    assert re.search(r"terminal\s*:\s*(complete|<?terminal)", skill_md_text, re.IGNORECASE)


def test_end_of_message_re_emission_rule_present(skill_md_text: str):
    assert "end of each message" in skill_md_text


def test_four_visualization_channels_specified(skill_md_text: str):
    """Sparkline + mini chart + mode+info line + trend arrow are the
    four channels the spec calls 'mandatory' for the trace block."""
    for needle in ["sparkline", "chart", "mode+info line", "trend arrow"]:
        assert needle in skill_md_text.lower(), f"channel '{needle}' missing"


def test_rendering_recipe_is_deterministic(skill_md_text: str):
    """The copy-verbatim rendering recipe must carry the exact formulas —
    otherwise two agents render different traces from the same numbers."""
    assert "Rendering recipe (deterministic — copy verbatim)" in skill_md_text
    for needle in [
        "▁▂▃▄▅▆▇█",             # sparkline glyphs
        "round(v / max(v) * 7)",  # index formula
        "ceil(max(v) / 0.25)",    # chart y-axis formula
        "round-half-up",          # snap rule
    ]:
        assert needle in skill_md_text, f"recipe missing formula: {needle!r}"


def test_red_flags_present(skill_md_text: str):
    """v0.5.1 red flags — rationalizations that cause agents to skip
    the per-iteration trace. Without them, the per-iteration rule
    degrades to 'when convenient'."""
    assert "RED FLAGS" in skill_md_text
    assert "post-mortem" in skill_md_text.lower() or "after the task" in skill_md_text.lower()


def test_bootstrap_userspace_fallback_documented(skill_md_text: str):
    """Claude Web has no writable .ldd/ — the bundle MUST document the
    non-filesystem fallback, or trace persistence silently fails."""
    assert "bootstrap-userspace" in skill_md_text
    assert "Tier" in skill_md_text  # tier protocol
    assert "artifact" in skill_md_text.lower() or "conversation-history" in skill_md_text.lower()


def test_announcing_skill_invocation_rule_present(skill_md_text: str):
    """Every skill invocation must be announced before application —
    this is what makes the trace auditable in real time."""
    assert "*Invoking" in skill_md_text
    assert re.search(r"say which skill", skill_md_text, re.IGNORECASE)


# --- link resolution -----------------------------------------------------


def test_all_intra_bundle_links_resolve(fresh_bundle: Path):
    """Every `[text](path)` link in any bundled markdown must point to
    a file that exists in the bundle OR be an absolute URL."""
    bundle = fresh_bundle / "ldd"
    link_re = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
    broken: list[tuple[str, str]] = []
    for md in bundle.rglob("*.md"):
        for match in link_re.finditer(md.read_text(encoding="utf-8")):
            target = match.group(1).split("#")[0]
            if not target or target.startswith(("http://", "https://", "mailto:")):
                continue
            resolved = (md.parent / target).resolve()
            try:
                resolved.relative_to(bundle.resolve())
            except ValueError:
                broken.append((str(md.relative_to(bundle)), target))
                continue
            if not resolved.exists():
                broken.append((str(md.relative_to(bundle)), target))
    assert not broken, "broken intra-bundle links:\n" + "\n".join(
        f"  {src}: {tgt}" for src, tgt in broken
    )


# --- excluded-asset hygiene ----------------------------------------------


def test_host_statusline_stubbed_not_broken(fresh_bundle: Path):
    """host-statusline is excluded. Remaining references must be
    documentation-only (not live links) — otherwise Claude Web will
    follow a dead reference."""
    bundle = fresh_bundle / "ldd"
    for md in bundle.rglob("*.md"):
        text = md.read_text(encoding="utf-8")
        # No live markdown link pointing at host-statusline
        assert not re.search(
            r"\[[^\]]*host-statusline[^\]]*\]\([^)]*host-statusline[^)]*\)",
            text,
        ), f"{md.relative_to(bundle)}: live host-statusline link survives"


def test_no_diagrams_referenced_as_images(fresh_bundle: Path):
    bundle = fresh_bundle / "ldd"
    for md in bundle.rglob("*.md"):
        text = md.read_text(encoding="utf-8")
        assert "](diagrams/" not in text
        assert "](../diagrams/" not in text
        assert "](../../diagrams/" not in text


def test_no_path_traversal_to_unshipped_sources(fresh_bundle: Path):
    """Links that escape the bundle (../../scripts/..., ../../tests/...)
    are worse than broken — they leak a relative path into the user's
    Claude Web workspace where nothing resolves."""
    bundle = fresh_bundle / "ldd"
    for md in bundle.rglob("*.md"):
        text = md.read_text(encoding="utf-8")
        bad = re.findall(r"\]\(\.\.\/\.\.\/(?:scripts|tests|docs|skills)/[^)]+\)", text)
        assert not bad, f"{md.relative_to(bundle)} has escape links: {bad[:3]}"


# --- zip archive structure ----------------------------------------------


def test_zip_contains_exactly_the_expected_files():
    with zipfile.ZipFile(ZIP_PATH) as zf:
        names = sorted(zf.namelist())
    expected_prefix = "ldd/"
    expected_top = {"ldd/SKILL.md", "ldd/README.md"}
    expected_references = {
        f"ldd/references/{n}.md" for n in [
            "architect-mode", "bootstrap-userspace", "convergence",
            "define-metric", "dialectical-cot", "dialectical-reasoning",
            "docs-as-definition-of-done", "drift-detection",
            "e2e-driven-iteration", "hyperparameters", "iterative-refinement",
            "loop-driven-engineering", "loss-backprop-lens",
            "method-evolution", "reproducibility-first",
            "root-cause-by-layer", "theory", "thinking-levels",
        ]
    } | {"ldd/references/level_scorer.py"}
    actual_set = set(names)
    missing = (expected_top | expected_references) - actual_set
    assert not missing, f"missing from zip: {missing}"
    for name in names:
        assert name.startswith(expected_prefix), f"stray entry {name}"


def test_zip_drag_and_drop_shape():
    """Claude Web expects SKILL.md at the root of the skill folder inside
    the zip. `ldd/SKILL.md` (single top-level dir named 'ldd') is the
    shape; flat 'SKILL.md' at archive root is wrong, as is nested
    'ldd/ldd/SKILL.md'."""
    with zipfile.ZipFile(ZIP_PATH) as zf:
        top_dirs = {n.split("/", 1)[0] for n in zf.namelist()}
    assert top_dirs == {"ldd"}, f"zip must have exactly one top-level dir 'ldd', got {top_dirs}"
    with zipfile.ZipFile(ZIP_PATH) as zf:
        assert "ldd/SKILL.md" in zf.namelist()


# --- references carry their own body, not just a stub --------------------


def test_each_reference_has_its_own_body(fresh_bundle: Path):
    """A reference file that was reduced to a link-only placeholder
    would silently break progressive disclosure — the agent would
    follow the link and find no content."""
    refs = fresh_bundle / "ldd" / "references"
    for md in refs.glob("*.md"):
        body = md.read_text(encoding="utf-8")
        # Minimum viable body — well past the frontmatter block.
        assert len(body) > 1500, f"{md.name} suspiciously small ({len(body)} bytes)"
        assert "## " in body, f"{md.name} missing sections (progressive disclosure needs them)"


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
