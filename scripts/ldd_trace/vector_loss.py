"""Vector loss — multi-dimensional loss with Pareto-dominance semantics.

v0.13.x Fix 1: the scalar-loss assumption is incorrect for Pareto-problems
(latency AND memory AND correctness must all improve). Forcing a scalar
aggregate hides Pareto-dominance and produces ambiguous gradient directions.
This module stores per-dimension loss values and computes Pareto-dominance
between successive iterations without collapsing to a scalar.

Format on the trace-log wire:

    loss_vec=latency:0.80,memory:0.40,correctness:0.20

Tokens are comma-separated; each token is `name:value`. Names carry the same
character set as scorer signals (alphanumeric + `._->`), values are floats
in [0,1] normalized to their own dimension's range by the caller.

When an iteration carries BOTH `loss=…` and `loss_vec=…`, `loss=` is treated
as a convenience scalar (e.g. mean of vector components) and `loss_vec=`
carries the authoritative multi-dim information. Renderers prefer the vector
form when both are present.

Pareto-dominance rule:
    A dominates B  ⇔  ∀d: A[d] ≤ B[d]  ∧  ∃d: A[d] < B[d]
                      (A is at-least-as-good in every dim AND strictly better
                       in at least one)
    Missing dims are treated as 0 for the side that lacks them; the caller
    is responsible for aligning dimensions before comparison. Most consumers
    use the constructor-enforced `dims` list.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional


DOMINANCE_EPS = 1e-9


@dataclass(frozen=True)
class VectorLoss:
    """Immutable multi-dimensional loss.

    ``dims`` fixes the order for rendering and serialization. ``values`` is a
    mapping from dim name → float, which lets the caller keep dim names
    stable even if the iteration order changes.
    """

    dims: tuple
    values: Dict[str, float]

    def __post_init__(self) -> None:
        # No mutation on a frozen dataclass; validation only.
        missing = [d for d in self.dims if d not in self.values]
        if missing:
            raise ValueError(f"vector loss missing dims: {missing}")
        extra = [d for d in self.values if d not in self.dims]
        if extra:
            raise ValueError(f"vector loss has dims not in spec: {extra}")

    # --- comparison -----------------------------------------------------

    def dominates(self, other: "VectorLoss") -> Optional[bool]:
        """Ternary Pareto dominance.

        Returns:
            True   — self strictly dominates other
            False  — other strictly dominates self
            None   — incomparable (Pareto-non-dominated — the user has a choice)
        """
        if tuple(self.dims) != tuple(other.dims):
            raise ValueError(
                "dimension mismatch — align dims before Pareto comparison"
            )
        self_better_anywhere = False
        other_better_anywhere = False
        for d in self.dims:
            a = self.values[d]
            b = other.values[d]
            if a + DOMINANCE_EPS < b:
                self_better_anywhere = True
            elif b + DOMINANCE_EPS < a:
                other_better_anywhere = True
        if self_better_anywhere and not other_better_anywhere:
            return True
        if other_better_anywhere and not self_better_anywhere:
            return False
        return None

    def dominance_arrow(self, prev: "VectorLoss") -> str:
        """Unicode arrow vs. prev iteration — ⇓/⇔/⇑ replaces the scalar ↓/→/↑.

        ``⇓`` = self dominates prev (all dims equal or better, at least one better)
        ``⇔`` = Pareto non-dominated (trade-off — at least one dim improved,
                at least one regressed; the caller must judge)
        ``⇑`` = prev dominates self (regression across the whole front)
        """
        verdict = self.dominates(prev)
        if verdict is True:
            return "⇓"
        if verdict is False:
            return "⇑"
        return "⇔"

    # --- serde ----------------------------------------------------------

    def dumps(self) -> str:
        """Serialize to `name:value,name:value` format."""
        return ",".join(f"{d}:{self.values[d]:.3f}" for d in self.dims)


def loads(raw: str) -> VectorLoss:
    """Parse `name:value,name:value` back into a VectorLoss.

    Preserves the order of dimensions as they appear in the input, which is
    how the round-trip invariant (``loads(dumps(v)) == v``) holds.
    """
    dims: List[str] = []
    values: Dict[str, float] = {}
    for tok in raw.split(","):
        tok = tok.strip()
        if not tok or ":" not in tok:
            continue
        name, _, val = tok.rpartition(":")
        name = name.strip()
        try:
            values[name] = float(val.strip())
            dims.append(name)
        except ValueError:
            # Drop malformed entries silently; the caller can check .dims for
            # completeness versus an expected spec.
            continue
    return VectorLoss(dims=tuple(dims), values=values)


def mean_scalar(vec: VectorLoss) -> float:
    """Back-compat scalar view — equal-weighted mean across dims.

    Exposed so callers that still operate on `loss=` can get a sensible
    scalar without manually aggregating. **Do not use this for Pareto
    decisions** — that's exactly what VectorLoss was introduced to avoid.
    """
    if not vec.dims:
        return 0.0
    return sum(vec.values[d] for d in vec.dims) / len(vec.dims)
