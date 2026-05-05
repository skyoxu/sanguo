#!/usr/bin/env python3
"""
Patch .taskmaster/tasks/tasks_back.json overlay_refs to include required anchors:
  - docs/architecture/overlays/<PRD-ID>/08/_index.md
  - docs/architecture/overlays/<PRD-ID>/08/ACCEPTANCE_CHECKLIST.md

This script is intentionally deterministic and logs changes under:
  logs/ci/<YYYY-MM-DD>/task-overlays/
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
from dataclasses import dataclass
from pathlib import Path


OVERLAY_DIR_RE = re.compile(r"^(docs/architecture/overlays/[^/]+/08)(?:/.*)?$")


@dataclass(frozen=True)
class PatchResult:
    changed_tasks: list[str]
    total_tasks: int
    total_changed: int
    overlay_dir: str | None


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _today() -> str:
    return dt.date.today().isoformat()


def _ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def _load_tasks(task_file: Path) -> list[dict]:
    data = json.loads(task_file.read_text(encoding="utf-8"))
    if isinstance(data, list):
        return data
    if isinstance(data, dict) and isinstance(data.get("tasks"), list):
        return data["tasks"]
    raise ValueError(f"Unsupported task file schema: {task_file}")


def _infer_overlay_dir(task: dict) -> str | None:
    refs = task.get("overlay_refs") or []
    if isinstance(refs, str):
        refs = [refs]
    if not isinstance(refs, list):
        return None
    for r in refs:
        m = OVERLAY_DIR_RE.match(str(r))
        if m:
            return m.group(1)
    overlay = str(task.get("overlay") or "").strip()
    if overlay:
        m = OVERLAY_DIR_RE.match(overlay)
        if m:
            return m.group(1)
    return None


def _normalize_refs(refs: object) -> list[str]:
    if refs is None:
        return []
    if isinstance(refs, str):
        refs = [refs]
    if not isinstance(refs, list):
        return []
    return [str(x) for x in refs if str(x).strip()]


def _validate_overlay_files_exist(root: Path, overlay_dir: str) -> list[str]:
    missing: list[str] = []
    for rel in [f"{overlay_dir}/_index.md", f"{overlay_dir}/ACCEPTANCE_CHECKLIST.md"]:
        if not (root / rel).exists():
            missing.append(rel)
    return missing


def _write_logs(log_dir: Path, result: PatchResult) -> None:
    _ensure_dir(log_dir)
    summary = {
        "total_tasks": result.total_tasks,
        "total_changed": result.total_changed,
        "overlay_dir": result.overlay_dir,
        "changed_tasks": result.changed_tasks,
    }
    (log_dir / "patch-summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Patch tasks_back.json overlay_refs anchors.")
    parser.add_argument(
        "--task-file",
        type=str,
        default=str(Path(".taskmaster") / "tasks" / "tasks_back.json"),
        help="Path to tasks_back.json (default: .taskmaster/tasks/tasks_back.json)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Compute changes and write logs, but do not modify the task file.",
    )
    args = parser.parse_args()

    root = _repo_root()
    task_file = (root / args.task_file).resolve()

    if task_file.name != "tasks_back.json":
        raise ValueError("This patcher is intended for tasks_back.json only.")

    tasks = _load_tasks(task_file)
    # Patch in-memory, then write once.
    # (We call the patcher logic by temporarily writing to task dicts.)
    # Note: task dicts preserve insertion order from JSON, so a json dump keeps key order stable.
    _ = tasks  # explicit: mutable list of dicts
    # Reuse patch logic by operating on a temporary file path is overkill; patch inline:
    changed: list[str] = []
    inferred_dirs: set[str] = set()
    for task in tasks:
        task_id = str(task.get("id", "")).strip() or str(task.get("taskmaster_id", "")).strip()
        overlay_dir = _infer_overlay_dir(task)
        if overlay_dir:
            inferred_dirs.add(overlay_dir)
        overlay_refs = _normalize_refs(task.get("overlay_refs"))
        if not overlay_dir:
            raise ValueError(
                f"Task {task_id}: cannot infer overlay_dir; set overlay_refs to include "
                "docs/architecture/overlays/<PRD-ID>/08/_index.md and ACCEPTANCE_CHECKLIST.md"
            )
        required = [
            f"{overlay_dir}/_index.md",
            f"{overlay_dir}/ACCEPTANCE_CHECKLIST.md",
        ]
        missing = [x for x in required if x not in overlay_refs]
        if not missing:
            continue
        new_refs: list[str] = []
        if required[0] not in overlay_refs:
            new_refs.append(required[0])
        for r in overlay_refs:
            new_refs.append(r)
        if required[1] not in new_refs:
            new_refs.append(required[1])
        task["overlay_refs"] = new_refs
        changed.append(task_id)

    overlay_dir_value: str | None = None
    if len(inferred_dirs) == 1:
        overlay_dir_value = next(iter(inferred_dirs))

    result = PatchResult(
        changed_tasks=changed,
        total_tasks=len(tasks),
        total_changed=len(changed),
        overlay_dir=overlay_dir_value,
    )

    log_dir = root / "logs" / "ci" / _today() / "task-overlays"
    _write_logs(log_dir, result)

    if result.overlay_dir:
        missing = _validate_overlay_files_exist(root, result.overlay_dir)
        if missing:
            (log_dir / "missing-overlay-files.json").write_text(
                json.dumps({"missing": missing}, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            print(f"ERROR: required overlay anchor files missing: {missing}")
            return 2

    if args.dry_run:
        print(f"DRY RUN: would patch {result.total_changed}/{result.total_tasks} tasks")
        print(f"Logs: {log_dir}")
        return 0

    task_file.write_text(json.dumps(tasks, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"Patched {result.total_changed}/{result.total_tasks} tasks")
    print(f"Logs: {log_dir}")
    return 0


if __name__ == "__main__":
    os.environ.setdefault("PYTHONUTF8", "1")
    raise SystemExit(main())
