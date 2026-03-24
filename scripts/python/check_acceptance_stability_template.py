#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Soft gate for acceptance stability template markers.

Purpose:
- Provide a deterministic, non-LLM check for high-drift tasks.
- Ensure acceptance criteria include required machine-auditable markers.

Default scope:
- task files:
  .taskmaster/tasks/tasks_back.json
  .taskmaster/tasks/tasks_gameplay.json
- target config:
  scripts/python/config/acceptance-stability-targets.json

Output:
- logs/ci/<YYYY-MM-DD>/acceptance-stability-template/summary.json
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from pathlib import Path
from typing import Any


DEFAULT_TASK_FILES = [
    ".taskmaster/tasks/tasks_back.json",
    ".taskmaster/tasks/tasks_gameplay.json",
]
DEFAULT_TARGETS_FILE = "scripts/python/config/acceptance-stability-targets.json"
DEFAULT_REQUIRED_MARKERS = [
    "`adr_refs=",
    "`chapter_refs=",
    "`test_refs`",
    "`executed=false`",
    "fail-closed",
]


def _today() -> str:
    return dt.date.today().strftime("%Y-%m-%d")


def _posix(path: Path) -> str:
    return str(path).replace("\\", "/")


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_targets(path: Path) -> tuple[set[int], list[str]]:
    if not path.exists():
        raise FileNotFoundError(f"targets file not found: {_posix(path)}")

    payload = _read_json(path)
    if not isinstance(payload, dict):
        raise ValueError("targets file must be a JSON object")

    ids_raw = payload.get("taskmaster_ids")
    if not isinstance(ids_raw, list):
        raise ValueError("taskmaster_ids must be an array")

    task_ids: set[int] = set()
    for item in ids_raw:
        task_ids.add(int(item))

    markers_raw = payload.get("required_markers", DEFAULT_REQUIRED_MARKERS)
    if not isinstance(markers_raw, list) or not all(isinstance(x, str) for x in markers_raw):
        raise ValueError("required_markers must be an array of strings")

    markers = [str(x) for x in markers_raw if str(x).strip()]
    if not markers:
        raise ValueError("required_markers must not be empty")

    return task_ids, markers


def _validate_file(path: Path, target_ids: set[int], required_markers: list[str]) -> dict[str, Any]:
    payload = _read_json(path)
    if not isinstance(payload, list):
        raise ValueError(f"task file must be a JSON array: {_posix(path)}")

    scanned = 0
    matched = 0
    found_task_ids: set[int] = set()
    violations: list[dict[str, Any]] = []

    for task in payload:
        scanned += 1
        taskmaster_id = task.get("taskmaster_id")
        if taskmaster_id is None:
            continue
        try:
            taskmaster_id_int = int(taskmaster_id)
        except Exception:
            continue
        if taskmaster_id_int not in target_ids:
            continue

        matched += 1
        found_task_ids.add(taskmaster_id_int)
        task_id = str(task.get("id") or "")
        acceptance = task.get("acceptance")

        if not isinstance(acceptance, list):
            violations.append(
                {
                    "taskmaster_id": taskmaster_id_int,
                    "task_id": task_id,
                    "rule": "acceptance_not_array",
                    "message": "acceptance must be a JSON array",
                }
            )
            continue

        acceptance_lines = [str(x) for x in acceptance]
        for marker in required_markers:
            if any(marker in line for line in acceptance_lines):
                continue
            violations.append(
                {
                    "taskmaster_id": taskmaster_id_int,
                    "task_id": task_id,
                    "rule": "missing_required_marker",
                    "marker": marker,
                    "message": f"missing acceptance marker: {marker}",
                }
            )

    return {
        "path": _posix(path),
        "scanned": scanned,
        "matched": matched,
        "found_task_ids": sorted(found_task_ids),
        "violations": violations,
        "failed": len(violations),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Soft gate for acceptance stability template markers")
    parser.add_argument(
        "--task-files",
        nargs="*",
        default=DEFAULT_TASK_FILES,
        help="Task view files to scan",
    )
    parser.add_argument(
        "--targets-file",
        default=DEFAULT_TARGETS_FILE,
        help="JSON config with taskmaster_ids and required_markers",
    )
    parser.add_argument("--out", default="", help="Optional output summary path")
    args = parser.parse_args()

    repo_root = Path.cwd().resolve()
    targets_path = (repo_root / args.targets_file).resolve()

    try:
        target_ids, required_markers = _load_targets(targets_path)
    except Exception as exc:  # noqa: BLE001
        print(f"ACCEPTANCE_STABILITY_TEMPLATE status=fail reason=invalid_targets msg={exc}")
        return 1

    if not target_ids:
        if args.out:
            out_path = Path(args.out)
        else:
            out_path = Path("logs") / "ci" / _today() / "acceptance-stability-template" / "summary.json"
        out_path.parent.mkdir(parents=True, exist_ok=True)
        summary = {
            "ts": dt.datetime.now(dt.timezone.utc).isoformat(),
            "action": "acceptance-stability-template",
            "status": "skipped",
            "reason": "no_targets_configured",
            "targets_file": _posix(targets_path),
            "task_files": [_posix(Path(x)) for x in args.task_files],
            "target_taskmaster_ids": [],
            "required_markers": required_markers,
            "total_scanned": 0,
            "total_matched": 0,
            "total_failed": 0,
            "missing_targets": [],
            "target_coverage_violations": [],
            "results": [],
        }
        out_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"ACCEPTANCE_STABILITY_TEMPLATE status=skipped reason=no_targets_configured out={_posix(out_path)}")
        return 0

    file_results: list[dict[str, Any]] = []
    total_failed = 0
    total_scanned = 0
    total_matched = 0
    found_all: set[int] = set()

    for rel in args.task_files:
        full_path = (repo_root / rel).resolve()
        if not full_path.exists():
            total_failed += 1
            file_results.append(
                {
                    "path": _posix(Path(rel)),
                    "scanned": 0,
                    "matched": 0,
                    "found_task_ids": [],
                    "failed": 1,
                    "violations": [
                        {
                            "taskmaster_id": None,
                            "task_id": "",
                            "rule": "task_file_missing",
                            "message": f"task file not found: {_posix(Path(rel))}",
                        }
                    ],
                }
            )
            continue

        try:
            result = _validate_file(full_path, target_ids, required_markers)
        except Exception as exc:  # noqa: BLE001
            total_failed += 1
            file_results.append(
                {
                    "path": _posix(full_path),
                    "scanned": 0,
                    "matched": 0,
                    "found_task_ids": [],
                    "failed": 1,
                    "violations": [
                        {
                            "taskmaster_id": None,
                            "task_id": "",
                            "rule": "task_file_parse_error",
                            "message": str(exc),
                        }
                    ],
                }
            )
            continue

        file_results.append(result)
        total_failed += int(result["failed"])
        total_scanned += int(result["scanned"])
        total_matched += int(result["matched"])
        found_all.update(int(x) for x in result["found_task_ids"])

    missing_targets = sorted(target_ids - found_all)
    target_coverage_violations: list[dict[str, Any]] = []
    for taskmaster_id in missing_targets:
        target_coverage_violations.append(
            {
                "taskmaster_id": taskmaster_id,
                "task_id": "",
                "rule": "target_task_not_found",
                "message": "target taskmaster_id not found in any provided task file",
            }
        )

    total_failed += len(target_coverage_violations)

    summary = {
        "ts": dt.datetime.now(dt.timezone.utc).isoformat(),
        "action": "acceptance-stability-template",
        "status": "ok" if total_failed == 0 else "fail",
        "targets_file": _posix(targets_path),
        "task_files": [_posix(Path(x)) for x in args.task_files],
        "target_taskmaster_ids": sorted(target_ids),
        "required_markers": required_markers,
        "total_scanned": total_scanned,
        "total_matched": total_matched,
        "total_failed": total_failed,
        "missing_targets": missing_targets,
        "target_coverage_violations": target_coverage_violations,
        "results": file_results,
    }

    if args.out:
        out_path = Path(args.out)
    else:
        out_path = Path("logs") / "ci" / _today() / "acceptance-stability-template" / "summary.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    status = summary["status"]
    print(
        f"ACCEPTANCE_STABILITY_TEMPLATE status={status} "
        f"matched={total_matched} failed={total_failed} out={_posix(out_path)}"
    )

    if total_failed:
        for entry in target_coverage_violations:
            print(f" - rule={entry['rule']} taskmaster_id={entry['taskmaster_id']} msg={entry['message']}")
        for file_result in file_results:
            for violation in file_result.get("violations", [])[:50]:
                print(
                    f" - file={file_result.get('path')} taskmaster_id={violation.get('taskmaster_id')} "
                    f"task_id={violation.get('task_id')} rule={violation.get('rule')} "
                    f"marker={violation.get('marker', '')} msg={violation.get('message')}"
                )

    return 0 if total_failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
