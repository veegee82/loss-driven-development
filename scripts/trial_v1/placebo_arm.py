"""Three-arm treatment-assignment harness for LDD-Trial-v1.

The three arms answer three DIFFERENT causal questions; keeping them all
in one RCT is what makes the Placebo contrast load-bearing:

    T_baseline   Claude Code with NO LDD plugin, NO `LDD:` prefix, and a
                 dummy `CLAUDE.md` of equal length to the LDD one (to
                 control for file-length priming effects).

    T_LDD        Claude Code with the LDD plugin installed AND the `LDD:`
                 prefix added to the task. Full discipline.

    T_placebo    Claude Code WITHOUT the LDD plugin installed but WITH the
                 `LDD:` prefix on the task, and the same dummy CLAUDE.md
                 as T_baseline. Tests the "prompt-priming" null hypothesis:
                 does the literal prefix change behavior by itself, even
                 when the plugin code never loads?

Pre-registered interpretation matrix:

    T_LDD wins over T_baseline   AND   T_LDD wins over T_placebo:
        → LDD's measured effect is load-bearing on the skill discipline,
          not reducible to prompt-priming.

    T_LDD wins over T_baseline   BUT   T_LDD ≈ T_placebo:
        → The effect is prompt-priming, not skill discipline. LDD's claim
          of being "gradient descent for agents" is refuted for this
          distribution; the plugin is placebo-grade.

    T_LDD ≈ T_baseline:
        → LDD has no effect on this distribution.

The module's only job is (a) compose the correct prompt per arm and (b)
emit a structured record of which arm ran. It does NOT call an LLM; that's
the trial runner's job.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Literal, Optional


ARM = Literal["T_baseline", "T_LDD", "T_placebo"]


# Pre-registered dummy CLAUDE.md. The exact byte-length is matched to the
# project's real CLAUDE.md at trial-setup time; this constant is the
# baseline content both T_baseline and T_placebo see. Keeping the file
# byte-equivalent to the LDD one (padding a comment block) removes
# file-length priming as a confounder.
DUMMY_CLAUDE_MD_HEADER = (
    "# CLAUDE.md — neutral instructions\n\n"
    "This file is intentionally generic. Follow good software-engineering "
    "practices: tests pass, code is readable, commits are atomic. No "
    "specific methodology is imposed here.\n"
)


# Pre-registered task prefix per arm.
ARM_PREFIX = {
    "T_baseline": "",  # no prefix
    "T_LDD":      "LDD: ",
    "T_placebo":  "LDD: ",
}


# Pre-registered plugin flag per arm. The RCT runner is expected to spawn
# its Claude-Code subprocess with LDD plugin enabled ⇔ this flag is True.
ARM_LDD_LOADED = {
    "T_baseline": False,
    "T_LDD":      True,
    "T_placebo":  False,
}


@dataclass(frozen=True)
class ArmAssignment:
    """One row in the pre-registered arm ledger.

    Every Task × seed × arm combination produces exactly one ArmAssignment
    record before the run starts; the record is hashed so arm reassignment
    post-hoc is detectable (would change the integrity hash).
    """

    task_id: str
    seed: int
    arm: ARM
    assigned_at: str                  # ISO-8601 UTC
    integrity_hash: str               # sha256(task_id|seed|arm|assigned_at)[:16]


def integrity(task_id: str, seed: int, arm: ARM, assigned_at: str) -> str:
    payload = f"{task_id}|{seed}|{arm}|{assigned_at}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def assign_arm(task_id: str, seed: int, arm: ARM) -> ArmAssignment:
    """Record an arm assignment with a timestamp and integrity hash."""
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return ArmAssignment(
        task_id=task_id,
        seed=seed,
        arm=arm,
        assigned_at=ts,
        integrity_hash=integrity(task_id, seed, arm, ts),
    )


@dataclass(frozen=True)
class ArmRun:
    """A prepared prompt + config for one Task × arm."""

    task_id: str
    arm: ARM
    prompt: str
    ldd_plugin_loaded: bool
    claude_md_content: str


def prepare_run(task_id: str, arm: ARM, task_text: str, claude_md_body: str) -> ArmRun:
    """Compose the prompt + config a runner will hand to Claude Code.

    The `claude_md_body` differs per arm:
      * T_LDD:       the real LDD CLAUDE.md
      * T_baseline:  the pre-registered dummy (length-matched)
      * T_placebo:   the same dummy
    """
    prefix = ARM_PREFIX[arm]
    prompt = f"{prefix}{task_text}" if prefix else task_text
    return ArmRun(
        task_id=task_id,
        arm=arm,
        prompt=prompt,
        ldd_plugin_loaded=ARM_LDD_LOADED[arm],
        claude_md_content=claude_md_body,
    )


def pad_claude_md_to_match(real_md: str, header: str = DUMMY_CLAUDE_MD_HEADER) -> str:
    """Return a dummy CLAUDE.md byte-length-matched to `real_md`.

    Pads with a comment block of neutral filler so file-length confounders
    cannot explain any arm difference. The filler is pre-registered text
    (this function's source IS the registration).
    """
    target_len = len(real_md.encode("utf-8"))
    base = header.encode("utf-8")
    if len(base) >= target_len:
        return header[:target_len]
    padding_source = (
        "\n<!-- padding to match real CLAUDE.md byte length for "
        "file-length-priming control -->\n"
    )
    out = header
    while len(out.encode("utf-8")) < target_len:
        out += padding_source
    # Trim to exact target (byte-wise).
    encoded = out.encode("utf-8")[:target_len]
    # Decoding byte-trimmed utf-8 can hit a partial codepoint; loop back a
    # few bytes if so.
    for cut in range(0, 4):
        try:
            return encoded[: target_len - cut].decode("utf-8")
        except UnicodeDecodeError:
            continue
    return header       # pragma: no cover — reachable only for degenerate inputs
