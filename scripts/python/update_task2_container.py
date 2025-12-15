#!/usr/bin/env python3
"""
Update Task 2 (id=2) wording to avoid introducing City in Task 2.

- tasks.json: replace List<City> with index/placeholder container guidance
- tasks_back.json / tasks_gameplay.json: sync acceptance/test_strategy for taskmaster_id=2

All outputs are UTF-8 and an audit record is written to logs/ci/<date>/task-update/.
"""

from __future__ import annotations

import datetime as dt
import json
from pathlib import Path
from typing import Any


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")


def _find_task(tasks: list[dict], task_id: str) -> dict | None:
    for t in tasks:
        if str(t.get("id")) == task_id:
            return t
    return None


def _find_task_by_taskmaster_id(tasks: list[dict], taskmaster_id: int) -> dict | None:
    for t in tasks:
        try:
            if int(t.get("taskmaster_id")) == taskmaster_id:
                return t
        except Exception:
            continue
    return None


def _update_task2_tasks_json(tasks_json: dict) -> dict:
    tasks = tasks_json.get("master", {}).get("tasks", [])
    if not isinstance(tasks, list):
        raise ValueError("tasks.json: master.tasks is not a list")

    task = _find_task(tasks, "2")
    if task is None:
        raise ValueError("tasks.json: task id=2 not found")

    before = {
        "details": task.get("details", ""),
        "testStrategy": task.get("testStrategy", ""),
    }

    details: str = str(task.get("details", ""))
    suffix = ""
    pivot = "在地图与关卡设计上"
    idx = details.find(pivot)
    if idx >= 0:
        suffix = details[idx:]

    new_details_prefix = (
        "使用纯 C# 的环形索引抽象（例如 `CircularMapPosition(current, totalPositions)`），"
        "或以 `List<int>` 表示环形路线上的格子索引/城池占位符；"
        "先实现根据当前位置和骰子点数计算新位置、以及多步移动的索引序列（不引入 `City` 领域对象）。"
        "`City` 的定义与计价/过路费逻辑在 Task 3 落地，并在后续通过 index→City 映射接入本结构。"
    )
    task["details"] = (new_details_prefix + suffix) if suffix else new_details_prefix

    ts: str = str(task.get("testStrategy", ""))
    local_pivot = "\nLocal demo paths:"
    local_suffix = ""
    if local_pivot in ts:
        local_suffix = ts.split(local_pivot, 1)[1]

    new_test_strategy_prefix = (
        "编写单元测试，验证环形索引在正常与边界位置上的跳转是否正确；"
        "并通过构造多步移动用例对照预期“索引序列/路径”，确保与设计文档中的环形路线行为一致（不依赖 `City`）。"
    )
    task["testStrategy"] = (
        new_test_strategy_prefix + local_pivot + local_suffix if local_suffix else new_test_strategy_prefix
    )

    after = {
        "details": task.get("details", ""),
        "testStrategy": task.get("testStrategy", ""),
    }
    return {"before": before, "after": after}


def _replace_phrase(items: list[str], old: str, new: str) -> list[str]:
    out: list[str] = []
    for s in items:
        if s == old:
            out.append(new)
        else:
            out.append(s)
    return out


def _update_task2_back_or_gameplay(data: list[dict]) -> dict:
    task = _find_task_by_taskmaster_id(data, 2)
    if task is None:
        raise ValueError("tasks_back/tasks_gameplay: taskmaster_id=2 not found")

    before = {
        "acceptance": list(task.get("acceptance") or []),
        "test_strategy": list(task.get("test_strategy") or []),
    }

    acceptance = list(task.get("acceptance") or [])
    test_strategy = list(task.get("test_strategy") or [])

    acceptance = [
        s.replace("（棋盘 / 城池 / 环形路线）", "（棋盘 / 环形路线）")
        for s in acceptance
    ]

    # Clarify boundary: Task 2 is index/path only; City lands in Task 3.
    boundary_line = "Task 2 仅落地环形索引/路径计算，不引入 `City`；`City` 在 Task 3 落地并通过映射接入。"
    if boundary_line not in acceptance:
        acceptance.insert(0, boundary_line)

    test_strategy = [
        s.replace("用于验证环形路线与城池状态更新逻辑", "用于验证环形路线的索引跳转与多步路径序列（不依赖 `City`）")
        for s in test_strategy
    ]

    task["acceptance"] = acceptance
    task["test_strategy"] = test_strategy

    after = {"acceptance": task.get("acceptance"), "test_strategy": task.get("test_strategy")}
    return {"before": before, "after": after}


def main() -> int:
    repo_root = Path(__file__).resolve().parents[2]
    tasks_dir = repo_root / ".taskmaster" / "tasks"
    tasks_json_path = tasks_dir / "tasks.json"
    tasks_back_path = tasks_dir / "tasks_back.json"
    tasks_gameplay_path = tasks_dir / "tasks_gameplay.json"

    tasks_json = _read_json(tasks_json_path)
    tasks_back = _read_json(tasks_back_path)
    tasks_gameplay = _read_json(tasks_gameplay_path)

    audit: dict[str, Any] = {
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z"),
        "changes": {},
    }

    audit["changes"]["tasks.json"] = _update_task2_tasks_json(tasks_json)
    audit["changes"]["tasks_back.json"] = _update_task2_back_or_gameplay(tasks_back)
    audit["changes"]["tasks_gameplay.json"] = _update_task2_back_or_gameplay(tasks_gameplay)

    _write_json(tasks_json_path, tasks_json)
    _write_json(tasks_back_path, tasks_back)
    _write_json(tasks_gameplay_path, tasks_gameplay)

    date = dt.date.today().strftime("%Y-%m-%d")
    out_dir = repo_root / "logs" / "ci" / date / "task-update"
    out_path = out_dir / "task2-container-update.json"
    _write_json(out_path, audit)

    print(f"TASK2_CONTAINER_UPDATE status=ok out={out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

