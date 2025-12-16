#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Ensure PRD-SANGUO-T2 acceptance checklist is referenced from task view files.

Updates:
  - .taskmaster/tasks/tasks_back.json
  - .taskmaster/tasks/tasks_gameplay.json

Rule:
  For every task entry, ensure `overlay_refs` contains:
    docs/architecture/overlays/PRD-SANGUO-T2/08/ACCEPTANCE_CHECKLIST.md

This is a guardrail so `validate_task_overlays.py` can validate the checklist schema
without requiring tasks.json schema changes.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
ACCEPTANCE_PATH = "docs/architecture/overlays/PRD-SANGUO-T2/08/ACCEPTANCE_CHECKLIST.md"


@dataclass
class UpdateResult:
    path: Path
    tasks_total: int
    tasks_changed: int


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def ensure_refs(task: dict) -> bool:
    changed = False
    refs = task.get("overlay_refs")
    if not isinstance(refs, list):
        overlay = task.get("overlay")
        refs = [overlay] if isinstance(overlay, str) and overlay else []
        task["overlay_refs"] = refs
        changed = True

    if ACCEPTANCE_PATH not in refs:
        refs.append(ACCEPTANCE_PATH)
        changed = True
    return changed


def update_file(path: Path) -> UpdateResult:
    tasks = load_json(path)
    if not isinstance(tasks, list):
        raise ValueError(f"Expected a JSON list in {path}")

    changed = 0
    for t in tasks:
        if not isinstance(t, dict):
            continue
        if ensure_refs(t):
            changed += 1

    write_json(path, tasks)
    return UpdateResult(path=path, tasks_total=len(tasks), tasks_changed=changed)


def write_log(results: list[UpdateResult]) -> Path:
    date_str = datetime.now().strftime("%Y-%m-%d")
    out_dir = ROOT / "logs" / "ci" / date_str / "tasks-acceptance-overlay"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "summary.json"

    payload = {
        "ts": datetime.now().astimezone().isoformat(timespec="seconds"),
        "action": "add_t2_acceptance_checklist_overlay_refs",
        "acceptance_path": ACCEPTANCE_PATH,
        "results": [
            {
                "file": r.path.as_posix(),
                "tasks_total": r.tasks_total,
                "tasks_changed": r.tasks_changed,
            }
            for r in results
        ],
    }
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return out_path


def main() -> int:
    back = ROOT / ".taskmaster" / "tasks" / "tasks_back.json"
    gameplay = ROOT / ".taskmaster" / "tasks" / "tasks_gameplay.json"

    results: list[UpdateResult] = []
    for p in (back, gameplay):
        if not p.exists():
            continue
        results.append(update_file(p))

    out = write_log(results)
    for r in results:
        print(f"UPDATED {r.path} changed={r.tasks_changed}/{r.tasks_total}")
    print(f"Wrote log: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

