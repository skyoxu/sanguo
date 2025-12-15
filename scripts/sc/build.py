#!/usr/bin/env python3
"""
sc-build: Repo-specific build shim (Godot+C# template).

Usage (Windows):
  py -3 scripts/sc/build.py
  py -3 scripts/sc/build.py GodotGame.sln --type prod --clean --verbose

TDD helper (gated, non-generative):
  py -3 scripts/sc/build.py tdd --stage green
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from _util import ci_dir, repo_root, run_cmd, write_json, write_text


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description="sc-build (build shim)")
    ap.add_argument("target", nargs="?", default="GodotGame.csproj", help="build target (.csproj/.sln)")
    ap.add_argument("--type", choices=["dev", "prod", "test"], default="dev")
    ap.add_argument("--clean", action="store_true")
    ap.add_argument("--optimize", action="store_true")
    ap.add_argument("--verbose", action="store_true")
    return ap


def main() -> int:
    # Lightweight subcommand routing (keeps backward compatibility):
    #   py -3 scripts/sc/build.py tdd ...
    if len(sys.argv) > 1 and sys.argv[1] == "tdd":
        cmd = ["py", "-3", "scripts/sc/build/tdd.py"] + sys.argv[2:]
        rc, out = run_cmd(cmd, cwd=repo_root(), timeout_sec=3_600)
        out_dir = ci_dir("sc-build")
        write_text(out_dir / "tdd.log", out)
        print(f"SC_BUILD_TDD rc={rc} out={out_dir}")
        return 0 if rc == 0 else rc

    args = build_parser().parse_args()
    out_dir = ci_dir("sc-build")

    config = "Debug"
    if args.type == "prod" or args.optimize:
        config = "Release"

    target = repo_root() / args.target
    if not target.exists():
        print(f"[sc-build] ERROR: target not found: {target}")
        return 2

    summary = {
        "cmd": "sc-build",
        "target": str(target),
        "configuration": config,
        "clean": bool(args.clean),
        "optimize": bool(args.optimize),
        "status": "fail",
    }

    logs = []
    if args.clean:
        cmd = ["dotnet", "clean", str(target), "-c", config]
        rc, out = run_cmd(cmd, cwd=repo_root(), timeout_sec=900)
        log_path = out_dir / "dotnet-clean.log"
        write_text(log_path, out)
        logs.append({"name": "dotnet-clean", "cmd": cmd, "rc": rc, "log": str(log_path)})
        if rc != 0:
            summary["logs"] = logs
            write_json(out_dir / "summary.json", summary)
            print(f"SC_BUILD status=fail out={out_dir}")
            return rc

    cmd = ["dotnet", "build", str(target), "-c", config, "-warnaserror"]
    if args.verbose:
        cmd += ["-v", "normal"]

    rc, out = run_cmd(cmd, cwd=repo_root(), timeout_sec=1_800)
    log_path = out_dir / "dotnet-build.log"
    write_text(log_path, out)
    logs.append({"name": "dotnet-build", "cmd": cmd, "rc": rc, "log": str(log_path)})

    summary["logs"] = logs
    summary["status"] = "ok" if rc == 0 else "fail"
    write_json(out_dir / "summary.json", summary)

    print(f"SC_BUILD status={summary['status']} out={out_dir}")
    return 0 if rc == 0 else rc


if __name__ == "__main__":
    raise SystemExit(main())
