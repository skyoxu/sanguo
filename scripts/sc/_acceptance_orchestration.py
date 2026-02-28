#!/usr/bin/env python3
"""
Execution planning and orchestration helpers for acceptance_check.
"""

from __future__ import annotations

from typing import Any, Callable

from _acceptance_evidence_steps import (
    step_acceptance_executed_refs,
    step_headless_e2e_evidence,
    step_security_audit_evidence,
)
from _acceptance_steps import (
    StepResult,
    step_acceptance_anchors_validate,
    step_acceptance_refs_validate,
    step_adr_compliance,
    step_architecture_boundary,
    step_build_warnaserror,
    step_contracts_validate,
    step_overlay_validate,
    step_quality_rules,
    step_security_hard,
    step_security_soft,
    step_subtasks_coverage_llm,
    step_task_links_validate,
    step_task_test_refs_validate,
    step_test_quality_soft,
    step_tests_all,
    step_ui_event_security,
)
from _env_evidence_preflight import step_env_evidence_preflight


def is_enabled(only_steps: set[str] | None, key: str) -> bool:
    return True if only_steps is None else (key in only_steps)


def build_step_plan(
    *,
    only_steps: set[str] | None,
    subtasks_mode: str,
    security_modes: dict[str, str],
    has_gd_refs: bool,
    needs_env_preflight: bool,
    require_headless_e2e: bool,
    require_executed_refs: bool,
    audit_evidence_mode: str,
    perf_p95_ms: int,
) -> list[dict[str, Any]]:
    plan: list[dict[str, Any]] = []

    def add(name: str, enabled: bool, gate_level: str, reason: str | None = None) -> None:
        item: dict[str, Any] = {
            "name": name,
            "enabled": enabled,
            "gate_level": gate_level,
        }
        if reason:
            item["reason"] = reason
        plan.append(item)

    tests_enabled = is_enabled(only_steps, "tests")

    add(
        "env-evidence-preflight",
        tests_enabled and needs_env_preflight,
        "hard",
        None if (tests_enabled and needs_env_preflight) else "not_required_or_tests_disabled",
    )

    for group, steps in [
        ("adr", ["adr-compliance"]),
        ("links", ["task-links-validate", "task-test-refs", "acceptance-refs", "acceptance-anchors"]),
        ("overlay", ["validate-task-overlays"]),
        ("contracts", ["validate-contracts"]),
        ("arch", ["architecture-boundary"]),
        ("build", ["dotnet-build-warnaserror"]),
    ]:
        for step_name in steps:
            add(step_name, is_enabled(only_steps, group), "hard", None if is_enabled(only_steps, group) else f"{group}_disabled")

    if is_enabled(only_steps, "subtasks"):
        gate_level = "hard" if subtasks_mode == "require" else "soft"
        add("subtasks-coverage", True, gate_level, None if subtasks_mode != "skip" else "subtasks_coverage_skip")
    else:
        add("subtasks-coverage", False, "soft", "subtasks_disabled")

    add("test-quality", is_enabled(only_steps, "quality"), "soft", None if is_enabled(only_steps, "quality") else "quality_disabled")
    add("quality-rules", is_enabled(only_steps, "rules"), "soft", None if is_enabled(only_steps, "rules") else "rules_disabled")

    security_enabled = is_enabled(only_steps, "security")
    add("security-hard", security_enabled, "hard", None if security_enabled else "security_disabled")
    ui_gate = "hard" if ("require" in (security_modes["ui_event_json_guards"], security_modes["ui_event_source_verify"])) else "soft"
    add("ui-event-security", security_enabled, ui_gate, None if security_enabled else "security_disabled")
    add("security-soft", security_enabled, "soft", None if security_enabled else "security_disabled")

    test_type = "all" if has_gd_refs else "unit"
    add("tests-all", tests_enabled, "hard", None if tests_enabled else "tests_disabled")
    add(
        "headless-e2e-evidence",
        tests_enabled and require_headless_e2e,
        "hard",
        None if (tests_enabled and require_headless_e2e) else ("not_required" if tests_enabled else "tests_disabled"),
    )
    add(
        "acceptance-executed-refs",
        tests_enabled and require_executed_refs,
        "hard",
        None if (tests_enabled and require_executed_refs) else ("not_required" if tests_enabled else "tests_disabled"),
    )

    audit_gate = "hard" if audit_evidence_mode == "require" else "soft"
    add(
        "security-audit-executed-evidence",
        tests_enabled and audit_evidence_mode in ("warn", "require"),
        audit_gate,
        None if (tests_enabled and audit_evidence_mode in ("warn", "require")) else ("not_required" if tests_enabled else "tests_disabled"),
    )

    perf_enabled = is_enabled(only_steps, "perf")
    add("perf-budget", perf_enabled, "hard" if perf_p95_ms > 0 else "soft", None if perf_enabled else "perf_disabled")
    add("risk-summary", is_enabled(only_steps, "risk"), "hard", None if is_enabled(only_steps, "risk") else "risk_disabled")

    for item in plan:
        if item["name"] == "tests-all":
            item["test_type"] = test_type
    return plan


def run_registry_steps(
    *,
    out_dir: Any,
    triplet: Any,
    args: Any,
    only_steps: set[str] | None,
    subtasks_mode: str,
    security_modes: dict[str, str],
    needs_env_preflight: bool,
    godot_bin: str | None,
) -> list[StepResult]:
    steps: list[StepResult] = []

    if is_enabled(only_steps, "tests") and needs_env_preflight:
        steps.append(step_env_evidence_preflight(out_dir, godot_bin=godot_bin, task_id=str(triplet.task_id)))

    handlers: list[tuple[str, Callable[[], list[StepResult]]]] = [
        ("adr", lambda: [step_adr_compliance(out_dir, triplet, strict_status=bool(args.strict_adr_status))]),
        (
            "links",
            lambda: [
                step_task_links_validate(out_dir),
                step_task_test_refs_validate(out_dir, triplet, require_non_empty=bool(args.require_task_test_refs)),
                step_acceptance_refs_validate(out_dir, triplet),
                step_acceptance_anchors_validate(out_dir, triplet),
            ],
        ),
        (
            "subtasks",
            lambda: [StepResult(name="subtasks-coverage", status="skipped", rc=0, details={"reason": "subtasks_coverage_skip"})]
            if subtasks_mode == "skip"
            else [step_subtasks_coverage_llm(out_dir, triplet, timeout_sec=int(args.subtasks_timeout_sec))],
        ),
        ("overlay", lambda: [step_overlay_validate(out_dir, triplet)]),
        ("contracts", lambda: [step_contracts_validate(out_dir)]),
        ("arch", lambda: [step_architecture_boundary(out_dir)]),
        ("build", lambda: [step_build_warnaserror(out_dir)]),
        ("quality", lambda: [step_test_quality_soft(out_dir, triplet, strict=bool(args.strict_test_quality))]),
        ("rules", lambda: [step_quality_rules(out_dir, strict=bool(args.strict_quality_rules))]),
        (
            "security",
            lambda: [
                step_security_hard(
                    out_dir,
                    path_mode=security_modes["path"],
                    sql_mode=security_modes["sql"],
                    audit_schema_mode=security_modes["audit_schema"],
                ),
                step_ui_event_security(
                    out_dir,
                    json_mode=security_modes["ui_event_json_guards"],
                    source_mode=security_modes["ui_event_source_verify"],
                ),
                step_security_soft(out_dir),
            ],
        ),
    ]

    for key, run in handlers:
        if is_enabled(only_steps, key):
            steps.extend(run())
    return steps


def run_tests_bundle(
    *,
    out_dir: Any,
    triplet: Any,
    only_steps: set[str] | None,
    has_gd_refs: bool,
    require_headless_e2e: bool,
    require_executed_refs: bool,
    audit_evidence_mode: str,
    godot_bin: str | None,
    run_id: str,
) -> list[StepResult]:
    steps: list[StepResult] = []
    if not is_enabled(only_steps, "tests"):
        return steps

    test_type = "all" if has_gd_refs else "unit"
    if test_type != "unit" and not godot_bin:
        steps.append(StepResult(name="tests-all", status="fail", rc=2, details={"error": "missing_godot_bin", "hint": "set --godot-bin or env GODOT_BIN"}))
        return steps

    steps.append(step_tests_all(out_dir, godot_bin, run_id=run_id, test_type=test_type, task_id=str(triplet.task_id)))

    if require_headless_e2e:
        steps.append(step_headless_e2e_evidence(out_dir, expected_run_id=run_id))
    if require_executed_refs:
        steps.append(step_acceptance_executed_refs(out_dir, task_id=int(triplet.task_id), expected_run_id=run_id))

    if audit_evidence_mode in ("warn", "require"):
        audit_step = step_security_audit_evidence(out_dir, expected_run_id=run_id)
        if audit_evidence_mode == "warn" and audit_step.status != "ok":
            steps.append(StepResult(name="security-audit-executed-evidence", status="ok", rc=0, details={"mode": "warn", "reason": "audit_evidence_missing"}))
        else:
            steps.append(audit_step)
    return steps
