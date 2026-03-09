#!/usr/bin/env python3
"""
Run a deterministic local review pipeline with one shared run_id:
1) sc-test
2) sc-acceptance-check
3) sc-llm-review
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import uuid
from pathlib import Path
from typing import Any

from _summary_schema import (
    SummarySchemaError,
    validate_pipeline_summary,
    validate_sc_acceptance_summary,
    validate_sc_test_summary,
)
from _util import repo_root, run_cmd, today_str, write_json, write_text

OUT_RE = re.compile(r"\bout=([^\r\n]+)")


def _read_json(path: Path) -> dict[str, Any] | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    return payload if isinstance(payload, dict) else None


def _validate_step_summary(step_name: str, summary_file: str) -> str | None:
    # Enforce deterministic summary contracts before pipeline summary persists.
    if step_name not in {"sc-test", "sc-acceptance-check"}:
        return None
    if not summary_file:
        return f"{step_name} missing summary.json output."
    payload = _read_json(Path(summary_file))
    if payload is None:
        return f"{step_name} summary is not a valid JSON object: {summary_file}"
    try:
        if step_name == "sc-test":
            validate_sc_test_summary(payload)
        else:
            validate_sc_acceptance_summary(payload)
    except SummarySchemaError as exc:
        return str(exc)
    return None


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run task review pipeline with strict run_id binding.")
    parser.add_argument("--task-id", required=True, help="Task id (e.g. 1 or 1.3).")
    parser.add_argument("--run-id", default=None, help="Optional fixed run id. Auto-generated if omitted.")
    parser.add_argument("--godot-bin", default=None, help="Godot binary path (or env GODOT_BIN).")
    parser.add_argument("--security-profile", default="host-safe", choices=["strict", "host-safe"])
    parser.add_argument("--skip-test", action="store_true", help="Skip sc-test step.")
    parser.add_argument("--skip-acceptance", action="store_true", help="Skip sc-acceptance-check step.")
    parser.add_argument("--skip-llm-review", action="store_true", help="Skip sc-llm-review step.")
    parser.add_argument("--llm-agents", default="all", help="llm_review --agents value. Default: all.")
    parser.add_argument("--llm-timeout-sec", type=int, default=900, help="llm_review total timeout.")
    parser.add_argument("--llm-agent-timeout-sec", type=int, default=300, help="llm_review per-agent timeout.")
    parser.add_argument("--llm-semantic-gate", default="warn", choices=["skip", "warn", "require"])
    parser.add_argument("--llm-base", default="main", help="llm_review --base value.")
    parser.add_argument("--llm-diff-mode", default="full", choices=["full", "summary", "none"], help="llm_review --diff-mode value.")
    parser.add_argument("--llm-no-uncommitted", action="store_true", help="Do not pass --uncommitted to llm_review.")
    parser.add_argument("--llm-strict", action="store_true", help="Pass --strict to llm_review.")
    parser.add_argument(
        "--review-template",
        default="scripts/sc/templates/llm_review/bmad-godot-review-template.txt",
        help="llm_review template path.",
    )
    parser.add_argument("--dry-run", action="store_true", help="Print planned commands without executing.")
    parser.add_argument(
        "--allow-overwrite",
        action="store_true",
        help="Allow reusing an existing task+run_id output directory by deleting it first.",
    )
    parser.add_argument(
        "--force-new-run-id",
        action="store_true",
        help="When task+run_id directory exists, auto-generate a new run_id instead of failing.",
    )
    return parser


def _task_root_id(task_id: str) -> str:
    return str(task_id).strip().split(".", 1)[0].strip()


def _prepare_env(run_id: str) -> None:
    os.environ["SC_PIPELINE_RUN_ID"] = run_id
    os.environ["SC_TEST_RUN_ID"] = run_id
    os.environ["SC_ACCEPTANCE_RUN_ID"] = run_id


def _pipeline_run_dir(task_id: str, run_id: str) -> Path:
    return repo_root() / "logs" / "ci" / today_str() / f"sc-review-pipeline-task-{task_id}-{run_id}"


def _pipeline_latest_index_path(task_id: str) -> Path:
    return repo_root() / "logs" / "ci" / today_str() / f"sc-review-pipeline-task-{task_id}" / "latest.json"


def _write_latest_index(*, task_id: str, run_id: str, out_dir: Path, status: str) -> None:
    index_payload: dict[str, Any] = {
        "task_id": task_id,
        "run_id": run_id,
        "status": status,
        "date": today_str(),
        "latest_out_dir": str(out_dir),
        "summary_path": str(out_dir / "summary.json"),
    }
    write_json(_pipeline_latest_index_path(task_id), index_payload)


def _run_step(*, out_dir: Path, name: str, cmd: list[str], timeout_sec: int) -> dict[str, Any]:
    rc, out = run_cmd(cmd, cwd=repo_root(), timeout_sec=timeout_sec)
    log_path = out_dir / f"{name}.log"
    reported_out_dir = ""
    summary_file = ""
    for line in reversed(out.splitlines()):
        matched = OUT_RE.search(line)
        if not matched:
            continue
        candidate = matched.group(1).strip().strip("\"'").strip()
        if not candidate:
            continue
        candidate_path = Path(candidate)
        if candidate_path.exists():
            reported_out_dir = str(candidate_path)
            summary_candidate = candidate_path / "summary.json"
            if summary_candidate.exists():
                summary_file = str(summary_candidate)
            break
    schema_error = _validate_step_summary(name, summary_file)
    if schema_error:
        rc = 1
        out = (
            f"{out.rstrip()}\n"
            f"[sc-review-pipeline] ERROR: {schema_error}\n"
            f"[sc-review-pipeline] step={name} summary_file={summary_file or '<none>'}\n"
        )
    write_text(log_path, out)
    return {
        "name": name,
        "cmd": cmd,
        "rc": rc,
        "status": "ok" if rc == 0 else "fail",
        "log": str(log_path),
        "reported_out_dir": reported_out_dir,
        "summary_file": summary_file,
    }


def main() -> int:
    args = build_parser().parse_args()
    task_id = _task_root_id(args.task_id)
    if not task_id:
        print("[sc-review-pipeline] ERROR: invalid --task-id")
        return 2

    if bool(args.allow_overwrite) and bool(args.force_new_run_id):
        print("[sc-review-pipeline] ERROR: --allow-overwrite and --force-new-run-id are mutually exclusive.")
        return 2

    requested_run_id = str(args.run_id or "").strip() or uuid.uuid4().hex
    run_id = requested_run_id

    out_dir = _pipeline_run_dir(task_id, run_id)
    if out_dir.exists():
        if bool(args.force_new_run_id):
            original_run_id = run_id
            attempts = 0
            while out_dir.exists():
                run_id = uuid.uuid4().hex
                out_dir = _pipeline_run_dir(task_id, run_id)
                attempts += 1
                if attempts > 16:
                    print("[sc-review-pipeline] ERROR: failed to allocate a unique run_id after 16 attempts.")
                    return 2
            print(f"[sc-review-pipeline] INFO: run_id collision detected, remapped {original_run_id} -> {run_id}")
        elif not bool(args.allow_overwrite):
            print(
                "[sc-review-pipeline] ERROR: output directory already exists for this task/run_id. "
                "Use a new --run-id, --force-new-run-id, or pass --allow-overwrite."
            )
            return 2
        else:
            try:
                shutil.rmtree(out_dir, ignore_errors=False)
            except Exception as exc:  # noqa: BLE001
                print(f"[sc-review-pipeline] ERROR: failed to clear existing output directory: {exc}")
                return 2

    _prepare_env(run_id)
    write_text(out_dir / "run_id.txt", run_id + "\n")

    summary: dict[str, Any] = {
        "cmd": "sc-review-pipeline",
        "task_id": task_id,
        "requested_run_id": requested_run_id,
        "run_id": run_id,
        "allow_overwrite": bool(args.allow_overwrite),
        "force_new_run_id": bool(args.force_new_run_id),
        "status": "ok",
        "steps": [],
    }

    schema_error_log = out_dir / "summary-schema-validation-error.log"

    def persist() -> bool:
        try:
            validate_pipeline_summary(summary)
        except SummarySchemaError as exc:
            error_message = f"{exc}\n"
            write_text(schema_error_log, error_message)
            write_json(out_dir / "summary.invalid.json", summary)
            _write_latest_index(task_id=task_id, run_id=run_id, out_dir=out_dir, status="fail")
            print(f"[sc-review-pipeline] ERROR: summary schema validation failed. details={schema_error_log}")
            return False
        invalid_summary_path = out_dir / "summary.invalid.json"
        if schema_error_log.exists():
            schema_error_log.unlink(missing_ok=True)
        if invalid_summary_path.exists():
            invalid_summary_path.unlink(missing_ok=True)
        write_json(out_dir / "summary.json", summary)
        _write_latest_index(task_id=task_id, run_id=run_id, out_dir=out_dir, status=str(summary.get("status", "fail")))
        return True

    def add_step(step: dict[str, Any]) -> bool:
        summary["steps"].append(step)
        if step.get("status") == "fail":
            summary["status"] = "fail"
        if not persist():
            return False
        return step.get("status") != "fail"

    if not persist():
        return 2

    steps: list[tuple[str, list[str], int, bool]] = []

    test_cmd = ["py", "-3", "scripts/sc/test.py", "--task-id", task_id, "--run-id", run_id]
    if args.godot_bin:
        test_cmd += ["--godot-bin", str(args.godot_bin)]
    steps.append(("sc-test", test_cmd, 1800, args.skip_test))

    acceptance_cmd = [
        "py",
        "-3",
        "scripts/sc/acceptance_check.py",
        "--task-id",
        task_id,
        "--run-id",
        run_id,
        "--out-per-task",
        "--security-profile",
        args.security_profile,
        "--require-task-test-refs",
    ]
    if args.godot_bin:
        acceptance_cmd += ["--godot-bin", str(args.godot_bin)]
    steps.append(("sc-acceptance-check", acceptance_cmd, 1800, args.skip_acceptance))

    llm_cmd = [
        "py",
        "-3",
        "scripts/sc/llm_review.py",
        "--task-id",
        task_id,
        "--security-profile",
        args.security_profile,
        "--review-profile",
        "bmad-godot",
        "--review-template",
        args.review_template,
        "--semantic-gate",
        args.llm_semantic_gate,
        "--agents",
        args.llm_agents,
        "--base",
        args.llm_base,
        "--diff-mode",
        args.llm_diff_mode,
        "--timeout-sec",
        str(args.llm_timeout_sec),
        "--agent-timeout-sec",
        str(args.llm_agent_timeout_sec),
    ]
    if not args.llm_no_uncommitted:
        llm_cmd.append("--uncommitted")
    if args.llm_strict:
        llm_cmd.append("--strict")
    steps.append(("sc-llm-review", llm_cmd, max(300, int(args.llm_timeout_sec) + 120), args.skip_llm_review))

    for step_name, cmd, timeout_sec, skipped in steps:
        if skipped:
            if not add_step({"name": step_name, "status": "skipped", "rc": 0, "cmd": cmd}):
                if schema_error_log.exists():
                    return 2
                break
            continue
        if args.dry_run:
            print(f"[dry-run] {step_name}: {' '.join(cmd)}")
            if not add_step({"name": step_name, "status": "planned", "rc": 0, "cmd": cmd}):
                if schema_error_log.exists():
                    return 2
                break
            continue

        ok = add_step(_run_step(out_dir=out_dir, name=step_name, cmd=cmd, timeout_sec=timeout_sec))
        if not ok:
            if schema_error_log.exists():
                return 2
            break

    if not persist():
        return 2
    print(f"SC_REVIEW_PIPELINE status={summary['status']} out={out_dir}")
    return 0 if summary["status"] == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
