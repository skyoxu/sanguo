#!/usr/bin/env python3
"""
Ensure Tests.Godot uses a single source of truth for runtime assets/scripts.

This script enforces the following invariant on Windows:
  Tests.Godot/Game.Godot  is a junction ->  <repo>/Game.Godot

Why:
  Having both <repo>/Game.Godot and Tests.Godot/Game.Godot as independent copies
  creates "double-source" drift where tests can pass against stale code.

Artifacts:
  logs/ci/<YYYY-MM-DD>/ensure-tests-project-junction/summary.json
  logs/ci/<YYYY-MM-DD>/ensure-tests-project-junction/details.json

Usage (Windows):
  py -3 scripts/python/ensure_tests_project_junction.py --project Tests.Godot
  py -3 scripts/python/ensure_tests_project_junction.py --project Tests.Godot --migrate
"""

from __future__ import annotations

import argparse
import datetime as dt
import io
import json
import os
import shutil
import subprocess
import sys


def _write_json(path: str, obj: dict) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with io.open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)


def _run_cmd(args: list[str], cwd: str | None = None, timeout_sec: int = 30) -> tuple[int, str]:
    p = subprocess.Popen(
        args, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="ignore"
    )
    try:
        out, _ = p.communicate(timeout=timeout_sec)
    except subprocess.TimeoutExpired:
        p.kill()
        out, _ = p.communicate()
        return 124, out
    return p.returncode or 0, out


def _find_powershell() -> str:
    # Prefer PowerShell 7 (pwsh) when available, otherwise fall back to Windows PowerShell.
    cand = shutil.which("pwsh")
    if cand:
        return cand
    cand = shutil.which("powershell")
    if cand:
        return cand
    # Common install path for PowerShell 7.
    common = r"C:\Program Files\PowerShell\7\pwsh.exe"
    if os.path.isfile(common):
        return common
    return "powershell"


def _probe_link(path: str) -> dict:
    # PowerShell provides LinkType/Target for junctions in modern versions.
    p = path.replace("'", "''")
    ps = [
        _find_powershell(),
        "-NoProfile",
        "-Command",
        (
            f"$p = '{p}'; "
            "if (-not (Test-Path -LiteralPath $p)) { "
            "  [pscustomobject]@{ exists=$false } | ConvertTo-Json -Compress; exit 0 "
            "} "
            "$i = Get-Item -LiteralPath $p -Force; "
            "[pscustomobject]@{ exists=$true; linkType=$i.LinkType; target=$i.Target; fullName=$i.FullName; attributes=$i.Attributes.ToString() } "
            "| ConvertTo-Json -Compress"
        ),
    ]
    rc, out = _run_cmd(ps, timeout_sec=20)
    if rc != 0:
        return {"exists": os.path.exists(path), "probe_error": out.strip(), "probe_rc": rc}
    try:
        return json.loads(out.strip() or "{}")
    except Exception:
        return {"exists": os.path.exists(path), "probe_error": out.strip(), "probe_rc": rc}


def _is_dir_empty(path: str) -> bool:
    try:
        return os.path.isdir(path) and (len(os.listdir(path)) == 0)
    except Exception:
        return False


def _make_junction(dst: str, src: str) -> tuple[int, str]:
    # mklink is a cmd built-in.
    return _run_cmd(["cmd", "/c", "mklink", "/J", dst, src], timeout_sec=30)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", default="Tests.Godot", help="Godot test project directory (default: Tests.Godot)")
    ap.add_argument("--source", default="Game.Godot", help="Runtime source directory relative to repo root")
    ap.add_argument(
        "--migrate",
        action="store_true",
        help="If a non-junction directory exists at Tests.Godot/Game.Godot, move it aside and create the junction.",
    )
    args = ap.parse_args()

    repo_root = os.path.abspath(os.getcwd())
    proj = os.path.abspath(args.project)
    src = os.path.abspath(os.path.join(repo_root, args.source))
    dst = os.path.abspath(os.path.join(proj, "Game.Godot"))

    date = dt.date.today().strftime("%Y-%m-%d")
    out_dir = os.path.join(repo_root, "logs", "ci", date, "ensure-tests-project-junction")
    os.makedirs(out_dir, exist_ok=True)

    details: dict = {
        "repo_root": repo_root,
        "project": proj,
        "source": src,
        "destination": dst,
        "platform": sys.platform,
        "generated": dt.datetime.now().isoformat(),
        "actions": [],
    }

    if os.name != "nt":
        details["status"] = "fail"
        details["error"] = "windows_required"
        _write_json(os.path.join(out_dir, "details.json"), details)
        _write_json(os.path.join(out_dir, "summary.json"), {"status": "fail", "out": out_dir, "reason": "windows_required"})
        print(f"ENSURE_TESTS_JUNCTION status=fail out={out_dir} reason=windows_required")
        return 1

    if not os.path.isdir(src):
        details["status"] = "fail"
        details["error"] = "source_missing"
        details["source_exists"] = False
        _write_json(os.path.join(out_dir, "details.json"), details)
        _write_json(os.path.join(out_dir, "summary.json"), {"status": "fail", "out": out_dir, "reason": "source_missing"})
        print(f"ENSURE_TESTS_JUNCTION status=fail out={out_dir} reason=source_missing")
        return 1

    if not os.path.isdir(proj):
        details["status"] = "fail"
        details["error"] = "project_missing"
        _write_json(os.path.join(out_dir, "details.json"), details)
        _write_json(os.path.join(out_dir, "summary.json"), {"status": "fail", "out": out_dir, "reason": "project_missing"})
        print(f"ENSURE_TESTS_JUNCTION status=fail out={out_dir} reason=project_missing")
        return 1

    probe = _probe_link(dst)
    details["probe_before"] = probe

    # OK if already a junction to the desired src
    if probe.get("exists") and str(probe.get("linkType") or "").lower() == "junction":
        targets = probe.get("target")
        if isinstance(targets, list):
            tgt_ok = any(os.path.abspath(str(t)) == src for t in targets)
        else:
            tgt_ok = os.path.abspath(str(targets)) == src if targets else False
        if tgt_ok:
            details["status"] = "ok"
            details["actions"].append({"action": "noop", "reason": "junction_already_ok"})
            _write_json(os.path.join(out_dir, "details.json"), details)
            _write_json(os.path.join(out_dir, "summary.json"), {"status": "ok", "out": out_dir, "reason": "junction_already_ok"})
            print(f"ENSURE_TESTS_JUNCTION status=ok out={out_dir} reason=junction_already_ok")
            return 0

    # If destination exists but isn't a junction, decide how to handle.
    if os.path.exists(dst):
        if not args.migrate:
            details["status"] = "fail"
            details["error"] = "destination_exists_not_junction"
            details["hint"] = "Run with --migrate to move the existing directory aside and create a junction."
            _write_json(os.path.join(out_dir, "details.json"), details)
            _write_json(
                os.path.join(out_dir, "summary.json"),
                {"status": "fail", "out": out_dir, "reason": "destination_exists_not_junction"},
            )
            print(f"ENSURE_TESTS_JUNCTION status=fail out={out_dir} reason=destination_exists_not_junction")
            return 1

        if os.path.isdir(dst) and _is_dir_empty(dst):
            details["actions"].append({"action": "remove_empty_directory", "path": dst})
            shutil.rmtree(dst, ignore_errors=True)
        else:
            ts = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
            backup = dst + f"__backup__{ts}"
            details["actions"].append({"action": "move_aside", "from": dst, "to": backup})
            try:
                os.rename(dst, backup)
            except Exception:
                # Fallback: copy then remove
                shutil.copytree(dst, backup, dirs_exist_ok=True)
                shutil.rmtree(dst, ignore_errors=True)

    # Create junction
    rc, out = _make_junction(dst, src)
    details["actions"].append({"action": "mklink_junction", "rc": rc, "output": out.strip()})
    probe_after = _probe_link(dst)
    details["probe_after"] = probe_after

    ok = probe_after.get("exists") and str(probe_after.get("linkType") or "").lower() == "junction"
    if ok:
        details["status"] = "ok"
        _write_json(os.path.join(out_dir, "details.json"), details)
        _write_json(os.path.join(out_dir, "summary.json"), {"status": "ok", "out": out_dir, "reason": "junction_created"})
        print(f"ENSURE_TESTS_JUNCTION status=ok out={out_dir} reason=junction_created")
        return 0

    details["status"] = "fail"
    details["error"] = "junction_create_failed"
    _write_json(os.path.join(out_dir, "details.json"), details)
    _write_json(os.path.join(out_dir, "summary.json"), {"status": "fail", "out": out_dir, "reason": "junction_create_failed"})
    print(f"ENSURE_TESTS_JUNCTION status=fail out={out_dir} reason=junction_create_failed")
    return 1


if __name__ == "__main__":
    sys.exit(main())
