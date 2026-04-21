"""Retrieval surface — turns project_memory.json into navigation hints.

v0.5.2. Three query shapes:

  * **suggest**  — at current iteration state, rank candidate skills by
                   expected-Δloss (empirical), partitioned by terminal.
                   Bias-guarded: relative Δ used primarily so hard-bug
                   skills don't trivially rank higher.
  * **check**    — inspect the IN-FLIGHT task's last iterations against the
                   project-memory. Returns warnings for:
                     - plateau detected (≥ 2 consecutive near-zero Δ)
                     - project-typical `k` already exceeded
                     - next-planned skill historically regresses at
                       similar starting loss
  * **similar**  — rank past tasks by file-overlap with the current task
                   (no embeddings, pure set math on the `files=` field if
                   populated).
  * **health**   — human-readable summary of the project's memory.

None of these modify the loss. They inform navigation (which skill next,
when to escalate, where to warm-start).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence, Tuple

from ldd_trace.store import TaskSlice, TraceStore


# ---------------------------------------------------------------------------
# suggest — rank skills
# ---------------------------------------------------------------------------


@dataclass
class SkillSuggestion:
    skill: str
    delta_mean_relative: float
    delta_mean_absolute: float
    regression_rate: float
    plateau_rate: float
    n_invocations: int
    rank_score: float
    reason: str


def suggest_skills(
    memory: dict,
    min_invocations: int = 3,
    top_n: int = 5,
) -> List[SkillSuggestion]:
    """Rank skills by empirical effectiveness, using relative Δ as primary.

    `rank_score = delta_mean_relative * (1 - regression_rate) * log(1+n)/log(1+10)`
    — relative Δ is the gradient's apparent strength, regression-rate
    penalizes noisy skills, log(n) rewards sample size without overweighting
    skills that fire 100× vs 10×.

    Skills below `min_invocations` are surfaced as "insufficient data" rather
    than ranked — the rank-score for n=1 is not a gradient, it's a single
    sample (see `reproducibility-first`).
    """
    import math

    eff = memory.get("skill_effectiveness", {})
    ranked: List[SkillSuggestion] = []
    insufficient: List[SkillSuggestion] = []
    for name, s in eff.items():
        n = s.get("n_invocations", 0)
        rel = s.get("delta_mean_relative", 0.0)
        absd = s.get("delta_mean_abs", 0.0)
        reg = s.get("regression_rate", 0.0)
        pla = s.get("plateau_rate", 0.0)
        if n < min_invocations:
            insufficient.append(
                SkillSuggestion(
                    skill=name,
                    delta_mean_relative=rel,
                    delta_mean_absolute=absd,
                    regression_rate=reg,
                    plateau_rate=pla,
                    n_invocations=n,
                    rank_score=0.0,
                    reason=f"insufficient data (n={n} < {min_invocations})",
                )
            )
            continue
        # Δ is expected negative (loss reduction); rank by magnitude of -Δ
        directional = -rel
        score = directional * (1.0 - reg) * (math.log(1 + n) / math.log(1 + 10))
        ranked.append(
            SkillSuggestion(
                skill=name,
                delta_mean_relative=rel,
                delta_mean_absolute=absd,
                regression_rate=reg,
                plateau_rate=pla,
                n_invocations=n,
                rank_score=score,
                reason=(
                    f"rel_Δ={rel:+.3f}  reg={reg:.1%}  pla={pla:.1%}  n={n}"
                ),
            )
        )
    ranked.sort(key=lambda s: -s.rank_score)
    return ranked[:top_n] + insufficient[:2]


# ---------------------------------------------------------------------------
# check — in-flight task warnings
# ---------------------------------------------------------------------------


@dataclass
class Warning:
    kind: str
    severity: str  # "info" | "warn" | "high"
    message: str


def _current_task_delta_streak(task: TaskSlice) -> int:
    """Consecutive plateau iterations at the tail of the in-flight task."""
    deltas: List[float] = []
    by_loop: Dict[str, List] = {}
    for e in task.iterations:
        by_loop.setdefault(e.loop, []).append(e)
    # Compute deltas for the most-recent loop
    if not by_loop:
        return 0
    most_recent_loop = task.iterations[-1].loop
    entries = by_loop[most_recent_loop]
    prev: Optional[float] = None
    for e in entries:
        cur = e.get_float("loss_norm", 0.0)
        if e.fields.get("baseline") == "true":
            prev = cur
            continue
        if prev is None:
            prev = cur
            continue
        deltas.append(cur - prev)
        prev = cur
    streak = 0
    for d in reversed(deltas):
        if abs(d) <= 0.005:
            streak += 1
        else:
            break
    return streak


def check_in_flight(
    memory: dict,
    current: Optional[TaskSlice],
    next_planned_skill: Optional[str] = None,
) -> List[Warning]:
    """Inspect the current task against project-memory. Returns warnings.

    This is the primary "memory helps optimization" surface — detects:
      - plateau: 2+ consecutive near-zero Δ
      - over-budget vs project-typical mean_k
      - next-planned skill is historically a bad bet at similar start-loss
    """
    warnings: List[Warning] = []
    if current is None:
        return warnings

    # Plateau detection
    streak = _current_task_delta_streak(current)
    if streak >= 2:
        # Sum all historical plateau-resolution buckets where the recorded
        # streak is ≥ the current streak. Rationale: a task that survived a
        # 3-plateau run and was resolved by skill X is ALSO evidence for
        # what resolves a 2-plateau run (the 3rd plateau subsumes the 2nd).
        # This avoids false-negatives on exact-key-match.
        plateau_patterns = memory.get("plateau_resolution_patterns", {})
        matched_n = 0
        matched_resolvers: Dict[str, int] = {}
        for key, info in plateau_patterns.items():
            # keys look like "after_N_consecutive_plateaus"
            try:
                key_streak = int(key.split("_")[1])
            except (ValueError, IndexError):
                continue
            if key_streak >= streak:
                matched_n += info.get("n_observed", 0)
                for resolver, cnt in info.get("resolver_skills", {}).items():
                    matched_resolvers[resolver] = (
                        matched_resolvers.get(resolver, 0) + cnt
                    )
        if matched_n > 0:
            top_resolvers = sorted(
                matched_resolvers.items(), key=lambda x: -x[1]
            )[:3]
            resolver_hint = ", ".join(f"{s} ({c})" for s, c in top_resolvers)
            warnings.append(
                Warning(
                    kind="plateau",
                    severity="high",
                    message=(
                        f"{streak} consecutive plateau iterations. "
                        f"Project-memory: past plateaus (streak ≥ {streak}) "
                        f"resolved by [{resolver_hint}] over {matched_n} observations."
                    ),
                )
            )
        else:
            warnings.append(
                Warning(
                    kind="plateau",
                    severity="warn",
                    message=(
                        f"{streak} consecutive plateau iterations. "
                        "No matching historical pattern; consider method-evolution."
                    ),
                )
            )

    # Over-budget check vs. project p95_k
    k = current.k_count
    shape = memory.get("task_shape", {}).get("overall", {})
    p95 = shape.get("p95_k", 0)
    mean = shape.get("mean_k", 0.0)
    if p95 and k >= p95 and not current.is_closed:
        warnings.append(
            Warning(
                kind="over_budget",
                severity="warn",
                message=(
                    f"Current k={k} at project p95 ({p95}). "
                    f"Mean_k={mean:.1f}. Probable escalation signal."
                ),
            )
        )

    # Next-planned skill historical regression rate
    if next_planned_skill:
        eff = memory.get("skill_effectiveness", {}).get(next_planned_skill)
        if eff and eff.get("n_invocations", 0) >= 3:
            reg = eff.get("regression_rate", 0.0)
            if reg >= 0.30:
                warnings.append(
                    Warning(
                        kind="wrong_decision",
                        severity="warn",
                        message=(
                            f"Planned skill '{next_planned_skill}' regresses "
                            f"{reg:.0%} of the time in this project "
                            f"(n={eff['n_invocations']}). Consider an alternative."
                        ),
                    )
                )

    return warnings


# ---------------------------------------------------------------------------
# similar — file-overlap retrieval
# ---------------------------------------------------------------------------


def similar_tasks(
    store: TraceStore,
    files: Sequence[str],
    top_n: int = 5,
    min_overlap: int = 1,
) -> List[Tuple[TaskSlice, float]]:
    """Rank completed tasks by Jaccard overlap on the `files=` field.

    If no past task has a `files=` field, returns empty. Embedding-based
    retrieval is explicitly out-of-scope (see v0.5.1 design decisions).
    """
    query = set(files)
    if not query:
        return []
    scored: List[Tuple[TaskSlice, float]] = []
    for t in store.completed_tasks():
        past_files: set = set()
        for e in t.iterations:
            f_str = e.fields.get("files", "")
            if f_str:
                past_files.update(f_str.split(","))
        if not past_files:
            continue
        overlap_set = query & past_files
        if len(overlap_set) < min_overlap:
            continue
        union = query | past_files
        jaccard = len(overlap_set) / len(union) if union else 0.0
        scored.append((t, jaccard))
    scored.sort(key=lambda x: -x[1])
    return scored[:top_n]


# ---------------------------------------------------------------------------
# health — human-readable summary
# ---------------------------------------------------------------------------


def format_health(memory: dict) -> str:
    """Render project-memory as a human-readable report (for `ldd_trace health`)."""
    lines: List[str] = []
    lines.append("╭─ LDD project health ─────────────────────────────────────────────╮")
    win = memory.get("window", {})
    lifetime = win.get("lifetime", {})
    lines.append(
        f"│ Tasks       : {lifetime.get('n_completed_tasks', 0)} completed, "
        f"{lifetime.get('n_in_progress_tasks', 0)} in-flight, "
        f"{lifetime.get('n_iterations', 0)} iterations total"
    )

    td = memory.get("terminal_distribution", {})
    if td:
        parts = [f"{name}={info['count']}({info['rate']:.0%})" for name, info in td.items()]
        lines.append("│ Terminals   : " + " · ".join(parts))

    shape = memory.get("task_shape", {}).get("overall", {})
    if shape.get("n"):
        lines.append(
            f"│ Task shape  : mean_k={shape['mean_k']} median_k={shape['median_k']} p95_k={shape['p95_k']}"
        )

    lines.append("│")
    lines.append("│ Skill effectiveness (sorted by rank_score):")
    suggestions = suggest_skills(memory, top_n=10)
    for s in suggestions:
        if s.n_invocations < 3:
            lines.append(f"│   {s.skill:<32}  {s.reason}")
        else:
            lines.append(
                f"│   {s.skill:<32}  rel_Δ={s.delta_mean_relative:+.3f}  "
                f"reg={s.regression_rate:.0%}  pla={s.plateau_rate:.0%}  n={s.n_invocations}"
            )

    plateau = memory.get("plateau_resolution_patterns", {})
    if plateau:
        lines.append("│")
        lines.append("│ Plateau-resolution patterns:")
        for key, info in plateau.items():
            top3 = sorted(info["resolver_skills"].items(), key=lambda x: -x[1])[:3]
            top3_str = ", ".join(f"{s}×{c}" for s, c in top3)
            lines.append(
                f"│   {key:<28}  n={info['n_observed']}  top_resolvers=[{top3_str}]"
            )

    lines.append("│")
    lines.append(
        "│ Bias guards : "
        + "; ".join(
            f"{k}: {v}" for k, v in memory.get("bias_guards", {}).items()
        )[:70]
        + "..."
    )
    lines.append("╰──────────────────────────────────────────────────────────────────╯")
    return "\n".join(lines)
