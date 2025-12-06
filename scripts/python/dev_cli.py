#!/usr/bin/env python3
"""Developer CLI entry for the Godot+C# template.

This script provides stable subcommands that other tools (BMAD,
task-master-ai, Claude Code, Codex.CLI) can call instead of
reconstructing long Python/PowerShell commands.

All output messages are in English to keep logs uniform.
"""

from __future__ import annotations

import argparse
import subprocess
import sys


def run(cmd: list[str]) -> int:
    """Run a subprocess and return its exit code."""

    print(f"[dev_cli] running: {' '.join(cmd)}")
    proc = subprocess.run(cmd, text=True)
    return proc.returncode


def cmd_run_ci_basic(args: argparse.Namespace) -> int:
    """Run core CI pipeline (dotnet tests + selfcheck + encoding)."""

    return run([
        "py",
        "-3",
        "scripts/python/ci_pipeline.py",
        "all",
        "--solution",
        args.solution,
        "--configuration",
        args.configuration,
        "--godot-bin",
        args.godot_bin,
        "--build-solutions",
    ])


def cmd_run_quality_gates(args: argparse.Namespace) -> int:
    """Run quality_gates.py all with optional hard GdUnit and smoke.""" 

    cmd = [
        "py",
        "-3",
        "scripts/python/quality_gates.py",
        "all",
        "--solution",
        args.solution,
        "--configuration",
        args.configuration,
        "--godot-bin",
        args.godot_bin,
        "--build-solutions",
    ]
    if args.gdunit_hard:
        cmd.append("--gdunit-hard")
    if args.smoke:
        cmd.append("--smoke")
    return run(cmd)


def cmd_run_gdunit_hard(args: argparse.Namespace) -> int:
    """Run hard GdUnit set (Adapters/Config + Security)."""

    return run([
        "py",
        "-3",
        "scripts/python/run_gdunit.py",
        "--prewarm",
        "--godot-bin",
        args.godot_bin,
        "--project",
        "Tests.Godot",
        "--add",
        "tests/Adapters/Config",
        "--add",
        "tests/Security/Hard",
        "--timeout-sec",
        "300",
        "--rd",
        "logs/e2e/dev-cli/gdunit-hard",
    ])


def cmd_run_gdunit_full(args: argparse.Namespace) -> int:
    """Run a broad GdUnit set (Adapters + Security + Integration + UI)."""

    return run([
        "py",
        "-3",
        "scripts/python/run_gdunit.py",
        "--prewarm",
        "--godot-bin",
        args.godot_bin,
        "--project",
        "Tests.Godot",
        "--add",
        "tests/Adapters",
        "--add",
        "tests/Security/Hard",
        "--add",
        "tests/Integration",
        "--add",
        "tests/UI",
        "--timeout-sec",
        "600",
        "--rd",
        "logs/e2e/dev-cli/gdunit-full",
    ])


def cmd_run_smoke_strict(args: argparse.Namespace) -> int:
    """Run strict headless smoke against Main scene."""

    return run([
        "py",
        "-3",
        "scripts/python/smoke_headless.py",
        "--godot-bin",
        args.godot_bin,
        "--project",
        ".",
        "--scene",
        "res://Game.Godot/Scenes/Main.tscn",
        "--timeout-sec",
        str(args.timeout_sec),
        "--mode",
        "strict",
    ])


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Dev CLI for Godot+C# template (AI-friendly entrypoint)",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    # run-ci-basic
    p_ci = sub.add_parser("run-ci-basic", help="run core CI pipeline (dotnet + selfcheck + encoding)")
    p_ci.add_argument("--solution", default="Game.sln")
    p_ci.add_argument("--configuration", default="Debug")
    p_ci.add_argument("--godot-bin", required=True)
    p_ci.set_defaults(func=cmd_run_ci_basic)

    # run-quality-gates
    p_qg = sub.add_parser("run-quality-gates", help="run quality_gates.py all with optional GdUnit hard and smoke")
    p_qg.add_argument("--solution", default="Game.sln")
    p_qg.add_argument("--configuration", default="Debug")
    p_qg.add_argument("--godot-bin", required=True)
    p_qg.add_argument("--gdunit-hard", action="store_true")
    p_qg.add_argument("--smoke", action="store_true")
    p_qg.set_defaults(func=cmd_run_quality_gates)

    # run-gdunit-hard
    p_gh = sub.add_parser("run-gdunit-hard", help="run hard GdUnit set (Adapters/Config + Security)")
    p_gh.add_argument("--godot-bin", required=True)
    p_gh.set_defaults(func=cmd_run_gdunit_hard)

    # run-gdunit-full
    p_gf = sub.add_parser("run-gdunit-full", help="run broad GdUnit tests (Adapters+Security+Integration+UI)")
    p_gf.add_argument("--godot-bin", required=True)
    p_gf.set_defaults(func=cmd_run_gdunit_full)

    # run-smoke-strict
    p_sm = sub.add_parser("run-smoke-strict", help="run strict headless smoke against Main scene")
    p_sm.add_argument("--godot-bin", required=True)
    p_sm.add_argument("--timeout-sec", type=int, default=5)
    p_sm.set_defaults(func=cmd_run_smoke_strict)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    func = getattr(args, "func", None)
    if func is None:
        parser.print_help()
        return 1
    return func(args)


if __name__ == "__main__":
    sys.exit(main())
