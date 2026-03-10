#!/usr/bin/env python3
"""Windows quality gates entry for Godot+C#."""
import argparse
import datetime as dt
import io
import json
import os
import subprocess
import sys


def run_ci_pipeline(solution: str, configuration: str, godot_bin: str, build_solutions: bool) -> int:
    args = [
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
    ]
    if build_solutions:
        args.append("--build-solutions")

    proc = subprocess.run(args, text=True)
    return proc.returncode


def _read_json(path: str) -> dict:
    try:
        with io.open(path, "r", encoding="utf-8") as f:
            obj = json.load(f)
        return obj if isinstance(obj, dict) else {}
    except Exception:
        return {}


def _write_json(path: str, obj: dict) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with io.open(path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
        f.write("\n")


def _as_bool(value: str | None) -> bool:
    v = str(value or "").strip().lower()
    return v in ("1", "true", "yes", "y", "on")


def _as_int(value: str | None, *, default: int) -> int:
    try:
        return int(str(value or "").strip())
    except Exception:
        return default


def run_perf_and_audit_validators(*, date: str, ci_dir: str) -> tuple[int, dict]:
    """Run Task 39 validators and emit stable artifacts under logs/ci/<date>/."""

    # Keep this gate non-disruptive for tasks that do not produce perf/audit artifacts yet.
    # Task 39 expects missing inputs to be a hard failure (but still produce artifacts),
    # so we always invoke the validators when the output directory matches logs/ci/<date>.
    root = os.getcwd()
    expected_ci_dir = os.path.abspath(os.path.join(root, "logs", "ci", date))
    actual_ci_dir = os.path.abspath(ci_dir)
    if actual_ci_dir != expected_ci_dir:
        return 0, {
            "enabled": False,
            "rc": 0,
            "reason": "out_dir_not_date_ci_dir",
            "expected_ci_dir": expected_ci_dir,
            "actual_ci_dir": actual_ci_dir,
        }

    perf_in = os.path.join(root, "logs", "perf", date, "summary.json")
    audit_in = os.path.join(root, "logs", "ci", date, "security-audit.jsonl")

    perf_out = os.path.join(ci_dir, "quality-gates-perf.json")
    audit_out = os.path.join(ci_dir, "quality-gates-audit.json")

    perf_args = [
        "py",
        "-3",
        "scripts/python/validate_perf.py",
        "--date",
        date,
        "--out",
        perf_out,
    ]
    audit_args = [
        "py",
        "-3",
        "scripts/python/validate_audit_logs.py",
        "--date",
        date,
        "--out",
        audit_out,
    ]

    perf_rc = subprocess.run(perf_args, text=True).returncode
    audit_rc = subprocess.run(audit_args, text=True).returncode
    rc = 0 if (perf_rc == 0 and audit_rc == 0) else 1

    details = {
        "enabled": True,
        "rc": rc,
        "inputs": {"perf_summary": perf_in, "security_audit_jsonl": audit_in},
        "perf": {"rc": perf_rc, "out": perf_out},
        "audit": {"rc": audit_rc, "out": audit_out},
    }
    return rc, details


def run_gdunit_hard(*, godot_bin: str, date: str) -> tuple[int, str]:
    """Run the hard-gate GdUnit4 subset (Adapters/Config + Security).

    Design goals:
    - Keep aligned with the hard-gate set in ci-windows.yml.
    - Write reports to logs/e2e/<date>/quality-gates/gdunit-hard.
    """

    report_dir = os.path.join("logs", "e2e", date, "quality-gates", "gdunit-hard")
    args = [
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
    proc = subprocess.run(args, text=True)
    return proc.returncode, report_dir


def run_gdunit_ui(*, godot_bin: str, date: str) -> tuple[int, str]:
    """Run the UI GdUnit4 suite (tests/UI)."""

    report_dir = os.path.join("logs", "e2e", date, "quality-gates", "gdunit-ui")
    args = [
        "py",
        "-3",
        "scripts/python/run_gdunit.py",
        "--prewarm",
        "--godot-bin",
        godot_bin,
        "--project",
        "Tests.Godot",
        "--add",
        "tests/UI",
        "--timeout-sec",
        "480",
        "--rd",
        report_dir,
    ]
    proc = subprocess.run(args, text=True)
    return proc.returncode, report_dir


def run_smoke_headless(*, godot_bin: str, timeout_sec: int) -> tuple[int, str]:
    """Run the Python headless smoke in strict mode.

    - Uses the Main scene as entry.
    - mode=strict requires marker/DB plus clean exit code (see smoke_headless.py).
    """

    args = [
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
        "--mode",
        "strict",
    ]
    env = dict(os.environ)
    # Prefer deterministic exit over timeout kill in strict mode.
    env["GD_SMOKE_EXIT_ON_READY"] = env.get("GD_SMOKE_EXIT_ON_READY") or "1"
    # Give perf/audit writers time to flush before quitting.
    env["GD_SMOKE_EXIT_DELAY_SEC"] = env.get("GD_SMOKE_EXIT_DELAY_SEC") or "2"
    proc = subprocess.run(args, text=True, env=env)
    return proc.returncode, env["GD_SMOKE_EXIT_ON_READY"]


def run_architecture_hotspots(*, ci_dir: str) -> tuple[int, str]:
    summary_path = os.path.join(ci_dir, "architecture-hotspots-summary.json")
    args = [
        "py",
        "-3",
        "scripts/python/check_architecture_hotspots.py",
        "--out",
        summary_path,
    ]
    proc = subprocess.run(args, text=True)
    return proc.returncode, summary_path


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_all = sub.add_parser("all", help="run quality gates (ci_pipeline + optional GdUnit/Smoke)")
    p_all.add_argument("--solution", default="Game.sln")
    p_all.add_argument("--configuration", default="Debug")
    p_all.add_argument("--godot-bin", required=True)
    p_all.add_argument("--build-solutions", action="store_true")
    p_all.add_argument("--gdunit-hard", action="store_true", help="run hard GdUnit set (Adapters/Config + Security)")
    p_all.add_argument("--gdunit-ui", action="store_true", help="run UI GdUnit suite (tests/UI)")
    p_all.add_argument("--smoke", action="store_true", help="run headless smoke (strict marker/DB check)")
    p_all.add_argument("--smoke-timeout-sec", type=int, default=120, help="smoke timeout seconds (default 120)")
    p_all.add_argument("--coverage-soft", action="store_true", help="treat coverage gate as soft (default hard)")

    args = parser.parse_args()

    if args.cmd == "all":
        date = dt.date.today().strftime("%Y-%m-%d")
        ci_dir = os.path.join("logs", "ci", date)

        test_mode = _as_bool(os.environ.get("QUALITY_GATES_TEST_MODE"))
        if test_mode:
            ci_dir = str(os.environ.get("QUALITY_GATES_TEST_OUT_DIR") or "").strip() or ci_dir
        os.makedirs(ci_dir, exist_ok=True)

        # 1) Base gates: dotnet + self-check + encoding scan.
        if test_mode:
            rc = _as_int(os.environ.get("QUALITY_GATES_TEST_CI_PIPELINE_RC"), default=0)
        else:
            rc = run_ci_pipeline(args.solution, args.configuration, args.godot_bin, args.build_solutions)
        hard_failed = rc != 0

        # Collect dotnet summary (coverage + thresholds) for downstream reporting.
        if test_mode:
            dotnet_summary_path = str(os.environ.get("QUALITY_GATES_TEST_DOTNET_SUMMARY_JSON") or "").strip()
            dotnet_summary = _read_json(dotnet_summary_path) if dotnet_summary_path else {}
        else:
            dotnet_summary_path = os.path.join("logs", "unit", date, "summary.json")
            dotnet_summary = _read_json(dotnet_summary_path)
        dotnet_status = str(dotnet_summary.get("status") or "")
        dotnet_coverage = dotnet_summary.get("coverage") if isinstance(dotnet_summary.get("coverage"), dict) else {}

        # Optional: surface ci_pipeline summary details (content pack gate, etc.)
        ci_pipeline_summary_path = os.path.join(ci_dir, "ci-pipeline-summary.json")
        ci_pipeline_summary = _read_json(ci_pipeline_summary_path) if os.path.isfile(ci_pipeline_summary_path) else {}
        content_packs = ci_pipeline_summary.get("content_packs") if isinstance(ci_pipeline_summary, dict) else {}

        # Default: treat coverage as a hard gate unless explicitly configured as soft.
        coverage_ok = bool(dotnet_summary.get("threshold_ok")) if isinstance(dotnet_summary, dict) else False
        coverage_failed = dotnet_status == "coverage_failed" or (dotnet_status == "ok" and not coverage_ok)
        if coverage_failed and not args.coverage_soft:
            hard_failed = True

        # 2) Optional hard gate: headless smoke (strict).
        smoke = {"enabled": bool(args.smoke)}
        if args.smoke:
            if test_mode:
                sm_rc = _as_int(os.environ.get("QUALITY_GATES_TEST_SMOKE_RC"), default=0)
                exit_on_ready = str(os.environ.get("GD_SMOKE_EXIT_ON_READY") or "1")
            else:
                sm_rc, exit_on_ready = run_smoke_headless(
                    godot_bin=args.godot_bin, timeout_sec=int(args.smoke_timeout_sec)
                )
            smoke["rc"] = sm_rc
            smoke["timeout_sec"] = int(args.smoke_timeout_sec)
            smoke["exit_on_ready"] = exit_on_ready
            if sm_rc != 0:
                hard_failed = True

        # 2.5) Task 39: Perf P95 + audit JSONL validators (hard gate).
        # Must run after smoke to ensure logs/perf/<date>/summary.json and logs/ci/<date>/security-audit.jsonl exist.
        perf_audit = {"enabled": True}
        perf_audit_rc, perf_audit_details = run_perf_and_audit_validators(date=date, ci_dir=ci_dir)
        perf_audit.update(perf_audit_details)
        if perf_audit_rc != 0:
            hard_failed = True

        architecture_hotspots = {"enabled": True}
        if test_mode:
            ah_rc = _as_int(os.environ.get("QUALITY_GATES_TEST_ARCH_HOTSPOTS_RC"), default=0)
            ah_summary_path = str(os.environ.get("QUALITY_GATES_TEST_ARCH_HOTSPOTS_SUMMARY") or "").strip() or os.path.join(
                ci_dir, "architecture-hotspots-summary.json")
        else:
            ah_rc, ah_summary_path = run_architecture_hotspots(ci_dir=ci_dir)
        architecture_hotspots["rc"] = ah_rc
        architecture_hotspots["summary_path"] = ah_summary_path
        architecture_hotspots["summary"] = _read_json(ah_summary_path) if os.path.isfile(ah_summary_path) else {}
        if ah_rc != 0:
            hard_failed = True

        # 3) Optional hard gate: GdUnit subset.
        gdunit = {"enabled": bool(args.gdunit_hard)}
        gdunit_rc = None
        gdunit_report_dir = None
        if args.gdunit_hard:
            if test_mode:
                gd_rc = _as_int(os.environ.get("QUALITY_GATES_TEST_GDUNIT_RC"), default=0)
                report_dir = str(os.environ.get("QUALITY_GATES_TEST_GDUNIT_REPORT_DIR") or "").strip() or os.path.join(
                    ci_dir, "gdunit-hard"
                )
                os.makedirs(report_dir, exist_ok=True)
                run_summary_path = str(os.environ.get("QUALITY_GATES_TEST_GDUNIT_RUN_SUMMARY_JSON") or "").strip()
                if run_summary_path and os.path.isfile(run_summary_path):
                    gdunit["run_summary_path"] = run_summary_path
                    gdunit["run_summary"] = _read_json(run_summary_path)
            else:
                gd_rc, report_dir = run_gdunit_hard(godot_bin=args.godot_bin, date=date)
            gdunit_rc = gd_rc
            gdunit_report_dir = report_dir
            gdunit["rc"] = gd_rc
            gdunit["report_dir"] = report_dir
            if not test_mode:
                run_summary_path = os.path.join(report_dir, "run-summary.json")
                gdunit["run_summary_path"] = run_summary_path
                gdunit["run_summary"] = _read_json(run_summary_path) if os.path.isfile(run_summary_path) else {}
            if gd_rc != 0:
                hard_failed = True

        gdunit_ui = {"enabled": bool(args.gdunit_ui)}
        gdunit_ui_rc = None
        gdunit_ui_report_dir = None
        if args.gdunit_ui:
            if test_mode:
                gd_ui_rc = _as_int(os.environ.get("QUALITY_GATES_TEST_GDUNIT_UI_RC"), default=0)
                report_dir = str(os.environ.get("QUALITY_GATES_TEST_GDUNIT_UI_REPORT_DIR") or "").strip() or os.path.join(
                    ci_dir, "gdunit-ui"
                )
                os.makedirs(report_dir, exist_ok=True)
                run_summary_path = str(os.environ.get("QUALITY_GATES_TEST_GDUNIT_UI_RUN_SUMMARY_JSON") or "").strip()
                if run_summary_path and os.path.isfile(run_summary_path):
                    gdunit_ui["run_summary_path"] = run_summary_path
                    gdunit_ui["run_summary"] = _read_json(run_summary_path)
            else:
                gd_ui_rc, report_dir = run_gdunit_ui(godot_bin=args.godot_bin, date=date)
            gdunit_ui_rc = gd_ui_rc
            gdunit_ui_report_dir = report_dir
            gdunit_ui["rc"] = gd_ui_rc
            gdunit_ui["report_dir"] = report_dir
            if not test_mode:
                run_summary_path = os.path.join(report_dir, "run-summary.json")
                gdunit_ui["run_summary_path"] = run_summary_path
                gdunit_ui["run_summary"] = _read_json(run_summary_path) if os.path.isfile(run_summary_path) else {}
            if gd_ui_rc != 0:
                hard_failed = True

        # Aggregate a stable summary for CI/ops.
        quality_gates_summary_path = os.path.join(ci_dir, "quality-gates-summary.json")
        summary = {
            "cmd": "quality_gates",
            "date": date,
            "solution": args.solution,
            "configuration": args.configuration,
            "status": "ok" if not hard_failed else "fail",
            "coverage_mode": "soft" if args.coverage_soft else "hard",
            "dotnet": {
                "status": dotnet_status,
                "threshold_ok": bool(dotnet_summary.get("threshold_ok")) if isinstance(dotnet_summary, dict) else False,
                "coverage": dotnet_coverage,
                "summary_path": dotnet_summary_path,
            },
            "content_packs": content_packs,
            "ci_pipeline_summary_path": ci_pipeline_summary_path,
            "perf_audit": perf_audit,
            "architecture_hotspots": architecture_hotspots,
            "gdunit_hard": gdunit,
            "gdunit_ui": gdunit_ui,
            "smoke": smoke,
            "artifacts": {
                "quality_gates_summary": quality_gates_summary_path,
                "quality_gates_perf": os.path.join(ci_dir, "quality-gates-perf.json"),
                "quality_gates_audit": os.path.join(ci_dir, "quality-gates-audit.json"),
            },
        }
        _write_json(quality_gates_summary_path, summary)
        print(f"QUALITY_GATES status={summary['status']} out={ci_dir} summary={quality_gates_summary_path}")

        return 0 if not hard_failed else 1

    print("Unsupported command", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
