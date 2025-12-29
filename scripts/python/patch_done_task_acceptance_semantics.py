#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Patch a small set of done tasks to align acceptance semantics with deterministic evidence.

Scope:
  - Task 1: rebind acceptance to deterministic "task views" checks (no longer bind to unrelated core ctor tests)
  - Task 9: rebind ACC:T9.3 to a deterministic UI boundary guard test
  - Task 12: remove CityTests from Refs for clarity; keep anchors aligned after earlier migrations
  - Task 14: remove the non-testable process clause from acceptance and move it to test_strategy

This script intentionally does not touch tasks.json (master view).

Usage (Windows):
  py -3 scripts/python/patch_done_task_acceptance_semantics.py --apply
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


REFS_RE = re.compile(r"\bRefs\s*:\s*(.+)$", flags=re.IGNORECASE)


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")


def split_refs(line: str) -> tuple[str, list[str]]:
    m = REFS_RE.search(line.strip())
    if not m:
        return line.strip(), []
    prefix = line[: m.start()].rstrip()
    blob = m.group(1) or ""
    normalized = blob.replace("`", " ").replace(",", " ").replace(";", " ")
    refs = [t.strip().replace("\\", "/") for t in normalized.split() if t.strip()]
    return prefix.rstrip(), refs


def join_refs(prefix: str, refs: list[str]) -> str:
    refs_norm: list[str] = []
    for r in refs:
        rr = str(r).strip().replace("\\", "/")
        if rr and rr not in refs_norm:
            refs_norm.append(rr)
    return f"{prefix} Refs: " + " ".join(refs_norm)


def ensure_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(x) for x in value if str(x).strip()]
    if isinstance(value, str):
        s = value.strip()
        return [s] if s else []
    return [str(value)]


def ensure_in_list(items: list[str], value: str) -> None:
    v = value.strip()
    if v and v not in items:
        items.append(v)


def patch_task_1(task: dict[str, Any]) -> dict[str, Any]:
    test_file = "Game.Core.Tests/Tasks/Task1TaskViewsTests.cs"
    acceptance = [
        "Taskmaster 任务三联文件（.taskmaster/tasks/tasks.json、tasks_back.json、tasks_gameplay.json）在 Windows 环境下可解析，且关键字段（id/status/taskmaster_id）满足基本约束。"
        + f" Refs: {test_file}",
        "任务视图（tasks_back/tasks_gameplay）的 taskmaster_id 与 tasks.json 中的 task id 一一对应（允许缺一侧但至少存在一侧），且不存在重复/缺失。"
        + f" Refs: {test_file}",
    ]
    task["acceptance"] = acceptance

    ts = ensure_list(task.get("test_strategy"))
    note = "（从 acceptance 迁移：执行环境/CI 事实由脚本门禁提供证据）"
    if note not in ts:
        ts.append(note)
        ts.append("- 原条款“脚本可运行/不破坏 CI”以 CI/验收脚本的可重复证据链为准，不再作为单测锚点验收。")
    task["test_strategy"] = ts

    tr = ensure_list(task.get("test_refs"))
    ensure_in_list(tr, test_file)
    task["test_refs"] = tr
    return task


def patch_task_9(task: dict[str, Any]) -> dict[str, Any]:
    test_file = "Game.Core.Tests/Tasks/Task9UiBoundaryTests.cs"
    acc = ensure_list(task.get("acceptance"))
    if len(acc) >= 3:
        prefix, _refs = split_refs(acc[2])
        acc[2] = join_refs(prefix, [test_file])
        task["acceptance"] = acc

    tr = ensure_list(task.get("test_refs"))
    ensure_in_list(tr, test_file)
    task["test_refs"] = tr
    return task


def patch_task_12(task: dict[str, Any]) -> dict[str, Any]:
    # Remove CityTests from Refs to avoid confusing evidence linkage (CityTests carries T3 anchors).
    drop = "Game.Core.Tests/Domain/CityTests.cs"
    acc = ensure_list(task.get("acceptance"))
    new_acc: list[str] = []
    for line in acc:
        prefix, refs = split_refs(line)
        # Also remove the "map index range" clause which cannot be proven at this stage (TotalPositions is a later task concern).
        prefix = prefix.replace("、与环形地图索引范围一致", "")
        refs2 = [r for r in refs if r != drop]
        new_acc.append(join_refs(prefix, refs2) if refs else line)
    task["acceptance"] = new_acc

    tr = ensure_list(task.get("test_refs"))
    # Keep test_refs as a superset; do not delete historical entries.
    task["test_refs"] = tr

    ts = ensure_list(task.get("test_strategy"))
    note = "（从 acceptance 迁移：后续任务口径/本任务不做硬验收）"
    if note not in ts:
        ts.append(note)
        ts.append("- “与环形地图索引范围一致”需要依赖棋盘总格数（TotalPositions）口径与配置，属于后续任务（如回合循环/棋盘配置任务）再收敛。")
    task["test_strategy"] = ts
    return task


def patch_task_14(task: dict[str, Any]) -> dict[str, Any]:
    acc = ensure_list(task.get("acceptance"))
    if len(acc) >= 2 and "不得自行临时拼装" in acc[1]:
        prefix, refs = split_refs(acc[1])
        # Remove the non-testable clause, keep the board state requirement.
        prefix2 = prefix.replace("本任务不得自行临时拼装 players/citiesById；", "").strip()
        task["acceptance"] = [acc[0], join_refs(prefix2, refs)]

        ts = ensure_list(task.get("test_strategy"))
        note = "（从 acceptance 迁移：过程约束/不可由单测证明）"
        if note not in ts:
            ts.append(note)
            ts.append("- 本任务不得自行临时拼装 players/citiesById（该约束需通过代码评审/设计口径保障）。")
        task["test_strategy"] = ts
    return task


def patch_view(view: list[dict[str, Any]]) -> int:
    changed = 0
    for t in view:
        if not isinstance(t, dict):
            continue
        tid = t.get("taskmaster_id")
        if tid == 1:
            patch_task_1(t)
            changed += 1
        elif tid == 9:
            patch_task_9(t)
            changed += 1
        elif tid == 12:
            patch_task_12(t)
            changed += 1
        elif tid == 14:
            patch_task_14(t)
            changed += 1
    return changed


def main() -> int:
    ap = argparse.ArgumentParser(description="Patch done tasks acceptance semantics in tasks_back/tasks_gameplay.")
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    root = repo_root()
    back_path = root / ".taskmaster/tasks/tasks_back.json"
    game_path = root / ".taskmaster/tasks/tasks_gameplay.json"

    back = load_json(back_path)
    game = load_json(game_path)
    if not isinstance(back, list) or not isinstance(game, list):
        raise ValueError("Expected tasks_back.json/tasks_gameplay.json to be JSON arrays")

    back_changed = patch_view(back)
    game_changed = patch_view(game)

    if args.apply:
        write_json(back_path, back)
        write_json(game_path, game)

    print(f"PATCH_DONE_ACCEPTANCE status=ok apply={args.apply} back_changed={back_changed} gameplay_changed={game_changed}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
