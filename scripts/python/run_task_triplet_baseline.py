#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _today_local() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def _default_out(root: Path) -> Path:
    return root / "logs" / "ci" / _today_local() / "task-generation" / "summary.json"


def _rel(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def _run_step(
    *,
    name: str,
    command: list[str],
    cwd: Path,
    summary_path: Path | None = None,
) -> dict[str, Any]:
    completed = subprocess.run(
        command,
        cwd=str(cwd),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    payload: dict[str, Any] = {
        "name": name,
        "command": command,
        "returncode": completed.returncode,
        "status": "ok" if completed.returncode == 0 else "fail",
        "stdout": completed.stdout,
        "stderr": completed.stderr,
    }
    if summary_path is not None:
        payload["summary_path"] = summary_path.as_posix()
    return payload


def main() -> int:
    root = _repo_root()
    parser = argparse.ArgumentParser(
        description="Run Chapter 3.8/3.9 task triplet baseline validators and record a unified summary.",
    )
    parser.add_argument(
        "--out",
        default=str(_default_out(root)),
        help="Output summary json path. Default: logs/ci/<date>/task-generation/summary.json",
    )
    args = parser.parse_args()

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    task_links_summary = out_path.parent / "task-links-validate-summary.json"
    task_refs_summary = out_path.parent / "check-tasks-all-refs-summary.json"

    steps = [
        _run_step(
            name="task_links_validate",
            command=[
                "py",
                "-3",
                "scripts/python/task_links_validate.py",
                "--mode",
                "all",
                "--summary-out",
                str(task_links_summary),
            ],
            cwd=root,
            summary_path=task_links_summary,
        ),
        _run_step(
            name="check_tasks_all_refs",
            command=[
                "py",
                "-3",
                "scripts/python/check_tasks_all_refs.py",
                "--summary-out",
                str(task_refs_summary),
            ],
            cwd=root,
            summary_path=task_refs_summary,
        ),
        _run_step(
            name="validate_task_master_triplet",
            command=["py", "-3", "scripts/python/validate_task_master_triplet.py"],
            cwd=root,
        ),
    ]

    ok = all(step["returncode"] == 0 for step in steps)
    summary = {
        "schema": "task-generation.baseline-summary.v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "ok" if ok else "fail",
        "root": _rel(root, root),
        "chapter": "3.8-3.9",
        "steps": steps,
        "artifacts": {
            "task_links_validate": _rel(task_links_summary, root),
            "check_tasks_all_refs": _rel(task_refs_summary, root),
        },
    }
    out_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"TASK_TRIPLET_BASELINE status={summary['status']} out={_rel(out_path, root)}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
