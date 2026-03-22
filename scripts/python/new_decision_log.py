#!/usr/bin/env python3
from __future__ import annotations

import argparse

from _recovery_doc_scaffold import (
    add_common_recovery_args,
    build_decision_log_markdown,
    ensure_output_path,
    infer_recovery_links,
    repo_root,
    resolve_git_branch,
    resolve_git_head,
    write_markdown,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Create a new decision log markdown scaffold.")
    parser.add_argument("--title", required=True, help="Decision log title.")
    parser.add_argument("--status", default="proposed", choices=["proposed", "accepted", "superseded"], help="Decision log status.")
    parser.add_argument("--why-now", default="TODO: explain why now", help="Why now field content.")
    parser.add_argument("--context", default="TODO: capture context", help="Context field content.")
    parser.add_argument("--decision", default="TODO: record decision", help="Decision field content.")
    parser.add_argument("--consequences", default="TODO: describe consequences", help="Consequences field content.")
    parser.add_argument("--recovery-impact", default="TODO: describe recovery impact", help="Recovery impact field content.")
    parser.add_argument("--validation", default="TODO: describe validation", help="Validation field content.")
    parser.add_argument("--supersedes", default="none", help="Supersedes field content.")
    parser.add_argument("--superseded-by", default="none", help="Superseded by field content.")
    parser.add_argument("--adr", action="append", default=[], help="Related ADR path; repeatable.")
    parser.add_argument("--execution-plan", action="append", default=[], help="Related execution plan path; repeatable.")
    add_common_recovery_args(parser)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    root = repo_root()
    out_path = ensure_output_path(root, args.output, "decision-logs", args.title)
    links = infer_recovery_links(root=root, task_id=args.task_id, run_id=args.run_id, latest_json=args.latest_json)
    content = build_decision_log_markdown(
        root=root,
        title=str(args.title).strip(),
        status=str(args.status).strip(),
        why_now=str(args.why_now).strip(),
        context=str(args.context).strip(),
        decision=str(args.decision).strip(),
        consequences=str(args.consequences).strip(),
        recovery_impact=str(args.recovery_impact).strip(),
        validation=str(args.validation).strip(),
        supersedes=str(args.supersedes).strip(),
        superseded_by=str(args.superseded_by).strip(),
        related_adrs=list(args.adr),
        related_execution_plans=list(args.execution_plan),
        links=links,
        branch=resolve_git_branch(root),
        git_head=resolve_git_head(root),
    )
    write_markdown(out_path, content)
    print(f"CREATED_DECISION_LOG path={out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
