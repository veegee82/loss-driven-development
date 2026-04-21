"""Tests for v0.9.1 TrustGuard — the input-sanitization layer between
agent-supplied values and framework internals.

Covers audit findings C1 (gaming-guard surface-only), C2 (prior bypass),
H1 (impact gameable), H4 (verify_fn quality), L1 (multilingual phrases).
"""
from __future__ import annotations

from dataclasses import dataclass

import pytest

from ldd_trace.cot import Antithesis
from ldd_trace.trust_guard import (
    MAX_PRIOR,
    MULTILINGUAL_GAMING_PHRASES,
    AntithesisAbsentError,
    GoodhartAccessorError,
    ImpactOutOfRangeError,
    PriorTooHighError,
    TrustGuard,
    VerifyFnMissingError,
    default_trust_guard,
)


class TestPriorGuard:
    """C2 fix — prior capping prevents LLM-always-confident bypass."""

    def test_normal_prior_passes(self) -> None:
        g = TrustGuard()
        assert g.guard_prior(0.5) == 0.5
        assert g.guard_prior(0.89) == 0.89

    def test_prior_capped_at_max(self) -> None:
        g = TrustGuard(max_prior=0.9)
        assert g.guard_prior(0.999) == 0.9
        assert g.guard_prior(1.0) == 0.9

    def test_invalid_prior_rejected(self) -> None:
        g = TrustGuard()
        with pytest.raises(PriorTooHighError, match=r"\[0, 1\]"):
            g.guard_prior(-0.1)
        with pytest.raises(PriorTooHighError, match=r"\[0, 1\]"):
            g.guard_prior(1.5)

    def test_custom_cap(self) -> None:
        g = TrustGuard(max_prior=0.7)
        assert g.guard_prior(0.8) == 0.7


class TestAntithesisGuard:
    """H1 fix — impact bounds prevent gaming via ±huge values.
       C2 fix — empty list rejected unless explicitly opted in."""

    def _make_ant(self, prob: float, impact: float) -> Antithesis:
        return Antithesis(
            source="independent", content="x", prob_applies=prob, impact=impact
        )

    def test_valid_antitheses_pass(self) -> None:
        g = TrustGuard()
        antis = [self._make_ant(0.5, -0.3), self._make_ant(0.8, -0.1)]
        out = g.guard_antitheses(antis)
        assert len(out) == 2

    def test_empty_rejected_by_default(self) -> None:
        g = TrustGuard()
        with pytest.raises(AntithesisAbsentError):
            g.guard_antitheses([])

    def test_empty_allowed_when_opted_in(self) -> None:
        g = TrustGuard()
        out = g.guard_antitheses([], allow_empty=True)
        assert out == []

    def test_impact_out_of_range_rejected(self) -> None:
        g = TrustGuard()
        with pytest.raises(ImpactOutOfRangeError):
            g.guard_antitheses([self._make_ant(0.5, -2.0)])  # impact < -1
        with pytest.raises(ImpactOutOfRangeError):
            g.guard_antitheses([self._make_ant(0.5, +1.5)])  # impact > +1

    def test_prob_out_of_range_rejected(self) -> None:
        g = TrustGuard()
        with pytest.raises(ValueError, match=r"prob_applies must be"):
            g.guard_antitheses([self._make_ant(1.5, 0.0)])
        with pytest.raises(ValueError, match=r"prob_applies must be"):
            g.guard_antitheses([self._make_ant(-0.1, 0.0)])

    def test_too_many_antitheses_rejected(self) -> None:
        g = TrustGuard(max_antitheses=3)
        antis = [self._make_ant(0.1, -0.1) for _ in range(5)]
        with pytest.raises(ValueError, match="too many"):
            g.guard_antitheses(antis)


class TestVerifyFnGuard:
    """H4 fix — missing verify_fn rejected when required."""

    def test_present_fn_passes_through(self) -> None:
        g = TrustGuard()
        fn = lambda a, gt: a == gt
        assert g.guard_verify_fn(fn) is fn

    def test_none_rejected_when_required(self) -> None:
        g = TrustGuard(require_verify_fn=True)
        with pytest.raises(VerifyFnMissingError, match="canonicalize"):
            g.guard_verify_fn(None, required=True)

    def test_none_allowed_when_not_required(self) -> None:
        g = TrustGuard(require_verify_fn=True)
        fallback = g.guard_verify_fn(None, required=False)
        # Fallback is a callable (benign string-eq)
        assert callable(fallback)
        assert fallback("a", "a") is True
        assert fallback("a", "b") is False


class TestAccessorGuard:
    """C1 fix — goodhart accessor audit via AST scan."""

    def test_benign_accessor_passes(self) -> None:
        g = TrustGuard(accessor_audit_enabled=True)
        benign = lambda θ: θ.get("test_failures", 0) / θ.get("test_total", 1)
        out = g.guard_accessor(benign, spec_name="test_pass_rate")
        assert out is benign

    def test_goodhart_lines_added_detected(self) -> None:
        g = TrustGuard(accessor_audit_enabled=True)
        # This is the canonical gaming pattern: reward LoC
        def gamed(θ):
            return θ.get("lines_added", 0)

        with pytest.raises(GoodhartAccessorError, match="lines_added"):
            g.guard_accessor(gamed, spec_name="commit_impact")

    def test_goodhart_by_agent_suffix_detected(self) -> None:
        g = TrustGuard(accessor_audit_enabled=True)
        def gamed(θ):
            return θ.get("changes_by_agent", 0)

        with pytest.raises(GoodhartAccessorError, match="_by_agent"):
            g.guard_accessor(gamed, spec_name="changes")

    def test_audit_can_be_disabled(self) -> None:
        g = TrustGuard(accessor_audit_enabled=False)
        def gamed(θ):
            return θ.get("lines_added", 0)
        # With audit disabled, accessor is returned as-is
        out = g.guard_accessor(gamed, spec_name="x")
        assert out is gamed

    def test_unparseable_accessor_tolerated(self) -> None:
        """Built-in functions or accessors without source are skipped
        (can't audit what we can't introspect)."""
        g = TrustGuard(accessor_audit_enabled=True)
        # `len` is a built-in — no Python source
        out = g.guard_accessor(len, spec_name="x")
        assert out is len


class TestMultilingualGamingGuard:
    """L1 fix — multilingual phrase coverage."""

    @pytest.mark.parametrize(
        "phrase",
        [
            "my current approach",           # English
            "belohnt meine aktuelle",        # German
            "mon action actuelle",           # French
            "recompensa mi enfoque",         # Spanish
        ],
    )
    def test_phrase_rejected(self, phrase: str) -> None:
        from ldd_trace.trust_guard import TrustGuard as TG
        with pytest.raises(ValueError, match="gaming-guard"):
            TG.check_description_multilingual(f"this metric {phrase}")

    def test_neutral_description_passes(self) -> None:
        from ldd_trace.trust_guard import TrustGuard as TG
        # Should NOT raise
        TG.check_description_multilingual(
            "fraction of failing assertions in the test suite"
        )
        TG.check_description_multilingual(
            "wall-clock latency of http request processing"
        )


class TestDefaultInstance:
    def test_module_level_default_exists(self) -> None:
        assert default_trust_guard is not None
        assert isinstance(default_trust_guard, TrustGuard)
        assert default_trust_guard.max_prior == MAX_PRIOR


if __name__ == "__main__":
    import sys
    sys.exit(pytest.main([__file__, "-v"]))
