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

Smoke session (exit-on-ready):
  # When GD_SMOKE_EXIT_ON_READY=1 is set, the Godot project is expected to quit
  # by itself after it reaches the ready state. This avoids relying on timeout-kill
  # for strict smoke runs.
  GD_SMOKE_EXIT_ON_READY=1 py -3 scripts/python/smoke_headless.py --mode strict --timeout-sec 120 ...
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from datetime import timezone


_PERF_RE = re.compile(
    r"\[PERF\]\s*frames=(\d+)\s+avg_ms=([0-9]+(?:\.[0-9]+)?)\s+p50_ms=([0-9]+(?:\.[0-9]+)?)\s+p95_ms=([0-9]+(?:\.[0-9]+)?)\s+p99_ms=([0-9]+(?:\.[0-9]+)?)"
)


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")


def _read_project_meta(project_root: Path) -> tuple[str | None, str | None]:
    """Return (config/name, project/assembly_name) from project.godot, best-effort."""

    p = project_root / "project.godot"
    if not p.is_file():
        return None, None
    text = p.read_text(encoding="utf-8", errors="ignore")

    name = None
    m = re.search(r'(?m)^\s*config/name\s*=\s*"([^"]+)"\s*$', text)
    if m:
        name = m.group(1).strip()

    assembly = None
    m2 = re.search(r'(?m)^\s*project/assembly_name\s*=\s*"([^"]+)"\s*$', text)
    if m2:
        assembly = m2.group(1).strip()

    return name, assembly


def _find_latest_app_userdata_file(*, rel_path: str, project_root: Path) -> Path | None:
    """Locate a file under %APPDATA%/Godot/app_userdata/<project>/... (fallback to newest match)."""

    appdata = os.environ.get("APPDATA") or ""
    if not appdata:
        return None
    base = Path(appdata) / "Godot" / "app_userdata"
    if not base.is_dir():
        return None

    project_name, assembly_name = _read_project_meta(project_root)
    candidates: list[Path] = []
    for n in [project_name, assembly_name]:
        if not n:
            continue
        candidates.append(base / n / rel_path)
    for p in candidates:
        if p.is_file():
            return p

    # Fallback: scan newest matching file (bounded to app_userdata).
    try:
        matches = list(base.rglob(Path(rel_path).name))
        if not matches:
            return None
        matches = [m for m in matches if m.is_file() and str(m).lower().endswith(rel_path.replace("\\", "/").lower())]
        if not matches:
            return None
        return max(matches, key=lambda x: x.stat().st_mtime)
    except Exception:
        return None


def _export_perf_summary(*, date: str, run_id: str, scene: str, headless_log: Path, combined_text: str) -> dict | None:
    matches = list(_PERF_RE.finditer(combined_text or ""))
    if not matches:
        return None
    last = matches[-1]
    metrics = {
        "frames": int(last.group(1)),
        "avg_ms": float(last.group(2)),
        "p50_ms": float(last.group(3)),
        "p95_ms": float(last.group(4)),
        "p99_ms": float(last.group(5)),
    }
    out_path = Path("logs") / "perf" / date / "summary.json"
    payload = {
        **metrics,
        "scene": scene,
        "run_id": run_id,
        "source_headless_log": str(headless_log).replace("\\", "/"),
    }
    _write_json(out_path, payload)
    print(f"[smoke_headless] PERF_SUMMARY_OUT={out_path}")
    return payload


def _export_security_audit(*, date: str, project_root: Path) -> str | None:
    src = _find_latest_app_userdata_file(rel_path="logs/security/security-audit.jsonl", project_root=project_root)
    if not src:
        return None
    dst = Path("logs") / "ci" / date / "security-audit.jsonl"
    dst.parent.mkdir(parents=True, exist_ok=True)

    # Prefer exporting only the entries written during this smoke run.
    # This avoids local dev machines failing deterministic validators due to legacy records
    # from older schema versions.
    run_started_at_iso = os.environ.get("SMOKE_RUN_STARTED_AT_UTC", "").strip()
    run_started_at = None
    if run_started_at_iso:
        try:
            run_started_at = _dt.datetime.fromisoformat(run_started_at_iso.replace("Z", "+00:00"))
        except Exception:
            run_started_at = None

    kept = 0
    dropped = 0
    lines: list[str] = []
    for raw in src.read_text(encoding="utf-8", errors="ignore").splitlines():
        s = raw.strip()
        if not s:
            continue
        try:
            obj = json.loads(s)
        except Exception:
            dropped += 1
            continue
        if not isinstance(obj, dict):
            dropped += 1
            continue
        ts = str(obj.get("ts") or "").strip()
        if not ts:
            dropped += 1
            continue
        if run_started_at is not None:
            try:
                ts_dt = _dt.datetime.fromisoformat(ts.replace("Z", "+00:00"))
                if ts_dt.tzinfo is None:
                    ts_dt = ts_dt.replace(tzinfo=timezone.utc)
            except Exception:
                dropped += 1
                continue
            # Allow a small skew to include the first audit record.
            if ts_dt < (run_started_at - _dt.timedelta(seconds=5)):
                dropped += 1
                continue

        lines.append(s)
        kept += 1

    dst.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8", newline="\n")
    print(f"[smoke_headless] SECURITY_AUDIT_EXPORTED src={src} dst={dst} kept={kept} dropped={dropped}")
    return str(dst)


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
    exit_code: int = -1
    exit_on_ready = os.environ.get("GD_SMOKE_EXIT_ON_READY", "").strip()
    exit_on_ready_enabled = exit_on_ready in ("1", "true", "True", "yes", "YES")
    run_started_at_utc = _dt.datetime.now(tz=timezone.utc).isoformat().replace("+00:00", "Z")
    os.environ["SMOKE_RUN_STARTED_AT_UTC"] = run_started_at_utc

    with out_path.open("w", encoding="utf-8", errors="ignore") as f_out, \
            err_path.open("w", encoding="utf-8", errors="ignore") as f_err:
        try:
            env = os.environ.copy()
            if exit_on_ready_enabled:
                env["GD_SMOKE_EXIT_ON_READY"] = "1"
            # Used for exporting only the audit entries emitted during this smoke run.
            env["SMOKE_RUN_STARTED_AT_UTC"] = run_started_at_utc
            proc = subprocess.Popen(cmd, stdout=f_out, stderr=f_err, text=True, env=env)
        except Exception as exc:  # pragma: no cover - environment-specific failure
            print(f"[smoke_headless] failed to start Godot: {exc}", file=sys.stderr)
            return 1

        try:
            proc.wait(timeout=timeout_sec)
            exit_code = proc.returncode if proc.returncode is not None else -1
        except subprocess.TimeoutExpired:
            timed_out = True
            print("[smoke_headless] timeout reached; terminating Godot (expected for smoke)")
            try:
                proc.kill()
                try:
                    proc.wait(timeout=5)
                except Exception:
                    pass
            except Exception:
                pass
            exit_code = proc.returncode if proc.returncode is not None else -1

    content_parts: list[str] = []
    if out_path.is_file():
        content_parts.append(out_path.read_text(encoding="utf-8", errors="ignore"))
    if err_path.is_file():
        content_parts.append("\n" + err_path.read_text(encoding="utf-8", errors="ignore"))

    combined = "".join(content_parts)
    print(f"[smoke_headless] log saved at {log_path} (out={out_path}, err={err_path})")

    # Export Task 39 inputs (best-effort):
    # - logs/perf/<date>/summary.json from [PERF] marker lines
    # - logs/ci/<date>/security-audit.jsonl copied from Godot app_userdata
    project_root = Path(project_path).resolve()
    _export_perf_summary(date=date, run_id=run_id, scene=scene, headless_log=log_path, combined_text=combined)
    _export_security_audit(date=date, project_root=project_root)

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
        # Strict mode: require marker + clean exit (exit_code == 0) + no timeout kill.
        clean_exit = exit_code == 0
        reason: str | None = None

        if timed_out:
            reason = "timeout"
        elif not (has_marker or has_db_open):
            reason = "missing_marker"
        elif exit_code != 0:
            reason = "exit_code_nonzero"

        gate = "strict-passed" if (reason is None and clean_exit) else "strict-failed"
        timeout_note = "\n[SMOKE] timeout\n" if timed_out else ""

        if gate == "strict-passed":
            log_path.write_text(
                combined
                + "\n[SMOKE] strict-passed\n"
                + f"[SMOKE] details exit_code={exit_code} timed_out={timed_out} marker={has_marker} db_open={has_db_open}\n"
                + timeout_note,
                encoding="utf-8",
                errors="ignore",
            )
            return 0

        # Example: [SMOKE] strict-failed reason=timeout
        log_path.write_text(
            combined
            + f"\n[SMOKE] strict-failed reason={reason or 'unknown'} exit_code={exit_code} timed_out={timed_out} marker={has_marker} db_open={has_db_open}\n"
            + timeout_note,
            encoding="utf-8",
            errors="ignore",
        )
        return 1

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
    godot_bin = os.path.expandvars(args.godot_bin).strip().strip('"')
    return _run_smoke(godot_bin, args.project_path, args.scene, args.timeout_sec, args.mode)


if __name__ == "__main__":
    sys.exit(main())
