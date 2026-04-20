# Scenario-2 notes — root-cause-by-layer

## Why a second scenario

The primary scenario (`../scenario.md`) is a notifier/domain-boundary contract violation. A single scenario authored by the skill's author creates design-bias risk: the failure mode in the scenario was specifically crafted to showcase the 5-layer diagnosis. A skill that only works on scenarios it was designed against does not generalize.

This scenario exercises the same skill (`root-cause-by-layer`) against a **different domain**:
- **Primary:** notifier expects dict, caller passes dataclass — domain↔integration boundary leak
- **Scenario-2:** rate-limiter `_buckets[client_id]` without prior `register_client()` — **missing-precondition contract violation**, different layer shape

Same skill, different shape of contract violation. A GREEN response should:

1. Walk 5 layers: Symptom → Mechanism (dict lookup on unregistered key) → Contract (`register_client` docstring states "must be called before allow()") → Structural origin (state-initialization responsibility at API boundary) → Conceptual origin (implicit-over-explicit precondition)
2. Fix at named layer — options: (a) auto-register in `allow()` if not present; (b) raise `ClientNotRegisteredError` with a clearer message so the caller knows to register first; (c) have the `middleware` register on first-seen client
3. Neither: `try/except KeyError`, `dict.get('requests_this_minute', 0)`, `setdefault` without owning the choice — all are symptom patches that hide the precondition contract

## Expected RED failure modes

Base LLMs tend to reach for:
- `self._buckets.setdefault(client_id, {'requests_this_minute': 0})` inside `allow()` — fixes the test, but silently creates an implicit auto-register path that contradicts the docstring
- `try/except KeyError: return True` — lets unregistered clients through (security issue)
- `dict.get(...)` with default — similar to setdefault

All three violate rubric item 7 (no symptom-patch patterns) and item 3 (identify the contract — the docstring says `register_client` MUST be called first; fixing `allow()` to tolerate unregistered clients silently changes the contract).

## How to run

```bash
export OPENROUTER_API_KEY=...
python scripts/capture-clean-baseline.py \
  tests/fixtures/root-cause-by-layer/scenario-2/scenario.md \
  --temperature 0.8 \
  --out tests/fixtures/root-cause-by-layer/scenario-2/runs/$(date -u +%Y%m%dT%H%M%SZ)/red.md
```

Score against `../rubric.md` (the same rubric applies — it is skill-level, not scenario-level).

## What this partially addresses

- **Scenario-design bias** (partial): two scenarios across two domains by the same author reduces single-point-of-failure risk, but does not eliminate author bias. True unbiased measurement requires community-contributed scenarios.
- **N=1 point estimate** (partial): per-fixture N=1 can at least be combined across fixtures for a bundle-level distribution.

Open invitation: adopter PRs with new scenarios per skill will close the remaining bias.
