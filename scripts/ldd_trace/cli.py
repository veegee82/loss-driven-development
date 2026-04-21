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

from ldd_trace.renderer import render_trace
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
    print(render_trace(store.to_task()))
    return 0


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

    return p


def main(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
