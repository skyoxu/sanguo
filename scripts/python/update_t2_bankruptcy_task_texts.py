#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Update task text in .taskmaster/tasks/*.json to reflect the agreed T2 bankruptcy rules.

Rules (agreed by user):
  - If toll payment is insufficient: transfer remaining money to creditor, payer money becomes 0, payer is eliminated.
  - Eliminated NPC: exits the match; owned cities become unowned.
  - Eliminated human player: game over (handled by TurnManager / game loop tasks).

This script only updates task descriptions/acceptance/test strategy text (and Task 4 test_refs),
and keeps JSON field structure intact.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
TASKMASTER_DIR = REPO_ROOT / ".taskmaster" / "tasks"


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")


def split_local_demo(text: str) -> tuple[str, str]:
    marker = "\nLocal demo paths:"
    if marker in text:
        main, rest = text.split(marker, 1)
        return main, "Local demo paths:" + rest
    return text, ""


def clean_garbled_lines(lines: list[str]) -> list[str]:
    cleaned: list[str] = []
    for line in lines:
        stripped = (line or "").lstrip()
        if stripped.startswith("?"):
            continue
        cleaned.append(line)
    return cleaned


def insert_before_local_demo(lines: list[str], new_line: str) -> list[str]:
    if new_line in lines:
        return lines
    for i, line in enumerate(lines):
        if isinstance(line, str) and line.startswith("Local demo references:"):
            return lines[:i] + [new_line] + lines[i:]
    return lines + [new_line]


def insert_before_local_demo_paths(lines: list[str], new_line: str) -> list[str]:
    if new_line in lines:
        return lines
    for i, line in enumerate(lines):
        if isinstance(line, str) and line.startswith("Local demo paths for implementation/tests:"):
            return lines[:i] + [new_line] + lines[i:]
    return lines + [new_line]


def update_tasks_json() -> None:
    path = TASKMASTER_DIR / "tasks.json"
    data = read_json(path)
    tasks = data.get("master", {}).get("tasks", [])

    for task in tasks:
        tid = str(task.get("id"))
        if tid == "4":
            task["details"] = (
                "新增 SanguoPlayer（避免复用现有战斗语义 Player），增加资金、当前位置索引、已拥有城池列表等属性，"
                "实现购买城池与支付过路费的方法；所有经济结算保持在 Game.Core 层，不依赖 Godot。"
                "过路费破产规则（与 Task 13 对齐）：当资金不足以支付过路费时，将剩余资金一次性转给债权人，"
                "支付方资金归零并判定出局，同时释放其全部已占领城池为无人占领；真人玩家出局触发 GameOver，"
                "NPC 出局退出本局由 TurnManager 处理。"
                "在职责划分与输入处理上，可参考 Godot 官方演示项目 2d/kinematic_character、2d/platformer 中的角色控制器结构，"
                "采用类似的“数据在 Core、表现留在 Godot 场景”的分层思路。"
            )
            task["testStrategy"] = (
                "编写 xUnit 单元测试，验证玩家属性初始化、购买城池、支付过路费等方法在不同边界条件下的行为；"
                "覆盖资金不足支付过路费的破产/出局分支：剩余资金转移给债权人、资金不允许为负、出局后释放城池为无人占领；"
                "通过构造多轮交易场景，确保资金与城池所有权变更符合 T2 PRD 中的经济规则。"
            )

        if tid == "6":
            task["details"] = (
                "创建 TurnManager 类，管理当前日期（年/月/日）和当前行动玩家，实现 NextTurn() 方法，按 T2 PRD 规定的顺序推进"
                "“玩家行动 → 日推进 → 月末结算 → 季度事件 → 年度地价调整”等阶段。时间轴与回合驱动逻辑保持在 Game.Core 中，"
                "Godot 层只负责展示当前轮次与日期。\n\n"
                "破产/出局规则（与 Task 13 对齐）：当行动者在本回合内发生资金不足支付（例如过路费）时，将其剩余资金一次性转给债权人，"
                "行动者资金归零并判定出局；出局者释放全部已占领城池为无人占领。真人玩家出局立即触发 GameOver；"
                "NPC 出局从后续回合轮转中移除并锁定状态（不再行动/不再参与结算）。"
            )
            _, local = split_local_demo(task.get("testStrategy", ""))
            task["testStrategy"] = (
                "通过 xUnit 模拟多回合游戏流程，验证在不同起始日期下推进若干回合后，玩家轮换顺序、日期、月份、季度与年度节点都与 "
                "T2 PRD 中的时间轴设计一致。\n\n"
                "补充：加入“资金不足支付→出局”场景，验证剩余资金转移给债权人、出局者资金归零且释放城池；"
                "真人玩家触发 GameOver，NPC 被从轮转列表剔除且不会再获得回合。"
                + ("\n" + local if local else "")
            )

        if tid == "13":
            task["details"] = (
                "在玩家停留在他人城池时，计算应支付过路费并更新资金；若资金不足，则将剩余资金转给债权人，支付方资金归零并判定出局，"
                "同时释放其全部已占领城池为无人占领（回合轮转/游戏结束由 TurnManager 处理：玩家出局→GameOver；NPC 出局→退出本局）。"
            )
            _, local = split_local_demo(task.get("testStrategy", ""))
            task["testStrategy"] = (
                "通过多次支付测试，验证过路费计算和资金更新的正确性，并覆盖资金不足的破产/出局分支："
                "剩余资金正确转移、资金不允许为负、城池释放为无人占领。"
                + ("\n" + local if local else "")
            )

        if tid == "17":
            task["details"] = (
                "实现回合循环逻辑，确保玩家和AI轮流行动，时间正常推进，并正确处理出局者：跳过已出局 NPC；"
                "真人玩家出局时立即结束回合循环并触发游戏结束。"
            )
            _, local = split_local_demo(task.get("testStrategy", ""))
            task["testStrategy"] = (
                "通过长时间运行游戏，验证回合循环的稳定性和正确性，并包含 NPC 出局后轮转跳过、玩家出局触发 GameOver 的用例。"
                + ("\n" + local if local else "")
            )

        if tid == "26":
            task["details"] = (
                "在游戏达到特定条件时，触发游戏结束。至少覆盖：真人玩家因资金不足支付过路费而出局→GameOver；"
                "NPC 资金不足则出局退出本局，其城池状态改为无人占领。"
            )
            task["testStrategy"] = (
                "通过模拟多种结束条件，验证游戏结束的正确性；至少包含真人玩家资金不足支付触发 GameOver、"
                "NPC 资金不足退出且其城池释放为无人占领的用例。"
            )

    write_json(path, data)


def update_aux_tasks(file_name: str, taskmaster_ids: set[int]) -> None:
    path = TASKMASTER_DIR / file_name
    data = read_json(path)
    if not isinstance(data, list):
        raise SystemExit(f"{path} must be a JSON array")

    for item in data:
        tm_id = item.get("taskmaster_id")
        try:
            tm_id_int = int(tm_id)
        except Exception:
            continue
        if tm_id_int not in taskmaster_ids:
            continue

        if tm_id_int == 4:
            item["test_refs"] = ["Game.Core.Tests/Domain/SanguoPlayerTests.cs"]

        acc = item.get("acceptance")
        if isinstance(acc, list):
            acc = clean_garbled_lines(acc)
            if tm_id_int in (4, 13):
                acc = insert_before_local_demo(
                    acc,
                    "过路费破产规则：资金不足支付时，将剩余资金一次性转给债权人，支付方资金归零并判定出局；出局者释放全部已占领城池为无人占领（不允许出现 Money < 0）。",
                )
            if tm_id_int in (6, 17, 26):
                acc = insert_before_local_demo(
                    acc,
                    "回合/循环需正确处理出局：真人玩家出局立即 GameOver；NPC 出局退出本局并从后续轮转中移除（状态锁定），其已占领城池变为无人占领。",
                )
            item["acceptance"] = acc

        ts = item.get("test_strategy")
        if isinstance(ts, list):
            ts = clean_garbled_lines(ts)
            if tm_id_int in (4, 13):
                ts = insert_before_local_demo_paths(
                    ts,
                    "加入资金不足支付过路费的测试：验证剩余资金转移给债权人、支付方资金归零并出局、城池释放为无人占领，并确保不会出现负资金。",
                )
            if tm_id_int in (6, 17, 26):
                ts = insert_before_local_demo_paths(
                    ts,
                    "加入出局相关的轮转/结束用例：验证玩家出局触发 GameOver，NPC 出局后轮转跳过且不会再获得回合，并校验其城池已释放为无人占领。",
                )
            item["test_strategy"] = ts

    write_json(path, data)


def main() -> int:
    update_tasks_json()
    update_aux_tasks("tasks_back.json", {4, 6, 13, 17, 26})
    update_aux_tasks("tasks_gameplay.json", {4, 6, 13, 17})
    print("ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

