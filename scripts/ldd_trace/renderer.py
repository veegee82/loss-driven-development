"""Pure rendering functions for the LDD trace block.

Extracted from `scripts/demo-trace-chart.py` in v0.5.1 so the logic can be
reused by the persistence layer + CLI. Output format is the v0.5.0 spec;
no behavior change versus the demo script.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import List, Literal, Optional, Tuple

Phase = Literal["inner", "refine", "outer"]


@dataclass
class Iteration:
    phase: Phase
    label: str                    # "i1", "r1", "o1", "p1"...
    loss_norm: float              # normalized to [0, 1]
    raw_num: float                # numerator; supports 0.5 for half-credit
    raw_max: int                  # rubric size for this phase
    skill_lines: List[str] = field(default_factory=list)
    # `mode` is a read-compat hook only (v0.11.0+): the scorer no longer
    # tracks `mode=` as a user-facing axis (it is a pure function of level).
    # Projections from a log still set it so the design-phase renderer can
    # pick the right label. Default stays ``reactive`` for backward compat.
    mode: str = "reactive"
    creativity: Optional[str] = None  # "standard" | "conservative" | "inventive"
    timestamp: str = ""           # ISO-8601 — used for chronological sort


@dataclass
class Task:
    title: str
    loops_used: List[Phase]
    budgets: dict                      # phase -> (k_used, k_max)
    iterations: List[Iteration]
    fix_layer_4: str = ""
    fix_layer_5: str = ""
    docs_synced: str = ""
    terminal: str = ""                 # "complete" | "partial" | "failed" | "aborted" | "in-progress"
    # v0.11.x — meta-line metadata surfaced in the trace-block header.
    # bootstrap-userspace mandates Store; using-ldd mandates Dispatched +
    # mode-indicator whenever a level/creativity was chosen. All optional;
    # header lines are emitted only when the corresponding field is non-empty.
    store: str = ""                    # scope label from bootstrap-userspace
    dispatched: str = ""               # full "Dispatched: ..." line, verbatim
    level: str = ""                    # "L0".."L4"
    level_name: str = ""               # "reflex" / "diagnostic" / ... / "method"
    creativity: str = ""               # "standard" / "conservative" / "inventive"


_SPARK_BLOCKS = "▁▂▃▄▅▆▇█"  # 8 levels


def sparkline(values: List[float]) -> str:
    """Unicode sparkline auto-scaled to max(values).

    Zero values render as '·' (middle dot) so the baseline is visually distinct
    from low-but-nonzero values on convergent tails. This matches the §"Loss
    visualization" recipe in `skills/using-ldd/SKILL.md`.
    """
    if not values:
        return ""
    vmax = max(values)
    out: List[str] = []
    for v in values:
        if v == 0 or vmax == 0:
            out.append("·")
            continue
        ratio = v / vmax
        idx = min(7, int(ratio * 7 + 0.5))
        out.append(_SPARK_BLOCKS[idx])
    return "".join(out)


def trend_arrow(values: List[float]) -> str:
    """Coarse end-to-end trend: ↓ / ↑ / → with ±0.005 plateau band.

    Uses last − first, NOT local / majority direction. A session that
    regresses mid-way but recovers below the starting value still reads ↓.
    """
    if len(values) < 2:
        return "·"
    delta = values[-1] - values[0]
    if abs(delta) < 0.005:
        return "→"
    return "↓" if delta < 0 else "↑"


def _snap(v: float, step: float) -> float:
    """Round-half-up snap to nearest `step` multiple."""
    return math.floor(v / step + 0.5) * step


def mini_chart(
    iterations: List[Iteration],
    y_step: float = 0.25,
    col_width: int = 3,
) -> List[str]:
    """Multi-line ASCII loss curve; only rendered for ≥ 3 iterations."""
    values = [it.loss_norm for it in iterations]
    labels = [it.label for it in iterations]

    max_val = max(values) if values else 0.0
    ylim = math.ceil(max_val / y_step) * y_step
    ylim = max(ylim, y_step)

    gridlines: List[float] = []
    y = ylim
    while y > -0.001:
        gridlines.append(round(y, 4))
        y -= y_step

    lines: List[str] = []
    for y in gridlines:
        cells: List[str] = []
        for v in values:
            v_snap = _snap(v, y_step)
            cells.append("●" if abs(v_snap - y) < 0.001 else " ")
        sep = " " * (col_width - 1)
        row_data = sep.join(cells)
        lines.append(f"│   {y:.2f} ┤ {row_data}")

    label_sep = "─" * max(1, col_width - 2)
    x_axis_body = label_sep.join(labels)
    lines.append(f"│        └─{x_axis_body}→  iter")
    return lines


def _format_raw(num: float, denom: int) -> str:
    if num == int(num):
        return f"{int(num)}/{denom}"
    if num == 0.5:
        return f"½/{denom}"
    return f"{num}/{denom}"


def _format_mode(it: Iteration) -> str:
    if it.phase == "inner":
        # The v0.11.0 `design` phase label replaces the legacy `architect` word
        # in display. `it.mode == "architect"` is still set by the projection
        # layer for pre-v0.11.0 traces so the renderer can distinguish the
        # design-phase rows from inner-loop rows.
        if it.mode == "architect":
            return f"design, {it.creativity or 'standard'}"
        return "inner, reactive"
    if it.phase == "cot":
        return "cot, dialectical"
    return it.phase


def _header_mode_line(task: Task) -> Optional[str]:
    """Mode indicator — only emitted when a creativity was selected (L3/L4)
    OR when the explicit mode is non-default. Matches the `mode: architect,
    creativity: ...` line specified in `using-ldd` §Auto-dispatch.
    """
    if task.creativity:
        return f"│ Mode       : architect, {task.creativity}"
    return None


def render_trace(task: Task) -> str:
    """Full trace block: header, sparkline, mini chart, per-iter detail, close."""
    lines: List[str] = []
    lines.append("╭─ LDD trace " + "─" * 70 + "╮")

    # v0.11.x — bootstrap-userspace + using-ldd mandated header lines.
    # Emitted only when the corresponding meta field is populated; otherwise
    # the header stays backward-compatible with pre-v0.11.x traces.
    if task.store:
        lines.append(f"│ Store      : {task.store}")
    if task.dispatched:
        lines.append(f"│ Dispatched : {task.dispatched}")
    mode_line = _header_mode_line(task)
    if mode_line is not None:
        lines.append(mode_line)

    lines.append(f"│ Task       : {task.title}")
    if task.loops_used:
        loops_str = " → ".join(task.loops_used)
        loops_set = set(task.loops_used)
        # The v0.11.0 `design` loop replaces the old `architect` loop name in
        # display; either spelling satisfies the "all N fired" annotations.
        reactive_triple = {"inner", "refine", "outer"}
        if reactive_triple | {"cot"} == loops_set or reactive_triple | {"cot", "design"} == loops_set:
            extra = "  (all four fired)" if loops_set == reactive_triple | {"cot"} else "  (all five fired)"
        elif loops_set == reactive_triple:
            extra = "  (all three fired)"
        else:
            extra = ""
        lines.append(f"│ Loops      : {loops_str}{extra}")
    lines.append("│ Loss-type  : normalized [0,1]  (raw counts per loop in parens)")
    if task.budgets:
        budget_parts = [f"{p} k={k}/{kmax}" for p, (k, kmax) in task.budgets.items()]
        lines.append("│ Budget     : " + " · ".join(budget_parts))
    lines.append("│")

    # Sparkline trajectory — mandatory at ≥ 2 iterations.
    values = [it.loss_norm for it in task.iterations]
    if len(values) >= 2:
        spark = sparkline(values)
        vals_str = " → ".join(f"{v:.3f}" for v in values)
        arrow = trend_arrow(values)
        lines.append(f"│ Trajectory : {spark}   {vals_str}  {arrow}")
        lines.append("│")
    elif len(values) == 1:
        lines.append(f"│ Trajectory : (single data point, loss={values[0]:.3f})")
        lines.append("│")

    # Mini chart — mandatory at ≥ 3 iterations.
    if len(task.iterations) >= 3:
        lines.append("│ Loss curve (auto-scaled, linear):")
        lines.extend(mini_chart(task.iterations))
        lines.append("│        Phase prefixes: i=inner · r=refine · o=outer · c=cot · p=design-phase")
        lines.append("│")

    # Per-iteration detail — always.
    prev: Optional[float] = None
    for it in task.iterations:
        label_kind = "Phase" if it.phase == "inner" and it.mode == "architect" else "Iteration"
        header = f"│ {label_kind} {it.label} ({_format_mode(it)})"
        header_padded = f"{header:<36}"
        raw_str = f"({_format_raw(it.raw_num, it.raw_max)})"
        if prev is None:
            delta_str = ""
        else:
            delta = it.loss_norm - prev
            if abs(delta) < 0.0005:
                sign, d_arrow = "±", "→"
            elif delta < 0:
                sign, d_arrow = "−", "↓"
            else:
                sign, d_arrow = "+", "↑"
            delta_str = f"   Δ {sign}{abs(delta):.3f} {d_arrow}"
        lines.append(f"{header_padded} loss={it.loss_norm:.3f}  {raw_str}{delta_str}")
        for sk in it.skill_lines:
            lines.append(f"│   {sk}")
        prev = it.loss_norm

    # Close block — only if task has terminal state.
    if task.terminal and task.terminal != "in-progress":
        lines.append("│")
        lines.append("│ Close:")
        layer_str = " · ".join(
            s for s in (task.fix_layer_4, task.fix_layer_5) if s
        )
        if layer_str:
            lines.append(f"│   Fix at layer : {layer_str}")
        if task.docs_synced:
            lines.append(f"│   Docs synced  : {task.docs_synced}")
        lines.append(f"│   Terminal    : {task.terminal}")

    lines.append("╰" + "─" * 82 + "╯")
    return "\n".join(lines)
