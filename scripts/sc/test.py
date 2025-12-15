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
import shutil
from pathlib import Path
from typing import Any

from _util import ci_dir, repo_root, run_cmd, today_str, write_json, write_text


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description="sc-test (test shim)")
    ap.add_argument("--type", choices=["unit", "integration", "e2e", "all"], default="all")
    ap.add_argument("--solution", default="Game.sln")
    ap.add_argument("--configuration", default="Debug")
    ap.add_argument("--godot-bin", default=None, help="Godot mono console binary (required for e2e/all)")
    ap.add_argument("--smoke-scene", default="res://Game.Godot/Scenes/Main.tscn", help="Main scene for smoke test")
    ap.add_argument("--timeout-sec", type=int, default=600)
    ap.add_argument("--skip-smoke", action="store_true")
    ap.add_argument("--no-coverage-gate", action="store_true", help="do not enforce default coverage thresholds")
    ap.add_argument("--no-coverage-report", action="store_true", help="skip HTML coverage report generation")
    return ap


def run_unit(out_dir: Path, solution: str, configuration: str) -> dict[str, Any]:
    cmd = ["py", "-3", "scripts/python/run_dotnet.py", "--solution", solution, "--configuration", configuration]
    rc, out = run_cmd(cmd, cwd=repo_root(), timeout_sec=1_800)
    log_path = out_dir / "unit.log"
    write_text(log_path, out)
    unit_artifacts_dir = repo_root() / "logs" / "unit" / today_str()
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


def run_gdunit_hard(out_dir: Path, godot_bin: str, timeout_sec: int) -> dict[str, Any]:
    date = today_str()
    report_dir = Path("logs") / "e2e" / date / "sc-test" / "gdunit-hard"

    add_dirs: list[str] = []
    for rel in ["tests/Scenes", "tests/Adapters/Config", "tests/Security/Hard"]:
        if (repo_root() / rel).exists():
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
    return {"name": "gdunit-hard", "cmd": cmd, "rc": rc, "log": str(log_path), "report_dir": str(report_dir)}


def run_smoke(out_dir: Path, godot_bin: str, scene: str) -> dict[str, Any]:
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
        "--project",
        ".",
        "--scene",
        scene,
        "--timeout-sec",
        "5",
        "--mode",
        "strict",
    ]
    rc, out = run_cmd(cmd, cwd=repo_root(), timeout_sec=120)
    log_path = out_dir / "smoke.log"
    write_text(log_path, out)
    return {"name": "smoke", "cmd": cmd, "rc": rc, "log": str(log_path)}


def main() -> int:
    args = build_parser().parse_args()
    out_dir = ci_dir("sc-test")

    godot_bin = args.godot_bin or os.environ.get("GODOT_BIN")

    summary: dict[str, Any] = {
        "cmd": "sc-test",
        "type": args.type,
        "solution": args.solution,
        "configuration": args.configuration,
        "status": "fail",
        "steps": [],
    }

    hard_fail = False

    if args.type in ("unit", "all"):
        if not args.no_coverage_gate:
            os.environ.setdefault("COVERAGE_LINES_MIN", "90")
            os.environ.setdefault("COVERAGE_BRANCHES_MIN", "85")

        step = run_unit(out_dir, args.solution, args.configuration)
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

        step = run_gdunit_hard(out_dir, godot_bin, args.timeout_sec)
        summary["steps"].append(step)
        if step["rc"] != 0:
            hard_fail = True

        if not args.skip_smoke:
            sm = run_smoke(out_dir, godot_bin, args.smoke_scene)
            summary["steps"].append(sm)
            if sm["rc"] != 0:
                hard_fail = True

    summary["status"] = "ok" if not hard_fail else "fail"
    write_json(out_dir / "summary.json", summary)

    print(f"SC_TEST status={summary['status']} out={out_dir}")
    return 0 if not hard_fail else 1


if __name__ == "__main__":
    raise SystemExit(main())
