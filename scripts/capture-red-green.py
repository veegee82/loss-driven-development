#!/usr/bin/env python3
"""Capture paired RED/GREEN baselines for a multi-scenario fixture.

Extends the single-prompt `capture-clean-baseline.py` pattern to:

- take multiple named scenario prompts
- call the LLM twice per scenario — once without the skill content (RED),
  once with the skill content prepended as a system message (GREEN)
- write `red.md` / `green.md` under `<fixture>/runs/<timestamp>/<scenario>/`

No agent harness, no tool use, no ambient methodology — one direct API call
per RED/GREEN capture, same OpenRouter / OpenAI / Anthropic provider fallback
as the sibling script.

Usage:
    export OPENROUTER_API_KEY=...          # or OPENAI / ANTHROPIC
    python scripts/capture-red-green.py \\
        --fixture tests/fixtures/architect-mode-auto-dispatch \\
        --skill-files skills/using-ldd/SKILL.md skills/architect-mode/SKILL.md \\
        --scenarios bugfix-skip:"fix the off-by-one..." \\
                    greenfield-inventive:"prototype a new consistency protocol..." \\
        --model openai/gpt-5-mini \\
        --temperature 0.7 \\
        --run-dir runs/20260421T120000Z-clean

Scenarios can also live in a JSON file via `--scenarios-file <path>` with shape:
    {"bugfix-skip": "...", "greenfield-inventive": "...", ...}
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import time
from pathlib import Path
from urllib import error as _e
from urllib import request as _r

logging.basicConfig(format="%(message)s", level=logging.INFO)
log = logging.getLogger("capture-red-green")

PROVIDERS = {
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
    for env_var, (endpoint, default_model) in PROVIDERS.items():
        key = os.environ.get(env_var)
        if key:
            return key, endpoint, default_model
    log.error("no API key found. Set one of: %s", ", ".join(PROVIDERS.keys()))
    sys.exit(2)


def call_openai_style(
    api_key: str,
    endpoint: str,
    model: str,
    user_prompt: str,
    temperature: float,
    system_prompt: str | None = None,
) -> str:
    messages: list[dict[str, str]] = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": user_prompt})
    req = _r.Request(
        endpoint,
        method="POST",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        data=json.dumps(
            {
                "model": model,
                "messages": messages,
                "temperature": temperature,
            }
        ).encode("utf-8"),
    )
    with _r.urlopen(req, timeout=180) as resp:
        out = json.loads(resp.read())
    return out["choices"][0]["message"]["content"]


def call_anthropic(
    api_key: str,
    endpoint: str,
    model: str,
    user_prompt: str,
    temperature: float,
    system_prompt: str | None = None,
) -> str:
    payload: dict[str, object] = {
        "model": model,
        "max_tokens": 4096,
        "messages": [{"role": "user", "content": user_prompt}],
        "temperature": temperature,
    }
    if system_prompt:
        payload["system"] = system_prompt
    req = _r.Request(
        endpoint,
        method="POST",
        headers={
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
        },
        data=json.dumps(payload).encode("utf-8"),
    )
    with _r.urlopen(req, timeout=180) as resp:
        out = json.loads(resp.read())
    return out["content"][0]["text"]


def call_with_retry(
    api_key: str,
    endpoint: str,
    model: str,
    user_prompt: str,
    temperature: float,
    system_prompt: str | None,
) -> str:
    fn = call_anthropic if endpoint.endswith("/messages") else call_openai_style
    try:
        return fn(api_key, endpoint, model, user_prompt, temperature, system_prompt)
    except (_e.HTTPError, _e.URLError, TimeoutError) as exc:
        log.warning("first attempt failed (%s); retrying once after 30s backoff", exc)
        time.sleep(30)
        return fn(api_key, endpoint, model, user_prompt, temperature, system_prompt)


def parse_scenarios(args) -> dict[str, str]:
    if args.scenarios_file:
        data = json.loads(Path(args.scenarios_file).read_text())
        if not isinstance(data, dict):
            log.error("scenarios-file must be a JSON object (name → prompt)")
            sys.exit(2)
        return {str(k): str(v) for k, v in data.items()}
    scenarios: dict[str, str] = {}
    for raw in args.scenarios or []:
        if ":" not in raw:
            log.error("scenario %r missing 'name:prompt' format", raw)
            sys.exit(2)
        name, _, prompt = raw.partition(":")
        scenarios[name.strip()] = prompt.strip()
    if not scenarios:
        log.error("no scenarios provided (use --scenarios or --scenarios-file)")
        sys.exit(2)
    return scenarios


def build_system_prompt(skill_files: list[str]) -> str:
    chunks: list[str] = []
    for f in skill_files:
        body = Path(f).read_text()
        chunks.append(f"# --- {f} ---\n{body}")
    return "\n\n".join(chunks)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--fixture", required=True, help="Fixture dir root")
    ap.add_argument(
        "--skill-files",
        nargs="+",
        required=True,
        help="SKILL.md files to concat as system-message for GREEN runs",
    )
    ap.add_argument(
        "--scenarios",
        nargs="*",
        help="Inline scenarios: name:prompt pairs",
    )
    ap.add_argument(
        "--scenarios-file",
        help="JSON file {name: prompt} for scenarios (alternative to --scenarios)",
    )
    ap.add_argument("--model", default=None)
    ap.add_argument("--temperature", type=float, default=0.7)
    ap.add_argument(
        "--run-dir",
        required=True,
        help="Run dir relative to fixture (e.g. runs/20260421T120000Z-clean)",
    )
    args = ap.parse_args()

    scenarios = parse_scenarios(args)
    fixture_root = Path(args.fixture)
    run_root = fixture_root / args.run_dir
    run_root.mkdir(parents=True, exist_ok=True)

    api_key, endpoint, default_model = pick_provider()
    model = args.model or default_model

    green_system = build_system_prompt(args.skill_files)

    results: dict[str, dict[str, str]] = {}

    for name, prompt in scenarios.items():
        scenario_dir = run_root / name
        scenario_dir.mkdir(parents=True, exist_ok=True)
        log.info("[%s] capturing RED (no skill content)", name)
        red = call_with_retry(
            api_key, endpoint, model, prompt, args.temperature, system_prompt=None
        )
        log.info("[%s] capturing GREEN (with skill content)", name)
        green = call_with_retry(
            api_key, endpoint, model, prompt, args.temperature, system_prompt=green_system
        )
        header = (
            f"<!-- captured via scripts/capture-red-green.py\n"
            f"     model: {model}\n"
            f"     temperature: {args.temperature}\n"
            f"     scenario: {name}\n"
            f"     prompt: {prompt!r} -->\n\n"
        )
        (scenario_dir / "red.md").write_text(header + red)
        (scenario_dir / "green.md").write_text(header + green)
        results[name] = {"red_chars": str(len(red)), "green_chars": str(len(green))}
        log.info(
            "[%s] wrote red.md (%d chars) + green.md (%d chars)",
            name,
            len(red),
            len(green),
        )

    (run_root / "_capture_summary.json").write_text(
        json.dumps({"model": model, "temperature": args.temperature, "scenarios": results}, indent=2)
    )
    log.info("done: %d scenarios captured under %s", len(scenarios), run_root)
    return 0


if __name__ == "__main__":
    sys.exit(main())
