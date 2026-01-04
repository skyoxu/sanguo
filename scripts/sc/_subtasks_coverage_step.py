#!/usr/bin/env python3
"""
Acceptance check step: LLM-backed subtasks coverage.

Semantically checks whether tasks.json subtasks are covered by >= 1 acceptance item
across the available task views (tasks_back/tasks_gameplay).

This uses `codex exec` via scripts/sc/llm_check_subtasks_coverage.py.
"""

from __future__ import annotations

from pathlib import Path

from _step_result import StepResult
from _taskmaster import TaskmasterTriplet
from _util import repo_root, run_cmd, write_json, write_text


def step_subtasks_coverage_llm(out_dir: Path, triplet: TaskmasterTriplet, *, timeout_sec: int) -> StepResult:
    subtasks = triplet.master.get("subtasks") or []
    if not isinstance(subtasks, list) or not subtasks:
        details = {"task_id": triplet.task_id, "reason": "no_subtasks"}
        write_json(out_dir / "subtasks-coverage.json", details)
        return StepResult(name="subtasks-coverage", status="skipped", rc=0, details=details)

    cmd = [
        "py",
        "-3",
        "scripts/sc/llm_check_subtasks_coverage.py",
        "--task-id",
        str(triplet.task_id),
        "--timeout-sec",
        str(int(timeout_sec)),
    ]
    rc, out = run_cmd(cmd, cwd=repo_root(), timeout_sec=max(30, int(timeout_sec) + 30))
    log_path = out_dir / "subtasks-coverage.log"
    write_text(log_path, out)

    details = {
        "task_id": triplet.task_id,
        "timeout_sec": int(timeout_sec),
        "note": "This step uses codex exec (LLM) to semantically check: each tasks.json subtask is covered by >=1 acceptance item in tasks_back/tasks_gameplay.",
    }
    write_json(out_dir / "subtasks-coverage.json", details)
    return StepResult(name="subtasks-coverage", status="ok" if rc == 0 else "fail", rc=rc, cmd=cmd, log=str(log_path), details=details)

