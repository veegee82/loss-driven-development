#!/usr/bin/env python3
"""Drift-scan for the seven LDD drift indicators.

Runs quick checks for identifier drift, contract drift, layer drift, doc-model
drift, rubric drift, test/spec drift, and defaults drift across a target repo.
Outputs a Markdown report to stdout (or to --out).

This is a best-effort heuristic scanner, not a static-analysis tool. It finds
candidates for human review; it does not prove drift.

Usage:
    python scripts/drift-scan.py [--repo PATH] [--out REPORT.md] [--exclude DIR...]

By default, excludes common virtualenv / build / cache dirs AND this bundle's
own scripts/ directory (so the scanner's own synonym lists don't show up as
"identifier drift" findings).

See skills/drift-detection/SKILL.md for the conceptual spec.
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable


@dataclass
class Finding:
    indicator: str
    detail: str

    def render(self) -> str:
        return f"- {self.detail}"


@dataclass
class Report:
    findings: dict[str, list[Finding]] = field(default_factory=lambda: defaultdict(list))

    def add(self, indicator: str, detail: str) -> None:
        self.findings[indicator].append(Finding(indicator, detail))

    def render(self) -> str:
        lines = ["# Drift scan"]
        if not any(self.findings.values()):
            lines.append("")
            lines.append("_No drift indicators fired. Either the project is healthy, the scan is incomplete, or the indicators are miscalibrated. Review the indicator list in `skills/drift-detection/SKILL.md`._")
            return "\n".join(lines)
        for indicator in INDICATORS:
            findings = self.findings.get(indicator, [])
            if not findings:
                continue
            lines.append("")
            lines.append(f"## {indicator}")
            for f in findings:
                lines.append(f.render())
        return "\n".join(lines)


INDICATORS = [
    "Identifier drift",
    "Contract drift",
    "Layer drift",
    "Doc-model drift",
    "Rubric drift",
    "Test/spec drift",
    "Defaults drift",
    "Moving-target-loss drift",
]


# Epoch-abuse threshold: more than one bump per N iterations in the same task
# suggests the scope is being reset to mask regressions rather than recorded
# because reality actually shifted. Keep conservative — false positives here
# are noise but not destructive; false negatives defeat the whole point of
# epoch markers. v0.13.x Fix 1.
EPOCH_ABUSE_ITER_WINDOW = 5


def iter_code_files(root: Path) -> Iterable[Path]:
    patterns = ("*.py", "*.ts", "*.tsx", "*.js", "*.jsx", "*.go", "*.rs", "*.java", "*.rb")
    for pattern in patterns:
        yield from root.rglob(pattern)


def iter_doc_files(root: Path) -> Iterable[Path]:
    yield from root.rglob("*.md")


_DEFAULT_EXCLUDES = {
    ".git", "node_modules", "__pycache__", ".venv", "venv", "dist", "build",
    "target", ".pytest_cache", ".mypy_cache", ".ruff_cache", ".tox", "vendor",
    "scripts",  # avoid false positives where the scanner finds its own heuristic lists
}


def skip_path(p: Path, extra: set[str] | None = None) -> bool:
    parts = set(p.parts)
    excludes = _DEFAULT_EXCLUDES | (extra or set())
    return bool(parts & excludes)


# ---------- Indicator 1: identifier drift ----------
SYNONYM_GROUPS = [
    ("user_id", "userId", "uid"),
    ("request_id", "requestId", "reqId", "rid"),
    ("order_id", "orderId", "oid"),
    ("created_at", "createdAt", "creationTime"),
    ("updated_at", "updatedAt", "modificationTime"),
]


def check_identifier_drift(report: Report, root: Path) -> None:
    for group in SYNONYM_GROUPS:
        counts: Counter[str] = Counter()
        for path in iter_code_files(root):
            if skip_path(path):
                continue
            try:
                text = path.read_text(errors="replace")
            except OSError:
                continue
            for name in group:
                counts[name] += len(re.findall(rf"\b{name}\b", text))
        present = {k: v for k, v in counts.items() if v > 0}
        if len(present) >= 2:
            detail = ", ".join(f"`{k}` ({v})" for k, v in sorted(present.items(), key=lambda kv: -kv[1]))
            report.add("Identifier drift", f"{detail} — same concept, multiple names")


# ---------- Indicator 2: contract drift ----------
def check_contract_drift(report: Report, root: Path) -> None:
    # Heuristic: Python only. Find functions defined with the same name in
    # multiple locations with differing arg-list lengths.
    defs: dict[str, set[tuple[str, int]]] = defaultdict(set)
    def_re = re.compile(r"^def\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\(([^)]*)\)", re.MULTILINE)
    for path in root.rglob("*.py"):
        if skip_path(path):
            continue
        try:
            text = path.read_text(errors="replace")
        except OSError:
            continue
        for m in def_re.finditer(text):
            name, args = m.group(1), m.group(2)
            arg_count = len([a for a in args.split(",") if a.strip() and not a.strip().startswith("self")])
            defs[name].add((str(path.relative_to(root)), arg_count))
    for name, locs in defs.items():
        if len({arg_count for _, arg_count in locs}) >= 2 and len(locs) >= 2:
            detail = f"`{name}` — defined with differing arg counts across " + ", ".join(
                f"{p} ({a} args)" for p, a in sorted(locs)
            )
            report.add("Contract drift", detail)


# ---------- Indicator 3: layer drift ----------
LAYER_PATTERNS = {
    "domain": re.compile(r"(^|/)domain(/|$)"),
    "persistence": re.compile(r"(^|/)(persistence|db|storage)(/|$)"),
    "transport": re.compile(r"(^|/)(transport|api|http|grpc)(/|$)"),
    "ui": re.compile(r"(^|/)(ui|frontend|views?|components?)(/|$)"),
}


def infer_layer(p: Path) -> str | None:
    s = str(p)
    for layer, pat in LAYER_PATTERNS.items():
        if pat.search(s):
            return layer
    return None


FORBIDDEN_EDGES = {
    ("domain", "persistence"),
    ("domain", "transport"),
    ("domain", "ui"),
    ("ui", "persistence"),
}

IMPORT_RE = re.compile(r"^\s*(?:from\s+([.\w]+)\s+import|import\s+([.\w]+))", re.MULTILINE)


def check_layer_drift(report: Report, root: Path) -> None:
    for path in root.rglob("*.py"):
        if skip_path(path):
            continue
        src_layer = infer_layer(path)
        if not src_layer:
            continue
        try:
            text = path.read_text(errors="replace")
        except OSError:
            continue
        for m in IMPORT_RE.finditer(text):
            module = (m.group(1) or m.group(2) or "").lstrip(".")
            dst_layer = None
            for layer in LAYER_PATTERNS:
                if module.startswith(layer) or f".{layer}." in f".{module}.":
                    dst_layer = layer
                    break
            if dst_layer and (src_layer, dst_layer) in FORBIDDEN_EDGES:
                rel = path.relative_to(root)
                report.add("Layer drift", f"`{rel}` ({src_layer}) imports `{module}` ({dst_layer})")


# ---------- Indicator 4: doc-model drift ----------
def check_doc_model_drift(report: Report, root: Path) -> None:
    readme = root / "README.md"
    if not readme.exists():
        return
    text = readme.read_text(errors="replace")
    # Actual top-level directories — for doc-model check we include all dirs, even
    # those excluded from code scanning (e.g. scripts/). We only skip git / cache /
    # hidden dirs so dotfile directories don't pollute the comparison.
    hidden_or_cache = {".git", ".github", "node_modules", "__pycache__", ".venv", "venv",
                        ".pytest_cache", ".mypy_cache", ".ruff_cache", ".tox", "dist", "build"}
    top_dirs = {
        p.name for p in root.iterdir()
        if p.is_dir() and not p.name.startswith(".") and p.name not in hidden_or_cache
    }
    # Match LOCAL path references only. Three conservative forms:
    #   (1) ](./name/...) — relative markdown link target
    #   (2) `name/`       — bare directory in backticks (trailing slash)
    #   (3) `name/file.ext` — path to a recognised source/doc file in backticks
    # This avoids matching GitHub URLs, `try/except`, `.github/*`, or
    # repo handles like `obra/superpowers` which don't match any of the three.
    file_exts = r"(?:md|py|sh|dot|svg|json|yaml|yml|toml|ts|tsx|js|jsx|go|rs)"
    path_patterns = [
        r"\]\(\./([a-z][a-z0-9_-]{1,})/",                    # (1)
        r"(?<![A-Za-z0-9_])`([a-z][a-z0-9_-]{1,})/`",        # (2)
        rf"(?<![A-Za-z0-9_])`([a-z][a-z0-9_-]{{1,}})/[^`]+\.{file_exts}`",  # (3) path to a source/doc file
        r"(?<![A-Za-z0-9_])`([a-z][a-z0-9_-]{1,})/\*`",      # (4) bare glob: `name/*`
    ]
    mentioned: set[str] = set()
    for pat in path_patterns:
        mentioned.update(re.findall(pat, text))
    if mentioned and (missing := mentioned - top_dirs):
        report.add("Doc-model drift", f"README mentions directories not present: {', '.join(sorted(missing))}")
    unmentioned = top_dirs - mentioned
    if unmentioned:
        report.add("Doc-model drift", f"Top-level dirs not mentioned in README: {', '.join(sorted(unmentioned))}")


# ---------- Indicator 5: rubric drift ----------
def check_rubric_drift(report: Report, root: Path) -> None:
    rubric_paths = list(root.rglob("rubric.md")) + list(root.rglob("evaluation.md"))
    for rp in rubric_paths:
        try:
            out = subprocess.run(
                ["git", "-C", str(root), "log", "--oneline", "--follow", "--", str(rp.relative_to(root))],
                capture_output=True, text=True, timeout=10,
            )
        except (subprocess.SubprocessError, OSError):
            continue
        lines = [ln for ln in out.stdout.splitlines() if ln.strip()]
        if len(lines) >= 2:
            last = lines[0]
            if not re.search(r"(delta|Δloss|Δ-loss|regression|rollback|evolve)", last, re.IGNORECASE):
                rel = rp.relative_to(root)
                report.add("Rubric drift", f"`{rel}` was edited (`{last[:60]}`) without a Δloss / evolve marker in the commit message")


# ---------- Indicator 6: test/spec drift ----------
def check_test_spec_drift(report: Report, root: Path) -> None:
    spec_dirs = [root / "spec", root / "specs", root / "docs" / "spec"]
    for spec_dir in spec_dirs:
        if not spec_dir.exists():
            continue
        for spec_file in spec_dir.rglob("*.md"):
            try:
                text = spec_file.read_text(errors="replace")
            except OSError:
                continue
            # Heuristic: look for normative words followed by a noun phrase.
            matches = re.findall(r"(?:MUST|SHOULD|REQUIRED|shall|must|should)\s+([a-zA-Z_][\w\s]{3,40})", text)
            if not matches:
                continue
            report.add(
                "Test/spec drift",
                f"`{spec_file.relative_to(root)}` contains {len(matches)} normative requirements; cross-check that each has a corresponding test"
            )
            break  # one note per spec file is enough


# ---------- Indicator 7: defaults drift ----------
DEFAULT_RE = re.compile(r"(?:DEFAULT|default)[_\s]?([A-Z_]+)\s*[:=]\s*(\d+|\"[^\"]+\"|'[^']+')", re.MULTILINE)


def check_thinking_levels_drift(report: Report, root: Path) -> None:
    """Verify the 5-level bucket boundaries agree across code + docs.

    The scorer in `scripts/level_scorer.py`, the SKILL.md table in
    `skills/using-ldd/SKILL.md`, and the authoritative doc at
    `docs/ldd/thinking-levels.md` must all agree on the 4 boundaries
    (between L0/L1, L1/L2, L2/L3, L3/L4). Any disagreement is a doc-sync
    failure that would let the scorer and the user's mental model drift
    apart.
    """
    scorer_path = root / "scripts" / "level_scorer.py"
    doc_path = root / "docs" / "ldd" / "thinking-levels.md"
    skill_path = root / "skills" / "using-ldd" / "SKILL.md"

    if not scorer_path.exists():
        return  # thinking-levels not installed in this repo

    scorer_text = scorer_path.read_text(errors="replace")
    # The score_to_level function uses plain integer literals in if-branches.
    # Extract the four boundaries by order of appearance in the function.
    func_match = re.search(
        r"def score_to_level.*?return Level\.L4",
        scorer_text,
        re.DOTALL,
    )
    if not func_match:
        report.add(
            "Test/spec drift",
            "thinking-levels: could not locate `score_to_level` in "
            "`scripts/level_scorer.py` — the drift check needs the function to "
            "be importable for the check to run.",
        )
        return
    func_body = func_match.group(0)
    boundaries_in_code = [
        int(m) for m in re.findall(r"score\s*<=\s*(-?\d+)", func_body)
    ]
    if len(boundaries_in_code) != 4:
        report.add(
            "Test/spec drift",
            f"thinking-levels: expected 4 `score <= N` branches in "
            f"`score_to_level`, found {len(boundaries_in_code)}. Probably a "
            f"refactor that moved the boundaries out of this pattern.",
        )
        return

    # Normalize: the scorer uses ≤ against each boundary; docs use Unicode
    # ≤ / ≥. We extract the 4 numbers from doc tables that look like
    # "score ≤ N" or "score ≥ N" or "A ≤ score ≤ B" rows.
    def extract_doc_boundaries(text: str) -> list[int]:
        # Unicode minus U+2212 is used in the doc tables; normalize to ASCII "-"
        norm = text.replace("−", "-")
        found: list[int] = []
        for m in re.finditer(
            r"score\s*(?:≤|<=)\s*(-?\d+)|(-?\d+)\s*(?:≤|<=)\s*score\s*(?:≤|<=)\s*(-?\d+)|score\s*(?:≥|>=)\s*(-?\d+)",
            norm,
        ):
            for g in m.groups():
                if g is not None:
                    found.append(int(g))
        return found

    for doc_file, doc_label in ((doc_path, "thinking-levels.md"), (skill_path, "using-ldd SKILL.md")):
        if not doc_file.exists():
            continue
        doc_text = doc_file.read_text(errors="replace")
        doc_bounds = extract_doc_boundaries(doc_text)
        # The doc table carries: ≤ −7 | −6 ≤ … ≤ −2 | −1 ≤ … ≤ 3 | 4 ≤ … ≤ 7 | ≥ 8
        # That gives us the set {−7, −6, −2, −1, 3, 4, 7, 8}.
        expected_set = set()
        for b in boundaries_in_code:
            expected_set.add(b)        # upper bound of the bucket
            expected_set.add(b + 1)    # lower bound of the next bucket
        # The L4 bucket has no "score <= N" branch in code, but its lower bound
        # is (last_boundary + 1). That's already in expected_set.
        doc_set = set(doc_bounds)
        missing = expected_set - doc_set
        if missing:
            report.add(
                "Doc-model drift",
                f"thinking-levels: {doc_label} missing boundary number(s) "
                f"{sorted(missing)} — code boundaries in `score_to_level` "
                f"are {boundaries_in_code}, doc must cover the full "
                f"complementary set {sorted(expected_set)}. Sync the bucket "
                f"table in the doc to match the scorer.",
            )


def check_defaults_drift(report: Report, root: Path) -> None:
    declared: dict[str, set[tuple[str, str]]] = defaultdict(set)
    for path in iter_code_files(root):
        if skip_path(path):
            continue
        try:
            text = path.read_text(errors="replace")
        except OSError:
            continue
        for m in DEFAULT_RE.finditer(text):
            name, value = m.group(1), m.group(2)
            declared[name].add((str(path.relative_to(root)), value))
    for name, locs in declared.items():
        values = {v for _, v in locs}
        if len(values) >= 2:
            detail = f"`DEFAULT_{name}` has {len(values)} different values across files: " + "; ".join(
                f"{p}={v}" for p, v in sorted(locs)
            )
            report.add("Defaults drift", detail)


def check_moving_target_loss_drift(report: Report, root: Path) -> None:
    """Flag projects whose `.ldd/trace.log` bumps epoch too often.

    v0.13.x Fix 1 introduced explicit epoch markers so cross-epoch Δloss
    comparisons can be suppressed (honest). The same mechanism can be abused:
    an agent that hits a regression could bump the epoch to erase the bad
    delta from the display. The guard is simple — count bumps per task and
    compare to the task's iteration count.

    Heuristics:
        * ``>= 2`` bumps in a task with ``<= EPOCH_ABUSE_ITER_WINDOW``
          iterations → abuse candidate.
        * ``>= 3`` bumps in any task → abuse candidate regardless of length
          (three rubric changes mid-task is implausible in normal work).

    Reports per-task; aggregates by task title so reviewers can skim and
    triage without opening the trace.log.
    """
    trace = root / ".ldd" / "trace.log"
    if not trace.exists():
        return
    try:
        lines = trace.read_text(errors="replace").splitlines()
    except OSError:
        return
    # Walk the log, segmenting on `meta` lines (task boundaries). Keep a
    # running count of `epoch` lines and `iter` lines per task.
    current_task: str | None = None
    iters_in_task = 0
    bumps_in_task = 0
    findings: list[tuple[str, int, int]] = []

    def flush() -> None:
        nonlocal current_task, iters_in_task, bumps_in_task
        if current_task is None:
            return
        abuse = False
        if bumps_in_task >= 3:
            abuse = True
        elif bumps_in_task >= 2 and iters_in_task <= EPOCH_ABUSE_ITER_WINDOW:
            abuse = True
        if abuse:
            findings.append((current_task, iters_in_task, bumps_in_task))

    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        # Cheap tokenizer — enough to tell meta/iter/epoch apart.
        tokens = stripped.split()
        if len(tokens) < 2:
            continue
        kind = tokens[1]
        if kind == "meta":
            flush()
            # Extract the task title (unquoted for the heuristic — exact
            # match not needed, readable label is).
            m = re.search(r'task="([^"]*)"', stripped) or re.search(r"task=(\S+)", stripped)
            current_task = m.group(1) if m else "(unnamed)"
            iters_in_task = 0
            bumps_in_task = 0
        elif kind == "epoch":
            bumps_in_task += 1
        elif kind in ("inner", "refine", "outer", "design", "cot"):
            iters_in_task += 1
    flush()

    for title, iters, bumps in findings:
        report.add(
            "Moving-target-loss drift",
            f"Task \"{title}\": {bumps} epoch bumps across {iters} iterations — "
            "exceeds the 1-bump-per-5-iterations guard. Review the bump "
            "reasons in `.ldd/trace.log` — epoch bumps should record real "
            "rubric/scope shifts, not erase inconvenient regressions.",
        )


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=".", help="Repository root to scan")
    ap.add_argument("--out", default=None, help="Output file (default: stdout)")
    ap.add_argument("--exclude", action="append", default=[], metavar="DIR",
                    help="Extra directory name to exclude (can repeat). "
                         "Defaults already exclude common vendor/build/cache dirs and scripts/.")
    args = ap.parse_args()

    root = Path(args.repo).resolve()
    if not root.exists():
        print(f"error: repo path not found: {root}", file=sys.stderr)
        return 2

    # Merge user-supplied excludes into the module default so every scanner honors them.
    _DEFAULT_EXCLUDES.update(args.exclude)

    report = Report()
    check_identifier_drift(report, root)
    check_contract_drift(report, root)
    check_layer_drift(report, root)
    check_doc_model_drift(report, root)
    check_rubric_drift(report, root)
    check_test_spec_drift(report, root)
    check_defaults_drift(report, root)
    check_thinking_levels_drift(report, root)
    check_moving_target_loss_drift(report, root)

    out = report.render()
    if args.out:
        Path(args.out).write_text(out + "\n")
    else:
        print(out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
