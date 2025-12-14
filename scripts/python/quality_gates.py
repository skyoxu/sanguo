#!/usr/bin/env python3
"""
Quality gates entry for Windows (Godot+C# variant).

Current minimal implementation:
- Delegates to ci_pipeline.py `all` command, which runs:
  * dotnet tests + coverage (soft gate on coverage)
  * Godot self-check (hard gate)
  * encoding scan (soft gate)

Usage (Windows):
  py -3 scripts/python/quality_gates.py all `
    --solution Game.sln --configuration Debug `
    --godot-bin "C:\\Godot\\Godot_v4.5.1-stable_mono_win64_console.exe" `
    --build-solutions

Exit codes:
  0  all hard gates passed
  1  hard gate failed (dotnet tests or self-check)

This script is designed to be extended in Phase 13 to include
additional gates (GdUnit4 sets, smoke, perf, etc.).
"""

import argparse
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


def run_gdunit_hard(godot_bin: str) -> int:
    """Run the hard-gate GdUnit4 subset (Adapters/Config + Security).

    Design goals:
    - Keep aligned with the hard-gate set in ci-windows.yml.
    - Write reports to logs/e2e/quality-gates/gdunit-hard.
    """

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
        "logs/e2e/quality-gates/gdunit-hard",
    ]
    proc = subprocess.run(args, text=True)
    return proc.returncode


def run_smoke_headless(godot_bin: str) -> int:
    """Run the Python headless smoke in strict mode.

    - Uses the Main scene as entry.
    - mode=strict requires either marker or [DB] opened.
    """

    args = [
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
    proc = subprocess.run(args, text=True)
    return proc.returncode


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_all = sub.add_parser("all", help="run quality gates (ci_pipeline + optional GdUnit/Smoke)")
    p_all.add_argument("--solution", default="Game.sln")
    p_all.add_argument("--configuration", default="Debug")
    p_all.add_argument("--godot-bin", required=True)
    p_all.add_argument("--build-solutions", action="store_true")
    p_all.add_argument("--gdunit-hard", action="store_true", help="run hard GdUnit set (Adapters/Config + Security)")
    p_all.add_argument("--smoke", action="store_true", help="run headless smoke (strict marker/DB check)")

    args = parser.parse_args()

    if args.cmd == "all":
        # 1) Base gates: dotnet + self-check + encoding scan.
        rc = run_ci_pipeline(args.solution, args.configuration, args.godot_bin, args.build_solutions)
        hard_failed = rc != 0

        # 2) Optional hard gate: GdUnit subset.
        if args.gdunit_hard:
            gd_rc = run_gdunit_hard(args.godot_bin)
            if gd_rc != 0:
                hard_failed = True

        # 3) Optional hard gate: headless smoke (strict).
        if args.smoke:
            sm_rc = run_smoke_headless(args.godot_bin)
            if sm_rc != 0:
                hard_failed = True

        return 0 if not hard_failed else 1

    print("Unsupported command", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
