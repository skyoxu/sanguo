#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Update T2 evolution notes in tasks_back.json and tasks_gameplay.json.

Scope:
- Do not change JSON schema/field names.
- Append (dedupe) short evolution notes into acceptance/test_strategy for a few tasks.

This is a repo-local helper to keep Taskmaster triplet files aligned (master ↔ back/gameplay).
"""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
TASKS_BACK = ROOT / ".taskmaster" / "tasks" / "tasks_back.json"
TASKS_GAMEPLAY = ROOT / ".taskmaster" / "tasks" / "tasks_gameplay.json"


def _append_unique(items: list[str], value: str) -> None:
    if value not in items:
        items.append(value)


def _ensure_list(task: dict, key: str) -> list[str]:
    value = task.get(key)
    if value is None:
        value = []
        task[key] = value
    if not isinstance(value, list):
        raise TypeError(f"Task {task.get('id')} field {key} must be a list.")
    for i, v in enumerate(value):
        if not isinstance(v, str):
            raise TypeError(f"Task {task.get('id')} field {key}[{i}] must be a string.")
    return value


def _load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload) -> None:
    text = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    with path.open("w", encoding="utf-8", newline="\n") as f:
        f.write(text)


def _apply_updates(tasks: list[dict]) -> None:
    by_taskmaster_id = {t.get("taskmaster_id"): t for t in tasks}

    # City ownership future evolution (avoid double SSoT drift).
    city_ownership_note = (
        "后续演进（所有权 SSoT）：当 UI/存档/回放需要全局城池所有权状态时，"
        "统一引入 CityOwnershipRegistry（CityId -> OwnerId?）作为唯一事实来源；"
        "玩家侧 OwnedCityIds 仅为派生快照/缓存；出局释放必须清理 registry，禁止双写不同步。"
    )

    # Toll payment API future evolution (avoid implicit bool + missing handling).
    toll_outcome_note = (
        "后续演进（结算结果对象）：将过路费/破产结算从 bool 演进为 TollPaymentOutcome，"
        "至少包含 PaidToOwner/OverflowToTreasury/PayerEliminated/ReleasedCityIds，"
        "由 TurnManager/EconomyService/UI 统一消费，避免调用方漏处理溢出或漏清理城池。"
    )

    # Task 12: buying / ownership entry point.
    t12 = by_taskmaster_id.get(12)
    if isinstance(t12, dict):
        _append_unique(_ensure_list(t12, "acceptance"), city_ownership_note)
        _append_unique(
            _ensure_list(t12, "test_strategy"),
            "加入 xUnit 用例：验证 CityOwnershipRegistry 的单一事实来源不变式（同一 CityId 不能同时属于多个玩家；出局释放后 owner 必为 null）。",
        )

    # Task 13: toll payment / bankruptcy path.
    t13 = by_taskmaster_id.get(13)
    if isinstance(t13, dict):
        _append_unique(_ensure_list(t13, "acceptance"), city_ownership_note)
        _append_unique(_ensure_list(t13, "acceptance"), toll_outcome_note)
        _append_unique(
            _ensure_list(t13, "test_strategy"),
            "加入 xUnit 用例：覆盖足额/不足额/收款方封顶溢出三路径，并断言 TollPaymentOutcome 字段与实际状态一致。",
        )

    # Task 17: game loop consumes outcomes and handles toast/audit.
    t17 = by_taskmaster_id.get(17)
    if isinstance(t17, dict):
        _append_unique(
            _ensure_list(t17, "acceptance"),
            "后续演进（Task 13/17）：GameLoop 不通过推断判断溢出/出局，而是消费 TollPaymentOutcome 驱动 toast/audit/treasury 归集，保证状态更新原子。",
        )

    # Task 23: UI city state display consumes the same SSoT.
    t23 = by_taskmaster_id.get(23)
    if isinstance(t23, dict):
        _append_unique(
            _ensure_list(t23, "acceptance"),
            "城池 UI 状态必须基于单一所有权来源：Phase 1 从玩家 OwnedCityIds 派生；Phase 2 引入 CityOwnershipRegistry 后仅从 registry 读取。",
        )


def main() -> int:
    back = _load_json(TASKS_BACK)
    game = _load_json(TASKS_GAMEPLAY)

    if not isinstance(back, list):
        raise TypeError("tasks_back.json root must be a list.")
    if not isinstance(game, list):
        raise TypeError("tasks_gameplay.json root must be a list.")

    _apply_updates(back)
    _apply_updates(game)

    _write_json(TASKS_BACK, back)
    _write_json(TASKS_GAMEPLAY, game)

    print(f"ok updated: {TASKS_BACK}")
    print(f"ok updated: {TASKS_GAMEPLAY}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

