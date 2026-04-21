"""Project-memory aggregator — v0.5.2.

Reads `.ldd/trace.log` and produces `.ldd/project_memory.json` — a
deterministic, machine-computed projection suitable for navigation hints
(skill suggestion, plateau detection, wrong-decision detection).

**Non-negotiable design principle: the memory does NOT bias the loss.**

Per-metric bias-guards applied here:
  - Survivorship guard: every aggregate counts ALL terminal states
    (complete / partial / failed / aborted). Skills are broken out BY
    terminal so the caller can't silently privilege "complete" data.
  - Regression-to-mean guard: skill Δloss is reported BOTH as absolute
    and relative (Δ / prev_loss). A skill that fires on hard bugs will
    have higher absolute Δ but equivalent relative Δ.
  - Recency-drift guard: both lifetime and last-30-day windows are
    emitted; the caller sees the ratio and can detect skill-drift.
  - Confirmation-bias guard: aggregation is purely deterministic on
    the raw trace. The agent never curates "which entries to include."

See `skills/using-ldd/SKILL.md` § RED FLAGS for the full doctrine.
"""
from __future__ import annotations

import datetime as _dt
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from ldd_trace.store import TaskSlice, TraceStore


SCHEMA_VERSION = 1
MEMORY_FILE_NAME = "project_memory.json"
RECENT_WINDOW_DAYS = 30
PLATEAU_THRESHOLD = 0.005
REGRESSION_THRESHOLD = 0.005


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class SkillStats:
    name: str
    n_invocations: int = 0
    sum_delta_abs: float = 0.0
    sum_delta_rel: float = 0.0
    n_with_prev_loss_nonzero: int = 0
    n_regressions: int = 0
    n_plateaus: int = 0
    by_terminal: Dict[str, Dict[str, float]] = field(default_factory=dict)

    def record(
        self,
        delta: Optional[float],
        prev_loss: Optional[float],
        terminal: Optional[str],
    ) -> None:
        self.n_invocations += 1
        if delta is None:
            return
        self.sum_delta_abs += delta
        if prev_loss is not None and prev_loss > 0:
            self.sum_delta_rel += delta / prev_loss
            self.n_with_prev_loss_nonzero += 1
        if delta > REGRESSION_THRESHOLD:
            self.n_regressions += 1
        elif abs(delta) <= PLATEAU_THRESHOLD:
            self.n_plateaus += 1
        if terminal is not None:
            bucket = self.by_terminal.setdefault(
                terminal, {"n": 0, "sum_delta_abs": 0.0}
            )
            bucket["n"] = bucket["n"] + 1
            bucket["sum_delta_abs"] = bucket["sum_delta_abs"] + delta

    def to_json(self) -> dict:
        delta_mean_abs = (
            self.sum_delta_abs / self.n_invocations if self.n_invocations else 0.0
        )
        delta_mean_rel = (
            self.sum_delta_rel / self.n_with_prev_loss_nonzero
            if self.n_with_prev_loss_nonzero
            else 0.0
        )
        # NB: regression/plateau rates use n_invocations as denominator so that
        # the baseline iteration (no delta) shows as neither regression nor
        # plateau — that's honest, not suppression.
        by_term_out = {}
        for term, b in self.by_terminal.items():
            b_delta_mean = b["sum_delta_abs"] / b["n"] if b["n"] else 0.0
            by_term_out[term] = {"n": int(b["n"]), "delta_mean_abs": round(b_delta_mean, 4)}
        return {
            "n_invocations": self.n_invocations,
            "delta_mean_abs": round(delta_mean_abs, 4),
            "delta_mean_relative": round(delta_mean_rel, 4),
            "regression_rate": round(
                self.n_regressions / self.n_invocations if self.n_invocations else 0.0, 4
            ),
            "plateau_rate": round(
                self.n_plateaus / self.n_invocations if self.n_invocations else 0.0, 4
            ),
            "by_terminal": by_term_out,
        }


# ---------------------------------------------------------------------------
# Aggregator
# ---------------------------------------------------------------------------


def _parse_timestamp(ts: str) -> Optional[_dt.datetime]:
    try:
        # Strip the trailing "Z" and parse as UTC
        return _dt.datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except ValueError:
        return None


def _task_in_window(task: TaskSlice, cutoff: _dt.datetime) -> bool:
    if not task.meta:
        return False
    ts = _parse_timestamp(task.meta.timestamp)
    return ts is not None and ts >= cutoff


def _iteration_deltas(task: TaskSlice) -> List[Tuple[int, float, float, str]]:
    """Yield (absolute index within task, delta, prev_loss, skill) tuples.

    Baselines are included but delta=None semantically; we represent that as
    prev_loss=None. Returns only non-baseline iterations for delta computation.
    """
    out: List[Tuple[int, float, float, str]] = []
    # Group by loop so we compute delta within-loop
    by_loop: Dict[str, List] = {}
    for e in task.iterations:
        by_loop.setdefault(e.loop, []).append(e)
    for loop, entries in by_loop.items():
        prev_loss: Optional[float] = None
        for e in entries:
            cur = e.get_float("loss_norm", 0.0)
            skill = e.fields.get("skill", "(unknown)")
            if e.fields.get("baseline") == "true":
                prev_loss = cur
                continue
            if prev_loss is None:
                # iteration without a preceding baseline: can't compute delta
                prev_loss = cur
                continue
            delta = cur - prev_loss
            out.append((len(out), delta, prev_loss, skill))
            prev_loss = cur
    return out


def _skill_on_iteration(entry) -> str:
    return entry.fields.get("skill", "(unknown)")


def aggregate(store: TraceStore) -> dict:
    """Compute project_memory.json content from the current trace.log.

    Pure function: does not write. Call `write_memory()` to persist.
    """
    completed = store.completed_tasks()
    all_tasks = store.segment_tasks()
    now = _dt.datetime.now(_dt.timezone.utc)
    cutoff = now - _dt.timedelta(days=RECENT_WINDOW_DAYS)

    # ------------------------------------------------------------------
    # Window stats — lifetime + recent
    # ------------------------------------------------------------------
    def _window_stats(tasks: List[TaskSlice]) -> Dict:
        return {
            "n_completed_tasks": sum(1 for t in tasks if t.is_closed),
            "n_in_progress_tasks": sum(1 for t in tasks if not t.is_closed),
            "n_iterations": sum(len(t.iterations) for t in tasks),
        }

    lifetime_stats = _window_stats(all_tasks)
    recent_tasks = [t for t in all_tasks if _task_in_window(t, cutoff)]
    recent_stats = _window_stats(recent_tasks)

    # ------------------------------------------------------------------
    # Terminal distribution (no survivorship filter — include ALL)
    # ------------------------------------------------------------------
    terminal_counts: Dict[str, int] = {}
    for t in completed:
        term = t.terminal or "(unknown)"
        terminal_counts[term] = terminal_counts.get(term, 0) + 1
    total_completed = sum(terminal_counts.values())
    terminal_distribution = {
        term: {
            "count": n,
            "rate": round(n / total_completed, 4) if total_completed else 0.0,
        }
        for term, n in sorted(terminal_counts.items())
    }

    # ------------------------------------------------------------------
    # Task shape — mean_k, p95_k, broken out by terminal
    # ------------------------------------------------------------------
    def _shape(tasks: List[TaskSlice]) -> Dict:
        ks = [t.k_count for t in tasks]
        if not ks:
            return {"mean_k": 0.0, "median_k": 0, "p95_k": 0, "n": 0}
        ks_sorted = sorted(ks)
        n = len(ks_sorted)
        p95_idx = min(n - 1, int(round(n * 0.95)) - 1) if n >= 2 else n - 1
        return {
            "mean_k": round(sum(ks_sorted) / n, 2),
            "median_k": ks_sorted[n // 2],
            "p95_k": ks_sorted[max(0, p95_idx)],
            "n": n,
        }

    task_shape = _shape(completed)
    task_shape_by_terminal = {
        term: _shape([t for t in completed if t.terminal == term])
        for term in terminal_counts
    }

    # ------------------------------------------------------------------
    # Skill effectiveness — per skill, per iteration delta.
    # Both absolute and relative deltas computed. All terminal states.
    # ------------------------------------------------------------------
    skill_stats: Dict[str, SkillStats] = {}
    for t in completed:
        terminal = t.terminal
        for _, delta, prev, skill in _iteration_deltas(t):
            s = skill_stats.setdefault(skill, SkillStats(name=skill))
            s.record(delta=delta, prev_loss=prev, terminal=terminal)
    skill_effectiveness = {
        name: s.to_json() for name, s in sorted(skill_stats.items())
    }

    # ------------------------------------------------------------------
    # Plateau resolution patterns — what skills fire AFTER n consecutive
    # plateau iterations, and do those sub-paths close?
    # ------------------------------------------------------------------
    plateau_resolutions: Dict[str, Dict] = {}
    for t in completed:
        plateau_streak = 0
        for i, (_, delta, _prev, skill) in enumerate(_iteration_deltas(t)):
            if abs(delta) <= PLATEAU_THRESHOLD:
                plateau_streak += 1
            else:
                if plateau_streak >= 2:
                    # This `skill` is what broke out of the plateau
                    bucket_key = f"after_{plateau_streak}_consecutive_plateaus"
                    bucket = plateau_resolutions.setdefault(
                        bucket_key,
                        {"n_observed": 0, "resolver_skills": {}, "delta_when_resolved": []},
                    )
                    bucket["n_observed"] += 1
                    bucket["resolver_skills"][skill] = (
                        bucket["resolver_skills"].get(skill, 0) + 1
                    )
                    bucket["delta_when_resolved"].append(round(delta, 4))
                plateau_streak = 0

    # ------------------------------------------------------------------
    # Common closing paths (happy path) and failure paths (non-complete)
    # ------------------------------------------------------------------
    def _skill_path(task: TaskSlice) -> Tuple[str, ...]:
        return tuple(
            _skill_on_iteration(e)
            for e in task.iterations
            if e.fields.get("baseline") != "true"
        )

    closing_paths_count: Dict[Tuple[str, ...], int] = {}
    failure_paths_count: Dict[Tuple[str, ...], int] = {}
    for t in completed:
        path = _skill_path(t)
        if t.terminal == "complete":
            closing_paths_count[path] = closing_paths_count.get(path, 0) + 1
        else:
            failure_paths_count[path] = failure_paths_count.get(path, 0) + 1

    top_closing = sorted(closing_paths_count.items(), key=lambda x: -x[1])[:5]
    top_failure = sorted(failure_paths_count.items(), key=lambda x: -x[1])[:5]

    # ------------------------------------------------------------------
    # Calibration — v0.7.0. Mean |prediction_error| over all iterations
    # that carried a predicted_Δloss field. Guards against silent drift
    # between predicted and observed loss movement.
    # ------------------------------------------------------------------
    prediction_errors: List[float] = []
    predictions_by_skill: Dict[str, List[float]] = {}
    for t in completed:
        for e in t.iterations:
            err_str = e.fields.get("prediction_error")
            if err_str is None:
                continue
            try:
                # err format: "±N.NNN" or "+N.NNN" / "-N.NNN"
                err_clean = err_str.replace("±", "").replace("+", "")
                err_val = float(err_clean)
                prediction_errors.append(abs(err_val))
                skill = e.fields.get("skill", "(unknown)")
                predictions_by_skill.setdefault(skill, []).append(abs(err_val))
            except ValueError:
                continue

    calibration = {
        "n_predictions": len(prediction_errors),
        "mean_abs_error": (
            round(sum(prediction_errors) / len(prediction_errors), 4)
            if prediction_errors
            else None
        ),
        "by_skill": {
            s: {
                "n": len(errs),
                "mean_abs_error": round(sum(errs) / len(errs), 4),
            }
            for s, errs in predictions_by_skill.items()
        },
        "drift_warning": (
            len(prediction_errors) >= 5
            and sum(prediction_errors) / len(prediction_errors) > 0.15
        ),
    }

    # ------------------------------------------------------------------
    # Assemble memory
    # ------------------------------------------------------------------
    memory = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "bias_guards": {
            "survivorship": "all terminal states counted; skill stats broken out by terminal",
            "regression_to_mean": "delta_mean reported both absolute AND relative (Δ/prev_loss)",
            "recency_drift": f"lifetime + last-{RECENT_WINDOW_DAYS}-days windows both shown",
            "confirmation": "deterministic aggregation on raw trace; no agent curation",
        },
        "window": {
            "lifetime": lifetime_stats,
            f"last_{RECENT_WINDOW_DAYS}_days": recent_stats,
        },
        "terminal_distribution": terminal_distribution,
        "task_shape": {
            "overall": task_shape,
            "by_terminal": task_shape_by_terminal,
        },
        "skill_effectiveness": skill_effectiveness,
        "plateau_resolution_patterns": plateau_resolutions,
        "calibration": calibration,
        "common_closing_paths": [
            {"path": list(p), "count": c} for p, c in top_closing
        ],
        "common_failure_paths": [
            {"path": list(p), "count": c} for p, c in top_failure
        ],
    }
    return memory


def write_memory(store: TraceStore, memory: dict) -> Path:
    """Write memory to `.ldd/project_memory.json`."""
    store.ensure_dir()
    out_path = store.trace_dir / MEMORY_FILE_NAME
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(memory, f, indent=2, sort_keys=False)
        f.write("\n")
    return out_path


def aggregate_and_write(store: TraceStore) -> Path:
    return write_memory(store, aggregate(store))


def read_memory(store: TraceStore) -> Optional[dict]:
    mem_path = store.trace_dir / MEMORY_FILE_NAME
    if not mem_path.exists():
        return None
    with mem_path.open("r", encoding="utf-8") as f:
        return json.load(f)
