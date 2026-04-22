"""Tests for the LDD-Trial-v1 analysis pipeline."""
from __future__ import annotations

import json
import math
from pathlib import Path

import pytest

from trial_v1 import analyze, judge, placebo_arm, power_analysis, run_mini


# ---------------------------------------------------------------------------
# power_analysis
# ---------------------------------------------------------------------------


class TestPowerAnalysis:
    def test_cohen_h_zero_when_equal(self) -> None:
        assert power_analysis.cohen_h(0.5, 0.5) == 0.0

    def test_cohen_h_sign(self) -> None:
        # p1 > p2 → positive h
        assert power_analysis.cohen_h(0.6, 0.4) > 0

    def test_required_n_shrinks_for_larger_effect(self) -> None:
        n_small = power_analysis.required_n_per_arm(0.50, 0.55)
        n_big   = power_analysis.required_n_per_arm(0.50, 0.70)
        assert n_big < n_small

    def test_required_n_benchmark(self) -> None:
        """The pre-reg cites N ≈ 168-170 per arm for p=(0.50, 0.65) @ α=0.05, β=0.80.

        Using the pooled-variance formula with the hard-coded z-table:
          z_{0.025} = 1.96, z_{0.80} = 0.8416
          n = (2.8016)² * 2 * 0.575 * 0.425 / 0.0225  ≈  171
        """
        n = power_analysis.required_n_per_arm(0.50, 0.65, alpha=0.05, power=0.80)
        assert 160 <= n <= 180

    def test_effect_size_labels(self) -> None:
        assert power_analysis.effect_size_label(0.05)  == "negligible"
        assert power_analysis.effect_size_label(0.25)  == "small"
        assert power_analysis.effect_size_label(0.60)  == "medium"
        assert power_analysis.effect_size_label(1.00)  == "large"

    def test_power_curve_shape(self) -> None:
        curve = power_analysis.power_curve(0.42, [0.50, 0.60, 0.70])
        assert len(curve) == 3
        # Larger p2 → smaller required N (greater sensitivity).
        assert curve[0].n_per_arm > curve[-1].n_per_arm


# ---------------------------------------------------------------------------
# judge
# ---------------------------------------------------------------------------


class TestJudge:
    def _pair(self, arm_a: str = "T_LDD", arm_b: str = "T_baseline") -> judge.TaskPair:
        return judge.TaskPair(
            task_id="t1",
            task_description="add handling for empty list input",
            diff_a="--- a\n+++ b\n+ if not xs: return []\n",
            diff_b="--- a\n+++ b\n+ try: return xs[0]\n+ except IndexError: return []\n",
            target_test_output="FAIL: test_empty_returns_empty",
            arm_a=arm_a, arm_b=arm_b,
        )

    def test_prompt_is_deterministic(self) -> None:
        p = self._pair()
        prompt1 = judge.build_prompt(p)
        prompt2 = judge.build_prompt(p)
        assert prompt1.content_hash == prompt2.content_hash

    def test_prompt_hash_changes_when_diff_changes(self) -> None:
        p1 = self._pair()
        p2 = judge.TaskPair(**{**p1.__dict__, "diff_a": p1.diff_a + "\n# extra"})
        assert judge.build_prompt(p1).content_hash != judge.build_prompt(p2).content_hash

    def test_randomize_order_deterministic_per_task_id(self) -> None:
        p = self._pair()
        r1 = judge.randomize_order(p, seed=1)
        r2 = judge.randomize_order(p, seed=1)
        assert (r1.arm_a, r1.arm_b) == (r2.arm_a, r2.arm_b)

    def test_randomize_order_differs_by_seed(self) -> None:
        p = self._pair()
        # Different seeds should eventually produce both orderings across many tasks;
        # we assert the function at least changes output for SOME seed.
        orderings = {
            (judge.randomize_order(p, seed=s).arm_a,
             judge.randomize_order(p, seed=s).arm_b)
            for s in range(20)
        }
        assert len(orderings) == 2  # both ⟨LDD, baseline⟩ and ⟨baseline, LDD⟩ occur

    def test_parse_reply_verdict(self) -> None:
        v = judge.parse_reply("t1", "gpt-4o",
            "VERDICT: A\nREASON: fixes root cause; B uses try/except")
        assert v is not None
        assert v.verdict == "A"
        assert "root cause" in v.reason

    def test_parse_reply_tie(self) -> None:
        v = judge.parse_reply("t1", "gpt-4o", "VERDICT: tie\nREASON: same behaviour")
        assert v is not None and v.verdict == "tie"

    def test_parse_reply_malformed(self) -> None:
        assert judge.parse_reply("t1", "gpt-4o", "I think A is better") is None

    def test_winner_arm_a(self) -> None:
        p = self._pair(arm_a="T_LDD", arm_b="T_baseline")
        v = judge.JudgeVerdict(task_id="t1", judge_model="gpt-4o", verdict="A", reason="")
        assert judge.winner_arm(p, v) == "T_LDD"

    def test_winner_tie_is_none(self) -> None:
        p = self._pair()
        v = judge.JudgeVerdict(task_id="t1", judge_model="gpt-4o", verdict="tie", reason="")
        assert judge.winner_arm(p, v) is None


# ---------------------------------------------------------------------------
# placebo_arm
# ---------------------------------------------------------------------------


class TestPlaceboArm:
    def test_prefix_per_arm(self) -> None:
        assert placebo_arm.ARM_PREFIX["T_baseline"] == ""
        assert placebo_arm.ARM_PREFIX["T_LDD"]      == "LDD: "
        assert placebo_arm.ARM_PREFIX["T_placebo"]  == "LDD: "

    def test_plugin_flag_per_arm(self) -> None:
        assert placebo_arm.ARM_LDD_LOADED["T_baseline"] is False
        assert placebo_arm.ARM_LDD_LOADED["T_LDD"]      is True
        assert placebo_arm.ARM_LDD_LOADED["T_placebo"]  is False

    def test_placebo_differs_from_ldd_only_in_plugin_flag(self) -> None:
        """The load-bearing contrast: same prompt prefix, different plugin state."""
        task = "fix the empty-list bug"
        ldd = placebo_arm.prepare_run("t1", "T_LDD", task, "dummy")
        placebo = placebo_arm.prepare_run("t1", "T_placebo", task, "dummy")
        assert ldd.prompt == placebo.prompt  # same prefix
        assert ldd.ldd_plugin_loaded != placebo.ldd_plugin_loaded

    def test_assign_arm_integrity_hash(self) -> None:
        a = placebo_arm.assign_arm("t1", seed=1, arm="T_LDD")
        expected = placebo_arm.integrity("t1", 1, "T_LDD", a.assigned_at)
        assert a.integrity_hash == expected

    def test_pad_claude_md_matches_byte_length(self) -> None:
        real = "# real ldd claude.md with substantive content\n" * 20
        padded = placebo_arm.pad_claude_md_to_match(real)
        assert len(padded.encode("utf-8")) == len(real.encode("utf-8"))


# ---------------------------------------------------------------------------
# analyze
# ---------------------------------------------------------------------------


class TestAnalyze:
    def test_wilson_ci_contains_phat(self) -> None:
        lo, hi = analyze.wilson_ci(60, 100)
        assert lo < 0.60 < hi

    def test_wilson_ci_edge_cases(self) -> None:
        lo0, hi0 = analyze.wilson_ci(0, 100)
        assert lo0 == 0.0 and 0.0 < hi0 < 0.2
        lo100, hi100 = analyze.wilson_ci(100, 100)
        # `hi100 == 1.0` fails for floating-point reasons — Wilson upper
        # bound at k=n is 1 - ε where ε is FPU noise. Accept anything within
        # 1e-9 of 1.0 as "1.0" for test purposes.
        assert 0.8 < lo100 < 1.0 and math.isclose(hi100, 1.0, abs_tol=1e-9)

    def test_two_proportion_z_sign(self) -> None:
        """T_LDD better than T_baseline → diff > 0, z > 0."""
        r = analyze.primary_proportion_test(60, 100, 40, 100)
        assert r.diff > 0 and r.z > 0

    def test_two_proportion_ci_contains_diff(self) -> None:
        r = analyze.primary_proportion_test(60, 100, 40, 100)
        assert r.diff_ci_low < r.diff < r.diff_ci_high

    def test_bh_simple_case(self) -> None:
        # Classic example from BH 1995: 5 p-values, α=0.05
        ps = [0.001, 0.008, 0.039, 0.041, 0.042]
        reject = analyze.bh_correction(ps, alpha=0.05)
        # Largest p that survives: 0.042 <= 5/5 * 0.05 = 0.05 → all 5 survive,
        # which in BH means the entire set is rejected.
        assert all(reject)

    def test_bh_noisy_case(self) -> None:
        ps = [0.001, 0.5, 0.5, 0.5, 0.5]
        reject = analyze.bh_correction(ps, alpha=0.05)
        # Smallest p=0.001 must be rejected; others should not be.
        assert reject[0]
        assert not any(reject[1:])

    def test_paired_judge_significance(self) -> None:
        # 70 wins, 30 losses → one-sided p < 0.001
        r = analyze.paired_judge_test(70, 30, 0)
        assert r.p_value_one_sided < 0.001
        assert r.win_rate == 0.70

    def test_paired_judge_ties_excluded_from_test(self) -> None:
        r = analyze.paired_judge_test(40, 40, 20)
        assert r.p_value_one_sided > 0.1   # null not rejected
        assert r.ties == 20

    def test_bootstrap_ci_deterministic_by_seed(self) -> None:
        values = [0, 1, 1, 0, 1, 0, 1, 1, 1, 0]
        a = analyze.bootstrap_ci(values, seed=1, n_resamples=2000)
        b = analyze.bootstrap_ci(values, seed=1, n_resamples=2000)
        assert a == b

    def test_verdict_load_bearing(self) -> None:
        # Significant win over BOTH baseline and placebo → load_bearing
        baseline = analyze.primary_proportion_test(600, 1000, 420, 1000)
        placebo = analyze.primary_proportion_test(600, 1000, 440, 1000)
        assert analyze.verdict(baseline, placebo) == "load_bearing"

    def test_verdict_prompt_priming(self) -> None:
        # Significant win vs baseline, but NOT vs placebo → prompt_priming
        baseline = analyze.primary_proportion_test(600, 1000, 420, 1000)
        placebo = analyze.primary_proportion_test(600, 1000, 590, 1000)
        assert analyze.verdict(baseline, placebo) == "prompt_priming"

    def test_verdict_no_effect(self) -> None:
        baseline = analyze.primary_proportion_test(420, 1000, 420, 1000)
        placebo  = analyze.primary_proportion_test(420, 1000, 440, 1000)
        assert analyze.verdict(baseline, placebo) == "no_effect"


# ---------------------------------------------------------------------------
# run_mini — smoke
# ---------------------------------------------------------------------------


class TestRunMini:
    def test_seeded_deterministic(self) -> None:
        a = run_mini.run(seed=0)
        b = run_mini.run(seed=0)
        assert a == b

    def test_all_outcomes_present(self) -> None:
        r = run_mini.run(seed=0)
        for outcome in run_mini.PRIORS:
            assert outcome in r["outcomes"]

    def test_priors_roughly_recovered(self) -> None:
        """With N_TASKS × SEEDS_PER_TASK draws (~180 Bernoulli), the empirical
        rate should be within the 95 %-CI-half-width of the prior for a
        typical seed — loosened to 0.10 so nobody gets yellow-card'd by one
        unlucky arm on p≈0.70 where binomial variance is widest."""
        r = run_mini.run(seed=0)
        for outcome, priors in run_mini.PRIORS.items():
            arms = r["outcomes"][outcome]["arm_rates"]
            for arm, p_prior in priors.items():
                empirical = arms[arm]["p_hat"]
                assert abs(empirical - p_prior) < 0.10, (
                    f"{outcome}/{arm}: prior={p_prior} empirical={empirical}"
                )

    def test_power_curve_monotonic(self) -> None:
        r = run_mini.run(seed=0)
        ns = [row["n_per_arm"] for row in r["power_curve"]]
        assert ns == sorted(ns, reverse=True)

    def test_judge_prompt_hash_stable(self) -> None:
        """Reviewer audit — any prompt edit bumps this hash."""
        expected = run_mini._judge_prompt_reference_hash()
        r = run_mini.run(seed=0)
        assert r["judge_prompt_hash"] == expected


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-v"]))
