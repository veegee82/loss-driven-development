# LDD in AWP — where this came from, and what it looks like at scale

> **TL;DR.** Loss-Driven Development is distilled from [**AWP — Agent Workflow Protocol**](https://github.com/veegee82/agent-workflow-protocol), an open standard for multi-agent orchestration. AWP *runs* the LDD discipline on a 200k-line codebase: three of the [four gradients](../theory.md) — inner, refinement, outer — are implemented as live SGD code (delegation loop + `awp refine` + `awp optimize --with-textgrad`). The fourth gradient (CoT, v0.8.0) is in LDD itself via `dialectical-cot`; AWP does not yet ship it as a runtime feature. If LDD's Gradient-Descent-for-Agents framing makes sense to you at the skill level, AWP shows what it looks like when the whole system is built around it.

- **GitHub:** [`veegee82/agent-workflow-protocol`](https://github.com/veegee82/agent-workflow-protocol)
- **PyPI:** [`awp-agents`](https://pypi.org/project/awp-agents/) — `pip install awp-agents && python -m awp studio`
- **Philosophy:** AWP's own [`CLAUDE.md`](https://github.com/veegee82/agent-workflow-protocol/blob/main/CLAUDE.md) is the source document that LDD was distilled from.

This page does three things: (1) shows the one-to-one mapping from **AWP concepts** to **LDD skills**, (2) walks a concrete debugging moment in AWP that LDD-users will recognize, and (3) points AWP-curious readers at the right parts of the AWP repo.

---

## 1. The mapping: AWP → LDD

Every LDD skill has a direct AWP origin. The table below pairs them. If you want to see the production-scale instantiation of any LDD skill, follow the AWP link in the second column.

| LDD skill | AWP origin | Where to read it |
|---|---|---|
| `root-cause-by-layer` | **§3 Debugging Discipline** — the 5-Why-by-Layer protocol (Symptom → Mechanism → Contract → Structural origin → Conceptual origin) is verbatim from AWP's role-definition in `CLAUDE.md` | [`CLAUDE.md` §3](https://github.com/veegee82/agent-workflow-protocol/blob/main/CLAUDE.md#3-debugging-discipline-structural--conceptual-root-cause-analysis) |
| `loss-backprop-lens` | **§4 Loss & Backprop: the ML Lens** — AWP models the whole development process as SGD over code, with a full mapping (forward pass / loss / gradient / learning rate / regularization) | [`CLAUDE.md` §4](https://github.com/veegee82/agent-workflow-protocol/blob/main/CLAUDE.md#4-loss--backprop-the-ml-lens) |
| `dialectical-reasoning` | **§5 Dialectical Reasoning** — every non-trivial analysis passes through thesis → antithesis → synthesis before it's admissible | [`CLAUDE.md` §5](https://github.com/veegee82/agent-workflow-protocol/blob/main/CLAUDE.md#5-dialectical-reasoning-thesis--antithesis--synthesis) |
| `docs-as-definition-of-done` | **§2 Doc Sync as Definition-of-Done** — enforced by four mechanical gates (`check_docs_drift.py`, `check_sync_coverage.py`, `check_mirror_drift.py`, edit reminder hook) that block commits | [`CLAUDE.md` §2](https://github.com/veegee82/agent-workflow-protocol/blob/main/CLAUDE.md#2-doc-sync-as-definition-of-done) |
| `loop-driven-engineering` | **§1 Session Start Protocol + K_MAX=5 work loop + test pyramid** — the budget-bounded inner loop is AWP's default working rhythm | [`CLAUDE.md` §1](https://github.com/veegee82/agent-workflow-protocol/blob/main/CLAUDE.md#1-session-start-protocol) |
| `reproducibility-first` | **"No update on a single sample"** — §4 Rule 1 of the ML Lens, operationalized in AWP's E2E monitoring (`docs/e2e.md`) | [`CLAUDE.md` §4 Rule 1](https://github.com/veegee82/agent-workflow-protocol/blob/main/CLAUDE.md#4-loss--backprop-the-ml-lens) |
| `e2e-driven-iteration` | **AWP's E2E Tests section + Active Monitoring** — E2E is defined normatively (rubric, tags, artifacts, terminal status) and every E2E failure triggers the 5-Why-by-Layer walk | [`docs/e2e.md`](https://github.com/veegee82/agent-workflow-protocol/blob/main/docs/e2e.md) |
| `iterative-refinement` | **Refinement Mode (`awp refine`)** — y-axis SGD on a completed run's deliverable. Gradient = critique defects + gate rejections + eval deltas. Budget halves per iteration. R36 aborts on empty gradient. This is **live code**, not a metaphor. | [`docs/refinement.md`](https://github.com/veegee82/agent-workflow-protocol/blob/main/docs/refinement.md) + `packages/awp-runtime/src/awp/refinement/` |
| `method-evolution` | **Outer Loop (`awp optimize --with-textgrad`)** — θ-axis SGD on prompt artifacts, with TextGrad as the LLM-as-optimizer, rollback on `mean_loss` regression, halved learning rate on regression. **Also live code.** | [`packages/awp-runtime/src/awp/outer_loop/`](https://github.com/veegee82/agent-workflow-protocol/tree/main/packages/awp-runtime/src/awp/outer_loop) |
| `drift-detection` | **The three drift-check scripts** — `check_docs_drift.py`, `check_sync_coverage.py`, `check_mirror_drift.py`. Each runs on every commit and blocks merges on violation. | [`scripts/`](https://github.com/veegee82/agent-workflow-protocol/tree/main/scripts) |

**Observation:** LDD is the portable discipline. AWP is the production system where three of these skills are not just disciplines but actual SGD implementations running against real LLMs. If you find yourself wishing LDD's `method-evolution` had a TextGrad backend, that's because one exists — it's called `awp optimize`.

## 2. A concrete moment: LDD discipline in AWP debugging

A real-shaped debugging moment inside AWP — the kind of thing LDD is built for.

**Symptom (layer 1).** An E2E run of an A2 workflow terminates `partial` with reason `max_rejected_completions`.

**Mechanism (layer 2).** The manager's COMPLETE attempt passes through AWP's completion gate chain — `l0 → critique → deliverable_presence → placeholder → file → deliverable → structural_integrity → eval` — and is rejected twice. On the third attempt, the circuit breaker fires and the run terminates.

**Contract (layer 3).** AWP's R17 says every agent `run()` returns `{self.name: {"confidence": 0.0-1.0, ...}}`. The manager is satisfying this. But the **completion-gate contract** says: when a gate rejects, the manager receives a repair nudge naming the specific defect; the manager should either address the defect or derive a repair subtask. In this run, the manager received the rejection but re-attempted without addressing the named defect.

**Structural origin (layer 4).** The leak is between the **completion-gate chain** (which produces a human-readable rejection reason) and the **manager prompt** (which sees the reason, but as free text, not as a typed signal the manager is forced to consume). The repair-nudge is a suggestion, not a contract.

**Conceptual origin (layer 5).** **Implicit contract** between two adjacent components. The gate says "here's why I rejected." The manager reads it. Nothing enforces that the manager's next action must be causally tied to the rejection reason. Classical separation-of-concerns violation: the *routing* of the rejection to a manager action is nowhere.

**LDD-style fix.** Not a `try/except` around the rejection. Not a wider `max_rejected_completions` cap (that would be `loss-backprop-lens` red-flag #3 — widening thresholds). The structural fix: make the repair-nudge a **typed field** the manager must acknowledge before its next DELEGATE is accepted. In AWP-terms: extend the repair-fixpoint-guard (R35) to also guard the nudge→action causality.

**What LDD contributes.** The 5-Why-by-Layer forced us past "just make it retry more." The `loss-backprop-lens` refused a threshold-widen. `dialectical-reasoning` made us ask "what would a hostile reviewer say about extending the cap?" (answer: "you're papering over a structural defect"). `docs-as-definition-of-done` reminds that the fix needs to show up in `docs/runtime.md`, `CLAUDE.md` Key Protocols section, and R35's normative text.

**This is what LDD looks like on a 200k-line codebase.** The skills are not cute — they are load-bearing.

## 3. Why you might want AWP itself

If LDD's *discipline* appeals to you, three AWP concepts go further and are worth knowing even if you don't use AWP as your runtime:

### 3.1 The 7 semantic layers

AWP separates workflow definition (YAML) from implementation (Python) across **7 semantic layers**: manifest, identity, capabilities, communication, memory, orchestration, observability. Each layer has its own normative rules (R1–R36) enforced by a deterministic validator before any LLM work happens.

Why it matters for LDD-users: the layer model is how AWP gives `root-cause-by-layer` concrete layer names instead of generic ones. If you want to see what "structurally and conceptually grounded layer model" looks like beyond the LDD skill's generic `domain/integration/transport/persistence/UI`, read [`spec/`](https://github.com/veegee82/agent-workflow-protocol/tree/main/spec).

### 3.2 The autonomy spectrum (A0–A4)

Workflows sit on an axis from A0 (fully prescribed DAG) through A4 (self-organizing recursive delegation). Each level has explicit rules about what the agent can and cannot decide. This is the multi-agent equivalent of LDD's step-size discipline: match the autonomy to the problem, don't let A4 code do A1 things or vice versa.

Why it matters: the autonomy-spectrum idea is more general than AWP. If you build multi-agent systems, this is the clearest formalism I know.

### 3.3 Three of the four SGD loops in code

The four-loop model in [`docs/ldd/convergence.md`](./convergence.md) is **not theoretical** in AWP — three of the four gradients are implemented as running code:

- **Inner loop** (`∂L/∂code`) — the DAG engine and the delegation-loop engine in `packages/awp-runtime/src/awp/runtime/`
- **Refinement loop** (`∂L/∂output`) — `awp refine`, authoritative at [`docs/refinement.md`](https://github.com/veegee82/agent-workflow-protocol/blob/main/docs/refinement.md)
- **Outer loop** (`∂L/∂method`) — `awp optimize --with-textgrad`, code at [`packages/awp-runtime/src/awp/outer_loop/`](https://github.com/veegee82/agent-workflow-protocol/tree/main/packages/awp-runtime/src/awp/outer_loop)

The fourth gradient (**CoT loop**, `∂L/∂thought`, v0.8.0) is in LDD itself via [`skills/dialectical-cot/SKILL.md`](../../skills/dialectical-cot/SKILL.md); AWP does not yet ship it as a runtime feature — an open item for a future AWP version.

If you want to see an LLM-based SGD-on-prompts run live, clone AWP, run `awp optimize` on one of the example suites, and watch epoch-by-epoch `mean_loss` change.

## 4. Try AWP

```bash
# Minimum viable
pip install awp-agents
python -m awp studio  # opens the workflow UI on localhost

# Full development install (from source)
git clone https://github.com/veegee82/agent-workflow-protocol.git
cd agent-workflow-protocol
pip install -e packages/awp-core/
pip install -e "packages/awp-runtime/[data]"
pytest packages/awp-core/tests/ packages/awp-runtime/tests/ -k "not e2e"
```

Start reading:

1. [`README.md`](https://github.com/veegee82/agent-workflow-protocol/blob/main/README.md) — what AWP is, top-level
2. [`CLAUDE.md`](https://github.com/veegee82/agent-workflow-protocol/blob/main/CLAUDE.md) — the methodology LDD was distilled from, in AWP's native vocabulary
3. [`docs/refinement.md`](https://github.com/veegee82/agent-workflow-protocol/blob/main/docs/refinement.md) + [`docs/e2e.md`](https://github.com/veegee82/agent-workflow-protocol/blob/main/docs/e2e.md) — the two loops running as code
4. [`examples/`](https://github.com/veegee82/agent-workflow-protocol/tree/main/examples) — 18 runnable workflows progressing A0 → A4

## 5. Where LDD and AWP diverge (intentionally)

LDD is **portable** — it works in any coding agent with any project. It has no runtime. AWP is a runtime with its own protocol, its own model contracts (R1–R36), its own YAML schema, its own validator, its own UI. That's a much bigger surface area.

If you want the discipline without the framework: use LDD. If you want the discipline **running inside** a full multi-agent orchestration framework with a delegation loop and optimization loops built in: use AWP.

They're compatible. LDD can sit on top of AWP in an LDD-compliant Claude Code / Codex session *working on* AWP code. That's how the skills were originally tested.

---

## Credit

AWP is authored by Silvio Jurk (`silvio.jurk@googlemail.com` · [github.com/veegee82](https://github.com/veegee82)). LDD is the distilled, platform-agnostic form of AWP's role-definition `CLAUDE.md`. If LDD helped you, install [`awp-agents`](https://pypi.org/project/awp-agents/) and star the [AWP repo](https://github.com/veegee82/agent-workflow-protocol) — that's where the methodology comes from and where it gets pushed forward.
