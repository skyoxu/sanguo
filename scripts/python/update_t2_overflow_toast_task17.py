#!/usr/bin/env python3
"""
Update Task 17 descriptions to specify runtime handling for Money overflow.

This script modifies:
- .taskmaster/tasks/tasks.json (Task id "17"): details/testStrategy (string fields)
- .taskmaster/tasks/tasks_back.json (taskmaster_id == 17): acceptance/test_strategy (list fields)
- .taskmaster/tasks/tasks_gameplay.json (taskmaster_id == 17): acceptance/test_strategy (list fields)

Notes:
- Uses UTF-8 read/write (repo requirement).
- Preserves JSON key order by relying on Python's insertion-ordered dict.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def append_unique_line(text: str, line: str) -> str:
    if line in text:
        return text
    if not text.endswith("\n"):
        text += "\n"
    return text + line + "\n"

def replace_line_containing(text: str, needle: str, replacement: str) -> str:
    lines = text.splitlines()
    replaced = False
    out: list[str] = []
    for ln in lines:
        if needle in ln:
            out.append(replacement)
            replaced = True
        else:
            out.append(ln)
    if not replaced:
        out.append(replacement)
    return "\n".join(out).rstrip("\n") + "\n"


def append_unique_item(items: list[str], item: str) -> None:
    if item not in items:
        items.append(item)


def update_tasks_json(tasks_path: Path) -> None:
    data = load_json(tasks_path)
    tasks = data.get("master", {}).get("tasks", [])
    for task in tasks:
        if task.get("id") == "17":
            details_line = (
                "新增异常边界：当领域层触发 Money 上限（OverflowException）时，回合循环应捕获异常、写入审计日志并上报错误；"
                "前台用 3 秒自动消失的浮窗提示替代 GameOver/错误界面，本次动作视为失败且不得产生半更新状态。"
            )
            test_line = (
                "新增用例：构造会触发 Money 上限的结算/转账路径，验证回合循环捕获 OverflowException 后仍可继续推进；"
                "同时校验审计日志/错误上报被调用，且浮窗提示显示 3 秒后自动消失。"
            )
            details_line = (
                "新增异常边界：当金额入账触发 Money 上限时（例如过路费/结算导致收款方超上限），回合循环应记录审计日志并上报错误；"
                "前台用 3 秒自动消失的浮窗提示替代 GameOver/错误界面；并采用封顶规则：付款方仍扣全额，收款方资金封顶，溢出金额进入国库（或按设计丢弃），不得产生半更新状态。"
            )
            test_line = (
                "新增用例：构造会触发 Money 上限的转账路径，验证回合循环不中断推进；"
                "同时校验审计日志/错误上报被调用，浮窗提示 3 秒后自动消失；并断言封顶规则（付款方扣全额、收款方封顶、溢出进入国库/丢弃）。"
            )
            task["details"] = replace_line_containing(task.get("details", ""), "新增异常边界：", details_line)
            task["testStrategy"] = replace_line_containing(task.get("testStrategy", ""), "新增用例：构造会触发 Money 上限", test_line)
            break
    save_json(tasks_path, data)


def update_tasks_list(list_path: Path) -> None:
    items = load_json(list_path)
    if not isinstance(items, list):
        raise ValueError(f"Expected list JSON: {list_path}")

    acceptance_item = (
        "Money overflow handling (Task 17): when a credit operation would exceed Money max limit, "
        "the game loop writes an audit entry (logs/** per AGENTS 6.3) and reports via IErrorReporter; "
        "UI shows a non-blocking toast for 3 seconds; apply cap rule: payer still pays full amount, creditor is capped at max, "
        "overflow goes to treasury (or discarded by design) and state updates must be atomic."
    )
    test_item = (
        "Add a test scenario to force Money overflow during turn processing and assert: "
        "(1) payer deducted full amount, (2) creditor capped at max, (3) overflow accounted to treasury (or discarded), "
        "(4) audit/error reporter invoked, (5) toast shown and auto-dismissed."
    )

    for t in items:
        if t.get("taskmaster_id") == 17:
            acceptance = t.get("acceptance")
            test_strategy = t.get("test_strategy")
            if isinstance(acceptance, list):
                acceptance[:] = [x for x in acceptance if not x.startswith("Money overflow handling (Task 17):")]
                append_unique_item(acceptance, acceptance_item)
            if isinstance(test_strategy, list):
                test_strategy[:] = [x for x in test_strategy if not x.startswith("Add a test scenario to force Money overflow")]
                append_unique_item(test_strategy, test_item)
            break

    save_json(list_path, items)


def main() -> int:
    tasks_json = REPO_ROOT / ".taskmaster" / "tasks" / "tasks.json"
    tasks_back = REPO_ROOT / ".taskmaster" / "tasks" / "tasks_back.json"
    tasks_gameplay = REPO_ROOT / ".taskmaster" / "tasks" / "tasks_gameplay.json"

    update_tasks_json(tasks_json)
    update_tasks_list(tasks_back)
    update_tasks_list(tasks_gameplay)

    print("OK: updated Task 17 overflow handling in tasks.json/tasks_back.json/tasks_gameplay.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
