#!/usr/bin/env python3
"""LDD thinking-levels scorer (Phase 1 of the thinking-levels design).

Pure-function scorer that maps a user task prompt to one of five thinking
levels (L0..L4) plus a creativity suggestion (conservative/standard/inventive)
and a dispatch source (auto-level / user-explicit / user-bump /
user-override-down). No LLM call, no side effects.

Reference spec:
    docs/superpowers/specs/2026-04-22-ldd-thinking-levels-design.md

Usage (CLI):
    python scripts/level_scorer.py "<task prompt>"
    echo "<task prompt>" | python scripts/level_scorer.py -

Usage (library):
    from level_scorer import score_task
    result = score_task("fix the typo in README.md line 12")
    print(result.dispatch_header())
"""
from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass, field
from enum import Enum
from typing import Iterable


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class Level(str, Enum):
    L0 = "L0"
    L1 = "L1"
    L2 = "L2"
    L3 = "L3"
    L4 = "L4"

    @classmethod
    def from_int(cls, n: int) -> "Level":
        return cls(f"L{max(0, min(4, n))}")

    def to_int(self) -> int:
        return int(self.value[1])


class Creativity(str, Enum):
    CONSERVATIVE = "conservative"
    STANDARD = "standard"
    INVENTIVE = "inventive"


class DispatchSource(str, Enum):
    AUTO = "auto-level"
    USER_EXPLICIT = "user-explicit"
    USER_BUMP = "user-bump"
    USER_OVERRIDE_DOWN = "user-override-down"


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Signal:
    name: str
    weight: int


@dataclass
class ScoreResult:
    raw_score: int
    auto_level: Level
    final_level: Level
    creativity: Creativity
    dispatch_source: DispatchSource
    signals_fired: list[Signal]
    clamp_reason: str | None = None
    override_fragment: str | None = None  # the user phrase/flag that triggered a bump

    def top_signals(self, n: int = 2) -> list[Signal]:
        """Top-N signals by absolute weight, stable tie-break by name."""
        return sorted(
            self.signals_fired,
            key=lambda s: (-abs(s.weight), s.name),
        )[:n]

    def dispatch_header(self) -> str:
        """Render the mandatory trace-header line."""
        if self.dispatch_source == DispatchSource.AUTO:
            sigs = ", ".join(f"{s.name}={_fmt_weight(s.weight)}" for s in self.top_signals())
            line = f"Dispatched: auto-level {self.final_level.value} (signals: {sigs})"
            if self.clamp_reason:
                line += f" [{self.clamp_reason}]"
            return line
        if self.dispatch_source == DispatchSource.USER_EXPLICIT:
            return (
                f"Dispatched: user-explicit {self.final_level.value} "
                f"(scorer proposed {self.auto_level.value})"
            )
        if self.dispatch_source == DispatchSource.USER_BUMP:
            frag = self.override_fragment or ""
            return (
                f"Dispatched: user-bump {self.final_level.value} "
                f"(scorer proposed {self.auto_level.value}, bump: {frag})"
            )
        if self.dispatch_source == DispatchSource.USER_OVERRIDE_DOWN:
            return (
                f"Dispatched: user-override-down {self.final_level.value} "
                f"(scorer proposed {self.auto_level.value}). User accepts loss risk."
            )
        raise ValueError(f"unknown dispatch source: {self.dispatch_source}")


def _fmt_weight(w: int) -> str:
    return f"+{w}" if w >= 0 else str(w)


# ---------------------------------------------------------------------------
# Signal detection — pure functions over the task text
# ---------------------------------------------------------------------------


_GREENFIELD_PATTERNS = [
    r"\bfrom scratch\b",
    r"\bnew service\b",
    r"\bnew module\b",
    r"\bgreenfield\b",
    r"\bno existing code\b",
    r"\bdesign a new\b",
    r"\bbuild a new\b",
    # A novel/experimental thing being designed/prototyped is also greenfield —
    # "design a novel protocol" is as structurally new as "design a new protocol".
    r"\bdesign a novel\b",
    r"\bprototype a novel\b",
    r"\bdesign (?:an? )?experimental\b",
    r"\bprototype (?:an? )?experimental\b",
]

_EXPLICIT_BUGFIX_PATTERNS = [
    r"\bfix\b(?!\s+(?:forward|in place))",
    r"\bfailing\b",
    r"\bbroken\b",
    r"\bdoesn'?t work\b",
    r"\bdoes not work\b",
    r"\boff-by-one\b",
    r"\btypo\b",
]

# Mechanical verbs that mark the work as bounded single-file even when not a
# bugfix (rename, move, delete, etc.). Used ONLY by the single-file detector;
# does NOT fire the explicit-bugfix signal.
_KNOWN_SOLUTION_VERBS = [
    r"\brename\b",
    r"\bmove\b",
    r"\bdelete\b",
    r"\bremove\b",
]

_SINGLE_FILE_PATH = re.compile(
    r"\b[\w./\-]+\.(?:py|ts|tsx|js|jsx|md|yaml|yml|json|toml|sh|sql|go|rs|java|rb)\b",
)

_LINE_REF = re.compile(r"\bline\s+\d+\b", re.IGNORECASE)

_AMBIGUOUS_PATTERNS = [
    r"\bsomehow\b",
    r"\bsomewhere\b",
    r"\bmaybe\b",
    r"\bafter my last change\b",
    r"\bwhen.*?(?:doesn'?t|does not)\b",
    r"\bI'?m not sure\b",
    r"\bI don'?t know\b",
    # "no known X fits" phrases — the user is explicitly saying they don't
    # have a solution pattern in mind. Requirements are underspecified.
    r"\bno known pattern\b",
    r"\bno known solution\b",
    r"\bno existing pattern\b",
]

_CROSS_LAYER_PATTERNS = [
    r"\bacross\b",
    r"\bbetween\b.*?\band\b",
    r"\bintegrate\b",
    r"\bwire\b",
    r"\bbridge\b",
    r"\bhook into\b",
    r"\binto\s+the\s+\w+\s+loop\b",
]

_CONTRACT_PATTERNS = [
    r"\bR\d{1,3}\b",
    r"\bschema\b",
    r"\bcontract\b",
    r"\bAPI surface\b",
    r"\binvariant\b",
    r"\bmust always\b",
    r"\bconfidence (?:field|threshold)\b",
    r"\bcritique gate\b",
    r"\bdeliverable_presence\b",
    r"\bvalidator\b",
]

_NEW_COMPONENTS_PATTERNS = [
    # Any "new|novel|experimental + <component-noun>" — covers "new module",
    # "novel protocol", "experimental mechanism". Plural forms accepted.
    r"\b(?:a|an|the)?\s*(?:new|novel|experimental)\s+(?:\w+\s+){0,3}(?:gate|service|module|component|components|mechanism|mechanisms|subsystem|layer|sublevel|protocol|protocols|store|stores|system|systems|pipeline|pipelines)\b",
    # LDD/AWP-specific multi-word compound concepts that each count as a
    # significant new piece of design work.
    r"\b(?:recursive\s+delegation|shared\s+memory|novel\s+mechanism|partial[- ]ordering|multi-master)\b",
]

_INVENTIVE_CUES = [
    r"\bnovel\b",
    r"\bresearch\b",
    r"\bprototype\b",
    r"\bno known pattern\b",
    r"\bno known solution\b",
    r"\binvent\b",
    r"\bexperimental\b",
    r"\bparadigm\b",
]

_CONSERVATIVE_CUES = [
    r"\bregulated\b",
    r"\bcompliance\b",
    r"\bHIPAA\b",
    r"\bPCI\b",
    r"\bSOC2\b",
    r"\bmigration of production\b",
    r"\bexisting stack only\b",
    r"\bno new tech\b",
    r"\bon-call\b",
    r"\btight deadline\b",
    r"\bteam of \d\b",
]


def _any_match(text: str, patterns: Iterable[str]) -> bool:
    lower = text.lower()
    return any(re.search(p, lower, re.IGNORECASE) for p in patterns)


def _count_matches(text: str, patterns: Iterable[str]) -> int:
    lower = text.lower()
    return sum(1 for p in patterns if re.search(p, lower, re.IGNORECASE))


def detect_signals(text: str, history: list[str] | None = None) -> list[Signal]:
    """Return the list of signals that fire on the given task text.

    history: list of recently-touched filenames from .ldd/trace.log. When empty
    or None, the `unknown-file-territory` signal contributes +0 (per spec §5.2).
    """
    sigs: list[Signal] = []

    # Original 6 architect-mode signals
    if _any_match(text, _GREENFIELD_PATTERNS):
        sigs.append(Signal("greenfield", +3))

    if _count_matches(text, _NEW_COMPONENTS_PATTERNS) >= 2 or _count_new_noun_components(text) >= 3:
        sigs.append(Signal("components>=3", +2))

    if _any_match(text, _CROSS_LAYER_PATTERNS):
        sigs.append(Signal("cross-layer", +2))

    if _any_match(text, _AMBIGUOUS_PATTERNS):
        sigs.append(Signal("ambiguous", +2))

    if _any_match(text, _EXPLICIT_BUGFIX_PATTERNS):
        sigs.append(Signal("explicit-bugfix", -5))

    if _is_single_file_known_solution(text):
        sigs.append(Signal("single-file", -3))

    # New 3 level-specific signals
    if _count_layer_crossings(text) >= 2:
        sigs.append(Signal("layer-crossings", +2))

    if _any_match(text, _CONTRACT_PATTERNS):
        sigs.append(Signal("contract-rule-hit", +2))

    if history and _has_unknown_file_territory(text, history):
        sigs.append(Signal("unknown-file-territory", +1))

    return sigs


def _is_single_file_known_solution(text: str) -> bool:
    """Exactly one file path mentioned AND the work is bounded.

    Boundedness is signalled by: a line reference, an explicit fix verb, OR a
    known-solution mechanical verb (rename, move, delete, remove). Multi-file
    asks ("validator and tests") do NOT fire, because the signal requires an
    unambiguous single target.
    """
    paths = _SINGLE_FILE_PATH.findall(text)
    if len(paths) != 1:
        return False
    has_line = bool(_LINE_REF.search(text))
    has_fix_verb = _any_match(text, _EXPLICIT_BUGFIX_PATTERNS)
    has_known_solution_verb = _any_match(text, _KNOWN_SOLUTION_VERBS)
    return has_line or has_fix_verb or has_known_solution_verb


def _count_new_noun_components(text: str) -> int:
    """Count distinct nouns preceded by 'new' (heuristic for ≥3 components)."""
    pattern = re.compile(r"\bnew\s+(\w+)", re.IGNORECASE)
    nouns = {m.group(1).lower() for m in pattern.finditer(text)}
    return len(nouns)


def _count_layer_crossings(text: str) -> int:
    """Count distinct references to named layers/packages/subsystems.

    Heuristic: look for known LDD/AWP layer/package names and count distinct hits.
    """
    layer_terms = [
        r"\bvalidator\b",
        r"\bcritique\b",
        r"\bdeliverable_presence\b",
        r"\bdelegation loop\b",
        r"\bmanager\b",
        r"\brunner\b",
        r"\bscorer\b",
        r"\borchestration\b",
        r"\bparser\b",
        r"\bruntime\b",
        r"\bcore\b",
        r"\bagent\b",
        r"\btool\b",
        r"\bmemory\b",
        r"\bobservability\b",
        r"\bcommunication\b",
        r"\bidentity\b",
        r"\bcapabilities\b",
        r"\bmanifest\b",
    ]
    lower = text.lower()
    return sum(1 for p in layer_terms if re.search(p, lower))


def _has_unknown_file_territory(text: str, history: list[str]) -> bool:
    """True if the text mentions a path not present in the history list."""
    paths = set(_SINGLE_FILE_PATH.findall(text))
    if not paths:
        return False
    known = {h.lower() for h in history}
    return any(p.lower() not in known for p in paths)


# ---------------------------------------------------------------------------
# Score → Level bucketing (spec §5.2 initial proposal)
# ---------------------------------------------------------------------------


def score_to_level(score: int) -> Level:
    """Map raw score to auto-level. Boundaries encode upward-bias tie-break.

    Phase-1-tuned boundaries (wider than initial spec §5.2 proposal). The L0
    bucket is deliberately narrow — pure mechanical typos with both
    explicit-bugfix AND single-file firing. Anything with an ambiguity signal
    on top lands in L1, which is the correct home for "failing test,
    investigation required".
    """
    if score <= -7:
        return Level.L0
    if score <= -2:  # -6..-2
        return Level.L1
    if score <= 3:  # -1..3 — L2 is the zero-signal baseline
        return Level.L2
    if score <= 7:  # 4..7
        return Level.L3
    return Level.L4  # score >= 8


# ---------------------------------------------------------------------------
# Creativity inference
# ---------------------------------------------------------------------------


def infer_creativity(text: str) -> Creativity:
    """Pick creativity level from task text. Tie: conservative > inventive."""
    if _any_match(text, _CONSERVATIVE_CUES):
        return Creativity.CONSERVATIVE
    if _any_match(text, _INVENTIVE_CUES):
        return Creativity.INVENTIVE
    return Creativity.STANDARD


def has_implicit_ack(text: str) -> bool:
    """≥2 inventive cues AND ≥100 chars → implicit ack for inventive creativity.

    Spec §8, Phase 2 relaxation. Present in Phase 1 for completeness but only
    consulted when creativity == inventive.
    """
    if len(text) < 100:
        return False
    return _count_matches(text, _INVENTIVE_CUES) >= 2


# ---------------------------------------------------------------------------
# Override parsing — precedence order from spec §5.3
# ---------------------------------------------------------------------------


_OVERRIDE_EXPLICIT = re.compile(r"\bLDD\[level=L([0-4])\]:", re.IGNORECASE)
_OVERRIDE_MAX = re.compile(r"\bLDD=max:", re.IGNORECASE)
_OVERRIDE_PLUSPLUS = re.compile(r"\bLDD\+\+:")
_OVERRIDE_PLUS = re.compile(r"\bLDD\+:")

_NATURAL_BUMP_1 = [
    r"\btake your time\b",
    r"\bthink hard\b",
    r"\bthink carefully\b",
    r"\bdenk gründlich\b",
    r"\bdenke gründlich\b",
    r"\bsorgfältig\b",
    r"\bdurchdacht\b",
    r"\bcareful\b",
]

_NATURAL_BUMP_2 = [
    r"\breally think\b",
    r"\bvery careful\b",
    r"\bultra-careful\b",
    r"\bmaximum rigor\b",
    r"\bthink really hard\b",
    r"\bthink thoroughly\b",
    r"\bsehr sorgfältig\b",
]

_NATURAL_BUMP_MAX = [
    r"\bfull LDD\b",
    r"\buse everything\b",
    r"\bmaximum deliberation\b",
    r"\bvolle Kanne\b",
]


@dataclass(frozen=True)
class Override:
    kind: str  # "explicit" | "max" | "plusplus" | "plus" | "natural"
    delta: int | None  # bump amount; None for explicit/max
    absolute_level: Level | None  # set for explicit/max
    fragment: str  # the matched user-facing text


def parse_override(text: str) -> Override | None:
    """Parse the highest-priority override in the text. Returns None if none."""
    # 1. explicit LDD[level=Lx]:
    m = _OVERRIDE_EXPLICIT.search(text)
    if m:
        lvl = Level(f"L{m.group(1)}")
        return Override("explicit", delta=None, absolute_level=lvl, fragment=m.group(0))

    # 2. LDD=max:
    m = _OVERRIDE_MAX.search(text)
    if m:
        return Override("max", delta=None, absolute_level=Level.L4, fragment="LDD=max")

    # 3. LDD++:
    m = _OVERRIDE_PLUSPLUS.search(text)
    if m:
        return Override("plusplus", delta=+2, absolute_level=None, fragment="LDD++")

    # 4. LDD+:
    m = _OVERRIDE_PLUS.search(text)
    if m:
        return Override("plus", delta=+1, absolute_level=None, fragment="LDD+")

    # 5. Natural language (category 4 in precedence) — lowest override tier.
    # Semantic dedup: all BUMP_1 phrases ("be careful") saturate at +1 together,
    # regardless of count. +2 requires an explicit strong phrase (BUMP_2).
    for pat in _NATURAL_BUMP_MAX:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            return Override(
                "natural", delta=None, absolute_level=Level.L4, fragment=m.group(0)
            )

    for pat in _NATURAL_BUMP_2:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            return Override(
                "natural", delta=+2, absolute_level=None, fragment=m.group(0)
            )

    bump_1_fragments: list[str] = []
    for pat in _NATURAL_BUMP_1:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            bump_1_fragments.append(m.group(0))

    if bump_1_fragments:
        return Override(
            "natural",
            delta=+1,
            absolute_level=None,
            fragment=" + ".join(f'"{f}"' for f in bump_1_fragments),
        )

    return None


# ---------------------------------------------------------------------------
# Top-level: score_task
# ---------------------------------------------------------------------------


def score_task(text: str, history: list[str] | None = None) -> ScoreResult:
    """Compute level + creativity + dispatch source for a task prompt."""
    signals = detect_signals(text, history=history)
    raw_score = sum(s.weight for s in signals)
    auto_level = score_to_level(raw_score)
    creativity = infer_creativity(text)

    # Creativity-clamp rule (spec §5.2): L4 bucket but creativity=standard
    # → clamp to L3.
    clamp_reason: str | None = None
    if auto_level == Level.L4 and creativity == Creativity.STANDARD:
        auto_level = Level.L3
        clamp_reason = "clamped from L4 (creativity=standard)"

    # Parse override
    override = parse_override(text)

    if override is None:
        return ScoreResult(
            raw_score=raw_score,
            auto_level=auto_level,
            final_level=auto_level,
            creativity=creativity,
            dispatch_source=DispatchSource.AUTO,
            signals_fired=signals,
            clamp_reason=clamp_reason,
        )

    # Apply override
    if override.absolute_level is not None:
        final_level = override.absolute_level
        if override.kind == "explicit":
            if final_level.to_int() < auto_level.to_int():
                src = DispatchSource.USER_OVERRIDE_DOWN
            else:
                src = DispatchSource.USER_EXPLICIT
        else:  # max or natural-max
            src = DispatchSource.USER_BUMP
    else:
        assert override.delta is not None
        new_int = auto_level.to_int() + override.delta
        final_level = Level.from_int(new_int)
        src = DispatchSource.USER_BUMP

    return ScoreResult(
        raw_score=raw_score,
        auto_level=auto_level,
        final_level=final_level,
        creativity=creativity,
        dispatch_source=src,
        signals_fired=signals,
        clamp_reason=clamp_reason if src == DispatchSource.AUTO else None,
        override_fragment=override.fragment,
    )


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _cli() -> int:
    parser = argparse.ArgumentParser(description="LDD thinking-levels scorer")
    parser.add_argument(
        "prompt",
        nargs="?",
        help='Task prompt. Use "-" to read from stdin.',
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit JSON instead of the dispatch header.",
    )
    args = parser.parse_args()

    if args.prompt is None or args.prompt == "-":
        text = sys.stdin.read()
    else:
        text = args.prompt

    result = score_task(text)
    if args.json:
        import json

        payload = {
            "raw_score": result.raw_score,
            "auto_level": result.auto_level.value,
            "final_level": result.final_level.value,
            "creativity": result.creativity.value,
            "dispatch_source": result.dispatch_source.value,
            "signals": [{"name": s.name, "weight": s.weight} for s in result.signals_fired],
            "clamp_reason": result.clamp_reason,
            "override_fragment": result.override_fragment,
            "dispatch_header": result.dispatch_header(),
        }
        print(json.dumps(payload, indent=2))
    else:
        print(result.dispatch_header())
        if result.creativity != Creativity.STANDARD or result.final_level == Level.L4:
            print(f"mode: architect, creativity: {result.creativity.value}")
    return 0


if __name__ == "__main__":
    sys.exit(_cli())
