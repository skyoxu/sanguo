#!/usr/bin/env python3
"""
sc-git: Repo-specific git shim with basic safety rails.

Usage (Windows):
  py -3 scripts/sc/git.py status
  py -3 scripts/sc/git.py diff -- --stat
  py -3 scripts/sc/git.py commit --smart-commit --yes
"""

from __future__ import annotations

import argparse
import shlex
from pathlib import Path
from typing import Any

from _util import ci_dir, repo_root, run_cmd, write_json, write_text


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description="sc-git (git shim)")
    ap.add_argument("operation", nargs="?", default="status")
    ap.add_argument("args", nargs=argparse.REMAINDER, help="args for git operation (use -- to separate)")
    ap.add_argument("--smart-commit", action="store_true")
    ap.add_argument("--interactive", action="store_true")
    ap.add_argument("--yes", action="store_true", help="confirm potentially destructive operations")
    return ap


def is_force_push(op: str, args: list[str]) -> bool:
    if op != "push":
        return False
    force_flags = {"--force", "-f", "--force-with-lease"}
    return any(a in force_flags for a in args)


def requires_yes(op: str, args: list[str]) -> bool:
    if op in {"reset", "clean", "rebase"}:
        return True
    if is_force_push(op, args):
        return True
    return False


def has_commit_message(args: list[str]) -> bool:
    return "-m" in args or "--message" in args


def smart_commit_message() -> str:
    rc, out = run_cmd(["git", "diff", "--cached", "--name-only"], cwd=repo_root(), timeout_sec=30)
    files = [ln.strip() for ln in out.splitlines() if ln.strip()]
    if not files:
        return "chore: update working tree"

    areas = set()
    for f in files:
        f = f.replace("\\", "/")
        if f.startswith("docs/"):
            areas.add("docs")
        elif f.startswith("scripts/"):
            areas.add("scripts")
        elif f.startswith("Game.Core.Tests/") or f.endswith("Tests.cs"):
            areas.add("tests")
        elif f.startswith("Game.Core/Contracts/"):
            areas.add("contracts")
        elif f.startswith("Game.Core/"):
            areas.add("core")
        elif f.startswith("Game.Godot/"):
            areas.add("godot")
        else:
            areas.add("repo")

    scope = ",".join(sorted(areas))
    prefix = "chore"
    if "tests" in areas and len(areas) == 1:
        prefix = "test"
    if "docs" in areas and len(areas) == 1:
        prefix = "docs"
    if "core" in areas and len(areas) == 1:
        prefix = "feat"
    if "contracts" in areas and len(areas) == 1:
        prefix = "feat"

    return f"{prefix}: update {scope}"


def main() -> int:
    args = build_parser().parse_args()

    op = args.operation
    extra = list(args.args)
    if extra and extra[0] == "--":
        extra = extra[1:]

    if requires_yes(op, extra) and not args.yes:
        print(f"[sc-git] ERROR: operation '{op}' requires --yes for confirmation.")
        return 2

    git_args = ["git", op] + extra
    notes = []

    if op == "commit" and args.smart_commit and not has_commit_message(extra):
        msg = smart_commit_message()
        git_args += ["-m", msg]
        notes.append({"smart_commit_message": msg})

    out_dir = ci_dir("sc-git")
    rc, out = run_cmd(git_args, cwd=repo_root(), timeout_sec=300)

    # Log output
    safe_op = "".join(ch for ch in op if ch.isalnum() or ch in ("-", "_"))[:32]
    log_path = out_dir / f"{safe_op}.log"
    write_text(log_path, out)

    summary: dict[str, Any] = {
        "cmd": "sc-git",
        "operation": op,
        "args": extra,
        "interactive": bool(args.interactive),
        "rc": rc,
        "log": str(log_path),
        "notes": notes,
    }
    write_json(out_dir / "summary.json", summary)

    printable = " ".join(shlex.quote(a) for a in git_args)
    print(f"SC_GIT rc={rc} op={op} cmd={printable} out={out_dir}")
    return 0 if rc == 0 else rc


if __name__ == "__main__":
    raise SystemExit(main())

