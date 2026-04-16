#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Hard gate for signal-compliance workflow wiring.

Rules:
1) Track signal workflow tasks (T157/T162/T163) from task views.
2) Only active tasks (done/in-progress) are enforced.
3) For each active task, require:
   - logs/ci/signal-compliance/T<id>/signal-compliance-report.json exists
   - report contains task identity
   - report contains at least one evidence path
   - report declares compliant=true

Output:
  logs/ci/<YYYY-MM-DD>/signal-compliance-workflow-hard-gate/summary.json
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
SIGNAL_WORKFLOW_TASK_IDS = {157, 162, 163}
ACTIVE_STATUSES = {"done", "in_progress", "in-progress", "completed", "complete"}
GATE_NAME = "signal_compliance_workflow_hard_gate"


def _today() -> str:
    return dt.date.today().strftime("%Y-%m-%d")


def _posix(path: Path) -> str:
    return str(path).replace("\\", "/")


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _normalize_status(raw: Any) -> str:
    return str(raw or "").strip().lower().replace(" ", "_")


def _to_int(value: Any) -> int | None:
    try:
        return int(str(value).strip())
    except Exception:
        return None


def _pick(payload: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        if key in payload:
            return payload[key]
    return None


def _coerce_bool(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"true", "1", "yes"}:
            return True
        if lowered in {"false", "0", "no"}:
            return False
    if isinstance(value, (int, float)):
        if value == 1:
            return True
        if value == 0:
            return False
    return None


def _collect_active_tasks(repo_root: Path, task_files: list[Path]) -> dict[int, dict[str, Any]]:
    active: dict[int, dict[str, Any]] = {}
    for task_file in task_files:
        full_path = task_file if task_file.is_absolute() else (repo_root / task_file)
        if not full_path.exists():
            continue
        payload = _read_json(full_path)
        if not isinstance(payload, list):
            continue
        for task in payload:
            if not isinstance(task, dict):
                continue
            task_id = _to_int(task.get("taskmaster_id"))
            if task_id is None or task_id not in SIGNAL_WORKFLOW_TASK_IDS:
                continue
            status = _normalize_status(task.get("status"))
            if status not in ACTIVE_STATUSES:
                continue
            existing = active.get(task_id)
            file_label = _posix(full_path.relative_to(repo_root)) if full_path.is_relative_to(repo_root) else _posix(full_path)
            if existing is None:
                active[task_id] = {
                    "status": status,
                    "task_refs": [file_label],
                }
            else:
                refs = set(existing.get("task_refs") or [])
                refs.add(file_label)
                existing["task_refs"] = sorted(refs)
    return active


def _normalize_evidence_paths(payload: dict[str, Any]) -> list[str]:
    one = _pick(payload, "evidence_path", "evidencePath", "EvidencePath")
    many = _pick(payload, "evidence_paths", "evidencePaths", "EvidencePaths")

    paths: list[str] = []
    if isinstance(one, str) and one.strip():
        paths.append(one.strip())
    if isinstance(many, list):
        paths.extend(str(item).strip() for item in many if str(item).strip())
    return sorted(set(paths))


def run_gate(*, repo_root: Path, task_files: list[Path], reports_root: Path) -> dict[str, Any]:
    active_tasks = _collect_active_tasks(repo_root, task_files)
    task_ids = sorted(active_tasks.keys())

    findings: list[dict[str, Any]] = []
    failed = 0

    for task_id in task_ids:
        report_path = reports_root / f"T{task_id}" / "signal-compliance-report.json"
        evidence_path = _posix(report_path.relative_to(repo_root)) if report_path.is_relative_to(repo_root) else _posix(report_path)
        base = {
            "assertion_id": "R11-PH9-B4-signal-compliance-workflow",
            "task_id": f"T{task_id}",
            "gate_name": GATE_NAME,
            "evidence_path": evidence_path,
        }

        if not report_path.exists():
            failed += 1
            findings.append(
                {
                    **base,
                    "status": "fail",
                    "reason": "report_missing",
                }
            )
            continue

        try:
            payload = _read_json(report_path)
        except Exception as exc:
            failed += 1
            findings.append(
                {
                    **base,
                    "status": "fail",
                    "reason": "report_parse_error",
                    "message": str(exc),
                }
            )
            continue

        if not isinstance(payload, dict):
            failed += 1
            findings.append(
                {
                    **base,
                    "status": "fail",
                    "reason": "report_not_object",
                }
            )
            continue

        report_task = str(_pick(payload, "task_id", "taskId", "TaskId") or "").strip()
        accepted_task_tokens = {str(task_id), f"T{task_id}"}
        if report_task not in accepted_task_tokens:
            failed += 1
            findings.append(
                {
                    **base,
                    "status": "fail",
                    "reason": "task_id_mismatch",
                    "report_task_id": report_task,
                }
            )
            continue

        evidence_paths = _normalize_evidence_paths(payload)
        if not evidence_paths:
            failed += 1
            findings.append(
                {
                    **base,
                    "status": "fail",
                    "reason": "missing_evidence_path",
                }
            )
            continue

        is_compliant = _coerce_bool(_pick(payload, "is_compliant", "isCompliant", "IsCompliant"))
        if is_compliant is None:
            failed += 1
            findings.append(
                {
                    **base,
                    "status": "fail",
                    "reason": "missing_is_compliant",
                }
            )
            continue

        if not is_compliant:
            failed += 1
            findings.append(
                {
                    **base,
                    "status": "fail",
                    "reason": "non_compliant",
                    "evidence_paths": evidence_paths,
                }
            )
            continue

        findings.append(
            {
                **base,
                "status": "ok",
                "reason": "compliant",
                "evidence_paths": evidence_paths,
            }
        )

    return {
        "ts": dt.datetime.now(dt.timezone.utc).isoformat(),
        "action": "signal-compliance-workflow-hard-gate",
        "gate_name": GATE_NAME,
        "status": "ok" if failed == 0 else "fail",
        "reason": "no_active_signal_tasks" if not task_ids else ("all_compliant" if failed == 0 else "signal_compliance_gate_failed"),
        "active_task_ids": [f"T{task_id}" for task_id in task_ids],
        "active_task_meta": {f"T{task_id}": active_tasks[task_id] for task_id in task_ids},
        "checked": len(findings),
        "failed": failed,
        "results": findings,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Hard gate: signal compliance workflow wiring and evidence.")
    parser.add_argument(
        "--task-files",
        nargs="*",
        default=DEFAULT_TASK_FILES,
        help="Task view files used to discover active signal workflow tasks.",
    )
    parser.add_argument(
        "--reports-root",
        default="logs/ci/signal-compliance",
        help="Root directory that stores signal compliance reports by task.",
    )
    parser.add_argument("--out", default="", help="Optional output summary path.")
    args = parser.parse_args()

    repo_root = Path.cwd().resolve()
    task_files = [Path(item) for item in args.task_files]
    reports_root = Path(args.reports_root)
    if not reports_root.is_absolute():
        reports_root = (repo_root / reports_root).resolve()

    summary = run_gate(repo_root=repo_root, task_files=task_files, reports_root=reports_root)

    if args.out:
        out_path = Path(args.out)
        if not out_path.is_absolute():
            out_path = (repo_root / out_path).resolve()
    else:
        out_path = repo_root / "logs" / "ci" / _today() / "signal-compliance-workflow-hard-gate" / "summary.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(
        "SIGNAL_COMPLIANCE_WORKFLOW_HARD_GATE "
        f"status={summary['status']} active_tasks={len(summary.get('active_task_ids') or [])} "
        f"checked={summary.get('checked', 0)} failed={summary.get('failed', 0)} "
        f"reason={summary.get('reason', '')} out={_posix(out_path)}"
    )
    if summary.get("failed", 0):
        for item in (summary.get("results") or [])[:20]:
            if str(item.get("status")) != "fail":
                continue
            print(
                " - "
                f"task={item.get('task_id')} reason={item.get('reason')} "
                f"evidence={item.get('evidence_path')}"
            )
    return 0 if summary["status"] == "ok" else 1


if __name__ == "__main__":
    sys.exit(main())
