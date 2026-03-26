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
from typing import Any

from quality_gates_builders import (
    DEFAULT_GATE_BUNDLE_TASK_FILES,
    build_gate_bundle_hard_cmd,
    build_gdunit_hard_cmd,
    build_smoke_headless_cmd,
)


QUALITY_GATES_SUMMARY_FILE = "quality-gates-summary.json"
QUALITY_GATES_TEST_MODE_ENV = "QUALITY_GATES_TEST_MODE"
QUALITY_GATES_TEST_OUT_DIR_ENV = "QUALITY_GATES_TEST_OUT_DIR"
QUALITY_GATES_TEST_DOTNET_SUMMARY_JSON_ENV = "QUALITY_GATES_TEST_DOTNET_SUMMARY_JSON"
QUALITY_GATES_TEST_CI_PIPELINE_RC_ENV = "QUALITY_GATES_TEST_CI_PIPELINE_RC"
QUALITY_GATES_TEST_GDUNIT_RC_ENV = "QUALITY_GATES_TEST_GDUNIT_RC"
QUALITY_GATES_TEST_GDUNIT_RUN_SUMMARY_JSON_ENV = "QUALITY_GATES_TEST_GDUNIT_RUN_SUMMARY_JSON"
QUALITY_GATES_TEST_ARCH_HOTSPOTS_RC_ENV = "QUALITY_GATES_TEST_ARCH_HOTSPOTS_RC"
QUALITY_GATES_TEST_SMOKE_RC_ENV = "QUALITY_GATES_TEST_SMOKE_RC"
QUALITY_GATES_TEST_PERF_RC_ENV = "QUALITY_GATES_TEST_PERF_RC"
QUALITY_GATES_TEST_AUDIT_RC_ENV = "QUALITY_GATES_TEST_AUDIT_RC"
QUALITY_GATES_ENABLE_EXTENDED_GATES_ENV = "QUALITY_GATES_ENABLE_EXTENDED_GATES"


def _run(cmd: list[str]) -> int:
    proc = subprocess.run(cmd, text=True)
    return proc.returncode


def _run_capture(cmd: list[str]) -> tuple[int, str]:
    proc = subprocess.run(cmd, text=True, capture_output=True)
    output = (proc.stdout or "") + (proc.stderr or "")
    if output:
        print(output, end="" if output.endswith("\n") else "\n")
    return proc.returncode, output


def _is_truthy_env(name: str) -> bool:
    return (os.environ.get(name, "").strip().lower() in {"1", "true", "yes", "on"})


def _read_int_env(name: str, default: int) -> int:
    raw = os.environ.get(name, "").strip()
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _today_str() -> str:
    return dt.date.today().strftime("%Y-%m-%d")


def _default_out_dir() -> Path:
    return Path("logs") / "ci" / _today_str()


def _resolve_out_dir(cli_out_dir: str, test_mode: bool) -> Path:
    if test_mode:
        env_out_dir = os.environ.get(QUALITY_GATES_TEST_OUT_DIR_ENV, "").strip()
        if env_out_dir:
            return Path(env_out_dir)
    if cli_out_dir:
        return Path(cli_out_dir)
    return _default_out_dir()


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def _normalize_dotnet_summary(path: Path) -> dict[str, Any]:
    payload = _read_json(path)
    status = str(payload.get("status") or "missing").strip() or "missing"
    threshold_ok = bool(payload.get("threshold_ok", False))

    coverage_obj = payload.get("coverage")
    coverage = coverage_obj if isinstance(coverage_obj, dict) else {}
    line_pct = float(coverage.get("line_pct") or coverage.get("lines_pct") or 0.0)
    branch_pct = float(coverage.get("branch_pct") or coverage.get("branches_pct") or 0.0)
    lines_min = float(coverage.get("lines_min") or 90.0)
    branches_min = float(coverage.get("branches_min") or 85.0)

    if status == "missing":
        threshold_ok = False

    return {
        "status": status,
        "threshold_ok": threshold_ok,
        "coverage": {
            "line_pct": line_pct,
            "branch_pct": branch_pct,
            "lines_min": lines_min,
            "branches_min": branches_min,
        },
        "summary_path": str(path).replace("\\", "/"),
    }


def _load_run_summary(path: Path) -> dict[str, Any] | None:
    summary = _read_json(path)
    if not summary:
        return None
    return summary


def _should_run_real_validation_in_test(out_dir: Path, date: str) -> bool:
    expected = (Path.cwd() / "logs" / "ci" / date).resolve()
    try:
        return out_dir.resolve() == expected
    except Exception:
        return False


def _run_validate_perf(*, date: str, out_path: Path, test_mode: bool, run_real: bool) -> int:
    max_p95 = os.environ.get("PERF_P95_THRESHOLD_MS", "16.6").strip() or "16.6"
    if test_mode and not run_real:
        rc = _read_int_env(QUALITY_GATES_TEST_PERF_RC_ENV, 0)
        p95 = 10.0 if rc == 0 else 999.0
        payload = {
            "cmd": "validate_perf",
            "date": date,
            "ok": rc == 0,
            "max_p95_ms": float(max_p95),
            "p95_ms": p95,
            "perf_summary_path": "(quality-gates-test-mode-simulated)",
            "errors": [] if rc == 0 else ["simulated_perf_failure"],
        }
        _write_json(out_path, payload)
        print(f"VALIDATE_PERF status={'ok' if rc == 0 else 'fail'} p95_ms={p95:.2f} max_p95_ms={float(max_p95):.2f}")
        return rc

    cmd = [
        "py",
        "-3",
        "scripts/python/validate_perf.py",
        "--date",
        date,
        "--out",
        str(out_path),
        "--max-p95-ms",
        max_p95,
    ]
    rc, _ = _run_capture(cmd)
    return rc


def _run_validate_audit(*, date: str, out_path: Path, test_mode: bool, run_real: bool) -> int:
    if test_mode and not run_real:
        rc = _read_int_env(QUALITY_GATES_TEST_AUDIT_RC_ENV, 0)
        payload = {
            "cmd": "validate_audit_logs",
            "date": date,
            "ok": rc == 0,
            "audit_path": "(quality-gates-test-mode-simulated)",
            "required_keys": ["ts", "action", "reason", "target", "caller"],
            "nonempty_lines": 1 if rc == 0 else 0,
            "valid_lines": 1 if rc == 0 else 0,
            "results": [] if rc == 0 else [{"line": 1, "ok": False, "error": "simulated_audit_failure"}],
            "errors": [] if rc == 0 else ["simulated_audit_failure"],
        }
        _write_json(out_path, payload)
        print(f"VALIDATE_AUDIT_LOGS status={'ok' if rc == 0 else 'fail'} lines={payload['nonempty_lines']} valid={payload['valid_lines']}")
        return rc

    cmd = [
        "py",
        "-3",
        "scripts/python/validate_audit_logs.py",
        "--date",
        date,
        "--out",
        str(out_path),
    ]
    rc, _ = _run_capture(cmd)
    return rc


def _write_success_placeholder(path: Path, payload: dict[str, Any]) -> None:
    _write_json(path, payload)


def _run_architecture_hotspots(*, out_path: Path, test_mode: bool) -> int:
    if test_mode:
        rc = _read_int_env(QUALITY_GATES_TEST_ARCH_HOTSPOTS_RC_ENV, 0)
        payload = {
            "status": "ok" if rc == 0 else "fail",
            "reason": "quality_gates_test_mode",
            "violations": [] if rc == 0 else [{"type": "simulated_architecture_hotspot_failure"}],
        }
        _write_json(out_path, payload)
        return rc

    cmd = [
        "py",
        "-3",
        "scripts/python/check_architecture_hotspots.py",
        "--out",
        str(out_path),
    ]
    rc, _ = _run_capture(cmd)
    return rc


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
    original_exit_on_ready = os.environ.get("GD_SMOKE_EXIT_ON_READY")
    original_exit_delay = os.environ.get("GD_SMOKE_EXIT_DELAY_SEC")
    os.environ["GD_SMOKE_EXIT_ON_READY"] = "1"
    os.environ["GD_SMOKE_EXIT_DELAY_SEC"] = "0.25"
    try:
        return _run(build_smoke_headless_cmd(godot_bin=godot_bin))
    finally:
        if original_exit_on_ready is None:
            os.environ.pop("GD_SMOKE_EXIT_ON_READY", None)
        else:
            os.environ["GD_SMOKE_EXIT_ON_READY"] = original_exit_on_ready
        if original_exit_delay is None:
            os.environ.pop("GD_SMOKE_EXIT_DELAY_SEC", None)
        else:
            os.environ["GD_SMOKE_EXIT_DELAY_SEC"] = original_exit_delay


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_all = sub.add_parser(
        "all",
        help="run hard gate bundle with optional GdUnit hard and smoke follow-up steps",
    )
    p_all.add_argument("--solution", default="Game.sln")
    p_all.add_argument("--configuration", default="Debug")
    p_all.add_argument("--build-solutions", action="store_true")
    p_all.add_argument("--godot-bin", default="")
    p_all.add_argument("--delivery-profile", default="")
    p_all.add_argument("--task-file", action="append", default=[])
    p_all.add_argument("--out-dir", default="")
    p_all.add_argument("--run-id", default="")
    p_all.add_argument("--gdunit-hard", action="store_true", help="run hard GdUnit set (Adapters/Config + Security)")
    p_all.add_argument("--gdunit-ui", action="store_true", help=argparse.SUPPRESS)
    p_all.add_argument("--coverage-soft", action="store_true", help=argparse.SUPPRESS)
    p_all.add_argument("--smoke", action="store_true", help="run strict headless smoke after the hard gate bundle")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.cmd != "all":
        print("Unsupported command", file=sys.stderr)
        return 1

    test_mode = _is_truthy_env(QUALITY_GATES_TEST_MODE_ENV)
    out_dir = _resolve_out_dir(args.out_dir, test_mode)
    out_dir.mkdir(parents=True, exist_ok=True)
    summary_path = out_dir / QUALITY_GATES_SUMMARY_FILE
    date = _today_str()

    gdunit_requested = bool(args.gdunit_hard or args.gdunit_ui)
    if (gdunit_requested or args.smoke) and not args.godot_bin:
        print("[quality_gates] error: --godot-bin is required when --gdunit-hard or --smoke is enabled", file=sys.stderr)
        return 2

    task_files = list(args.task_file or DEFAULT_GATE_BUNDLE_TASK_FILES)
    if test_mode:
        gate_bundle_rc = _read_int_env(QUALITY_GATES_TEST_CI_PIPELINE_RC_ENV, 0)
    else:
        gate_bundle_rc = run_gate_bundle_hard(
            delivery_profile=args.delivery_profile,
            task_files=task_files,
            out_dir=args.out_dir,
            run_id=args.run_id,
        )

    dotnet_summary_path = os.environ.get(QUALITY_GATES_TEST_DOTNET_SUMMARY_JSON_ENV, "").strip() if test_mode else ""
    if not dotnet_summary_path:
        dotnet_summary_path = str(Path("logs") / "unit" / date / "summary.json")
    dotnet = _normalize_dotnet_summary(Path(dotnet_summary_path))
    coverage_mode = "soft" if args.coverage_soft else "hard"

    dotnet_status = str(dotnet.get("status") or "")
    dotnet_threshold_ok = bool(dotnet.get("threshold_ok"))
    dotnet_coverage_failed = (dotnet_status == "coverage_failed") or (not dotnet_threshold_ok)
    dotnet_tests_failed = dotnet_status == "tests_failed"
    dotnet_missing_or_invalid = dotnet_status in {"missing", "invalid"}
    dotnet_hard_failed = dotnet_tests_failed or dotnet_missing_or_invalid or (
        dotnet_coverage_failed and coverage_mode == "hard"
    )

    gdunit_rc = 0
    gdunit_run_summary_path = ""
    gdunit_run_summary: dict[str, Any] | None = None
    gdunit_report_dir = ""
    if gdunit_requested:
        if test_mode:
            gdunit_rc = _read_int_env(QUALITY_GATES_TEST_GDUNIT_RC_ENV, 0)
            gdunit_run_summary_path = os.environ.get(QUALITY_GATES_TEST_GDUNIT_RUN_SUMMARY_JSON_ENV, "").strip()
            gdunit_report_dir = os.environ.get("QUALITY_GATES_TEST_GDUNIT_REPORT_DIR", "").strip()
        else:
            gdunit_rc = run_gdunit_hard(args.godot_bin)
            gdunit_run_summary_path = str(Path("logs") / "e2e" / "quality-gates" / "gdunit-hard" / "run-summary.json")
            gdunit_report_dir = str(Path("logs") / "e2e" / "quality-gates" / "gdunit-hard")

        if gdunit_run_summary_path:
            gdunit_run_summary = _load_run_summary(Path(gdunit_run_summary_path))

    smoke_rc = 0
    if args.smoke:
        if test_mode:
            smoke_rc = _read_int_env(QUALITY_GATES_TEST_SMOKE_RC_ENV, 0)
        else:
            smoke_rc = run_smoke_headless(args.godot_bin)

    arch_out = out_dir / "architecture-hotspots-summary.json"
    perf_artifact = out_dir / "quality-gates-perf.json"
    audit_artifact = out_dir / "quality-gates-audit.json"
    extended_gates_enabled = test_mode or _is_truthy_env(QUALITY_GATES_ENABLE_EXTENDED_GATES_ENV)

    if extended_gates_enabled:
        arch_rc = _run_architecture_hotspots(out_path=arch_out, test_mode=test_mode)
        run_real_validators = (not test_mode) or _should_run_real_validation_in_test(out_dir, date)
        perf_rc = _run_validate_perf(date=date, out_path=perf_artifact, test_mode=test_mode, run_real=run_real_validators)
        audit_rc = _run_validate_audit(date=date, out_path=audit_artifact, test_mode=test_mode, run_real=run_real_validators)
    else:
        arch_rc = 0
        perf_rc = 0
        audit_rc = 0
        _write_success_placeholder(
            arch_out,
            {
                "status": "ok",
                "reason": "extended_gates_disabled",
                "enabled": False,
            },
        )
        _write_success_placeholder(
            perf_artifact,
            {
                "cmd": "validate_perf",
                "date": date,
                "ok": True,
                "reason": "extended_gates_disabled",
            },
        )
        _write_success_placeholder(
            audit_artifact,
            {
                "cmd": "validate_audit_logs",
                "date": date,
                "ok": True,
                "reason": "extended_gates_disabled",
            },
        )

    hard_failed = any(
        [
            gate_bundle_rc != 0,
            dotnet_hard_failed,
            gdunit_rc != 0,
            smoke_rc != 0,
            arch_rc != 0,
            perf_rc != 0,
            audit_rc != 0,
        ]
    )
    status = "fail" if hard_failed else "ok"

    summary: dict[str, Any] = {
        "status": status,
        "coverage_mode": coverage_mode,
        "dotnet": dotnet,
        "gdunit_hard": {
            "enabled": gdunit_requested,
            "rc": gdunit_rc,
            "report_dir": gdunit_report_dir,
            "run_summary_path": gdunit_run_summary_path,
            "run_summary": gdunit_run_summary,
        },
        "smoke": {
            "enabled": bool(args.smoke),
            "rc": smoke_rc,
        },
        "architecture_hotspots": {
            "enabled": bool(extended_gates_enabled),
            "rc": arch_rc,
            "summary_path": str(arch_out).replace("\\", "/"),
        },
        "perf": {
            "enabled": bool(extended_gates_enabled),
            "rc": perf_rc,
        },
        "audit": {
            "enabled": bool(extended_gates_enabled),
            "rc": audit_rc,
        },
        "artifacts": {
            "quality_gates_perf": str(perf_artifact).replace("\\", "/"),
            "quality_gates_audit": str(audit_artifact).replace("\\", "/"),
            "quality_gates_summary": str(summary_path).replace("\\", "/"),
        },
    }
    _write_json(summary_path, summary)

    print(
        "QUALITY_GATES "
        f"status={status} "
        f"out={str(summary_path).replace('\\', '/')} "
        f"coverage_mode={coverage_mode} "
        f"dotnet={dotnet_status} "
        f"gate_bundle_rc={gate_bundle_rc} "
        f"gdunit_rc={gdunit_rc} "
        f"arch_rc={arch_rc} "
        f"perf_rc={perf_rc} "
        f"audit_rc={audit_rc}"
    )
    return 0 if not hard_failed else 1


if __name__ == "__main__":
    sys.exit(main())
