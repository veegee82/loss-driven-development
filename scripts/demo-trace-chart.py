#!/usr/bin/env python3
"""LDD trace-block demo renderer — all three optimizer loops.

Renders a fictional end-to-end trace showing all three LDD optimizer loops
(inner -> refinement -> outer) with three parallel visualizations of the
same loss signal:

  1. A single-line Unicode sparkline (blocks from U+2581..U+2588), auto-scaled
     to max loss observed in the task. Shows fine-grained dynamics including
     the convergence tail where the mini chart collapses to the baseline.

  2. A mini ASCII loss-curve chart with a 0.25-step Y-axis snap. Shows the
     macro trajectory at a glance; tail convergence collapses to the baseline
     row by design (the loss IS flat below the snap step).

  3. Per-iteration 20-character magnitude bars next to each loss=... line,
     giving column-aligned local magnitude without consuming chart rows.

This is a pure renderer. No skill invocations, no LLM calls, no filesystem
writes. The six iterations and their loss values are hard-coded in
`demo_task()` at the bottom of this file and encode a made-up AWP bug
("L0 gate false-positive on nested JSON deliverables") fixed across all
three loops.

Usage:
    python scripts/demo-trace-chart.py

The rendering functions (`sparkline`, `bar`, `mini_chart`, `trend_arrow`,
`render_trace`) are intentionally decoupled from the demo data so they can
be lifted into a renderer module under `skills/using-ldd/` unchanged.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Literal


Phase = Literal["inner", "refine", "outer"]


@dataclass
class Iteration:
    phase: Phase
    label: str              # "i1", "r1", "o1" — prefix encodes phase
    loss_norm: float        # normalized to [0, 1]
    raw_num: float          # numerator of (N / max); float supports ½
    raw_max: int            # rubric size for this phase
    skill_lines: list[str] = field(default_factory=list)
    # Mode indicator, per v0.5.0 SKILL.md § Loss visualization. For inner:
    # "reactive" or "architect". For refine/outer: unused. Creativity applies
    # only when mode == "architect".
    mode: str = "reactive"
    creativity: str | None = None


@dataclass
class Task:
    title: str
    loops_used: list[Phase]
    budgets: dict[Phase, tuple[int, int]]     # phase -> (k_used, k_max)
    iterations: list[Iteration]
    fix_layer_4: str
    fix_layer_5: str
    docs_synced: str
    terminal: str


# ---------------------------------------------------------------------------
# Pure renderers — take data, return strings. No I/O, no globals.
# ---------------------------------------------------------------------------

_SPARK_BLOCKS = "▁▂▃▄▅▆▇█"  # 8 levels


def sparkline(values: list[float]) -> str:
    """Unicode sparkline auto-scaled to max(values).

    Zero values render as '·' so the baseline is visually distinct from
    low-but-nonzero values in the sparkline body. Matters on convergent tails.
    """
    if not values:
        return ""
    vmax = max(values)
    out: list[str] = []
    for v in values:
        if v == 0 or vmax == 0:
            out.append("·")  # middle dot
            continue
        ratio = v / vmax
        idx = min(7, int(ratio * 7 + 0.5))
        out.append(_SPARK_BLOCKS[idx])
    return "".join(out)


def trend_arrow(values: list[float]) -> str:
    """Coarse end-to-end trend: down / up / flat (within 0.005)."""
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
    iterations: list[Iteration],
    y_step: float = 0.25,
    col_width: int = 3,
) -> list[str]:
    """Multi-line ASCII loss curve.

    Y-axis: gridlines at `y_step` multiples from 0.0 up to the smallest
    multiple >= max(loss). Values snap round-half-up to the nearest gridline.

    X-axis: labels from each iteration, first char aligned with data marker.
    With `col_width=3` and 2-char labels, the axis reads "i1-i2-i3-r1-r2-o1".
    """
    values = [it.loss_norm for it in iterations]
    labels = [it.label for it in iterations]

    max_val = max(values) if values else 0.0
    # Smallest y_step multiple >= max_val — ceil, not round, so e.g.
    # max=0.750 gives ylim=0.75 (not 1.00) and the top row is non-empty.
    ylim = math.ceil(max_val / y_step) * y_step
    ylim = max(ylim, y_step)  # at least one non-zero row

    gridlines: list[float] = []
    y = ylim
    while y > -0.001:
        gridlines.append(round(y, 4))
        y -= y_step

    lines: list[str] = []
    for y in gridlines:
        cells: list[str] = []
        for v in values:
            v_snap = _snap(v, y_step)
            cells.append("●" if abs(v_snap - y) < 0.001 else " ")
        sep = " " * (col_width - 1)
        row_data = sep.join(cells)
        lines.append(f"│   {y:.2f} ┤ {row_data}")

    # X-axis: labels joined by single-char separator; col_width-2 dashes between.
    label_sep = "─" * max(1, col_width - 2)
    x_axis_body = label_sep.join(labels)
    lines.append(f"│        └─{x_axis_body}→  iter")

    return lines


def _format_raw(num: float, denom: int) -> str:
    """Compact '(N/max)' where N may be a half-integer (rendered as ½)."""
    if num == int(num):
        return f"{int(num)}/{denom}"
    if num == 0.5:
        return f"½/{denom}"
    return f"{num}/{denom}"


def _format_mode(it: Iteration) -> str:
    """Render the mode+creativity parenthetical content for an iteration label.

    Per v0.5.0 SKILL.md § Loss visualization, grammar is:
      inner + reactive   → "inner, reactive"
      inner + architect  → "architect, <creativity>"  (caller uses "Phase")
      refine             → "refine"    (no mode/creativity)
      outer              → "outer"     (no mode/creativity)
    """
    if it.phase == "inner":
        if it.mode == "architect":
            return f"architect, {it.creativity or 'standard'}"
        return "inner, reactive"
    return it.phase


def render_trace(task: Task) -> str:
    """Full trace block: header, sparkline, mini chart, per-iter detail, close."""
    lines: list[str] = []

    # Frame top (wide enough for longest content line in demo — open right side)
    lines.append("╭─ LDD trace " + "─" * 70 + "╮")

    # Header
    lines.append(f"│ Task       : {task.title}")
    loops_str = " → ".join(task.loops_used)
    extra = "  (all three fired)" if set(task.loops_used) == {"inner", "refine", "outer"} else ""
    lines.append(f"│ Loops      : {loops_str}{extra}")
    lines.append("│ Loss-type  : normalized [0,1]  (raw counts per loop in parens)")
    budget_parts = [f"{p} k={k}/{kmax}" for p, (k, kmax) in task.budgets.items()]
    lines.append("│ Budget     : " + " · ".join(budget_parts))
    lines.append("│")

    # Sparkline trajectory
    values = [it.loss_norm for it in task.iterations]
    spark = sparkline(values)
    vals_str = " → ".join(f"{v:.3f}" for v in values)
    arrow = trend_arrow(values)
    lines.append(f"│ Trajectory : {spark}   {vals_str}  {arrow}")
    lines.append("│")

    # Mini chart
    lines.append("│ Loss curve (auto-scaled, linear):")
    lines.extend(mini_chart(task.iterations))
    lines.append("│        Phase prefixes: i=inner · r=refine · o=outer")
    lines.append("│")

    # Per-iteration detail — label line + indented skill-info continuation
    prev: float | None = None
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
        lines.append(
            f"{header_padded} loss={it.loss_norm:.3f}  {raw_str}{delta_str}"
        )
        for sk in it.skill_lines:
            lines.append(f"│   {sk}")
        prev = it.loss_norm
    lines.append("│")

    # Close
    lines.append("│ Close:")
    lines.append(
        f"│   Fix at layer : 4: {task.fix_layer_4} · 5: {task.fix_layer_5}"
    )
    lines.append(f"│   Docs synced  : {task.docs_synced}")
    lines.append(f"│   Terminal    : {task.terminal}")

    # Frame bottom
    lines.append("╰" + "─" * 82 + "╯")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Demo data — fictional AWP bug closed across all three optimizer loops.
# ---------------------------------------------------------------------------

def demo_task() -> Task:
    return Task(
        title="fix L0 gate false-positive on nested JSON deliverables",
        loops_used=["inner", "refine", "outer"],
        budgets={"inner": (3, 5), "refine": (2, 3), "outer": (1, 1)},
        iterations=[
            Iteration(
                phase="inner", label="i1",
                loss_norm=0.750, raw_num=6, raw_max=8,
                skill_lines=[
                    "*reproducibility-first* → reproduced 3/3, signal clean",
                    "*root-cause-by-layer*   → layer 4: gate-chain ordering",
                ],
            ),
            Iteration(
                phase="inner", label="i2",
                loss_norm=0.500, raw_num=4, raw_max=8,
                skill_lines=[
                    "*e2e-driven-iteration*  → 2 gates still red (file, eval)",
                ],
            ),
            Iteration(
                phase="inner", label="i3",
                loss_norm=0.125, raw_num=1, raw_max=8,
                skill_lines=[
                    "*loss-backprop-lens*    → sibling-test check 3/3 green",
                ],
            ),
            Iteration(
                phase="refine", label="r1",
                loss_norm=0.100, raw_num=1, raw_max=10,
                skill_lines=[
                    "*iterative-refinement*  → deliverable polish, no code touch",
                ],
            ),
            Iteration(
                phase="refine", label="r2",
                loss_norm=0.050, raw_num=0.5, raw_max=10,
                skill_lines=[
                    "*iterative-refinement*  → plateau detected, loop closes",
                ],
            ),
            Iteration(
                phase="outer", label="o1",
                loss_norm=0.000, raw_num=0, raw_max=8,
                skill_lines=[
                    "*method-evolution*      → SKILL.md rubric updated;",
                    "                          regression prevented on 3 sibling tasks",
                ],
            ),
        ],
        fix_layer_4="gate-chain ordering",
        fix_layer_5="deterministic-before-LLM invariant",
        docs_synced="yes (docs/runtime.md + R33 rubric + SKILL.md)",
        terminal="complete",
    )


def main() -> int:
    print(render_trace(demo_task()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
