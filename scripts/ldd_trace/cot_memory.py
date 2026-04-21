"""Chain-memory store + aggregator for dialectical-CoT.

Persistence layer specific to CoT chains:

    .ldd/cot_traces.jsonl   — append-only, one JSON-per-line, one chain per entry
    .ldd/cot_memory.json    — aggregate: per-task-type step effectiveness, common
                              failure modes, calibration MAE, drift_warning

The store reuses `TraceStore` for the project root / `.ldd/` directory lookup
but the files and aggregation are independent from the inner-loop trace.log.

Bias-invariance is preserved by the same rules as v0.5.2 aggregator:
  - All terminal states counted (complete/partial/failed/aborted)
  - Per-task-type partitioning (no cross-task-type signal mixing)
  - Both absolute and relative metrics reported
  - Calibration separated from correctness
"""
from __future__ import annotations

import datetime as _dt
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from ldd_trace.cot import Antithesis, CoTChain
    from ldd_trace.store import TraceStore


COT_TRACES_FILE = "cot_traces.jsonl"
COT_MEMORY_FILE = "cot_memory.json"
COT_MEMORY_SCHEMA_VERSION = 1

# Threshold above which calibration MAE is flagged as drifting
COT_DRIFT_MAE_THRESHOLD = 0.15
COT_DRIFT_MIN_N = 5


# ---------------------------------------------------------------------------
# Persistence — append chain, read traces
# ---------------------------------------------------------------------------


def _traces_path(store: "TraceStore") -> Path:
    return store.trace_dir / COT_TRACES_FILE


def _memory_path(store: "TraceStore") -> Path:
    return store.trace_dir / COT_MEMORY_FILE


def append_chain_trace(store: "TraceStore", chain: "CoTChain") -> Path:
    store.ensure_dir()
    path = _traces_path(store)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(chain.to_dict(), sort_keys=False) + "\n")
    return path


def read_chain_traces(store: "TraceStore") -> List[dict]:
    path = _traces_path(store)
    if not path.exists():
        return []
    out: List[dict] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return out


def read_cot_memory(store: "TraceStore") -> Optional[dict]:
    path = _memory_path(store)
    if not path.exists():
        return None
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# Aggregator — per-task-type statistics
# ---------------------------------------------------------------------------


def update_cot_memory(store: "TraceStore") -> Path:
    """Re-aggregate from `.ldd/cot_traces.jsonl` into `.ldd/cot_memory.json`.

    Intended to be called after each chain closes (auto by CoTRunner); cheap
    for hundreds of chains because JSON parsing is the bottleneck, not stats.
    """
    traces = read_chain_traces(store)
    memory = _aggregate(traces)
    path = _memory_path(store)
    store.ensure_dir()
    with path.open("w", encoding="utf-8") as f:
        json.dump(memory, f, indent=2, sort_keys=False)
        f.write("\n")
    return path


def _aggregate(traces: List[dict]) -> dict:
    now = _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    if not traces:
        return {
            "schema_version": COT_MEMORY_SCHEMA_VERSION,
            "generated_at": now,
            "n_chains": 0,
            "by_task_type": {},
            "bias_guards": _bias_guards_block(),
        }

    by_type: Dict[str, dict] = {}
    for tr in traces:
        t_type = tr.get("task_type") or "general"
        bucket = by_type.setdefault(
            t_type,
            {
                "n_chains": 0,
                "terminal_distribution": {},
                "mean_chain_length": 0.0,
                "mean_backtrack_count": 0.0,
                "correct_rate": None,
                "prediction_errors": [],  # (predicted_chain_correct, actual) pairs
                "common_failure_modes": {},
                "step_decision_distribution": {},
                "total_tokens_mean": 0.0,
            },
        )
        bucket["n_chains"] += 1

        term = tr.get("terminal", "partial")
        bucket["terminal_distribution"][term] = (
            bucket["terminal_distribution"].get(term, 0) + 1
        )

        steps = tr.get("steps", [])
        bucket["mean_chain_length"] += len(steps)
        bucket["mean_backtrack_count"] += tr.get("backtrack_count", 0)
        bucket["total_tokens_mean"] += tr.get("total_tokens", 0)

        # Decision distribution
        for step in steps:
            dec = step.get("decision", "commit")
            bucket["step_decision_distribution"][dec] = (
                bucket["step_decision_distribution"].get(dec, 0) + 1
            )
            # Failure-mode harvesting: for steps with decision=revise or reject,
            # the antitheses that "won" are the failure modes. Count by content.
            if dec in ("revise", "reject"):
                for a in step.get("antitheses", []):
                    if a.get("impact", 0) < -0.05:
                        content = a.get("content", "")[:80]
                        bucket["common_failure_modes"][content] = (
                            bucket["common_failure_modes"].get(content, 0) + 1
                        )

        # Calibration: predicted vs actual
        predicted = tr.get("predicted_chain_correct")
        actual = tr.get("actual_correct")
        if predicted is not None and actual is not None:
            actual_float = 1.0 if actual else 0.0
            bucket["prediction_errors"].append(
                {"predicted": predicted, "actual": actual_float}
            )

    # Finalize means + calibration
    out_by_type: Dict[str, dict] = {}
    for t_type, b in by_type.items():
        n = b["n_chains"]
        mean_length = b["mean_chain_length"] / n if n else 0
        mean_backtracks = b["mean_backtrack_count"] / n if n else 0
        tokens_mean = b["total_tokens_mean"] / n if n else 0

        # Correct rate (only for chains where actual_correct is known)
        known = [e for e in b["prediction_errors"] if e["actual"] in (0.0, 1.0)]
        correct_rate = (
            round(sum(e["actual"] for e in known) / len(known), 4)
            if known
            else None
        )

        # Calibration MAE
        errs = [abs(e["predicted"] - e["actual"]) for e in b["prediction_errors"]]
        mae = round(sum(errs) / len(errs), 4) if errs else None
        drift_warning = (
            mae is not None
            and len(errs) >= COT_DRIFT_MIN_N
            and mae > COT_DRIFT_MAE_THRESHOLD
        )

        # Terminal rates
        total_term = sum(b["terminal_distribution"].values())
        term_rates = {
            term: {
                "count": n_count,
                "rate": round(n_count / total_term, 4) if total_term else 0.0,
            }
            for term, n_count in sorted(b["terminal_distribution"].items())
        }

        # Top-5 failure modes
        top_failures = sorted(
            b["common_failure_modes"].items(), key=lambda x: -x[1]
        )[:5]

        # Step decisions
        total_decisions = sum(b["step_decision_distribution"].values())
        dec_rates = {
            dec: {
                "count": n_count,
                "rate": round(n_count / total_decisions, 4) if total_decisions else 0.0,
            }
            for dec, n_count in sorted(b["step_decision_distribution"].items())
        }

        out_by_type[t_type] = {
            "n_chains": n,
            "terminal_distribution": term_rates,
            "mean_chain_length": round(mean_length, 2),
            "mean_backtrack_count": round(mean_backtracks, 2),
            "mean_total_tokens": round(tokens_mean, 1),
            "correct_rate": correct_rate,
            "calibration": {
                "n_predictions": len(errs),
                "mae": mae,
                "drift_warning": drift_warning,
            },
            "common_failure_modes": [
                {"pattern": p, "count": c} for p, c in top_failures
            ],
            "step_decision_distribution": dec_rates,
        }

    return {
        "schema_version": COT_MEMORY_SCHEMA_VERSION,
        "generated_at": now,
        "n_chains": len(traces),
        "by_task_type": out_by_type,
        "bias_guards": _bias_guards_block(),
    }


def _bias_guards_block() -> dict:
    return {
        "survivorship": "all terminal states counted; per-terminal breakdown exposed",
        "cross_task_type_mixing": "per-task-type partitioning enforced; no signal mixing",
        "calibration_vs_correctness": "calibration MAE separated from correct_rate; both reported",
        "no_loss_modification": "memory never modifies ground-truth verification (L(θ))",
    }


# ---------------------------------------------------------------------------
# Primer generation for the CoT runner
# ---------------------------------------------------------------------------


def cot_primers_for_task_type(
    store: "TraceStore",
    task_type: str,
    max_primers: int = 3,
) -> List["Antithesis"]:
    """Generate antithesis primers from CoT memory for a given task-type.

    Pulls two categories:
      - common_failure_modes → one primer per top failure (up to N)
      - calibration drift → one primer if drift_warning is active (predictions
        are over-confident in this task type)
    """
    from ldd_trace.cot import Antithesis

    memory = read_cot_memory(store)
    if memory is None:
        return []
    bucket = memory.get("by_task_type", {}).get(task_type)
    if bucket is None:
        return []

    primers: List[Antithesis] = []

    # Failure-mode primers
    for fm in bucket.get("common_failure_modes", [])[:max_primers]:
        primers.append(
            Antithesis(
                source="primer",
                content=(
                    f"Historical failure mode in {task_type} chains "
                    f"(seen {fm['count']} times): {fm['pattern']}"
                ),
                prob_applies=0.3,
                impact=-0.25,
                provenance=f"cot_memory[{task_type}]/common_failure_modes",
            )
        )

    # Calibration-drift primer
    calib = bucket.get("calibration", {})
    if calib.get("drift_warning"):
        primers.append(
            Antithesis(
                source="primer",
                content=(
                    f"Calibration drift in {task_type} chains: "
                    f"MAE={calib.get('mae')} (n={calib.get('n_predictions')}). "
                    f"Your confidence estimates for this task type are unreliable; "
                    f"treat thesis_prior with skepticism."
                ),
                prob_applies=0.5,
                impact=-0.10,
                provenance=f"cot_memory[{task_type}]/calibration_drift",
            )
        )

    return primers


# ---------------------------------------------------------------------------
# Human-readable health report
# ---------------------------------------------------------------------------


def format_cot_health(memory: dict) -> str:
    lines: List[str] = []
    lines.append("╭─ LDD CoT health (dialectical chain-of-thought) ──────────────────╮")
    lines.append(f"│ Chains observed  : {memory.get('n_chains', 0)}")
    by_type = memory.get("by_task_type", {})
    if not by_type:
        lines.append("│ (no chains recorded yet — run `ldd_trace cot run --task ...`)")
    else:
        for t_type, b in sorted(by_type.items()):
            lines.append("│")
            lines.append(f"│ ── task_type: {t_type}  (n={b['n_chains']} chains) ──")
            lines.append(
                f"│     mean_chain_length = {b['mean_chain_length']}  "
                f"mean_backtracks = {b['mean_backtrack_count']}  "
                f"mean_tokens = {b['mean_total_tokens']}"
            )
            term = b.get("terminal_distribution", {})
            if term:
                parts = [f"{k}={v['count']}({v['rate']:.0%})" for k, v in term.items()]
                lines.append(f"│     terminals          : {' · '.join(parts)}")
            if b.get("correct_rate") is not None:
                lines.append(f"│     correct_rate       : {b['correct_rate']:.1%}")
            calib = b.get("calibration", {})
            if calib.get("n_predictions", 0) > 0:
                marker = "⚠ drift" if calib.get("drift_warning") else "ok"
                mae = calib.get("mae")
                lines.append(
                    f"│     calibration        : n={calib['n_predictions']} "
                    f"MAE={mae:.3f} [{marker}]"
                )
            failures = b.get("common_failure_modes", [])
            if failures:
                lines.append("│     top failure modes  :")
                for fm in failures[:3]:
                    content = fm["pattern"][:60]
                    lines.append(f"│       × {fm['count']:>2}  {content}")
    lines.append("╰──────────────────────────────────────────────────────────────────╯")
    return "\n".join(lines)
