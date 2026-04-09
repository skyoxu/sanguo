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
import json
import os
from pathlib import Path
import subprocess
import sys

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


def _run_capture(cmd: list[str]) -> tuple[int, str]:
    proc = subprocess.run(
        cmd,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    out = proc.stdout or ""
    if out:
        print(out, end="" if out.endswith("\n") else "\n")
    return proc.returncode, out


def _read_json(path: Path) -> dict:
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return obj if isinstance(obj, dict) else {}


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")


def _today_local_str() -> str:
    from datetime import date

    return date.today().strftime("%Y-%m-%d")


def _is_ci_date_root(path: Path) -> bool:
    # logs/ci/YYYY-MM-DD
    if path.parent.name != "ci":
        return False
    name = path.name
    if len(name) != 10:
        return False
    try:
        from datetime import datetime

        datetime.strptime(name, "%Y-%m-%d")
        return True
    except Exception:
        return False


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
    p_all.add_argument("--gdunit-hard", action="store_true", help="run hard GdUnit set (Adapters/Config + Security)")
    p_all.add_argument("--smoke", action="store_true", help="run strict headless smoke after the hard gate bundle")
    p_all.add_argument("--coverage-soft", action="store_true", help="compatibility mode: keep process green when dotnet coverage fails")
    return parser


def _run_test_mode_all(args: argparse.Namespace) -> int:
    out_dir = Path(
        str(
            args.out_dir
            or os.environ.get("QUALITY_GATES_TEST_OUT_DIR")
            or Path("logs") / "ci" / _today_local_str() / "quality-gates-test"
        )
    )
    out_dir.mkdir(parents=True, exist_ok=True)

    coverage_mode = "soft" if bool(args.coverage_soft) else "hard"

    dotnet_summary_path = Path(str(os.environ.get("QUALITY_GATES_TEST_DOTNET_SUMMARY_JSON") or out_dir / "dotnet-summary.json"))
    dotnet = _read_json(dotnet_summary_path)
    dotnet_status = str(dotnet.get("status") or "")
    dotnet_threshold_ok = bool(dotnet.get("threshold_ok", True))
    dotnet_coverage = dotnet.get("coverage") if isinstance(dotnet.get("coverage"), dict) else {}

    pipeline_rc = int(str(os.environ.get("QUALITY_GATES_TEST_CI_PIPELINE_RC") or "0"))
    arch_rc = int(str(os.environ.get("QUALITY_GATES_TEST_ARCH_HOTSPOTS_RC") or "0"))
    gdunit_rc = int(str(os.environ.get("QUALITY_GATES_TEST_GDUNIT_RC") or "0"))

    gdunit_run_summary_path = str(os.environ.get("QUALITY_GATES_TEST_GDUNIT_RUN_SUMMARY_JSON") or "")
    gdunit_report_dir = str(os.environ.get("QUALITY_GATES_TEST_GDUNIT_REPORT_DIR") or "")
    gdunit_run_summary = {}
    if gdunit_run_summary_path:
        gdunit_run_summary = _read_json(Path(gdunit_run_summary_path))

    date = _today_local_str()
    perf_out = out_dir / "quality-gates-perf.json"
    audit_out = out_dir / "quality-gates-audit.json"
    strict_perf_audit = _is_ci_date_root(out_dir)
    perf_rc = 0
    audit_rc = 0
    if strict_perf_audit:
        perf_rc, _perf_log = _run_capture(
            [
                "py",
                "-3",
                "scripts/python/validate_perf.py",
                "--date",
                date,
                "--out",
                str(perf_out),
            ]
        )
        audit_rc, _audit_log = _run_capture(
            [
                "py",
                "-3",
                "scripts/python/validate_audit_logs.py",
                "--date",
                date,
                "--out",
                str(audit_out),
            ]
        )
    else:
        _write_json(
            perf_out,
            {
                "cmd": "validate_perf",
                "date": date,
                "ok": True,
                "skipped": True,
                "reason": "test_mode_non_ci_root_out_dir",
            },
        )
        _write_json(
            audit_out,
            {
                "cmd": "validate_audit_logs",
                "date": date,
                "ok": True,
                "skipped": True,
                "reason": "test_mode_non_ci_root_out_dir",
                "required_keys": ["ts", "action", "reason", "target", "caller"],
                "results": [],
            },
        )

    hard_failed = False
    if pipeline_rc != 0:
        hard_failed = True
    if arch_rc != 0:
        hard_failed = True
    if strict_perf_audit and (perf_rc != 0 or audit_rc != 0):
        hard_failed = True
    if args.gdunit_hard and gdunit_rc != 0:
        hard_failed = True

    dotnet_is_fail = (dotnet_status != "ok") or (not dotnet_threshold_ok)
    if coverage_mode == "hard" and dotnet_is_fail:
        hard_failed = True

    summary = {
        "status": "fail" if hard_failed else "ok",
        "coverage_mode": coverage_mode,
        "dotnet": {
            "status": dotnet_status,
            "threshold_ok": dotnet_threshold_ok,
            "coverage": dotnet_coverage,
            "summary_path": str(dotnet_summary_path),
        },
        "ci_pipeline": {"rc": pipeline_rc},
        "architecture_hotspots": {"rc": arch_rc},
        "gdunit_hard": {
            "enabled": bool(args.gdunit_hard),
            "rc": gdunit_rc if args.gdunit_hard else 0,
            "run_summary_path": gdunit_run_summary_path,
            "run_summary": gdunit_run_summary,
            "report_dir": gdunit_report_dir,
        },
        "artifacts": {
            "quality_gates_perf": str(perf_out),
            "quality_gates_audit": str(audit_out),
        },
    }
    # Keep a stable artifact path for tests and downstream tooling.
    _write_json(out_dir / "quality-gates-summary.json", summary)
    return 1 if hard_failed else 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.cmd != "all":
        print("Unsupported command", file=sys.stderr)
        return 1

    if str(os.environ.get("QUALITY_GATES_TEST_MODE") or "").strip() == "1":
        return _run_test_mode_all(args)

    # Keep argument compatibility while normalizing default behavior.
    # This value is currently not consumed by the gate-bundle branch.
    _resolved_solution = resolve_test_solution_arg(args.solution)

    if (args.gdunit_hard or args.smoke) and not args.godot_bin:
        print("[quality_gates] error: --godot-bin is required when --gdunit-hard or --smoke is enabled", file=sys.stderr)
        return 2

    task_files = list(args.task_file or DEFAULT_GATE_BUNDLE_TASK_FILES)
    rc = run_gate_bundle_hard(
        delivery_profile=args.delivery_profile,
        task_files=task_files,
        out_dir=args.out_dir,
        run_id=args.run_id,
    )
    hard_failed = rc != 0

    if args.gdunit_hard:
        gd_rc = run_gdunit_hard(args.godot_bin)
        if gd_rc != 0:
            hard_failed = True

    if args.smoke:
        # Strict smoke should request the app to exit as soon as ready.
        original_exit_on_ready = os.environ.get("GD_SMOKE_EXIT_ON_READY")
        try:
            os.environ["GD_SMOKE_EXIT_ON_READY"] = "1"
            smoke_rc = run_smoke_headless(args.godot_bin)
        finally:
            if original_exit_on_ready is None:
                os.environ.pop("GD_SMOKE_EXIT_ON_READY", None)
            else:
                os.environ["GD_SMOKE_EXIT_ON_READY"] = original_exit_on_ready
        if smoke_rc != 0:
            hard_failed = True

    return 0 if not hard_failed else 1


if __name__ == "__main__":
    sys.exit(main())
