"""Blind cross-model judge — builds the pre-registered prompt.

This module DOES NOT call an LLM. It emits the exact prompt string that will
be sent to GPT-4o / Claude-Sonnet / Gemini / Qwen so third parties can
replay the same judgment pipeline. The prompt is pre-registered; any change
bumps the `VERSION` constant and is a separate trial.

Pre-registered protocol:

    1. Each `TaskPair` carries two fixes A and B produced by two different
       arms of the RCT (T_baseline / T_LDD / T_placebo). The arm assignment
       is hidden from the judge.

    2. A / B order is randomized per pair so the judge cannot infer arms
       from position.

    3. The judge receives: task description, diff A, diff B, target test
       output, and a fixed rubric. Nothing about LDD, nothing about the
       plugin, no mention of "which arm is which".

    4. The judge returns one of {"A", "B", "tie"} plus a one-sentence
       rationale. Ties are counted separately — they are NOT split 50/50.

    5. Three judges (three different model families) vote independently.
       Primary aggregate: majority vote; secondary: per-model win rate.

The null hypothesis the judge-arm tests:
    H0:  P(judge picks T_LDD | {T_LDD, T_baseline}) = 0.5
    H1:  P(judge picks T_LDD | {T_LDD, T_baseline}) > 0.5

Rejected if the 95 %-CI (Wilson) excludes 0.5. Binomial power calc lives
in `power_analysis.required_n_per_arm(p1=0.5, p2=0.60)` → ≈ 389 pairs to
detect a 10-pp lift.
"""
from __future__ import annotations

import hashlib
import random
from dataclasses import dataclass
from typing import Literal, Optional


VERSION = "v1.0.0"          # bump on any prompt change — it's a DIFFERENT trial
JUDGE_MAX_TOKENS = 512      # judge reply must be short; rationale ≤ 1 sentence


JUDGE_SYSTEM = """\
You are a senior software engineer reviewing patches for merge.

You will see ONE task description and TWO candidate patches labeled A and B.
You do not know which team produced which patch. Your job is to pick the one
you would merge, on the merits of the code alone.

Review criteria (in decreasing priority):
  1. Correctness — does it actually fix the reported issue?
  2. No regression — no other reasonable behavior appears to break.
  3. Fix depth — the patch addresses a root cause, not only the symptom.
     A symptom patch that works (e.g. a targeted try/except) loses to a
     structural fix that addresses the invariant.
  4. Commit hygiene — tests updated; documentation / changelog updated when
     the change is user-visible.
  5. Readability — the reviewer understands the intent without context.

If the two patches are genuinely indistinguishable on the above, reply
"tie". Do NOT reply "tie" merely because you are uncertain — uncertainty
picks the lower-risk of the two.

Reply in EXACTLY this format:
    VERDICT: <A | B | tie>
    REASON: <one sentence>
"""


@dataclass(frozen=True)
class TaskPair:
    task_id: str
    task_description: str
    diff_a: str
    diff_b: str
    target_test_output: str
    # Hidden metadata — the judge sees ONLY the above fields. These travel
    # with the pair so the analyzer can re-link verdicts to arms AFTER
    # scoring.
    arm_a: Literal["T_LDD", "T_baseline", "T_placebo"]
    arm_b: Literal["T_LDD", "T_baseline", "T_placebo"]


@dataclass(frozen=True)
class JudgePrompt:
    system: str
    user: str
    # Hash of the user prompt — used in the analysis step to verify the
    # judge received the exact pre-registered text (no silent prompt drift).
    content_hash: str


def build_prompt(pair: TaskPair) -> JudgePrompt:
    """Compose the judge prompt for one pair. Deterministic given the pair."""
    user = (
        f"# Task\n\n{pair.task_description}\n\n"
        f"# Target test output (before either patch)\n\n"
        f"```\n{pair.target_test_output}\n```\n\n"
        f"# Patch A\n\n```diff\n{pair.diff_a}\n```\n\n"
        f"# Patch B\n\n```diff\n{pair.diff_b}\n```\n\n"
        f"Which patch would you merge? Use the format specified in the system prompt."
    )
    h = hashlib.sha256(user.encode("utf-8")).hexdigest()[:16]
    return JudgePrompt(system=JUDGE_SYSTEM, user=user, content_hash=h)


def randomize_order(pair: TaskPair, seed: Optional[int] = None) -> TaskPair:
    """Return a pair with A/B possibly swapped based on a deterministic seed.

    Pre-registered: order is swapped iff sha256(task_id||seed)%2==1. This
    makes the flip reproducible and auditable without needing to trust the
    RNG of the machine that runs the trial.
    """
    rng = random.Random()
    if seed is None:
        seed_key = pair.task_id
    else:
        seed_key = f"{pair.task_id}|{seed}"
    rng.seed(int(hashlib.sha256(seed_key.encode("utf-8")).hexdigest(), 16) & 0xFFFFFFFF)
    if rng.random() < 0.5:
        return TaskPair(
            task_id=pair.task_id,
            task_description=pair.task_description,
            diff_a=pair.diff_b,
            diff_b=pair.diff_a,
            target_test_output=pair.target_test_output,
            arm_a=pair.arm_b,
            arm_b=pair.arm_a,
        )
    return pair


@dataclass(frozen=True)
class JudgeVerdict:
    """What a judge returned, parsed from its reply."""
    task_id: str
    judge_model: str
    verdict: Literal["A", "B", "tie"]
    reason: str


def parse_reply(task_id: str, judge_model: str, reply: str) -> Optional[JudgeVerdict]:
    """Parse a judge reply into a JudgeVerdict. Returns None on malformed input.

    Tolerant to whitespace / case; strict on the VERDICT: prefix to prevent
    prompt-injection laundering (a judge that smuggles arbitrary text must
    still follow the machine-readable envelope).
    """
    verdict: Optional[str] = None
    reason = ""
    for line in reply.splitlines():
        stripped = line.strip()
        if stripped.upper().startswith("VERDICT:"):
            v = stripped.split(":", 1)[1].strip().lower()
            if v in {"a", "b", "tie"}:
                verdict = {"a": "A", "b": "B", "tie": "tie"}[v]
        elif stripped.upper().startswith("REASON:"):
            reason = stripped.split(":", 1)[1].strip()
    if verdict is None:
        return None
    return JudgeVerdict(
        task_id=task_id,
        judge_model=judge_model,
        verdict=verdict,          # type: ignore[arg-type]
        reason=reason,
    )


def winner_arm(pair: TaskPair, verdict: JudgeVerdict) -> Optional[str]:
    """Map A/B verdict back to the arm that produced the winning patch."""
    if verdict.verdict == "tie":
        return None
    return pair.arm_a if verdict.verdict == "A" else pair.arm_b
