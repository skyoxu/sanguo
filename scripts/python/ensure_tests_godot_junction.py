#!/usr/bin/env python
"""
Ensure Tests.Godot/Game.Godot is a Junction pointing to the real Game.Godot directory.

Why:
- Tests.Godot uses `res://Game.Godot/...` paths in GdUnit4 tests.
- A Junction makes Tests.Godot always read the same scripts/resources as the real game,
  eliminating drift caused by mirrored copies.

Behavior:
- Verify the link exists and points to the expected target.
- Optionally create the Junction if it is missing.
- Never delete a non-reparse directory (hard fail with repair instructions).
- Write an audit JSON under logs/ci/<YYYY-MM-DD>/.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
from datetime import datetime
from pathlib import Path


FILE_ATTRIBUTE_REPARSE_POINT = 0x0400


def _date_dir(root: Path) -> Path:
    return root / "logs" / "ci" / datetime.now().strftime("%Y-%m-%d")


def _write_utf8(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def _is_reparse_point(path: Path) -> bool:
    try:
        return bool(path.lstat().st_file_attributes & FILE_ATTRIBUTE_REPARSE_POINT)
    except Exception:
        return False


def _norm_path(path: Path) -> str:
    return os.path.normcase(os.path.abspath(str(path)))


def _run_cmd(args: list[str], cwd: Path | None = None) -> tuple[int, str]:
    p = subprocess.run(
        args,
        cwd=str(cwd) if cwd else None,
        capture_output=True,
        text=True,
        errors="ignore",
    )
    out = (p.stdout or "") + (p.stderr or "")
    return int(p.returncode or 0), out


def _create_junction(link_dir: Path, target_dir: Path) -> tuple[int, str]:
    rel_target = os.path.relpath(str(target_dir), str(link_dir.parent))
    # mklink expects Windows-style separators
    rel_target = rel_target.replace("/", "\\")
    args = ["cmd", "/c", "mklink", "/J", link_dir.name, rel_target]
    return _run_cmd(args, cwd=link_dir.parent)


def _remove_junction(link_dir: Path) -> tuple[int, str]:
    # rmdir on a Junction removes the link itself (not the target directory).
    args = ["cmd", "/c", "rmdir", link_dir.name]
    return _run_cmd(args, cwd=link_dir.parent)


def ensure_tests_godot_junction(
    root: Path,
    tests_project: str,
    link_name: str,
    target_rel: str,
    create_if_missing: bool,
    fix_wrong_target: bool,
) -> dict[str, object]:
    tests_dir = (root / tests_project).resolve()
    link_dir = tests_dir / link_name
    expected_target = (root / target_rel).resolve()
    expected_norm = _norm_path(expected_target)

    report: dict[str, object] = {
        "ok": False,
        "root": str(root),
        "tests_project": tests_project,
        "link": str(link_dir),
        "expected_target": str(expected_target),
        "create_if_missing": create_if_missing,
        "fix_wrong_target": fix_wrong_target,
        "action": "none",
        "details": {},
    }

    if not tests_dir.is_dir():
        report["action"] = "fail_tests_project_missing"
        report["details"] = {"reason": "tests_project_dir_missing"}
        return report

    if not expected_target.is_dir():
        report["action"] = "fail_expected_target_missing"
        report["details"] = {"reason": "expected_target_dir_missing"}
        return report

    link_exists = link_dir.exists()
    report["details"]["link_exists"] = link_exists

    if not link_exists:
        if not create_if_missing:
            report["action"] = "fail_link_missing"
            report["details"]["repair"] = [
                f"cd {tests_dir}",
                f"mklink /J {link_name} {os.path.relpath(str(expected_target), str(tests_dir)).replace('/', '\\\\')}",
            ]
            return report

        rc, out = _create_junction(link_dir, expected_target)
        report["details"]["create_rc"] = rc
        report["details"]["create_out"] = out.strip()
        if rc != 0:
            report["action"] = "fail_create"
            report["details"]["repair"] = [
                f"cd {tests_dir}",
                f"mklink /J {link_name} {os.path.relpath(str(expected_target), str(tests_dir)).replace('/', '\\\\')}",
            ]
            return report

        report["action"] = "created"

    is_reparse = _is_reparse_point(link_dir)
    report["details"]["link_is_reparse_point"] = is_reparse

    resolved_target = None
    resolved_norm = None
    try:
        resolved_target = link_dir.resolve()
        report["details"]["resolved_target"] = str(resolved_target)
        resolved_norm = _norm_path(resolved_target)
    except Exception as ex:
        report["details"]["resolve_error"] = type(ex).__name__

    if not is_reparse:
        report["action"] = "fail_not_reparse_point"
        report["details"]["repair"] = [
            f"Expected a Junction at: {link_dir}",
            "Refuse to delete a normal directory automatically.",
            "If this is a mirrored copy, delete it manually and re-run:",
            f"cd {tests_dir}",
            f"rmdir /s /q {link_name}",
            f"mklink /J {link_name} {os.path.relpath(str(expected_target), str(tests_dir)).replace('/', '\\\\')}",
        ]
        return report

    if resolved_target is None or resolved_norm != expected_norm:
        if fix_wrong_target:
            # Only remove if it is a reparse point; safest we can do here.
            rc_r, out_r = _remove_junction(link_dir)
            report["details"]["remove_rc"] = rc_r
            report["details"]["remove_out"] = out_r.strip()
            if rc_r != 0:
                report["action"] = "fail_remove_wrong_target"
                return report
            rc_c, out_c = _create_junction(link_dir, expected_target)
            report["details"]["recreate_rc"] = rc_c
            report["details"]["recreate_out"] = out_c.strip()
            if rc_c != 0:
                report["action"] = "fail_recreate_wrong_target"
                return report
            resolved_after = link_dir.resolve()
            report["details"]["resolved_target"] = str(resolved_after)
            if _norm_path(resolved_after) != expected_norm:
                report["action"] = "fail_wrong_target_after_recreate"
                return report
            report["action"] = "fixed_wrong_target"
            report["ok"] = True
            return report

        report["action"] = "fail_wrong_target"
        report["details"]["repair"] = [
            f"cd {tests_dir}",
            f"rmdir {link_name}",
            f"mklink /J {link_name} {os.path.relpath(str(expected_target), str(tests_dir)).replace('/', '\\\\')}",
        ]
        return report

    report["action"] = "ok"
    report["ok"] = True
    return report


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="Ensure Tests.Godot/Game.Godot is a Junction to the real Game.Godot."
    )
    ap.add_argument("--root", default=".", help="Repo root (default: .)")
    ap.add_argument("--tests-project", default="Tests.Godot", help="Tests project directory under root.")
    ap.add_argument("--link-name", default="Game.Godot", help="Link directory name under the tests project.")
    ap.add_argument("--target-rel", default="Game.Godot", help="Expected target directory under root.")
    ap.add_argument(
        "--create-if-missing",
        action="store_true",
        help="Create the Junction if missing (default: verify only).",
    )
    ap.add_argument(
        "--fix-wrong-target",
        action="store_true",
        help="If the link is a reparse point but points elsewhere, recreate it.",
    )
    args = ap.parse_args(argv)

    root = Path(args.root).resolve()
    report = ensure_tests_godot_junction(
        root=root,
        tests_project=args.tests_project,
        link_name=args.link_name,
        target_rel=args.target_rel,
        create_if_missing=bool(args.create_if_missing),
        fix_wrong_target=bool(args.fix_wrong_target),
    )

    out_dir = _date_dir(root)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "ensure-tests-godot-junction.json"
    _write_utf8(out_path, json.dumps(report, ensure_ascii=False, indent=2) + "\n")

    # ASCII-only summary for logs/CI consoles.
    status = "OK" if report.get("ok") else "FAIL"
    print(f"ensure_tests_godot_junction: {status} action={report.get('action')}")
    print(f"report={out_path.as_posix()}")
    return 0 if report.get("ok") else 2


if __name__ == "__main__":
    raise SystemExit(main())
