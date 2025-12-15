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
from pathlib import Path
from typing import Any

from _util import ci_dir, repo_root, run_cmd, today_str, write_json, write_text


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description="sc-test (test shim)")
    ap.add_argument("--type", choices=["unit", "integration", "e2e", "all"], default="all")
    ap.add_argument("--solution", default="Game.sln")
    ap.add_argument("--configuration", default="Debug")
    ap.add_argument("--godot-bin", default=None, help="Godot mono console binary (required for e2e/all)")
    ap.add_argument("--timeout-sec", type=int, default=600)
    ap.add_argument("--skip-smoke", action="store_true")
    return ap


def run_unit(out_dir: Path, solution: str, configuration: str) -> dict[str, Any]:
    cmd = ["py", "-3", "scripts/python/run_dotnet.py", "--solution", solution, "--configuration", configuration]
    rc, out = run_cmd(cmd, cwd=repo_root(), timeout_sec=1_800)
    log_path = out_dir / "unit.log"
    write_text(log_path, out)
    return {"name": "unit", "cmd": cmd, "rc": rc, "log": str(log_path)}


def run_gdunit_hard(out_dir: Path, godot_bin: str, timeout_sec: int) -> dict[str, Any]:
    date = today_str()
    report_dir = Path("logs") / "e2e" / date / "sc-test" / "gdunit-hard"
    cmd = [
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
        str(timeout_sec),
        "--rd",
        str(report_dir),
    ]
    rc, out = run_cmd(cmd, cwd=repo_root(), timeout_sec=timeout_sec + 300)
    log_path = out_dir / "gdunit-hard.log"
    write_text(log_path, out)
    return {"name": "gdunit-hard", "cmd": cmd, "rc": rc, "log": str(log_path), "report_dir": str(report_dir)}


def run_smoke(out_dir: Path, godot_bin: str) -> dict[str, Any]:
    cmd = [
        "py",
        "-3",
        "scripts/python/smoke_headless.py",
        "--godot-bin",
        godot_bin,
        "--project",
        ".",
        "--scene",
        "res://Game.Godot/Scenes/Main.tscn",
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
        step = run_unit(out_dir, args.solution, args.configuration)
        summary["steps"].append(step)
        if step["rc"] != 0:
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
            sm = run_smoke(out_dir, godot_bin)
            summary["steps"].append(sm)
            if sm["rc"] != 0:
                hard_fail = True

    summary["status"] = "ok" if not hard_fail else "fail"
    write_json(out_dir / "summary.json", summary)

    print(f"SC_TEST status={summary['status']} out={out_dir}")
    return 0 if not hard_fail else 1


if __name__ == "__main__":
    raise SystemExit(main())

