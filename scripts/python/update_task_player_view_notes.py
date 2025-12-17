#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Update supplemental task notes to require using ISanguoPlayerView snapshots for UI/AI reads.

Why this exists:
- Console pipelines can corrupt non-ASCII text depending on the active code page.
- This script keeps its source ASCII-friendly and writes JSON as UTF-8.

Targets:
  - .taskmaster/tasks/tasks_back.json
  - .taskmaster/tasks/tasks_gameplay.json
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any, Dict, List, Tuple


PROJECT_ROOT = Path(__file__).resolve().parents[2]
TASK_FILES = [
    PROJECT_ROOT / ".taskmaster" / "tasks" / "tasks_back.json",
    PROJECT_ROOT / ".taskmaster" / "tasks" / "tasks_gameplay.json",
]


def zh(s: str) -> str:
    """
    Decode a \\uXXXX-escaped literal into a Unicode string.
    Keep the Python source ASCII-only while emitting Chinese into JSON.
    """

    return s.encode("ascii").decode("unicode_escape")


AI_ACCEPTANCE_LINE = zh(
    "AI \\u51b3\\u7b56\\u8bfb\\u53d6\\u73a9\\u5bb6\\u72b6\\u6001\\u5fc5\\u987b\\u901a\\u8fc7 `ISanguoPlayerView`\\uff08\\u63a8\\u8350\\u4f7f\\u7528 `SanguoPlayer.ToView()` \\u751f\\u6210 `SanguoPlayerView` \\u5feb\\u7167\\uff09\\uff0c\\u7981\\u6b62\\u76f4\\u63a5\\u6301\\u6709/\\u8de8\\u7ebf\\u7a0b\\u8bbf\\u95ee `SanguoPlayer` \\u5b9e\\u4f53\\uff1b\\u540e\\u53f0\\u7ebf\\u7a0b\\u4ec5\\u63a5\\u6536\\u5feb\\u7167\\u8f93\\u5165\\u3002\\u53c2\\u8003\\uff1a`Game.Core/Domain/ISanguoPlayerView.cs`\\u3001`Game.Core/Domain/SanguoPlayer.cs:ToView()`\\u3001`Game.Core/Domain/SanguoPlayerView.cs`\\u3002"
)

AI_TEST_STRATEGY_LINE = zh(
    "\\u65b0\\u589e\\u5355\\u6d4b\\uff1aAI \\u884c\\u4e3a\\u4ec5\\u4f9d\\u8d56 `ISanguoPlayerView`/`SanguoPlayerView` \\u8f93\\u5165\\uff1b\\u6a21\\u62df\\u540e\\u53f0\\u7ebf\\u7a0b\\u8c03\\u7528\\u65f6\\u4e0d\\u5f97\\u89e6\\u53d1 `ThreadAccessGuard`\\uff08\\u5373\\u4e0d\\u76f4\\u63a5\\u8c03\\u7528 `SanguoPlayer` \\u4e0a\\u7684\\u65b9\\u6cd5\\uff09\\u3002"
)

UI_ACCEPTANCE_LINE = zh(
    "UI \\u5c55\\u793a\\u5c42\\u8bfb\\u53d6\\u73a9\\u5bb6\\u72b6\\u6001\\u5fc5\\u987b\\u901a\\u8fc7 `ISanguoPlayerView`\\uff08\\u63a8\\u8350\\u4f7f\\u7528 `SanguoPlayer.ToView()` \\u751f\\u6210 `SanguoPlayerView` \\u5feb\\u7167\\uff09\\uff0c\\u7981\\u6b62 UI \\u76f4\\u63a5\\u6301\\u6709 `SanguoPlayer` \\u5b9e\\u4f53\\u4f5c\\u4e3a\\u72b6\\u6001\\u6e90\\uff1b\\u8de8\\u5c42\\u4f20\\u9012\\u4ec5\\u63a5\\u6536\\u5feb\\u7167\\uff0c\\u9632\\u6b62\\u672a\\u6765\\u5e76\\u53d1/\\u540e\\u53f0\\u8ba1\\u7b97\\u5f15\\u5165\\u7684\\u8c03\\u7528\\u7ebf\\u7a0b\\u8fdd\\u4f8b\\u3002\\u53c2\\u8003\\uff1a`Game.Core/Domain/ISanguoPlayerView.cs`\\u3001`Game.Core/Domain/SanguoPlayer.cs:ToView()`\\u3001`Game.Core/Domain/SanguoPlayerView.cs`\\u3002"
)

UI_TEST_STRATEGY_LINE = zh(
    "\\u7f16\\u5199/\\u66f4\\u65b0 UI \\u7528\\u4f8b\\uff1aUI \\u6570\\u636e\\u7ed1\\u5b9a\\u4ec5\\u4f7f\\u7528 `SanguoPlayerView`\\uff08\\u6216 `ISanguoPlayerView`\\uff09\\u5feb\\u7167\\u8f93\\u5165\\uff0c\\u4e0d\\u5f97\\u76f4\\u63a5\\u5f15\\u7528 `SanguoPlayer`\\uff1b\\u82e5\\u9700\\u8981\\u80cc\\u666f\\u7ebf\\u7a0b\\u66f4\\u65b0 UI\\uff0c\\u5fc5\\u987b\\u5148\\u751f\\u6210\\u5feb\\u7167\\u518d\\u53d1\\u9001\\u5230\\u4e3b\\u7ebf\\u7a0b\\u6e32\\u67d3\\u3002"
)


@dataclass(frozen=True)
class Change:
    file: str
    taskmaster_id: str
    field: str
    action: str
    value: str


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def is_corrupted_placeholder(text: str) -> bool:
    if not isinstance(text, str):
        return False
    return "ISanguoPlayerView" in text and "?" in text


def ensure_list_field(task: Dict[str, Any], field: str) -> List[str]:
    value = task.get(field)
    if value is None:
        task[field] = []
        return task[field]
    if not isinstance(value, list):
        raise SystemExit(f"Invalid field type: {field}={type(value)}")
    return value


def apply_lines(
    task: Dict[str, Any],
    taskmaster_id: str,
    acceptance_line: str,
    test_strategy_line: str,
    rel_path: str,
) -> List[Change]:
    changes: List[Change] = []

    acceptance = ensure_list_field(task, "acceptance")
    before = list(acceptance)
    acceptance[:] = [x for x in acceptance if not is_corrupted_placeholder(str(x))]
    if acceptance != before:
        changes.append(
            Change(
                file=rel_path,
                taskmaster_id=taskmaster_id,
                field="acceptance",
                action="remove_corrupted",
                value="ISanguoPlayerView placeholders",
            )
        )
    if not any("ISanguoPlayerView" in str(x) and "?" not in str(x) for x in acceptance):
        acceptance.append(acceptance_line)
        changes.append(
            Change(
                file=rel_path,
                taskmaster_id=taskmaster_id,
                field="acceptance",
                action="append",
                value=acceptance_line,
            )
        )

    test_strategy = ensure_list_field(task, "test_strategy")
    before = list(test_strategy)
    test_strategy[:] = [x for x in test_strategy if not is_corrupted_placeholder(str(x))]
    if test_strategy != before:
        changes.append(
            Change(
                file=rel_path,
                taskmaster_id=taskmaster_id,
                field="test_strategy",
                action="remove_corrupted",
                value="ISanguoPlayerView placeholders",
            )
        )
    if not any("ISanguoPlayerView" in str(x) and "?" not in str(x) for x in test_strategy):
        test_strategy.append(test_strategy_line)
        changes.append(
            Change(
                file=rel_path,
                taskmaster_id=taskmaster_id,
                field="test_strategy",
                action="append",
                value=test_strategy_line,
            )
        )

    return changes


def update_task(path: Path, taskmaster_id: str, mode: str) -> List[Change]:
    data = load_json(path)
    if not isinstance(data, list):
        raise SystemExit(f"Unexpected JSON root in {path}: {type(data)}")

    task = next((t for t in data if str(t.get("taskmaster_id")) == str(taskmaster_id)), None)
    if task is None:
        raise SystemExit(f"Missing taskmaster_id={taskmaster_id} in {path}")

    if mode == "ai":
        acceptance_line, test_strategy_line = AI_ACCEPTANCE_LINE, AI_TEST_STRATEGY_LINE
    elif mode == "ui":
        acceptance_line, test_strategy_line = UI_ACCEPTANCE_LINE, UI_TEST_STRATEGY_LINE
    else:
        raise SystemExit(f"Unknown mode: {mode}")

    rel = str(path.relative_to(PROJECT_ROOT))
    changes = apply_lines(task, str(taskmaster_id), acceptance_line, test_strategy_line, rel)

    if changes:
        write_json(path, data)

    return changes


def write_audit(changes: List[Change]) -> None:
    if not changes:
        return
    out_dir = PROJECT_ROOT / "logs" / "ci" / date.today().isoformat()
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "task-player-view-notes.json"
    out_path.write_text(json.dumps([c.__dict__ for c in changes], ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"[audit] {out_path}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--taskmaster-id", required=True, help="Task id in tasks.json (e.g., 9 or 11).")
    parser.add_argument("--mode", choices=["ui", "ai"], required=True, help="Which wording to apply.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    all_changes: List[Change] = []
    for path in TASK_FILES:
        changes = update_task(path, args.taskmaster_id, args.mode)
        status = "changed" if changes else "no-op"
        print(f"[update] {path.relative_to(PROJECT_ROOT)}: {status}")
        all_changes.extend(changes)

    write_audit(all_changes)


if __name__ == "__main__":
    main()
