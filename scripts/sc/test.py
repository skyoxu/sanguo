#!/usr/bin/env python3
"""
sc-test: Repo-specific test shim (Godot+C# template).

This script maps SuperClaude `/sc:test` into repository-native test entrypoints:
- unit: dotnet test + coverage via scripts/python/run_dotnet.py
- e2e: Godot headless tests via scripts/python/run_gdunit.py + smoke_headless.py

Usage (Windows):
  py -3 scripts/sc/test.py --type unit
  py -3 scripts/sc/test.py --type e2e --godot-bin \"C:\\Godot\\Godot_v4.5.1-stable_mono_win64_console.exe\"
  py -3 scripts/sc/test.py --type all --godot-bin \"%GODOT_BIN%\"
"""

from __future__ import annotations

import argparse
import os
import uuid
from pathlib import Path
from typing import Any

from _delivery_profile import default_security_profile_for_delivery, known_delivery_profiles, profile_test_defaults, resolve_delivery_profile
from _sc_test_refs import (
    build_dotnet_filter_from_cs_refs as _build_dotnet_filter_from_cs_refs_impl,
    normalize_task_root_id as _normalize_task_root_id_impl,
    task_scoped_cs_refs as _task_scoped_cs_refs_impl,
    task_scoped_gdunit_refs as _task_scoped_gdunit_refs_impl,
)
from _sc_test_steps import (
    run_csharp_test_conventions as _run_csharp_test_conventions_impl,
    run_coverage_report as _run_coverage_report_impl,
    run_gdunit_hard as _run_gdunit_hard_impl,
    run_smoke as _run_smoke_impl,
    run_unit as _run_unit_impl,
)
from _security_profile import resolve_security_profile
from _summary_schema import SummarySchemaError, validate_sc_test_summary
from _util import ci_dir, repo_root, today_str, write_json, write_text


DELIVERY_PROFILE_CHOICES = tuple(sorted(known_delivery_profiles()))


def resolve_test_runtime(*, delivery_profile: str | None, security_profile: str | None, no_coverage_gate: bool) -> dict[str, Any]:
    resolved_delivery_profile = resolve_delivery_profile(delivery_profile)
    resolved_security_profile = resolve_security_profile(
        security_profile or default_security_profile_for_delivery(resolved_delivery_profile)
    )
    defaults = profile_test_defaults(resolved_delivery_profile)
    return {
        "delivery_profile": resolved_delivery_profile,
        "security_profile": resolved_security_profile,
        "coverage_gate": bool(defaults.get("coverage_gate", True)) and not bool(no_coverage_gate),
        "coverage_lines_min": max(0, int(defaults.get("coverage_lines_min", 90) or 0)),
        "coverage_branches_min": max(0, int(defaults.get("coverage_branches_min", 85) or 0)),
        "smoke_strict": bool(defaults.get("smoke_strict", True)),
        "allow_full_unit_fallback": bool(defaults.get("allow_full_unit_fallback", False)),
    }


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description="sc-test (test shim)")
    ap.add_argument("--self-check", action="store_true", help="Validate parser/runtime wiring and summary contract without running tests.")
    ap.add_argument("--type", choices=["unit", "integration", "e2e", "all"], default="all")
    ap.add_argument("--task-id", default=None, help="Optional task id for smoke evidence file logs/ci/<date>/task-<id>.json")
    ap.add_argument("--solution", default="auto")
    ap.add_argument("--configuration", default="Debug")
    ap.add_argument("--delivery-profile", default=None, choices=DELIVERY_PROFILE_CHOICES, help="Delivery profile (default: env DELIVERY_PROFILE or fast-ship).")
    ap.add_argument("--security-profile", default=None, choices=["strict", "host-safe"], help="Security profile override (default derives from delivery profile).")
    ap.add_argument("--godot-bin", default=None, help="Godot mono console binary (required for e2e/all)")
    ap.add_argument("--run-id", default=None, help="Optional run identifier for evidence binding (default: auto-generate).")
    ap.add_argument("--smoke-scene", default="res://Game.Godot/Scenes/Main.tscn", help="Main scene for smoke test")
    ap.add_argument("--timeout-sec", type=int, default=600)
    ap.add_argument("--skip-smoke", action="store_true")
    ap.add_argument("--no-coverage-gate", action="store_true", help="do not enforce default coverage thresholds")
    ap.add_argument("--no-coverage-report", action="store_true", help="skip HTML coverage report generation")
    ap.add_argument(
        "--allow-full-unit-fallback",
        action="store_true",
        help="when task-scoped unit coverage reports 0.0%%, retry once without the task filter",
    )
    return ap


def _planned_steps(*, test_type: str, include_coverage_report: bool, skip_smoke: bool) -> list[dict[str, Any]]:
    planned: list[dict[str, Any]] = []
    if test_type in ("unit", "all"):
        planned.append({"name": "unit", "status": "skipped", "reason": "planned"})
        planned.append({"name": "csharp-test-conventions", "status": "skipped", "reason": "planned"})
        if include_coverage_report:
            planned.append({"name": "coverage-report", "status": "skipped", "reason": "planned"})
    if test_type in ("integration", "e2e", "all"):
        planned.append({"name": "gdunit-hard", "status": "skipped", "reason": "planned"})
        if not skip_smoke:
            planned.append({"name": "smoke", "status": "skipped", "reason": "planned"})
    return planned


def _validate_planned_runtime_summary(*, run_id: str, args: argparse.Namespace, task_root_id: str | None, include_coverage_report: bool) -> None:
    summary: dict[str, Any] = {
        "cmd": "sc-test",
        "run_id": run_id,
        "type": args.type,
        "solution": args.solution,
        "configuration": args.configuration,
        "status": "fail",
        "steps": _planned_steps(test_type=args.type, include_coverage_report=include_coverage_report, skip_smoke=bool(args.skip_smoke)),
    }
    if task_root_id:
        summary["task_id"] = task_root_id
    validate_sc_test_summary(summary)


def _run_self_check(args: argparse.Namespace) -> int:
    out_dir = ci_dir("sc-test-self-check")
    run_id = str(args.run_id or "").strip() or uuid.uuid4().hex
    task_root_id = _normalize_task_root_id(args.task_id)
    errors: list[str] = []
    try:
        _validate_planned_runtime_summary(
            run_id=run_id,
            args=args,
            task_root_id=task_root_id,
            include_coverage_report=not bool(args.no_coverage_report),
        )
    except SummarySchemaError as exc:
        errors.append(str(exc))
    payload: dict[str, Any] = {
        "cmd": "sc-test",
        "mode": "self-check",
        "status": "ok" if not errors else "fail",
        "out_dir": str(out_dir),
        "run_id": run_id,
        "type": args.type,
        "solution": args.solution,
        "configuration": args.configuration,
        "planned_steps": _planned_steps(test_type=args.type, include_coverage_report=not bool(args.no_coverage_report), skip_smoke=bool(args.skip_smoke)),
        "arg_validation": {"valid": len(errors) == 0, "errors": errors},
    }
    if task_root_id:
        payload["task_id"] = task_root_id
    write_json(out_dir / "summary.json", payload)
    print(f"SC_TEST_SELF_CHECK status={payload['status']} out={out_dir}")
    return 0 if not errors else 2


def _normalize_task_root_id(task_id: str | None) -> str | None:
    return _normalize_task_root_id_impl(task_id)


def _task_scoped_gdunit_refs(*, task_id: str | None, tests_project: Path) -> list[str]:
    return _task_scoped_gdunit_refs_impl(task_id=task_id, tests_project=tests_project)


def _task_scoped_cs_refs(*, task_id: str | None) -> list[str]:
    return _task_scoped_cs_refs_impl(task_id=task_id)


def _build_dotnet_filter_from_cs_refs(cs_refs: list[str]) -> str:
    return _build_dotnet_filter_from_cs_refs_impl(cs_refs)


def run_unit(
    out_dir: Path,
    solution: str,
    configuration: str,
    *,
    run_id: str,
    task_id: str | None = None,
    allow_full_unit_fallback: bool = False,
) -> dict[str, Any]:
    return _run_unit_impl(
        out_dir,
        solution,
        configuration,
        run_id=run_id,
        task_id=task_id,
        allow_full_unit_fallback=allow_full_unit_fallback,
    )


def run_coverage_report(out_dir: Path, unit_artifacts_dir: Path) -> dict[str, Any]:
    return _run_coverage_report_impl(out_dir, unit_artifacts_dir)


def run_csharp_test_conventions(out_dir: Path, *, task_id: str | None = None) -> dict[str, Any]:
    return _run_csharp_test_conventions_impl(out_dir, task_id=task_id)


def run_gdunit_hard(
    out_dir: Path,
    godot_bin: str,
    timeout_sec: int,
    *,
    run_id: str,
    task_id: str | None = None,
    require_task_scoped_refs: bool = False,
) -> dict[str, Any]:
    return _run_gdunit_hard_impl(
        out_dir,
        godot_bin,
        timeout_sec,
        run_id=run_id,
        task_id=task_id,
        require_task_scoped_refs=require_task_scoped_refs,
    )


def run_smoke(out_dir: Path, godot_bin: str, scene: str, task_id: str | None = None, *, strict: bool = True) -> dict[str, Any]:
    return _run_smoke_impl(out_dir, godot_bin, scene, task_id=task_id, strict=strict)


def _skipped_step(*, name: str, reason: str, cmd: list[str] | None = None) -> dict[str, Any]:
    step: dict[str, Any] = {
        "name": name,
        "status": "skipped",
        "reason": reason,
    }
    if cmd:
        step["cmd"] = list(cmd)
    return step


def main() -> int:
    args = build_parser().parse_args()
    if bool(args.self_check):
        return _run_self_check(args)
    runtime = resolve_test_runtime(
        delivery_profile=args.delivery_profile,
        security_profile=args.security_profile,
        no_coverage_gate=bool(args.no_coverage_gate),
    )
    os.environ["DELIVERY_PROFILE"] = str(runtime["delivery_profile"])
    os.environ["SECURITY_PROFILE"] = str(runtime["security_profile"])
    out_dir = ci_dir("sc-test")
    run_id = str(args.run_id or "").strip() or uuid.uuid4().hex
    run_date = today_str()
    write_text(out_dir / "run_id.txt", run_id + "\n")
    os.environ["SC_TEST_RUN_ID"] = run_id
    os.environ["SC_TEST_DATE"] = run_date
    godot_bin = args.godot_bin or os.environ.get("GODOT_BIN")

    summary: dict[str, Any] = {
        "cmd": "sc-test",
        "run_id": run_id,
        "type": args.type,
        "solution": args.solution,
        "configuration": args.configuration,
        "status": "fail",
        "steps": [],
    }
    task_root_id = _normalize_task_root_id(args.task_id)
    if task_root_id:
        summary["task_id"] = task_root_id
    schema_error_log = out_dir / "summary-schema-validation-error.log"

    try:
        _validate_planned_runtime_summary(
            run_id=run_id,
            args=args,
            task_root_id=task_root_id,
            include_coverage_report=not bool(args.no_coverage_report),
        )
    except SummarySchemaError as exc:
        write_text(schema_error_log, f"{exc}\n")
        write_json(out_dir / "summary.invalid.json", summary)
        print(f"[sc-test] ERROR: planned summary schema validation failed. details={schema_error_log}")
        return 2

    def _persist_summary() -> bool:
        try:
            validate_sc_test_summary(summary)
        except SummarySchemaError as exc:
            write_text(schema_error_log, f"{exc}\n")
            write_json(out_dir / "summary.invalid.json", summary)
            print(f"[sc-test] ERROR: summary schema validation failed. details={schema_error_log}")
            return False
        invalid_summary_path = out_dir / "summary.invalid.json"
        if schema_error_log.exists():
            schema_error_log.unlink(missing_ok=True)
        if invalid_summary_path.exists():
            invalid_summary_path.unlink(missing_ok=True)
        write_json(out_dir / "summary.json", summary)
        return True

    hard_fail = False
    if not _persist_summary():
        return 2

    if args.type in ("unit", "all"):
        if bool(runtime["coverage_gate"]):
            os.environ["COVERAGE_LINES_MIN"] = str(runtime["coverage_lines_min"])
            os.environ["COVERAGE_BRANCHES_MIN"] = str(runtime["coverage_branches_min"])
        else:
            os.environ.pop("COVERAGE_LINES_MIN", None)
            os.environ.pop("COVERAGE_BRANCHES_MIN", None)
        step = run_unit(
            out_dir,
            args.solution,
            args.configuration,
            run_id=run_id,
            task_id=args.task_id,
            allow_full_unit_fallback=bool(runtime["allow_full_unit_fallback"]) or bool(args.allow_full_unit_fallback),
        )
        summary["steps"].append(step)
        if not _persist_summary():
            return 2
        if step["rc"] != 0:
            hard_fail = True
        else:
            conventions = run_csharp_test_conventions(out_dir, task_id=args.task_id)
            summary["steps"].append(conventions)
            if not _persist_summary():
                return 2
            if conventions["rc"] != 0:
                hard_fail = True
        if not hard_fail and not args.no_coverage_report:
            cov = run_coverage_report(out_dir, Path(step["artifacts_dir"]))
            summary["steps"].append(cov)
            if not _persist_summary():
                return 2
            if cov.get("status") == "fail":
                hard_fail = True

    task_gd_refs = _task_scoped_gdunit_refs(task_id=args.task_id, tests_project=repo_root() / "Tests.Godot") if args.task_id else []
    explicit_engine_lane = args.type in ("integration", "e2e")
    should_run_engine_lane = args.type in ("integration", "e2e") or (args.type == "all" and (not args.task_id or bool(task_gd_refs)))

    if args.type in ("integration", "e2e", "all"):
        if args.type == "all" and args.task_id and not task_gd_refs:
            summary["steps"].append(
                _skipped_step(
                    name="gdunit-hard",
                    reason="no_task_scoped_gd_refs_for_task",
                    cmd=["py", "-3", "scripts/python/run_gdunit.py"],
                )
            )
            if not _persist_summary():
                return 2
            if not args.skip_smoke:
                summary["steps"].append(
                    _skipped_step(
                        name="smoke",
                        reason="no_task_scoped_gd_refs_for_task",
                        cmd=["py", "-3", "scripts/python/smoke_headless.py"],
                    )
                )
                if not _persist_summary():
                    return 2
        elif should_run_engine_lane:
            if not godot_bin:
                print("[sc-test] ERROR: --godot-bin (or env GODOT_BIN) is required for e2e/integration tests.")
                return 2
            step = run_gdunit_hard(
                out_dir,
                godot_bin,
                args.timeout_sec,
                run_id=run_id,
                task_id=args.task_id,
                require_task_scoped_refs=bool(args.task_id and (explicit_engine_lane or bool(task_gd_refs))),
            )
            summary["steps"].append(step)
            if not _persist_summary():
                return 2
            if step["rc"] != 0:
                hard_fail = True
            if not args.skip_smoke:
                smoke = run_smoke(out_dir, godot_bin, args.smoke_scene, task_id=args.task_id, strict=bool(runtime["smoke_strict"]))
                summary["steps"].append(smoke)
                if not _persist_summary():
                    return 2
                if smoke["rc"] != 0:
                    hard_fail = True

    summary["status"] = "ok" if not hard_fail else "fail"
    if not _persist_summary():
        return 2
    print(f"SC_TEST status={summary['status']} out={out_dir}")
    return 0 if not hard_fail else 1


if __name__ == "__main__":
    raise SystemExit(main())
