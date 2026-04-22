"""Tests for the `Moving-target-loss drift` indicator in drift-scan.

Exercises three scenarios:
  * Clean task (0–1 epoch bumps, normal iteration count) — no finding.
  * Abuse pattern (3+ bumps) — finding fires.
  * Borderline pattern (2 bumps in a short task) — finding fires.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
SCAN_PATH = REPO / "scripts" / "drift-scan.py"


def _load_drift_module():
    """Import scripts/drift-scan.py despite the dash in the filename."""
    spec = importlib.util.spec_from_file_location("drift_scan", SCAN_PATH)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules["drift_scan"] = mod
    spec.loader.exec_module(mod)
    return mod


drift_scan = _load_drift_module()


def _write_trace(path: Path, entries: list[str]) -> None:
    (path / ".ldd").mkdir(parents=True, exist_ok=True)
    (path / ".ldd" / "trace.log").write_text("\n".join(entries) + "\n")


def test_clean_task_no_finding(tmp_path: Path) -> None:
    _write_trace(
        tmp_path,
        [
            '2026-04-22T00:00:00Z  meta  L2/deliberate  task="clean task"  loops=inner',
            '2026-04-22T00:00:01Z  inner  k=0  skill=baseline  action=x  loss=0.5  raw=1/2',
            '2026-04-22T00:00:02Z  inner  k=1  skill=fix  action=x  loss=0.0  raw=0/2',
            '2026-04-22T00:00:03Z  inner  close  terminal=complete',
        ],
    )
    report = drift_scan.Report()
    drift_scan.check_moving_target_loss_drift(report, tmp_path)
    assert report.findings.get("Moving-target-loss drift", []) == []


def test_three_bumps_fires(tmp_path: Path) -> None:
    _write_trace(
        tmp_path,
        [
            '2026-04-22T00:00:00Z  meta  L3/structural  task="abuse task"  loops=inner',
            '2026-04-22T00:00:01Z  inner  k=0  skill=baseline  action=x  loss=0.5  raw=1/2',
            '2026-04-22T00:00:02Z  epoch  epoch=1  reason="first shift"',
            '2026-04-22T00:00:03Z  inner  k=1  skill=fix  action=x  loss=0.5  raw=1/2  epoch=1',
            '2026-04-22T00:00:04Z  epoch  epoch=2  reason="second shift"',
            '2026-04-22T00:00:05Z  inner  k=2  skill=fix  action=x  loss=0.3  raw=1/3  epoch=2',
            '2026-04-22T00:00:06Z  epoch  epoch=3  reason="third shift"',
            '2026-04-22T00:00:07Z  inner  k=3  skill=fix  action=x  loss=0.1  raw=1/10  epoch=3',
            '2026-04-22T00:00:08Z  inner  close  terminal=complete',
        ],
    )
    report = drift_scan.Report()
    drift_scan.check_moving_target_loss_drift(report, tmp_path)
    findings = report.findings.get("Moving-target-loss drift", [])
    assert len(findings) == 1
    assert "abuse task" in findings[0].detail


def test_two_bumps_in_short_task_fires(tmp_path: Path) -> None:
    _write_trace(
        tmp_path,
        [
            '2026-04-22T00:00:00Z  meta  L3/structural  task="short and churny"  loops=inner',
            '2026-04-22T00:00:01Z  inner  k=0  skill=baseline  action=x  loss=0.5  raw=1/2',
            '2026-04-22T00:00:02Z  epoch  epoch=1  reason="first shift"',
            '2026-04-22T00:00:03Z  inner  k=1  skill=fix  action=x  loss=0.4  raw=2/5  epoch=1',
            '2026-04-22T00:00:04Z  epoch  epoch=2  reason="second shift"',
            '2026-04-22T00:00:05Z  inner  k=2  skill=fix  action=x  loss=0.0  raw=0/8  epoch=2',
            '2026-04-22T00:00:06Z  inner  close  terminal=complete',
        ],
    )
    report = drift_scan.Report()
    drift_scan.check_moving_target_loss_drift(report, tmp_path)
    findings = report.findings.get("Moving-target-loss drift", [])
    assert len(findings) == 1
    assert "short and churny" in findings[0].detail


def test_two_bumps_in_long_task_no_finding(tmp_path: Path) -> None:
    """Two bumps across many iterations is legitimate — don't cry wolf."""
    entries = [
        '2026-04-22T00:00:00Z  meta  L3/structural  task="long work"  loops=inner',
        '2026-04-22T00:00:01Z  inner  k=0  skill=baseline  action=x  loss=0.5  raw=1/2',
    ]
    for k in range(1, 7):
        entries.append(
            f'2026-04-22T00:01:0{k}Z  inner  k={k}  skill=fix  action=x  loss=0.3  raw=3/10'
        )
    entries.append('2026-04-22T00:02:00Z  epoch  epoch=1  reason="rubric expanded"')
    for k in range(7, 12):
        entries.append(
            f'2026-04-22T00:03:0{k - 7}Z  inner  k={k}  skill=fix  action=x  loss=0.1  raw=1/10  epoch=1'
        )
    entries.append('2026-04-22T00:04:00Z  epoch  epoch=2  reason="threat model change"')
    entries.append('2026-04-22T00:05:00Z  inner  k=12  skill=fix  action=x  loss=0.0  raw=0/12  epoch=2')
    entries.append('2026-04-22T00:05:01Z  inner  close  terminal=complete')
    _write_trace(tmp_path, entries)
    report = drift_scan.Report()
    drift_scan.check_moving_target_loss_drift(report, tmp_path)
    assert report.findings.get("Moving-target-loss drift", []) == []


def test_absent_trace_is_silent(tmp_path: Path) -> None:
    """No .ldd/trace.log → check silently no-ops (not every repo uses LDD)."""
    report = drift_scan.Report()
    drift_scan.check_moving_target_loss_drift(report, tmp_path)
    assert report.findings.get("Moving-target-loss drift", []) == []


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-v"]))
