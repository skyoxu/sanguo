#!/usr/bin/env python3
"""Headless smoke test runner for Godot (Windows, Godot+C# template).

This is a Python equivalent of `scripts/ci/smoke_headless.ps1` with two behaviors:

- mode="loose" (default): never fails the build; prints PASS hints only.
- mode="strict": returns non-zero unless core markers are detected.

Heuristics (kept aligned with the PowerShell version):
- Prefer "[TEMPLATE_SMOKE_READY]".
- Fallback to "[DB] opened".
- In loose mode, any output counts as PASS.

Example (PowerShell):
  py -3 scripts/python/smoke_headless.py `
    --godot-bin "C:\\Godot\\Godot_v4.5.1-stable_mono_win64_console.exe" `
    --project-path "." --scene "res://Game.Godot/Scenes/Main.tscn" `
    --timeout-sec 5 --mode loose
"""

from __future__ import annotations

import argparse
import datetime as _dt
import os
import subprocess
import sys
from pathlib import Path


def _run_smoke(godot_bin: str, project_path: str, scene: str, timeout_sec: int, mode: str) -> int:
    bin_path = Path(godot_bin)
    if not bin_path.is_file():
        print(f"[smoke_headless] GODOT_BIN not found: {godot_bin}", file=sys.stderr)
        return 1

    now = _dt.datetime.now()
    date = now.strftime("%Y-%m-%d")
    # Use a high-resolution run id to avoid collisions when smoke is invoked in parallel
    # (e.g., multiple unit tests running within the same second on CI).
    run_id = f"{now.strftime('%Y%m%d-%H%M%S-%f')}-{os.getpid()}"
    dest = Path("logs") / "ci" / date / "smoke" / run_id
    dest.mkdir(parents=True, exist_ok=True)

    out_path = dest / "headless.out.log"
    err_path = dest / "headless.err.log"
    log_path = dest / "headless.log"

    base_args = ["--headless", "--path", project_path, "--scene", scene]
    if bin_path.suffix.lower() in (".cmd", ".bat"):
        cmd = ["cmd.exe", "/c", str(bin_path)] + base_args
    else:
        cmd = [str(bin_path)] + base_args
    print(f"[smoke_headless] starting Godot: {' '.join(cmd)} (timeout={timeout_sec}s)")

    timed_out = False

    with out_path.open("w", encoding="utf-8", errors="ignore") as f_out, \
            err_path.open("w", encoding="utf-8", errors="ignore") as f_err:
        try:
            proc = subprocess.Popen(cmd, stdout=f_out, stderr=f_err, text=True)
        except Exception as exc:  # pragma: no cover - environment-specific failure
            print(f"[smoke_headless] failed to start Godot: {exc}", file=sys.stderr)
            return 1

        try:
            proc.wait(timeout=timeout_sec)
        except subprocess.TimeoutExpired:
            timed_out = True
            print("[smoke_headless] timeout reached; terminating Godot (expected for smoke)")
            try:
                proc.kill()
            except Exception:
                pass

    content_parts: list[str] = []
    if out_path.is_file():
        content_parts.append(out_path.read_text(encoding="utf-8", errors="ignore"))
    if err_path.is_file():
        content_parts.append("\n" + err_path.read_text(encoding="utf-8", errors="ignore"))

    combined = "".join(content_parts)
    print(f"[smoke_headless] log saved at {log_path} (out={out_path}, err={err_path})")

    text = combined or ""
    has_marker = "[TEMPLATE_SMOKE_READY]" in text
    has_db_open = "[DB] opened" in text
    has_any = bool(text.strip())

    if has_marker:
        print("SMOKE PASS (marker)")
    elif has_db_open:
        print("SMOKE PASS (db opened)")
    elif has_any:
        print("SMOKE PASS (any output)")
    else:
        print("SMOKE INCONCLUSIVE (no output). Check logs.")

    if mode == "strict":
        # Strict mode: require at least the marker or a DB opened line (independent of Godot's exit code).
        gate = "strict-passed" if (has_marker or has_db_open) else "strict-failed"
        timeout_note = "\n[SMOKE] timeout\n" if timed_out else ""
        log_path.write_text(combined + f"\n[SMOKE] {gate}\n" + timeout_note, encoding="utf-8", errors="ignore")
        return 0 if gate == "strict-passed" else 1

    # Loose mode never gates; logs are the artifact.
    timeout_note = "\n[SMOKE] timeout\n" if timed_out else ""
    log_path.write_text(combined + timeout_note, encoding="utf-8", errors="ignore")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Godot headless smoke test (Python variant)")
    parser.add_argument("--godot-bin", required=True, help="Path to Godot executable (mono console)")
    parser.add_argument("--project-path", default=".", help="Godot project path (default '.')")
    parser.add_argument("--scene", default="res://Game.Godot/Scenes/Main.tscn", help="Scene to load")
    parser.add_argument("--timeout-sec", type=int, default=5, help="Timeout seconds before kill")
    parser.add_argument("--mode", choices=["loose", "strict"], default="loose", help="Gate mode")

    args = parser.parse_args()
    return _run_smoke(args.godot_bin, args.project_path, args.scene, args.timeout_sec, args.mode)


if __name__ == "__main__":
    sys.exit(main())
