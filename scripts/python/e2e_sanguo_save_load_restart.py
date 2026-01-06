#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
E2E proof: Sanguo save/load survives process restart.

This script runs two separate Godot headless processes:
  1) mode=save: start a new game and save to a slot, then quit.
  2) mode=load: load the same slot and print a marker, then quit.

It captures stdout/stderr into logs/e2e/<YYYY-MM-DD>/sanguo-save-load-restart/
and exits non-zero if markers are missing or inconsistent.

Windows example:
  py -3 scripts/python/e2e_sanguo_save_load_restart.py --godot-bin "%GODOT_BIN%"
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import re
import subprocess
import sys
import uuid
from pathlib import Path


SAVED_RE = re.compile(r"\[E2E_SAVELOAD\]\s+saved\s+slot=(\S+)\s+turn=(\d+)\s+active_index=(\d+)\s+date=(\d{4}-\d{2}-\d{2})")
LOADED_RE = re.compile(r"\[E2E_SAVELOAD\]\s+loaded\s+slot=(\S+)\s+turn=(\d+)\s+active_index=(\d+)\s+date=(\d{4}-\d{2}-\d{2})")


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _today() -> str:
    return _dt.date.today().strftime("%Y-%m-%d")


def _run_one(
    *,
    godot_bin: str,
    project: str,
    scene: str,
    mode: str,
    slot: str,
    correlation_id: str,
    timeout_sec: int,
    out_dir: Path,
) -> tuple[int, str]:
    cmd = [
        godot_bin,
        "--headless",
        "--path",
        project,
        "--scene",
        scene,
        "--",
        "--sc-saveload-mode",
        mode,
        "--sc-saveload-slot",
        slot,
        "--sc-saveload-correlation",
        correlation_id,
    ]
    out_path = out_dir / f"{mode}.out.log"
    err_path = out_dir / f"{mode}.err.log"

    with out_path.open("w", encoding="utf-8", errors="ignore") as f_out, err_path.open("w", encoding="utf-8", errors="ignore") as f_err:
        try:
            proc = subprocess.Popen(cmd, cwd=_repo_root(), stdout=f_out, stderr=f_err, text=True)
        except Exception as exc:
            return 2, f"failed to start Godot: {exc}"

        try:
            proc.wait(timeout=timeout_sec)
        except subprocess.TimeoutExpired:
            try:
                proc.kill()
            except Exception:
                pass
            return 1, f"timeout ({timeout_sec}s)"

    combined = ""
    if out_path.exists():
        combined += out_path.read_text(encoding="utf-8", errors="ignore")
    if err_path.exists():
        combined += "\n" + err_path.read_text(encoding="utf-8", errors="ignore")
    return int(proc.returncode or 0), combined


def _build_godot_csharp(out_dir: Path) -> tuple[int, str]:
    cmd = ["dotnet", "build", "GodotGame.csproj", "-c", "Debug"]
    log_path = out_dir / "dotnet-build.log"
    try:
        proc = subprocess.run(cmd, cwd=_repo_root(), capture_output=True, text=True, timeout=300)
    except Exception as exc:
        log_path.write_text(str(exc) + "\n", encoding="utf-8", errors="ignore")
        return 2, f"dotnet build failed to start: {exc}"

    combined = (proc.stdout or "") + "\n" + (proc.stderr or "")
    log_path.write_text(combined, encoding="utf-8", errors="ignore")
    return int(proc.returncode or 0), combined


def main() -> int:
    ap = argparse.ArgumentParser(description="Sanguo save/load restart e2e proof")
    ap.add_argument("--godot-bin", required=True, help="Path to Godot mono console executable")
    ap.add_argument("--project", default=".", help="Godot project path (default '.')")
    ap.add_argument("--scene", default="res://Game.Godot/Scenes/Main.tscn", help="Scene to load")
    ap.add_argument("--slot", default="e2e", help="Save slot id")
    ap.add_argument("--timeout-sec", type=int, default=30, help="Timeout seconds for each run")
    ap.add_argument("--run-id", default=None, help="Run id for evidence binding (default: random)")
    ap.add_argument("--skip-build", action="store_true", help="Skip dotnet build of GodotGame.csproj (not recommended).")
    args = ap.parse_args()

    run_id = str(args.run_id or "").strip() or uuid.uuid4().hex
    root = _repo_root()
    out_dir = root / "logs" / "e2e" / _today() / "sanguo-save-load-restart"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "run_id.txt").write_text(run_id + "\n", encoding="utf-8")

    correlation_id = f"e2e-{run_id}"

    if not bool(args.skip_build):
        build_rc, _ = _build_godot_csharp(out_dir)
        if build_rc != 0:
            (out_dir / "summary.json").write_text(
                json.dumps(
                    {
                        "run_id": run_id,
                        "status": "fail",
                        "errors": [f"dotnet_build_rc={build_rc}"],
                    },
                    ensure_ascii=True,
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )
            print(f"E2E_SAVELOAD_RESTART status=fail out={out_dir.relative_to(root)}")
            print(f"ERROR dotnet_build_rc={build_rc}")
            return 1

    save_rc, save_text = _run_one(
        godot_bin=args.godot_bin,
        project=args.project,
        scene=args.scene,
        mode="save",
        slot=args.slot,
        correlation_id=correlation_id,
        timeout_sec=int(args.timeout_sec),
        out_dir=out_dir,
    )

    saved = SAVED_RE.search(save_text)
    load_rc, load_text = _run_one(
        godot_bin=args.godot_bin,
        project=args.project,
        scene=args.scene,
        mode="load",
        slot=args.slot,
        correlation_id=correlation_id,
        timeout_sec=int(args.timeout_sec),
        out_dir=out_dir,
    )

    loaded = LOADED_RE.search(load_text)

    ok = True
    errors: list[str] = []

    if save_rc != 0:
        ok = False
        errors.append(f"save_rc={save_rc}")
    if load_rc != 0:
        ok = False
        errors.append(f"load_rc={load_rc}")

    if not saved:
        ok = False
        errors.append("missing_saved_marker")
    if not loaded:
        ok = False
        errors.append("missing_loaded_marker")

    details: dict[str, object] = {
        "run_id": run_id,
        "slot": args.slot,
        "correlation_id": correlation_id,
        "save_rc": save_rc,
        "load_rc": load_rc,
        "status": "ok" if ok else "fail",
        "errors": errors,
    }

    if saved:
        details["saved"] = {
            "slot": saved.group(1),
            "turn": int(saved.group(2)),
            "active_index": int(saved.group(3)),
            "date": saved.group(4),
        }
    if loaded:
        details["loaded"] = {
            "slot": loaded.group(1),
            "turn": int(loaded.group(2)),
            "active_index": int(loaded.group(3)),
            "date": loaded.group(4),
        }

    if saved and loaded:
        if details["saved"] != details["loaded"]:
            ok = False
            details["status"] = "fail"
            errors.append("saved_loaded_mismatch")

    (out_dir / "summary.json").write_text(json.dumps(details, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")

    print(f"E2E_SAVELOAD_RESTART status={details['status']} out={out_dir.relative_to(root)}")
    if errors:
        for e in errors:
            print(f"ERROR {e}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
