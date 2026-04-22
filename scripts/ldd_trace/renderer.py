"""Pure rendering functions for the LDD trace block.

Extracted from `scripts/demo-trace-chart.py` in v0.5.1 so the logic can be
reused by the persistence layer + CLI. Output format is the v0.5.0 spec;
no behavior change versus the demo script.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, List, Literal, Optional, Tuple

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
    # v0.13.x Fix 1 — multi-dim loss + epoch marker.
    # ``loss_vec`` is the raw string from trace.log (e.g.
    # ``"latency:0.8,memory:0.4,correctness:0.2"``); the renderer parses it on
    # demand. ``epoch`` defaults to 0 (baseline epoch); a strictly larger value
    # indicates the iteration was recorded under a new rubric/scope frame,
    # so scalar Δloss vs. the previous iteration is meaningless and must be
    # suppressed in the display.
    loss_vec: Optional[str] = None
    epoch: int = 0


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
_EPOCH_MARK = "┊"             # v0.13.x Fix 1 — epoch boundary in sparkline


def _parse_loss_vec(raw: Optional[str]) -> Dict[str, float]:
    """Loose parser for the inline `loss_vec=` wire format used by trace.log.

    Kept minimal here so the renderer has no import-cycle with vector_loss.
    Malformed tokens are dropped; dim-order preservation mirrors
    `vector_loss.loads()`.
    """
    out: Dict[str, float] = {}
    if not raw:
        return out
    for tok in raw.split(","):
        tok = tok.strip()
        if not tok or ":" not in tok:
            continue
        name, _, val = tok.rpartition(":")
        try:
            out[name.strip()] = float(val.strip())
        except ValueError:
            continue
    return out


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


def has_vector_loss(iterations: List[Iteration]) -> bool:
    """True iff at least one iteration carries a parseable `loss_vec`.

    Mixed traces (some iters vector, some scalar-only) count as vector —
    the scalar ones render as single-value sparkline rows per dim using
    their mean-scalar as a degenerate fallback. The renderer is explicit
    about this degeneracy so the user is not misled.
    """
    return any(_parse_loss_vec(it.loss_vec) for it in iterations)


def _sparkline_with_epoch_breaks(
    iterations: List[Iteration], values: List[float]
) -> str:
    """Sparkline with ``┊`` inserted at every boundary where iteration ``k+1``
    carries a strictly larger ``epoch`` than iteration ``k``.

    v0.13.x Fix 1 — visualizing moving-target-loss boundaries so the reader
    immediately sees that Δloss across the `┊` is semantically void.
    """
    if not values:
        return ""
    vmax = max(values)
    out: List[str] = []
    prev_epoch: Optional[int] = None
    for it, v in zip(iterations, values):
        if prev_epoch is not None and it.epoch > prev_epoch:
            out.append(_EPOCH_MARK)
        prev_epoch = it.epoch
        if v == 0 or vmax == 0:
            out.append("·")
        else:
            ratio = v / vmax
            idx = min(7, int(ratio * 7 + 0.5))
            out.append(_SPARK_BLOCKS[idx])
    return "".join(out)


def _trajectory_values_with_epoch_breaks(
    iterations: List[Iteration], values: List[float]
) -> str:
    """Value sequence rendered `a → b │ c → d` where ``│`` marks epoch boundaries."""
    parts: List[str] = []
    prev_epoch: Optional[int] = None
    for it, v in zip(iterations, values):
        if prev_epoch is not None and it.epoch > prev_epoch:
            parts.append("│")
        prev_epoch = it.epoch
        parts.append(f"{v:.3f}")
    # Collapse consecutive `val │ val` into `val │ val`, everything else
    # becomes `a → b → c`.
    out: List[str] = []
    for i, p in enumerate(parts):
        if i == 0:
            out.append(p)
            continue
        sep = " " if p == "│" or parts[i - 1] == "│" else " → "
        out.append(sep)
        out.append(p)
    return "".join(out)


def _pareto_arrow(prev_vec: Dict[str, float], cur_vec: Dict[str, float]) -> str:
    """Ternary Pareto-dominance arrow for the renderer.

    ⇓ — cur dominates prev (all dims equal or better, ≥1 strictly better)
    ⇔ — non-dominated trade-off (at least one dim better, one worse)
    ⇑ — prev dominates cur (regression across the front)
    """
    if not prev_vec or not cur_vec:
        return "·"
    shared = sorted(set(prev_vec) & set(cur_vec))
    if not shared:
        return "·"
    cur_better = False
    prev_better = False
    eps = 1e-9
    for d in shared:
        if cur_vec[d] + eps < prev_vec[d]:
            cur_better = True
        elif prev_vec[d] + eps < cur_vec[d]:
            prev_better = True
    if cur_better and not prev_better:
        return "⇓"
    if prev_better and not cur_better:
        return "⇑"
    return "⇔"


def multi_dim_trajectory(iterations: List[Iteration]) -> List[str]:
    """One sparkline row per dimension in the vector loss.

    Determines the full dimension set by unioning all parsed `loss_vec`
    values; missing dims on an iteration are filled with that iteration's
    scalar `loss_norm` (the degenerate fallback). Adds a final "Pareto" row
    that summarizes per-step dominance between consecutive iterations.

    Returns a list of ready-to-join lines (each with the leading ``│ ``
    prefix the caller expects).
    """
    vecs: List[Dict[str, float]] = [_parse_loss_vec(it.loss_vec) for it in iterations]
    dims: List[str] = []
    for v in vecs:
        for d in v:
            if d not in dims:
                dims.append(d)
    if not dims:
        return []

    # Fill missing dims with the scalar loss so the sparkline rows are
    # comparable across iterations. Mark such fallbacks in the "Pareto"
    # summary as "incomplete" so the reader knows the Pareto verdict is
    # approximate for those steps.
    dim_width = max(len(d) for d in dims)
    lines: List[str] = []
    lines.append("│ Trajectory (vector):")
    for d in dims:
        values_for_dim: List[float] = []
        for i, it in enumerate(iterations):
            v = vecs[i].get(d)
            values_for_dim.append(it.loss_norm if v is None else v)
        spark = _sparkline_with_epoch_breaks(iterations, values_for_dim)
        trend = trend_arrow(values_for_dim)
        vals_str = _trajectory_values_with_epoch_breaks(iterations, values_for_dim)
        lines.append(f"│   {d:<{dim_width}} : {spark}   {vals_str}  {trend}")

    if len(iterations) >= 2:
        lines.append(f"│   {'Pareto':<{dim_width}} :")
        for i in range(1, len(iterations)):
            prev = vecs[i - 1]
            cur = vecs[i]
            arrow = _pareto_arrow(prev, cur)
            note = (
                "dominant" if arrow == "⇓"
                else "regression" if arrow == "⇑"
                else "non-dominated trade-off" if arrow == "⇔"
                else "incomplete"
            )
            prev_lbl = iterations[i - 1].label
            cur_lbl = iterations[i].label
            epoch_note = (
                "  [epoch boundary — Δloss invalid]"
                if iterations[i].epoch > iterations[i - 1].epoch
                else ""
            )
            lines.append(
                f"│   {' ':<{dim_width}}   {prev_lbl} → {cur_lbl} {arrow} "
                f"({note}){epoch_note}"
            )
    return lines


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


def render_summary(task: Task) -> str:
    """Compact 5-7 line block: task, loops, loss trajectory, close verdict.

    Target audience: the "stop-hook rendered a block for every turn and I only
    wanted a tiny digest" case. Shows what happened without the mini-chart or
    per-iteration info lines. Full block remains available via
    `ldd_trace render --verbosity full` or the `/ldd-trace` command.
    """
    width = 82  # match render_trace frame width
    inner_width = width - 2  # minus the two corner chars

    lines: List[str] = []
    lines.append("╭─ LDD summary " + "─" * (width - 15) + "╮")

    terminal_tag = f"  ({task.terminal})" if task.terminal else "  (in-progress)"
    title = task.title or "(no title)"
    lines.append(f"│ Task    : {title}{terminal_tag}")

    if task.loops_used:
        # Count iterations per loop for a one-line "loops=design×5 · inner×4 …".
        from collections import Counter
        c = Counter(it.phase for it in task.iterations)
        # Display order follows the canonical loop order, not first-seen.
        order = ["design", "inner", "cot", "refine", "outer"]
        parts = []
        for loop in order:
            # `design` iterations have phase="inner" and mode="architect" in
            # this model — count via label prefix instead of phase.
            if loop == "design":
                n = sum(1 for it in task.iterations if it.label.startswith("p"))
            else:
                prefix = {"inner": "i", "cot": "c", "refine": "r", "outer": "o"}[loop]
                n = sum(1 for it in task.iterations if it.label.startswith(prefix))
            if n > 0:
                parts.append(f"{loop}×{n}")
        if parts:
            loops_str = " · ".join(parts)
            # Optional "(all N fired)" annotation — reuse render_trace logic.
            loops_set = set(task.loops_used)
            reactive_triple = {"inner", "refine", "outer"}
            if reactive_triple | {"cot", "design"} == loops_set:
                extra = "  (all five fired)"
            elif reactive_triple | {"cot"} == loops_set:
                extra = "  (all four fired)"
            elif loops_set == reactive_triple:
                extra = "  (all three fired)"
            else:
                extra = ""
            lines.append(f"│ Loops   : {loops_str}{extra}")

    values = [it.loss_norm for it in task.iterations]
    if len(values) >= 2:
        spark = sparkline(values)
        arrow = trend_arrow(values)
        lines.append(
            f"│ Loss    : {values[0]:.3f} → {values[-1]:.3f}  {arrow}   {spark}"
        )
    elif len(values) == 1:
        lines.append(f"│ Loss    : {values[0]:.3f}  (single data point)")

    if task.terminal and task.terminal != "in-progress":
        layer_str = " · ".join(
            s for s in (task.fix_layer_4, task.fix_layer_5) if s
        )
        if layer_str:
            lines.append(f"│ Layer   : {layer_str}")
        if task.docs_synced:
            lines.append(f"│ Docs    : {task.docs_synced}")

    lines.append(f"│ {'':74}  full: /ldd-trace")
    lines.append("╰" + "─" * width + "╯")
    return "\n".join(lines)


def render(task: Task, verbosity: str = "full") -> str:
    """Dispatcher: pick rendering variant based on verbosity preset.

    Presets:
        off     — empty string (hook emits nothing)
        summary — compact digest (render_summary)
        full    — full trace block (render_trace) — legacy default
        debug   — full + diagnostic footer
    """
    v = (verbosity or "full").strip().lower()
    if v == "off":
        return ""
    if v == "summary":
        return render_summary(task)
    if v == "debug":
        body = render_trace(task)
        footer = (
            f"\n[debug] iterations={len(task.iterations)}  "
            f"loops={sorted(set(task.loops_used))}  "
            f"terminal={task.terminal or 'in-progress'}"
        )
        return body + footer
    # full (and any unknown value falls back to full — safest default)
    return render_trace(task)


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

    # Sparkline trajectory — mandatory at ≥ 2 iterations. If ANY iteration
    # carries a vector loss, switch to the multi-dim renderer (one sparkline
    # row per dim + a Pareto-dominance summary). Epoch boundaries always
    # show as ``┊`` in the scalar sparkline and as `│` in the value string.
    values = [it.loss_norm for it in task.iterations]
    vector_mode = has_vector_loss(task.iterations)
    if len(values) >= 2:
        spark = _sparkline_with_epoch_breaks(task.iterations, values)
        vals_str = _trajectory_values_with_epoch_breaks(task.iterations, values)
        arrow = trend_arrow(values)
        lines.append(f"│ Trajectory : {spark}   {vals_str}  {arrow}")
        if vector_mode:
            lines.append("│")
            lines.extend(multi_dim_trajectory(task.iterations))
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
    prev_epoch: Optional[int] = None
    prev_vec: Dict[str, float] = {}
    prev_label: str = ""
    for it in task.iterations:
        label_kind = "Phase" if it.phase == "inner" and it.mode == "architect" else "Iteration"
        header = f"│ {label_kind} {it.label} ({_format_mode(it)})"
        header_padded = f"{header:<36}"
        raw_str = f"({_format_raw(it.raw_num, it.raw_max)})"
        cur_vec = _parse_loss_vec(it.loss_vec)
        # Δ-column rules (v0.13.x Fix 1):
        #   * Cross-epoch boundary → Δ is meaningless; print "Δ n/a (epoch boundary)"
        #   * Vector loss on both sides → use Pareto arrow ⇓⇔⇑, not scalar ↓→↑
        #   * Otherwise → scalar Δ as before
        if prev is None:
            delta_str = ""
        elif prev_epoch is not None and it.epoch > prev_epoch:
            delta_str = "   Δ  n/a (epoch boundary)"
        elif cur_vec and prev_vec:
            arrow = _pareto_arrow(prev_vec, cur_vec)
            delta_str = f"   Pareto {arrow} vs {prev_label}"
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
        prev_epoch = it.epoch
        prev_vec = cur_vec
        prev_label = it.label

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
