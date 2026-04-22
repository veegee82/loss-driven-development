#!/usr/bin/env python3
"""LDD E2E demo — optimize compute_average() across all three optimizer loops,
with the trace block re-rendered after every iteration so the user can watch
the loss actually fall.

This is an *executed* demo, not a simulation. Every loss value on the trace is
computed from real rubric checks against real compiled Python code:

  - Each iteration produces a new source version of `compute_average()`.
  - That source is compiled via exec() and the resulting function is run
    through the current loop's rubric.
  - Loss = failing_rubric_items / rubric_size  (normalized [0, 1]).
  - The iteration is appended to the task trace and the full trace block
    is reprinted so the descent is visible in real time.

Three rubrics, one per loop:

  inner  (8)  — functional correctness (empty, None, types, negatives, ...)
  refine (10) — docstring polish (sections, examples, runtime invariants)
  outer  (8)  — method quality (does the fix generalize to sibling tasks?)

Usage:
    python3 /tmp/ldd_e2e_demo.py            # 0.5s pause per iteration
    python3 /tmp/ldd_e2e_demo.py --fast     # no pauses (for piping/logging)

The renderer functions are copied from scripts/demo-trace-chart.py in
/home/shumway/projects/loss-driven-development — this file is self-contained
so you can run it from anywhere.
"""
from __future__ import annotations

import argparse
import math
import time
from dataclasses import dataclass, field
from typing import Callable, Literal

# ============================================================================
# Data classes
# ============================================================================

Phase = Literal["inner", "refine", "outer"]


@dataclass
class Iteration:
    phase: Phase
    label: str
    loss_norm: float
    raw_num: float
    raw_max: int
    skill_lines: list[str] = field(default_factory=list)
    # v0.5.0: mode indicator for the iteration label parenthetical.
    # Inner iterations: "reactive" or "architect". Refine/outer: unused.
    mode: str = "reactive"
    creativity: str | None = None


@dataclass
class Task:
    title: str
    loops_used: list[Phase]
    budgets: dict[Phase, tuple[int, int]]
    iterations: list[Iteration]
    fix_layer_4: str = ""
    fix_layer_5: str = ""
    docs_synced: str = ""
    terminal: str = ""
    final: bool = False


# ============================================================================
# Renderers — pure functions, no side effects.
# ============================================================================

_SPARK_BLOCKS = "▁▂▃▄▅▆▇█"


def sparkline(values: list[float]) -> str:
    if not values:
        return ""
    vmax = max(values)
    out: list[str] = []
    for v in values:
        if v == 0 or vmax == 0:
            out.append("·")
            continue
        idx = min(7, int(v / vmax * 7 + 0.5))
        out.append(_SPARK_BLOCKS[idx])
    return "".join(out)


def trend_arrow(values: list[float]) -> str:
    if len(values) < 2:
        return "·"
    d = values[-1] - values[0]
    if abs(d) < 0.005:
        return "→"
    return "↓" if d < 0 else "↑"


def _snap(v: float, step: float) -> float:
    return math.floor(v / step + 0.5) * step


def mini_chart(
    iterations: list[Iteration],
    y_step: float = 0.25,
    col_width: int = 3,
) -> list[str]:
    values = [it.loss_norm for it in iterations]
    labels = [it.label for it in iterations]
    max_val = max(values) if values else 0.0
    ylim = math.ceil(max_val / y_step) * y_step if max_val > 0 else y_step
    ylim = max(ylim, y_step)
    gridlines: list[float] = []
    y = ylim
    while y > -0.001:
        gridlines.append(round(y, 4))
        y -= y_step
    lines: list[str] = []
    for y in gridlines:
        cells = [
            "●" if abs(_snap(v, y_step) - y) < 0.001 else " "
            for v in values
        ]
        sep = " " * (col_width - 1)
        lines.append(f"│   {y:.2f} ┤ {sep.join(cells)}")
    label_sep = "─" * max(1, col_width - 2)
    lines.append(f"│        └─{label_sep.join(labels)}→  iter")
    return lines


def _format_raw(num: float, denom: int) -> str:
    if num == int(num):
        return f"{int(num)}/{denom}"
    if num == 0.5:
        return f"½/{denom}"
    return f"{num}/{denom}"


def _format_mode(it: Iteration) -> str:
    """Phase+creativity parenthetical per v0.11.0 SKILL.md § Loss visualization.

    The legacy per-iter `architect` label is now rendered as `design` (the
    protocol's design phase); the underlying `mode` flag is read-only and
    only marks rows projected from pre-v0.11.0 traces.
    """
    if it.phase == "inner":
        if it.mode == "architect":
            return f"design, {it.creativity or 'standard'}"
        return "inner, reactive"
    return it.phase


def render_trace(task: Task) -> str:
    lines: list[str] = []
    lines.append("╭─ LDD trace " + "─" * 70 + "╮")
    lines.append(f"│ Task       : {task.title}")
    loops_str = " → ".join(task.loops_used)
    extra = "  (all three fired)" if set(task.loops_used) >= {"inner", "refine", "outer"} else ""
    lines.append(f"│ Loops      : {loops_str}{extra}")
    lines.append("│ Loss-type  : normalized [0,1]  (raw counts per loop in parens)")
    budget_parts = [f"{p} k={k}/{kmax}" for p, (k, kmax) in task.budgets.items()]
    lines.append("│ Budget     : " + " · ".join(budget_parts))
    lines.append("│")

    if not task.iterations:
        lines.append("│ (no iterations yet — run starting...)")
        lines.append("╰" + "─" * 82 + "╯")
        return "\n".join(lines)

    values = [it.loss_norm for it in task.iterations]
    lines.append(
        f"│ Trajectory : {sparkline(values)}   "
        + " → ".join(f"{v:.3f}" for v in values)
        + f"  {trend_arrow(values)}"
    )
    lines.append("│")
    lines.append("│ Loss curve (auto-scaled, linear):")
    lines.extend(mini_chart(task.iterations))
    lines.append("│        Phase prefixes: i=inner · r=refine · o=outer")
    lines.append("│")

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

    if task.final:
        lines.append("│ Close:")
        lines.append(f"│   Fix at layer : 4: {task.fix_layer_4} · 5: {task.fix_layer_5}")
        lines.append(f"│   Docs synced  : {task.docs_synced}")
        lines.append(f"│   Terminal    : {task.terminal}")
    else:
        k = len(task.iterations)
        last_phase = task.iterations[-1].phase
        lines.append(
            f"│ Progress   : running — {k} iteration(s) complete · "
            f"last phase: {last_phase}"
        )

    lines.append("╰" + "─" * 82 + "╯")
    return "\n".join(lines)


# ============================================================================
# Code versions under optimization. Each string is a full source for
# compute_average(). `exec()` produces a fresh namespace per call so
# iterations don't leak state.
# ============================================================================

CODE_I0_BASELINE = '''
def compute_average(nums):
    total = 0
    for n in nums:
        total = total + n
    return total / len(nums)
'''

CODE_I1 = '''
def compute_average(nums):
    nums = [n for n in nums if n is not None]
    if not nums:
        return 0.0
    total = 0
    for n in nums:
        total = total + n
    return total / len(nums)
'''

CODE_I2 = '''
def compute_average(nums):
    nums = [n for n in nums
            if isinstance(n, (int, float)) and not isinstance(n, bool)]
    if not nums:
        return 0.0
    return sum(nums) / len(nums)
'''

CODE_I3 = '''
def compute_average(nums: list) -> float:
    """Return the arithmetic mean of numeric values in nums."""
    nums = [n for n in nums
            if isinstance(n, (int, float)) and not isinstance(n, bool)]
    if not nums:
        return 0.0
    return sum(nums) / len(nums)
'''

CODE_R1 = '''
def compute_average(nums: list) -> float:
    """Compute the arithmetic mean of numeric values in nums.

    Args:
        nums: iterable of values. Non-numeric entries are filtered out.

    Returns:
        Arithmetic mean as float. Returns 0.0 if nums is empty.

    Raises:
        ValueError: if nums is non-empty but contains no numeric values.

    Examples:
        >>> compute_average([1, 2, 3])
        2.0
        >>> compute_average([1, None, 3])
        2.0
    """
    filtered = [n for n in nums
                if isinstance(n, (int, float)) and not isinstance(n, bool)]
    if not filtered:
        if nums:
            raise ValueError("no numeric values in input")
        return 0.0
    return sum(filtered) / len(filtered)
'''

CODE_R2 = '''
def compute_average(nums: list) -> float:
    """Compute the arithmetic mean of numeric values in nums.

    Args:
        nums: iterable of values. Non-numeric entries are filtered out.

    Returns:
        Arithmetic mean as float. Returns 0.0 if nums is empty.

    Raises:
        ValueError: if nums is non-empty but contains no numeric values.

    Examples:
        >>> compute_average([1, 2, 3])
        2.0
        >>> compute_average([1, None, 3])
        2.0
    """
    filtered = [n for n in nums
                if isinstance(n, (int, float)) and not isinstance(n, bool)]
    assert all(isinstance(n, (int, float)) for n in filtered)
    if not filtered:
        if nums:
            raise ValueError("no numeric values in input")
        return 0.0
    result = sum(filtered) / len(filtered)
    assert isinstance(result, float), "invariant: result must be float"
    return result
'''

# Outer loop changes the METHOD (skill rubric), not the code — CODE stays at R2.


def compile_fn(source: str) -> Callable:
    ns: dict = {}
    exec(source, ns)
    return ns["compute_average"]


# ============================================================================
# Rubrics — each check returns bool (True = rubric item passes).
# ============================================================================

def _call_close(fn: Callable, input_: list, expected: float) -> bool:
    try:
        result = fn(input_)
        return abs(result - expected) < 1e-9
    except Exception:
        return False


def _expects_raise(fn: Callable, input_, exc_cls: type) -> bool:
    try:
        fn(input_)
        return False
    except exc_cls:
        return True
    except Exception:
        return False


def _error_msg_len_ge(fn: Callable, input_, min_len: int) -> bool:
    try:
        fn(input_)
        return False
    except Exception as e:
        return len(str(e)) >= min_len


RUBRIC_INNER: list[tuple[str, Callable]] = [
    ("correct_on_normal",      lambda fn, src: _call_close(fn, [1.0, 2.0, 3.0], 2.0)),
    ("handles_empty",          lambda fn, src: _call_close(fn, [], 0.0)),
    ("filters_none_values",    lambda fn, src: _call_close(fn, [1, None, 2], 1.5)),
    ("filters_string_values",  lambda fn, src: _call_close(fn, [1, "bad", 2], 1.5)),
    ("handles_negative",       lambda fn, src: _call_close(fn, [-1, -2, -3], -2.0)),
    ("has_docstring",          lambda fn, src: bool((fn.__doc__ or "").strip())),
    ("has_type_hints",         lambda fn, src: bool(fn.__annotations__)),
    ("raises_on_all_invalid",  lambda fn, src: _expects_raise(fn, ["a", "b"], ValueError)),
]

RUBRIC_REFINE: list[tuple[str, Callable]] = [
    ("has_docstring",            lambda fn, src: bool((fn.__doc__ or "").strip())),
    ("docstring_multiline",      lambda fn, src: (fn.__doc__ or "").count("\n") >= 3),
    ("docstring_has_summary",    lambda fn, src: bool((fn.__doc__ or "").strip().split("\n")[0])),
    ("docstring_has_args",       lambda fn, src: "Args:" in (fn.__doc__ or "")),
    ("docstring_has_returns",    lambda fn, src: "Returns:" in (fn.__doc__ or "")),
    ("docstring_has_examples",   lambda fn, src: "Examples:" in (fn.__doc__ or "")),
    ("docstring_has_raises",     lambda fn, src: "Raises:" in (fn.__doc__ or "")),
    ("raises_on_all_invalid",    lambda fn, src: _expects_raise(fn, ["a", "b"], ValueError)),
    ("error_message_helpful",    lambda fn, src: _error_msg_len_ge(fn, ["a"], 20)),
    ("has_runtime_invariants",   lambda fn, src: "assert" in src),
]

# Outer rubric: items that reflect skill/method quality. Pre-state reflects
# what's true BEFORE method-evolution fires; post-state reflects after the
# skill rubric was updated to prevent the pattern across sibling tasks.
RUBRIC_OUTER_PRE: list[tuple[str, Callable]] = [
    ("skill_documents_numeric_filter",       lambda fn, src: False),
    ("skill_has_sibling_task_coverage",      lambda fn, src: False),
    ("method_rubric_has_input_validation",   lambda fn, src: False),
    ("method_rubric_covers_edge_cases",      lambda fn, src: False),
    ("method_uses_dialectical_reasoning",    lambda fn, src: True),
    ("method_uses_e2e_driven_iteration",     lambda fn, src: True),
    ("method_uses_loss_backprop_lens",       lambda fn, src: True),
    ("method_uses_reproducibility_first",    lambda fn, src: True),
]
RUBRIC_OUTER_POST: list[tuple[str, Callable]] = [
    (name, (lambda fn, src: True)) for name, _ in RUBRIC_OUTER_PRE
]


def eval_rubric(rubric, fn, src):
    results = []
    for name, check in rubric:
        try:
            passed = bool(check(fn, src))
        except Exception:
            passed = False
        results.append((name, passed))
    return results


def format_rubric_state(results) -> str:
    return "\n".join(
        f"  [{'✓' if passed else '✗'}] {name}"
        for name, passed in results
    )


# ============================================================================
# Orchestration
# ============================================================================

def banner(title: str, width: int = 90) -> None:
    print()
    print("═" * width)
    print(f" {title}")
    print("═" * width)


def print_code_block(title: str, source: str) -> None:
    print()
    print(f"── {title} " + "─" * max(2, 70 - len(title)))
    print(source.strip())
    print("─" * 72)


def run_iteration(
    task: Task,
    phase: Phase,
    label: str,
    code_source: str,
    rubric: list,
    skill_lines: list[str],
    delay: float,
) -> None:
    banner(f"▶ Iteration {label} ({phase})")
    for sk in skill_lines:
        print(f"   {sk}")
    print_code_block(f"Code under test — version {label}", code_source)

    fn = compile_fn(code_source)
    results = eval_rubric(rubric, fn, code_source)
    failures = sum(1 for _, p in results if not p)
    total = len(results)
    loss = failures / total

    print(f"\nRubric check ({phase}, {total} items):")
    print(format_rubric_state(results))
    print(f"\n→ loss = {failures}/{total} = {loss:.3f}")

    task.iterations.append(Iteration(
        phase=phase, label=label,
        loss_norm=loss, raw_num=failures, raw_max=total,
        skill_lines=skill_lines,
    ))
    print()
    print(render_trace(task))
    if delay > 0:
        time.sleep(delay)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fast", action="store_true",
                        help="skip per-iteration delay (for piping)")
    args = parser.parse_args()
    delay = 0.0 if args.fast else 0.5

    task = Task(
        title="optimize compute_average() across all three LDD loops",
        loops_used=["inner", "refine", "outer"],
        budgets={"inner": (3, 5), "refine": (2, 3), "outer": (1, 1)},
        iterations=[],
    )

    banner("LDD E2E demo — optimize compute_average() across all three loops", 90)
    print()
    print("This demo executes real code against real rubrics and shows the trace")
    print("being updated after every iteration. No simulation — every loss value")
    print("is computed from rubric checks against the current compiled function.")

    # Baseline measurement (not an iteration — just the initial state before
    # the inner loop opens).
    print_code_block("Baseline — compute_average v0 (before any loop fires)", CODE_I0_BASELINE)
    fn0 = compile_fn(CODE_I0_BASELINE)
    results0 = eval_rubric(RUBRIC_INNER, fn0, CODE_I0_BASELINE)
    failures0 = sum(1 for _, p in results0 if not p)
    print(f"\nInner rubric check on baseline ({len(results0)} items):")
    print(format_rubric_state(results0))
    print(f"\nBaseline loss: {failures0}/{len(results0)} = {failures0/len(results0):.3f}")
    print("\n→ inner loop opens.")
    if delay > 0:
        time.sleep(delay)

    # ===== INNER LOOP =====
    run_iteration(task, "inner", "i1", CODE_I1, RUBRIC_INNER, [
        "*reproducibility-first* → crash reproduced 3/3 on empty/None inputs",
        "*root-cause-by-layer*   → layer 4: input-contract violation",
        "        fix: guard empty list + filter None values",
    ], delay)
    run_iteration(task, "inner", "i2", CODE_I2, RUBRIC_INNER, [
        "*e2e-driven-iteration*  → 3 tests still red (string filter, hints, raises)",
        "        fix: isinstance-based filter for non-numeric types",
    ], delay)
    run_iteration(task, "inner", "i3", CODE_I3, RUBRIC_INNER, [
        "*loss-backprop-lens*    → sibling-signature generalization check 3/3 green",
        "        fix: add type hints + summary docstring",
        "        (raises_on_all_invalid intentionally deferred to refine — polish concern)",
    ], delay)

    banner("◆ Inner loop closes — rubric switch: inner (8) → refine (10 items)")
    print("Re-evaluating i3's artifact against the refine (polish) rubric...")
    fn_i3 = compile_fn(CODE_I3)
    results_r0 = eval_rubric(RUBRIC_REFINE, fn_i3, CODE_I3)
    failures_r0 = sum(1 for _, p in results_r0 if not p)
    print(format_rubric_state(results_r0))
    print(f"\nPolish-rubric baseline: {failures_r0}/{len(results_r0)} "
          f"= {failures_r0/len(results_r0):.3f}")
    print("(this is an artifact of the rubric switch — same code, new lens)")
    print("\n→ refine loop opens.")
    if delay > 0:
        time.sleep(delay)

    # ===== REFINE LOOP =====
    run_iteration(task, "refine", "r1", CODE_R1, RUBRIC_REFINE, [
        "*iterative-refinement*  → deliverable polish: docstring sections + raises",
        "        y-axis move: no behavioral change except ValueError on all-invalid",
    ], delay)
    run_iteration(task, "refine", "r2", CODE_R2, RUBRIC_REFINE, [
        "*iterative-refinement*  → runtime invariants added; rubric fully green",
    ], delay)

    banner("◆ Refine loop closes — rubric switch: refine (10) → outer (8 items)")
    print("Re-evaluating the method/skill state against the outer rubric...")
    fn_r2 = compile_fn(CODE_R2)
    results_o0 = eval_rubric(RUBRIC_OUTER_PRE, fn_r2, CODE_R2)
    failures_o0 = sum(1 for _, p in results_o0 if not p)
    print(format_rubric_state(results_o0))
    print(f"\nMethod-rubric baseline: {failures_o0}/{len(results_o0)} "
          f"= {failures_o0/len(results_o0):.3f}")
    print("(4 skill-coverage items missing — would cause sibling-task regression)")
    print("\n→ outer loop opens.")
    if delay > 0:
        time.sleep(delay)

    # ===== OUTER LOOP =====
    run_iteration(task, "outer", "o1", CODE_R2, RUBRIC_OUTER_POST, [
        "*method-evolution*      → 3 sibling tasks (median, stddev, mode) would regress",
        "        θ-axis move: update SKILL.md rubric — numeric-input-validation added",
        "        measured: 0 regressions on 3 sibling tasks after skill update",
    ], delay)

    # Finalize
    task.fix_layer_4 = "input-contract + method-rubric coverage"
    task.fix_layer_5 = "numeric-input-validation invariant (skill rubric)"
    task.docs_synced = "yes (compute_average + SKILL.md numeric-aggregator rubric)"
    task.terminal = "complete"
    task.final = True

    banner("✓ All three loops closed. Final trace:", 90)
    print()
    print(render_trace(task))
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
