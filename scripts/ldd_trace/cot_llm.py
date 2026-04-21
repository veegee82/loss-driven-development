"""LLM client implementations for the dialectical-CoT harness.

Two implementations ship:
  - MockCotLLMClient — deterministic, scripted; used by tests and for
    offline demonstration of the protocol
  - OpenRouterCotLLMClient — optional; activates if `OPENROUTER_API_KEY`
    env var is set. Uses the OpenRouter HTTP API directly (stdlib-only;
    no heavy SDK dependency)
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Callable, List, Optional

from ldd_trace.cot import (
    Antithesis,
    ProposedStep,
    Step,
    SynthesisOutput,
)


# ---------------------------------------------------------------------------
# Mock — deterministic, scripted. Used for tests.
# ---------------------------------------------------------------------------


@dataclass
class ScriptedTurn:
    """One scripted LLM turn — the Mock follows a queue of these in order.

    For propose_step: use `thesis` + `prior`.
    For attack_step: use `antitheses`.
    For synthesize: use `synthesis_content` + `synthesis_decision`.
    For is_answer_reached / extract_answer / verify_answer: use `answer_flag`,
    `extracted_answer`, `verified`.
    """

    thesis: Optional[str] = None
    prior: Optional[float] = None
    antitheses: List[Antithesis] = field(default_factory=list)
    synthesis_content: Optional[str] = None
    answer_flag: Optional[bool] = None
    extracted_answer: Optional[str] = None
    verified: Optional[bool] = None
    tokens: int = 10


class MockCotLLMClient:
    """Scripted LLM for deterministic testing.

    Constructed with a list of ScriptedTurns OR individual per-method callables.
    Each LLM call consumes the next relevant scripted value. Running past the
    end of the script raises AssertionError (test writers must provide enough).

    This mimics how the user would plug in a real LLM — same protocol, but
    responses are scripted.
    """

    def __init__(
        self,
        propose_queue: Optional[List[ProposedStep]] = None,
        attack_queue: Optional[List[List[Antithesis]]] = None,
        synth_queue: Optional[List[SynthesisOutput]] = None,
        answer_reached_at_step: Optional[int] = None,
        extract_answer_fn: Optional[Callable[[List[Step]], str]] = None,
        verify_fn: Optional[Callable[[str, Optional[str]], Optional[bool]]] = None,
    ) -> None:
        self._propose_queue = list(propose_queue or [])
        self._attack_queue = list(attack_queue or [])
        self._synth_queue = list(synth_queue or [])
        self._answer_reached_at_step = answer_reached_at_step
        self._extract_answer_fn = extract_answer_fn
        self._verify_fn = verify_fn

    def propose_step(self, task: str, task_type: str, chain: List[Step]) -> ProposedStep:
        if not self._propose_queue:
            raise AssertionError(
                f"MockCotLLMClient.propose_step called past script end (chain_len={len(chain)})"
            )
        return self._propose_queue.pop(0)

    def attack_step(
        self,
        task: str,
        thesis: str,
        chain: List[Step],
        skip_primers: bool = False,
    ) -> List[Antithesis]:
        if not self._attack_queue:
            return []
        return self._attack_queue.pop(0)

    def synthesize(
        self,
        thesis: str,
        thesis_prior: float,
        antitheses: List[Antithesis],
    ) -> SynthesisOutput:
        if not self._synth_queue:
            # Default: accept thesis as-is with prior as predicted (the runner
            # recomputes authoritative number — this is just filler)
            return SynthesisOutput(
                content=thesis, predicted_correct=thesis_prior, decision="commit"
            )
        return self._synth_queue.pop(0)

    def is_answer_reached(self, chain: List[Step]) -> bool:
        if self._answer_reached_at_step is None:
            return False
        return len(chain) >= self._answer_reached_at_step

    def extract_answer(self, chain: List[Step]) -> str:
        if self._extract_answer_fn is not None:
            return self._extract_answer_fn(chain)
        # Default: use the last step's synthesis
        return chain[-1].synthesis if chain else ""

    def verify_answer(
        self, answer: str, ground_truth: Optional[str]
    ) -> Optional[bool]:
        if self._verify_fn is not None:
            return self._verify_fn(answer, ground_truth)
        if ground_truth is None:
            return None
        return answer.strip() == ground_truth.strip()


# ---------------------------------------------------------------------------
# OpenRouter — optional, activates on env var. stdlib-only HTTP.
# ---------------------------------------------------------------------------


OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
DEFAULT_MODEL = os.environ.get("LDD_COT_MODEL", "openai/gpt-4o-mini")


class OpenRouterCotLLMClient:
    """Real-LLM client using OpenRouter's chat completions API.

    Activates when `OPENROUTER_API_KEY` env var is set. Uses urllib.request
    (stdlib only) to avoid heavy dependencies. Model defaults to
    `openai/gpt-4o-mini` but can be overridden via `LDD_COT_MODEL` env var.

    NOTE: this client makes the LLM prompts explicit — each method builds
    a prompt, sends it, parses the response. The prompt templates are tuned
    for the dialectical-CoT protocol: they ask the LLM to produce structured
    output (step + prior, antithesis list with probs and impacts, etc.).
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = DEFAULT_MODEL,
        timeout: float = 30.0,
    ) -> None:
        self.api_key = api_key or os.environ.get("OPENROUTER_API_KEY")
        if not self.api_key:
            raise RuntimeError(
                "OpenRouterCotLLMClient requires OPENROUTER_API_KEY env var"
            )
        self.model = model
        self.timeout = timeout

    def _call(self, messages: List[dict]) -> tuple[str, int]:
        payload = json.dumps({"model": self.model, "messages": messages}).encode()
        req = urllib.request.Request(
            OPENROUTER_URL,
            data=payload,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                data = json.loads(resp.read())
        except urllib.error.URLError as exc:
            raise RuntimeError(f"OpenRouter call failed: {exc}") from exc
        content = data["choices"][0]["message"]["content"]
        tokens = data.get("usage", {}).get("total_tokens", 0)
        return content, tokens

    def propose_step(
        self, task: str, task_type: str, chain: List[Step]
    ) -> ProposedStep:
        chain_str = "\n".join(
            f"Step {s.k}: {s.synthesis}" for s in chain
        )
        prompt = (
            f"Task ({task_type}): {task}\n\n"
            f"Chain so far:\n{chain_str if chain_str else '(empty)'}\n\n"
            f"Propose the next reasoning step. Respond as JSON:\n"
            f'{{"step": "<one-line next reasoning move>", "prior": <float in [0,1], your self-rated probability the step is correct>}}'
        )
        content, tokens = self._call([{"role": "user", "content": prompt}])
        parsed = _parse_json_block(content)
        return ProposedStep(
            content=parsed.get("step", "(malformed)"),
            prior=float(parsed.get("prior", 0.5)),
            tokens=tokens,
        )

    def attack_step(
        self,
        task: str,
        thesis: str,
        chain: List[Step],
        skip_primers: bool = False,
    ) -> List[Antithesis]:
        chain_str = "\n".join(
            f"Step {s.k}: {s.synthesis}" for s in chain
        )
        prompt = (
            f"Task: {task}\n\n"
            f"Chain so far:\n{chain_str if chain_str else '(empty)'}\n\n"
            f"Proposed next step: {thesis}\n\n"
            f"Attack this step. Generate 1–3 counter-cases — reasons this step "
            f"might be wrong. Respond as JSON array:\n"
            f'[{{"content": "<counter-case>", "prob_applies": <float [0,1]>, "impact": <float [-1,+1] — effect on correctness if applies>}}, ...]\n'
            f"If you cannot think of a counter-case, return []."
        )
        content, tokens = self._call([{"role": "user", "content": prompt}])
        parsed = _parse_json_block(content)
        out: List[Antithesis] = []
        if isinstance(parsed, list):
            for item in parsed:
                out.append(
                    Antithesis(
                        source="independent",
                        content=item.get("content", ""),
                        prob_applies=float(item.get("prob_applies", 0.3)),
                        impact=float(item.get("impact", -0.2)),
                        provenance="llm-independent",
                    )
                )
        return out

    def synthesize(
        self,
        thesis: str,
        thesis_prior: float,
        antitheses: List[Antithesis],
    ) -> SynthesisOutput:
        anti_str = "\n".join(
            f"- {a.content} (prob={a.prob_applies:.2f}, impact={a.impact:+.2f})"
            for a in antitheses
        )
        prompt = (
            f"Thesis (self-rated prior {thesis_prior:.2f}):\n{thesis}\n\n"
            f"Antitheses:\n{anti_str if anti_str else '(none)'}\n\n"
            f"Produce synthesis. If antitheses force revision, rewrite the step. "
            f"Otherwise restate the thesis. Respond as JSON:\n"
            f'{{"content": "<synthesized step>", "decision": "commit"|"revise"|"reject"}}'
        )
        content, tokens = self._call([{"role": "user", "content": prompt}])
        parsed = _parse_json_block(content)
        return SynthesisOutput(
            content=parsed.get("content", thesis),
            # predicted_correct is recomputed authoritatively by the runner
            predicted_correct=thesis_prior,
            decision=parsed.get("decision", "commit"),
            tokens=tokens,
        )

    def is_answer_reached(self, chain: List[Step]) -> bool:
        if not chain:
            return False
        last = chain[-1].synthesis.lower()
        return (
            "answer:" in last
            or "final answer" in last
            or last.startswith("answer ")
        )

    def extract_answer(self, chain: List[Step]) -> str:
        if not chain:
            return ""
        last = chain[-1].synthesis
        for marker in ("Answer:", "answer:", "Final answer:"):
            if marker in last:
                return last.split(marker, 1)[1].strip()
        return last.strip()

    def verify_answer(
        self, answer: str, ground_truth: Optional[str]
    ) -> Optional[bool]:
        if ground_truth is None:
            return None
        return answer.strip() == ground_truth.strip()


def _parse_json_block(text: str):
    """Parse a JSON object or array from LLM text, tolerating markdown fences."""
    text = text.strip()
    if text.startswith("```"):
        # strip ```json ... ``` fences
        text = text.split("```", 2)[1]
        if text.lower().startswith("json"):
            text = text[4:]
        text = text.strip().rstrip("`").strip()
    # Find first JSON-looking substring
    first_brace = min(
        i for i in (text.find("{"), text.find("[")) if i >= 0
    ) if text.find("{") >= 0 or text.find("[") >= 0 else -1
    if first_brace < 0:
        return {}
    # Best-effort: decode from first brace to end
    try:
        return json.loads(text[first_brace:])
    except json.JSONDecodeError:
        # Try to find balanced pair
        depth = 0
        opener = text[first_brace]
        closer = "}" if opener == "{" else "]"
        for i in range(first_brace, len(text)):
            if text[i] == opener:
                depth += 1
            elif text[i] == closer:
                depth -= 1
                if depth == 0:
                    try:
                        return json.loads(text[first_brace : i + 1])
                    except json.JSONDecodeError:
                        return {}
        return {}
