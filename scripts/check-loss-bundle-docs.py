#!/usr/bin/env python3
"""Gate: every place that cites Δloss_bundle must match the computed value.

Runs `compute-loss-bundle.py` to get the current authoritative number, then
greps the five canonical citation sites for their claimed value and compares
them. Any mismatch fails with an actionable diff so the maintainer knows
exactly which file to fix.

Canonical citation sites (kept in sync):

  1. README.md                     — hero badge + § "What Δloss_bundle means"
  2. evaluation.md                 — § Loss (bundle-wide)
  3. tests/README.md               — § Current measurements
  4. .claude-plugin/plugin.json    — description string
  5. SUBMISSION.md                 — criteria table

Any additional site that cites the number should add a parser below. Use
this script in the pre-commit hook (`./.githooks/pre-commit`) so doc drift
is caught BEFORE the bad commit lands.

Exit codes:
  0 — all cited values match computed value.
  1 — drift detected.
  2 — compute-loss-bundle.py itself could not run.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path


REPO = Path(__file__).resolve().parent.parent
COMPUTE = REPO / "scripts" / "compute-loss-bundle.py"


# --- Citation-site parsers -------------------------------------------------
# Each returns ``list[tuple[path, extracted_value]]`` or raises SystemExit if
# the file is missing. We deliberately search for the exact cited string
# rather than a looser pattern — a doc that doesn't cite the bundle value
# at all produces an EMPTY list, which is a separate "never cited" warning
# path (not a mismatch).


def _find_values(text: str) -> list[str]:
    """Extract every occurrence of `Δloss_bundle = X.XXX` (3-decimal form)."""
    pat = re.compile(r"Δloss_bundle\s*=\s*(0\.\d{3})")
    return pat.findall(text)


def _find_badge_value(text: str) -> list[str]:
    """Shields.io badge: `Δloss_bundle: 0.561 (normalized)` or URL-encoded form."""
    pats = [
        re.compile(r"%CE%94loss__bundle-(0\.\d{3})-"),
        re.compile(r"Δloss_bundle:\s*(0\.\d{3})"),
    ]
    out: list[str] = []
    for p in pats:
        out.extend(p.findall(text))
    return out


def _find_plugin_description(text: str) -> list[str]:
    """plugin.json: `Measured Δloss_bundle = 0.561 (normalized mean…)`."""
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return []
    desc = data.get("description", "")
    return _find_values(desc)


def _find_bundle_mean_formula(text: str) -> list[str]:
    """tests/README.md spells it out as `= 0.561` on a line of its own."""
    pat = re.compile(r"=\s*(0\.\d{3})\s*$", re.MULTILINE)
    return pat.findall(text)


SITES: list[tuple[str, callable]] = [
    ("README.md",                     lambda t: _find_values(t) + _find_badge_value(t)),
    ("evaluation.md",                 _find_values),
    ("tests/README.md",               lambda t: _find_values(t) + _find_bundle_mean_formula(t)),
    (".claude-plugin/plugin.json",    _find_plugin_description),
    ("SUBMISSION.md",                 _find_values),
]


def main() -> int:
    # 1. Get the authoritative value.
    try:
        result = subprocess.run(
            [sys.executable, str(COMPUTE), "--json"],
            capture_output=True, text=True, check=False,
        )
    except OSError as exc:
        print(f"[check] failed to invoke compute-loss-bundle.py: {exc}", file=sys.stderr)
        return 2
    if result.returncode not in (0, 1):  # 1 = target not met, still valid output
        print(
            f"[check] compute-loss-bundle.py failed (exit {result.returncode}):\n"
            f"{result.stderr}",
            file=sys.stderr,
        )
        return 2
    try:
        aggregate = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        print(f"[check] compute script output not JSON: {exc}", file=sys.stderr)
        return 2
    truth = f"{aggregate['bundle_mean']:.3f}"

    # 2. Walk citation sites.
    mismatches: list[str] = []
    uncited: list[str] = []
    cited: list[tuple[str, int]] = []
    for rel, extractor in SITES:
        path = REPO / rel
        if not path.exists():
            uncited.append(f"  {rel} — file missing")
            continue
        values = extractor(path.read_text(errors="replace"))
        if not values:
            uncited.append(f"  {rel} — no Δloss_bundle value cited")
            continue
        cited.append((rel, len(values)))
        bad = [v for v in values if v != truth]
        if bad:
            mismatches.append(
                f"  {rel} — cites {sorted(set(values))}, expected {truth}"
            )

    # 3. Report.
    if mismatches:
        print(
            f"[check] Δloss_bundle doc drift — computed {truth}, but:\n"
            + "\n".join(mismatches)
            + "\n\nFix by (a) editing the listed files to cite "
              f"{truth}, OR (b) re-running the measurement pass and updating "
              "the manifest if the fixtures have changed. "
              "See CLAUDE.md § 'Δloss_bundle — update policy'.",
            file=sys.stderr,
        )
        return 1

    ok_msg = [
        f"[check] Δloss_bundle = {truth} — all {len(cited)} citation sites match."
    ]
    for rel, n in cited:
        ok_msg.append(f"  {rel}  ×{n} citation(s)")
    if uncited:
        ok_msg.append("  (non-fatal) sites that do not cite the value:")
        ok_msg.extend(uncited)
    print("\n".join(ok_msg))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
