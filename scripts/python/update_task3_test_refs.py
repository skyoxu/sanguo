"""
Update Task 3 test references across task files.

Targets:
  - .taskmaster/tasks/tasks.json (master task testStrategy)
  - .taskmaster/tasks/tasks_back.json (SG-0003 test_refs)
  - .taskmaster/tasks/tasks_gameplay.json (GM-0003 test_refs)

This script is designed to be safe for Taskmaster MCP:
  - It does not change JSON schema/field names.
  - It only updates existing string/list fields.

Audit output:
  logs/ci/<YYYY-MM-DD>/task-update/task3-test-refs-update.json
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


TASK_ID = "3"
TEST_REF_PATH = "Game.Core.Tests/Domain/CityTests.cs"
REMOVED_TEST_REF_PATH = "Game.Core.Tests/Tasks/Task3RedTests.cs"


@dataclass(frozen=True)
class Change:
    file: str
    action: str
    details: dict[str, Any]


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _ensure_test_ref_list(test_refs: list[str]) -> tuple[list[str], bool]:
    original = list(test_refs)

    test_refs = [ref for ref in test_refs if ref != REMOVED_TEST_REF_PATH]
    if TEST_REF_PATH not in test_refs:
        test_refs.append(TEST_REF_PATH)

    return test_refs, test_refs != original


def _inject_test_refs_into_test_strategy(text: str) -> tuple[str, bool]:
    marker = f"Test-Refs: {TEST_REF_PATH}"
    if marker in text:
        return text, False

    local_demo_idx = text.find("Local demo paths:")
    if local_demo_idx != -1:
        prefix = text[:local_demo_idx].rstrip()
        suffix = text[local_demo_idx:].lstrip()
        updated = f"{prefix}\n{marker}\n{suffix}"
        return updated, True

    updated = f"{text.rstrip()}\n{marker}"
    return updated, True


def main() -> int:
    repo_root = Path(__file__).resolve().parents[2]
    tasks_json_path = repo_root / ".taskmaster" / "tasks" / "tasks.json"
    tasks_back_path = repo_root / ".taskmaster" / "tasks" / "tasks_back.json"
    tasks_gameplay_path = repo_root / ".taskmaster" / "tasks" / "tasks_gameplay.json"

    changes: list[Change] = []

    # Update tasks.json (master)
    tasks_json = _read_json(tasks_json_path)
    tasks = tasks_json.get("master", {}).get("tasks", [])
    task = next((t for t in tasks if t.get("id") == TASK_ID), None)
    if task is None:
        raise SystemExit(f"[FAIL] Task id={TASK_ID} not found in {tasks_json_path}")

    old_test_strategy = task.get("testStrategy", "")
    new_test_strategy, changed = _inject_test_refs_into_test_strategy(old_test_strategy)
    if changed:
        task["testStrategy"] = new_test_strategy
        changes.append(
            Change(
                file=str(tasks_json_path.relative_to(repo_root)).replace("\\", "/"),
                action="update",
                details={"task_id": TASK_ID, "field": "testStrategy", "added": f"Test-Refs: {TEST_REF_PATH}"},
            )
        )

    # Update tasks_back.json
    back_tasks = _read_json(tasks_back_path)
    if not isinstance(back_tasks, list):
        raise SystemExit(f"[FAIL] Expected a list in {tasks_back_path}")

    for t in back_tasks:
        if t.get("taskmaster_id") != int(TASK_ID):
            continue
        test_refs, changed = _ensure_test_ref_list(t.get("test_refs", []))
        if changed:
            t["test_refs"] = test_refs
            changes.append(
                Change(
                    file=str(tasks_back_path.relative_to(repo_root)).replace("\\", "/"),
                    action="update",
                    details={"taskmaster_id": int(TASK_ID), "field": "test_refs", "value": test_refs},
                )
            )

    # Update tasks_gameplay.json
    gameplay_tasks = _read_json(tasks_gameplay_path)
    if not isinstance(gameplay_tasks, list):
        raise SystemExit(f"[FAIL] Expected a list in {tasks_gameplay_path}")

    for t in gameplay_tasks:
        if t.get("taskmaster_id") != int(TASK_ID):
            continue
        test_refs, changed = _ensure_test_ref_list(t.get("test_refs", []))
        if changed:
            t["test_refs"] = test_refs
            changes.append(
                Change(
                    file=str(tasks_gameplay_path.relative_to(repo_root)).replace("\\", "/"),
                    action="update",
                    details={"taskmaster_id": int(TASK_ID), "field": "test_refs", "value": test_refs},
                )
            )

    # Persist only if changes exist
    if changes:
        _write_json(tasks_json_path, tasks_json)
        _write_json(tasks_back_path, back_tasks)
        _write_json(tasks_gameplay_path, gameplay_tasks)

    # Audit
    day = datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d")
    audit_dir = repo_root / "logs" / "ci" / day / "task-update"
    audit_dir.mkdir(parents=True, exist_ok=True)
    audit_path = audit_dir / "task3-test-refs-update.json"

    audit = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "task_id": TASK_ID,
        "test_ref": TEST_REF_PATH,
        "removed_test_ref": REMOVED_TEST_REF_PATH,
        "changes": [c.__dict__ for c in changes],
    }
    audit_path.write_text(json.dumps(audit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if changes:
        print(f"[OK] Updated Task {TASK_ID} test references ({len(changes)} file updates)")
        print(f"[OK] Audit: {audit_path}")
        return 0

    print(f"[OK] No changes needed (Task {TASK_ID} already references {TEST_REF_PATH})")
    print(f"[OK] Audit: {audit_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

