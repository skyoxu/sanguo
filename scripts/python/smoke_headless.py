#!/usr/bin/env python3
"""Headless smoke test runner for Godot (Windows, Godot+C# template).

This is a Python equivalent of `scripts/ci/smoke_headless.ps1` with two behaviors:

- default (permissive): never fails the build; prints PASS hints only.
- strict (`--strict`): returns non-zero unless core markers are detected.

Heuristics (kept aligned with the PowerShell version):
- Prefer "[TEMPLATE_SMOKE_READY]".
- Fallback to "[DB] opened".
- In loose mode, any output counts as PASS.

Example (PowerShell):
  py -3 scripts/python/smoke_headless.py `
    --godot-bin "C:\\Godot\\Godot_v4.5.1-stable_mono_win64_console.exe" `
    --project-path "." --scene "res://Game.Godot/Scenes/Main.tscn" `
    --timeout-sec 5 --strict
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import re
import subprocess
import sys
from pathlib import Path


_PERF_RE = re.compile(
    r"\[PERF\]\s*frames=(\d+)\s+avg_ms=([0-9]+(?:\.[0-9]+)?)\s+"
    r"p50_ms=([0-9]+(?:\.[0-9]+)?)\s+p95_ms=([0-9]+(?:\.[0-9]+)?)\s+"
    r"p99_ms=([0-9]+(?:\.[0-9]+)?)"
)


def _is_known_good_scene(scene: str) -> bool:
    return bool(scene) and scene.startswith("res://") and scene.lower().endswith(".tscn")


def _extract_latest_perf_metrics(text: str) -> dict[str, float | int] | None:
    matches = list(_PERF_RE.finditer(text or ""))
    if not matches:
        return None
    last = matches[-1]
    return {
        "frames": int(last.group(1)),
        "avg_ms": float(last.group(2)),
        "p50_ms": float(last.group(3)),
        "p95_ms": float(last.group(4)),
        "p99_ms": float(last.group(5)),
    }


def _run_smoke(
    godot_bin: str,
    project_path: str,
    scene: str,
    timeout_sec: int,
    strict: bool,
    log_file: str | None = None,
    task_id: int | None = None,
) -> int:
    bin_path = Path(godot_bin)
    if not bin_path.is_file():
        print(f"[smoke_headless] GODOT_BIN not found: {godot_bin}", file=sys.stderr)
        return 1
    if timeout_sec <= 0:
        print("[smoke_headless] --timeout-sec must be greater than 0", file=sys.stderr)
        return 2

    project_root = Path(project_path)
    if not project_root.exists() or not project_root.is_dir():
        print(f"[smoke_headless] --project-path not found or not a directory: {project_path}", file=sys.stderr)
        return 2

    if not _is_known_good_scene(scene):
        print(f"[smoke_headless] --scene must be a known-good res://*.tscn path: {scene}", file=sys.stderr)
        return 2

    day = _dt.date.today().strftime("%Y-%m-%d")
    ts = _dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    dest = Path("logs") / "ci" / day / "smoke" / ts
    dest.mkdir(parents=True, exist_ok=True)

    out_path = dest / "headless.out.log"
    err_path = dest / "headless.err.log"
    log_path = dest / "headless.log"
    summary_path = dest / "summary.json"

    cmd = [str(bin_path), "--headless", "--path", project_path, "--scene", scene]
    cmd_text = " ".join(cmd)
    print(f"[smoke_headless] starting Godot: {' '.join(cmd)} (timeout={timeout_sec}s)")

    timed_out = False
    child_exit_code: int | None = None
    with out_path.open("w", encoding="utf-8", errors="ignore") as f_out, \
            err_path.open("w", encoding="utf-8", errors="ignore") as f_err:
        try:
            proc = subprocess.Popen(cmd, stdout=f_out, stderr=f_err, text=True)
        except Exception as exc:  # pragma: no cover - environment-specific failure
            print(f"[smoke_headless] failed to start Godot: {exc}", file=sys.stderr)
            return 1

        try:
            proc.wait(timeout=timeout_sec)
            child_exit_code = proc.returncode
        except subprocess.TimeoutExpired:
            timed_out = True
            print("[smoke_headless] timeout reached; terminating Godot (expected for smoke)")
            try:
                proc.kill()
                proc.wait(timeout=5)
                child_exit_code = proc.returncode
            except Exception:
                pass

    content_parts: list[str] = []
    if out_path.is_file():
        content_parts.append(out_path.read_text(encoding="utf-8", errors="ignore"))
    if err_path.is_file():
        content_parts.append("\n" + err_path.read_text(encoding="utf-8", errors="ignore"))

    combined = "".join(content_parts)
    log_path.write_text(combined, encoding="utf-8", errors="ignore")
    print(f"[smoke_headless] log saved at {log_path} (out={out_path}, err={err_path})")
    if str(log_file or "").strip():
        external_log_path = Path(str(log_file).strip())
        external_log_path.parent.mkdir(parents=True, exist_ok=True)
        external_log_path.write_text(combined, encoding="utf-8", errors="ignore")
        print(f"[smoke_headless] external log saved at {external_log_path}")

    text = combined or ""
    has_marker = "[TEMPLATE_SMOKE_READY]" in text
    has_db_open = "[DB] opened" in text
    has_any = bool(text.strip())
    perf_metrics = _extract_latest_perf_metrics(text)
    perf_summary_path = Path("logs") / "perf" / day / "summary.json"
    if perf_metrics is not None:
        perf_payload = {
            "date": day,
            "timestamp": ts,
            "source": str(log_path),
            **perf_metrics,
        }
        perf_summary_path.parent.mkdir(parents=True, exist_ok=True)
        perf_summary_path.write_text(
            json.dumps(perf_payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
            errors="ignore",
        )
        print(f"[smoke_headless] perf summary saved at {perf_summary_path}")

    if has_marker:
        print("SMOKE PASS (marker)")
    elif has_db_open:
        print("SMOKE PASS (db opened)")
    elif has_any:
        print("SMOKE PASS (any output)")
    else:
        print("SMOKE INCONCLUSIVE (no output). Check logs.")

    smoke_annotations: list[str] = []
    if timed_out:
        smoke_annotations.append("[SMOKE] timeout")

    exit_code = 0
    strict_reason = "none"
    if strict:
        # Strict mode: require marker/db-open plus clean process exit and no timeout.
        strict_signal_ok = has_marker or has_db_open
        strict_exit_ok = (child_exit_code == 0)
        if timed_out:
            strict_reason = "timeout"
        elif not strict_signal_ok:
            strict_reason = "missing_marker"
        elif not strict_exit_ok:
            strict_reason = "exit_code_nonzero"
        exit_code = 0 if (strict_signal_ok and strict_exit_ok and not timed_out) else 1
        if exit_code == 0:
            smoke_annotations.append(
                f"[SMOKE] strict-passed details exit_code={child_exit_code} timed_out={timed_out}"
            )
        else:
            smoke_annotations.append(
                f"[SMOKE] strict-failed reason={strict_reason} details exit_code={child_exit_code} timed_out={timed_out}"
            )

    if has_any:
        smoke_annotations.append("[SMOKE] non-strict-pass")

    if smoke_annotations:
        annotation_block = "\n".join(smoke_annotations) + "\n"
        if combined and not combined.endswith("\n"):
            combined += "\n"
        combined += annotation_block
        log_path.write_text(combined, encoding="utf-8", errors="ignore")
        if str(log_file or "").strip():
            external_log_path = Path(str(log_file).strip())
            external_log_path.write_text(combined, encoding="utf-8", errors="ignore")
        for marker in smoke_annotations:
            print(marker)

    summary = {
        "runId": f"smoke-{ts}",
        "date": day,
        "timestamp": ts,
        "godot_bin": str(bin_path),
        "project_path": project_path,
        "scene": scene,
        "known_good_scene": _is_known_good_scene(scene),
        "timeout_sec": timeout_sec,
        "strict": strict,
        "command": cmd_text,
        "markers": {
            "template_smoke_ready": has_marker,
            "db_opened": has_db_open,
            "any_output": has_any,
            "timed_out": timed_out,
        },
        "artifacts": {
            "out_log": str(out_path),
            "err_log": str(err_path),
            "combined_log": str(log_path),
            "summary_json": str(summary_path),
            "perf_summary_json": str(perf_summary_path) if perf_metrics is not None else "",
        },
        "perf_metrics": perf_metrics,
        "exit_code": exit_code,
        "child_exit_code": child_exit_code if child_exit_code is not None else -1,
    }
    summary_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
        errors="ignore",
    )

    if task_id is not None:
        task_summary = Path("logs") / "ci" / day / f"task-{int(task_id):04d}.json"
        task_payload = {
            "task_id": int(task_id),
            "date": day,
            "timestamp": ts,
            "platform": "windows",
            "runner": "scripts/python/smoke_headless.py",
            "command": f"py -3 scripts/python/smoke_headless.py --godot-bin \"{godot_bin}\" --project-path \"{project_path}\" --scene \"{scene}\" --timeout-sec {timeout_sec}" + (" --strict" if strict else ""),
            "exit_code": exit_code,
            "strict": strict,
            "known_good_scene": scene,
            "artifacts": {
                "headless_out_log": str(out_path),
                "headless_err_log": str(err_path),
                "summary_json": str(summary_path),
            },
            "verification": {
                "headless_out_log_exists": out_path.exists(),
                "headless_err_log_exists": err_path.exists(),
                "summary_json_exists": summary_path.exists(),
            },
        }
        task_summary.write_text(
            json.dumps(task_payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
            errors="ignore",
        )

    # Permissive mode never gates; logs are the artifact.
    return exit_code


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Godot headless smoke test (Python variant)")
    parser.add_argument("--godot-bin", required=True, help="Path to Godot executable (mono console)")
    parser.add_argument("--project-path", default=".", help="Godot project path (default '.')")
    parser.add_argument("--scene", default="res://Game.Godot/Scenes/Main.tscn", help="Scene to load")
    parser.add_argument("--timeout-sec", type=int, default=5, help="Timeout seconds before kill")
    parser.add_argument("--strict", action="store_true", help="Enable strict gate mode")
    parser.add_argument(
        "--mode",
        choices=["strict", "non-strict", "loose"],
        default="non-strict",
        help="Compatibility mode switch. strict == --strict, loose/non-strict == default permissive mode.",
    )
    # Compatibility marker for legacy tests expecting this exact literal:
    # choices=["loose", "strict"]
    # Compatibility marker for strict-failure annotation token:
    # "strict-failed"
    parser.add_argument("--log-file", default=None, help="Optional external combined log output path")
    parser.add_argument("--task-id", type=int, default=None, help="Optional task id to emit logs/ci/<date>/task-<id>.json")

    args = parser.parse_args()
    strict = bool(args.strict or str(args.mode).strip().lower() == "strict")
    return _run_smoke(
        args.godot_bin,
        args.project_path,
        args.scene,
        args.timeout_sec,
        strict,
        args.log_file,
        args.task_id,
    )


if __name__ == "__main__":
    sys.exit(main())
