#!/usr/bin/env python3
"""
Evidence-oriented acceptance-check steps.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from _step_result import StepResult
from _util import repo_root, run_cmd, today_str, write_json, write_text


def step_headless_e2e_evidence(out_dir: Path, *, expected_run_id: str) -> StepResult:
    root = repo_root()
    date = today_str()
    sc_test_summary = root / "logs" / "ci" / date / "sc-test" / "summary.json"
    sc_test_run_id = root / "logs" / "ci" / date / "sc-test" / "run_id.txt"
    e2e_dir = root / "logs" / "e2e" / date / "sc-test" / "gdunit-hard"
    e2e_run_id = e2e_dir / "run_id.txt"

    details: dict[str, Any] = {
        "date": date,
        "expected_run_id": expected_run_id,
        "sc_test_summary": str(sc_test_summary.relative_to(root)).replace("\\", "/"),
        "sc_test_run_id_file": str(sc_test_run_id.relative_to(root)).replace("\\", "/"),
        "e2e_dir": str(e2e_dir.relative_to(root)).replace("\\", "/"),
        "e2e_run_id_file": str(e2e_run_id.relative_to(root)).replace("\\", "/"),
        "gdunit_step": None,
    }

    if not sc_test_summary.exists():
        write_json(out_dir / "headless-e2e-evidence.json", {**details, "error": "missing_sc_test_summary"})
        return StepResult(name="headless-e2e-evidence", status="fail", rc=1, details={**details, "error": "missing_sc_test_summary"})

    try:
        parsed = json.loads(sc_test_summary.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        write_json(out_dir / "headless-e2e-evidence.json", {**details, "error": f"invalid_sc_test_summary_json: {exc}"})
        return StepResult(
            name="headless-e2e-evidence",
            status="fail",
            rc=1,
            details={**details, "error": f"invalid_sc_test_summary_json: {exc}"},
        )

    run_id_in_summary = parsed.get("run_id") if isinstance(parsed, dict) else None
    details["run_id_in_summary"] = run_id_in_summary
    if str(run_id_in_summary or "") != expected_run_id:
        details["error"] = "run_id_mismatch"
        write_json(out_dir / "headless-e2e-evidence.json", details)
        return StepResult(name="headless-e2e-evidence", status="fail", rc=1, details=details)

    run_id_in_file = None
    if sc_test_run_id.exists():
        run_id_in_file = sc_test_run_id.read_text(encoding="utf-8", errors="ignore").strip()
    details["run_id_in_file"] = run_id_in_file
    if str(run_id_in_file or "") != expected_run_id:
        details["error"] = "run_id_file_mismatch"
        write_json(out_dir / "headless-e2e-evidence.json", details)
        return StepResult(name="headless-e2e-evidence", status="fail", rc=1, details=details)

    gd_step = None
    if isinstance(parsed, dict):
        for s in parsed.get("steps") or []:
            if isinstance(s, dict) and s.get("name") == "gdunit-hard":
                gd_step = s
                break
    details["gdunit_step"] = gd_step

    ok = True
    if not gd_step or gd_step.get("rc") != 0:
        ok = False
        details["error"] = "gdunit_step_missing_or_failed"

    if not e2e_dir.exists() or not any(e2e_dir.rglob("*")):
        ok = False
        details["error"] = details.get("error") or "e2e_dir_missing_or_empty"

    e2e_run_id_value = None
    if e2e_run_id.exists():
        e2e_run_id_value = e2e_run_id.read_text(encoding="utf-8", errors="ignore").strip()
    details["e2e_run_id_value"] = e2e_run_id_value
    if str(e2e_run_id_value or "") != expected_run_id:
        ok = False
        details["error"] = details.get("error") or "e2e_run_id_mismatch"

    write_json(out_dir / "headless-e2e-evidence.json", details)
    return StepResult(name="headless-e2e-evidence", status="ok" if ok else "fail", rc=0 if ok else 1, details=details)


def step_acceptance_executed_refs(out_dir: Path, *, task_id: int, expected_run_id: str) -> StepResult:
    out_json = out_dir / "acceptance-executed-refs.json"
    cmd = [
        "py",
        "-3",
        "scripts/python/validate_acceptance_execution_evidence.py",
        "--task-id",
        str(task_id),
        "--run-id",
        expected_run_id,
        "--out",
        str(out_json),
    ]
    rc, out = run_cmd(cmd, cwd=repo_root(), timeout_sec=120)
    log_path = out_dir / "acceptance-executed-refs.log"
    write_text(log_path, out)
    return StepResult(name="acceptance-executed-refs", status="ok" if rc == 0 else "fail", rc=rc, cmd=cmd, log=str(log_path))


def step_security_audit_evidence(out_dir: Path, *, expected_run_id: str) -> StepResult:
    out_json = out_dir / "security-audit-executed-evidence.json"
    cmd = [
        "py",
        "-3",
        "scripts/python/validate_security_audit_execution_evidence.py",
        "--run-id",
        expected_run_id,
        "--out",
        str(out_json),
    ]
    rc, out = run_cmd(cmd, cwd=repo_root(), timeout_sec=120)
    log_path = out_dir / "security-audit-executed-evidence.log"
    write_text(log_path, out)
    return StepResult(name="security-audit-executed-evidence", status="ok" if rc == 0 else "fail", rc=rc, cmd=cmd, log=str(log_path))

