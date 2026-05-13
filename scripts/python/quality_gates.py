#!/usr/bin/env python3
"""Quality gates entry for Windows (Godot+C# template).

Default behavior:
- run hard gate bundle first
- optionally append GdUnit hard set
- optionally append strict headless smoke

The legacy ``ci_pipeline.py`` remains available as a separate tool, but this
entrypoint now follows the same gate bundle mainline used by current CI.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import subprocess
import sys
from pathlib import Path

from quality_gates_builders import (
    DEFAULT_GATE_BUNDLE_TASK_FILES,
    build_gate_bundle_hard_cmd,
    build_gdunit_hard_cmd,
    build_smoke_headless_cmd,
)
from solution_target import resolve_test_solution_arg


def _run(cmd: list[str]) -> int:
    proc = subprocess.run(cmd, text=True)
    return proc.returncode


def run_gate_bundle_hard(
    *,
    delivery_profile: str,
    task_files: list[str],
    out_dir: str,
    run_id: str,
) -> int:
    return _run(
        build_gate_bundle_hard_cmd(
            delivery_profile=delivery_profile,
            task_files=task_files,
            out_dir=out_dir,
            run_id=run_id,
        )
    )


def run_gdunit_hard(godot_bin: str) -> int:
    """Run the hard GdUnit subset for adapters/config and security."""

    return _run(build_gdunit_hard_cmd(godot_bin=godot_bin))


def run_smoke_headless(godot_bin: str) -> int:
    """Run strict headless smoke against the main scene."""

    return _run(build_smoke_headless_cmd(godot_bin=godot_bin))


def _today() -> str:
    return dt.date.today().strftime("%Y-%m-%d")


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _as_posix(path: Path) -> str:
    return str(path).replace("\\", "/")


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _run_and_stream(cmd: list[str]) -> int:
    proc = subprocess.run(cmd, text=True)
    return proc.returncode


def _quality_gates_all_legacy(args: argparse.Namespace) -> int:
    # Keep legacy compatibility for Task39/Task47 tests while preserving gate-bundle first behavior.
    root = _repo_root()
    test_mode = str(os.getenv("QUALITY_GATES_TEST_MODE", "")).strip() == "1"
    test_out_dir = str(os.getenv("QUALITY_GATES_TEST_OUT_DIR", "")).strip()
    out_dir = Path(test_out_dir) if test_out_dir else (root / "logs" / "ci" / _today())
    out_dir.mkdir(parents=True, exist_ok=True)
    summary_path = out_dir / "quality-gates-summary.json"
    ci_day_dir = (root / "logs" / "ci" / _today()).resolve()
    try:
        out_dir_resolved = out_dir.resolve()
    except Exception:
        out_dir_resolved = out_dir
    test_mode_is_ci_day_root = out_dir_resolved == ci_day_dir

    delivery_profile = str(args.delivery_profile or "").strip()
    task_files = list(args.task_file or DEFAULT_GATE_BUNDLE_TASK_FILES)
    run_id = str(args.run_id or "").strip()

    ci_pipeline_rc_env = str(os.getenv("QUALITY_GATES_TEST_CI_PIPELINE_RC", "")).strip() if test_mode else ""
    if test_mode and ci_pipeline_rc_env:
        gate_bundle_rc = int(ci_pipeline_rc_env)
    else:
        gate_bundle_cmd = build_gate_bundle_hard_cmd(
            delivery_profile=delivery_profile,
            task_files=task_files,
            out_dir=str(out_dir),
            run_id=run_id,
        )
        gate_bundle_rc = _run_and_stream(gate_bundle_cmd)

    dotnet_status = "unknown"
    dotnet_threshold_ok = False
    dotnet_coverage = {}
    dotnet_summary_path = ""
    dotnet_summary_override = str(os.getenv("QUALITY_GATES_TEST_DOTNET_SUMMARY_JSON", "")).strip()
    if dotnet_summary_override:
        candidate = Path(dotnet_summary_override)
        if not candidate.is_absolute():
            candidate = (root / candidate).resolve()
        if candidate.exists():
            dotnet_summary = _read_json(candidate)
            dotnet_status = str(dotnet_summary.get("status") or "unknown")
            dotnet_threshold_ok = bool(dotnet_summary.get("threshold_ok"))
            dotnet_coverage = dotnet_summary.get("coverage") if isinstance(dotnet_summary.get("coverage"), dict) else {}
            dotnet_summary_path = _as_posix(candidate)

    coverage_mode = "soft" if bool(args.coverage_soft) else "hard"
    coverage_failed = (dotnet_status == "coverage_failed" or not dotnet_threshold_ok)
    coverage_blocking = coverage_failed and coverage_mode == "hard"

    perf_artifact = out_dir / "quality-gates-perf.json"
    perf_source = root / "logs" / "perf" / _today() / "summary.json"
    should_run_perf = True
    if test_mode and not test_mode_is_ci_day_root:
        should_run_perf = False
    if should_run_perf:
        perf_cmd = ["py", "-3", "scripts/python/validate_perf.py", "--out", str(perf_artifact)]
        perf_rc = _run_and_stream(perf_cmd)
        perf_ok = perf_rc == 0
    else:
        perf_rc = 0
        perf_ok = True

    audit_artifact = out_dir / "quality-gates-audit.json"
    audit_source = root / "logs" / "ci" / _today() / "security-audit.jsonl"
    should_run_audit = True
    if test_mode and not test_mode_is_ci_day_root:
        should_run_audit = False
    if should_run_audit:
        audit_cmd = ["py", "-3", "scripts/python/validate_audit_logs.py", "--out", str(audit_artifact)]
        audit_rc = _run_and_stream(audit_cmd)
        audit_ok = audit_rc == 0
    else:
        audit_rc = 0
        audit_ok = True

    arch_rc_env = str(os.getenv("QUALITY_GATES_TEST_ARCH_HOTSPOTS_RC", "")).strip() if test_mode else ""
    if test_mode:
        if arch_rc_env:
            try:
                arch_rc = int(arch_rc_env)
            except ValueError:
                arch_rc = 1
        else:
            arch_rc = 0
    else:
        arch_rc = _run_and_stream(["py", "-3", "scripts/python/check_architecture_hotspots.py"])
    arch_ok = arch_rc == 0

    gdunit_enabled = bool(args.gdunit_hard)
    gdunit_rc = 0
    gdunit_run_summary_path = ""
    gdunit_run_summary_raw = {}
    if gdunit_enabled:
        if test_mode and str(os.getenv("QUALITY_GATES_TEST_GDUNIT_RC", "")).strip():
            gdunit_rc = int(str(os.getenv("QUALITY_GATES_TEST_GDUNIT_RC")).strip())
        else:
            gdunit_rc = run_gdunit_hard(args.godot_bin)
        gdunit_run_summary_override = str(os.getenv("QUALITY_GATES_TEST_GDUNIT_RUN_SUMMARY_JSON", "")).strip() if test_mode else ""
        if gdunit_run_summary_override:
            gdunit_path = Path(gdunit_run_summary_override)
            if not gdunit_path.is_absolute():
                gdunit_path = (root / gdunit_path).resolve()
            if gdunit_path.exists():
                gdunit_run_summary_path = str(gdunit_path)
                try:
                    gdunit_run_summary_raw = _read_json(gdunit_path)
                except Exception:
                    gdunit_run_summary_raw = {}
    gdunit_ok = gdunit_rc == 0

    smoke_rc = 0
    if args.smoke:
        smoke_rc = run_smoke_headless(args.godot_bin)

    ci_pipeline_rc = int(ci_pipeline_rc_env) if ci_pipeline_rc_env else 0

    failed_reasons = []
    if gate_bundle_rc != 0:
        failed_reasons.append("gate_bundle_failed")
    if coverage_blocking:
        failed_reasons.append("coverage_gate_failed")
    if not perf_ok:
        failed_reasons.append("perf_gate_failed")
    if not audit_ok:
        failed_reasons.append("audit_gate_failed")
    if not arch_ok:
        failed_reasons.append("architecture_hotspots_failed")
    if gdunit_enabled and not gdunit_ok:
        failed_reasons.append("gdunit_hard_failed")
    if args.smoke and smoke_rc != 0:
        failed_reasons.append("smoke_failed")
    if ci_pipeline_rc != 0:
        failed_reasons.append("ci_pipeline_failed")

    status = "ok" if not failed_reasons else "fail"
    summary = {
        "cmd": "quality_gates.py all",
        "status": status,
        "coverage_mode": coverage_mode,
        "dotnet": {
            "status": dotnet_status,
            "threshold_ok": dotnet_threshold_ok,
            "coverage": dotnet_coverage,
            "summary_path": dotnet_summary_path,
        },
        "gdunit_hard": {
            "enabled": gdunit_enabled,
            "rc": gdunit_rc,
            "run_summary_path": gdunit_run_summary_path,
            "run_summary": gdunit_run_summary_raw,
        },
        "architecture_hotspots": {
            "rc": arch_rc,
            "ok": arch_ok,
        },
        "artifacts": {
            "quality_gates_summary": _as_posix(summary_path),
            "quality_gates_perf": _as_posix(perf_artifact),
            "quality_gates_audit": _as_posix(audit_artifact),
        },
        "reasons": failed_reasons,
        "gate_bundle_rc": gate_bundle_rc,
        "perf_rc": perf_rc,
        "audit_rc": audit_rc,
        "ci_pipeline_rc": ci_pipeline_rc,
        "notes": "adapters + security gdunit-hard path supported",
    }
    _write_json(summary_path, summary)
    return 0 if status == "ok" else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_all = sub.add_parser(
        "all",
        help="run hard gate bundle with optional GdUnit hard and smoke follow-up steps",
    )
    p_all.add_argument("--solution", default="")
    p_all.add_argument("--configuration", default="Debug")
    p_all.add_argument("--build-solutions", action="store_true")
    p_all.add_argument("--godot-bin", default="")
    p_all.add_argument("--delivery-profile", default="")
    p_all.add_argument("--task-file", action="append", default=[])
    p_all.add_argument("--out-dir", default="")
    p_all.add_argument("--run-id", default="")
    p_all.add_argument("--coverage-soft", action="store_true", help="Treat coverage threshold failure as soft gate.")
    p_all.add_argument("--gdunit-hard", action="store_true", help="run hard GdUnit set (Adapters/Config + Security)")
    p_all.add_argument("--smoke", action="store_true", help="run strict headless smoke after the hard gate bundle")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.cmd != "all":
        print("Unsupported command", file=sys.stderr)
        return 1

    # Keep argument compatibility while normalizing default behavior.
    # This value is currently not consumed by the gate-bundle branch.
    _resolved_solution = resolve_test_solution_arg(args.solution)

    if (args.gdunit_hard or args.smoke) and not args.godot_bin:
        print("[quality_gates] error: --godot-bin is required when --gdunit-hard or --smoke is enabled", file=sys.stderr)
        return 2

    return _quality_gates_all_legacy(args)


if __name__ == "__main__":
    sys.exit(main())
