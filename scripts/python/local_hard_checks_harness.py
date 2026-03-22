#!/usr/bin/env python3
"""Protocolized local hard checks run wrapper."""

from __future__ import annotations

import datetime as dt
import subprocess
import sys
import uuid
from pathlib import Path
from typing import Any, Callable

from dev_cli_builders import (
    DEFAULT_GATE_BUNDLE_TASK_FILES,
)
from local_hard_checks_support import (
    CMD_NAME,
    PROTOCOL_VERSION,
    SCHEMA_VERSION,
    TASK_SCOPE,
    build_execution_context,
    build_harness_capabilities,
    build_repair_guide,
    build_step_plan,
    default_out_dir,
    persist_sidecars,
    write_latest_index,
    write_step_log,
)

try:
    from _delivery_profile import default_security_profile_for_delivery, resolve_delivery_profile
    from _pipeline_events import append_run_event
    from _summary_schema import SummarySchemaError, validate_local_hard_checks_summary
    from _util import write_json, write_text
except ImportError:
    _SC_DIR = Path(__file__).resolve().parents[1] / "sc"
    if str(_SC_DIR) not in sys.path:
        sys.path.insert(0, str(_SC_DIR))
    from _delivery_profile import default_security_profile_for_delivery, resolve_delivery_profile
    from _pipeline_events import append_run_event
    from _summary_schema import SummarySchemaError, validate_local_hard_checks_summary
    from _util import write_json, write_text


def _utc_now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _run_step_default(cmd: list[str]) -> int:
    print(f"[local-hard-checks] running: {' '.join(cmd)}")
    proc = subprocess.run(cmd, text=True)
    return proc.returncode


def run_local_hard_checks(
    *,
    solution: str = "Game.sln",
    configuration: str = "Debug",
    godot_bin: str = "",
    delivery_profile: str = "",
    task_files: list[str] | None = None,
    out_dir: str = "",
    run_id: str = "",
    timeout_sec: int = 5,
    run_fn: Callable[[list[str]], int] | None = None,
) -> int:
    resolved_delivery_profile = resolve_delivery_profile(delivery_profile or None)
    security_profile = default_security_profile_for_delivery(resolved_delivery_profile)
    requested_run_id = str(run_id or "").strip() or uuid.uuid4().hex
    resolved_run_id = requested_run_id
    resolved_out_dir = Path(out_dir) if out_dir else default_out_dir(resolved_run_id)
    resolved_out_dir.mkdir(parents=True, exist_ok=True)
    task_file_list = list(task_files or DEFAULT_GATE_BUNDLE_TASK_FILES)
    runner = run_fn or _run_step_default
    started_at = _utc_now_iso()

    write_text(resolved_out_dir / "run_id.txt", resolved_run_id + "\n")
    write_json(
        resolved_out_dir / "harness-capabilities.json",
        build_harness_capabilities(
            run_id=resolved_run_id,
            delivery_profile=resolved_delivery_profile,
            security_profile=security_profile,
        ),
    )

    append_run_event(
        out_dir=resolved_out_dir,
        event="run_started",
        task_id=TASK_SCOPE,
        run_id=resolved_run_id,
        delivery_profile=resolved_delivery_profile,
        security_profile=security_profile,
        status="running",
        details={"requested_run_id": requested_run_id, "cmd": CMD_NAME},
    )

    summary: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "protocol_version": PROTOCOL_VERSION,
        "cmd": CMD_NAME,
        "task_id": TASK_SCOPE,
        "requested_run_id": requested_run_id,
        "run_id": resolved_run_id,
        "delivery_profile": resolved_delivery_profile,
        "security_profile": security_profile,
        "status": "ok",
        "failed_step": "",
        "started_at": started_at,
        "finished_at": "",
        "out_dir": str(resolved_out_dir).replace("\\", "/"),
        "steps": [],
    }

    rc = 0
    for step in build_step_plan(
        delivery_profile=resolved_delivery_profile,
        task_files=task_file_list,
        out_dir=resolved_out_dir,
        run_id=resolved_run_id,
        solution=solution,
        configuration=configuration,
        godot_bin=godot_bin,
        timeout_sec=timeout_sec,
    ):
        name = str(step["name"])
        cmd = [str(x) for x in step["cmd"]]
        artifacts = dict(step.get("artifacts") or {})
        step_log = resolved_out_dir / f"{name}.log"
        append_run_event(
            out_dir=resolved_out_dir,
            event="step_started",
            task_id=TASK_SCOPE,
            run_id=resolved_run_id,
            delivery_profile=resolved_delivery_profile,
            security_profile=security_profile,
            step_name=name,
            status="running",
            details={"cmd": cmd},
        )
        step_rc = int(runner(cmd))
        step_status = "ok" if step_rc == 0 else "fail"
        write_step_log(step_log, cmd=cmd, rc=step_rc, status=step_status, artifacts=artifacts)
        append_run_event(
            out_dir=resolved_out_dir,
            event="step_finished",
            task_id=TASK_SCOPE,
            run_id=resolved_run_id,
            delivery_profile=resolved_delivery_profile,
            security_profile=security_profile,
            step_name=name,
            status=step_status,
            details={"rc": step_rc, "log": str(step_log).replace("\\", "/"), **artifacts},
        )
        summary["steps"].append(
            {
                "name": name,
                "cmd": cmd,
                "rc": step_rc,
                "status": step_status,
                "log": str(step_log).replace("\\", "/"),
                **artifacts,
            }
        )
        if step_rc != 0:
            rc = step_rc
            summary["status"] = "fail"
            summary["failed_step"] = name
            break

    summary["finished_at"] = _utc_now_iso()
    event_name = "run_completed" if summary["status"] == "ok" else "run_failed"
    append_run_event(
        out_dir=resolved_out_dir,
        event=event_name,
        task_id=TASK_SCOPE,
        run_id=resolved_run_id,
        delivery_profile=resolved_delivery_profile,
        security_profile=security_profile,
        status=summary["status"],
        details={"failed_step": summary["failed_step"]},
    )

    execution_context = build_execution_context(
        out_dir=resolved_out_dir,
        run_id=resolved_run_id,
        requested_run_id=requested_run_id,
        delivery_profile=resolved_delivery_profile,
        security_profile=security_profile,
        status=str(summary["status"]),
        failed_step=str(summary["failed_step"]),
    )
    repair_guide = build_repair_guide(
        out_dir=resolved_out_dir,
        requested_run_id=requested_run_id,
        run_id=resolved_run_id,
        status=str(summary["status"]),
        failed_step=str(summary["failed_step"]),
        godot_bin=godot_bin,
    )

    if not persist_sidecars(
        out_dir=resolved_out_dir,
        run_id=resolved_run_id,
        summary=summary,
        execution_context=execution_context,
        repair_guide=repair_guide,
        validate_summary=validate_local_hard_checks_summary,
        summary_schema_error=SummarySchemaError,
    ):
        return 2
    return 0 if summary["status"] == "ok" else (rc or 1)
