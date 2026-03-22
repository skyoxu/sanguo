from __future__ import annotations

from typing import Any


def build_pipeline_steps(
    *,
    args: Any,
    task_id: str,
    run_id: str,
    delivery_profile: str,
    security_profile: str,
    acceptance_defaults: dict[str, Any],
    llm_agents: str,
    llm_timeout_sec: int,
    llm_agent_timeout_sec: int,
    llm_semantic_gate: str,
    llm_strict: bool,
) -> list[tuple[str, list[str], int, bool]]:
    steps: list[tuple[str, list[str], int, bool]] = []

    test_cmd = ["py", "-3", "scripts/sc/test.py", "--task-id", task_id, "--run-id", run_id, "--delivery-profile", delivery_profile]
    if args.godot_bin:
        test_cmd += ["--godot-bin", str(args.godot_bin)]
    steps.append(("sc-test", test_cmd, 1800, args.skip_test))

    acceptance_cmd = ["py", "-3", "scripts/sc/acceptance_check.py", "--task-id", task_id, "--run-id", run_id, "--out-per-task", "--delivery-profile", delivery_profile, "--security-profile", security_profile]
    if bool(acceptance_defaults.get("strict_adr_status", False)):
        acceptance_cmd.append("--strict-adr-status")
    if bool(acceptance_defaults.get("strict_test_quality", False)):
        acceptance_cmd.append("--strict-test-quality")
    if bool(acceptance_defaults.get("strict_quality_rules", False)):
        acceptance_cmd.append("--strict-quality-rules")
    if bool(acceptance_defaults.get("require_task_test_refs", False)):
        acceptance_cmd.append("--require-task-test-refs")
    if bool(acceptance_defaults.get("require_executed_refs", False)):
        acceptance_cmd.append("--require-executed-refs")
    if bool(acceptance_defaults.get("require_headless_e2e", False)):
        acceptance_cmd.append("--require-headless-e2e")
    subtasks_mode = str(acceptance_defaults.get("subtasks_coverage") or "skip")
    if subtasks_mode in {"warn", "require"}:
        acceptance_cmd += ["--subtasks-coverage", subtasks_mode]
    perf_p95_ms = int(acceptance_defaults.get("perf_p95_ms") or 0)
    if perf_p95_ms > 0:
        acceptance_cmd += ["--perf-p95-ms", str(perf_p95_ms)]
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
        security_profile,
        "--review-profile",
        "bmad-godot",
        "--review-template",
        args.review_template,
        "--semantic-gate",
        llm_semantic_gate,
        "--agents",
        llm_agents,
        "--base",
        args.llm_base,
        "--diff-mode",
        args.llm_diff_mode,
        "--timeout-sec",
        str(llm_timeout_sec),
        "--agent-timeout-sec",
        str(llm_agent_timeout_sec),
    ]
    if not args.llm_no_uncommitted:
        llm_cmd.append("--uncommitted")
    if llm_strict:
        llm_cmd.append("--strict")
    steps.append(("sc-llm-review", llm_cmd, max(300, int(llm_timeout_sec) + 120), args.skip_llm_review))
    return steps
