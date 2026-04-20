#!/usr/bin/env python3
"""Capture a clean RED baseline for any skill by calling the LLM directly —
no Claude Code, no agent harness, no ambient CLAUDE.md.

This bypasses the main contamination problem in LDD's RED measurement:
subagents in a Claude Code session inherit the ambient methodology file
and refuse to set it aside, which means baseline measurements for
discipline skills (especially `docs-as-definition-of-done`) are biased
toward compliance even without the skill loaded.

A direct API call has no such ambient influence — the model starts from
its base training only.

Usage:
    export OPENROUTER_API_KEY=...   # or OPENAI_API_KEY / ANTHROPIC_API_KEY
    python scripts/capture-clean-baseline.py \\
        tests/fixtures/<skill>/scenario.md \\
        --model openai/gpt-5-mini \\
        --out tests/fixtures/<skill>/runs/<ts>-clean/red.md

The output is the raw LLM response — no agent harness, no tool use.
Score it manually against the fixture's rubric.md.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from urllib import request as _r

PROVIDERS = {
    # key env var -> (endpoint, default model)
    "OPENROUTER_API_KEY": (
        "https://openrouter.ai/api/v1/chat/completions",
        "openai/gpt-5-mini",
    ),
    "OPENAI_API_KEY": (
        "https://api.openai.com/v1/chat/completions",
        "gpt-4o-mini",
    ),
    "ANTHROPIC_API_KEY": (
        "https://api.anthropic.com/v1/messages",
        "claude-haiku-4-5",
    ),
}


def pick_provider() -> tuple[str, str, str]:
    """Return (api_key, endpoint, default_model) for the first available provider."""
    for env_var, (endpoint, default_model) in PROVIDERS.items():
        key = os.environ.get(env_var)
        if key:
            return key, endpoint, default_model
    print(
        "error: no API key found. Set one of: "
        + ", ".join(PROVIDERS.keys()),
        file=sys.stderr,
    )
    sys.exit(2)


def call_openai_style(api_key: str, endpoint: str, model: str, prompt: str, temperature: float) -> str:
    req = _r.Request(
        endpoint,
        method="POST",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        data=json.dumps({
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
        }).encode("utf-8"),
    )
    with _r.urlopen(req, timeout=120) as resp:
        out = json.loads(resp.read())
    return out["choices"][0]["message"]["content"]


def call_anthropic(api_key: str, endpoint: str, model: str, prompt: str, temperature: float) -> str:
    req = _r.Request(
        endpoint,
        method="POST",
        headers={
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
        },
        data=json.dumps({
            "model": model,
            "max_tokens": 4096,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
        }).encode("utf-8"),
    )
    with _r.urlopen(req, timeout=120) as resp:
        out = json.loads(resp.read())
    return out["content"][0]["text"]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("scenario", help="Path to scenario.md (or any prompt file)")
    ap.add_argument("--model", default=None, help="Model identifier (defaults per provider)")
    ap.add_argument("--temperature", type=float, default=0.7)
    ap.add_argument("--out", default=None, help="Output file (default: stdout)")
    args = ap.parse_args()

    prompt = Path(args.scenario).read_text()
    api_key, endpoint, default_model = pick_provider()
    model = args.model or default_model

    if endpoint.endswith("/messages"):
        text = call_anthropic(api_key, endpoint, model, prompt, args.temperature)
    else:
        text = call_openai_style(api_key, endpoint, model, prompt, args.temperature)

    header = (
        f"<!-- captured via scripts/capture-clean-baseline.py\n"
        f"     model: {model}\n"
        f"     temperature: {args.temperature}\n"
        f"     scenario: {args.scenario} -->\n\n"
    )
    out = header + text

    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(out)
        print(f"wrote {args.out}")
    else:
        print(out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
