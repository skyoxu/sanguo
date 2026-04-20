#!/usr/bin/env python3
"""Command builders shared by dev_cli entrypoints."""

from __future__ import annotations


DEFAULT_GATE_BUNDLE_TASK_FILES = [
    ".taskmaster/tasks/tasks_back.json",
    ".taskmaster/tasks/tasks_gameplay.json",
]


def build_gate_bundle_hard_cmd(
    *,
    delivery_profile: str,
    task_files: list[str],
    out_dir: str,
    run_id: str,
) -> list[str]:
    cmd = [
        "py",
        "-3",
        "scripts/python/run_gate_bundle.py",
        "--mode",
        "hard",
        "--task-files",
        *task_files,
    ]
    if delivery_profile:
        cmd += ["--delivery-profile", delivery_profile]
    if run_id:
        cmd += ["--run-id", run_id]
    if out_dir:
        cmd += ["--out-dir", out_dir]
    return cmd


def build_legacy_ci_pipeline_cmd(
    *,
    solution: str,
    configuration: str,
    godot_bin: str,
) -> list[str]:
    return [
        "py",
        "-3",
        "scripts/python/ci_pipeline.py",
        "all",
        "--solution",
        solution,
        "--configuration",
        configuration,
        "--godot-bin",
        godot_bin,
        "--build-solutions",
    ]


def build_run_dotnet_cmd(*, solution: str, configuration: str) -> list[str]:
    return [
        "py",
        "-3",
        "scripts/python/run_dotnet.py",
        "--solution",
        solution,
        "--configuration",
        configuration,
    ]


def build_quality_gates_cmd(
    *,
    solution: str,
    configuration: str,
    build_solutions: bool,
    godot_bin: str,
    delivery_profile: str,
    task_files: list[str],
    out_dir: str,
    run_id: str,
    gdunit_hard: bool,
    smoke: bool,
) -> list[str]:
    cmd = [
        "py",
        "-3",
        "scripts/python/quality_gates.py",
        "all",
    ]
    if solution:
        cmd += ["--solution", solution]
    if configuration:
        cmd += ["--configuration", configuration]
    if build_solutions:
        cmd.append("--build-solutions")
    if godot_bin:
        cmd += ["--godot-bin", godot_bin]
    if delivery_profile:
        cmd += ["--delivery-profile", delivery_profile]
    for item in task_files:
        cmd += ["--task-file", item]
    if out_dir:
        cmd += ["--out-dir", out_dir]
    if run_id:
        cmd += ["--run-id", run_id]
    if gdunit_hard:
        cmd.append("--gdunit-hard")
    if smoke:
        cmd.append("--smoke")
    return cmd


def build_run_gdunit_hard_cmd(*, godot_bin: str, report_dir: str) -> list[str]:
    return [
        "py",
        "-3",
        "scripts/python/run_gdunit.py",
        "--prewarm",
        "--godot-bin",
        godot_bin,
        "--project",
        "Tests.Godot",
        "--add",
        "tests/Adapters/Config",
        "--add",
        "tests/Security/Hard",
        "--timeout-sec",
        "300",
        "--rd",
        report_dir,
    ]


def build_run_gdunit_full_cmd(*, godot_bin: str) -> list[str]:
    return [
        "py",
        "-3",
        "scripts/python/run_gdunit.py",
        "--prewarm",
        "--godot-bin",
        godot_bin,
        "--project",
        "Tests.Godot",
        "--add",
        "tests/Adapters",
        "--add",
        "tests/Security/Hard",
        "--add",
        "tests/Integration",
        "--add",
        "tests/UI",
        "--timeout-sec",
        "600",
        "--rd",
        "logs/e2e/dev-cli/gdunit-full",
    ]


def build_preflight_cmd(*, test_project: str, configuration: str) -> list[str]:
    return [
        "py",
        "-3",
        "scripts/python/preflight.py",
        "--test-project",
        test_project,
        "--configuration",
        configuration,
    ]


def build_smoke_strict_cmd(*, godot_bin: str, timeout_sec: int) -> list[str]:
    return [
        "py",
        "-3",
        "scripts/python/smoke_headless.py",
        "--godot-bin",
        godot_bin,
        "--project-path",
        ".",
        "--scene",
        "res://Game.Godot/Scenes/Main.tscn",
        "--timeout-sec",
        str(timeout_sec),
        "--strict",
    ]


def build_run_prototype_tdd_cmd(args) -> list[str]:
    cmd = [
        "py",
        "-3",
        "scripts/python/run_prototype_tdd.py",
        "--slug",
        args.slug,
        "--stage",
        args.stage,
    ]
    if args.expect:
        cmd += ["--expect", args.expect]
    if args.prototype_dir:
        cmd += ["--prototype-dir", args.prototype_dir]
    if args.record_path:
        cmd += ["--record-path", args.record_path]
    if args.skip_record:
        cmd.append("--skip-record")
    if args.owner:
        cmd += ["--owner", args.owner]
    for item in args.related_task_id:
        cmd += ["--related-task-id", item]
    if args.hypothesis:
        cmd += ["--hypothesis", args.hypothesis]
    for item in args.scope_in:
        cmd += ["--scope-in", item]
    for item in args.scope_out:
        cmd += ["--scope-out", item]
    for item in args.success_criteria:
        cmd += ["--success-criteria", item]
    for item in args.evidence:
        cmd += ["--evidence", item]
    if args.next_step:
        cmd += ["--next-step", args.next_step]
    if args.create_record_only:
        cmd.append("--create-record-only")
    for item in args.dotnet_target:
        cmd += ["--dotnet-target", item]
    if args.filter:
        cmd += ["--filter", args.filter]
    if args.configuration:
        cmd += ["--configuration", args.configuration]
    if args.godot_bin:
        cmd += ["--godot-bin", args.godot_bin]
    for item in args.gdunit_path:
        cmd += ["--gdunit-path", item]
    if args.timeout_sec:
        cmd += ["--timeout-sec", str(args.timeout_sec)]
    if args.out_dir:
        cmd += ["--out-dir", args.out_dir]
    return cmd


def build_new_execution_plan_cmd(args) -> list[str]:
    cmd = [
        "py",
        "-3",
        "scripts/python/new_execution_plan.py",
        "--title",
        args.title,
    ]
    if args.status:
        cmd += ["--status", args.status]
    if args.goal:
        cmd += ["--goal", args.goal]
    if args.scope:
        cmd += ["--scope", args.scope]
    if args.current_step:
        cmd += ["--current-step", args.current_step]
    if args.stop_loss:
        cmd += ["--stop-loss", args.stop_loss]
    if args.next_action:
        cmd += ["--next-action", args.next_action]
    if args.exit_criteria:
        cmd += ["--exit-criteria", args.exit_criteria]
    for item in args.adr:
        cmd += ["--adr", item]
    for item in args.decision_log:
        cmd += ["--decision-log", item]
    if args.task_id:
        cmd += ["--task-id", args.task_id]
    if args.run_id:
        cmd += ["--run-id", args.run_id]
    if args.latest_json:
        cmd += ["--latest-json", args.latest_json]
    if args.output:
        cmd += ["--output", args.output]
    return cmd


def build_new_decision_log_cmd(args) -> list[str]:
    cmd = [
        "py",
        "-3",
        "scripts/python/new_decision_log.py",
        "--title",
        args.title,
    ]
    if args.status:
        cmd += ["--status", args.status]
    if args.why_now:
        cmd += ["--why-now", args.why_now]
    if args.context:
        cmd += ["--context", args.context]
    if args.decision:
        cmd += ["--decision", args.decision]
    if args.consequences:
        cmd += ["--consequences", args.consequences]
    if args.recovery_impact:
        cmd += ["--recovery-impact", args.recovery_impact]
    if args.validation:
        cmd += ["--validation", args.validation]
    if args.supersedes:
        cmd += ["--supersedes", args.supersedes]
    if args.superseded_by:
        cmd += ["--superseded-by", args.superseded_by]
    for item in args.adr:
        cmd += ["--adr", item]
    for item in args.execution_plan:
        cmd += ["--execution-plan", item]
    if args.task_id:
        cmd += ["--task-id", args.task_id]
    if args.run_id:
        cmd += ["--run-id", args.run_id]
    if args.latest_json:
        cmd += ["--latest-json", args.latest_json]
    if args.output:
        cmd += ["--output", args.output]
    return cmd


def build_resume_task_cmd(args) -> list[str]:
    cmd = [
        "py",
        "-3",
        "scripts/python/resume_task.py",
    ]
    if args.repo_root:
        cmd += ["--repo-root", args.repo_root]
    if args.task_id:
        cmd += ["--task-id", args.task_id]
    if args.run_id:
        cmd += ["--run-id", args.run_id]
    if args.latest:
        cmd += ["--latest", args.latest]
    if args.out_json:
        cmd += ["--out-json", args.out_json]
    if args.out_md:
        cmd += ["--out-md", args.out_md]
    if getattr(args, "recommendation_only", False):
        cmd += ["--recommendation-only"]
    recommendation_format = str(getattr(args, "recommendation_format", "") or "").strip()
    if recommendation_format:
        cmd += ["--recommendation-format", recommendation_format]
    return cmd


def build_inspect_run_cmd(args) -> list[str]:
    cmd = [
        "py",
        "-3",
        "scripts/python/inspect_run.py",
    ]
    if args.repo_root:
        cmd += ["--repo-root", args.repo_root]
    if args.latest:
        cmd += ["--latest", args.latest]
    if args.kind:
        cmd += ["--kind", args.kind]
    if args.task_id:
        cmd += ["--task-id", args.task_id]
    if args.run_id:
        cmd += ["--run-id", args.run_id]
    if args.out_json:
        cmd += ["--out-json", args.out_json]
    if getattr(args, "recommendation_only", False):
        cmd += ["--recommendation-only"]
    recommendation_format = str(getattr(args, "recommendation_format", "") or "").strip()
    if recommendation_format:
        cmd += ["--recommendation-format", recommendation_format]
    return cmd


def build_chapter6_route_cmd(args) -> list[str]:
    cmd = [
        "py",
        "-3",
        "scripts/python/chapter6_route.py",
    ]
    if args.repo_root:
        cmd += ["--repo-root", args.repo_root]
    if args.task_id:
        cmd += ["--task-id", args.task_id]
    if args.run_id:
        cmd += ["--run-id", args.run_id]
    if args.latest:
        cmd += ["--latest", args.latest]
    if getattr(args, "record_residual", False):
        cmd += ["--record-residual"]
    if args.out_json:
        cmd += ["--out-json", args.out_json]
    if args.out_md:
        cmd += ["--out-md", args.out_md]
    if getattr(args, "recommendation_only", False):
        cmd += ["--recommendation-only"]
    recommendation_format = str(getattr(args, "recommendation_format", "") or "").strip()
    if recommendation_format:
        cmd += ["--recommendation-format", recommendation_format]
    return cmd


def build_run_single_task_chapter6_cmd(args) -> list[str]:
    cmd = [
        "py",
        "-3",
        "scripts/python/run_single_task_chapter6_lane.py",
        "--task-id",
        args.task_id,
    ]
    if args.godot_bin:
        cmd += ["--godot-bin", args.godot_bin]
    if args.delivery_profile:
        cmd += ["--delivery-profile", args.delivery_profile]
    if args.security_profile:
        cmd += ["--security-profile", args.security_profile]
    if args.fix_through:
        cmd += ["--fix-through", args.fix_through]
    if args.out_dir:
        cmd += ["--out-dir", args.out_dir]
    if getattr(args, "self_check", False):
        cmd.append("--self-check")
    return cmd


def build_run_chapter7_ui_wiring_cmd(args) -> list[str]:
    cmd = [
        "py",
        "-3",
        "scripts/python/run_chapter7_ui_wiring.py",
    ]
    if getattr(args, 'repo_root', ''):
        cmd += ["--repo-root", args.repo_root]
    if getattr(args, 'delivery_profile', ''):
        cmd += ["--delivery-profile", args.delivery_profile]
    if getattr(args, 'write_doc', False):
        cmd.append("--write-doc")
    if getattr(args, 'out_json', ''):
        cmd += ["--out-json", args.out_json]
    if getattr(args, 'self_check', False):
        cmd.append("--self-check")
    return cmd


def build_detect_project_stage_cmd(args) -> list[str]:
    cmd = [
        "py",
        "-3",
        "scripts/python/detect_project_stage.py",
    ]
    if args.repo_root:
        cmd += ["--repo-root", args.repo_root]
    return cmd


def build_doctor_project_cmd(args) -> list[str]:
    cmd = [
        "py",
        "-3",
        "scripts/python/doctor_project.py",
    ]
    if args.repo_root:
        cmd += ["--repo-root", args.repo_root]
    return cmd


def build_check_directory_boundaries_cmd(args) -> list[str]:
    cmd = [
        "py",
        "-3",
        "scripts/python/check_directory_boundaries.py",
    ]
    if args.repo_root:
        cmd += ["--repo-root", args.repo_root]
    return cmd


def build_project_health_scan_cmd(args) -> list[str]:
    cmd = [
        "py",
        "-3",
        "scripts/python/project_health_scan.py",
    ]
    if args.repo_root:
        cmd += ["--repo-root", args.repo_root]
    if getattr(args, "serve", False):
        cmd.append("--serve")
    port = int(getattr(args, "port", 0) or 0)
    if port > 0:
        cmd += ["--port", str(port)]
    return cmd


def build_serve_project_health_cmd(args) -> list[str]:
    cmd = [
        "py",
        "-3",
        "scripts/python/serve_project_health.py",
    ]
    if args.repo_root:
        cmd += ["--repo-root", args.repo_root]
    port = int(getattr(args, "port", 0) or 0)
    if port > 0:
        cmd += ["--port", str(port)]
    return cmd
