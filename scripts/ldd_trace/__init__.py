"""ldd_trace — persistence + rendering for the LDD trace block.

Added in v0.5.1. Extracts the render logic from `scripts/demo-trace-chart.py`
into a reusable module, and wraps it with a `.ldd/trace.log` persistence
layer and a CLI.

The trace block is mandatory after every iteration (see
`skills/using-ldd/SKILL.md` § "When to emit"). This module makes
compliance cheap enough that skipping is no longer rational.

Public API:
    renderer.sparkline / mini_chart / trend_arrow / render_trace
    store.TraceStore        — read/write .ldd/trace.log
    cli.main                — `python -m ldd_trace ...` entry point
"""
from __future__ import annotations

__version__ = "0.7.0"

from ldd_trace.renderer import (
    Iteration,
    Task,
    mini_chart,
    render_trace,
    sparkline,
    trend_arrow,
)
from ldd_trace.store import TraceStore, TraceEntry
from ldd_trace.dialectical_prime import (
    AntithesisMaterial,
    Primer,
    format_antithesis_material,
    prime_antithesis,
)

__all__ = [
    "__version__",
    "Iteration",
    "Task",
    "sparkline",
    "mini_chart",
    "trend_arrow",
    "render_trace",
    "TraceStore",
    "TraceEntry",
    "AntithesisMaterial",
    "Primer",
    "format_antithesis_material",
    "prime_antithesis",
]
