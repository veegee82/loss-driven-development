"""E2E demo for v0.13.x Fix 1 (vector-loss + epoch) and Fix 2 (telemetry).

Runs four fictitious tasks end-to-end through the real `ldd_trace` API,
then prints the telemetry report so the user can see the new pipeline in
action. Fix 3 (ack-cache) is exercised in its own section — it does not
write to trace.log.

Each task is deliberately crafted to trigger a different weakness described
in the first analysis:

    T1 — Ordinary scalar bug-fix (L1 diagnostic) — baseline path; no vector
         loss, no epoch, no ack. Shows Fix 2 meta-line signals round-trip.
    T2 — Pareto-multi-objective (L4 method · inventive; IoT Byzantine
         consensus — three objectives trade off). Demonstrates Fix 1 vector
         loss + dominance check.
    T3 — Moving-target mid-task (L3 structural; requirements shift after
         iteration 2). Demonstrates Fix 1 epoch boundary.
    T4 — Autonomous inventive (L4 method · inventive, pre-granted family)
         demonstrates Fix 3 ack-cache activation.

The script creates a fresh `.ldd/trace.log` under tests/e2e-demos/ so no
production state is touched.
"""
from __future__ import annotations

import json
import os
import shutil
import sys
from pathlib import Path

# Make the repo's scripts/ importable regardless of how this file is run.
REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))

from ldd_trace.ack_cache import AckCache
from ldd_trace.aggregator import dispatch_accuracy
from ldd_trace.renderer import render_trace
from ldd_trace.store import TraceStore
from ldd_trace.vector_loss import VectorLoss


DEMO_DIR = REPO / "tests" / "e2e-demos" / "v013x"
ACK_ROOT = DEMO_DIR / "ldd-acks"


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def section(title: str) -> None:
    print(f"\n{'=' * 78}\n{title}\n{'=' * 78}")


def task_store(subdir: str) -> TraceStore:
    """Fresh TraceStore — each demo task gets its own project dir so the
    aggregator sees them as separate tasks."""
    path = DEMO_DIR / subdir
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)
    return TraceStore(path)


def show_trace(store: TraceStore) -> None:
    print(store.trace_path.read_text())


def show_rendered(store: TraceStore) -> None:
    """Print the full framed trace block as the renderer would emit it live."""
    task = store.to_task()
    print("\n--- rendered block ---")
    print(render_trace(task))


# ---------------------------------------------------------------------------
# T1 — Ordinary scalar bug-fix
# ---------------------------------------------------------------------------


def t1_scalar_bugfix() -> TraceStore:
    section("T1 — Ordinary scalar bug-fix (L1 diagnostic)")
    store = task_store("t1-scalar-bugfix")
    store.init(
        task_title="checkout test intermittently fails on empty cart",
        loops=["inner"],
        level_chosen="L1",
        dispatch_source="auto",
        signals="explicit-bugfix:-5,layer-crossings:+2",
    )
    store.append_iteration(
        loop="inner", k=0, skill="baseline", action="baseline",
        loss_norm=0.600, raw="3/5", baseline=True,
    )
    store.append_iteration(
        loop="inner", k=1, skill="reproducibility-first",
        action="confirmed reproducible 5/5 on empty cart",
        loss_norm=0.600, raw="3/5",
    )
    store.append_iteration(
        loop="inner", k=2, skill="root-cause-by-layer",
        action="empty list → len check missing → guard added",
        loss_norm=0.000, raw="0/5",
    )
    store.append_close(
        loop="inner", terminal="complete",
        layer="3: input-contract · 5: len-check-before-access",
        docs="synced",
        loss_final=0.0,
    )
    show_trace(store)
    show_rendered(store)
    return store


# ---------------------------------------------------------------------------
# T2 — Pareto multi-objective (vector loss)
# ---------------------------------------------------------------------------


def t2_pareto() -> TraceStore:
    section("T2 — Pareto multi-objective (IoT Byzantine consensus)")
    store = task_store("t2-pareto")
    store.init(
        task_title="Byzantine consensus under 100ms + 1KB RAM",
        loops=["inner"],
        level_chosen="L4",
        dispatch_source="auto",
        creativity="inventive",
        signals="greenfield:+3,components>=3:+2,cross-layer:+2,ambiguous:+2",
    )

    # Baseline — high loss across all three dims
    v0 = VectorLoss(
        dims=("latency", "memory", "correctness"),
        values={"latency": 0.80, "memory": 0.60, "correctness": 0.40},
    )
    store.append_iteration(
        loop="inner", k=0, skill="baseline",
        action="HotStuff baseline — too heavy on RAM, Byzantine marginal",
        loss_norm=round(sum(v0.values.values()) / 3, 3),
        raw="6/10",
        loss_vec=v0.dumps(),
        baseline=True,
    )

    # i1 — dominant improvement (all three dims better)
    v1 = VectorLoss(
        dims=("latency", "memory", "correctness"),
        values={"latency": 0.50, "memory": 0.40, "correctness": 0.20},
    )
    arrow1 = v1.dominance_arrow(v0)
    store.append_iteration(
        loop="inner", k=1, skill="architect-mode",
        action=f"MPO-CRDT with dominance ordering — Pareto {arrow1} vs baseline",
        loss_norm=round(sum(v1.values.values()) / 3, 3),
        raw="4/10",
        loss_vec=v1.dumps(),
    )

    # i2 — trade-off (latency worse, memory better)
    v2 = VectorLoss(
        dims=("latency", "memory", "correctness"),
        values={"latency": 0.65, "memory": 0.25, "correctness": 0.20},
    )
    arrow2 = v2.dominance_arrow(v1)
    store.append_iteration(
        loop="inner", k=2, skill="loss-backprop-lens",
        action=f"compact lattice-merge (RAM↓ / latency↑) — Pareto {arrow2} vs i1",
        loss_norm=round(sum(v2.values.values()) / 3, 3),
        raw="3/10",
        loss_vec=v2.dumps(),
    )

    store.append_close(
        loop="inner", terminal="complete",
        layer="4: protocol-invariant · 5: partial-order",
        docs="synced",
        loss_final=round(sum(v2.values.values()) / 3, 3),
    )
    show_trace(store)
    print(
        f"\n→ Pareto verdicts: i0→i1 {arrow1} (dominant), "
        f"i1→i2 {arrow2} (trade-off — no scalar direction)"
    )
    show_rendered(store)
    return store


# ---------------------------------------------------------------------------
# T3 — Moving-target mid-task (epoch boundary)
# ---------------------------------------------------------------------------


def t3_moving_target() -> TraceStore:
    section("T3 — Moving-target mid-task (requirements shift)")
    store = task_store("t3-moving-target")
    store.init(
        task_title="billing refund flow — requirements shift mid-task",
        loops=["inner"],
        level_chosen="L3",
        dispatch_source="auto",
        creativity="standard",
        signals="cross-layer:+2,components>=3:+2,ambiguous:+2",
    )

    # Epoch 0 — original scope
    store.append_iteration(
        loop="inner", k=0, skill="baseline", action="baseline under original scope",
        loss_norm=0.500, raw="4/8", baseline=True,
    )
    store.append_iteration(
        loop="inner", k=1, skill="architect-mode",
        action="initial refund protocol passes 4/8 tests",
        loss_norm=0.500, raw="4/8",
    )
    store.append_iteration(
        loop="inner", k=2, skill="e2e-driven-iteration",
        action="guarded partial refunds, down to 2/8",
        loss_norm=0.250, raw="2/8",
    )

    # ---- Mid-task shift: rubric changes (SCA compliance added)
    store.append_epoch_bump(
        new_epoch=1,
        reason="PSD2 SCA compliance requirement added to rubric mid-task — 2 new rubric items",
    )

    # Epoch 1 — new rubric (10 items now, prior 2/8 translates to 4/10 in the
    # new frame). Δloss vs. the pre-epoch iteration would be meaningless; the
    # agent must judge progress *within* epoch 1 only.
    store.append_iteration(
        loop="inner", k=3, skill="root-cause-by-layer",
        action="baseline under new SCA rubric — 4/10 failing",
        loss_norm=0.400, raw="4/10", baseline=True, epoch=1,
    )
    store.append_iteration(
        loop="inner", k=4, skill="e2e-driven-iteration",
        action="SCA challenge flow wired — down to 1/10",
        loss_norm=0.100, raw="1/10", epoch=1,
    )
    store.append_iteration(
        loop="inner", k=5, skill="docs-as-definition-of-done",
        action="protocol doc + rubric documented — 0/10",
        loss_norm=0.000, raw="0/10", epoch=1,
    )
    store.append_close(
        loop="inner", terminal="complete",
        layer="3: PSD2-SCA-contract · 5: no-silent-fallback",
        docs="synced",
        loss_final=0.0,
    )
    show_trace(store)
    print(
        "\n→ Two distinct Δloss regimes: epoch 0 (i1..i2 vs the 8-item rubric) "
        "and epoch 1 (i4..i5 vs the 10-item rubric). "
        "Cross-epoch Δ is semantically nonsense and rightly NOT rendered."
    )
    show_rendered(store)
    return store


# ---------------------------------------------------------------------------
# T4 — Autonomous inventive (ack-cache)
# ---------------------------------------------------------------------------


def t4_autonomous_inventive() -> None:
    section("T4 — Autonomous inventive run (ack-cache)")
    os.environ["LDD_ACK_ROOT"] = str(ACK_ROOT)
    cache = AckCache()
    # Clean slate
    if ACK_ROOT.exists():
        shutil.rmtree(ACK_ROOT)

    # Agent starts task — no human present. First probe finds no grant.
    print("1. Autonomous agent probes cache before a grant exists:")
    probe1 = cache.check("consensus-research")
    print(f"   cache.check('consensus-research') = {probe1}")
    print("   → agent falls back to creativity=standard (safe)")

    # User runs /ldd-autonomy-ack grant from a prior interactive session.
    print("\n2. User pre-grants the family via /ldd-autonomy-ack grant:")
    grant = cache.grant("consensus-research", ttl_days=14)
    print(
        f"   granted family='{grant.family}' scope={grant.scope} "
        f"ttl={grant.ttl_days}d granted_at={grant.granted_at}"
    )

    # Next autonomous run — cache hit, inventive activates.
    print("\n3. Next autonomous run probes the cache and finds the grant:")
    probe2 = cache.check("consensus-research")
    print(f"   cache.check('consensus-research') = {probe2}")
    print("   → agent activates creativity=inventive (cached ack path)")

    # Tamper path — show that on-disk mutation fails the check.
    print("\n4. Tamper-detection — on-disk TTL mutation invalidates the grant:")
    path = ACK_ROOT / f"{grant.family_hash}.json"
    body = json.loads(path.read_text())
    body["ttl_days"] = 9999
    path.write_text(json.dumps(body))
    probe3 = cache.check("consensus-research")
    print(f"   cache.check after tampering = {probe3}  (HMAC no longer matches)")
    print("   → agent falls back to standard even though file says 9999d valid")


# ---------------------------------------------------------------------------
# Aggregated telemetry across T1..T3 (T4 does not touch trace.log)
# ---------------------------------------------------------------------------


def show_telemetry(stores: list[TraceStore]) -> None:
    section("Dispatch telemetry — aggregated across T1..T3")
    # Merge all three trace logs into one virtual store so dispatch_accuracy
    # sees the full task set. For the demo we concatenate files into a fresh
    # store; in production `telemetry dispatch --project <root>` already
    # handles a multi-task project.
    merged_root = DEMO_DIR / "merged-view"
    if merged_root.exists():
        shutil.rmtree(merged_root)
    merged_root.mkdir(parents=True)
    merged = TraceStore(merged_root)
    merged.ensure_dir()
    merged.trace_path.write_text(
        "".join(s.trace_path.read_text() for s in stores)
    )
    report = dispatch_accuracy(merged, days=36500)
    print(json.dumps(report, indent=2))


def main() -> int:
    if DEMO_DIR.exists():
        shutil.rmtree(DEMO_DIR)
    DEMO_DIR.mkdir(parents=True)
    s1 = t1_scalar_bugfix()
    s2 = t2_pareto()
    s3 = t3_moving_target()
    show_telemetry([s1, s2, s3])
    t4_autonomous_inventive()
    section("Done — all four fictitious tasks exercised the new pipeline")
    print(f"artefacts in: {DEMO_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
