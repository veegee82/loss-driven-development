"""Memory-informed antithesis priming — v0.6.0.

Bridges `dialectical-reasoning` (Hessian-probing) with `ldd_trace` project
memory (1st-moment, bias-guarded). Memory feeds STRUCTURED EVIDENCE into the
antithesis generation step, so the dialectical pass starts with domain-
specific counter-cases instead of generic ones.

SGD framing:
    - memory provides 1st-order information (past Δloss / failure-rate stats)
    - dialectical provides 2nd-order information (local Hessian via
      adversarial probing of the current thesis)
    - together they approach a Bayesian update on action-confidence:

        confidence(action) ∝ memory_likelihood × dialectical_likelihood

**Bias invariant**: priming does NOT assign weights or rank antitheses. It
surfaces evidence; the dialectical pass decides what's load-bearing. The
loss function L(θ) is untouched.

Agent contract: when using primed antitheses, the dialectical skill MUST
additionally generate ≥ 1 antithesis that is NOT from the primer — to
avoid "groupthink" where memory-sourced counter-cases crowd out
novel reasoning. See `skills/dialectical-reasoning/SKILL.md` §
"Memory-informed antithesis generation".
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from ldd_trace.retrieval import _current_task_delta_streak
from ldd_trace.store import TaskSlice, TraceStore


# Thesis-keyword → skill-name matcher. Simple first-pass: if a thesis
# mentions a skill name verbatim, assume it's the primary candidate.
# Alternatives (fuzzy match / LLM extract) are deferred — this keeps the
# primer deterministic and testable.

def _extract_candidate_skill(thesis: str, memory: dict) -> Optional[str]:
    thesis_lower = thesis.lower()
    candidates = memory.get("skill_effectiveness", {}).keys()
    for name in candidates:
        if name.lower() in thesis_lower:
            return name
    return None


@dataclass
class Primer:
    """One unit of antithesis material.

    Attributes:
        source   — which memory signal fed this primer
        severity — "high" / "warn" / "info"; informs how prominently the
                   dialectical pass should address it
        material — the counter-case phrased as a question/challenge
        evidence — where the claim comes from (for transparency)
    """

    source: str
    severity: str
    material: str
    evidence: str


@dataclass
class AntithesisMaterial:
    thesis: str
    primers: List[Primer] = field(default_factory=list)
    summary: str = ""

    @property
    def has_signal(self) -> bool:
        return bool(self.primers)


# ---------------------------------------------------------------------------
# Priming — the core routine
# ---------------------------------------------------------------------------


def prime_antithesis(
    memory: dict,
    thesis: str,
    current: Optional[TaskSlice] = None,
    files: Optional[List[str]] = None,
    store: Optional[TraceStore] = None,
) -> AntithesisMaterial:
    """Generate antithesis primers from project memory.

    Primer sources (in priority order):
      1. skill_failure_mode   — thesis names a skill with high reg/plateau rate
      2. plateau_pattern      — in-flight streak ≥ 2 and historical resolvers differ
      3. similar_task         — prior completed tasks with file-overlap
      4. terminal_analysis    — project's non-complete rate ≥ 15%
      5. regression_context   — thesis at high starting_loss vs. skill's low-loss comfort

    Each primer is phrased as a *question* the antithesis must answer —
    the dialectical pass still does the reasoning; memory just loads the gun.
    """
    primers: List[Primer] = []

    # --- Primer 1: skill failure mode --------------------------------
    skill = _extract_candidate_skill(thesis, memory)
    if skill:
        stats = memory.get("skill_effectiveness", {}).get(skill, {})
        n = stats.get("n_invocations", 0)
        reg = stats.get("regression_rate", 0.0)
        pla = stats.get("plateau_rate", 0.0)
        if n >= 3 and (reg + pla) >= 0.30:
            by_terminal = stats.get("by_terminal", {})
            terminal_hint = ""
            if by_terminal:
                term_parts = [
                    f"{t}:{info.get('n', 0)}" for t, info in by_terminal.items()
                ]
                terminal_hint = f" (outcomes: {', '.join(term_parts)})"
            primers.append(
                Primer(
                    source="skill_failure_mode",
                    severity="warn" if (reg + pla) < 0.6 else "high",
                    material=(
                        f"Skill `{skill}` has a {reg + pla:.0%} no-progress rate "
                        f"in this project (reg={reg:.0%}, pla={pla:.0%}, n={n})"
                        f"{terminal_hint}. If thesis hits that failure mode this "
                        "time, what happens — and is thesis equipped to detect it?"
                    ),
                    evidence=(
                        f"skill_effectiveness['{skill}']: "
                        f"regression_rate={reg:.3f}, plateau_rate={pla:.3f}, n={n}"
                    ),
                )
            )

    # --- Primer 2: in-flight plateau pattern -------------------------
    if current is not None:
        streak = _current_task_delta_streak(current)
        if streak >= 2:
            patterns = memory.get("plateau_resolution_patterns", {})
            aggregated_resolvers: dict = {}
            total_n = 0
            for key, info in patterns.items():
                try:
                    key_streak = int(key.split("_")[1])
                except (ValueError, IndexError):
                    continue
                if key_streak >= streak:
                    total_n += info.get("n_observed", 0)
                    for resolver, cnt in info.get("resolver_skills", {}).items():
                        aggregated_resolvers[resolver] = (
                            aggregated_resolvers.get(resolver, 0) + cnt
                        )
            if aggregated_resolvers:
                top = sorted(aggregated_resolvers.items(), key=lambda x: -x[1])[:3]
                top_str = ", ".join(f"`{s}`×{c}" for s, c in top)
                primers.append(
                    Primer(
                        source="plateau_pattern",
                        severity="high",
                        material=(
                            f"Current plateau streak={streak}. Historical "
                            f"resolvers at this streak level are [{top_str}] "
                            f"(n={total_n}). Does thesis pivot to one of those — "
                            f"or continue same-layer? If same-layer, why would it "
                            f"break the plateau this time?"
                        ),
                        evidence=(
                            f"plateau_resolution_patterns; aggregated over keys "
                            f"with streak ≥ {streak}"
                        ),
                    )
                )
            else:
                primers.append(
                    Primer(
                        source="plateau_pattern",
                        severity="warn",
                        material=(
                            f"Current plateau streak={streak}. No historical "
                            "resolver pattern in this project — unprecedented. "
                            "Does thesis acknowledge it's unusual or treat it "
                            "as routine?"
                        ),
                        evidence="plateau_resolution_patterns: empty or no match",
                    )
                )

    # --- Primer 3: similar tasks via file overlap --------------------
    if files and store is not None:
        from ldd_trace.retrieval import similar_tasks as _sim

        matches = _sim(store, files, top_n=3, min_overlap=1)
        if matches:
            top = matches[0]
            task_slice, jaccard = top
            terminal = task_slice.terminal or "in-flight"
            title = (
                task_slice.meta.fields.get("task", "(no title)")
                if task_slice.meta
                else "(no meta)"
            )
            if terminal != "complete" and jaccard >= 0.3:
                primers.append(
                    Primer(
                        source="similar_task",
                        severity="warn",
                        material=(
                            f"Most-similar past task (jaccard={jaccard:.2f}) was "
                            f'"{title}" — terminal={terminal}. What made that '
                            "task NOT close, and does thesis share the same risk?"
                        ),
                        evidence=f"similar_tasks file-overlap={jaccard:.3f}",
                    )
                )

    # --- Primer 4: project's non-complete rate -----------------------
    td = memory.get("terminal_distribution", {})
    non_complete_n = sum(
        v["count"] for k, v in td.items() if k != "complete"
    )
    total_n = sum(v["count"] for v in td.values())
    if total_n >= 5 and non_complete_n / total_n > 0.15:
        primers.append(
            Primer(
                source="terminal_analysis",
                severity="info",
                material=(
                    f"Project non-complete rate is "
                    f"{non_complete_n / total_n:.0%} (n={total_n} completed tasks). "
                    "What defenses does thesis carry against the typical failure "
                    "modes observed here (partial/aborted/failed)?"
                ),
                evidence=(
                    f"terminal_distribution: "
                    f"{non_complete_n}/{total_n} non-complete"
                ),
            )
        )

    # --- Summary -----------------------------------------------------
    if not primers:
        summary = (
            "Memory has insufficient signal to prime antithesis. "
            "Run the standard dialectical pass with generic counter-cases."
        )
    else:
        sev_counts: dict = {}
        for p in primers:
            sev_counts[p.severity] = sev_counts.get(p.severity, 0) + 1
        sev_str = " · ".join(
            f"{k}={v}" for k, v in sorted(sev_counts.items())
        )
        summary = (
            f"Generated {len(primers)} antithesis primers from project memory "
            f"[{sev_str}]. Dialectical pass MUST address each in its counter-"
            "argument section; synthesis MUST reconcile or reject each. Additionally, "
            "produce ≥ 1 antithesis NOT sourced from these primers to guard "
            "against memory-groupthink."
        )

    return AntithesisMaterial(thesis=thesis, primers=primers, summary=summary)


# ---------------------------------------------------------------------------
# Formatter
# ---------------------------------------------------------------------------


_SEV_MARKER = {"high": "⚠⚠", "warn": "⚠", "info": "ℹ"}


def format_antithesis_material(material: AntithesisMaterial) -> str:
    lines: List[str] = []
    lines.append("╭─ Memory-primed antithesis material ──────────────────────────────╮")
    lines.append(f"│ Thesis     : {material.thesis}")
    lines.append("│")
    # Wrap summary at ~70 chars
    words = material.summary.split()
    line_buf = "│ Summary    : "
    for w in words:
        if len(line_buf) + len(w) + 1 > 70:
            lines.append(line_buf)
            line_buf = "│              " + w
        else:
            line_buf = line_buf + (" " if line_buf[-1] != " " else "") + w
    lines.append(line_buf)
    lines.append("│")
    if not material.primers:
        lines.append("│ (no primers — project memory lacks signal for this thesis)")
    else:
        for i, p in enumerate(material.primers, 1):
            marker = _SEV_MARKER.get(p.severity, "·")
            lines.append(f"│ {marker} Primer {i}  [{p.source} · {p.severity}]")
            # Wrap material
            buf = "│    material: "
            for w in p.material.split():
                if len(buf) + len(w) + 1 > 68:
                    lines.append(buf)
                    buf = "│              " + w
                else:
                    buf = buf + (" " if buf[-1] != " " else "") + w
            lines.append(buf)
            lines.append(f"│    evidence: {p.evidence}")
            lines.append("│")
    lines.append("│ Agent contract — dialectical-reasoning + memory-priming (v0.6.0):")
    lines.append("│   1. Each primer above becomes a required antithesis point.")
    lines.append("│   2. Generate ≥ 1 additional antithesis NOT sourced from primers.")
    lines.append("│   3. Synthesis MUST explicitly reconcile or reject each point.")
    lines.append("│   4. Emit trace via `ldd_trace append` after the iteration closes.")
    lines.append("╰──────────────────────────────────────────────────────────────────╯")
    return "\n".join(lines)
