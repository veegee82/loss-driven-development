"""LDD spectrum E2E — exercises every level × loop × creativity × v0.13.x feature.

Supersedes `demo-e2e-v013x.py` (which covered only the Fix 1/2/3 subset).
Each scenario drives the **real** `ldd_trace` API — no mocks — and emits one
self-contained trace block. The harness aggregates what each scenario
exercised into a coverage matrix so the reader can see, at a glance, which
parts of the LDD surface actually fired.

Scenario inventory (15 total):

    L0 reflex:
      1. typo-fix — one-line edit, no reproducibility-first, minimal trace
    L1 diagnostic:
      2. failing-test — reproducibility-first → root-cause-by-layer cascade
    L2 deliberate:
      3. cross-module bug — dialectical-reasoning + docs-as-definition-of-done
    L3 structural (creativity=standard):
      4. webhook-replay design — architect-mode 5-phase protocol
    L3 structural (creativity=conservative):
      5. HIPAA audit trail — architect-mode with novelty-penalty
    L4 method (creativity=inventive, explicit ack):
      6. novel consensus — inventive loss function, +prior-art penalty
    L4 method (creativity=inventive, CACHED ack):
      7. autonomous inventive — ack-cache activates inventive in unattended run
    v0.13.x Fix 1 — vector loss:
      8. IoT Byzantine — 3-dim Pareto with ⇓/⇔ arrows
    v0.13.x Fix 1 — epoch boundary:
      9. mid-task PSD2 shift — moving-target-loss with Δ n/a
    Refinement loop:
      10. arch-doc polish — iterative-refinement, y-axis only
    Outer loop:
      11. method-evolution — same rubric violation across 3 sibling tasks
    CoT loop:
      12. Collatz proof — dialectical-cot multi-step reasoning
    Drift-detection:
      13. quarterly audit — 7 indicators, actionable findings
    User overrides:
      14. LDD+ bump — natural-language "take your time" raises level
      15. LDD[level=L0] — explicit user-override-down, warning surfaced

Each scenario writes to its OWN sub-directory under `tests/e2e-spectrum/`
so the traces are independent and inspectable. At the end the harness
prints:
  * A coverage matrix  (level × loop × creativity × features)
  * Δloss_bundle       (by invoking scripts/compute-loss-bundle.py)
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))

from ldd_trace.ack_cache import AckCache
from ldd_trace.renderer import render_trace
from ldd_trace.store import TraceStore
from ldd_trace.vector_loss import VectorLoss

SUITE_ROOT = REPO / "tests" / "e2e-spectrum"
ACK_ROOT = SUITE_ROOT / "ldd-acks"


# ---------------------------------------------------------------------------
# Scenario result + registry
# ---------------------------------------------------------------------------


@dataclass
class Result:
    name: str
    level: str                         # "L0".."L4"
    creativity: Optional[str] = None   # None | standard | conservative | inventive
    loops_used: list[str] = field(default_factory=list)
    features: list[str] = field(default_factory=list)
    store: Optional[TraceStore] = None


def fresh_store(name: str, loops: list[str]) -> TraceStore:
    path = SUITE_ROOT / name
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)
    return TraceStore(path)


def banner(title: str) -> None:
    print(f"\n{'=' * 78}\n  {title}\n{'=' * 78}")


def show(store: TraceStore) -> None:
    print(render_trace(store.to_task()))


# ---------------------------------------------------------------------------
# Reactive levels — L0 / L1 / L2
# ---------------------------------------------------------------------------


def s01_L0_typo_fix() -> Result:
    banner("01 · L0/reflex — typo fix (single file, known solution)")
    store = fresh_store("01-L0-typo", ["inner"])
    store.init(
        task_title="fix typo in error message at api/handler.py:L42",
        loops=["inner"],
        level_chosen="L0",
        dispatch_source="auto",
        signals="explicit-bugfix:-5,single-file:-3",
    )
    store.append_iteration(
        loop="inner", k=0, skill="baseline", action="baseline",
        loss_norm=0.333, raw="1/3", baseline=True,
    )
    store.append_iteration(
        loop="inner", k=1, skill="e2e-driven-iteration",
        action='replace "recieved" → "received"',
        loss_norm=0.000, raw="0/3",
    )
    store.append_close(
        loop="inner", terminal="complete",
        layer="1: surface · no deeper layer", docs="N/A",
        loss_final=0.0,
    )
    show(store)
    return Result("01-L0-typo", "L0", None, ["inner"], ["scalar-loss"], store)


def s02_L1_failing_test() -> Result:
    banner("02 · L1/diagnostic — failing test (reproducibility + root-cause cascade)")
    store = fresh_store("02-L1-failing-test", ["inner"])
    store.init(
        task_title="checkout test fails intermittently on empty cart",
        loops=["inner"],
        level_chosen="L1",
        dispatch_source="auto",
        signals="explicit-bugfix:-5,ambiguous:+2,layer-crossings:+2",
    )
    store.append_iteration(
        loop="inner", k=0, skill="baseline", action="baseline 3/5 rubric violations",
        loss_norm=0.600, raw="3/5", baseline=True,
    )
    store.append_iteration(
        loop="inner", k=1, skill="reproducibility-first",
        action="5/5 reproducible when cart is empty — real bug",
        loss_norm=0.600, raw="3/5",
    )
    store.append_iteration(
        loop="inner", k=2, skill="root-cause-by-layer",
        action="layer 3 (input-contract): len-check before .first() access",
        loss_norm=0.200, raw="1/5",
    )
    store.append_iteration(
        loop="inner", k=3, skill="docs-as-definition-of-done",
        action="CHANGELOG + api-docs updated in same commit",
        loss_norm=0.000, raw="0/5",
    )
    store.append_close(
        loop="inner", terminal="complete",
        layer="3: input-contract · 5: len-check-before-access", docs="synced",
        loss_final=0.0,
    )
    show(store)
    return Result(
        "02-L1-failing-test", "L1", None, ["inner"],
        ["reproducibility-first", "root-cause-by-layer", "docs-as-definition-of-done"],
        store,
    )


def s03_L2_cross_module_bug() -> Result:
    banner("03 · L2/deliberate — cross-module bug (dialectical-reasoning + docs-sync)")
    store = fresh_store("03-L2-cross-module", ["inner"])
    store.init(
        task_title="auth middleware rejects valid JWT after clock skew fix",
        loops=["inner"],
        level_chosen="L2",
        dispatch_source="auto",
        signals="cross-layer:+2,layer-crossings:+2",
    )
    store.append_iteration(
        loop="inner", k=0, skill="baseline",
        action="baseline — 4 rubric items open",
        loss_norm=0.500, raw="4/8", baseline=True,
    )
    store.append_iteration(
        loop="inner", k=1, skill="dialectical-reasoning",
        action="thesis 'widen window' · antithesis 'widens replay window' · "
               "synthesis 'NTP-sync + 2s tolerance'",
        loss_norm=0.250, raw="2/8",
    )
    store.append_iteration(
        loop="inner", k=2, skill="loss-backprop-lens",
        action="sibling signatures checked — 3/3 consistent with new invariant",
        loss_norm=0.000, raw="0/8",
    )
    store.append_close(
        loop="inner", terminal="complete",
        layer="4: auth-invariant · 5: clock-authority-is-ntp", docs="synced",
        loss_final=0.0,
    )
    show(store)
    return Result(
        "03-L2-cross-module", "L2", None, ["inner"],
        ["dialectical-reasoning", "loss-backprop-lens"],
        store,
    )


# ---------------------------------------------------------------------------
# Structural — L3 (standard + conservative)
# ---------------------------------------------------------------------------


def s04_L3_standard_design() -> Result:
    banner("04 · L3/structural · standard — webhook-replay design (architect-mode)")
    store = fresh_store("04-L3-standard", ["design", "inner"])
    store.init(
        task_title="design webhook replay service (500 req/min, 6-8wk, team=2)",
        loops=["design", "inner"],
        level_chosen="L3",
        dispatch_source="auto",
        creativity="standard",
        signals="greenfield:+3,components>=3:+2,cross-layer:+2",
    )
    # 5-phase architect protocol
    for k, (skill, action, loss, raw) in enumerate([
        ("architect-mode (P1 constraints)", "7 requirements named, 2 uncertainties flagged", 0.900, "9/10"),
        ("architect-mode (P2 non-goals)",  "4 non-goals: not exactly-once, not multi-region", 0.800, "8/10"),
        ("architect-mode (P3 candidates)", "3 options on storage/replay axis (S3-index, Kafka-first, Postgres-JSONB)", 0.600, "6/10"),
        ("architect-mode (P4 scoring)",    "S3-index wins 27/30 after 6-dim scoring table", 0.300, "3/10"),
        ("architect-mode (P5 deliverable)","arch.md + scaffold + 6 failing tests", 0.000, "0/10"),
    ]):
        store.append_iteration(
            loop="design", k=k, skill=skill, action=action,
            loss_norm=loss, raw=raw, baseline=(k == 0),
        )
    store.append_close(
        loop="design", terminal="complete",
        layer="4: protocol-invariant · 5: idempotency-via-partition-key",
        docs="synced", loss_final=0.0,
    )
    show(store)
    return Result(
        "04-L3-standard", "L3", "standard", ["design"],
        ["architect-mode-5phase", "drift-detection-floor", "iterative-refinement-floor"],
        store,
    )


def s05_L3_conservative_compliance() -> Result:
    banner("05 · L3/structural · conservative — HIPAA audit trail")
    store = fresh_store("05-L3-conservative", ["design"])
    store.init(
        task_title="HIPAA-compliant PHI access audit (regulated, existing stack only)",
        loops=["design"],
        level_chosen="L3",
        dispatch_source="auto",
        creativity="conservative",
        signals="greenfield:+3,cross-layer:+2,contract-rule-hit:+2",
    )
    for k, (skill, action, loss, raw) in enumerate([
        ("architect-mode (P1 constraints)", "10 compliance constraints + 1 novelty-penalty row", 0.909, "10/11"),
        ("architect-mode (P2 non-goals)",  "'no new tech', 'no cross-region replication' explicit", 0.727, "8/11"),
        ("architect-mode (P3 candidates)", "3 candidates all using existing Postgres+Redis stack", 0.455, "5/11"),
        ("architect-mode (P4 scoring)",    "append-only-log wins; novelty ≤ 1 across all components", 0.182, "2/11"),
        ("architect-mode (P5 deliverable)","HIPAA-reviewed audit-trail design + rollback plan", 0.000, "0/11"),
    ]):
        store.append_iteration(
            loop="design", k=k, skill=skill, action=action,
            loss_norm=loss, raw=raw, baseline=(k == 0),
        )
    store.append_close(
        loop="design", terminal="complete",
        layer="4: audit-invariant · 5: append-only",
        docs="synced", loss_final=0.0,
    )
    show(store)
    return Result(
        "05-L3-conservative", "L3", "conservative", ["design"],
        ["architect-mode-5phase", "novelty-penalty"],
        store,
    )


# ---------------------------------------------------------------------------
# Method — L4 inventive (explicit ack + cached ack)
# ---------------------------------------------------------------------------


def s06_L4_inventive_explicit() -> Result:
    banner("06 · L4/method · inventive (EXPLICIT ack) — novel allocator")
    store = fresh_store("06-L4-inventive-explicit", ["design"])
    store.init(
        task_title="novel lock-free allocator for IoT edge devices (experimental paradigm)",
        loops=["design"],
        level_chosen="L4",
        dispatch_source="explicit",
        creativity="inventive",
        signals="greenfield:+3,components>=3:+2,cross-layer:+2,ambiguous:+2",
    )
    for k, (skill, action, loss, raw) in enumerate([
        ("architect-mode (P1)", "5 constraints + 3 known-unknowns declared", 0.857, "6/7"),
        ("architect-mode (P2)", "non-goals: not drop-in to libc malloc, not thread-safe across cores", 0.714, "5/7"),
        ("architect-mode (P3)", "baseline (slab) + 1 invention (hazard-hop) — 2 candidates is OK at inventive", 0.429, "3/7"),
        ("architect-mode (P4)", "PRIOR_ART.md: rejects Hazard-Pointer v1 and RCU — explicit why", 0.143, "1/7"),
        ("architect-mode (P5)", "prototype + EXPERIMENT.md + fallback-to-slab path", 0.000, "0/7"),
    ]):
        store.append_iteration(
            loop="design", k=k, skill=skill, action=action,
            loss_norm=loss, raw=raw, baseline=(k == 0),
        )
    store.append_close(
        loop="design", terminal="complete",
        layer="4: allocator-contract · 5: hazard-hop-invariant",
        docs="synced", loss_final=0.0,
    )
    show(store)
    return Result(
        "06-L4-inventive-explicit", "L4", "inventive", ["design"],
        ["architect-mode-5phase", "prior-art-penalty", "ack-explicit"],
        store,
    )


def s07_L4_inventive_cached() -> Result:
    banner("07 · L4/method · inventive (CACHED ack) — autonomous run")
    store = fresh_store("07-L4-inventive-cached", ["design"])
    # Pre-grant the cached ack so the "autonomous" run finds it.
    os.environ["LDD_ACK_ROOT"] = str(ACK_ROOT)
    if ACK_ROOT.exists():
        shutil.rmtree(ACK_ROOT)
    cache = AckCache()
    cache.grant("consensus-research", ttl_days=14)
    found = cache.check("consensus-research")
    print(f"  [cache] pre-granted consensus-research — check={found}")

    store.init(
        task_title="autonomous: explore novel BFT consensus for unreliable links",
        loops=["design"],
        level_chosen="L4",
        dispatch_source="auto",
        creativity="inventive",
        signals="greenfield:+3,ambiguous:+2,cross-layer:+2",
    )
    for k, (skill, action, loss, raw) in enumerate([
        ("architect-mode (P1)", "7 constraints + consensus-bound uncertainty flagged", 0.857, "6/7"),
        ("architect-mode (P2)", "non-goals: no global consensus, no strict serializability", 0.571, "4/7"),
        ("architect-mode (P3)", "baseline (Raft) + MPO-CRDT invention", 0.286, "2/7"),
        ("architect-mode (P5)", "prototype + fallback-to-Raft path documented", 0.000, "0/7"),
    ]):
        store.append_iteration(
            loop="design", k=k, skill=skill, action=action,
            loss_norm=loss, raw=raw, baseline=(k == 0),
        )
    store.append_close(
        loop="design", terminal="complete",
        layer="4: partial-order · 5: MPO-CRDT-merge", docs="synced",
        loss_final=0.0,
    )
    show(store)
    return Result(
        "07-L4-inventive-cached", "L4", "inventive", ["design"],
        ["architect-mode-5phase", "ack-cached", "autonomous-run"],
        store,
    )


# ---------------------------------------------------------------------------
# v0.13.x — vector loss + epoch marker
# ---------------------------------------------------------------------------


def s08_vector_pareto() -> Result:
    banner("08 · v0.13.x Fix 1 — vector loss (3-dim IoT Byzantine consensus)")
    store = fresh_store("08-vector-pareto", ["inner"])
    store.init(
        task_title="Byzantine consensus under 100ms + 1KB RAM",
        loops=["inner"],
        level_chosen="L4",
        dispatch_source="auto",
        creativity="inventive",
        signals="greenfield:+3,components>=3:+2,cross-layer:+2,ambiguous:+2",
    )
    vecs = [
        VectorLoss(dims=("latency", "memory", "correctness"),
                   values={"latency": 0.80, "memory": 0.60, "correctness": 0.40}),
        VectorLoss(dims=("latency", "memory", "correctness"),
                   values={"latency": 0.50, "memory": 0.40, "correctness": 0.20}),
        VectorLoss(dims=("latency", "memory", "correctness"),
                   values={"latency": 0.65, "memory": 0.25, "correctness": 0.20}),
    ]
    actions = [
        ("baseline",        "HotStuff baseline — too heavy on RAM"),
        ("architect-mode",  "MPO-CRDT — Pareto ⇓ vs baseline"),
        ("loss-backprop-lens", "compact lattice-merge — Pareto ⇔ trade-off (RAM↓, latency↑)"),
    ]
    for k, (v, (skill, act)) in enumerate(zip(vecs, actions)):
        mean = sum(v.values.values()) / len(v.values)
        store.append_iteration(
            loop="inner", k=k, skill=skill, action=act,
            loss_norm=round(mean, 3), raw=f"{int(mean * 10)}/10",
            loss_vec=v.dumps(), baseline=(k == 0),
        )
    store.append_close(
        loop="inner", terminal="complete",
        layer="4: protocol-invariant · 5: partial-order", docs="synced",
        loss_final=0.367,
    )
    show(store)
    return Result(
        "08-vector-pareto", "L4", "inventive", ["inner"],
        ["vector-loss", "pareto-⇔"],
        store,
    )


def s09_epoch_moving_target() -> Result:
    banner("09 · v0.13.x Fix 1 — epoch boundary (PSD2 SCA added mid-task)")
    store = fresh_store("09-epoch-moving-target", ["inner"])
    store.init(
        task_title="billing refund flow — requirements shift mid-task",
        loops=["inner"],
        level_chosen="L3",
        dispatch_source="auto",
        creativity="standard",
        signals="cross-layer:+2,ambiguous:+2,components>=3:+2",
    )
    store.append_iteration(
        loop="inner", k=0, skill="baseline", action="baseline under 8-item rubric",
        loss_norm=0.500, raw="4/8", baseline=True,
    )
    store.append_iteration(
        loop="inner", k=1, skill="e2e-driven-iteration",
        action="partial refunds guarded — 2/8",
        loss_norm=0.250, raw="2/8",
    )
    store.append_epoch_bump(
        new_epoch=1,
        reason="PSD2 SCA compliance added mid-task — rubric grew to 10 items",
    )
    store.append_iteration(
        loop="inner", k=2, skill="root-cause-by-layer",
        action="baseline under NEW 10-item rubric — 4/10 failing", baseline=True,
        loss_norm=0.400, raw="4/10", epoch=1,
    )
    store.append_iteration(
        loop="inner", k=3, skill="docs-as-definition-of-done",
        action="SCA challenge flow + docs updated — 0/10",
        loss_norm=0.000, raw="0/10", epoch=1,
    )
    store.append_close(
        loop="inner", terminal="complete",
        layer="3: PSD2-SCA-contract · 5: no-silent-fallback", docs="synced",
        loss_final=0.0,
    )
    show(store)
    return Result(
        "09-epoch-moving-target", "L3", "standard", ["inner"],
        ["epoch-bump", "Δ-suppression"],
        store,
    )


# ---------------------------------------------------------------------------
# Loops — refinement + outer + CoT
# ---------------------------------------------------------------------------


def s10_refinement_polish() -> Result:
    banner("10 · Refinement loop — polish architecture document (y-axis only)")
    store = fresh_store("10-refinement-polish", ["refine"])
    store.init(
        task_title="polish arch.md for clarity + pending-decisions section",
        loops=["refine"],
        level_chosen="L2",
        dispatch_source="auto",
        signals="ambiguous:+2",
    )
    for k, (action, loss, raw) in enumerate([
        ("baseline: 6 reviewer nits open", 0.600, "6/10"),
        ("reorder trade-off section before decision table", 0.400, "4/10"),
        ("add pending-decisions.md pointer from arch.md", 0.200, "2/10"),
        ("proofread pass — 0 open nits", 0.000, "0/10"),
    ]):
        store.append_iteration(
            loop="refine", k=k, skill="iterative-refinement",
            action=action, loss_norm=loss, raw=raw, baseline=(k == 0),
        )
    store.append_close(
        loop="refine", terminal="complete",
        layer="(y-axis — no code change)", docs="synced",
        loss_final=0.0,
    )
    show(store)
    return Result(
        "10-refinement-polish", "L2", None, ["refine"],
        ["iterative-refinement"],
        store,
    )


def s11_outer_method_evolution() -> Result:
    banner("11 · Outer loop — method-evolution (same rubric violation × 3 tasks)")
    store = fresh_store("11-outer-method-evolution", ["inner", "outer"])
    store.init(
        task_title="evolve loss-backprop-lens rubric: 3 sibling tasks all false-reverted",
        loops=["inner", "outer"],
        level_chosen="L4",
        dispatch_source="auto",
        creativity="standard",  # will clamp to L3
        signals="components>=3:+2,cross-layer:+2,contract-rule-hit:+2,layer-crossings:+2",
    )
    # Inner (the task that surfaced the pattern)
    store.append_iteration(
        loop="inner", k=0, skill="baseline",
        action="3 tasks each reverted a legitimate exploration spike",
        loss_norm=0.667, raw="2/3", baseline=True,
    )
    store.append_iteration(
        loop="inner", k=1, skill="loss-backprop-lens",
        action="diagnose: revert-on-regression rule fires on announced exploration",
        loss_norm=0.333, raw="1/3",
    )
    store.append_close(
        loop="inner", terminal="handoff",
        layer="root cause at method layer, not code", docs="synced",
        loss_final=0.333,
    )
    # Outer: the rubric change
    store.append_iteration(
        loop="outer", k=0, skill="method-evolution",
        action="add 'announced-spike exception' to revert-on-regression rule",
        loss_norm=0.500, raw="1/2", baseline=True,
    )
    store.append_iteration(
        loop="outer", k=1, skill="method-evolution",
        action="3 sibling tasks re-run under new rubric — 3/3 no longer false-revert",
        loss_norm=0.000, raw="0/2",
    )
    store.append_close(
        loop="outer", terminal="complete",
        layer="method (loss-backprop-lens/SKILL.md)", docs="synced",
        loss_final=0.0,
    )
    show(store)
    return Result(
        "11-outer-method-evolution", "L3", "standard", ["inner", "outer"],
        ["method-evolution", "rubric-rollback"],
        store,
    )


def s12_cot_proof() -> Result:
    banner("12 · CoT loop — dialectical-cot multi-step reasoning (math)")
    store = fresh_store("12-cot-proof", ["cot"])
    store.init(
        task_title="prove finite Collatz stopping time for n ∈ [1, 2^30]",
        loops=["cot"],
        level_chosen="L4",
        dispatch_source="auto",
        creativity="standard",  # will clamp to L3
        signals="components>=3:+2,contract-rule-hit:+2,ambiguous:+2",
    )
    for k, (skill, action, loss, raw) in enumerate([
        ("dialectical-cot (step 1)", "thesis: brute-force iterate; antithesis: memory grows O(2^30)", 0.800, "4/5"),
        ("dialectical-cot (step 2)", "synthesis: iterate with 64-bit early-exit on known-finite set", 0.500, "2.5/5"),
        ("dialectical-cot (step 3)", "verify: cache hits 93 % after n=10^6 — finite-time bound holds",   0.200, "1/5"),
        ("dialectical-cot (step 4)", "proof complete; predicted Δ = -0.2, actual Δ = -0.2 (calibrated)", 0.000, "0/5"),
    ]):
        store.append_iteration(
            loop="cot", k=k, skill=skill, action=action,
            loss_norm=loss, raw=raw, baseline=(k == 0),
            predicted_delta=-0.2 if k == 3 else None,
        )
    store.append_close(
        loop="cot", terminal="complete",
        layer="(thought-axis — reasoning chain)", docs="synced",
        loss_final=0.0,
    )
    show(store)
    return Result(
        "12-cot-proof", "L3", "standard", ["cot"],
        ["dialectical-cot", "per-step-calibration"],
        store,
    )


# ---------------------------------------------------------------------------
# Drift-detection + user-override scenarios
# ---------------------------------------------------------------------------


def s13_drift_detection() -> Result:
    banner("13 · Drift-detection — quarterly audit across 7 indicators")
    store = fresh_store("13-drift-detection", ["outer"])
    store.init(
        task_title="quarterly drift sweep — 7 indicators + moving-target-loss (v0.13.x)",
        loops=["outer"],
        level_chosen="L2",
        dispatch_source="auto",
        signals="cross-layer:+2,layer-crossings:+2",
    )
    for k, (action, loss, raw) in enumerate([
        ("scan across 7 indicators — 3 findings surface", 0.429, "3/7"),
        ("triage: 2 immediate-fix, 1 method-evolution", 0.143, "1/7"),
        ("findings committed to drift-report-Q2.md",  0.000, "0/7"),
    ]):
        store.append_iteration(
            loop="outer", k=k, skill="drift-detection",
            action=action, loss_norm=loss, raw=raw, baseline=(k == 0),
        )
    store.append_close(
        loop="outer", terminal="complete",
        layer="(audit — no direct fix)", docs="synced",
        loss_final=0.0,
    )
    show(store)
    return Result(
        "13-drift-detection", "L2", None, ["outer"],
        ["drift-detection", "periodic-audit"],
        store,
    )


def s14_ldd_plus_bump() -> Result:
    banner("14 · User override — natural-language bump ('take your time')")
    store = fresh_store("14-ldd-plus-bump", ["inner"])
    store.init(
        task_title="refactor auth middleware (take your time, think carefully)",
        loops=["inner"],
        level_chosen="L3",
        dispatch_source="bump",
        creativity="standard",
        dispatched='user-bump from L2, fragment: "take your time"',
        signals="cross-layer:+2,layer-crossings:+2",
    )
    for k, (skill, action, loss, raw) in enumerate([
        ("baseline",              "auto-score would have given L2; +1 bumps to L3", 0.625, "5/8"),
        ("architect-mode (P1-2)", "constraints + non-goals tabled", 0.375, "3/8"),
        ("architect-mode (P3-5)", "3-candidate scoring → deliverable", 0.000, "0/8"),
    ]):
        store.append_iteration(
            loop="inner", k=k, skill=skill, action=action,
            loss_norm=loss, raw=raw, baseline=(k == 0),
        )
    store.append_close(
        loop="inner", terminal="complete",
        layer="3: auth-contract · 5: single-source-of-identity",
        docs="synced", loss_final=0.0,
    )
    show(store)
    return Result(
        "14-ldd-plus-bump", "L3", "standard", ["inner"],
        ["user-bump", "natural-language-override"],
        store,
    )


def s15_ldd_override_down() -> Result:
    banner("15 · User override — LDD[level=L0] explicit DOWN from L3")
    store = fresh_store("15-ldd-override-down", ["inner"])
    store.init(
        task_title="LDD[level=L0]: rename a helper function in utils.py — I know the scope",
        loops=["inner"],
        level_chosen="L0",
        dispatch_source="override-down",
        dispatched="user-override-down from L3. User accepts loss risk.",
        signals="cross-layer:+2,single-file:-3",
    )
    store.append_iteration(
        loop="inner", k=0, skill="baseline", action="baseline 1/2",
        loss_norm=0.500, raw="1/2", baseline=True,
    )
    store.append_iteration(
        loop="inner", k=1, skill="e2e-driven-iteration",
        action="rename + update 3 callers",
        loss_norm=0.000, raw="0/2",
    )
    store.append_close(
        loop="inner", terminal="complete",
        layer="1: surface", docs="N/A", loss_final=0.0,
    )
    show(store)
    return Result(
        "15-ldd-override-down", "L0", None, ["inner"],
        ["user-override-down", "loss-risk-accepted"],
        store,
    )


# ---------------------------------------------------------------------------
# Harness
# ---------------------------------------------------------------------------


SCENARIOS: list[Callable[[], Result]] = [
    s01_L0_typo_fix,
    s02_L1_failing_test,
    s03_L2_cross_module_bug,
    s04_L3_standard_design,
    s05_L3_conservative_compliance,
    s06_L4_inventive_explicit,
    s07_L4_inventive_cached,
    s08_vector_pareto,
    s09_epoch_moving_target,
    s10_refinement_polish,
    s11_outer_method_evolution,
    s12_cot_proof,
    s13_drift_detection,
    s14_ldd_plus_bump,
    s15_ldd_override_down,
]


def coverage_matrix(results: list[Result]) -> str:
    """Render a markdown-ish coverage matrix."""
    lines: list[str] = []
    lines.append("\n" + "=" * 78)
    lines.append("  Spectrum coverage matrix")
    lines.append("=" * 78)

    # Level × creativity coverage
    levels = ["L0", "L1", "L2", "L3", "L4"]
    creativs = ["—", "standard", "conservative", "inventive"]
    # Build a grid of N scenarios per cell
    grid: dict[tuple[str, str], list[str]] = {}
    for r in results:
        grid.setdefault((r.level, r.creativity or "—"), []).append(r.name)
    lines.append("\n  Level × Creativity:")
    header = f"    {'':<10} " + " ".join(f"{c:<13}" for c in creativs)
    lines.append(header)
    for lv in levels:
        row = f"    {lv:<10} "
        for cr in creativs:
            n = len(grid.get((lv, cr), []))
            row += f"{'✓ × ' + str(n) if n else '·':<13} "
        lines.append(row)

    # Loops fired
    all_loops = {"inner", "refine", "outer", "cot", "design"}
    loops_hit = set()
    for r in results:
        loops_hit.update(r.loops_used)
    lines.append("\n  Loops fired:")
    for loop in sorted(all_loops):
        hit = "✓" if loop in loops_hit else "·"
        scenarios = [r.name for r in results if loop in r.loops_used]
        lines.append(f"    {hit} {loop:<8} — {len(scenarios)} scenario(s): {', '.join(scenarios) if scenarios else '(none)'}")

    # Features
    lines.append("\n  Features exercised (v0.13.x + overrides):")
    feature_set: set[str] = set()
    for r in results:
        feature_set.update(r.features)
    for feat in sorted(feature_set):
        scenarios = [r.name for r in results if feat in r.features]
        lines.append(f"    ✓ {feat:<30} — {', '.join(scenarios)}")

    # Summary
    lines.append("\n  Totals:")
    lines.append(f"    scenarios   : {len(results)}")
    lines.append(f"    levels fired: {len({r.level for r in results})} / 5")
    lines.append(f"    loops fired : {len(loops_hit)} / {len(all_loops)}")
    lines.append(f"    features    : {len(feature_set)}")

    return "\n".join(lines)


def compute_loss_bundle() -> None:
    banner("Δloss_bundle — authoritative value from tests/fixtures/")
    script = REPO / "scripts" / "compute-loss-bundle.py"
    result = subprocess.run(
        [sys.executable, str(script)],
        capture_output=True, text=True, check=False,
    )
    print(result.stdout, end="")
    if result.stderr:
        print(result.stderr, end="", file=sys.stderr)


def main() -> int:
    if SUITE_ROOT.exists():
        shutil.rmtree(SUITE_ROOT)
    SUITE_ROOT.mkdir(parents=True)
    results = [fn() for fn in SCENARIOS]
    print(coverage_matrix(results))
    compute_loss_bundle()
    banner(f"Done — {len(results)} scenarios · artefacts in {SUITE_ROOT.relative_to(REPO)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
