#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Hard gate: reject git-tracked files under the Tests.Godot/Game.Godot mirror path.

Why:
- Tests.Godot/Game.Godot must remain a runtime junction alias, not a tracked copy.
- If mirror files are tracked, clean CI clones can rehydrate stale runtime content.

Outputs:
- logs/ci/<YYYY-MM-DD>/audit-tests-godot-mirror-git-tracking/summary.json
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import subprocess
import sys
from pathlib import Path


def _today() -> str:
    return dt.date.today().strftime("%Y-%m-%d")


def _posix(path: Path) -> str:
    return str(path).replace("\\", "/")


def _run_git_ls_files(repo_root: Path) -> list[str]:
    proc = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=repo_root,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if proc.returncode != 0:
        stderr = (proc.stderr or b"").decode("utf-8", errors="replace").strip()
        raise RuntimeError(f"git ls-files failed: rc={proc.returncode} msg={stderr}")

    raw = (proc.stdout or b"").decode("utf-8", errors="replace")
    files = [item.replace("\\", "/") for item in raw.split("\x00") if item]
    return files


def main() -> int:
    parser = argparse.ArgumentParser(description="Hard gate: audit git-tracked Tests.Godot/Game.Godot mirror files.")
    parser.add_argument("--root", default=".", help="Repository root (default: .)")
    parser.add_argument(
        "--mirror-prefix",
        default="Tests.Godot/Game.Godot/",
        help="Mirror path prefix to ban from git index.",
    )
    parser.add_argument(
        "--primary-prefix",
        default="Game.Godot/",
        help="Primary runtime path prefix (for repair hint).",
    )
    parser.add_argument(
        "--max-print",
        type=int,
        default=20,
        help="Max mirrored tracked paths to print.",
    )
    args = parser.parse_args()

    repo_root = Path(args.root).resolve()
    mirror_prefix = str(args.mirror_prefix).replace("\\", "/").strip()
    primary_prefix = str(args.primary_prefix).replace("\\", "/").strip()
    if mirror_prefix and not mirror_prefix.endswith("/"):
        mirror_prefix += "/"
    if primary_prefix and not primary_prefix.endswith("/"):
        primary_prefix += "/"

    out_path = repo_root / "logs" / "ci" / _today() / "audit-tests-godot-mirror-git-tracking" / "summary.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        tracked_files = _run_git_ls_files(repo_root)
    except Exception as exc:
        summary = {
            "ts": dt.datetime.now(dt.timezone.utc).isoformat(),
            "action": "audit-tests-godot-mirror-git-tracking",
            "status": "fail",
            "reason": "git_ls_files_failed",
            "message": str(exc),
            "mirror_prefix": mirror_prefix,
            "primary_prefix": primary_prefix,
            "tracked_mirror_paths": [],
            "tracked_count": 0,
        }
        out_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(
            "AUDIT_TESTS_GODOT_MIRROR_GIT_TRACKING "
            f"status=fail reason=git_ls_files_failed tracked=0 out={_posix(out_path)}"
        )
        return 1

    tracked_mirror = sorted(path for path in tracked_files if path.startswith(mirror_prefix))
    ok = len(tracked_mirror) == 0
    summary = {
        "ts": dt.datetime.now(dt.timezone.utc).isoformat(),
        "action": "audit-tests-godot-mirror-git-tracking",
        "status": "ok" if ok else "fail",
        "reason": "no_tracked_mirror_files" if ok else "tracked_mirror_files_found",
        "mirror_prefix": mirror_prefix,
        "primary_prefix": primary_prefix,
        "tracked_mirror_paths": tracked_mirror,
        "tracked_count": len(tracked_mirror),
        "repair": [
            f"Untrack mirror files under {mirror_prefix} from git index.",
            "Keep mirror path ignored and rely on junction/runtime preparation.",
            f"Use {primary_prefix} as the source-of-truth runtime tree.",
        ],
    }
    out_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(
        "AUDIT_TESTS_GODOT_MIRROR_GIT_TRACKING "
        f"status={'ok' if ok else 'fail'} tracked={len(tracked_mirror)} out={_posix(out_path)}"
    )
    if not ok:
        for path in tracked_mirror[: max(1, int(args.max_print))]:
            print(f" - tracked={path}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
