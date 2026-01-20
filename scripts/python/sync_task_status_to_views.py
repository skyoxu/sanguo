#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sync task status from SSoT (tasks.json) into view task files.

SSoT:
  .taskmaster/tasks/tasks.json master.tasks[].status

Views:
  .taskmaster/tasks/tasks_back.json[].status
  .taskmaster/tasks/tasks_gameplay.json[].status

This script only updates the matched taskmaster_id entries and preserves the
rest of the JSON structure.

Writes UTF-8 (no BOM) and CRLF newlines to match repo eol=crlf attributes.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json_crlf(path: Path, obj: Any) -> None:
    text = json.dumps(obj, ensure_ascii=False, indent=2) + "\n"
    path.write_text(text, encoding="utf-8", newline="\r\n")


def _find_master_status(tasks_json: dict[str, Any], task_id: int) -> str:
    tasks = (tasks_json.get("master") or {}).get("tasks") or []
    for t in tasks:
        if isinstance(t, dict) and str(t.get("id")) == str(task_id):
            return str(t.get("status") or "")
    raise ValueError(f"Task id not found in tasks.json: {task_id}")


def _sync_view(view: list[dict[str, Any]], task_id: int, status: str) -> tuple[bool, int]:
    changed = False
    updated = 0
    for t in view:
        if not isinstance(t, dict):
            continue
        if t.get("taskmaster_id") != task_id:
            continue
        if str(t.get("status") or "") != status:
            t["status"] = status
            changed = True
            updated += 1
    return changed, updated


def main() -> int:
    ap = argparse.ArgumentParser(description="Sync a task status from tasks.json into tasks_back/tasks_gameplay views.")
    ap.add_argument("--task-id", required=True, help="Taskmaster id (e.g. 50).")
    ap.add_argument("--write", action="store_true", help="Write changes to disk.")
    args = ap.parse_args()

    try:
        task_id = int(str(args.task_id).split(".", 1)[0])
    except ValueError as exc:
        raise SystemExit(f"Invalid --task-id: {args.task_id}") from exc

    root = _repo_root()
    tasks_json_path = root / ".taskmaster" / "tasks" / "tasks.json"
    back_path = root / ".taskmaster" / "tasks" / "tasks_back.json"
    gameplay_path = root / ".taskmaster" / "tasks" / "tasks_gameplay.json"

    tasks_json = _load_json(tasks_json_path)
    if not isinstance(tasks_json, dict):
        raise SystemExit("tasks.json must be a JSON object")

    status = _find_master_status(tasks_json, task_id)
    if not status:
        raise SystemExit(f"Empty status for task id={task_id} in tasks.json")

    back = _load_json(back_path)
    gameplay = _load_json(gameplay_path)
    if not isinstance(back, list) or not isinstance(gameplay, list):
        raise SystemExit("tasks_back.json and tasks_gameplay.json must be JSON arrays")

    back_changed, back_updated = _sync_view(back, task_id, status)
    game_changed, game_updated = _sync_view(gameplay, task_id, status)

    payload = {
        "task_id": task_id,
        "status": status,
        "back": {"changed": back_changed, "updated": back_updated},
        "gameplay": {"changed": game_changed, "updated": game_updated},
        "write": bool(args.write),
    }
    print(json.dumps(payload, ensure_ascii=True))

    if args.write:
        if back_changed:
            _write_json_crlf(back_path, back)
        if game_changed:
            _write_json_crlf(gameplay_path, gameplay)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

