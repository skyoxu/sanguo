#!/usr/bin/env python3
from __future__ import annotations

import json
import shutil
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

REPO_ROOT = Path(__file__).resolve().parents[3]
EXAMPLES_DIR = REPO_ROOT / "examples" / "taskmaster"
TASKMASTER_DIR = REPO_ROOT / ".taskmaster" / "tasks"
_BACKUP_DIR = REPO_ROOT / ".taskmaster" / "tasks.__backup_for_sc_tests__"


def _read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def _example_triplet() -> tuple[dict, list, list]:
    return (
        _read_json(EXAMPLES_DIR / "tasks.json"),
        _read_json(EXAMPLES_DIR / "tasks_back.json"),
        _read_json(EXAMPLES_DIR / "tasks_gameplay.json"),
    )


def _inject_task1(tasks_json: dict, tasks_back: list, tasks_gameplay: list) -> None:
    master = (tasks_json.get("master") or {}).get("tasks") or []
    if not any(str(t.get("id")) == "1" for t in master if isinstance(t, dict)):
        master.insert(0, {
            "id": 1,
            "title": "Template Task1 evidence gate demo",
            "status": "in-progress",
            "adrRefs": ["ADR-0031", "ADR-0011"],
            "archRefs": ["CH07"],
            "overlay": "docs/architecture/overlays/PRD-Guild-Manager/08/ACCEPTANCE_CHECKLIST.md",
        })
    if not any(isinstance(t, dict) and t.get("taskmaster_id") == 1 for t in tasks_back):
        tasks_back.insert(0, {
            "id": "T1-back",
            "taskmaster_id": 1,
            "acceptance": [
                "ACC:T1.1 template headless evidence. Refs: Tests.Godot/tests/Adapters/Config/test_settings_config_utf8.gd"
            ],
            "test_refs": [
                "Game.Core.Tests/Tasks/Task1EnvironmentEvidencePersistenceTests.cs",
                "Game.Core.Tests/Tasks/Task1WindowsPlatformGateTests.cs",
                "Game.Core.Tests/Tasks/Task1ToolchainVersionChecksTests.cs",
                "Tests.Godot/tests/Adapters/Config/test_settings_config_utf8.gd",
            ],
        })
    if not any(isinstance(t, dict) and t.get("taskmaster_id") == 1 for t in tasks_gameplay):
        tasks_gameplay.insert(0, {
            "id": "T1-gameplay",
            "taskmaster_id": 1,
            "acceptance": [
                "ACC:T1.2 template gd ref. Refs: Tests.Godot/tests/Adapters/Config/test_settings_config_utf8.gd"
            ],
            "test_refs": ["Tests.Godot/tests/Adapters/Config/test_settings_config_utf8.gd"],
        })


def _remove_tree_if_exists(path: Path) -> None:
    if not path.exists():
        return
    if path.is_dir():
        shutil.rmtree(path)
        return
    path.unlink()


@contextmanager
def staged_taskmaster_triplet(*, include_task1: bool = False) -> Iterator[Path]:
    _remove_tree_if_exists(_BACKUP_DIR)
    if TASKMASTER_DIR.exists():
        _BACKUP_DIR.parent.mkdir(parents=True, exist_ok=True)
        try:
            TASKMASTER_DIR.rename(_BACKUP_DIR)
        except FileNotFoundError:
            pass
    TASKMASTER_DIR.mkdir(parents=True, exist_ok=True)
    try:
        tasks_json, tasks_back, tasks_gameplay = _example_triplet()
        if include_task1:
            _inject_task1(tasks_json, tasks_back, tasks_gameplay)
        _write_json(TASKMASTER_DIR / "tasks.json", tasks_json)
        _write_json(TASKMASTER_DIR / "tasks_back.json", tasks_back)
        _write_json(TASKMASTER_DIR / "tasks_gameplay.json", tasks_gameplay)
        yield TASKMASTER_DIR
    finally:
        _remove_tree_if_exists(TASKMASTER_DIR)
        if _BACKUP_DIR.exists():
            _BACKUP_DIR.rename(TASKMASTER_DIR)
