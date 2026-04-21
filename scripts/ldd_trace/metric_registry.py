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
CALIB_MIN_N = 5
CALIB_MAX_MAE = 0.15


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
    metric_name: str
    version: int
    is_load_bearing: bool = False
    promoted_at: Optional[str] = None
    n_calibration_samples: int = 0
    last_mae: Optional[float] = None


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
        # New registration → reset promotion state (advisory)
        self._promotions[name] = PromotionState(
            metric_name=name, version=metric.spec.version, is_load_bearing=False
        )
        self._persist()

    def get(self, name: str) -> Optional[Metric]:
        return self._metrics.get(name)

    def list_names(self) -> List[str]:
        return sorted(self._metrics.keys())

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
            ps = PromotionState(
                metric_name=p_dict["metric_name"],
                version=p_dict["version"],
                is_load_bearing=p_dict.get("is_load_bearing", False),
                promoted_at=p_dict.get("promoted_at"),
                n_calibration_samples=p_dict.get("n_calibration_samples", 0),
                last_mae=p_dict.get("last_mae"),
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

    def __init__(self, registry: MetricRegistry) -> None:
        self.registry = registry
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

    def can_promote(
        self,
        metric_name: str,
        min_n: int = CALIB_MIN_N,
        max_mae: float = CALIB_MAX_MAE,
    ) -> bool:
        n = self.n_samples(metric_name)
        if n < min_n:
            return False
        mae = self.mae(metric_name)
        return mae is not None and mae <= max_mae

    def try_promote(self, metric_name: str) -> bool:
        """If calibration gate passes, promote metric to load_bearing=True.

        Idempotent: if already promoted, returns True without side effects.
        """
        promo = self.registry.promotion(metric_name)
        if promo is None:
            raise ValueError(f"unknown metric: {metric_name!r}")
        if promo.is_load_bearing:
            return True
        if not self.can_promote(metric_name):
            # Update stats without promoting
            promo.n_calibration_samples = self.n_samples(metric_name)
            promo.last_mae = self.mae(metric_name)
            self.registry._persist()
            return False
        # Promote
        promo.is_load_bearing = True
        promo.promoted_at = _utcnow_iso()
        promo.n_calibration_samples = self.n_samples(metric_name)
        promo.last_mae = self.mae(metric_name)
        self.registry._persist()
        return True

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
        self.registry.store.ensure_dir()
        path = self._calibrations_path()
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record.to_dict()) + "\n")
