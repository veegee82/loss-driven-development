"""CLI entry point: `python -m ldd_trace <command> ...`

Subcommands:
    init     Create .ldd/trace.log with a meta header for a task.
    append   Record one iteration close and print the full trace block.
    close    Record a loop-close event and print the final trace block.
    render   Read .ldd/trace.log and print the trace block.
    status   Machine-readable status (next-k per loop, iteration counts).
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from ldd_trace.aggregator import aggregate_and_write, read_memory
from ldd_trace.cot_memory import (
    format_cot_health,
    read_cot_memory,
    update_cot_memory,
)
from ldd_trace.dialectical_prime import (
    format_antithesis_material,
    prime_antithesis,
)
from ldd_trace.renderer import render_trace
from ldd_trace.retrieval import (
    check_in_flight,
    format_health,
    similar_tasks,
    suggest_skills,
)
from ldd_trace.store import TraceStore


def _add_common_args(p: argparse.ArgumentParser) -> None:
    p.add_argument(
        "--project",
        default=".",
        help="Project root (contains or will contain .ldd/trace.log). Default: cwd.",
    )


def _cmd_init(args: argparse.Namespace) -> int:
    store = TraceStore(Path(args.project))
    loops = [l.strip() for l in args.loops.split(",") if l.strip()]
    store.init(task_title=args.task, loops=loops)
    print(f"trace.log initialized at {store.trace_path}")
    return 0


def _cmd_append(args: argparse.Namespace) -> int:
    store = TraceStore(Path(args.project))
    if args.auto_k:
        k = store.next_k(args.loop)
    else:
        if args.k is None:
            print("error: --k or --auto-k required", file=sys.stderr)
            return 2
        k = args.k
    store.append_iteration(
        loop=args.loop,
        k=k,
        skill=args.skill,
        action=args.action,
        loss_norm=args.loss_norm,
        raw=args.raw,
        loss_type=args.loss_type,
        mode=args.mode,
        creativity=args.creativity,
        baseline=args.baseline,
        predicted_delta=args.predicted_delta,
    )
    print(render_trace(store.to_task()))
    return 0


def _cmd_close(args: argparse.Namespace) -> int:
    store = TraceStore(Path(args.project))
    store.append_close(
        loop=args.loop,
        terminal=args.terminal,
        layer=args.layer,
        docs=args.docs,
    )
    # Auto-aggregate on close (v0.5.2) — keeps project_memory.json fresh.
    # Cheap (<50ms for hundreds of entries) and prevents stale-read on next task.
    try:
        memory_path = aggregate_and_write(store)
        print(render_trace(store.to_task()))
        print(f"\n[memory auto-refreshed → {memory_path}]")
    except Exception as exc:
        # Aggregation should never block the close event itself.
        print(render_trace(store.to_task()))
        print(f"\n[warning: memory aggregation failed: {exc}]", file=sys.stderr)
    return 0


def _cmd_aggregate(args: argparse.Namespace) -> int:
    store = TraceStore(Path(args.project))
    if not store.exists():
        print(f"no trace.log at {store.trace_path}", file=sys.stderr)
        return 1
    out = aggregate_and_write(store)
    print(f"project_memory.json written to {out}")
    if args.print:
        import json
        with out.open("r") as f:
            print(json.dumps(json.load(f), indent=2))
    return 0


def _cmd_suggest(args: argparse.Namespace) -> int:
    store = TraceStore(Path(args.project))
    memory = read_memory(store)
    if memory is None:
        print(
            f"no project_memory.json at {store.trace_dir}; "
            "run `ldd_trace aggregate` first",
            file=sys.stderr,
        )
        return 1
    suggestions = suggest_skills(memory, top_n=args.top_n)
    if not suggestions:
        print("no skill data available yet (empty project_memory.json)")
        return 0
    print(f"Top skill suggestions from project memory (window: lifetime):\n")
    print(f"  {'skill':<32}  {'rank':>6}  {'rel_Δ':>8}  {'reg':>5}  {'pla':>5}  {'n':>4}")
    print(f"  {'-'*32}  {'-'*6}  {'-'*8}  {'-'*5}  {'-'*5}  {'-'*4}")
    for s in suggestions:
        if s.n_invocations < 3:
            print(f"  {s.skill:<32}  {'n/a':>6}  {s.reason}")
        else:
            print(
                f"  {s.skill:<32}  "
                f"{s.rank_score:>6.3f}  "
                f"{s.delta_mean_relative:>+8.3f}  "
                f"{s.regression_rate:>5.0%}  "
                f"{s.plateau_rate:>5.0%}  "
                f"{s.n_invocations:>4d}"
            )
    return 0


def _cmd_check(args: argparse.Namespace) -> int:
    store = TraceStore(Path(args.project))
    memory = read_memory(store)
    if memory is None:
        print(
            f"no project_memory.json at {store.trace_dir}; "
            "run `ldd_trace aggregate` first (need ≥ 1 closed task)",
            file=sys.stderr,
        )
        return 1
    current = store.current_task()
    warnings = check_in_flight(memory, current, next_planned_skill=args.next_skill)
    if not warnings:
        print("[ok] no warnings — current task aligns with project memory")
        return 0
    print(f"[{len(warnings)} warning(s) from project memory]\n")
    for w in warnings:
        severity_marker = {"info": "ℹ", "warn": "⚠", "high": "⚠⚠"}.get(w.severity, "?")
        print(f"  {severity_marker} [{w.kind:<14} · {w.severity:<4}] {w.message}")
    return 0


def _cmd_similar(args: argparse.Namespace) -> int:
    store = TraceStore(Path(args.project))
    if not store.exists():
        print(f"no trace.log at {store.trace_path}", file=sys.stderr)
        return 1
    files = [f.strip() for f in args.files.split(",") if f.strip()]
    ranked = similar_tasks(store, files, top_n=args.top_n)
    if not ranked:
        print("no similar past tasks (no `files=` metadata in prior entries, "
              "or no overlap)")
        return 0
    print(f"similar past tasks (by file-overlap with {files}):\n")
    for task, jaccard in ranked:
        title = task.meta.fields.get("task", "(no title)") if task.meta else "(no meta)"
        terminal = task.terminal or "(in-flight)"
        print(f"  {jaccard:.2f}  k={task.k_count}  [{terminal}]  {title}")
    return 0


def _cmd_health(args: argparse.Namespace) -> int:
    store = TraceStore(Path(args.project))
    memory = read_memory(store)
    if memory is None:
        print(
            f"no project_memory.json at {store.trace_dir}; "
            "run `ldd_trace aggregate` first",
            file=sys.stderr,
        )
        return 1
    print(format_health(memory))
    return 0


def _cmd_cot_run(args: argparse.Namespace) -> int:
    from ldd_trace.cot import CoTRunner
    from ldd_trace.cot_llm import OpenRouterCotLLMClient

    store = TraceStore(Path(args.project))
    try:
        llm = OpenRouterCotLLMClient(model=args.model) if args.model else OpenRouterCotLLMClient()
    except RuntimeError as exc:
        print(f"error: {exc}", file=sys.stderr)
        print(
            "\nEither set OPENROUTER_API_KEY env var, or use the Python API with "
            "a custom CotLLMClient for offline / non-OpenRouter LLMs.",
            file=sys.stderr,
        )
        return 1

    runner = CoTRunner(llm=llm, store=store)
    chain = runner.run(
        task=args.task,
        task_type=args.task_type,
        ground_truth=args.ground_truth,
        max_steps=args.max_steps,
    )

    # Print a compact summary
    print(f"\n═══ CoT run summary ═══")
    print(f"Task           : {chain.task}")
    print(f"Task type      : {chain.task_type}")
    print(f"Terminal       : {chain.terminal}")
    print(f"Steps          : {len(chain.steps)}")
    print(f"Backtracks     : {chain.backtrack_count}")
    print(f"Total tokens   : {chain.total_tokens}")
    if chain.predicted_chain_correct is not None:
        print(f"Predicted corr.: {chain.predicted_chain_correct:.3f}")
    print(f"Actual correct : {chain.actual_correct}")
    print(f"Final answer   : {chain.final_answer}")
    print(f"\nChain logged to: {store.trace_dir}/cot_traces.jsonl")
    print(f"Memory updated : {store.trace_dir}/cot_memory.json")
    return 0


def _cmd_cot_aggregate(args: argparse.Namespace) -> int:
    store = TraceStore(Path(args.project))
    out = update_cot_memory(store)
    print(f"cot_memory.json written to {out}")
    return 0


def _cmd_cot_health(args: argparse.Namespace) -> int:
    store = TraceStore(Path(args.project))
    memory = read_cot_memory(store)
    if memory is None:
        print(
            f"no cot_memory.json at {store.trace_dir}; "
            "run `ldd_trace cot run ...` (at least one chain)",
            file=sys.stderr,
        )
        return 1
    print(format_cot_health(memory))
    return 0


def _cmd_prime_antithesis(args: argparse.Namespace) -> int:
    store = TraceStore(Path(args.project))
    memory = read_memory(store)
    if memory is None:
        print(
            f"no project_memory.json at {store.trace_dir}; "
            "run `ldd_trace aggregate` first (need ≥ 1 closed task)",
            file=sys.stderr,
        )
        return 1
    current = store.current_task()
    files_list = None
    if args.files:
        files_list = [f.strip() for f in args.files.split(",") if f.strip()]
    material = prime_antithesis(
        memory=memory,
        thesis=args.thesis,
        current=current,
        files=files_list,
        store=store,
    )
    print(format_antithesis_material(material))
    return 0 if material.has_signal else 0  # non-zero exit would be misleading


def _cmd_render(args: argparse.Namespace) -> int:
    store = TraceStore(Path(args.project))
    if not store.exists():
        print(f"no trace.log at {store.trace_path}", file=sys.stderr)
        return 1
    print(render_trace(store.to_task()))
    return 0


def _cmd_status(args: argparse.Namespace) -> int:
    store = TraceStore(Path(args.project))
    if not store.exists():
        print(f"no trace.log at {store.trace_path}", file=sys.stderr)
        return 1
    iters = store.iterations()
    print(f"trace_path: {store.trace_path}")
    print(f"iterations: {len(iters)}")
    for loop in ("architect", "inner", "refine", "outer"):
        n = sum(1 for e in iters if e.loop == loop)
        next_k = store.next_k(loop)
        if n > 0:
            last = [e for e in iters if e.loop == loop][-1]
            print(f"  {loop}: n={n} next_k={next_k} last_loss={last.get_float('loss_norm'):.3f}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="ldd_trace",
        description="LDD per-iteration trace emission + persistence (v0.5.1)",
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    p_init = sub.add_parser("init", help="Create .ldd/trace.log meta header")
    _add_common_args(p_init)
    p_init.add_argument("--task", required=True, help="One-line task title")
    p_init.add_argument(
        "--loops",
        default="inner",
        help="Comma-separated loops expected (inner,refine,outer)",
    )
    p_init.set_defaults(func=_cmd_init)

    p_app = sub.add_parser(
        "append",
        help="Record one iteration and print the full trace block",
    )
    _add_common_args(p_app)
    p_app.add_argument("--loop", required=True, choices=["inner", "refine", "outer", "architect"])
    p_app.add_argument("--k", type=int, default=None, help="Iteration index")
    p_app.add_argument("--auto-k", action="store_true", help="Derive k from trace.log")
    p_app.add_argument("--skill", required=True, help="Skill name that fired this iteration")
    p_app.add_argument("--action", required=True, help="One-line description of concrete change")
    p_app.add_argument("--loss-norm", type=float, required=True, help="Loss normalized to [0,1]")
    p_app.add_argument("--raw", required=True, help="Raw loss count, format 'N/max'")
    p_app.add_argument(
        "--loss-type",
        default="normalized-rubric",
        choices=["normalized-rubric", "rate", "absolute"],
    )
    p_app.add_argument("--mode", default=None, help="For architect: 'architect'")
    p_app.add_argument(
        "--creativity",
        default=None,
        choices=["standard", "conservative", "inventive"],
    )
    p_app.add_argument(
        "--baseline",
        action="store_true",
        help="Mark this as pre-iteration baseline (k=0), no Δloss computed",
    )
    p_app.add_argument(
        "--predicted-delta",
        type=float,
        default=None,
        help="v0.7.0 — predicted Δloss from the quantitative dialectic protocol. "
        "When provided, the aggregator computes prediction_error and mean |error| "
        "as a calibration metric.",
    )
    p_app.set_defaults(func=_cmd_append)

    p_close = sub.add_parser("close", help="Record loop close and print final block")
    _add_common_args(p_close)
    p_close.add_argument("--loop", required=True, choices=["inner", "refine", "outer", "architect"])
    p_close.add_argument(
        "--terminal",
        required=True,
        choices=["complete", "partial", "failed", "aborted", "handoff"],
    )
    p_close.add_argument("--layer", default="", help="Fix description (layers 4 · 5)")
    p_close.add_argument("--docs", default="", help="Docs-sync verdict")
    p_close.set_defaults(func=_cmd_close)

    p_r = sub.add_parser("render", help="Render current trace.log to stdout")
    _add_common_args(p_r)
    p_r.set_defaults(func=_cmd_render)

    p_s = sub.add_parser("status", help="Machine-readable status")
    _add_common_args(p_s)
    p_s.set_defaults(func=_cmd_status)

    # --- v0.5.2 memory commands -----------------------------------------
    p_ag = sub.add_parser(
        "aggregate",
        help="Compute .ldd/project_memory.json from trace.log",
    )
    _add_common_args(p_ag)
    p_ag.add_argument(
        "--print",
        action="store_true",
        help="Print the full memory JSON to stdout after write",
    )
    p_ag.set_defaults(func=_cmd_aggregate)

    p_sug = sub.add_parser(
        "suggest",
        help="Rank skills by empirical effectiveness from project memory",
    )
    _add_common_args(p_sug)
    p_sug.add_argument("--top-n", type=int, default=5)
    p_sug.set_defaults(func=_cmd_suggest)

    p_ck = sub.add_parser(
        "check",
        help="Warn if current in-flight task diverges from project patterns "
        "(plateau, over-budget, regressive next-skill)",
    )
    _add_common_args(p_ck)
    p_ck.add_argument(
        "--next-skill",
        default=None,
        help="Skill you're about to invoke — checked against historical regression rate",
    )
    p_ck.set_defaults(func=_cmd_check)

    p_sim = sub.add_parser(
        "similar",
        help="Rank past tasks by file-overlap (no embeddings; deterministic)",
    )
    _add_common_args(p_sim)
    p_sim.add_argument(
        "--files",
        required=True,
        help="Comma-separated list of files touched by the current task",
    )
    p_sim.add_argument("--top-n", type=int, default=5)
    p_sim.set_defaults(func=_cmd_similar)

    p_hl = sub.add_parser("health", help="Human-readable project-memory summary")
    _add_common_args(p_hl)
    p_hl.set_defaults(func=_cmd_health)

    # --- v0.8.0 dialectical chain-of-thought ----------------------------
    p_cot = sub.add_parser(
        "cot",
        help="Dialectical chain-of-thought subcommands (v0.8.0)",
    )
    cot_sub = p_cot.add_subparsers(dest="cot_cmd", required=True)

    p_cot_run = cot_sub.add_parser(
        "run",
        help="Run a dialectical-CoT chain on a task (requires OPENROUTER_API_KEY)",
    )
    _add_common_args(p_cot_run)
    p_cot_run.add_argument("--task", required=True, help="The task prompt / question")
    p_cot_run.add_argument(
        "--task-type",
        default="general",
        help="Task type (e.g. math, code, logic) — used for memory partitioning",
    )
    p_cot_run.add_argument(
        "--ground-truth",
        default=None,
        help="Expected answer (string) for verification; enables calibration logging",
    )
    p_cot_run.add_argument(
        "--max-steps", type=int, default=10, help="Maximum chain length",
    )
    p_cot_run.add_argument(
        "--model",
        default=None,
        help="Override LLM model (default: openai/gpt-4o-mini via OpenRouter)",
    )
    p_cot_run.set_defaults(func=_cmd_cot_run)

    p_cot_agg = cot_sub.add_parser(
        "aggregate",
        help="Re-aggregate .ldd/cot_traces.jsonl into .ldd/cot_memory.json",
    )
    _add_common_args(p_cot_agg)
    p_cot_agg.set_defaults(func=_cmd_cot_aggregate)

    p_cot_hl = cot_sub.add_parser(
        "health", help="Human-readable CoT health report",
    )
    _add_common_args(p_cot_hl)
    p_cot_hl.set_defaults(func=_cmd_cot_health)

    # --- v0.6.0 memory × dialectical coupling ---------------------------
    p_pa = sub.add_parser(
        "prime-antithesis",
        help="Generate memory-informed antithesis material for the "
        "dialectical-reasoning skill (v0.6.0)",
    )
    _add_common_args(p_pa)
    p_pa.add_argument(
        "--thesis",
        required=True,
        help="One-line description of the planned action / decision to challenge",
    )
    p_pa.add_argument(
        "--files",
        default=None,
        help="Comma-separated files the current task touches (for similar-task retrieval)",
    )
    p_pa.set_defaults(func=_cmd_prime_antithesis)

    return p


def main(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
