#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Hard gate for task view contractRefs consistency.

Rules:
1) contractRefs entries must exist in Game.Core/Contracts event constants.
2) UI-consumer tasks must have non-empty contractRefs.
3) Core-computation tasks must have non-empty contractRefs.
4) Same taskmaster_id across task views must have identical contractRefs,
   unless an explicit override is configured in whitelist.

Default target files:
  - .taskmaster/tasks/tasks_back.json
  - .taskmaster/tasks/tasks_gameplay.json

Output:
  logs/ci/<YYYY-MM-DD>/task-contract-refs-gate/summary.json

Whitelist format (optional):
  .taskmaster/docs/contractrefs-consistency-whitelist.json
  {
    "overrides": [
      {
        "taskmaster_id": 123,
        "files": {
          ".taskmaster/tasks/tasks_back.json": ["core.a", "core.b"],
          ".taskmaster/tasks/tasks_gameplay.json": ["core.a"]
        }
      }
    ]
  }
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
from pathlib import Path
from typing import Any


DEFAULT_TASK_FILES = [
    Path(".taskmaster/tasks/tasks_back.json"),
    Path(".taskmaster/tasks/tasks_gameplay.json"),
]

DEFAULT_CONSISTENCY_WHITELIST = Path(".taskmaster/docs/contractrefs-consistency-whitelist.json")

EVENT_TYPES_FILE = Path("Game.Core/Contracts/EventTypes.cs")
EVENT_CONST_RE = re.compile(r'public\s+const\s+string\s+\w+\s*=\s*"([a-z0-9._-]+)"\s*;')


def _today_str() -> str:
    return dt.date.today().strftime("%Y-%m-%d")


def _posix(path: Path) -> str:
    return str(path).replace("\\", "/")


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_allowed_events(repo_root: Path) -> set[str]:
    full_path = repo_root / EVENT_TYPES_FILE
    if not full_path.exists():
        raise FileNotFoundError(f"Missing event constants file: {_posix(EVENT_TYPES_FILE)}")

    text = full_path.read_text(encoding="utf-8")
    events = set(EVENT_CONST_RE.findall(text))
    if not events:
        raise ValueError(f"No event constants found in {_posix(EVENT_TYPES_FILE)}")
    return events


def _normalize_refs(refs: list[Any] | None) -> list[str]:
    if refs is None:
        return []
    normalized = sorted({str(item) for item in refs})
    return normalized


def _normalize_task_file_key(path: Path, repo_root: Path) -> str:
    try:
        rel = path.resolve().relative_to(repo_root)
        return _posix(rel)
    except Exception:
        return _posix(path)


def _load_consistency_overrides(repo_root: Path, whitelist_path: Path) -> dict[int, dict[str, list[str]]]:
    full_path = whitelist_path if whitelist_path.is_absolute() else (repo_root / whitelist_path)
    if not full_path.exists():
        return {}

    payload = _read_json(full_path)
    if not isinstance(payload, dict):
        raise ValueError(f"Whitelist must be an object: {_posix(whitelist_path)}")

    overrides_raw = payload.get("overrides", [])
    if not isinstance(overrides_raw, list):
        raise ValueError(f"Whitelist field overrides must be an array: {_posix(whitelist_path)}")

    overrides: dict[int, dict[str, list[str]]] = {}
    for idx, item in enumerate(overrides_raw):
        if not isinstance(item, dict):
            raise ValueError(f"Whitelist override item must be object at index {idx}: {_posix(whitelist_path)}")

        taskmaster_id = item.get("taskmaster_id")
        try:
            taskmaster_id_int = int(taskmaster_id)
        except Exception as exc:
            raise ValueError(
                f"Whitelist override taskmaster_id must be integer at index {idx}: {_posix(whitelist_path)}"
            ) from exc

        files = item.get("files")
        if not isinstance(files, dict):
            raise ValueError(f"Whitelist override files must be object at index {idx}: {_posix(whitelist_path)}")

        normalized_files: dict[str, list[str]] = {}
        for file_key, refs in files.items():
            if not isinstance(file_key, str):
                raise ValueError(
                    f"Whitelist override file key must be string at index {idx}: {_posix(whitelist_path)}"
                )
            if not isinstance(refs, list):
                raise ValueError(
                    f"Whitelist override refs must be array for file {file_key} at index {idx}: {_posix(whitelist_path)}"
                )
            normalized_files[_posix(Path(file_key))] = _normalize_refs(refs)

        overrides[taskmaster_id_int] = normalized_files

    return overrides


def _is_ui_task(task: dict[str, Any]) -> bool:
    title = str(task.get("title", "")).lower()
    labels = {str(x).lower() for x in task.get("labels", [])}
    if "ui" not in labels:
        return False

    # Only UI tasks that are likely to subscribe/consume runtime domain events.
    ui_keywords = ("scene", "menu", "hud", "display", "reward", "shop", "rest", "event")
    return any(keyword in title for keyword in ui_keywords)


def _is_core_compute_task(task: dict[str, Any]) -> bool:
    # Restrict to explicit core-layer computation tasks to avoid false positives.
    return str(task.get("layer", "")).lower() == "core"


def _validate_task_file(path: Path, allowed_events: set[str]) -> dict[str, Any]:
    data = _read_json(path)
    if not isinstance(data, list):
        raise ValueError(f"Task view file must be a JSON array: {_posix(path)}")

    violations: list[dict[str, Any]] = []
    scanned = 0

    for task in data:
        scanned += 1
        task_id = str(task.get("id", ""))
        refs = task.get("contractRefs")

        if refs is None:
            refs = []
        if not isinstance(refs, list):
            violations.append(
                {
                    "task_id": task_id,
                    "rule": "contractRefs_type",
                    "message": "contractRefs must be an array",
                }
            )
            continue

        invalid = [x for x in refs if str(x) not in allowed_events]
        if invalid:
            violations.append(
                {
                    "task_id": task_id,
                    "rule": "contractRefs_unknown_event",
                    "message": f"unknown contractRefs events: {invalid}",
                }
            )

        if _is_ui_task(task) and len(refs) == 0:
            violations.append(
                {
                    "task_id": task_id,
                    "rule": "ui_task_missing_contractRefs",
                    "message": "UI consumer task must define non-empty contractRefs",
                }
            )

        if _is_core_compute_task(task) and len(refs) == 0:
            violations.append(
                {
                    "task_id": task_id,
                    "rule": "core_task_missing_contractRefs",
                    "message": "Core computation task must define non-empty contractRefs",
                }
            )

    return {
        "path": _posix(path),
        "scanned": scanned,
        "violations": violations,
        "failed": len(violations),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Hard gate for task view contractRefs")
    parser.add_argument(
        "--task-files",
        nargs="*",
        default=[_posix(x) for x in DEFAULT_TASK_FILES],
        help="Task view json files to validate",
    )
    parser.add_argument(
        "--consistency-whitelist",
        default=_posix(DEFAULT_CONSISTENCY_WHITELIST),
        help="Optional whitelist json for controlled taskmaster_id cross-view contractRefs differences",
    )
    parser.add_argument("--out", default="", help="Optional output summary path")
    args = parser.parse_args()

    repo_root = Path.cwd().resolve()
    allowed_events = _load_allowed_events(repo_root)
    consistency_overrides = _load_consistency_overrides(repo_root, Path(args.consistency_whitelist))

    results: list[dict[str, Any]] = []
    total_failed = 0
    total_scanned = 0
    consistency_violations: list[dict[str, Any]] = []
    grouped_by_taskmaster: dict[int, list[dict[str, Any]]] = {}

    for rel in args.task_files:
        path = (repo_root / rel).resolve()
        if not path.exists():
            total_failed += 1
            results.append(
                {
                    "path": _posix(Path(rel)),
                    "scanned": 0,
                    "failed": 1,
                    "violations": [
                        {
                            "task_id": "-",
                            "rule": "task_file_missing",
                            "message": f"file not found: {_posix(Path(rel))}",
                        }
                    ],
                }
            )
            continue

        file_result = _validate_task_file(path, allowed_events)
        results.append(file_result)
        total_failed += file_result["failed"]
        total_scanned += file_result["scanned"]

        # collect per-taskmaster refs for cross-view consistency validation
        data = _read_json(path)
        file_key = _normalize_task_file_key(path, repo_root)
        for task in data:
            taskmaster_id = task.get("taskmaster_id")
            if taskmaster_id is None:
                continue
            try:
                taskmaster_id_int = int(taskmaster_id)
            except Exception:
                continue

            grouped_by_taskmaster.setdefault(taskmaster_id_int, []).append(
                {
                    "file": file_key,
                    "task_id": str(task.get("id", "")),
                    "refs": _normalize_refs(task.get("contractRefs")),
                }
            )

    for taskmaster_id, entries in grouped_by_taskmaster.items():
        if len(entries) <= 1:
            continue

        entries_sorted = sorted(entries, key=lambda item: (item["file"], item["task_id"]))
        override = consistency_overrides.get(taskmaster_id)

        if override is not None:
            for entry in entries_sorted:
                file_key = entry["file"]
                expected = override.get(file_key)
                if expected is None:
                    consistency_violations.append(
                        {
                            "taskmaster_id": taskmaster_id,
                            "task_id": entry["task_id"],
                            "file": file_key,
                            "rule": "taskmaster_contractrefs_consistency_override_missing_file",
                            "message": (
                                "override exists for taskmaster_id but current file missing in whitelist files mapping"
                            ),
                        }
                    )
                    continue

                if entry["refs"] != expected:
                    consistency_violations.append(
                        {
                            "taskmaster_id": taskmaster_id,
                            "task_id": entry["task_id"],
                            "file": file_key,
                            "rule": "taskmaster_contractrefs_consistency_override_mismatch",
                            "message": (
                                f"contractRefs mismatch with whitelist override. expected={expected} actual={entry['refs']}"
                            ),
                        }
                    )
            continue

        baseline = entries_sorted[0]
        baseline_refs = baseline["refs"]
        for entry in entries_sorted[1:]:
            if entry["refs"] == baseline_refs:
                continue

            missing = sorted(set(baseline_refs) - set(entry["refs"]))
            extra = sorted(set(entry["refs"]) - set(baseline_refs))
            consistency_violations.append(
                {
                    "taskmaster_id": taskmaster_id,
                    "task_id": entry["task_id"],
                    "file": entry["file"],
                    "baseline_file": baseline["file"],
                    "baseline_task_id": baseline["task_id"],
                    "rule": "taskmaster_contractrefs_consistency",
                    "message": (
                        f"contractRefs differ across views for same taskmaster_id; missing={missing} extra={extra}"
                    ),
                }
            )

    total_failed += len(consistency_violations)

    out_default = Path("logs") / "ci" / _today_str() / "task-contract-refs-gate" / "summary.json"
    out_path = Path(args.out) if args.out else out_default
    out_path.parent.mkdir(parents=True, exist_ok=True)

    summary = {
        "ts": dt.datetime.now(dt.timezone.utc).isoformat(),
        "action": "task-contract-refs-gate",
        "reason": "enforce minimal event coverage for UI consumers and core publishers",
        "allowed_events_file": _posix(EVENT_TYPES_FILE),
        "allowed_events_count": len(allowed_events),
        "allowed_events": sorted(allowed_events),
        "consistency_whitelist": _posix(Path(args.consistency_whitelist)),
        "consistency_overrides_count": len(consistency_overrides),
        "consistency_violations_count": len(consistency_violations),
        "consistency_violations": consistency_violations,
        "total_scanned": total_scanned,
        "total_failed": total_failed,
        "results": results,
    }

    out_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    status = "ok" if total_failed == 0 else "fail"
    print(
        f"TASK_CONTRACT_REFS_GATE status={status} scanned={total_scanned} "
        f"failed={total_failed} out={_posix(out_path)}"
    )
    if total_failed:
        for file_result in results:
            for violation in file_result.get("violations", [])[:20]:
                print(
                    f" - file={file_result.get('path')} task={violation.get('task_id')} "
                    f"rule={violation.get('rule')} msg={violation.get('message')}"
                )

    return 0 if total_failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
