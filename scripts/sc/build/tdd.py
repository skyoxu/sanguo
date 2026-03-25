#!/usr/bin/env python3
"""
sc-build tdd: TDD gatekeeper (non-generative).

This script does NOT synthesize business logic. It enforces a repeatable
red/green/refactor loop with logs under logs/ci/<date>/.

Usage (Windows):
  py -3 scripts/sc/build/tdd.py --stage green
  py -3 scripts/sc/build/tdd.py --stage red --generate-red-test
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import Any


def _bootstrap_imports() -> None:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


_bootstrap_imports()

from _delivery_profile import default_security_profile_for_delivery, known_delivery_profiles, profile_test_defaults, resolve_delivery_profile  # noqa: E402
from _security_profile import resolve_security_profile  # noqa: E402
from _taskmaster import resolve_triplet  # noqa: E402
from _util import ci_dir  # noqa: E402
from _tdd_shared import assert_no_new_contract_files, snapshot_contract_files, write_coverage_hotspots  # noqa: E402
from _tdd_steps import (  # noqa: E402
    build_summary,
    default_task_test_path as _default_task_test_path_impl,
    ensure_red_test_exists as _ensure_red_test_exists_impl,
    print_refactor_failure_hints,
    run_dotnet_test_filtered as _run_dotnet_test_filtered_impl,
    run_green_gate as _run_green_gate_impl,
    run_refactor_checks as _run_refactor_checks_impl,
    run_sc_analyze_task_context as _run_sc_analyze_task_context_impl,
    run_task_preflight as _run_task_preflight_impl,
    validate_task_context_required_fields as _validate_task_context_required_fields_impl,
    write_summary,
)


DELIVERY_PROFILE_CHOICES = tuple(sorted(known_delivery_profiles()))


def resolve_tdd_runtime(*, delivery_profile: str | None, security_profile: str | None, no_coverage_gate: bool) -> dict[str, Any]:
    resolved_delivery_profile = resolve_delivery_profile(delivery_profile)
    resolved_security_profile = resolve_security_profile(
        security_profile or default_security_profile_for_delivery(resolved_delivery_profile)
    )
    test_defaults = profile_test_defaults(resolved_delivery_profile)
    return {
        "delivery_profile": resolved_delivery_profile,
        "security_profile": resolved_security_profile,
        "coverage_gate": bool(test_defaults.get("coverage_gate", True)) and not bool(no_coverage_gate),
        "coverage_lines_min": max(0, int(test_defaults.get("coverage_lines_min", 90) or 0)),
        "coverage_branches_min": max(0, int(test_defaults.get("coverage_branches_min", 85) or 0)),
    }


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description="sc-build tdd gatekeeper")
    ap.add_argument("--stage", choices=["red", "green", "refactor"], default="green")
    ap.add_argument("--task-id", default=None, help="task id; defaults to first status=in-progress in tasks.json")
    ap.add_argument("--solution", default="Game.sln")
    ap.add_argument("--configuration", default="Debug")
    ap.add_argument("--delivery-profile", default=None, choices=DELIVERY_PROFILE_CHOICES, help="Delivery profile (default: env DELIVERY_PROFILE or fast-ship).")
    ap.add_argument("--security-profile", default=None, choices=["strict", "host-safe"], help="Security profile override (default derives from delivery profile).")
    ap.add_argument("--generate-red-test", action="store_true", help="create a failing test skeleton if missing")
    ap.add_argument("--no-coverage-gate", action="store_true", help="do not enforce default coverage thresholds")
    ap.add_argument("--allow-contract-changes", action="store_true", help="allow creating new files under Game.Core/Contracts during this TDD stage")
    return ap


def default_task_test_path(task_id: str) -> Path:
    return _default_task_test_path_impl(task_id)


def ensure_red_test_exists(task_id: str, title: str, *, allow_create: bool, out_dir: Path) -> Path | None:
    return _ensure_red_test_exists_impl(task_id, title, allow_create=allow_create, out_dir=out_dir)


def run_dotnet_test_filtered(task_id: str, *, solution: str, configuration: str, out_dir: Path) -> dict[str, Any]:
    return _run_dotnet_test_filtered_impl(task_id, solution=solution, configuration=configuration, out_dir=out_dir)


def run_sc_analyze_task_context(*, task_id: str, out_dir: Path) -> dict[str, Any]:
    return _run_sc_analyze_task_context_impl(task_id=task_id, out_dir=out_dir)


def validate_task_context_required_fields(*, task_id: str, stage: str, out_dir: Path) -> dict[str, Any]:
    return _validate_task_context_required_fields_impl(task_id=task_id, stage=stage, out_dir=out_dir)


def run_task_preflight(*, triplet: Any, out_dir: Path) -> dict[str, Any]:
    return _run_task_preflight_impl(triplet=triplet, out_dir=out_dir)


def run_green_gate(
    *,
    solution: str,
    configuration: str,
    out_dir: Path,
    coverage_gate: bool,
    coverage_lines_min: int,
    coverage_branches_min: int,
) -> dict[str, Any]:
    return _run_green_gate_impl(
        solution=solution,
        configuration=configuration,
        out_dir=out_dir,
        coverage_gate=coverage_gate,
        coverage_lines_min=coverage_lines_min,
        coverage_branches_min=coverage_branches_min,
    )


def run_refactor_checks(out_dir: Path, *, task_id: str) -> list[dict[str, Any]]:
    return _run_refactor_checks_impl(out_dir, task_id=task_id)


def _run_context_gate(*, stage: str, task_id: str, triplet: Any, out_dir: Path, summary: dict[str, Any]) -> bool:
    preflight_step = run_task_preflight(triplet=triplet, out_dir=out_dir)
    summary["steps"].append(preflight_step)
    if preflight_step["rc"] != 0:
        return False
    summary["steps"].append(run_sc_analyze_task_context(task_id=task_id, out_dir=out_dir))
    ctx_step = validate_task_context_required_fields(task_id=task_id, stage=stage, out_dir=out_dir)
    summary["steps"].append(ctx_step)
    return ctx_step["rc"] == 0


def _handle_red_stage(*, args: argparse.Namespace, triplet: Any, out_dir: Path, summary: dict[str, Any]) -> int:
    if not _run_context_gate(stage="red", task_id=triplet.task_id, triplet=triplet, out_dir=out_dir, summary=summary):
        write_summary(out_dir, summary)
        print(f"SC_BUILD_TDD status=fail out={out_dir}")
        return 1
    test_path = ensure_red_test_exists(
        triplet.task_id,
        str(triplet.master.get("title") or ""),
        allow_create=args.generate_red_test,
        out_dir=out_dir,
    )
    if not test_path:
        write_summary(out_dir, summary)
        print("[sc-build-tdd] ERROR: no task-scoped test found. Use --generate-red-test to create one.")
        return 2
    step = run_dotnet_test_filtered(triplet.task_id, solution=args.solution, configuration=args.configuration, out_dir=out_dir)
    summary["steps"].append(step)
    summary["status"] = "ok" if step["rc"] != 0 else "unexpected_green"
    write_summary(out_dir, summary)
    print(f"SC_BUILD_TDD status={summary['status']} out={out_dir}")
    return 0 if summary["status"] == "ok" else 1


def _handle_green_stage(*, args: argparse.Namespace, runtime: dict[str, Any], triplet: Any, out_dir: Path, summary: dict[str, Any]) -> int:
    if not _run_context_gate(stage="green", task_id=triplet.task_id, triplet=triplet, out_dir=out_dir, summary=summary):
        write_summary(out_dir, summary)
        print(f"SC_BUILD_TDD status=fail out={out_dir}")
        return 1
    step = run_green_gate(
        solution=args.solution,
        configuration=args.configuration,
        out_dir=out_dir,
        coverage_gate=bool(runtime["coverage_gate"]),
        coverage_lines_min=int(runtime["coverage_lines_min"]),
        coverage_branches_min=int(runtime["coverage_branches_min"]),
    )
    summary["steps"].append(step)
    if step["rc"] == 2:
        summary["steps"].append(write_coverage_hotspots(ci_out_dir=out_dir, run_dotnet_output=step.get("stdout") or ""))
    summary["status"] = "ok" if step["rc"] == 0 else "fail"
    write_summary(out_dir, summary)
    print(f"SC_BUILD_TDD status={summary['status']} out={out_dir}")
    return 0 if step["rc"] == 0 else 1


def _handle_refactor_stage(*, triplet: Any, out_dir: Path, summary: dict[str, Any]) -> int:
    if not _run_context_gate(stage="refactor", task_id=triplet.task_id, triplet=triplet, out_dir=out_dir, summary=summary):
        write_summary(out_dir, summary)
        print(f"SC_BUILD_TDD status=fail out={out_dir}")
        return 1
    steps = run_refactor_checks(out_dir, task_id=triplet.task_id)
    summary["steps"].extend(steps)
    summary["status"] = "ok" if all(step["rc"] == 0 for step in steps) else "fail"
    write_summary(out_dir, summary)
    if summary["status"] != "ok":
        failed = [step for step in steps if step.get("rc") != 0]
        print_refactor_failure_hints(out_dir=out_dir, failed_count=len(failed))
        return 1
    print(f"SC_BUILD_TDD status=ok out={out_dir}")
    return 0


def main() -> int:
    args = build_parser().parse_args()
    runtime = resolve_tdd_runtime(
        delivery_profile=args.delivery_profile,
        security_profile=args.security_profile,
        no_coverage_gate=bool(args.no_coverage_gate),
    )
    os.environ["DELIVERY_PROFILE"] = str(runtime["delivery_profile"])
    os.environ["SECURITY_PROFILE"] = str(runtime["security_profile"])
    out_dir = ci_dir("sc-build-tdd")
    before_contracts = snapshot_contract_files()
    triplet = resolve_triplet(task_id=args.task_id)
    summary = build_summary(stage=args.stage, allow_contract_changes=bool(args.allow_contract_changes), triplet=triplet)

    try:
        if args.stage == "red":
            return _handle_red_stage(args=args, triplet=triplet, out_dir=out_dir, summary=summary)
        if args.stage == "green":
            return _handle_green_stage(args=args, runtime=runtime, triplet=triplet, out_dir=out_dir, summary=summary)
        if args.stage == "refactor":
            return _handle_refactor_stage(triplet=triplet, out_dir=out_dir, summary=summary)
        write_summary(out_dir, summary)
        return 1
    finally:
        assert_no_new_contract_files(before_contracts, allow_changes=bool(args.allow_contract_changes))


if __name__ == "__main__":
    raise SystemExit(main())
