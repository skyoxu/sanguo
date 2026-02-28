#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

import check_tasks_all_refs
import check_tasks_back_references


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run task link validation (backlog-only, all, or both).",
    )
    parser.add_argument(
        "--mode",
        choices=["backlog", "all", "both"],
        default="all",
        help="Validation mode. 'all' is recommended for CI; use 'both' when debugging backlog-only drift.",
    )
    parser.add_argument(
        "--max-warnings",
        type=int,
        default=-1,
        help="Fail if total warnings in all-mode exceed this budget; -1 disables budget check.",
    )
    parser.add_argument(
        "--summary-out",
        type=str,
        default="",
        help="Optional summary json output path for all-mode.",
    )
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[2]

    ok_backlog = True
    ok_all = True

    if args.mode in {"backlog", "both"}:
        # Backlog-only check for tasks_back.json (taskmaster_exported != true).
        ok_backlog = check_tasks_back_references.run_check(root)

    if args.mode in {"all", "both"}:
        # Full check for tasks_back.json + tasks_gameplay.json.
        summary_out = Path(args.summary_out) if args.summary_out else None
        ok_all = check_tasks_all_refs.run_check_all(
            root,
            max_warnings=args.max_warnings,
            summary_out=summary_out,
        )

    if not (ok_backlog and ok_all):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
