#!/usr/bin/env python3
"""
Shared command runner helpers for acceptance-check steps.
"""

from __future__ import annotations

from pathlib import Path

from _step_result import StepResult
from _util import repo_root, run_cmd, write_text


def run_and_capture(out_dir: Path, name: str, cmd: list[str], timeout_sec: int) -> StepResult:
    rc, out = run_cmd(cmd, cwd=repo_root(), timeout_sec=timeout_sec)
    log_path = out_dir / f"{name}.log"
    write_text(log_path, out)
    return StepResult(
        name=name,
        status="ok" if rc == 0 else "fail",
        rc=rc,
        cmd=cmd,
        log=str(log_path),
    )


def run_and_capture_mode(out_dir: Path, name: str, cmd: list[str], timeout_sec: int, *, mode: str) -> StepResult:
    """
    mode:
      - require: fail on rc!=0
      - warn: never fail (record rc in details)
    """
    rc, out = run_cmd(cmd, cwd=repo_root(), timeout_sec=timeout_sec)
    log_path = out_dir / f"{name}.log"
    write_text(log_path, out)
    if mode == "warn":
        return StepResult(
            name=name,
            status="ok",
            rc=0,
            cmd=cmd,
            log=str(log_path),
            details={"mode": "warn", "rc": rc},
        )
    return StepResult(
        name=name,
        status="ok" if rc == 0 else "fail",
        rc=rc,
        cmd=cmd,
        log=str(log_path),
    )
