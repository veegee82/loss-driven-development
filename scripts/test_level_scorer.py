"""Tests for level_scorer.

Run with:
    cd scripts && python -m pytest test_level_scorer.py -v

or (from repo root):
    python -m pytest scripts/test_level_scorer.py -v

Covers:
    - Per-signal detection (unit level)
    - Score → level bucketing (boundaries)
    - Creativity inference
    - Override parsing (all 5 precedence categories)
    - Clamp rule (L4 → L3 when creativity=standard)
    - End-to-end: every fixture scenario hits its expected level

The end-to-end block is the authoritative contract: if any fixture fails,
weights or boundaries in level_scorer.py need tuning — NOT the fixture.
"""
from __future__ import annotations

import pytest

from level_scorer import (
    Creativity,
    DispatchSource,
    Level,
    detect_signals,
    has_implicit_ack,
    infer_creativity,
    parse_override,
    score_task,
    score_to_level,
)


# ---------------------------------------------------------------------------
# Signal detection
# ---------------------------------------------------------------------------


class TestSignalDetection:
    def test_greenfield_fires(self) -> None:
        sigs = detect_signals("design a new service from scratch")
        names = {s.name for s in sigs}
        assert "greenfield" in names

    def test_explicit_bugfix_fires(self) -> None:
        sigs = detect_signals("fix the typo in README.md line 12")
        names = {s.name for s in sigs}
        assert "explicit-bugfix" in names

    def test_single_file_fires_on_path_plus_line(self) -> None:
        sigs = detect_signals("fix the bug in src/foo.py line 42")
        names = {s.name for s in sigs}
        assert "single-file" in names

    def test_single_file_does_not_fire_on_multiple_paths(self) -> None:
        sigs = detect_signals("update src/foo.py and src/bar.py to match the schema")
        names = {s.name for s in sigs}
        assert "single-file" not in names

    def test_contract_rule_hit_on_R_rule(self) -> None:
        sigs = detect_signals("hook into the R35 mechanism")
        names = {s.name for s in sigs}
        assert "contract-rule-hit" in names

    def test_contract_rule_hit_on_validator(self) -> None:
        sigs = detect_signals("bump the confidence threshold in the validator")
        names = {s.name for s in sigs}
        assert "contract-rule-hit" in names

    def test_layer_crossings_fires_on_multiple_layers(self) -> None:
        sigs = detect_signals(
            "add a new critique gate in the delegation loop near the manager"
        )
        names = {s.name for s in sigs}
        assert "layer-crossings" in names

    def test_ambiguous_fires_on_last_change_phrase(self) -> None:
        sigs = detect_signals("the test is failing after my last change")
        names = {s.name for s in sigs}
        assert "ambiguous" in names

    def test_no_signals_on_chitchat(self) -> None:
        sigs = detect_signals("hello, can you help me out?")
        # Only thing that might fire is... nothing. raw sum should be 0.
        assert sum(s.weight for s in sigs) == 0

    def test_unknown_file_territory_zero_without_history(self) -> None:
        sigs = detect_signals("edit packages/unknown/src/whatever.py")
        names = {s.name for s in sigs}
        assert "unknown-file-territory" not in names

    def test_unknown_file_territory_fires_with_history(self) -> None:
        sigs = detect_signals(
            "edit packages/unknown/src/whatever.py",
            history=["packages/known/src/other.py"],
        )
        names = {s.name for s in sigs}
        assert "unknown-file-territory" in names


# ---------------------------------------------------------------------------
# Bucketing
# ---------------------------------------------------------------------------


class TestBucketing:
    @pytest.mark.parametrize(
        "score,expected",
        [
            (-10, Level.L0),
            (-7, Level.L0),
            (-6, Level.L1),
            (-2, Level.L1),
            (-1, Level.L2),
            (0, Level.L2),
            (3, Level.L2),
            (4, Level.L3),
            (7, Level.L3),
            (8, Level.L4),
            (15, Level.L4),
        ],
    )
    def test_boundaries(self, score: int, expected: Level) -> None:
        assert score_to_level(score) == expected


# ---------------------------------------------------------------------------
# Creativity inference
# ---------------------------------------------------------------------------


class TestCreativity:
    def test_standard_default(self) -> None:
        assert infer_creativity("build a thing") == Creativity.STANDARD

    def test_conservative_on_HIPAA(self) -> None:
        assert (
            infer_creativity("design an ingestion service for our HIPAA stack")
            == Creativity.CONSERVATIVE
        )

    def test_inventive_on_novel(self) -> None:
        assert (
            infer_creativity("prototype a novel consistency protocol")
            == Creativity.INVENTIVE
        )

    def test_conservative_beats_inventive_on_tie(self) -> None:
        text = "prototype a novel HIPAA-compliant thing"
        assert infer_creativity(text) == Creativity.CONSERVATIVE

    def test_implicit_ack_requires_two_cues_and_100_chars(self) -> None:
        short = "prototype a novel X"
        assert not has_implicit_ack(short)
        long_enough = (
            "we want to prototype a novel autonomy sublevel where no known "
            "pattern fits directly; this is research-grade experimental work"
        )
        assert has_implicit_ack(long_enough)


# ---------------------------------------------------------------------------
# Override parsing
# ---------------------------------------------------------------------------


class TestOverrideParsing:
    def test_no_override(self) -> None:
        assert parse_override("fix the typo in README.md") is None

    def test_explicit_L3(self) -> None:
        o = parse_override("LDD[level=L3]: do the thing")
        assert o is not None
        assert o.absolute_level == Level.L3
        assert o.kind == "explicit"

    def test_explicit_L0_override_down(self) -> None:
        o = parse_override("LDD[level=L0]: complex task")
        assert o is not None
        assert o.absolute_level == Level.L0

    def test_max(self) -> None:
        o = parse_override("LDD=max: typo fix")
        assert o is not None
        assert o.absolute_level == Level.L4
        assert o.kind == "max"

    def test_plusplus(self) -> None:
        o = parse_override("LDD++: fix the typo")
        assert o is not None
        assert o.delta == 2
        assert o.kind == "plusplus"

    def test_plus(self) -> None:
        o = parse_override("LDD+: fix the typo")
        assert o is not None
        assert o.delta == 1
        assert o.kind == "plus"

    def test_natural_single(self) -> None:
        o = parse_override("take your time with this rename")
        assert o is not None
        assert o.delta == 1
        assert o.kind == "natural"

    def test_natural_multiple_bump_1_dedup_to_plus_1(self) -> None:
        # "take your time" + "think hard" both express "be careful" — same
        # intent, should not double-count.
        o = parse_override("take your time and think hard about this rename")
        assert o is not None
        assert o.delta == 1

    def test_natural_saturates_at_1_regardless_of_count(self) -> None:
        o = parse_override("take your time think hard careful durchdacht")
        assert o is not None
        assert o.delta == 1  # all BUMP_1, saturates

    def test_natural_bump_2_requires_strong_phrase(self) -> None:
        o = parse_override("think really hard about this")
        assert o is not None
        assert o.delta == 2

    def test_natural_max(self) -> None:
        o = parse_override("volle Kanne: typo fix")
        assert o is not None
        assert o.absolute_level == Level.L4

    def test_explicit_beats_max(self) -> None:
        # If both are present somehow, explicit wins (precedence).
        o = parse_override("LDD[level=L2]: LDD=max: do it")
        assert o is not None
        assert o.absolute_level == Level.L2

    def test_max_beats_plusplus(self) -> None:
        o = parse_override("LDD=max: LDD++: do it")
        assert o is not None
        assert o.absolute_level == Level.L4
        assert o.kind == "max"


# ---------------------------------------------------------------------------
# Clamp rule
# ---------------------------------------------------------------------------


class TestClampRule:
    def test_L4_bucket_clamps_to_L3_on_standard_creativity(self) -> None:
        # Designed to score ≥ 8 (L4 bucket) without any inventive cues.
        text = (
            "design a new service integration across the orchestration layer "
            "and the observability layer, covering the runner, scorer, and "
            "manager; wire it into the delegation loop and honor R17"
        )
        r = score_task(text)
        assert r.creativity == Creativity.STANDARD, (
            f"expected STANDARD, got {r.creativity.value}"
        )
        assert r.raw_score >= 8, (
            f"expected raw_score ≥ 8 to trigger L4 bucket, got {r.raw_score} "
            f"(signals: {[(s.name, s.weight) for s in r.signals_fired]})"
        )
        assert r.auto_level == Level.L3
        assert r.clamp_reason is not None
        assert "clamped" in r.clamp_reason

    def test_L4_preserved_when_creativity_is_inventive(self) -> None:
        text = (
            "design a novel autonomy sublevel between A2 and A3 for recursive "
            "delegation with shared memory; greenfield, no known pattern fits, "
            "we want to prototype experimental mechanisms"
        )
        r = score_task(text)
        assert r.creativity == Creativity.INVENTIVE
        # Must NOT clamp
        assert r.clamp_reason is None


# ---------------------------------------------------------------------------
# End-to-end: fixture scenarios
# ---------------------------------------------------------------------------


# These prompts are pulled verbatim from tests/fixtures/thinking-levels/*/scenario.md.
# The expected_level values are the CONTRACT. If the scorer produces a
# different level, the scorer needs tuning (weights or boundaries), not the
# fixture. Asymmetric-loss rule: test parametrize IDs tagged so low-side
# failures are obvious.

FIXTURE_CASES = [
    (
        "L0-reflex",
        'fix the typo in README.md line 12: "Agent Worklow" should be "Agent Workflow"',
        Level.L0,
        DispatchSource.AUTO,
        None,
    ),
    (
        "L1-diagnostic",
        "the unit test test_parser_handles_empty_input in packages/awp-core/tests/test_parser.py is failing after my last change; help me fix it",
        Level.L1,
        DispatchSource.AUTO,
        None,
    ),
    (
        "L2-deliberate",
        "bump the confidence threshold default from 0.5 to 0.6 in the validator, and update any tests that expect the old value",
        Level.L2,
        DispatchSource.AUTO,
        None,
    ),
    (
        "L3-structural",
        "we need to add a new critique gate for repair-fixpoint detection between the existing critique and deliverable_presence gates in the delegation loop; it should hook into the same R35 mechanism",
        Level.L3,
        DispatchSource.AUTO,
        Creativity.STANDARD,
    ),
    (
        "L4-method",
        "design a new autonomy sublevel between A2 and A3 for manager-led recursive delegation with shared memory; greenfield, no known pattern fits directly, we want to prototype novel mechanisms",
        Level.L4,
        DispatchSource.AUTO,
        Creativity.INVENTIVE,
    ),
    (
        "override-up-from-L0",
        "LDD++: fix the typo in README.md line 12",
        Level.L2,
        DispatchSource.USER_BUMP,
        None,
    ),
    (
        "override-max-on-simple",
        "LDD=max: fix the typo in README.md line 12",
        Level.L4,
        DispatchSource.USER_BUMP,
        None,
    ),
    (
        "override-natural-language",
        "take your time and think hard about this: rename the variable `foo` to `bar` in packages/awp-core/src/awp/cli.py",
        # Accepts L1 or L2 per fixture spec — encoded via special-case below.
        # Value here is the preferred target (L2); custom check handles the
        # or-branch.
        Level.L2,
        DispatchSource.USER_BUMP,
        None,
    ),
    (
        "override-down-warning",
        "LDD[level=L0]: we need to add a new critique gate for repair-fixpoint detection between the existing critique and deliverable_presence gates in the delegation loop; it should hook into the same R35 mechanism",
        Level.L0,
        DispatchSource.USER_OVERRIDE_DOWN,
        None,
    ),
]


# Scenarios where the fixture spec explicitly accepts multiple levels as GREEN.
# Key: fixture name. Value: set of acceptable levels.
_MULTI_LEVEL_ACCEPT: dict[str, set[Level]] = {
    "override-natural-language": {Level.L1, Level.L2},
}


@pytest.mark.parametrize(
    "name,prompt,expected_level,expected_source,expected_creativity",
    FIXTURE_CASES,
    ids=[case[0] for case in FIXTURE_CASES],
)
def test_fixture_scenario(
    name: str,
    prompt: str,
    expected_level: Level,
    expected_source: DispatchSource,
    expected_creativity: Creativity | None,
) -> None:
    r = score_task(prompt)
    acceptable = _MULTI_LEVEL_ACCEPT.get(name, {expected_level})
    assert r.final_level in acceptable, (
        f"[{name}] expected {sorted(l.value for l in acceptable)}, "
        f"got {r.final_level.value} "
        f"(raw_score={r.raw_score}, signals={[(s.name, s.weight) for s in r.signals_fired]}, "
        f"header: {r.dispatch_header()})"
    )
    assert r.dispatch_source == expected_source, (
        f"[{name}] expected source {expected_source.value}, got {r.dispatch_source.value}"
    )
    if expected_creativity is not None:
        assert r.creativity == expected_creativity, (
            f"[{name}] expected creativity {expected_creativity.value}, got {r.creativity.value}"
        )


# ---------------------------------------------------------------------------
# Dispatch header rendering
# ---------------------------------------------------------------------------


class TestDispatchHeader:
    def test_auto_level_header_contains_top_signals(self) -> None:
        r = score_task("fix the typo in README.md line 12")
        h = r.dispatch_header()
        assert "auto-level" in h
        assert "L0" in h
        assert "explicit-bugfix" in h or "single-file" in h

    def test_user_bump_header_mentions_fragment(self) -> None:
        r = score_task("LDD++: fix the typo")
        h = r.dispatch_header()
        assert "user-bump" in h
        assert "LDD++" in h
        assert "scorer proposed" in h

    def test_user_override_down_warning_contains_loss_risk(self) -> None:
        r = score_task(
            "LDD[level=L0]: add a new critique gate in the delegation loop for R35 repair-fixpoint"
        )
        h = r.dispatch_header()
        assert "user-override-down" in h
        assert "loss risk" in h.lower() or "user accepts" in h.lower()

    def test_clamp_token_in_header_when_clamp_fires(self) -> None:
        r = score_task(
            "we need to add a new critique gate for repair-fixpoint detection "
            "between the existing critique and deliverable_presence gates in "
            "the delegation loop; it should hook into the same R35 mechanism"
        )
        if r.clamp_reason:
            h = r.dispatch_header()
            assert "clamped" in h.lower()
