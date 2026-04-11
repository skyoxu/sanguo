#!/usr/bin/env python3
"""Developer CLI entry for the Godot+C# template.

This script provides stable subcommands that other tools (BMAD,
task-master-ai, Claude Code, Codex.CLI) can call instead of
reconstructing long Python/PowerShell commands.

All output messages are in English to keep logs uniform.
"""

from __future__ import annotations

import argparse
import datetime as dt
import subprocess
import sys
from pathlib import Path

from dev_cli_builders import (
    DEFAULT_GATE_BUNDLE_TASK_FILES,
    build_check_directory_boundaries_cmd,
    build_detect_project_stage_cmd,
    build_doctor_project_cmd,
    build_gate_bundle_hard_cmd,
    build_legacy_ci_pipeline_cmd,
    build_new_decision_log_cmd,
    build_new_execution_plan_cmd,
    build_inspect_run_cmd,
    build_chapter6_route_cmd,
    build_preflight_cmd,
    build_project_health_scan_cmd,
    build_resume_task_cmd,
    build_run_single_task_chapter6_cmd,
    build_quality_gates_cmd,
    build_run_dotnet_cmd,
    build_run_gdunit_full_cmd,
    build_run_gdunit_hard_cmd,
    build_serve_project_health_cmd,
    build_smoke_strict_cmd,
)
from local_hard_checks_harness import run_local_hard_checks
from solution_resolver import resolve_solution_path, resolve_test_solution_path


def run(cmd: list[str]) -> int:
    """Run a subprocess and return its exit code."""

    print(f"[dev_cli] running: {' '.join(cmd)}")
    proc = subprocess.run(cmd, text=True)
    return proc.returncode


def cmd_run_ci_basic(args: argparse.Namespace) -> int:
    """Run hard gate bundle, with optional legacy preflight appended."""

    task_files = list(args.task_file or DEFAULT_GATE_BUNDLE_TASK_FILES)
    gate_cmd = build_gate_bundle_hard_cmd(
        delivery_profile=args.delivery_profile,
        task_files=task_files,
        out_dir=args.out_dir,
        run_id=args.run_id,
    )

    rc = run(gate_cmd)
    if rc != 0 or not args.legacy_preflight:
        return rc

    if not args.godot_bin:
        print("[dev_cli] error: --godot-bin is required when --legacy-preflight is enabled", file=sys.stderr)
        return 2

    solution = resolve_test_solution_path(args.solution)
    return run(
        build_legacy_ci_pipeline_cmd(
            solution=solution,
            configuration=args.configuration,
            godot_bin=args.godot_bin,
        )
    )


def cmd_run_quality_gates(args: argparse.Namespace) -> int:
    """Run quality_gates.py all with optional hard GdUnit and smoke."""

    solution = resolve_test_solution_path(args.solution)
    return run(
        build_quality_gates_cmd(
            solution=solution,
            configuration=args.configuration,
            build_solutions=bool(args.build_solutions),
            godot_bin=args.godot_bin,
            delivery_profile=args.delivery_profile,
            task_files=list(args.task_file or []),
            out_dir=args.out_dir,
            run_id=args.run_id,
            gdunit_hard=bool(args.gdunit_hard),
            smoke=bool(args.smoke),
        )
    )


def cmd_run_gdunit_hard(args: argparse.Namespace) -> int:
    """Run hard GdUnit set (Adapters/Config + Security)."""

    return run(build_run_gdunit_hard_cmd(godot_bin=args.godot_bin, report_dir="logs/e2e/dev-cli/gdunit-hard"))


def cmd_run_gdunit_full(args: argparse.Namespace) -> int:
    """Run a broad GdUnit set (Adapters + Security + Integration + UI)."""

    return run(build_run_gdunit_full_cmd(godot_bin=args.godot_bin))


def cmd_run_preflight(args: argparse.Namespace) -> int:
    """Run local pre-flight checks (dotnet --info + core tests)."""

    return run(build_preflight_cmd(test_project=args.test_project, configuration=args.configuration))


def _acceptance_preflight_out_dir(task_id: str, stage: str, out_dir: str) -> Path:
    """Resolve the output directory for acceptance preflight artifacts."""

    if str(out_dir or "").strip():
        return Path(out_dir)
    task_label = f"task-{task_id}" if str(task_id or "").strip() else "task-current"
    return Path("logs") / "ci" / dt.date.today().isoformat() / f"acceptance-preflight-{task_label}-{stage}"


def _build_acceptance_preflight_cmd(script_name: str, *, task_id: str, stage: str, out_path: Path) -> list[str]:
    """Build one acceptance preflight command."""

    cmd = [
        "py",
        "-3",
        f"scripts/python/{script_name}",
        "--stage",
        stage,
        "--out",
        str(out_path).replace("\\", "/"),
    ]
    if str(task_id or "").strip():
        cmd.extend(["--task-id", str(task_id)])
    return cmd


def cmd_run_acceptance_preflight(args: argparse.Namespace) -> int:
    """Run the lightweight acceptance refs + anchors preflight."""

    out_dir = _acceptance_preflight_out_dir(task_id=args.task_id, stage=args.stage, out_dir=args.out_dir)
    refs_cmd = _build_acceptance_preflight_cmd(
        "validate_acceptance_refs.py",
        task_id=args.task_id,
        stage=args.stage,
        out_path=out_dir / "acceptance-refs.json",
    )
    refs_rc = run(refs_cmd)
    if refs_rc != 0:
        return refs_rc

    anchors_cmd = _build_acceptance_preflight_cmd(
        "validate_acceptance_anchors.py",
        task_id=args.task_id,
        stage=args.stage,
        out_path=out_dir / "acceptance-anchors.json",
    )
    return run(anchors_cmd)


def cmd_run_local_hard_checks(args: argparse.Namespace) -> int:
    """Run local hard checks via the protocolized harness wrapper."""

    task_files = list(args.task_file or DEFAULT_GATE_BUNDLE_TASK_FILES)
    solution = resolve_test_solution_path(args.solution)
    return run_local_hard_checks(
        solution=solution,
        configuration=args.configuration,
        godot_bin=args.godot_bin,
        delivery_profile=args.delivery_profile,
        task_files=task_files,
        out_dir=args.out_dir,
        run_id=args.run_id,
        timeout_sec=args.timeout_sec,
        run_fn=run,
    )


def cmd_run_local_hard_checks_preflight(args: argparse.Namespace) -> int:
    """Run the lightweight 6.9 preflight: gate bundle + dotnet only."""

    task_files = list(args.task_file or DEFAULT_GATE_BUNDLE_TASK_FILES)
    gate_rc = run(
        build_gate_bundle_hard_cmd(
            delivery_profile=args.delivery_profile,
            task_files=task_files,
            out_dir=args.out_dir,
            run_id=args.run_id,
        )
    )
    if gate_rc != 0:
        return gate_rc

    solution = resolve_test_solution_path(args.solution)
    return run(build_run_dotnet_cmd(solution=solution, configuration=args.configuration))


def cmd_run_smoke_strict(args: argparse.Namespace) -> int:
    """Run strict headless smoke against Main scene."""

    return run(build_smoke_strict_cmd(godot_bin=args.godot_bin, timeout_sec=args.timeout_sec))


def cmd_new_execution_plan(args: argparse.Namespace) -> int:
    """Create a new execution plan scaffold."""

    return run(build_new_execution_plan_cmd(args))


def cmd_new_decision_log(args: argparse.Namespace) -> int:
    """Create a new decision log scaffold."""

    return run(build_new_decision_log_cmd(args))


def cmd_resume_task(args: argparse.Namespace) -> int:
    """Build a task-scoped recovery summary from the latest artifacts."""

    return run(build_resume_task_cmd(args))


def cmd_inspect_run(args: argparse.Namespace) -> int:
    """Inspect the latest local harness run and emit a recovery summary."""

    return run(build_inspect_run_cmd(args))


def cmd_chapter6_route(args: argparse.Namespace) -> int:
    """Route Chapter 6 rerun/stop-loss decisions through the stable recovery entrypoint."""

    return run(build_chapter6_route_cmd(args))


def cmd_run_single_task_chapter6(args: argparse.Namespace) -> int:
    """Run the Chapter 6 single-task orchestrator."""

    return run(build_run_single_task_chapter6_cmd(args))


def cmd_detect_project_stage(args: argparse.Namespace) -> int:
    """Detect the current repo stage and refresh project-health artifacts."""

    return run(build_detect_project_stage_cmd(args))


def cmd_doctor_project(args: argparse.Namespace) -> int:
    """Run project doctor checks and refresh project-health artifacts."""

    return run(build_doctor_project_cmd(args))


def cmd_check_directory_boundaries(args: argparse.Namespace) -> int:
    """Run deterministic directory responsibility checks."""

    return run(build_check_directory_boundaries_cmd(args))


def cmd_project_health_scan(args: argparse.Namespace) -> int:
    """Run the full project-health scan and refresh the dashboard."""

    return run(build_project_health_scan_cmd(args))


def cmd_serve_project_health(args: argparse.Namespace) -> int:
    """Serve the local project-health dashboard on 127.0.0.1."""

    return run(build_serve_project_health_cmd(args))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Dev CLI for Godot+C# template (AI-friendly entrypoint)",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    # run-ci-basic
    p_ci = sub.add_parser(
        "run-ci-basic",
        help="run hard gate bundle first; optionally append legacy ci_pipeline preflight",
    )
    p_ci.add_argument("--solution", default="auto")
    p_ci.add_argument("--configuration", default="Debug")
    p_ci.add_argument("--godot-bin", default="")
    p_ci.add_argument("--delivery-profile", default="")
    p_ci.add_argument("--task-file", action="append", default=[])
    p_ci.add_argument("--out-dir", default="")
    p_ci.add_argument("--run-id", default="")
    p_ci.add_argument("--legacy-preflight", action="store_true")
    p_ci.set_defaults(func=cmd_run_ci_basic)

    # run-quality-gates
    p_qg = sub.add_parser("run-quality-gates", help="run quality_gates.py all with optional GdUnit hard and smoke")
    p_qg.add_argument("--solution", default="auto")
    p_qg.add_argument("--configuration", default="Debug")
    p_qg.add_argument("--build-solutions", action="store_true")
    p_qg.add_argument("--godot-bin", default="")
    p_qg.add_argument("--delivery-profile", default="")
    p_qg.add_argument("--task-file", action="append", default=[])
    p_qg.add_argument("--out-dir", default="")
    p_qg.add_argument("--run-id", default="")
    p_qg.add_argument("--gdunit-hard", action="store_true")
    p_qg.add_argument("--smoke", action="store_true")
    p_qg.set_defaults(func=cmd_run_quality_gates)

    # run-local-hard-checks
    p_lh = sub.add_parser(
        "run-local-hard-checks",
        help="run gate bundle hard + run_dotnet, and append gdunit/smoke when --godot-bin is provided",
    )
    p_lh.add_argument("--solution", default="auto")
    p_lh.add_argument("--configuration", default="Debug")
    p_lh.add_argument("--godot-bin", default="")
    p_lh.add_argument("--delivery-profile", default="")
    p_lh.add_argument("--task-file", action="append", default=[])
    p_lh.add_argument("--out-dir", default="")
    p_lh.add_argument("--run-id", default="")
    p_lh.add_argument("--timeout-sec", type=int, default=5)
    p_lh.set_defaults(func=cmd_run_local_hard_checks)

    # run-local-hard-checks-preflight
    p_lhp = sub.add_parser(
        "run-local-hard-checks-preflight",
        help="run only gate bundle hard + run_dotnet before the full local-hard-checks harness",
    )
    p_lhp.add_argument("--solution", default="auto")
    p_lhp.add_argument("--configuration", default="Debug")
    p_lhp.add_argument("--delivery-profile", default="")
    p_lhp.add_argument("--task-file", action="append", default=[])
    p_lhp.add_argument("--out-dir", default="")
    p_lhp.add_argument("--run-id", default="")
    p_lhp.set_defaults(func=cmd_run_local_hard_checks_preflight)

    # run-gdunit-hard
    p_gh = sub.add_parser("run-gdunit-hard", help="run hard GdUnit set (Adapters/Config + Security)")
    p_gh.add_argument("--godot-bin", required=True)
    p_gh.set_defaults(func=cmd_run_gdunit_hard)

    # run-gdunit-full
    p_gf = sub.add_parser("run-gdunit-full", help="run broad GdUnit tests (Adapters+Security+Integration+UI)")
    p_gf.add_argument("--godot-bin", required=True)
    p_gf.set_defaults(func=cmd_run_gdunit_full)

    # run-preflight
    p_pf = sub.add_parser("run-preflight", help="run local pre-flight checks (dotnet --info + core tests)")
    p_pf.add_argument("--test-project", default="Game.Core.Tests/Game.Core.Tests.csproj")
    p_pf.add_argument("--configuration", default="Debug")
    p_pf.set_defaults(func=cmd_run_preflight)

    # run-acceptance-preflight
    p_ap = sub.add_parser(
        "run-acceptance-preflight",
        help="run validate_acceptance_refs + validate_acceptance_anchors as one lightweight task preflight",
    )
    p_ap.add_argument("--task-id", default="")
    p_ap.add_argument("--stage", default="refactor", choices=["red", "green", "refactor"])
    p_ap.add_argument("--out-dir", default="")
    p_ap.set_defaults(func=cmd_run_acceptance_preflight)

    # run-smoke-strict
    p_sm = sub.add_parser("run-smoke-strict", help="run strict headless smoke against Main scene")
    p_sm.add_argument("--godot-bin", required=True)
    p_sm.add_argument("--timeout-sec", type=int, default=5)
    p_sm.set_defaults(func=cmd_run_smoke_strict)

    # new-execution-plan
    p_ep = sub.add_parser("new-execution-plan", help="create an execution plan scaffold")
    p_ep.add_argument("--title", required=True)
    p_ep.add_argument("--status", default="active", choices=["active", "paused", "done", "blocked"])
    p_ep.add_argument("--goal", default="TODO: describe goal")
    p_ep.add_argument("--scope", default="TODO: define scope")
    p_ep.add_argument("--current-step", default="TODO: define current step")
    p_ep.add_argument("--stop-loss", default="TODO: define stop-loss boundary")
    p_ep.add_argument("--next-action", default="TODO: define next action")
    p_ep.add_argument("--exit-criteria", default="TODO: define exit criteria")
    p_ep.add_argument("--adr", action="append", default=[])
    p_ep.add_argument("--decision-log", action="append", default=[])
    p_ep.add_argument("--task-id", default="")
    p_ep.add_argument("--run-id", default="")
    p_ep.add_argument("--latest-json", default="")
    p_ep.add_argument("--output", default="")
    p_ep.set_defaults(func=cmd_new_execution_plan)

    # new-decision-log
    p_dl = sub.add_parser("new-decision-log", help="create a decision log scaffold")
    p_dl.add_argument("--title", required=True)
    p_dl.add_argument("--status", default="proposed", choices=["proposed", "accepted", "superseded"])
    p_dl.add_argument("--why-now", default="TODO: explain why now")
    p_dl.add_argument("--context", default="TODO: capture context")
    p_dl.add_argument("--decision", default="TODO: record decision")
    p_dl.add_argument("--consequences", default="TODO: describe consequences")
    p_dl.add_argument("--recovery-impact", default="TODO: describe recovery impact")
    p_dl.add_argument("--validation", default="TODO: describe validation")
    p_dl.add_argument("--supersedes", default="none")
    p_dl.add_argument("--superseded-by", default="none")
    p_dl.add_argument("--adr", action="append", default=[])
    p_dl.add_argument("--execution-plan", action="append", default=[])
    p_dl.add_argument("--task-id", default="")
    p_dl.add_argument("--run-id", default="")
    p_dl.add_argument("--latest-json", default="")
    p_dl.add_argument("--output", default="")
    p_dl.set_defaults(func=cmd_new_decision_log)

    # resume-task
    p_rt = sub.add_parser("resume-task", help="build a task-scoped recovery summary from the latest pipeline artifacts")
    p_rt.add_argument("--repo-root", default=".")
    p_rt.add_argument("--task-id", default="")
    p_rt.add_argument("--run-id", default="")
    p_rt.add_argument("--latest", default="")
    p_rt.add_argument("--out-json", default="")
    p_rt.add_argument("--out-md", default="")
    p_rt.add_argument("--recommendation-only", action="store_true")
    p_rt.add_argument("--recommendation-format", default="", choices=["", "kv", "json"])
    p_rt.set_defaults(func=cmd_resume_task)

    # inspect-run
    p_ir = sub.add_parser("inspect-run", help="inspect the latest local harness run and emit a stable recovery summary")
    p_ir.add_argument("--repo-root", default=".")
    p_ir.add_argument("--latest", default="")
    p_ir.add_argument("--kind", default="", choices=["", "pipeline", "local-hard-checks"])
    p_ir.add_argument("--task-id", default="")
    p_ir.add_argument("--run-id", default="")
    p_ir.add_argument("--out-json", default="")
    p_ir.add_argument("--recommendation-only", action="store_true")
    p_ir.add_argument("--recommendation-format", default="", choices=["", "kv", "json"])
    p_ir.set_defaults(func=cmd_inspect_run)

    # chapter6-route
    p_c6 = sub.add_parser("chapter6-route", help="route Chapter 6 recovery decisions through the artifact-aware entrypoint")
    p_c6.add_argument("--repo-root", default=".")
    p_c6.add_argument("--task-id", default="")
    p_c6.add_argument("--run-id", default="")
    p_c6.add_argument("--latest", default="")
    p_c6.add_argument("--record-residual", action="store_true")
    p_c6.add_argument("--out-json", default="")
    p_c6.add_argument("--out-md", default="")
    p_c6.add_argument("--recommendation-only", action="store_true")
    p_c6.add_argument("--recommendation-format", default="", choices=["", "kv", "json"])
    p_c6.set_defaults(func=cmd_chapter6_route)

    # run-single-task-chapter6
    p_ch6 = sub.add_parser(
        "run-single-task-chapter6",
        help="run the Chapter 6 single-task orchestrator with profile-aware defaults",
    )
    p_ch6.add_argument("--task-id", required=True)
    p_ch6.add_argument("--godot-bin", default="")
    p_ch6.add_argument("--delivery-profile", default="")
    p_ch6.add_argument("--security-profile", default="")
    p_ch6.add_argument("--fix-through", default="", choices=["", "P0", "P1", "P2", "P3"])
    p_ch6.add_argument("--out-dir", default="")
    p_ch6.add_argument("--self-check", action="store_true")
    p_ch6.set_defaults(func=cmd_run_single_task_chapter6)

    # detect-project-stage
    p_stage = sub.add_parser("detect-project-stage", help="detect repo stage and refresh project-health artifacts")
    p_stage.add_argument("--repo-root", default=".")
    p_stage.set_defaults(func=cmd_detect_project_stage)

    # doctor-project
    p_doctor = sub.add_parser("doctor-project", help="run repo doctor checks and refresh project-health artifacts")
    p_doctor.add_argument("--repo-root", default=".")
    p_doctor.set_defaults(func=cmd_doctor_project)

    # check-directory-boundaries
    p_boundaries = sub.add_parser(
        "check-directory-boundaries",
        help="run deterministic directory responsibility checks and refresh project-health artifacts",
    )
    p_boundaries.add_argument("--repo-root", default=".")
    p_boundaries.set_defaults(func=cmd_check_directory_boundaries)

    # project-health-scan
    p_scan = sub.add_parser("project-health-scan", help="run all project-health checks and refresh the dashboard")
    p_scan.add_argument("--repo-root", default=".")
    p_scan.add_argument("--serve", action="store_true")
    p_scan.add_argument("--port", type=int, default=0)
    p_scan.set_defaults(func=cmd_project_health_scan)

    # serve-project-health
    p_srv = sub.add_parser("serve-project-health", help="serve the local project-health dashboard on 127.0.0.1")
    p_srv.add_argument("--repo-root", default=".")
    p_srv.add_argument("--port", type=int, default=0)
    p_srv.set_defaults(func=cmd_serve_project_health)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    func = getattr(args, "func", None)
    if func is None:
        parser.print_help()
        return 1
    return func(args)


if __name__ == "__main__":
    sys.exit(main())
