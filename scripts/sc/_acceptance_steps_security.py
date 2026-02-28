#!/usr/bin/env python3
"""
Security-related acceptance-check steps.
"""

from __future__ import annotations

from pathlib import Path

from _acceptance_steps_runner import run_and_capture, run_and_capture_mode
from _step_result import StepResult
from _util import repo_root, write_json


def step_security_soft(out_dir: Path) -> StepResult:
    # Soft checks: do not block, but record output.
    steps = []
    steps.append(run_and_capture(out_dir, "check-sentry-secrets", ["py", "-3", "scripts/python/check_sentry_secrets.py"], 60))
    steps.append(run_and_capture(out_dir, "check-domain-contracts", ["py", "-3", "scripts/python/check_domain_contracts.py"], 60))
    steps.append(
        run_and_capture(
            out_dir,
            "security-soft-scan",
            ["py", "-3", "scripts/python/security_soft_scan.py", "--out", str(out_dir / "security-soft-scan.json")],
            120,
        )
    )
    # Optional: encoding scan (soft)
    steps.append(run_and_capture(out_dir, "check-encoding-since-today", ["py", "-3", "scripts/python/check_encoding.py", "--since-today"], 300))

    # Soft gate: always ok, but include failures in details.
    details = {"steps": [s.__dict__ for s in steps]}
    write_json(out_dir / "security-soft.json", details)
    return StepResult(name="security-soft", status="ok", details=details)


def step_security_hard(
    out_dir: Path,
    *,
    path_mode: str = "require",
    sql_mode: str = "require",
    audit_schema_mode: str = "require",
) -> StepResult:
    """
    Hard gates (deterministic):
      - Path safety invariants (static scan)
      - SQL injection anti-patterns (static scan)
      - Security audit logging presence & schema (static scan)
    """

    root = repo_root()
    path_out = out_dir / "security-path-gate.json"
    sql_out = out_dir / "security-sql-gate.json"
    audit_out = out_dir / "security-audit-gate.json"

    steps: list[StepResult] = []
    path_mode = str(path_mode or "require").strip().lower()
    sql_mode = str(sql_mode or "require").strip().lower()
    audit_schema_mode = str(audit_schema_mode or "require").strip().lower()
    if path_mode not in ("skip", "warn", "require"):
        path_mode = "require"
    if sql_mode not in ("skip", "warn", "require"):
        sql_mode = "require"
    if audit_schema_mode not in ("skip", "warn", "require"):
        audit_schema_mode = "require"

    if path_mode == "skip":
        steps.append(StepResult(name="security-path-gate", status="skipped", rc=0, details={"mode": "skip"}))
    else:
        steps.append(
            run_and_capture_mode(
                out_dir,
                "security-path-gate",
                ["py", "-3", "scripts/python/security_hard_path_gate.py", "--out", str(path_out)],
                120,
                mode=path_mode,
            )
        )

    if sql_mode == "skip":
        steps.append(StepResult(name="security-sql-gate", status="skipped", rc=0, details={"mode": "skip"}))
    else:
        steps.append(
            run_and_capture_mode(
                out_dir,
                "security-sql-gate",
                ["py", "-3", "scripts/python/security_hard_sql_gate.py", "--out", str(sql_out)],
                120,
                mode=sql_mode,
            )
        )

    if audit_schema_mode == "skip":
        steps.append(StepResult(name="security-audit-gate", status="skipped", rc=0, details={"mode": "skip"}))
    else:
        steps.append(
            run_and_capture_mode(
                out_dir,
                "security-audit-gate",
                ["py", "-3", "scripts/python/security_hard_audit_gate.py", "--out", str(audit_out)],
                120,
                mode=audit_schema_mode,
            )
        )

    ok = all(s.status in ("ok", "skipped") for s in steps)
    details = {
        "modes": {"path": path_mode, "sql": sql_mode, "audit_schema": audit_schema_mode},
        "steps": [s.__dict__ for s in steps],
        "outputs": {
            "path_gate": str(path_out.relative_to(root)).replace("\\", "/"),
            "sql_gate": str(sql_out.relative_to(root)).replace("\\", "/"),
            "audit_gate": str(audit_out.relative_to(root)).replace("\\", "/"),
        },
    }
    write_json(out_dir / "security-hard.json", details)
    return StepResult(name="security-hard", status="ok" if ok else "fail", rc=0 if ok else 1, details=details)


def step_ui_event_security(out_dir: Path, *, json_mode: str, source_mode: str) -> StepResult:
    """
    Optional gate: UI event security heuristics (deterministic static scan).

    mode:
      - skip: do nothing
      - warn: never fail
      - require: fail on violations
    """
    json_mode = str(json_mode or "skip").strip().lower()
    source_mode = str(source_mode or "skip").strip().lower()
    if json_mode not in ("skip", "warn", "require"):
        json_mode = "skip"
    if source_mode not in ("skip", "warn", "require"):
        source_mode = "skip"
    if json_mode == "skip" and source_mode == "skip":
        return StepResult(name="ui-event-security", status="skipped", rc=0, details={"json_mode": "skip", "source_mode": "skip"})

    root = repo_root()
    json_out = out_dir / "ui-event-json-guards.json"
    src_out = out_dir / "ui-event-source-verify.json"

    if json_mode == "skip":
        json_step = StepResult(name="ui-event-json-guards", status="skipped", rc=0, details={"mode": "skip"})
    else:
        json_step = run_and_capture_mode(
            out_dir,
            "ui-event-json-guards",
            ["py", "-3", "scripts/python/validate_ui_event_json_guards.py", "--out", str(json_out)],
            120,
            mode=json_mode,
        )

    if source_mode == "skip":
        src_step = StepResult(name="ui-event-source-verify", status="skipped", rc=0, details={"mode": "skip"})
    else:
        src_step = run_and_capture_mode(
            out_dir,
            "ui-event-source-verify",
            ["py", "-3", "scripts/python/validate_ui_event_source_verification.py", "--out", str(src_out)],
            120,
            mode=source_mode,
        )

    ok = (json_step.status in ("ok", "skipped")) and (src_step.status in ("ok", "skipped"))
    details = {
        "modes": {"json": json_mode, "source": source_mode},
        "steps": [json_step.__dict__, src_step.__dict__],
        "outputs": {
            "json_guards": str(json_out.relative_to(root)).replace("\\", "/"),
            "source_verify": str(src_out.relative_to(root)).replace("\\", "/"),
        },
    }
    write_json(out_dir / "ui-event-security.json", details)
    return StepResult(name="ui-event-security", status="ok" if ok else "fail", rc=0 if ok else 1, details=details)
