#!/usr/bin/env python
"""
Audit whether Tests.Godot/Game.Godot mirror files are tracked by git.

Background:
- In this template, Tests.Godot/Game.Godot should be a Junction to the real Game.Godot.
- If mirror files are tracked under Tests.Godot/Game.Godot/**, a fresh checkout will create a copy
  instead of a Junction, reintroducing drift.

Outputs:
- JSON report under logs/ci/<YYYY-MM-DD>/audit-tests-godot-mirror-tracking.json

This script is standard-library-only and prints ASCII-only summaries.
"""

from __future__ import annotations

import argparse
import json
import subprocess
from datetime import datetime
from pathlib import Path


def _date_dir(root: Path) -> Path:
    return root / "logs" / "ci" / datetime.now().strftime("%Y-%m-%d")


def _write_utf8(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def _git_ls_files(root: Path, pathspec: str) -> list[str]:
    p = subprocess.run(
        ["git", "ls-files", pathspec],
        cwd=str(root),
        capture_output=True,
        text=True,
        errors="ignore",
    )
    if p.returncode != 0:
        raise RuntimeError("git_ls_files_failed")
    return [line.strip() for line in (p.stdout or "").splitlines() if line.strip()]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Audit git tracking of Tests.Godot/Game.Godot mirror files.")
    ap.add_argument("--root", default=".", help="Repo root (default: .)")
    ap.add_argument(
        "--mirror-prefix",
        default="Tests.Godot/Game.Godot/",
        help="Mirror path prefix to audit (default: Tests.Godot/Game.Godot/)",
    )
    ap.add_argument(
        "--primary-prefix",
        default="Game.Godot/",
        help="Primary path prefix to compare against (default: Game.Godot/)",
    )
    args = ap.parse_args(argv)

    root = Path(args.root).resolve()
    mirror_prefix = args.mirror_prefix.replace("\\", "/")
    if not mirror_prefix.endswith("/"):
        mirror_prefix += "/"
    primary_prefix = args.primary_prefix.replace("\\", "/")
    if not primary_prefix.endswith("/"):
        primary_prefix += "/"

    mirror_tracked = _git_ls_files(root, f"{mirror_prefix}**")
    primary_tracked_set = set(_git_ls_files(root, f"{primary_prefix}**"))

    missing_primary: list[str] = []
    for p in mirror_tracked:
        rest = p[len(mirror_prefix) :]
        primary_equiv = primary_prefix + rest
        if primary_equiv not in primary_tracked_set:
            missing_primary.append(p)

    ok = True
    # If anything under mirror prefix is tracked, this is considered a hygiene failure.
    if mirror_tracked:
        ok = False

    report = {
        "ok": ok,
        "mirror_prefix": mirror_prefix,
        "primary_prefix": primary_prefix,
        "mirror_tracked_count": len(mirror_tracked),
        "mirror_tracked_sample": mirror_tracked[:50],
        "missing_primary_equivalent_count": len(missing_primary),
        "missing_primary_equivalent_sample": missing_primary[:50],
        "repair": [
            "Remove mirror files from index without deleting the real game files:",
            f"git rm -r --cached {mirror_prefix.rstrip('/')}",
            "Ensure .gitignore ignores the mirror path and rely on Junction creation for tests.",
        ],
    }

    out_dir = _date_dir(root)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "audit-tests-godot-mirror-tracking.json"
    _write_utf8(out_path, json.dumps(report, ensure_ascii=False, indent=2) + "\n")

    status = "OK" if report["ok"] else "FAIL"
    print(f"audit_tests_godot_mirror_git_tracking: {status}")
    print(f"mirror_tracked_count={report['mirror_tracked_count']}")
    print(f"report={out_path.as_posix()}")
    return 0 if report["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())

