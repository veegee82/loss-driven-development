#!/usr/bin/env python3
"""Compute Δloss_bundle from the canonical fixture runs.

**What is Δloss_bundle?** See `README.md § What Δloss_bundle means` for the
user-facing explanation, `evaluation.md § Loss (bundle-wide)` for the formal
definition, and `CLAUDE.md § Δloss_bundle — update policy` for the
maintainer workflow this script plugs into.

**Short form.** For each measured skill:

    Δloss_normalized(skill) = (RED_violations - GREEN_violations) / rubric_max

Bundle aggregate — the arithmetic mean across the N skills listed in the
manifest:

    Δloss_bundle = (1/N) · Σ_skill Δloss_normalized(skill)

**Inputs.**
  * `tests/fixtures/loss-bundle-manifest.json` — which skills count, which
    run directory is canonical per skill, and optional overrides for skills
    whose score is carried in a distribution-summary instead of a plain
    score.md (currently only `root-cause-by-layer`).
  * `tests/fixtures/<skill>/runs/<canonical_run>/score.md` — the
    human-authored rubric score for that run. Parsed for the RED/GREEN
    violation counts and the rubric max.

**Outputs.**
  * Human table on stdout (per-skill + bundle mean + target verdict).
  * Optional `--json` prints a machine-readable summary the `check` script
    consumes.
  * Optional `--write <path>` persists the JSON to disk — the default path
    is `tests/fixtures/aggregate.json` and is the drift-detection baseline
    the pre-commit hook compares against.

**Exit codes.**
  * 0 — bundle computed, target met (>= manifest.target_normalized).
  * 1 — bundle computed, target NOT met.
  * 2 — parse / manifest error.

This script has NO runtime dependencies beyond the Python standard library
and is safe to run on every commit.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


REPO = Path(__file__).resolve().parent.parent
MANIFEST = REPO / "tests" / "fixtures" / "loss-bundle-manifest.json"
DEFAULT_AGGREGATE_OUT = REPO / "tests" / "fixtures" / "aggregate.json"


# Score.md parser — two accepted patterns (both observed in-repo).
# Pattern A (multi-line boldface block):
#   **Baseline violations (RED):   5 / 6**
#   **With-skill violations (GREEN): 0 / 6**
#   **Δloss = 5 − 0 = +5**
# Pattern B (single inline line):
#   **RED: 3 / 6**   **GREEN: 0 / 6**   **Δloss = +3**
_RED_MULTI = re.compile(
    r"\*\*Baseline violations \(RED\):\s*(\d+)\s*/\s*(\d+)\*\*",
    re.IGNORECASE,
)
_GREEN_MULTI = re.compile(
    r"\*\*With-skill violations \(GREEN\):\s*(\d+)\s*/\s*\d+\*\*",
    re.IGNORECASE,
)
_RED_INLINE = re.compile(
    r"\*\*RED:\s*(\d+)\s*/\s*(\d+)\*\*",
    re.IGNORECASE,
)
_GREEN_INLINE = re.compile(
    r"\*\*GREEN:\s*(\d+)\s*/\s*\d+\*\*",
    re.IGNORECASE,
)


@dataclass
class Measurement:
    skill: str
    red: int
    green: int
    rubric_max: int
    source: Path
    status: str

    @property
    def delta_normalized(self) -> float:
        if self.rubric_max == 0:
            return 0.0
        return (self.red - self.green) / self.rubric_max

    def raw(self) -> str:
        return f"{self.red}/{self.rubric_max}"


def _parse_score_md(path: Path) -> tuple[int, int, int] | None:
    """Extract (RED, GREEN, rubric_max) from a score.md — None if not found."""
    text = path.read_text(errors="replace")
    red: Optional[tuple[int, int]] = None
    green: Optional[int] = None
    for m in _RED_MULTI.finditer(text):
        red = (int(m.group(1)), int(m.group(2)))
        break
    if red is None:
        for m in _RED_INLINE.finditer(text):
            red = (int(m.group(1)), int(m.group(2)))
            break
    for m in _GREEN_MULTI.finditer(text):
        green = int(m.group(1))
        break
    if green is None:
        for m in _GREEN_INLINE.finditer(text):
            green = int(m.group(1))
            break
    if red is None or green is None:
        return None
    return red[0], green, red[1]


def load_manifest(path: Path) -> dict:
    if not path.exists():
        raise SystemExit(f"manifest not found: {path}")
    return json.loads(path.read_text())


def measure(manifest: dict, repo: Path) -> list[Measurement]:
    out: list[Measurement] = []
    for entry in manifest["skills"]:
        skill = entry["name"]
        run_rel = Path(entry["canonical_run"])
        run_dir = repo / "tests" / "fixtures" / skill / run_rel
        score_path = run_dir / "score.md"
        # Prefer explicit overrides on the manifest entry. This is how
        # distribution-only fixtures (root-cause-by-layer) expose a
        # canonical point value.
        red = entry.get("red")
        green = entry.get("green")
        rubric_max = entry.get("rubric_max")
        if red is None or green is None or rubric_max is None:
            if not score_path.exists():
                raise SystemExit(
                    f"[{skill}] no score.md at {score_path} and no override "
                    f"on manifest entry. Fix the manifest or commit a score.md."
                )
            parsed = _parse_score_md(score_path)
            if parsed is None:
                raise SystemExit(
                    f"[{skill}] could not parse RED/GREEN from {score_path}. "
                    f"Add an explicit override on the manifest entry."
                )
            red_p, green_p, max_p = parsed
            red = red if red is not None else red_p
            green = green if green is not None else green_p
            rubric_max = rubric_max if rubric_max is not None else max_p
        out.append(
            Measurement(
                skill=skill,
                red=int(red),
                green=int(green),
                rubric_max=int(rubric_max),
                source=score_path if score_path.exists() else run_dir,
                status=entry.get("status", ""),
            )
        )
    return out


def bundle_mean(measurements: list[Measurement]) -> float:
    if not measurements:
        return 0.0
    return sum(m.delta_normalized for m in measurements) / len(measurements)


def render_table(measurements: list[Measurement], bundle: float, target: float) -> str:
    lines: list[str] = []
    lines.append(
        f"{'skill':<32}  {'Δloss_norm':>11}  {'raw':>6}  {'rubric':>6}  status"
    )
    lines.append("-" * 88)
    for m in measurements:
        lines.append(
            f"{m.skill:<32}  {m.delta_normalized:>11.3f}  "
            f"{m.raw():>6}  {m.rubric_max:>6}  {m.status}"
        )
    lines.append("-" * 88)
    verdict = "met with margin" if bundle >= target else "NOT MET"
    lines.append(
        f"{'Bundle mean (n=' + str(len(measurements)) + ')':<32}  "
        f"{bundle:>11.3f}  "
        f"target {target:.3f} — {verdict}"
    )
    return "\n".join(lines)


def build_aggregate_doc(
    measurements: list[Measurement], bundle: float, manifest: dict
) -> dict:
    return {
        "schema": 1,
        "measured_at": manifest.get("measured_at", ""),
        "target_normalized": manifest.get("target_normalized", 0.30),
        "bundle_mean": round(bundle, 3),
        "n_skills": len(measurements),
        "target_met": bundle >= manifest.get("target_normalized", 0.30),
        "per_skill": [
            {
                "name": m.skill,
                "delta_normalized": round(m.delta_normalized, 3),
                "red": m.red,
                "green": m.green,
                "rubric_max": m.rubric_max,
                "status": m.status,
            }
            for m in measurements
        ],
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument(
        "--manifest",
        default=str(MANIFEST),
        help=f"Path to manifest JSON (default: {MANIFEST.relative_to(REPO)})",
    )
    ap.add_argument(
        "--json",
        action="store_true",
        help="Emit the machine-readable aggregate instead of the human table",
    )
    ap.add_argument(
        "--write",
        nargs="?",
        const=str(DEFAULT_AGGREGATE_OUT),
        default=None,
        help=(
            "Persist the aggregate JSON — with no arg, writes to "
            f"{DEFAULT_AGGREGATE_OUT.relative_to(REPO)}; pass a path to "
            "override."
        ),
    )
    ns = ap.parse_args(argv)

    manifest = load_manifest(Path(ns.manifest))
    measurements = measure(manifest, REPO)
    bundle = bundle_mean(measurements)
    target = manifest.get("target_normalized", 0.30)

    aggregate = build_aggregate_doc(measurements, bundle, manifest)

    if ns.write:
        Path(ns.write).write_text(json.dumps(aggregate, indent=2) + "\n")
        print(f"[wrote] {ns.write}", file=sys.stderr)

    if ns.json:
        print(json.dumps(aggregate, indent=2))
    else:
        print(render_table(measurements, bundle, target))

    return 0 if bundle >= target else 1


if __name__ == "__main__":
    raise SystemExit(main())
