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
import subprocess
import sys

from quality_gates_builders import (
    DEFAULT_GATE_BUNDLE_TASK_FILES,
    build_gate_bundle_hard_cmd,
    build_gdunit_hard_cmd,
    build_smoke_headless_cmd,
)


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
    p_all.add_argument("--smoke", action="store_true", help="run strict headless smoke after the hard gate bundle")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.cmd != "all":
        print("Unsupported command", file=sys.stderr)
        return 1

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
        smoke_rc = run_smoke_headless(args.godot_bin)
        if smoke_rc != 0:
            hard_failed = True

    return 0 if not hard_failed else 1


if __name__ == "__main__":
    sys.exit(main())
