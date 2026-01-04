#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
sc-backfill-task-test-refs

Multi-step backfill for tasks_back.json/tasks_gameplay.json:
  1) Validate acceptance "Refs:" (syntax-level, stage=red).
  2) Ensure task-level test_refs includes all acceptance Refs (deterministic sync).
  3) If the master task status is in a configured set (default: done,in-progress),
     generate missing referenced test files via LLM (Codex CLI).
  4) For generated tasks, validate acceptance refs at refactor stage (file exists + in test_refs).

This script updates tasks_back/tasks_gameplay in-place only when --write is provided.
All logs/artifacts are written under logs/ci/<YYYY-MM-DD>/sc-backfill-test-refs/.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


def _bootstrap_imports() -> None:
    sys.path.insert(0, str(Path(__file__).resolve().parent))


_bootstrap_imports()

from _taskmaster import default_paths, iter_master_tasks, load_json  # noqa: E402
from _util import ci_dir, repo_root, run_cmd, split_csv, write_json, write_text  # noqa: E402


@dataclass(frozen=True)
class StepResult:
    name: str
    status: str  # ok|fail|skipped
    rc: int
    cmd: list[str]
    log: str


def _write_step_log(out_dir: Path, name: str, text: str) -> str:
    p = out_dir / f"{name}.log"
    write_text(p, text)
    return str(p)


def _run_step(out_dir: Path, name: str, cmd: list[str], timeout_sec: int) -> StepResult:
    rc, out = run_cmd(cmd, cwd=repo_root(), timeout_sec=timeout_sec)
    log = _write_step_log(out_dir, name, out)
    status = "ok" if rc == 0 else "fail"
    return StepResult(name=name, status=status, rc=rc, cmd=cmd, log=log)


def _task_ids_by_status(tasks_json: dict[str, Any], statuses: set[str]) -> list[str]:
    ids: list[str] = []
    for t in iter_master_tasks(tasks_json):
        st = str(t.get("status") or "").strip().lower()
        if st in statuses:
            ids.append(str(t.get("id")))
    return ids


def main() -> int:
    ap = argparse.ArgumentParser(description="Backfill test_refs and generate missing tests from acceptance Refs.")
    ap.add_argument(
        "--statuses",
        default="done,in-progress",
        help="Master task statuses eligible for test generation (CSV). Default: done,in-progress",
    )
    ap.add_argument("--all-tasks", action="store_true", help="Process all master tasks (still only generates for --statuses).")
    ap.add_argument("--task-id", default=None, help="Process a single task id.")
    ap.add_argument("--write", action="store_true", help="Write metadata changes (sync test_refs).")
    ap.add_argument("--timeout-sec", type=int, default=600, help="LLM per-file timeout passed to generator (seconds).")
    ap.add_argument("--verify", choices=["none", "unit", "all", "auto"], default="none", help="Verification mode for generated tests.")
    ap.add_argument("--godot-bin", default=None, help="Required when verify=all/auto and .gd tests are involved.")
    args = ap.parse_args()

    out_dir = ci_dir("sc-backfill-test-refs")
    eligible_statuses = {s.strip().lower() for s in split_csv(args.statuses)}
    tasks_json_p, _back_p, _gameplay_p = default_paths()
    tasks_json = load_json(tasks_json_p)

    if args.task_id:
        task_ids = [str(args.task_id).split(".", 1)[0].strip()]
    else:
        if args.all_tasks:
            task_ids = [str(t.get("id")) for t in iter_master_tasks(tasks_json)]
        else:
            task_ids = _task_ids_by_status(tasks_json, eligible_statuses)

    # Build status map for reporting.
    status_by_id: dict[str, str] = {}
    for t in iter_master_tasks(tasks_json):
        status_by_id[str(t.get("id"))] = str(t.get("status") or "")

    results: list[dict[str, Any]] = []
    hard_fail = False

    for task_id in task_ids:
        task_id = str(task_id).strip()
        if not task_id.isdigit():
            continue

        task_out = out_dir / f"task-{task_id}"
        task_out.mkdir(parents=True, exist_ok=True)

        master_status = str(status_by_id.get(task_id, "")).strip().lower()
        task_result: dict[str, Any] = {"task_id": task_id, "master_status": master_status, "steps": []}

        # 1) Validate acceptance refs at red stage (syntax only).
        step = _run_step(
            task_out,
            "acceptance-refs-red",
            [
                "py",
                "-3",
                "scripts/python/validate_acceptance_refs.py",
                "--task-id",
                task_id,
                "--stage",
                "red",
                "--out",
                str(task_out / "acceptance-refs.red.json"),
            ],
            timeout_sec=60,
        )
        task_result["steps"].append(step.__dict__)
        if step.status != "ok":
            hard_fail = True
            results.append(task_result)
            continue

        # 2) Sync test_refs from acceptance refs.
        if args.write:
            step = _run_step(
                task_out,
                "sync-test-refs",
                [
                    "py",
                    "-3",
                    "scripts/python/update_task_test_refs_from_acceptance_refs.py",
                    "--task-id",
                    task_id,
                    "--mode",
                    "replace",
                    "--write",
                ],
                timeout_sec=60,
            )
        else:
            step = _run_step(
                task_out,
                "sync-test-refs",
                [
                    "py",
                    "-3",
                    "scripts/python/update_task_test_refs_from_acceptance_refs.py",
                    "--task-id",
                    task_id,
                    "--mode",
                    "replace",
                ],
                timeout_sec=60,
            )
        task_result["steps"].append(step.__dict__)
        if step.status != "ok":
            hard_fail = True
            results.append(task_result)
            continue

        # 3) Generate missing test files only for eligible statuses.
        if master_status not in eligible_statuses:
            task_result["generation"] = "skipped"
            results.append(task_result)
            continue

        gen_cmd = [
            "py",
            "-3",
            "scripts/sc/llm_generate_tests_from_acceptance_refs.py",
            "--task-id",
            task_id,
            "--verify",
            str(args.verify),
            "--timeout-sec",
            str(int(args.timeout_sec)),
        ]
        if args.godot_bin:
            gen_cmd.extend(["--godot-bin", str(args.godot_bin)])
        step = _run_step(task_out, "llm-generate-tests", gen_cmd, timeout_sec=2_400)
        task_result["steps"].append(step.__dict__)
        if step.status != "ok":
            hard_fail = True
            results.append(task_result)
            continue

        # 4) Refactor-stage acceptance refs validation (files exist + included in test_refs).
        step = _run_step(
            task_out,
            "acceptance-refs-refactor",
            [
                "py",
                "-3",
                "scripts/python/validate_acceptance_refs.py",
                "--task-id",
                task_id,
                "--stage",
                "refactor",
                "--out",
                str(task_out / "acceptance-refs.refactor.json"),
            ],
            timeout_sec=60,
        )
        task_result["steps"].append(step.__dict__)
        if step.status != "ok":
            hard_fail = True

        results.append(task_result)

    summary = {
        "cmd": "sc-backfill-task-test-refs",
        "write": bool(args.write),
        "verify": str(args.verify),
        "eligible_statuses": sorted(eligible_statuses),
        "tasks_total": len(task_ids),
        "status": "fail" if hard_fail else "ok",
        "results": results,
        "out_dir": str(out_dir),
    }
    write_json(out_dir / "summary.json", summary)
    print(f"SC_BACKFILL_TEST_REFS status={summary['status']} out={out_dir}")
    return 1 if hard_fail else 0


if __name__ == "__main__":
    raise SystemExit(main())
