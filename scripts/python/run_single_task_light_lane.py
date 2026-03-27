#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Run workflow.md 5.1 single-task light lane with full-step execution.

Key behavior:
- Always executes all 7 steps per task by default (no early-stop on step failure).
- Supports resume from summary.json.
- Writes per-step logs and rolling summary for stable long runs on Windows.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import subprocess
from pathlib import Path
from typing import Any


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _today() -> str:
    return dt.date.today().strftime("%Y-%m-%d")


def _default_out_dir(root: Path) -> Path:
    return root / "logs" / "ci" / _today() / "single-task-light-lane-v2"


def _parse_task_ids_csv(raw: str) -> list[int]:
    out: list[int] = []
    for token in str(raw or "").split(","):
        s = token.strip()
        if not s:
            continue
        if not s.isdigit():
            continue
        n = int(s)
        if n > 0:
            out.append(n)
    return sorted(set(out))


def _load_master_task_ids(root: Path) -> list[int]:
    p = root / ".taskmaster" / "tasks" / "tasks.json"
    data = json.loads(p.read_text(encoding="utf-8"))
    tasks = ((data or {}).get("master") or {}).get("tasks") or []
    ids: list[int] = []
    for item in tasks:
        if not isinstance(item, dict):
            continue
        raw = str(item.get("id") or "").strip()
        if raw.isdigit():
            ids.append(int(raw))
    return sorted(set(ids))


def _steps(*, align_apply: bool) -> list[tuple[str, list[str]]]:
    align_cmd = [
        "py",
        "-3",
        "scripts/sc/llm_align_acceptance_semantics.py",
        "--task-ids",
        "{id}",
        "--strict-task-selection",
    ]
    if bool(align_apply):
        align_cmd.append("--apply")

    return [
        (
            "extract",
            [
                "py",
                "-3",
                "scripts/sc/llm_extract_task_obligations.py",
                "--task-id",
                "{id}",
                "--delivery-profile",
                "fast-ship",
                "--reuse-last-ok",
                "--explain-reuse-miss",
            ],
        ),
        ("align", align_cmd),
        (
            "coverage",
            [
                "py",
                "-3",
                "scripts/sc/llm_check_subtasks_coverage.py",
                "--task-id",
                "{id}",
                "--strict-view-selection",
            ],
        ),
        (
            "semantic_gate",
            [
                "py",
                "-3",
                "scripts/sc/llm_semantic_gate_all.py",
                "--task-ids",
                "{id}",
                "--max-needs-fix",
                "0",
                "--max-unknown",
                "3",
            ],
        ),
        (
            "fill_refs_dry",
            [
                "py",
                "-3",
                "scripts/sc/llm_fill_acceptance_refs.py",
                "--task-id",
                "{id}",
            ],
        ),
        (
            "fill_refs_write",
            [
                "py",
                "-3",
                "scripts/sc/llm_fill_acceptance_refs.py",
                "--task-id",
                "{id}",
                "--write",
            ],
        ),
        (
            "fill_refs_verify",
            [
                "py",
                "-3",
                "scripts/sc/llm_fill_acceptance_refs.py",
                "--task-id",
                "{id}",
            ],
        ),
    ]


def _run_step(root: Path, cmd: list[str], timeout_sec: int) -> tuple[int, str, str]:
    try:
        proc = subprocess.run(
            cmd,
            cwd=str(root),
            text=True,
            encoding="utf-8",
            errors="replace",
            capture_output=True,
            timeout=max(1, int(timeout_sec)),
        )
        return int(proc.returncode), proc.stdout or "", proc.stderr or ""
    except subprocess.TimeoutExpired as exc:
        stdout = (exc.stdout or "") if isinstance(exc.stdout, str) else ""
        stderr = (exc.stderr or "") if isinstance(exc.stderr, str) else ""
        return 124, stdout, stderr


def _load_summary(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    return data if isinstance(data, dict) else None


def _index_results(results: list[dict[str, Any]]) -> dict[int, dict[str, Any]]:
    out: dict[int, dict[str, Any]] = {}
    for row in results:
        if not isinstance(row, dict):
            continue
        tid_raw = str(row.get("task_id") or "").strip()
        if tid_raw.isdigit():
            out[int(tid_raw)] = row
    return out


def _rebuild_counts(summary: dict[str, Any]) -> None:
    results = [r for r in summary.get("results", []) if isinstance(r, dict)]
    failed_step_counts: dict[str, int] = {}
    passed = 0
    failed = 0
    for row in results:
        if bool(row.get("ok")):
            passed += 1
            continue
        failed += 1
        for step in row.get("failed_steps", []) or []:
            key = str(step)
            failed_step_counts[key] = failed_step_counts.get(key, 0) + 1
    summary["processed_tasks"] = len(results)
    summary["passed_tasks"] = passed
    summary["failed_tasks"] = failed
    summary["failed_step_counts"] = failed_step_counts


def main() -> int:
    ap = argparse.ArgumentParser(description="Run workflow.md 5.1 single-task light lane with full-step execution.")
    ap.add_argument("--task-ids", default="", help="Optional CSV task ids override (e.g. 66,67,70).")
    ap.add_argument("--task-id-start", type=int, default=66)
    ap.add_argument("--task-id-end", type=int, default=0, help="0 means until max task id.")
    ap.add_argument("--max-tasks", type=int, default=0, help="0 means all selected tasks.")
    ap.add_argument("--timeout-sec", type=int, default=420, help="Per-step timeout in seconds.")
    ap.add_argument("--out-dir", default="", help="Output directory. Default: logs/ci/<date>/single-task-light-lane-v2")
    ap.add_argument("--no-resume", action="store_true", help="Ignore existing summary.json and rerun from scratch.")
    ap.add_argument("--stop-on-step-failure", action="store_true", help="Stop remaining steps in a task when one step fails.")
    ap.add_argument("--no-align-apply", action="store_true", help="Do not pass --apply to align step (read-only triage mode).")
    ap.add_argument("--self-check", action="store_true", help="Print resolved task range and exit.")
    args = ap.parse_args()

    root = _repo_root()
    all_ids = _load_master_task_ids(root)
    if not all_ids:
        print("SINGLE_TASK_LIGHT_LANE status=fail reason=no_tasks")
        return 2

    if str(args.task_ids).strip():
        selected = [tid for tid in _parse_task_ids_csv(args.task_ids) if tid in set(all_ids)]
    else:
        start = max(1, int(args.task_id_start))
        end = int(args.task_id_end) if int(args.task_id_end) > 0 else max(all_ids)
        selected = [tid for tid in all_ids if start <= tid <= end]
    if int(args.max_tasks) > 0:
        selected = selected[: int(args.max_tasks)]
    if not selected:
        print("SINGLE_TASK_LIGHT_LANE status=fail reason=no_selected_tasks")
        return 2

    out_dir = Path(args.out_dir) if str(args.out_dir).strip() else _default_out_dir(root)
    out_dir.mkdir(parents=True, exist_ok=True)
    summary_path = out_dir / "summary.json"
    steps = _steps(align_apply=(not bool(args.no_align_apply)))

    if bool(args.self_check):
        payload = {
            "status": "ok",
            "task_count": len(selected),
            "task_id_start": selected[0],
            "task_id_end": selected[-1],
            "steps": [name for name, _ in steps],
            "out_dir": str(out_dir).replace("\\", "/"),
        }
        summary_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(
            f"SINGLE_TASK_LIGHT_LANE_SELF_CHECK status=ok tasks={len(selected)} "
            f"range=T{selected[0]}-T{selected[-1]} out={str(summary_path).replace('\\', '/')}"
        )
        return 0

    summary: dict[str, Any]
    if not bool(args.no_resume):
        old = _load_summary(summary_path)
        if old:
            summary = old
        else:
            summary = {}
    else:
        summary = {}

    if "results" not in summary or not isinstance(summary.get("results"), list):
        summary["results"] = []
    summary.setdefault("cmd", "run_single_task_light_lane")
    summary.setdefault("started_at", dt.datetime.now().isoformat(timespec="seconds"))
    summary["task_id_start"] = selected[0]
    summary["task_id_end"] = selected[-1]
    summary["task_count"] = len(selected)
    summary["out_dir"] = str(out_dir).replace("\\", "/")
    summary["status"] = "running"

    existing = _index_results(summary["results"])
    updated: dict[int, dict[str, Any]] = {k: v for k, v in existing.items() if k in set(selected)}

    for idx, tid in enumerate(selected, start=1):
        row = updated.get(tid, {"task_id": tid, "steps": []})
        step_map = {str(s.get("step")): s for s in row.get("steps", []) if isinstance(s, dict)}

        print(f"[{idx}/{len(selected)}] run task {tid}")
        failed_steps: list[str] = []
        for step_name, tpl in steps:
            cmd = [part.format(id=tid) for part in tpl]
            rc, stdout, stderr = _run_step(root, cmd, timeout_sec=int(args.timeout_sec))
            log_path = out_dir / f"t{tid:04d}--{step_name}.log"
            body = "\n".join(
                [
                    f"cmd: {' '.join(cmd)}",
                    f"rc: {rc}",
                    "--- stdout ---",
                    stdout or "",
                    "--- stderr ---",
                    stderr or "",
                ]
            )
            log_path.write_text(body, encoding="utf-8")
            step_map[step_name] = {
                "step": step_name,
                "rc": rc,
                "log": str(log_path.relative_to(root)).replace("\\", "/"),
                "stdout_tail": (stdout.strip().splitlines()[-1] if stdout.strip() else ""),
                "stderr_tail": (stderr.strip().splitlines()[-1] if stderr.strip() else ""),
            }
            if rc != 0:
                failed_steps.append(step_name)
                if bool(args.stop_on_step_failure):
                    break

        ordered_steps = [step_map[name] for name, _ in steps if name in step_map]
        row["steps"] = ordered_steps
        row["failed_steps"] = failed_steps
        row["first_failed_step"] = failed_steps[0] if failed_steps else ""
        row["ok"] = len(failed_steps) == 0 and len(ordered_steps) == len(steps)
        updated[tid] = row

        summary["results"] = [updated[k] for k in sorted(updated.keys())]
        _rebuild_counts(summary)
        summary["remaining_tasks"] = max(0, len(selected) - int(summary.get("processed_tasks", 0)))
        summary["last_task_id"] = tid
        summary["last_updated_at"] = dt.datetime.now().isoformat(timespec="seconds")
        summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    _rebuild_counts(summary)
    summary["remaining_tasks"] = max(0, len(selected) - int(summary.get("processed_tasks", 0)))
    summary["status"] = "ok" if int(summary.get("failed_tasks", 0)) == 0 else "fail"
    summary["finished_at"] = dt.datetime.now().isoformat(timespec="seconds")
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(
        "SINGLE_TASK_LIGHT_LANE "
        f"status={summary['status']} processed={summary.get('processed_tasks', 0)}/{len(selected)} "
        f"passed={summary.get('passed_tasks', 0)} failed={summary.get('failed_tasks', 0)} "
        f"out={str(summary_path).replace('\\', '/')}"
    )
    return 0 if summary["status"] == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
