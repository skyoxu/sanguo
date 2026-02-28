#!/usr/bin/env python3
"""
sc-acceptance-check: local, reproducible acceptance gate.
"""

from __future__ import annotations

import os
import uuid
from pathlib import Path
from typing import Any
from _acceptance_orchestration import (
    build_step_plan,
    is_enabled,
    run_registry_steps,
    run_tests_bundle,
)
from _acceptance_report import write_markdown_report
from _acceptance_runtime import (
    build_parser,
    compute_perf_p95_ms,
    normalize_subtasks_mode,
    parse_only_steps,
    resolve_security_modes,
    should_mark_hard_failure,
    validate_arg_conflicts,
)
from _acceptance_task_requirements import (
    parse_task_id,
    task_requires_env_evidence_preflight,
    task_requires_headless_e2e,
)
from _acceptance_steps import StepResult, step_perf_budget
from _risk_summary import write_risk_summary
from _security_profile import security_profile_payload
from _taskmaster import resolve_triplet
from _unit_metrics import collect_unit_metrics
from _util import ci_dir, repo_root, today_str, write_json


def _collect_metrics(steps: list[StepResult]) -> dict[str, Any]:
    metrics: dict[str, Any] = {}
    tests_step = next((s for s in steps if s.name == "tests-all" and s.log), None)
    tests_log = Path(tests_step.log) if (tests_step and tests_step.log) else None
    unit = collect_unit_metrics(
        tests_all_log=tests_log,
        fallback_unit_dir=(repo_root() / "logs" / "unit" / today_str()),
    )
    if unit:
        metrics["unit"] = unit

    perf_step = next((s for s in steps if s.name == "perf-budget" and isinstance(s.details, dict)), None)
    if perf_step and isinstance(perf_step.details, dict):
        metrics["perf"] = perf_step.details
    return metrics


def _append_risk_summary(
    *,
    out_dir: Path,
    triplet: Any,
    run_id: str,
    hard_failed: bool,
    steps: list[StepResult],
    metrics: dict[str, Any],
) -> tuple[bool, str | None]:
    try:
        risk_path, risk_payload = write_risk_summary(
            out_dir=out_dir,
            task_id=str(triplet.task_id),
            run_id=run_id,
            acceptance_status="fail" if hard_failed else "ok",
            steps=steps,
            metrics=metrics or None,
        )
        risk_summary_rel = str(risk_path.relative_to(repo_root())).replace("\\", "/")
        steps.append(
            StepResult(
                name="risk-summary",
                status="ok",
                rc=0,
                details={
                    "risk_summary": risk_summary_rel,
                    "levels": (risk_payload or {}).get("levels"),
                    "scores": (risk_payload or {}).get("scores"),
                    "verdict": (risk_payload or {}).get("verdict"),
                },
            )
        )
        return hard_failed, risk_summary_rel
    except Exception as exc:  # noqa: BLE001
        steps.append(StepResult(name="risk-summary", status="fail", rc=1, details={"error": str(exc)}))
        return True, None


def _build_summary(
    *,
    mode: str,
    status: str,
    out_dir: Path,
    args: Any,
    subtasks_mode: str,
    security_profile: str,
    security_modes: dict[str, str],
    arg_errors: list[str],
    run_id: str | None = None,
    task_id: str | None = None,
    title: str | None = None,
    steps: list[StepResult] | None = None,
    task_requirements: dict[str, Any] | None = None,
    metrics: dict[str, Any] | None = None,
    risk_summary_rel: str | None = None,
    step_plan: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    summary: dict[str, Any] = {
        "schema_version": "1.1.0",
        "cmd": "sc-acceptance-check",
        "mode": mode,
        "date": today_str(),
        "only": args.only,
        "status": status,
        "out_dir": str(out_dir),
        "subtasks_coverage_mode": subtasks_mode,
        "security_profile": security_profile_payload(security_profile),
        "security_modes": security_modes,
        "arg_validation": {
            "errors": arg_errors,
            "valid": len(arg_errors) == 0,
        },
    }
    if run_id is not None:
        summary["run_id"] = run_id
    if task_id is not None:
        summary["task_id"] = task_id
    if title is not None:
        summary["title"] = title
    if steps is not None:
        summary["steps"] = [s.__dict__ for s in steps]
    if task_requirements:
        summary["task_requirements"] = task_requirements
    if metrics:
        summary["metrics"] = metrics
    if risk_summary_rel:
        summary["risk_summary"] = risk_summary_rel
    if step_plan is not None:
        summary["step_plan"] = step_plan
    return summary


def _run_self_check(args: Any) -> int:
    only_steps = parse_only_steps(args.only)
    subtasks_mode = normalize_subtasks_mode(args.subtasks_coverage)
    security_profile, security_modes = resolve_security_modes(args)
    arg_errors = validate_arg_conflicts(
        only_steps=only_steps,
        subtasks_mode=subtasks_mode,
        require_headless_e2e=bool(args.require_headless_e2e),
        require_executed_refs=bool(args.require_executed_refs),
        audit_evidence_mode=security_modes["audit_evidence"],
    )
    out_dir = ci_dir("sc-acceptance-self-check")
    summary = _build_summary(
        mode="self-check",
        status="fail" if arg_errors else "ok",
        out_dir=out_dir,
        args=args,
        subtasks_mode=subtasks_mode,
        security_profile=security_profile,
        security_modes=security_modes,
        arg_errors=arg_errors,
    )
    write_json(out_dir / "summary.json", summary)
    for err in arg_errors:
        print(f"[sc-acceptance-check] ERROR: {err}")
    print(f"SC_ACCEPTANCE_SELF_CHECK status={summary['status']} out={out_dir}")
    return 0 if not arg_errors else 2


def main() -> int:
    args = build_parser().parse_args()
    if bool(getattr(args, "self_check", False)):
        return _run_self_check(args)
    task_id = parse_task_id(args.task_id)

    try:
        triplet = resolve_triplet(task_id=task_id)
    except Exception as exc:  # noqa: BLE001
        print(f"[sc-acceptance-check] ERROR: failed to resolve task: {exc}")
        return 2

    out_dir = ci_dir(f"sc-acceptance-check-task-{triplet.task_id}") if bool(args.out_per_task) else ci_dir("sc-acceptance-check")
    only_steps = parse_only_steps(args.only)
    subtasks_mode = normalize_subtasks_mode(args.subtasks_coverage)

    has_gd_refs = task_requires_headless_e2e(triplet)
    needs_env_preflight = task_requires_env_evidence_preflight(triplet)
    require_headless_e2e = bool(args.require_headless_e2e) and has_gd_refs
    require_executed_refs = bool(args.require_executed_refs)

    security_profile, security_modes = resolve_security_modes(args)
    audit_evidence_mode = security_modes["audit_evidence"]
    perf_p95_ms = compute_perf_p95_ms(perf_p95_ms=args.perf_p95_ms, require_perf=bool(args.require_perf))

    arg_errors = validate_arg_conflicts(
        only_steps=only_steps,
        subtasks_mode=subtasks_mode,
        require_headless_e2e=bool(args.require_headless_e2e),
        require_executed_refs=require_executed_refs,
        audit_evidence_mode=audit_evidence_mode,
    )
    if arg_errors:
        for e in arg_errors:
            print(f"[sc-acceptance-check] ERROR: {e}")
        return 2

    run_id = uuid.uuid4().hex
    godot_bin = args.godot_bin or os.environ.get("GODOT_BIN")

    if bool(getattr(args, "dry_run_plan", False)):
        out_dir = ci_dir(f"sc-acceptance-dry-plan-task-{triplet.task_id}") if bool(args.out_per_task) else ci_dir("sc-acceptance-dry-plan")
        step_plan = build_step_plan(
            only_steps=only_steps,
            subtasks_mode=subtasks_mode,
            security_modes=security_modes,
            has_gd_refs=has_gd_refs,
            needs_env_preflight=needs_env_preflight,
            require_headless_e2e=require_headless_e2e,
            require_executed_refs=require_executed_refs,
            audit_evidence_mode=audit_evidence_mode,
            perf_p95_ms=perf_p95_ms,
        )
        summary = _build_summary(
            mode="dry-run-plan",
            status="ok",
            out_dir=out_dir,
            args=args,
            subtasks_mode=subtasks_mode,
            security_profile=security_profile,
            security_modes=security_modes,
            arg_errors=arg_errors,
            run_id=run_id,
            task_id=str(triplet.task_id),
            title=str(triplet.master.get("title") or ""),
            task_requirements={
                "has_gd_refs": has_gd_refs,
                "requires_env_evidence_preflight": needs_env_preflight,
            },
            step_plan=step_plan,
        )
        write_json(out_dir / "summary.json", summary)
        print(f"SC_ACCEPTANCE_DRY_RUN_PLAN status={summary['status']} out={out_dir}")
        return 0

    steps = run_registry_steps(
        out_dir=out_dir,
        triplet=triplet,
        args=args,
        only_steps=only_steps,
        subtasks_mode=subtasks_mode,
        security_modes=security_modes,
        needs_env_preflight=needs_env_preflight,
        godot_bin=godot_bin,
    )
    steps.extend(
        run_tests_bundle(
            out_dir=out_dir,
            triplet=triplet,
            only_steps=only_steps,
            has_gd_refs=has_gd_refs,
            require_headless_e2e=require_headless_e2e,
            require_executed_refs=require_executed_refs,
            audit_evidence_mode=audit_evidence_mode,
            godot_bin=godot_bin,
            run_id=run_id,
        )
    )

    if is_enabled(only_steps, "perf"):
        steps.append(step_perf_budget(out_dir, max_p95_ms=perf_p95_ms))

    hard_failed = any(
        should_mark_hard_failure(step_name=s.name, status=s.status, subtasks_mode=subtasks_mode)
        for s in steps
    )
    metrics = _collect_metrics(steps)

    risk_summary_rel: str | None = None
    if is_enabled(only_steps, "risk"):
        hard_failed, risk_summary_rel = _append_risk_summary(
            out_dir=out_dir,
            triplet=triplet,
            run_id=run_id,
            hard_failed=hard_failed,
            steps=steps,
            metrics=metrics,
        )

    summary = _build_summary(
        mode="run",
        status="fail" if hard_failed else "ok",
        out_dir=out_dir,
        args=args,
        subtasks_mode=subtasks_mode,
        security_profile=security_profile,
        security_modes=security_modes,
        arg_errors=arg_errors,
        run_id=run_id,
        task_id=str(triplet.task_id),
        title=str(triplet.master.get("title") or ""),
        steps=steps,
        task_requirements={
            "has_gd_refs": has_gd_refs,
            "requires_env_evidence_preflight": needs_env_preflight,
        },
        metrics=metrics,
        risk_summary_rel=risk_summary_rel,
    )

    write_json(out_dir / "summary.json", summary)
    write_markdown_report(out_dir, triplet, steps, metrics=metrics or None)
    print(f"SC_ACCEPTANCE status={summary['status']} out={out_dir}")
    return 0 if not hard_failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
