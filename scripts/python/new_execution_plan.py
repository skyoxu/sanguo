#!/usr/bin/env python3
from __future__ import annotations

import argparse

from _recovery_doc_scaffold import (
    add_common_recovery_args,
    build_execution_plan_markdown,
    ensure_output_path,
    infer_recovery_links,
    repo_root,
    resolve_git_branch,
    resolve_git_head,
    write_markdown,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Create a new execution plan markdown scaffold.")
    parser.add_argument("--title", required=True, help="Execution plan title.")
    parser.add_argument("--status", default="active", choices=["active", "paused", "done", "blocked"], help="Execution plan status.")
    parser.add_argument("--goal", default="TODO: describe goal", help="Goal field content.")
    parser.add_argument("--scope", default="TODO: define scope", help="Scope field content.")
    parser.add_argument("--current-step", default="TODO: define current step", help="Current step field content.")
    parser.add_argument("--stop-loss", default="TODO: define stop-loss boundary", help="Stop-loss field content.")
    parser.add_argument("--next-action", default="TODO: define next action", help="Next action field content.")
    parser.add_argument("--exit-criteria", default="TODO: define exit criteria", help="Exit criteria field content.")
    parser.add_argument("--adr", action="append", default=[], help="Related ADR path; repeatable.")
    parser.add_argument("--decision-log", action="append", default=[], help="Related decision log path; repeatable.")
    add_common_recovery_args(parser)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    root = repo_root()
    out_path = ensure_output_path(root, args.output, "execution-plans", args.title)
    links = infer_recovery_links(root=root, task_id=args.task_id, run_id=args.run_id, latest_json=args.latest_json)
    content = build_execution_plan_markdown(
        root=root,
        title=str(args.title).strip(),
        status=str(args.status).strip(),
        goal=str(args.goal).strip(),
        scope=str(args.scope).strip(),
        current_step=str(args.current_step).strip(),
        stop_loss=str(args.stop_loss).strip(),
        next_action=str(args.next_action).strip(),
        exit_criteria=str(args.exit_criteria).strip(),
        related_adrs=list(args.adr),
        related_decision_logs=list(args.decision_log),
        links=links,
        branch=resolve_git_branch(root),
        git_head=resolve_git_head(root),
    )
    write_markdown(out_path, content)
    print(f"CREATED_EXECUTION_PLAN path={out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
