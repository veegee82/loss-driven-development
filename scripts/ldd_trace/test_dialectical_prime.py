"""Tests for memory-informed antithesis priming — v0.6.0.

Validates the bridge between `ldd_trace` memory (1st-order statistics) and
`dialectical-reasoning` skill (2nd-order Hessian probing). Priming surfaces
evidence but does NOT assign weights or bias the loss.

Run:
    PYTHONPATH=scripts python -m pytest scripts/ldd_trace/test_dialectical_prime.py -v
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from ldd_trace import TraceStore
from ldd_trace.aggregator import aggregate_and_write, read_memory
from ldd_trace.dialectical_prime import (
    AntithesisMaterial,
    Primer,
    format_antithesis_material,
    prime_antithesis,
)


# Reuse the synthetic-project fixture from the memory E2E tests.
from ldd_trace.test_e2e_memory import _populate_synthetic_project


# ---------------------------------------------------------------------------
# Priming — skill-failure-mode extraction
# ---------------------------------------------------------------------------


class TestSkillFailureModePrimer:
    def test_primer_fires_for_known_bad_skill(self, tmp_path: Path) -> None:
        """Thesis mentions `retry-variant` (high reg+plateau rate) → primer fires."""
        store = _populate_synthetic_project(tmp_path)
        aggregate_and_write(store)
        memory = read_memory(store)

        material = prime_antithesis(
            memory=memory,
            thesis="Apply retry-variant to reach 0 failures",
        )
        sources = [p.source for p in material.primers]
        assert "skill_failure_mode" in sources, (
            f"expected skill_failure_mode primer for retry-variant; got {sources}"
        )
        primer = next(p for p in material.primers if p.source == "skill_failure_mode")
        assert "retry-variant" in primer.material
        assert primer.severity in ("warn", "high")

    def test_primer_does_not_fire_for_good_skill(self, tmp_path: Path) -> None:
        """Thesis mentions `root-cause-by-layer` (0% regression) → no failure-mode primer."""
        store = _populate_synthetic_project(tmp_path)
        aggregate_and_write(store)
        memory = read_memory(store)

        material = prime_antithesis(
            memory=memory,
            thesis="Use root-cause-by-layer to diagnose the contract violation",
        )
        sources = [p.source for p in material.primers]
        assert "skill_failure_mode" not in sources, (
            f"good skill should not trigger failure-mode primer; got {sources}"
        )


# ---------------------------------------------------------------------------
# Priming — in-flight plateau pattern
# ---------------------------------------------------------------------------


class TestPlateauPatternPrimer:
    def test_primer_fires_on_current_plateau(self, tmp_path: Path) -> None:
        """In-flight task with 2-streak plateau → plateau_pattern primer fires."""
        store = _populate_synthetic_project(tmp_path)
        aggregate_and_write(store)
        memory = read_memory(store)

        # Simulate in-flight task with 2 plateau iterations
        store.init(task_title="in-flight", loops=["inner"])
        store.append_iteration(
            loop="inner", k=0, skill="baseline", action="stub",
            loss_norm=1.0, raw="5/5", loss_type="rate", baseline=True,
        )
        store.append_iteration(
            loop="inner", k=1, skill="reproducibility-first", action="verify",
            loss_norm=1.0, raw="5/5", loss_type="rate",
        )
        store.append_iteration(
            loop="inner", k=2, skill="e2e-driven-iteration", action="attempt",
            loss_norm=1.0, raw="5/5", loss_type="rate",
        )
        current = store.current_task()

        material = prime_antithesis(
            memory=memory,
            thesis="Continue with e2e-driven-iteration for one more attempt",
            current=current,
        )
        sources = [p.source for p in material.primers]
        assert "plateau_pattern" in sources, (
            f"plateau primer should fire on 2-streak plateau; got {sources}"
        )
        primer = next(p for p in material.primers if p.source == "plateau_pattern")
        assert primer.severity == "high"
        # The primer should cite historical resolvers
        assert (
            "root-cause-by-layer" in primer.material
            or "unprecedented" in primer.material.lower()
        )

    def test_primer_silent_on_healthy_task(self, tmp_path: Path) -> None:
        """A task making progress → no plateau primer."""
        store = _populate_synthetic_project(tmp_path)
        aggregate_and_write(store)
        memory = read_memory(store)

        store.init(task_title="healthy", loops=["inner"])
        store.append_iteration(
            loop="inner", k=0, skill="baseline", action="stub",
            loss_norm=1.0, raw="5/5", loss_type="rate", baseline=True,
        )
        store.append_iteration(
            loop="inner", k=1, skill="root-cause-by-layer", action="fix",
            loss_norm=0.2, raw="1/5", loss_type="rate",
        )
        current = store.current_task()

        material = prime_antithesis(
            memory=memory,
            thesis="Continue with root-cause-by-layer",
            current=current,
        )
        sources = [p.source for p in material.primers]
        assert "plateau_pattern" not in sources


# ---------------------------------------------------------------------------
# Priming — terminal_analysis (project-wide non-complete rate)
# ---------------------------------------------------------------------------


class TestTerminalAnalysisPrimer:
    def test_primer_fires_if_project_has_aborts(self, tmp_path: Path) -> None:
        """Synthetic project has 1 aborted / 12 total (~8%)... below 15% threshold.
        Adjust threshold test by creating a project with more failures.
        """
        store = _populate_synthetic_project(tmp_path)
        # Synthetic data has 1/12 ≈ 8% — below threshold. Primer should NOT fire.
        aggregate_and_write(store)
        memory = read_memory(store)
        material = prime_antithesis(
            memory=memory, thesis="random thesis"
        )
        sources = [p.source for p in material.primers]
        # 8% < 15% threshold → no terminal_analysis primer
        assert "terminal_analysis" not in sources

    def test_primer_fires_with_high_failure_rate(self, tmp_path: Path) -> None:
        """Synthesize a project with ≥ 15% non-complete → primer fires."""
        store = TraceStore(tmp_path)
        store.init(task_title="base", loops=["inner"])

        # 3 complete + 2 aborted + 1 failed = 6 total, 3/6 = 50% non-complete
        def _one_task(title: str, terminal: str) -> None:
            store.init(task_title=title, loops=["inner"])
            store.append_iteration(
                loop="inner", k=0, skill="baseline", action="stub",
                loss_norm=1.0, raw="5/5", loss_type="rate", baseline=True,
            )
            store.append_iteration(
                loop="inner", k=1, skill="some-skill", action="try",
                loss_norm=0.5, raw="2/5", loss_type="rate",
            )
            store.append_close(
                loop="inner", terminal=terminal, layer="n/a", docs="n/a",
            )

        for i in range(3):
            _one_task(f"good-{i}", "complete")
        for i in range(2):
            _one_task(f"bad-{i}", "aborted")
        _one_task("fail-0", "failed")

        aggregate_and_write(store)
        memory = read_memory(store)

        material = prime_antithesis(memory=memory, thesis="proceed as usual")
        sources = [p.source for p in material.primers]
        assert "terminal_analysis" in sources, (
            f"50% non-complete should trigger terminal_analysis primer; "
            f"got {sources}"
        )


# ---------------------------------------------------------------------------
# Combined integration — multiple primers fire together
# ---------------------------------------------------------------------------


class TestCombinedPriming:
    def test_plateau_plus_bad_skill_both_fire(self, tmp_path: Path) -> None:
        """In-flight plateau AND thesis naming retry-variant → 2 primers."""
        store = _populate_synthetic_project(tmp_path)
        aggregate_and_write(store)
        memory = read_memory(store)

        # In-flight plateau
        store.init(task_title="combined", loops=["inner"])
        store.append_iteration(
            loop="inner", k=0, skill="baseline", action="stub",
            loss_norm=1.0, raw="5/5", loss_type="rate", baseline=True,
        )
        store.append_iteration(
            loop="inner", k=1, skill="reproducibility-first", action="verify",
            loss_norm=1.0, raw="5/5", loss_type="rate",
        )
        store.append_iteration(
            loop="inner", k=2, skill="e2e-driven-iteration", action="try",
            loss_norm=1.0, raw="5/5", loss_type="rate",
        )
        current = store.current_task()

        material = prime_antithesis(
            memory=memory,
            thesis="Try retry-variant one more time",
            current=current,
        )
        sources = [p.source for p in material.primers]
        assert "skill_failure_mode" in sources
        assert "plateau_pattern" in sources
        # Summary should mention counts
        assert "2" in material.summary or "primers" in material.summary


# ---------------------------------------------------------------------------
# Formatter output shape
# ---------------------------------------------------------------------------


class TestFormatter:
    def test_empty_material_renders_cleanly(self) -> None:
        material = AntithesisMaterial(thesis="test", primers=[], summary="no signal")
        out = format_antithesis_material(material)
        assert "╭─ Memory-primed antithesis material" in out
        assert "╰" in out
        assert "test" in out
        assert "no primers" in out.lower()

    def test_populated_material_renders_all_primers(self) -> None:
        material = AntithesisMaterial(
            thesis="apply skill X",
            primers=[
                Primer(
                    source="skill_failure_mode",
                    severity="high",
                    material="skill X regresses 40%",
                    evidence="n=10",
                ),
                Primer(
                    source="plateau_pattern",
                    severity="warn",
                    material="plateau streak=2 not seen before",
                    evidence="empty buckets",
                ),
            ],
            summary="2 primers generated",
        )
        out = format_antithesis_material(material)
        assert "skill_failure_mode" in out
        assert "plateau_pattern" in out
        assert "⚠⚠" in out
        assert "⚠" in out
        assert "Primer 1" in out
        assert "Primer 2" in out


# ---------------------------------------------------------------------------
# CLI integration
# ---------------------------------------------------------------------------


class TestCLI:
    def _run(self, *args: str) -> subprocess.CompletedProcess:
        env = {"PYTHONPATH": str(Path(__file__).resolve().parent.parent)}
        return subprocess.run(
            [sys.executable, "-m", "ldd_trace", *args],
            env=env, capture_output=True, text=True, check=False,
        )

    def test_prime_antithesis_subcommand_in_help(self) -> None:
        r = self._run("--help")
        assert r.returncode == 0
        assert "prime-antithesis" in r.stdout

    def test_prime_antithesis_requires_memory(self, tmp_path: Path) -> None:
        r = self._run(
            "prime-antithesis",
            "--project", str(tmp_path),
            "--thesis", "apply X"
        )
        assert r.returncode != 0
        assert "no project_memory" in r.stderr or "aggregate" in r.stderr

    def test_prime_antithesis_full_flow(self, tmp_path: Path) -> None:
        # Populate synthetic memory
        store = _populate_synthetic_project(tmp_path)
        aggregate_and_write(store)

        r = self._run(
            "prime-antithesis",
            "--project", str(tmp_path),
            "--thesis", "Apply retry-variant",
        )
        assert r.returncode == 0, r.stderr
        assert "retry-variant" in r.stdout
        assert "Memory-primed antithesis material" in r.stdout
        assert "Agent contract" in r.stdout


# ---------------------------------------------------------------------------
# Bias invariant — priming does not modify loss or rank actions
# ---------------------------------------------------------------------------


class TestBiasInvariant:
    def test_primer_output_is_evidence_not_decision(self, tmp_path: Path) -> None:
        """Primers must be phrased as QUESTIONS (counter-cases to consider),
        not prescriptive directives. The dialectical pass decides."""
        store = _populate_synthetic_project(tmp_path)
        aggregate_and_write(store)
        memory = read_memory(store)

        material = prime_antithesis(
            memory=memory, thesis="retry-variant it",
        )
        for primer in material.primers:
            # Primers should ask questions, not command
            assert not primer.material.startswith("MUST"), (
                f"primer should be evidentiary, not prescriptive: {primer.material}"
            )
            assert not primer.material.startswith("DO NOT"), (
                f"primer should be evidentiary, not prescriptive: {primer.material}"
            )
            # Evidence must be present and cite source
            assert primer.evidence, f"primer missing evidence: {primer}"

    def test_no_ranking_weights_in_material(self, tmp_path: Path) -> None:
        """Primers list items without assigning relative weights that could
        be interpreted as auto-applied loss modifiers."""
        store = _populate_synthetic_project(tmp_path)
        aggregate_and_write(store)
        memory = read_memory(store)

        material = prime_antithesis(
            memory=memory, thesis="retry-variant and e2e-driven-iteration combined",
        )
        # Severity is a hint, not a weight
        for p in material.primers:
            assert p.severity in ("high", "warn", "info")
        # Agent contract explicitly requires synthesis to decide
        assert "reconcile or reject" in material.summary.lower() or \
               material.summary == "Memory has insufficient signal to prime antithesis. " \
                                  "Run the standard dialectical pass with generic counter-cases."


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
