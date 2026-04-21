"""Metric Registry + Calibrator — v0.9.0.

The registry is the persistent, agent-accessible catalogue of metrics defined
for a project. It enforces:

  - Name uniqueness (each metric registered exactly once)
  - Spec immutability (changes require version bump)
  - Composition-referential integrity (composed metrics must reference already-
    registered components)
  - Gaming-guard (inherited from MetricSpec.__post_init__)

The calibrator tracks (predicted, observed) pairs per metric. A metric is
`advisory_only=True` at registration; the calibrator can promote it to
`load_bearing=True` only if:

  - n_samples ≥ 5
  - MAE ≤ 0.15

This is the v0.7.0 drift-detection pattern applied to arbitrary metrics.

Persistent storage:
  .ldd/metrics.json              — specs + promotion state + component refs
  .ldd/metric_calibrations.jsonl — append-only log of (metric, pred, obs) pairs
"""
from __future__ import annotations

import datetime as _dt
import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, TYPE_CHECKING

from ldd_trace.metric import Metric, MetricSpec

if TYPE_CHECKING:
    from ldd_trace.store import TraceStore


METRICS_FILE = "metrics.json"
CALIBRATIONS_FILE = "metric_calibrations.jsonl"
REGISTRY_SCHEMA_VERSION = 1

# Calibration gate constants
class SpecExistsButCallableMissing(RuntimeError):
    """Raised by MetricRegistry.get() when the spec is on disk but the
    callable accessor wasn't re-registered this session. v0.9.1 fix for
    audit finding C3 / H5 (state API disagreement on reopen).
    """


# Calibration thresholds
CALIB_MIN_N = 5
CALIB_MAX_MAE = 0.15
# v0.9.1 P3 — tail-robustness (H2): promotion requires all three to pass
CALIB_MAX_P95_ERROR = 0.30
CALIB_MAX_WORST_ERROR = 0.50
# v0.9.1 P3 — rolling window for demotion detection (M3)
CALIB_DEMOTION_WINDOW = 10

# v0.9.1 P5 — explicit writer mode (H6)
SHARED_WRITER_MODE = "shared"
SINGLE_WRITER_MODE = "single_writer"

# v0.9.1 P3 tri-state promotion (H3) — replaces binary is_load_bearing
# (kept as-is for backward-compat; new `state` field adds resolution)
PROMOTION_LOAD_BEARING = "load_bearing"
PROMOTION_ADVISORY = "advisory"
PROMOTION_INSUFFICIENT_DATA = "insufficient_data"
PROMOTION_DRIFTING = "drifting"
PROMOTION_TAIL_RISK = "tail_risk_high"
PROMOTION_OUTLIER = "catastrophic_outlier"


def _utcnow_iso() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# ---------------------------------------------------------------------------
# CalibrationRecord — one (predicted, observed) pair
# ---------------------------------------------------------------------------


@dataclass
class CalibrationRecord:
    metric_name: str
    metric_version: int
    predicted: float
    observed: float
    timestamp: str = field(default_factory=_utcnow_iso)

    def to_dict(self) -> dict:
        return asdict(self)


# ---------------------------------------------------------------------------
# PromotionState — advisory vs load_bearing
# ---------------------------------------------------------------------------


@dataclass
class PromotionState:
    """v0.9.1 — tri-state+ promotion model with tail statistics + demotion.

    `state` is the authoritative field. `is_load_bearing` is a derived
    read-only view (backward-compat for v0.9.0 callers).
    """

    metric_name: str
    version: int
    state: str = PROMOTION_INSUFFICIENT_DATA
    promoted_at: Optional[str] = None
    demoted_at: Optional[str] = None          # v0.9.1 M3 fix (non-monotonic)
    n_calibration_samples: int = 0
    last_mae: Optional[float] = None
    last_p95_error: Optional[float] = None    # v0.9.1 H2
    last_worst_error: Optional[float] = None  # v0.9.1 H2

    @property
    def is_load_bearing(self) -> bool:
        """v0.9.0 backward-compat view — read-only. Use `state` in new code."""
        return self.state == PROMOTION_LOAD_BEARING


# ---------------------------------------------------------------------------
# MetricRegistry — catalogue of all metrics for a project
# ---------------------------------------------------------------------------


class MetricRegistry:
    """In-memory registry backed by .ldd/metrics.json.

    Registration is mutation-safe: reading from disk + writing back + updating
    the in-memory dict happens atomically at the filesystem level (whole-file
    write, not append).
    """

    def __init__(self, store: "TraceStore") -> None:
        self.store = store
        self._metrics: Dict[str, Metric] = {}
        self._specs: Dict[str, MetricSpec] = {}
        self._promotions: Dict[str, PromotionState] = {}
        self._load_specs_from_disk()

    # -- Registration ----------------------------------------------------

    def register(self, metric: Metric) -> None:
        """Register a metric. Spec is persisted to disk.

        Rejects:
          - Duplicate names (unless version incremented)
          - Composition referencing unregistered components
        """
        name = metric.spec.name
        existing = self._specs.get(name)
        if existing is not None:
            if existing.version == metric.spec.version:
                raise ValueError(
                    f"metric {name!r} already registered at version "
                    f"{existing.version}; bump version to replace"
                )
            if metric.spec.version < existing.version:
                raise ValueError(
                    f"metric {name!r} version must be > {existing.version}, "
                    f"got {metric.spec.version}"
                )
        # Composition-referential integrity
        if metric.spec.composition and metric.spec.components:
            for comp_name, _weight in metric.spec.components:
                if comp_name not in self._metrics and comp_name != name:
                    raise ValueError(
                        f"composed metric {name!r} references unregistered "
                        f"component {comp_name!r}; register components first"
                    )
        self._metrics[name] = metric
        self._specs[name] = metric.spec
        # New registration → reset promotion state to insufficient_data (v0.9.1 tri-state)
        self._promotions[name] = PromotionState(
            metric_name=name,
            version=metric.spec.version,
            state=PROMOTION_INSUFFICIENT_DATA,
        )
        self._persist()

    def get(self, name: str) -> Optional[Metric]:
        """Return the registered Metric object, or None if unknown.

        v0.9.1: if a spec exists on disk but the callable wasn't re-registered
        this session, raises SpecExistsButCallableMissing — the silent None
        of v0.9.0 was a C3-class vulnerability (list_names / specs / get could
        disagree).
        """
        spec = self._specs.get(name)
        if spec is None:
            return None
        callable_ = self._metrics.get(name)
        if callable_ is None:
            raise SpecExistsButCallableMissing(
                f"spec {name!r} is persisted (v{spec.version}) but the callable "
                "accessor was not re-registered this session. Call "
                "`reg.register(metric)` again with the same name to restore it. "
                "(See audit finding C3 / H5 for rationale.)"
            )
        return callable_

    def list_names(self) -> List[str]:
        """List all registered metric names.

        v0.9.1 fix (C3): returns specs.keys() — single-source-of-truth
        alignment. The v0.9.0 version returned _metrics.keys() which lied
        by omission after session reopen.
        """
        return sorted(self._specs.keys())

    def has_callable(self, name: str) -> bool:
        """v0.9.1: introspection helper — has the callable been registered
        this session? Use this before calling get() in post-reopen workflows.
        """
        return name in self._metrics

    def specs(self) -> Dict[str, MetricSpec]:
        return dict(self._specs)

    def promotion(self, name: str) -> Optional[PromotionState]:
        return self._promotions.get(name)

    # -- Persistence -----------------------------------------------------

    def _metrics_path(self) -> Path:
        return self.store.trace_dir / METRICS_FILE

    def _load_specs_from_disk(self) -> None:
        path = self._metrics_path()
        if not path.exists():
            return
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        for spec_dict in data.get("specs", []):
            components = spec_dict.get("components")
            spec = MetricSpec(
                name=spec_dict["name"],
                kind=spec_dict["kind"],
                unit=spec_dict["unit"],
                description=spec_dict.get("description", ""),
                version=spec_dict.get("version", 1),
                advisory_only=spec_dict.get("advisory_only", True),
                normalize_scale=spec_dict.get("normalize_scale", 1.0),
                composition=spec_dict.get("composition"),
                components=(
                    tuple((c["name"], c["weight"]) for c in components)
                    if components
                    else None
                ),
            )
            self._specs[spec.name] = spec
        for p_dict in data.get("promotions", []):
            # v0.9.1: tri-state+ state field, with backward-compat for
            # v0.9.0's is_load_bearing bool.
            state = p_dict.get("state")
            if state is None:
                state = (
                    PROMOTION_LOAD_BEARING
                    if p_dict.get("is_load_bearing", False)
                    else PROMOTION_INSUFFICIENT_DATA
                )
            ps = PromotionState(
                metric_name=p_dict["metric_name"],
                version=p_dict["version"],
                state=state,
                promoted_at=p_dict.get("promoted_at"),
                demoted_at=p_dict.get("demoted_at"),
                n_calibration_samples=p_dict.get("n_calibration_samples", 0),
                last_mae=p_dict.get("last_mae"),
                last_p95_error=p_dict.get("last_p95_error"),
                last_worst_error=p_dict.get("last_worst_error"),
            )
            self._promotions[ps.metric_name] = ps

    def _persist(self) -> None:
        self.store.ensure_dir()
        path = self._metrics_path()
        data = {
            "schema_version": REGISTRY_SCHEMA_VERSION,
            "generated_at": _utcnow_iso(),
            "specs": [s.to_dict() for s in self._specs.values()],
            "promotions": [asdict(p) for p in self._promotions.values()],
        }
        with path.open("w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, sort_keys=False)
            f.write("\n")


# ---------------------------------------------------------------------------
# Calibrator — tracks (predicted, observed) pairs; promotes on pass
# ---------------------------------------------------------------------------


class Calibrator:
    """Generic calibrator for any registered metric.

    Usage:
        cal = Calibrator(registry)
        cal.log(metric_name, predicted=0.3, observed=0.28)
        cal.log(...)
        ... after several samples ...
        cal.try_promote(metric_name)  → returns True if promotion succeeded
    """

    def __init__(
        self,
        registry: MetricRegistry,
        writer_mode: str = SINGLE_WRITER_MODE,
    ) -> None:
        """v0.9.1: `writer_mode` selects the concurrency contract.
        - "single_writer" (default): fast, caller guarantees exclusivity
        - "shared": advisory fcntl.flock wrap around each append; multiple
          concurrent processes / threads are safe.
        """
        if writer_mode not in (SINGLE_WRITER_MODE, SHARED_WRITER_MODE):
            raise ValueError(
                f"writer_mode must be {SINGLE_WRITER_MODE!r} or "
                f"{SHARED_WRITER_MODE!r}, got {writer_mode!r}"
            )
        self.registry = registry
        self.writer_mode = writer_mode
        self._records: List[CalibrationRecord] = []
        self._load_from_disk()

    # -- Log + query -----------------------------------------------------

    def log(
        self, metric_name: str, predicted: float, observed: float
    ) -> CalibrationRecord:
        spec = self.registry.specs().get(metric_name)
        if spec is None:
            raise ValueError(f"unknown metric: {metric_name!r}")
        record = CalibrationRecord(
            metric_name=metric_name,
            metric_version=spec.version,
            predicted=predicted,
            observed=observed,
        )
        self._records.append(record)
        self._append_to_disk(record)
        return record

    def records_for(self, metric_name: str) -> List[CalibrationRecord]:
        spec = self.registry.specs().get(metric_name)
        if spec is None:
            return []
        return [
            r for r in self._records
            if r.metric_name == metric_name and r.metric_version == spec.version
        ]

    def mae(self, metric_name: str) -> Optional[float]:
        recs = self.records_for(metric_name)
        if not recs:
            return None
        return sum(abs(r.predicted - r.observed) for r in recs) / len(recs)

    def n_samples(self, metric_name: str) -> int:
        return len(self.records_for(metric_name))

    # v0.9.1 — additional statistics (P3 H2 fix: MAE hides tail)
    def p95_error(self, metric_name: str) -> Optional[float]:
        """95th-percentile absolute error — tail-risk statistic."""
        recs = self.records_for(metric_name)
        if not recs:
            return None
        errors = sorted(abs(r.predicted - r.observed) for r in recs)
        idx = min(len(errors) - 1, int(len(errors) * 0.95))
        return errors[idx]

    def worst_error(self, metric_name: str) -> Optional[float]:
        """Maximum absolute error — catches single catastrophic misses."""
        recs = self.records_for(metric_name)
        if not recs:
            return None
        return max(abs(r.predicted - r.observed) for r in recs)

    def mae_window(self, metric_name: str, window: int = CALIB_DEMOTION_WINDOW) -> Optional[float]:
        """v0.9.1 — rolling-window MAE for demotion detection (M3)."""
        recs = self.records_for(metric_name)[-window:]
        if not recs:
            return None
        return sum(abs(r.predicted - r.observed) for r in recs) / len(recs)

    def evaluate_state(
        self,
        metric_name: str,
        min_n: int = CALIB_MIN_N,
        max_mae: float = CALIB_MAX_MAE,
        max_p95: float = CALIB_MAX_P95_ERROR,
        max_worst: float = CALIB_MAX_WORST_ERROR,
    ) -> str:
        """v0.9.1 P3 — multi-statistic gate (H2, H3 fix).

        Returns a tri-state+ verdict rather than a single bool:
          INSUFFICIENT_DATA  — n < min_n (H3 fix: distinct from advisory)
          CATASTROPHIC_OUTLIER — any single error > max_worst (H2 fix)
          TAIL_RISK_HIGH     — p95 error > max_p95 (H2 fix)
          DRIFTING           — mean MAE > max_mae
          LOAD_BEARING       — all gates pass
        """
        n = self.n_samples(metric_name)
        if n < min_n:
            return PROMOTION_INSUFFICIENT_DATA
        worst = self.worst_error(metric_name)
        if worst is not None and worst > max_worst:
            return PROMOTION_OUTLIER
        p95 = self.p95_error(metric_name)
        if p95 is not None and p95 > max_p95:
            return PROMOTION_TAIL_RISK
        mae = self.mae(metric_name)
        if mae is not None and mae > max_mae:
            return PROMOTION_DRIFTING
        return PROMOTION_LOAD_BEARING

    def can_promote(
        self,
        metric_name: str,
        min_n: int = CALIB_MIN_N,
        max_mae: float = CALIB_MAX_MAE,
    ) -> bool:
        """Backward-compat bool gate. New code should use evaluate_state()."""
        return (
            self.evaluate_state(metric_name, min_n=min_n, max_mae=max_mae)
            == PROMOTION_LOAD_BEARING
        )

    def try_promote(self, metric_name: str) -> bool:
        """v0.9.1 — promote / demote based on multi-statistic evaluation.

        Unlike v0.9.0's monotonic-only promotion, this method can also
        DEMOTE a previously-promoted metric if recent-window stats have
        drifted (M3 fix). Returns True iff state is currently LOAD_BEARING.
        """
        promo = self.registry.promotion(metric_name)
        if promo is None:
            raise ValueError(f"unknown metric: {metric_name!r}")

        # Update stats regardless of outcome
        promo.n_calibration_samples = self.n_samples(metric_name)
        promo.last_mae = self.mae(metric_name)
        promo.last_p95_error = self.p95_error(metric_name)
        promo.last_worst_error = self.worst_error(metric_name)

        # Evaluate current state; also consider rolling-window for demotion
        new_state = self.evaluate_state(metric_name)

        # v0.9.1 M3 fix — demotion on window drift
        if (
            promo.state == PROMOTION_LOAD_BEARING
            and new_state != PROMOTION_LOAD_BEARING
        ):
            # Recent window confirms drift; demote.
            window_mae = self.mae_window(metric_name)
            if window_mae is not None and window_mae > CALIB_MAX_MAE:
                promo.state = PROMOTION_DRIFTING
                promo.demoted_at = _utcnow_iso()
                self.registry._persist()
                return False
            # else: tolerate transient fluctuation, stay load-bearing
            self.registry._persist()
            return True

        # Promotion
        if new_state == PROMOTION_LOAD_BEARING and promo.state != PROMOTION_LOAD_BEARING:
            promo.state = PROMOTION_LOAD_BEARING
            promo.promoted_at = _utcnow_iso()
            self.registry._persist()
            return True

        # State change without crossing load-bearing boundary
        promo.state = new_state
        self.registry._persist()
        return new_state == PROMOTION_LOAD_BEARING

    # -- Persistence -----------------------------------------------------

    def _calibrations_path(self) -> Path:
        return self.registry.store.trace_dir / CALIBRATIONS_FILE

    def _load_from_disk(self) -> None:
        path = self._calibrations_path()
        if not path.exists():
            return
        with path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    d = json.loads(line)
                    self._records.append(
                        CalibrationRecord(
                            metric_name=d["metric_name"],
                            metric_version=d["metric_version"],
                            predicted=d["predicted"],
                            observed=d["observed"],
                            timestamp=d.get("timestamp", ""),
                        )
                    )
                except (json.JSONDecodeError, KeyError):
                    continue

    def _append_to_disk(self, record: CalibrationRecord) -> None:
        """v0.9.1 P5 — atomic append with optional advisory lock (H6 fix).

        Default is `single_writer` mode (fast path). If `writer_mode="shared"`
        is set on the Calibrator, we wrap the append in an fcntl.flock so
        multiple concurrent processes can safely append.
        """
        self.registry.store.ensure_dir()
        path = self._calibrations_path()
        payload = json.dumps(record.to_dict()) + "\n"
        if self.writer_mode == SHARED_WRITER_MODE:
            # Advisory exclusive lock; waits until the previous writer releases
            try:
                import fcntl  # POSIX only
            except ImportError:
                fcntl = None
            with path.open("a", encoding="utf-8") as f:
                if fcntl is not None:
                    fcntl.flock(f.fileno(), fcntl.LOCK_EX)
                    try:
                        f.write(payload)
                        f.flush()
                    finally:
                        fcntl.flock(f.fileno(), fcntl.LOCK_UN)
                else:
                    f.write(payload)
        else:
            # single_writer mode — caller guarantees exclusivity
            with path.open("a", encoding="utf-8") as f:
                f.write(payload)
