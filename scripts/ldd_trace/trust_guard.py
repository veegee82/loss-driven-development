"""Trust Boundary — v0.9.1 P1 fix for audit findings C1, C2, H1, H4, L1.

v0.9.0 had multiple paths where the agent / LLM supplies a number or
function that the framework trusted without external cross-validation:

  - MetricSpec.description was checked against English-only phrase list (C1, L1)
  - MetricSpec.accessor was NOT checked at all (C1)
  - ProposedStep.prior was accepted as-is (C2)
  - Antithesis.impact was accepted as-is (H1)
  - verify_fn could be a trivial default (H4)

This module introduces a single `TrustGuard` layer that stands between the
agent-supplied inputs and the framework internals. Each method returns the
input in sanitized / bounded form, OR raises a specific exception that the
caller can handle explicitly (rather than silently trusting bad input).

Design principle: the guard does NOT decide correctness. It enforces
REASONABLE BOUNDS so the agent cannot construct inputs that trivially
bypass the framework's discipline (prior=1.0 skip, impact=±huge to force
decisions, gamed accessor).
"""
from __future__ import annotations

import ast
import inspect
from dataclasses import dataclass
from typing import Any, Callable, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Exceptions — raised by TrustGuard to signal bounds violations
# ---------------------------------------------------------------------------


class TrustGuardError(ValueError):
    """Base for all TrustGuard rejections."""


class AntithesisAbsentError(TrustGuardError):
    """Raised when a dialectical step has zero antitheses — this bypasses
    the Hessian-probe entirely (audit finding C2).
    """


class ImpactOutOfRangeError(TrustGuardError):
    """Raised when Antithesis.impact is outside [-1, 1] — prevents forcing
    unbounded commit/reject (audit finding H1).
    """


class PriorTooHighError(TrustGuardError):
    """Raised when thesis_prior is above `MAX_PRIOR` — prevents a
    degenerate 'always confident' LLM from bypassing the dialectic
    (audit finding C2).
    """


class VerifyFnMissingError(TrustGuardError):
    """Raised when a calibration path requires verification but no
    `verify_fn` was supplied — prevents the default-string-equality
    false-negative problem (audit finding H4).
    """


class GoodhartAccessorError(TrustGuardError):
    """Raised when static analysis of a metric's accessor suggests it
    may be gamed — e.g. references `kwargs.get('agent_lines_added')`
    or similar self-referential state. Conservative heuristic; false
    positives are preferred to false negatives (audit finding C1).
    """


# ---------------------------------------------------------------------------
# Configuration — tunable bounds
# ---------------------------------------------------------------------------


# v0.9.1 P1 — prior cap to prevent LLM-confidence bypass (C2)
MAX_PRIOR = 0.9
# v0.9.1 P1 — impact bounds to prevent gaming (H1)
MAX_IMPACT_MAGNITUDE = 1.0


# v0.9.1 P1 — multilingual gaming-guard phrases (C1 + L1)
# English, German, French, Spanish common self-reference patterns.
# Intentionally overcautious — a benign description accidentally matching
# is fixable via rephrasing; a missed match is a real gaming hole.
MULTILINGUAL_GAMING_PHRASES = (
    # English (v0.9.0 baseline)
    "current action", "last action", "my decision", "the action i took",
    "the action just taken", "my current", "i want", "i prefer",
    "rewards me", "favor my", "my approach",
    # German (v0.9.1 L1 extension)
    "meine aktuelle", "meine aktion", "meine entscheidung",
    "belohnt mich", "begünstigt meine", "mein aktueller",
    # French (v0.9.1 L1 extension)
    "mon action", "ma décision", "mon approche", "récompense mon",
    "favorise mon", "mon actuel",
    # Spanish (v0.9.1 L1 extension)
    "mi acción", "mi decisión", "mi enfoque", "recompensa mi",
    "favorece mi", "mi actual",
)


# Accessor-audit heuristics — ast-scan for variable names that suggest
# the accessor reads state the agent controls (the goodhart pattern).
GOODHART_IDENTIFIER_PATTERNS = (
    "agent_", "_by_agent", "mine_", "_mine", "self_proposed",
    "lines_added", "lines_written",  # classic LOC-gaming proxy
    "commits_made", "prs_opened",     # volume-gaming proxy
)


# ---------------------------------------------------------------------------
# TrustGuard — central layer between agent input and framework internals
# ---------------------------------------------------------------------------


@dataclass
class TrustGuard:
    """Sanitizes agent-supplied inputs before they reach the framework.

    All methods are static; no mutable state. The guard is a pure
    input-validation/transformation function.
    """

    max_prior: float = MAX_PRIOR
    max_impact_magnitude: float = MAX_IMPACT_MAGNITUDE
    max_antitheses: int = 20
    require_verify_fn: bool = True
    accessor_audit_enabled: bool = True

    # --- Dialectical inputs (C2, H1 guards) ---------------------------------

    def guard_prior(self, prior: float) -> float:
        """Cap thesis_prior at max_prior.

        Rationale (C2): an LLM that always self-rates prior=1.0 with no
        antitheses would bypass the dialectic entirely. Capping at 0.9
        leaves room for "unknown unknowns" that a sensible antithesis
        generator must address.
        """
        if not (0.0 <= prior <= 1.0):
            raise PriorTooHighError(
                f"prior must be in [0, 1], got {prior}"
            )
        return min(prior, self.max_prior)

    def guard_antitheses(
        self,
        antis: list,  # List[Antithesis] but avoid import cycle
        allow_empty: bool = False,
    ) -> list:
        """Validate each antithesis's (prob, impact) bounds.

        Rationale (H1): unbounded impact can force commit/reject deterministically.
        Clamping to [-1, 1] ensures antitheses represent plausible
        counter-cases, not arbitrary gates.

        Rationale (C2 + v0.9.1): empty antithesis list is rejected unless
        the caller explicitly opts in via `allow_empty=True` (which is
        used only when memory has no primers AND LLM confirmed "no
        counter-case" as a distinct state).
        """
        if not antis and not allow_empty:
            raise AntithesisAbsentError(
                "no antitheses generated — dialectical pass is trivial. "
                "If this is intentional, pass allow_empty=True to signal "
                "'no counter-case applies' as a distinct verdict."
            )
        if len(antis) > self.max_antitheses:
            raise TrustGuardError(
                f"too many antitheses ({len(antis)}) — capped at {self.max_antitheses}"
            )
        sanitized = []
        for a in antis:
            prob = getattr(a, "prob_applies", None)
            impact = getattr(a, "impact", None)
            if prob is None or impact is None:
                raise TrustGuardError(
                    f"antithesis missing prob_applies or impact: {a!r}"
                )
            if not (0.0 <= prob <= 1.0):
                raise TrustGuardError(
                    f"prob_applies must be in [0, 1], got {prob}"
                )
            if abs(impact) > self.max_impact_magnitude:
                raise ImpactOutOfRangeError(
                    f"|impact|={abs(impact)} exceeds bound "
                    f"{self.max_impact_magnitude}"
                )
            sanitized.append(a)
        return sanitized

    # --- Calibration inputs (H4 guard) --------------------------------------

    def guard_verify_fn(
        self,
        verify_fn: Optional[Callable],
        *,
        required: bool = True,
    ) -> Callable:
        """Ensure calibration has a user-supplied verifier.

        Rationale (H4): the default string-equality verify_fn produces
        false negatives on semantic equivalences ('42' vs '42.0'), which
        inflates MAE and triggers spurious drift warnings. Agents that
        calibrate MUST supply a verify_fn appropriate for their task class.
        """
        if verify_fn is None:
            if required and self.require_verify_fn:
                raise VerifyFnMissingError(
                    "calibration requires a verify_fn — the default "
                    "string-equality verifier produces false negatives on "
                    "semantic equivalences (42 vs 42.0, whitespace, case). "
                    "Supply verify_fn=lambda ans, gt: <canonicalize-then-compare>"
                )
            # Fallback for non-calibrated paths — benign string eq
            return lambda a, gt: a == gt
        return verify_fn

    # --- Accessor audit (C1 guard) ------------------------------------------

    def guard_accessor(
        self,
        accessor: Callable,
        spec_name: str,
    ) -> Callable:
        """Static-analyze the accessor's source for goodhart patterns.

        Conservative heuristic (C1): if the AST references identifiers in
        GOODHART_IDENTIFIER_PATTERNS, the accessor MAY be reading
        agent-controlled state. Flag it for human review rather than
        silently accept.

        This is NOT foolproof — a clever adversary can rename. But it
        catches the common cases where an agent inadvertently writes
        `lambda θ: θ["lines_added_by_agent"]` thinking it's benign.
        """
        if not self.accessor_audit_enabled:
            return accessor

        try:
            source = inspect.getsource(accessor)
        except (OSError, TypeError):
            # Can't get source (e.g., lambda from exec, built-in) — skip audit
            return accessor

        try:
            tree = ast.parse(source.strip())
        except SyntaxError:
            return accessor

        # Collect all Name / Attribute / Subscript-string-constant nodes
        collected: List[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Name):
                collected.append(node.id)
            elif isinstance(node, ast.Attribute):
                collected.append(node.attr)
            elif isinstance(node, ast.Constant) and isinstance(node.value, str):
                collected.append(node.value)

        joined = " ".join(collected).lower()
        for pattern in GOODHART_IDENTIFIER_PATTERNS:
            if pattern.lower() in joined:
                raise GoodhartAccessorError(
                    f"accessor for metric {spec_name!r} references "
                    f"potentially-gamed identifier matching {pattern!r} "
                    f"(heuristic check). If the accessor is legitimate, "
                    f"rename the identifier or disable accessor_audit."
                )

        return accessor

    # --- Multilingual gaming-guard (L1 guard) -------------------------------

    @staticmethod
    def check_description_multilingual(description: str) -> None:
        """Check description against the multilingual self-reference
        phrase list. Raises if any phrase matches.

        Replaces the English-only GAMING_GUARD_PHRASES in MetricSpec.
        """
        desc_lower = (description or "").lower()
        for phrase in MULTILINGUAL_GAMING_PHRASES:
            if phrase in desc_lower:
                raise TrustGuardError(
                    f"gaming-guard (multilingual): description contains "
                    f"self-referential phrase {phrase!r}"
                )


# Module-level default instance — callers can use `default_trust_guard` or
# create their own with custom thresholds.
default_trust_guard = TrustGuard()
