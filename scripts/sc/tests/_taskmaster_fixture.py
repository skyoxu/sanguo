#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import shutil
import time
import uuid
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

REPO_ROOT = Path(__file__).resolve().parents[3]
EXAMPLES_DIR = REPO_ROOT / "examples" / "taskmaster"
TASKMASTER_DIR = REPO_ROOT / ".taskmaster" / "tasks"
_LOCK_DIR = REPO_ROOT / ".taskmaster" / "tasks.__sc_tests_lock__"
_LOCK_OWNER = _LOCK_DIR / "owner.json"
_STAGED_SENTINEL = ".sc-tests-staged.json"


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


def _lock_payload() -> dict[str, str]:
    return {
        "pid": str(os.getpid()),
        "token": uuid.uuid4().hex,
    }


def _try_acquire_lock(payload: dict[str, str]) -> bool:
    try:
        _LOCK_DIR.mkdir(parents=True, exist_ok=False)
    except FileExistsError:
        return False
    _write_json(_LOCK_OWNER, payload)
    return True


def _wait_for_lock(timeout_sec: float = 60.0, poll_sec: float = 0.1) -> dict[str, str]:
    started = time.monotonic()
    payload = _lock_payload()
    while True:
        if _try_acquire_lock(payload):
            return payload
        _maybe_break_stale_lock()
        if time.monotonic() - started >= timeout_sec:
            raise TimeoutError(f"timed out acquiring taskmaster test fixture lock: {_LOCK_DIR}")
        time.sleep(poll_sec)


def _backup_dir_for(payload: dict[str, str]) -> Path:
    token = str(payload.get("token") or "").strip() or "unknown"
    pid = str(payload.get("pid") or "").strip() or "0"
    return REPO_ROOT / ".taskmaster" / f"tasks.__backup_for_sc_tests__.{pid}.{token}"


def _pid_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError:
        return False
    return True


def _lock_age_seconds() -> float:
    try:
        return max(0.0, time.time() - _LOCK_DIR.stat().st_mtime)
    except FileNotFoundError:
        return 0.0


def _maybe_break_stale_lock(min_age_sec: float = 2.0) -> None:
    if not _LOCK_DIR.exists():
        return

    age = _lock_age_seconds()
    if age < min_age_sec:
        return

    owner = None
    try:
        owner = _read_json(_LOCK_OWNER)
    except Exception:
        owner = None

    if not isinstance(owner, dict):
        _remove_tree_if_exists(_LOCK_DIR)
        return

    pid_raw = str(owner.get("pid") or "").strip()
    try:
        owner_pid = int(pid_raw)
    except ValueError:
        owner_pid = -1

    if not _pid_alive(owner_pid):
        _remove_tree_if_exists(_LOCK_DIR)


def _write_staged_sentinel(payload: dict[str, str]) -> None:
    _write_json(
        TASKMASTER_DIR / _STAGED_SENTINEL,
        {
            "owner": payload,
        },
    )


def _is_owned_staging_dir(payload: dict[str, str]) -> bool:
    sentinel = TASKMASTER_DIR / _STAGED_SENTINEL
    if not sentinel.exists():
        return False
    try:
        data = _read_json(sentinel)
    except Exception:
        return False
    owner = data.get("owner") if isinstance(data, dict) else None
    if not isinstance(owner, dict):
        return False
    return owner == payload


@contextmanager
def staged_taskmaster_triplet(*, include_task1: bool = False) -> Iterator[Path]:
    lock_payload = _wait_for_lock()
    backup_dir = _backup_dir_for(lock_payload)
    _remove_tree_if_exists(backup_dir)
    if TASKMASTER_DIR.exists():
        backup_dir.parent.mkdir(parents=True, exist_ok=True)
        try:
            TASKMASTER_DIR.rename(backup_dir)
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
        _write_staged_sentinel(lock_payload)
        yield TASKMASTER_DIR
    finally:
        try:
            if _is_owned_staging_dir(lock_payload):
                _remove_tree_if_exists(TASKMASTER_DIR)
            if backup_dir.exists():
                backup_dir.rename(TASKMASTER_DIR)
        finally:
            _remove_tree_if_exists(_LOCK_DIR)
