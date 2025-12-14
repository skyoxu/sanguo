#!/usr/bin/env python3
from pathlib import Path

import check_tasks_all_refs
import check_tasks_back_references


def main() -> None:
    root = Path(__file__).resolve().parents[2]

    # 1) Backlog-only check for tasks_back.json (taskmaster_exported != true).
    ok_backlog = check_tasks_back_references.run_check(root)

    # 2) Full check for tasks_back.json + tasks_gameplay.json.
    ok_all = check_tasks_all_refs.run_check_all(root)

    if not (ok_backlog and ok_all):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
