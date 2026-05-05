from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
SC_DIR = REPO_ROOT / "scripts" / "sc"
if str(SC_DIR) not in sys.path:
    sys.path.insert(0, str(SC_DIR))

from _taskmaster import TaskmasterTriplet


ALLOWED_TIERS = {"auto", "minimal", "targeted", "full"}
ALLOWED_MODES = {"conservative", "materialize"}


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json_file(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")


def parse_task_ids(raw: str) -> set[int]:
    values: set[int] = set()
    for item in str(raw or "").split(","):
        token = item.strip()
        if not token:
            continue
        values.add(int(token))
    return values


def normalize_existing_tier(entry: dict[str, Any]) -> str | None:
    for key in ("semantic_review_tier", "semanticReviewTier"):
        value = str(entry.get(key) or "").strip().lower()
        if value in ALLOWED_TIERS:
            return value
    return None


def load_triplet_payloads(
    *,
    tasks_json_path: Path,
    tasks_back_path: Path,
    tasks_gameplay_path: Path,
) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]], dict[int, dict[str, Any]], dict[int, dict[str, Any]], dict[int, dict[str, Any]], list[int]]:
    tasks_json = load_json(tasks_json_path)
    tasks_back = load_json(tasks_back_path)
    tasks_gameplay = load_json(tasks_gameplay_path)

    if not isinstance(tasks_back, list) or not isinstance(tasks_gameplay, list):
        raise ValueError("tasks_back.json and tasks_gameplay.json must be JSON arrays.")

    master_tasks = []
    if isinstance(tasks_json, dict):
        master = tasks_json.get("master") or {}
        master_tasks = master.get("tasks") or []
    if not isinstance(master_tasks, list):
        raise ValueError("tasks.json master.tasks must be a JSON array.")

    master_by_id = {
        int(str(task.get("id"))): task
        for task in master_tasks
        if isinstance(task, dict) and str(task.get("id") or "").strip().isdigit()
    }
    back_by_id = {
        int(task.get("taskmaster_id")): task
        for task in tasks_back
        if isinstance(task, dict) and isinstance(task.get("taskmaster_id"), int)
    }
    gameplay_by_id = {
        int(task.get("taskmaster_id")): task
        for task in tasks_gameplay
        if isinstance(task, dict) and isinstance(task.get("taskmaster_id"), int)
    }
    candidate_ids = sorted(set(master_by_id) | set(back_by_id) | set(gameplay_by_id))
    return tasks_json, tasks_back, tasks_gameplay, master_by_id, back_by_id, gameplay_by_id, candidate_ids


def build_triplet(
    *,
    task_id: int,
    master_by_id: dict[int, dict[str, Any]],
    back_by_id: dict[int, dict[str, Any]],
    gameplay_by_id: dict[int, dict[str, Any]],
    tasks_json_path: Path,
    tasks_back_path: Path,
    tasks_gameplay_path: Path,
) -> TaskmasterTriplet:
    return TaskmasterTriplet(
        task_id=str(task_id),
        master=dict(master_by_id.get(task_id) or {"id": task_id, "title": "", "details": ""}),
        back=dict(back_by_id.get(task_id) or {}) or None,
        gameplay=dict(gameplay_by_id.get(task_id) or {}) or None,
        tasks_json_path=str(tasks_json_path),
        tasks_back_path=str(tasks_back_path),
        tasks_gameplay_path=str(tasks_gameplay_path),
        taskdoc_path=None,
    )


def title_for_task(task_id: int, master: dict[str, Any] | None, back: dict[str, Any] | None, gameplay: dict[str, Any] | None) -> str:
    for entry in (master or {}, back or {}, gameplay or {}):
        title = str(entry.get("title") or "").strip()
        if title:
            return title
    return f"Task {task_id}"
