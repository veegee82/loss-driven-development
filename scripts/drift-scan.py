#!/usr/bin/env python3
"""Drift-scan for the seven LDD drift indicators.

Runs quick checks for identifier drift, contract drift, layer drift, doc-model
drift, rubric drift, test/spec drift, and defaults drift across a target repo.
Outputs a Markdown report to stdout (or to --out).

This is a best-effort heuristic scanner, not a static-analysis tool. It finds
candidates for human review; it does not prove drift.

Usage:
    python scripts/drift-scan.py [--repo PATH] [--out REPORT.md]

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
]


def iter_code_files(root: Path) -> Iterable[Path]:
    patterns = ("*.py", "*.ts", "*.tsx", "*.js", "*.jsx", "*.go", "*.rs", "*.java", "*.rb")
    for pattern in patterns:
        yield from root.rglob(pattern)


def iter_doc_files(root: Path) -> Iterable[Path]:
    yield from root.rglob("*.md")


def skip_path(p: Path) -> bool:
    parts = set(p.parts)
    return bool(parts & {".git", "node_modules", "__pycache__", ".venv", "venv", "dist", "build", "target"})


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
    # Heuristic: README mentions a service/module list; compare with actual dirs.
    top_dirs = {p.name for p in root.iterdir() if p.is_dir() and not p.name.startswith(".") and not skip_path(p)}
    mentioned = set(re.findall(r"`([a-z][a-z0-9_-]{2,})/`", text))
    if mentioned and (missing := mentioned - top_dirs):
        report.add("Doc-model drift", f"README mentions directories not present: {', '.join(sorted(missing))}")
    if top_dirs - {"skills", "tests", "docs", "diagrams", "scripts"} and mentioned and (unmentioned := top_dirs - mentioned - {"skills", "tests", "docs", "diagrams", "scripts", ".claude-plugin"}):
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


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=".", help="Repository root to scan")
    ap.add_argument("--out", default=None, help="Output file (default: stdout)")
    args = ap.parse_args()

    root = Path(args.repo).resolve()
    if not root.exists():
        print(f"error: repo path not found: {root}", file=sys.stderr)
        return 2

    report = Report()
    check_identifier_drift(report, root)
    check_contract_drift(report, root)
    check_layer_drift(report, root)
    check_doc_model_drift(report, root)
    check_rubric_drift(report, root)
    check_test_spec_drift(report, root)
    check_defaults_drift(report, root)

    out = report.render()
    if args.out:
        Path(args.out).write_text(out + "\n")
    else:
        print(out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
