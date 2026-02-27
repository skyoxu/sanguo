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
import json
import os
import shutil
import uuid
from pathlib import Path
from typing import Any

from _util import ci_dir, repo_root, run_cmd, today_str, write_json, write_text


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description="sc-test (test shim)")
    ap.add_argument("--type", choices=["unit", "integration", "e2e", "all"], default="all")
    ap.add_argument("--solution", default="Game.sln")
    ap.add_argument("--configuration", default="Debug")
    ap.add_argument("--godot-bin", default=None, help="Godot mono console binary (required for e2e/all)")
    ap.add_argument("--run-id", default=None, help="Optional run identifier for evidence binding (default: auto-generate).")
    ap.add_argument("--smoke-scene", default="res://Game.Godot/Scenes/Main.tscn", help="Main scene for smoke test")
    ap.add_argument(
        "--smoke-timeout-sec",
        type=int,
        default=120,
        help="Smoke timeout seconds for scripts/python/smoke_headless.py (default 120).",
    )
    ap.add_argument("--timeout-sec", type=int, default=600)
    ap.add_argument("--skip-smoke", action="store_true")
    ap.add_argument("--include-sanguo-saveload-restart", action="store_true", help="Run Sanguo save/load restart e2e proof (two-process).")
    ap.add_argument("--no-coverage-gate", action="store_true", help="do not enforce default coverage thresholds")
    ap.add_argument("--no-coverage-report", action="store_true", help="skip HTML coverage report generation")
    return ap


def run_unit(out_dir: Path, solution: str, configuration: str, *, run_id: str) -> dict[str, Any]:
    cmd = ["py", "-3", "scripts/python/run_dotnet.py", "--solution", solution, "--configuration", configuration]
    rc, out = run_cmd(cmd, cwd=repo_root(), timeout_sec=1_800)
    log_path = out_dir / "unit.log"
    write_text(log_path, out)
    unit_artifacts_dir = repo_root() / "logs" / "unit" / today_str()
    write_text(unit_artifacts_dir / "run_id.txt", run_id + "\n")
    return {"name": "unit", "cmd": cmd, "rc": rc, "log": str(log_path), "artifacts_dir": str(unit_artifacts_dir)}


def run_coverage_report(out_dir: Path, unit_artifacts_dir: Path) -> dict[str, Any]:
    reportgenerator = shutil.which("reportgenerator")
    if not reportgenerator:
        return {
            "name": "coverage-report",
            "status": "skipped",
            "reason": "reportgenerator not found (install once via: dotnet tool install --global dotnet-reportgenerator-globaltool)",
        }

    cobertura = unit_artifacts_dir / "coverage.cobertura.xml"
    if not cobertura.exists():
        return {
            "name": "coverage-report",
            "status": "skipped",
            "reason": f"coverage file not found: {cobertura}",
        }

    target_dir = unit_artifacts_dir / "coverage-report"
    cmd = [
        "reportgenerator",
        f"-reports:{cobertura}",
        f"-targetdir:{target_dir}",
        "-reporttypes:Html",
    ]
    rc, out = run_cmd(cmd, cwd=repo_root(), timeout_sec=300)
    log_path = out_dir / "coverage-report.log"
    write_text(log_path, out)
    return {
        "name": "coverage-report",
        "cmd": cmd,
        "rc": rc,
        "log": str(log_path),
        "report_dir": str(target_dir),
        "status": "ok" if rc == 0 else "fail",
    }


def run_gdunit_hard(out_dir: Path, godot_bin: str, timeout_sec: int, *, run_id: str) -> dict[str, Any]:
    date = today_str()
    report_dir = Path("logs") / "e2e" / date / "sc-test" / "gdunit-hard"
    os.environ["AUDIT_LOG_ROOT"] = str(repo_root() / "logs" / "ci" / date)

    add_dirs: list[str] = []
    tests_project = repo_root() / "Tests.Godot"
    for rel in ["tests/Scenes", "tests/UI", "tests/Adapters/Config", "tests/Security/Hard"]:
        if (tests_project / rel).exists():
            add_dirs.append(rel)
        elif (repo_root() / rel).exists():
            # Backward-compatible fallback for repos that keep GdUnit suites at repo root.
            add_dirs.append(rel)

    cmd = [
        "py",
        "-3",
        "scripts/python/run_gdunit.py",
        "--prewarm",
        "--godot-bin",
        godot_bin,
        "--project",
        "Tests.Godot",
    ]
    for d in add_dirs:
        cmd += ["--add", d]
    cmd += ["--timeout-sec", str(timeout_sec), "--rd", str(report_dir)]
    rc, out = run_cmd(cmd, cwd=repo_root(), timeout_sec=timeout_sec + 300)
    log_path = out_dir / "gdunit-hard.log"
    write_text(log_path, out)
    write_text(repo_root() / report_dir / "run_id.txt", run_id + "\n")
    # Surface GdUnit console output into logs/ci for CI forensics (workflows usually upload logs/ci but not logs/e2e).
    try:
        console_src = repo_root() / report_dir / "gdunit-console.txt"
        if console_src.exists():
            console_dst = out_dir / "gdunit-hard-console.txt"
            write_text(console_dst, console_src.read_text(encoding="utf-8", errors="ignore"))
    except Exception:
        pass
    return {"name": "gdunit-hard", "cmd": cmd, "rc": rc, "log": str(log_path), "report_dir": str(report_dir)}


def run_smoke(out_dir: Path, godot_bin: str, scene: str, *, smoke_timeout_sec: int) -> dict[str, Any]:
    if scene.startswith("res://"):
        disk_path = repo_root() / scene[len("res://") :]
        if not disk_path.exists():
            msg = f"[sc-test] ERROR: smoke scene not found on disk: {disk_path}\n"
            log_path = out_dir / "smoke.log"
            write_text(log_path, msg)
            return {"name": "smoke", "cmd": [], "rc": 2, "log": str(log_path), "error": "smoke_scene_missing"}
    cmd = [
        "py",
        "-3",
        "scripts/python/smoke_headless.py",
        "--godot-bin",
        godot_bin,
        "--project-path",
        ".",
        "--scene",
        scene,
        "--timeout-sec",
        str(smoke_timeout_sec),
        "--mode",
        "strict",
    ]
    # Strict smoke requires a clean exit (see scripts/python/smoke_headless.py).
    # Ensure the project quits deterministically once the first scene reaches ready.
    old_exit_on_ready = os.environ.get("GD_SMOKE_EXIT_ON_READY")
    os.environ.setdefault("GD_SMOKE_EXIT_ON_READY", "1")
    try:
        rc, out = run_cmd(cmd, cwd=repo_root(), timeout_sec=max(30, smoke_timeout_sec + 30))
    finally:
        if old_exit_on_ready is None:
            os.environ.pop("GD_SMOKE_EXIT_ON_READY", None)
        else:
            os.environ["GD_SMOKE_EXIT_ON_READY"] = old_exit_on_ready
    log_path = out_dir / "smoke.log"
    write_text(log_path, out)
    return {"name": "smoke", "cmd": cmd, "rc": rc, "log": str(log_path)}


def run_sanguo_saveload_restart(out_dir: Path, godot_bin: str, *, run_id: str) -> dict[str, Any]:
    cmd = [
        "py",
        "-3",
        "scripts/python/e2e_sanguo_save_load_restart.py",
        "--godot-bin",
        godot_bin,
        "--run-id",
        run_id,
    ]
    rc, out = run_cmd(cmd, cwd=repo_root(), timeout_sec=180)
    log_path = out_dir / "sanguo-saveload-restart.log"
    write_text(log_path, out)
    return {"name": "sanguo-saveload-restart", "cmd": cmd, "rc": rc, "log": str(log_path)}


def _is_truthy(raw: str | None) -> bool:
    return str(raw or "").strip().lower() in {"1", "true", "yes", "on"}


def _validate_coverage_bypass_guard(*, no_coverage_gate: bool) -> tuple[bool, str, dict[str, Any]]:
    details: dict[str, Any] = {
        "enabled": bool(no_coverage_gate),
        "scope": "none",
        "status": "skipped",
    }

    if not no_coverage_gate:
        return True, "", details

    acceptance_scope = _is_truthy(os.environ.get("SC_ACCEPTANCE_NO_COVERAGE_GATE"))
    details["scope"] = "acceptance" if acceptance_scope else "manual"
    if not acceptance_scope:
        details["status"] = "ok"
        return True, "", details

    quality_summary = repo_root() / "logs" / "ci" / today_str() / "quality-gates-summary.json"
    details["quality_gates_summary"] = str(quality_summary)
    if not quality_summary.exists():
        details["status"] = "fail"
        return False, f"quality_gates_summary_missing: {quality_summary}", details

    try:
        payload = json.loads(quality_summary.read_text(encoding="utf-8"))
    except Exception as ex:
        details["status"] = "fail"
        details["error"] = f"quality_gates_summary_parse_error: {ex}"
        return False, details["error"], details

    status = str(payload.get("status") or "").strip().lower()
    details["quality_gates_status"] = status
    if status != "ok":
        details["status"] = "fail"
        return False, f"quality_gates_status_not_ok: {status or 'unknown'}", details

    details["status"] = "ok"
    return True, "", details


def main() -> int:
    args = build_parser().parse_args()
    out_dir = ci_dir("sc-test")
    run_id = str(args.run_id or "").strip() or uuid.uuid4().hex
    write_text(out_dir / "run_id.txt", run_id + "\n")

    godot_bin = args.godot_bin or os.environ.get("GODOT_BIN")
    if godot_bin:
        godot_bin = os.path.expandvars(godot_bin).strip().strip('"')

    summary: dict[str, Any] = {
        "cmd": "sc-test",
        "run_id": run_id,
        "type": args.type,
        "solution": args.solution,
        "configuration": args.configuration,
        "status": "fail",
        "steps": [],
    }

    hard_fail = False

    guard_ok, guard_reason, guard_details = _validate_coverage_bypass_guard(no_coverage_gate=bool(args.no_coverage_gate))
    summary["steps"].append(
        {
            "name": "coverage-bypass-guard",
            "status": "ok" if guard_ok else "fail",
            "rc": 0 if guard_ok else 1,
            "details": guard_details,
        }
    )
    if not guard_ok:
        summary["status"] = "fail"
        write_json(out_dir / "summary.json", summary)
        print(f"SC_TEST status=fail reason={guard_reason} out={out_dir}")
        return 1

    if args.type in ("unit", "all"):
        if args.no_coverage_gate:
            os.environ["COVERAGE_LINES_MIN"] = "0"
            os.environ["COVERAGE_BRANCHES_MIN"] = "0"
        else:
            os.environ.setdefault("COVERAGE_LINES_MIN", "90")
            os.environ.setdefault("COVERAGE_BRANCHES_MIN", "85")

        step = run_unit(out_dir, args.solution, args.configuration, run_id=run_id)
        summary["steps"].append(step)
        if step["rc"] != 0:
            hard_fail = True
        else:
            if not args.no_coverage_report:
                cov = run_coverage_report(out_dir, Path(step["artifacts_dir"]))
                summary["steps"].append(cov)
                if cov.get("status") == "fail":
                    hard_fail = True

    if args.type in ("integration", "e2e", "all"):
        if not godot_bin:
            print("[sc-test] ERROR: --godot-bin (or env GODOT_BIN) is required for e2e/integration tests.")
            return 2

        step = run_gdunit_hard(out_dir, godot_bin, args.timeout_sec, run_id=run_id)
        summary["steps"].append(step)
        if step["rc"] != 0:
            hard_fail = True

        if not args.skip_smoke:
            sm = run_smoke(out_dir, godot_bin, args.smoke_scene, smoke_timeout_sec=int(args.smoke_timeout_sec))
            summary["steps"].append(sm)
            if sm["rc"] != 0:
                hard_fail = True

        if args.include_sanguo_saveload_restart:
            sr = run_sanguo_saveload_restart(out_dir, godot_bin, run_id=run_id)
            summary["steps"].append(sr)
            if sr["rc"] != 0:
                hard_fail = True

    summary["status"] = "ok" if not hard_fail else "fail"
    write_json(out_dir / "summary.json", summary)

    print(f"SC_TEST status={summary['status']} out={out_dir}")
    return 0 if not hard_fail else 1


if __name__ == "__main__":
    raise SystemExit(main())
