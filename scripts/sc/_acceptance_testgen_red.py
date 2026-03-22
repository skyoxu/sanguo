from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def _read_json(path: Path) -> dict[str, Any]:
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return obj if isinstance(obj, dict) else {}


def _contains_compile_error(*, verify_log_text: str, unit_summary: dict[str, Any]) -> bool:
    haystacks = [verify_log_text]
    excerpt = unit_summary.get("failure_excerpt")
    if isinstance(excerpt, list):
        haystacks.extend(str(item) for item in excerpt)
    for blob in haystacks:
        lower = str(blob or "").lower()
        if "error cs" in lower or "build failed" in lower:
            return True
    return False


def evaluate_red_verification(
    *,
    repo_root: Path,
    out_dir: Path,
    verify_mode: str,
    test_step: dict[str, Any] | None,
    verify_log_text: str,
) -> dict[str, Any]:
    date = out_dir.parent.name
    report: dict[str, Any] = {
        "verify_mode": verify_mode,
        "status": "fail",
        "reason": "unknown",
    }
    if verify_mode == "none":
        report["reason"] = "verify_disabled"
        return report
    if not isinstance(test_step, dict):
        report["reason"] = "verify_step_missing"
        return report

    rc = test_step.get("rc")
    if rc == 0:
        report["reason"] = "unexpected_green"
        return report

    unit_summary = _read_json(repo_root / "logs" / "unit" / date / "summary.json")
    gdunit_summary = _read_json(repo_root / "logs" / "e2e" / date / "sc-test" / "gdunit-hard" / "run-summary.json")
    report["unit_summary_status"] = unit_summary.get("status")
    report["gdunit_failures"] = ((gdunit_summary.get("results") or {}).get("failures") if gdunit_summary else None)
    report["gdunit_errors"] = ((gdunit_summary.get("results") or {}).get("errors") if gdunit_summary else None)

    if _contains_compile_error(verify_log_text=verify_log_text, unit_summary=unit_summary):
        report["reason"] = "compile_error"
        return report

    unit_status = str(unit_summary.get("status") or "").strip()
    if unit_status == "tests_failed":
        report["status"] = "ok"
        report["reason"] = "unit_red"
        return report
    if unit_status in {"ok", "coverage_failed"}:
        report["reason"] = "unexpected_green"
        return report

    results = gdunit_summary.get("results") if isinstance(gdunit_summary, dict) else {}
    failures = int((results or {}).get("failures") or 0)
    errors = int((results or {}).get("errors") or 0)
    if failures > 0 and errors == 0:
        report["status"] = "ok"
        report["reason"] = "gdunit_red"
        return report
    if errors > 0:
        report["reason"] = "gdunit_errors"
        return report

    report["status"] = "ok"
    report["reason"] = "non_zero_without_compile_error"
    return report
