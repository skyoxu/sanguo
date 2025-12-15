from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from _util import repo_root


@dataclass(frozen=True)
class TaskmasterTriplet:
    task_id: str
    master: dict[str, Any]
    back: dict[str, Any] | None
    gameplay: dict[str, Any] | None
    tasks_json_path: str
    tasks_back_path: str
    tasks_gameplay_path: str
    taskdoc_path: str | None

    def adr_refs(self) -> list[str]:
        v = self.master.get("adrRefs") or []
        return [str(x) for x in v if str(x).strip()]

    def arch_refs(self) -> list[str]:
        v = self.master.get("archRefs") or []
        return [str(x) for x in v if str(x).strip()]

    def overlay(self) -> str | None:
        v = self.master.get("overlay")
        return str(v) if v else None


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def default_paths() -> tuple[Path, Path, Path]:
    root = repo_root()
    return (
        root / ".taskmaster" / "tasks" / "tasks.json",
        root / ".taskmaster" / "tasks" / "tasks_back.json",
        root / ".taskmaster" / "tasks" / "tasks_gameplay.json",
    )


def iter_master_tasks(tasks_json: dict[str, Any]) -> list[dict[str, Any]]:
    master = tasks_json.get("master") or {}
    tasks = master.get("tasks") or []
    if not isinstance(tasks, list):
        return []
    return [t for t in tasks if isinstance(t, dict)]


def resolve_current_task_id(tasks_json: dict[str, Any]) -> str:
    for t in iter_master_tasks(tasks_json):
        if str(t.get("status")) == "in-progress":
            return str(t.get("id"))
    raise ValueError("No task with status=in-progress found in tasks.json")


def find_master_task(tasks_json: dict[str, Any], task_id: str) -> dict[str, Any]:
    task_id_s = str(task_id)
    for t in iter_master_tasks(tasks_json):
        if str(t.get("id")) == task_id_s:
            return t
    raise KeyError(f"Task id not found in tasks.json: {task_id_s}")


def _find_view_task(view_tasks: list[dict[str, Any]], task_id: str) -> dict[str, Any] | None:
    try:
        tid_int = int(str(task_id))
    except ValueError:
        return None
    for t in view_tasks:
        if not isinstance(t, dict):
            continue
        if t.get("taskmaster_id") == tid_int:
            return t
    return None


def resolve_triplet(
    *,
    task_id: str | None = None,
    tasks_json_path: str | None = None,
    tasks_back_path: str | None = None,
    tasks_gameplay_path: str | None = None,
    taskdoc_dir: str = "taskdoc",
) -> TaskmasterTriplet:
    default_tasks_json, default_back, default_gameplay = default_paths()
    tasks_json_p = Path(tasks_json_path) if tasks_json_path else default_tasks_json
    tasks_back_p = Path(tasks_back_path) if tasks_back_path else default_back
    tasks_gameplay_p = Path(tasks_gameplay_path) if tasks_gameplay_path else default_gameplay

    tasks_json = load_json(tasks_json_p)
    resolved_id = str(task_id) if task_id else resolve_current_task_id(tasks_json)
    master_task = find_master_task(tasks_json, resolved_id)

    back_task = None
    gameplay_task = None
    if tasks_back_p.exists():
        back_obj = load_json(tasks_back_p)
        if isinstance(back_obj, list):
            back_task = _find_view_task(back_obj, resolved_id)
    if tasks_gameplay_p.exists():
        gameplay_obj = load_json(tasks_gameplay_p)
        if isinstance(gameplay_obj, list):
            gameplay_task = _find_view_task(gameplay_obj, resolved_id)

    taskdoc_p = repo_root() / taskdoc_dir / f"{resolved_id}.md"
    taskdoc_path = str(taskdoc_p) if taskdoc_p.exists() else None

    return TaskmasterTriplet(
        task_id=resolved_id,
        master=master_task,
        back=back_task,
        gameplay=gameplay_task,
        tasks_json_path=str(tasks_json_p),
        tasks_back_path=str(tasks_back_p),
        tasks_gameplay_path=str(tasks_gameplay_p),
        taskdoc_path=taskdoc_path,
    )

