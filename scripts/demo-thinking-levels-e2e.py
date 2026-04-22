#!/usr/bin/env python3
"""End-to-end walkthrough for the thinking-levels dispatch system.

For every fixture prompt (9 canonical + 3 stress-tests), compute the full
scorer output — raw score, signals fired, auto-level, clamp reason,
creativity, dispatch source, final header, skill floor — and render a
single-file Markdown report. Used as a system-level verification that
the scorer + preset table + clamp rule + override parsing all agree
with the documented contract.

Usage:
    python scripts/demo-thinking-levels-e2e.py                  # stdout
    python scripts/demo-thinking-levels-e2e.py --out REPORT.md  # to file

Does NOT make any LLM calls; the scorer is deterministic. A sibling
capture-red-green-style integration test against a live LLM is a
separate, optional artifact.
"""
from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path

# Make scripts/ importable when invoked from repo root
sys.path.insert(0, str(Path(__file__).parent))

from level_scorer import (  # noqa: E402
    Creativity,
    DispatchSource,
    Level,
    has_implicit_ack,
    infer_creativity,
    score_task,
)


@dataclass(frozen=True)
class Scenario:
    name: str
    category: str  # "level" | "override" | "stress"
    prompt: str
    expected_level: Level | tuple[Level, ...]  # tuple if multiple accepted
    expected_source: DispatchSource
    expected_creativity: Creativity | None = None
    notes: str = ""


SKILL_FLOOR = {
    Level.L0: ["e2e-driven-iteration"],
    Level.L1: [
        "e2e-driven-iteration",
        "reproducibility-first",
        "root-cause-by-layer",
    ],
    Level.L2: [
        "e2e-driven-iteration",
        "reproducibility-first",
        "root-cause-by-layer",
        "dialectical-reasoning",
        "loss-backprop-lens",
        "docs-as-definition-of-done",
    ],
    Level.L3: [
        "e2e-driven-iteration",
        "reproducibility-first",
        "root-cause-by-layer",
        "dialectical-reasoning",
        "loss-backprop-lens",
        "docs-as-definition-of-done",
        "architect-mode (standard)",
        "drift-detection",
        "iterative-refinement",
    ],
    Level.L4: [
        "e2e-driven-iteration",
        "reproducibility-first",
        "root-cause-by-layer",
        "dialectical-reasoning",
        "loss-backprop-lens",
        "docs-as-definition-of-done",
        "architect-mode (inventive, ack-gated)",
        "drift-detection",
        "iterative-refinement",
        "method-evolution",
        "dialectical-cot",
        "define-metric",
    ],
}


SCENARIOS: list[Scenario] = [
    # 5 level scenarios — one per bucket
    Scenario(
        "L0-reflex",
        "level",
        'fix the typo in README.md line 12: "Agent Worklow" should be "Agent Workflow"',
        Level.L0,
        DispatchSource.AUTO,
        notes="Pure mechanical typo fix. Minimum skill floor.",
    ),
    Scenario(
        "L1-diagnostic",
        "level",
        "the unit test test_parser_handles_empty_input in packages/awp-core/tests/test_parser.py is failing after my last change; help me fix it",
        Level.L1,
        DispatchSource.AUTO,
        notes="Failing test + ambiguous origin → reproducibility-first is mandatory.",
    ),
    Scenario(
        "L2-deliberate",
        "level",
        "bump the confidence threshold default from 0.5 to 0.6 in the validator, and update any tests that expect the old value",
        Level.L2,
        DispatchSource.AUTO,
        notes="Magic-number change on a contract → dialectical pass mandatory.",
    ),
    Scenario(
        "L3-structural",
        "level",
        "we need to add a new critique gate for repair-fixpoint detection between the existing critique and deliverable_presence gates in the delegation loop; it should hook into the same R35 mechanism",
        Level.L3,
        DispatchSource.AUTO,
        Creativity.STANDARD,
        notes="Cross-layer additive work, architect/standard.",
    ),
    Scenario(
        "L4-method",
        "level",
        "design a new autonomy sublevel between A2 and A3 for manager-led recursive delegation with shared memory; greenfield, no known pattern fits directly, we want to prototype novel mechanisms",
        Level.L4,
        DispatchSource.AUTO,
        Creativity.INVENTIVE,
        notes="Greenfield + novel + prototype → inventive, ack-gated.",
    ),

    # 4 override scenarios
    Scenario(
        "override-up-from-L0",
        "override",
        "LDD++: fix the typo in README.md line 12",
        Level.L2,
        DispatchSource.USER_BUMP,
        notes="Scorer would say L0; user explicitly asked for +2.",
    ),
    Scenario(
        "override-max-on-simple",
        "override",
        "LDD=max: fix the typo in README.md line 12",
        Level.L4,
        DispatchSource.USER_BUMP,
        notes="Clamp-to-L4 regardless of scorer.",
    ),
    Scenario(
        "override-natural-language",
        "override",
        "take your time and think hard about this: rename the variable `foo` to `bar` in packages/awp-core/src/awp/cli.py",
        (Level.L1, Level.L2),
        DispatchSource.USER_BUMP,
        notes='"take your time" + "think hard" dedup to +1 → L2 (L1 also acceptable).',
    ),
    Scenario(
        "override-down-warning",
        "override",
        "LDD[level=L0]: we need to add a new critique gate for repair-fixpoint detection between the existing critique and deliverable_presence gates in the delegation loop; it should hook into the same R35 mechanism",
        Level.L0,
        DispatchSource.USER_OVERRIDE_DOWN,
        notes='User explicit L0 on a cross-layer task → "loss risk" warning fires.',
    ),

    # 3 stress-test scenarios — beyond the canonical fixture suite
    Scenario(
        "stress-inventive-implicit-ack",
        "stress",
        "design a novel consistency protocol for a multi-master KV store where no known pattern fits our partial-ordering requirements; we want to prototype experimental mechanisms and research the design space",
        (Level.L3, Level.L4),
        DispatchSource.AUTO,
        Creativity.INVENTIVE,
        notes=(
            "≥2 inventive cues + ≥100 chars → implicit ack path. "
            "Both L3 and L4 are GREEN: L4 if raw-score signals push the "
            "bucket there, L3 + creativity=inventive otherwise (same "
            "architect-mode + inventive loss function, smaller budget). "
            "This encodes orthogonality of level (rigor) and creativity (objective)."
        ),
    ),
    Scenario(
        "stress-zero-signal-baseline",
        "stress",
        "hello, can you help me out with this",
        Level.L2,
        DispatchSource.AUTO,
        notes='Zero-signal chit-chat → baseline L2, not L0. Encodes "lieber schlau als zu dumm".',
    ),
    Scenario(
        "stress-L4-clamp-on-high-score-standard",
        "stress",
        "design a new service integration across the orchestration layer and the observability layer, covering the runner, scorer, and manager; wire it into the delegation loop and honor R17",
        Level.L3,
        DispatchSource.AUTO,
        Creativity.STANDARD,
        notes="Raw score ≥ 8 (L4 bucket) BUT no inventive cues → creativity-clamp fires back to L3.",
    ),
]


def _fmt_level(level: Level | tuple[Level, ...]) -> str:
    if isinstance(level, tuple):
        return " or ".join(l.value for l in level)
    return level.value


def _check_level(actual: Level, expected: Level | tuple[Level, ...]) -> bool:
    if isinstance(expected, tuple):
        return actual in expected
    return actual == expected


def run_scenario(s: Scenario) -> tuple[str, bool]:
    """Run the scorer on scenario `s` and return (markdown_block, passed)."""
    r = score_task(s.prompt)
    level_ok = _check_level(r.final_level, s.expected_level)
    source_ok = r.dispatch_source == s.expected_source
    creativity_ok = (
        s.expected_creativity is None or r.creativity == s.expected_creativity
    )
    passed = level_ok and source_ok and creativity_ok
    status = "✅ PASS" if passed else "❌ FAIL"

    # Compute implicit ack flag for inventive cases
    implicit_ack_note = ""
    if r.creativity == Creativity.INVENTIVE:
        if has_implicit_ack(s.prompt):
            implicit_ack_note = (
                " (implicit ack from ≥2 inventive cues in prompt)"
            )
        else:
            implicit_ack_note = " (explicit ack required before activation)"

    signals_str = ", ".join(
        f"{sig.name}={'+' if sig.weight >= 0 else ''}{sig.weight}"
        for sig in r.top_signals(n=len(r.signals_fired))
    ) or "(none)"

    floor = SKILL_FLOOR[r.final_level]

    block = f"""
### {s.name} — {status}

**Category:** {s.category}
**Prompt:**
> {s.prompt}

**Scorer output:**
- Raw score: `{r.raw_score}`
- Signals fired: `{signals_str}`
- Auto-level: `{r.auto_level.value}`
- Final level: `{r.final_level.value}` *(expected: {_fmt_level(s.expected_level)} — {'✓' if level_ok else '✗'})*
- Dispatch source: `{r.dispatch_source.value}` *(expected: {s.expected_source.value} — {'✓' if source_ok else '✗'})*
- Creativity: `{r.creativity.value}`{implicit_ack_note}{' *(expected: ' + s.expected_creativity.value + ' — ' + ('✓' if creativity_ok else '✗') + ')*' if s.expected_creativity else ''}
- Clamp reason: `{r.clamp_reason or 'none'}`
- Override fragment: `{r.override_fragment or 'none'}`

**Dispatch header emitted:**
```
{r.dispatch_header()}
"""
    # v0.11.0: the second `mode: architect, creativity: …` line is gone.
    # `mode` is derived from level; the creativity is already echoed inline
    # in `dispatch_header()` for L3/L4. Nothing more to append here.
    block += "```\n\n"

    block += f"**Skill floor invoked (minimum):**\n"
    for skill in floor:
        block += f"- `{skill}`\n"
    if s.notes:
        block += f"\n**Notes:** {s.notes}\n"

    return block, passed


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=None, help="Write report to file (default: stdout)")
    args = ap.parse_args()

    header = [
        "# Thinking-levels E2E walkthrough",
        "",
        "Deterministic system-level verification that the scorer + preset table + ",
        "clamp rule + override parsing agree with `docs/ldd/thinking-levels.md` ",
        "and `skills/using-ldd/SKILL.md` § Auto-dispatch: thinking-levels.",
        "",
        "No LLM call; the scorer is deterministic. 12 scenarios — 5 level, 4 override, 3 stress.",
        "",
    ]

    blocks = []
    passes = 0
    total = len(SCENARIOS)
    category_breakdown: dict[str, tuple[int, int]] = {"level": (0, 0), "override": (0, 0), "stress": (0, 0)}

    for s in SCENARIOS:
        block, passed = run_scenario(s)
        blocks.append(block)
        if passed:
            passes += 1
            p, t = category_breakdown[s.category]
            category_breakdown[s.category] = (p + 1, t + 1)
        else:
            p, t = category_breakdown[s.category]
            category_breakdown[s.category] = (p, t + 1)

    summary = [
        "## Summary",
        "",
        f"**{passes} / {total} scenarios passed.**",
        "",
        "| Category | Passed | Total |",
        "|---|---|---|",
    ]
    for cat in ("level", "override", "stress"):
        p, t = category_breakdown[cat]
        summary.append(f"| {cat} | {p} | {t} |")
    summary.append("")
    if passes == total:
        summary.append("All scenarios green. The dispatch system is consistent end-to-end.")
    else:
        summary.append(
            f"**{total - passes} scenario(s) failed** — inspect the blocks below and "
            "tune the scorer weights or fixture expectations. Per asymmetric-loss, "
            "prefer tuning toward fixing low-side failures first."
        )
    summary.append("")

    report = "\n".join(header) + "\n".join(summary) + "\n" + "\n".join(blocks)

    if args.out:
        Path(args.out).write_text(report)
        print(f"Wrote report to {args.out} ({passes}/{total} passed)", file=sys.stderr)
    else:
        print(report)

    return 0 if passes == total else 1


if __name__ == "__main__":
    sys.exit(main())
