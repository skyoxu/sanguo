#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Validate tasks_back.json / tasks_gameplay.json "test_refs" for a single task.

Why:
  - sc-build/sc-test only validate compilation + tests/coverage.
  - They do not enforce traceability metadata ("test_refs") in task views.
  - This script provides a deterministic check so acceptance_check can gate on it.

Rules (task-scoped, deterministic):
  - Resolve task_id from --task-id, otherwise first status=in-progress in tasks.json.
  - Find the mapped task entries in tasks_back.json and tasks_gameplay.json (by taskmaster_id).
  - test_refs must be a list; each entry must be a repo-relative path (no absolute paths).
  - Each referenced path must exist on disk.
  - When --require-non-empty is set, empty test_refs is an error.

Outputs:
  - Writes JSON report to --out.
  - Prints a short ASCII summary for log capture.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def resolve_current_task_id(tasks_json: dict[str, Any]) -> str:
    tasks = (tasks_json.get("master") or {}).get("tasks") or []
    for t in tasks:
        if not isinstance(t, dict):
            continue
        if str(t.get("status")) == "in-progress":
            return str(t.get("id"))
    raise ValueError("No task with status=in-progress found in tasks.json")


def find_view_task(view: list[dict[str, Any]], task_id: str) -> dict[str, Any] | None:
    try:
        tid_int = int(str(task_id))
    except ValueError:
        return None
    for t in view:
        if not isinstance(t, dict):
            continue
        if t.get("taskmaster_id") == tid_int:
            return t
    return None


def is_abs_path(p: str) -> bool:
    # Avoid platform ambiguity: treat both Windows and POSIX abs paths as forbidden here.
    if not p:
        return False
    if os.path.isabs(p):
        return True
    # Also disallow drive-letter without separator normalization.
    if len(p) >= 2 and p[1] == ":":
        return True
    return False


def validate_test_refs(
    *,
    root: Path,
    label: str,
    entry: dict[str, Any] | None,
    require_non_empty: bool,
) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []

    if entry is None:
        warnings.append(f"{label}: mapped task not found by taskmaster_id (skip)")
        return errors, warnings

    raw = entry.get("test_refs")
    if raw is None:
        errors.append(f"{label}: test_refs field missing")
        return errors, warnings

    if not isinstance(raw, list):
        errors.append(f"{label}: test_refs must be a list")
        return errors, warnings

    refs: list[str] = [str(x).strip() for x in raw if str(x).strip()]
    if require_non_empty and not refs:
        errors.append(f"{label}: test_refs is empty but require_non_empty=true")
        return errors, warnings

    for r in refs:
        rr = r.replace("\\", "/")
        if is_abs_path(rr):
            errors.append(f"{label}: absolute path is not allowed in test_refs: {rr}")
            continue
        # Hard rule: test_refs must point to real test files, not logs/docs.
        if not (rr.endswith(".cs") or rr.endswith(".gd")):
            errors.append(f"{label}: test_refs entry must be a test file (.cs/.gd): {rr}")
            continue
        allowed_prefixes = ("Game.Core.Tests/", "Tests.Godot/tests/", "Tests/")
        if not rr.startswith(allowed_prefixes):
            errors.append(f"{label}: test_refs entry must be under test roots: {rr}")
            continue

        disk = root / rr
        if not disk.exists():
            errors.append(f"{label}: referenced file not found: {rr}")
    return errors, warnings


def main() -> int:
    ap = argparse.ArgumentParser(description="Validate tasks_back/tasks_gameplay test_refs for one task.")
    ap.add_argument("--task-id", default=None, help="Task id (e.g. 11). Default: first status=in-progress in tasks.json.")
    ap.add_argument("--out", required=True, help="Output JSON path (under logs/ci/... recommended).")
    ap.add_argument("--require-non-empty", action="store_true", help="Fail if test_refs is empty.")
    args = ap.parse_args()

    root = repo_root()
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    tasks_json_path = root / ".taskmaster" / "tasks" / "tasks.json"
    back_path = root / ".taskmaster" / "tasks" / "tasks_back.json"
    gameplay_path = root / ".taskmaster" / "tasks" / "tasks_gameplay.json"

    tasks_json = load_json(tasks_json_path)
    task_id = str(args.task_id).strip() if args.task_id else resolve_current_task_id(tasks_json)

    back = load_json(back_path)
    gameplay = load_json(gameplay_path)
    if not isinstance(back, list) or not isinstance(gameplay, list):
        raise ValueError("tasks_back.json and tasks_gameplay.json must be JSON arrays")

    back_task = find_view_task(back, task_id)
    gameplay_task = find_view_task(gameplay, task_id)

    errors: list[str] = []
    warnings: list[str] = []

    e1, w1 = validate_test_refs(root=root, label="tasks_back.json", entry=back_task, require_non_empty=bool(args.require_non_empty))
    e2, w2 = validate_test_refs(
        root=root, label="tasks_gameplay.json", entry=gameplay_task, require_non_empty=bool(args.require_non_empty)
    )
    errors.extend(e1)
    errors.extend(e2)
    warnings.extend(w1)
    warnings.extend(w2)

    if back_task is None and gameplay_task is None:
        errors.append("both tasks_back.json and tasks_gameplay.json mapped tasks are missing; at least one view must exist")

    report = {
        "task_id": task_id,
        "require_non_empty": bool(args.require_non_empty),
        "status": "ok" if not errors else "fail",
        "errors": errors,
        "warnings": warnings,
        "back": {
            "mapped": bool(back_task),
            "test_refs": (back_task or {}).get("test_refs"),
        },
        "gameplay": {
            "mapped": bool(gameplay_task),
            "test_refs": (gameplay_task or {}).get("test_refs"),
        },
    }

    out_path.write_text(json.dumps(report, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")
    print(f"TASK_TEST_REFS status={report['status']} errors={len(errors)} warnings={len(warnings)} task_id={task_id}")
    return 0 if report["status"] == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())

