#!/usr/bin/env python3
"""
Ensure Tests.Godot uses a single source of truth for runtime assets/scripts.

This script enforces the following invariant on Windows:
  Tests.Godot/Game.Godot  is a junction ->  <repo>/Game.Godot
  Tests.Godot/Game.Core   is a junction ->  <repo>/Game.Core
  Tests.Godot/Data       is a junction ->  <repo>/Data
  Tests.Godot/Assets     is a junction ->  <repo>/Assets

Why:
  Having both <repo>/Game.Godot and Tests.Godot/Game.Godot as independent copies
  creates "double-source" drift where tests can pass against stale code.
  The test project must also see the same Data/Assets as the main project,
  otherwise runtime validators (e.g. portrait path existence) can fail only in CI.
  For contract-smoke tests, the test project must also be able to read Game.Core sources
  (e.g. event type constants) without duplicating code under Tests.Godot.

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

def _ensure_one_junction(*, name: str, src: str, dst: str, migrate: bool, details: dict) -> tuple[bool, str]:
    entry: dict = {"name": name, "source": src, "destination": dst, "actions": []}
    details.setdefault("links", []).append(entry)

    if not os.path.isdir(src):
        entry["status"] = "fail"
        entry["error"] = "source_missing"
        entry["source_exists"] = False
        return False, f"{name}:source_missing"

    probe = _probe_link(dst)
    entry["probe_before"] = probe

    # OK if already a junction to the desired src
    if probe.get("exists") and str(probe.get("linkType") or "").lower() == "junction":
        targets = probe.get("target")
        if isinstance(targets, list):
            tgt_ok = any(os.path.abspath(str(t)) == os.path.abspath(src) for t in targets)
        else:
            tgt_ok = os.path.abspath(str(targets)) == os.path.abspath(src) if targets else False
        if tgt_ok:
            entry["status"] = "ok"
            entry["actions"].append({"action": "noop", "reason": "junction_already_ok"})
            return True, f"{name}:junction_already_ok"

    # If destination exists but isn't a junction, decide how to handle.
    if os.path.exists(dst):
        if not migrate:
            entry["status"] = "fail"
            entry["error"] = "destination_exists_not_junction"
            entry["hint"] = "Run with --migrate to move the existing directory aside and create a junction."
            return False, f"{name}:destination_exists_not_junction"

        if os.path.isdir(dst) and _is_dir_empty(dst):
            entry["actions"].append({"action": "remove_empty_directory", "path": dst})
            shutil.rmtree(dst, ignore_errors=True)
        else:
            ts = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
            backup = dst + f"__backup__{ts}"
            entry["actions"].append({"action": "move_aside", "from": dst, "to": backup})
            try:
                os.rename(dst, backup)
            except Exception:
                shutil.copytree(dst, backup, dirs_exist_ok=True)
                shutil.rmtree(dst, ignore_errors=True)

    # Create junction
    rc, out = _make_junction(dst, src)
    entry["actions"].append({"action": "mklink_junction", "rc": rc, "output": out.strip()})
    probe_after = _probe_link(dst)
    entry["probe_after"] = probe_after

    ok = probe_after.get("exists") and str(probe_after.get("linkType") or "").lower() == "junction"
    if ok:
        entry["status"] = "ok"
        return True, f"{name}:junction_created"

    entry["status"] = "fail"
    entry["error"] = "junction_create_failed"
    return False, f"{name}:junction_create_failed"


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
    src_game = os.path.abspath(os.path.join(repo_root, args.source))
    dst_game = os.path.abspath(os.path.join(proj, "Game.Godot"))
    src_core = os.path.abspath(os.path.join(repo_root, "Game.Core"))
    dst_core = os.path.abspath(os.path.join(proj, "Game.Core"))
    src_data = os.path.abspath(os.path.join(repo_root, "Data"))
    dst_data = os.path.abspath(os.path.join(proj, "Data"))
    src_assets = os.path.abspath(os.path.join(repo_root, "Assets"))
    dst_assets = os.path.abspath(os.path.join(proj, "Assets"))

    date = dt.date.today().strftime("%Y-%m-%d")
    out_dir = os.path.join(repo_root, "logs", "ci", date, "ensure-tests-project-junction")
    os.makedirs(out_dir, exist_ok=True)

    details: dict = {
        "repo_root": repo_root,
        "project": proj,
        "source": src_game,
        "destination": dst_game,
        "platform": sys.platform,
        "generated": dt.datetime.now().isoformat(),
        "actions": [],
        "links": [],
    }

    if os.name != "nt":
        details["status"] = "fail"
        details["error"] = "windows_required"
        _write_json(os.path.join(out_dir, "details.json"), details)
        _write_json(os.path.join(out_dir, "summary.json"), {"status": "fail", "out": out_dir, "reason": "windows_required"})
        print(f"ENSURE_TESTS_JUNCTION status=fail out={out_dir} reason=windows_required")
        return 1

    if not os.path.isdir(proj):
        details["status"] = "fail"
        details["error"] = "project_missing"
        _write_json(os.path.join(out_dir, "details.json"), details)
        _write_json(os.path.join(out_dir, "summary.json"), {"status": "fail", "out": out_dir, "reason": "project_missing"})
        print(f"ENSURE_TESTS_JUNCTION status=fail out={out_dir} reason=project_missing")
        return 1

    ok_game, reason_game = _ensure_one_junction(
        name="Game.Godot",
        src=src_game,
        dst=dst_game,
        migrate=args.migrate,
        details=details,
    )
    ok_core, reason_core = _ensure_one_junction(
        name="Game.Core",
        src=src_core,
        dst=dst_core,
        migrate=args.migrate,
        details=details,
    )
    ok_data, reason_data = _ensure_one_junction(
        name="Data",
        src=src_data,
        dst=dst_data,
        migrate=args.migrate,
        details=details,
    )
    ok_assets, reason_assets = _ensure_one_junction(
        name="Assets",
        src=src_assets,
        dst=dst_assets,
        migrate=args.migrate,
        details=details,
    )

    all_ok = ok_game and ok_core and ok_data and ok_assets
    details["status"] = "ok" if all_ok else "fail"
    details["reason"] = [reason_game, reason_core, reason_data, reason_assets]
    _write_json(os.path.join(out_dir, "details.json"), details)
    _write_json(
        os.path.join(out_dir, "summary.json"),
        {"status": details["status"], "out": out_dir, "reason": details["reason"]},
    )
    print(f"ENSURE_TESTS_JUNCTION status={details['status']} out={out_dir} reason={details['reason']}")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
