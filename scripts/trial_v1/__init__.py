"""LDD-Trial-v1 — open-science RCT to measure LDD's effect on a coding agent.

Namespace layout:

    power_analysis   sample-size math (Cohen's h, two-proportion z-test, sensitivity curves)
    judge            blind cross-model judge prompt builder (no API call — produces the prompt)
    placebo_arm      three-arm harness record: T_baseline, T_LDD, T_placebo
    analyze          bootstrap CIs, two-proportion tests, linear mixed model proxy
    run_mini         synthetic orchestrator that walks a small N through all three arms
                     so the mechanics are runnable without burning API credits

Public entry points are exposed here so `from trial_v1 import …` works; heavy
imports stay lazy.
"""
from __future__ import annotations

__all__ = [
    "power_analysis",
    "judge",
    "placebo_arm",
    "analyze",
]
