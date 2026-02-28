#!/usr/bin/env python3
"""
Quality/perf-related acceptance-check steps.
"""

from __future__ import annotations

import re
import shutil
from pathlib import Path

from _quality_rules import scan_quality_rules
from _step_result import StepResult
from _taskmaster import TaskmasterTriplet
from _test_quality import assess_test_quality
from _util import repo_root, run_cmd, today_str, write_json, write_text


PERF_METRICS_RE = re.compile(
    r"\[PERF\]\s*frames=(\d+)\s+avg_ms=([0-9]+(?:\.[0-9]+)?)\s+p50_ms=([0-9]+(?:\.[0-9]+)?)\s+p95_ms=([0-9]+(?:\.[0-9]+)?)\s+p99_ms=([0-9]+(?:\.[0-9]+)?)"
)


def step_test_quality_soft(out_dir: Path, triplet: TaskmasterTriplet, *, strict: bool) -> StepResult:
    title = str(triplet.master.get("title") or "")
    details_blob = "\n".join(
        [
            str(triplet.master.get("details") or ""),
            str((triplet.back or {}).get("details") or ""),
            str((triplet.gameplay or {}).get("details") or ""),
        ]
    )
    taskdoc_path = Path(triplet.taskdoc_path) if triplet.taskdoc_path else None

    report = assess_test_quality(
        repo_root=repo_root(),
        task_id=triplet.task_id,
        title=title,
        details_blob=details_blob,
        taskdoc_path=taskdoc_path,
    )
    write_json(out_dir / "test-quality.json", report)

    verdict = str(report.get("verdict") or "OK")
    findings = report.get("findings") if isinstance(report.get("findings"), dict) else {}
    p1 = findings.get("p1") if isinstance(findings.get("p1"), list) else []
    p2 = findings.get("p2") if isinstance(findings.get("p2"), list) else []

    lines: list[str] = []
    lines.append(f"TEST_QUALITY verdict={verdict} ui_task={bool(report.get('ui_task'))} scanned={report.get('gdunit', {}).get('tests_scanned')}")
    for x in p1[:20]:
        lines.append(f"P1 {x}")
    for x in p2[:20]:
        lines.append(f"P2 {x}")
    log_path = out_dir / "test-quality.log"
    write_text(log_path, "\n".join(lines) + "\n")

    status = "ok"
    if strict and verdict == "Needs Fix":
        status = "fail"
    return StepResult(name="test-quality", status=status, rc=0 if status == "ok" else 1, log=str(log_path), details=report)


def step_quality_rules(out_dir: Path, *, strict: bool) -> StepResult:
    report = scan_quality_rules(repo_root=repo_root())
    write_json(out_dir / "quality-rules.json", report)

    verdict = str(report.get("verdict") or "OK")
    counts = report.get("counts") if isinstance(report.get("counts"), dict) else {}

    lines: list[str] = []
    lines.append(f"QUALITY_RULES verdict={verdict} total={counts.get('total')} p0={counts.get('p0')} p1={counts.get('p1')}")
    findings = report.get("findings") if isinstance(report.get("findings"), dict) else {}
    for sev in ["p0", "p1"]:
        items = findings.get(sev) if isinstance(findings.get(sev), list) else []
        for it in items[:50]:
            if not isinstance(it, dict):
                continue
            f = it.get("file")
            ln = it.get("line")
            msg = it.get("message")
            lines.append(f"{sev.upper()} {f}:{ln} {msg}")

    log_path = out_dir / "quality-rules.log"
    write_text(log_path, "\n".join(lines) + "\n")

    status = "ok"
    if strict and verdict == "Needs Fix":
        status = "fail"

    # Hard gate: forbid mirror path references (Tests.Godot/Game.Godot/**).
    mirror_json = repo_root() / "logs" / "ci" / today_str() / "forbid-mirror-path-refs.json"
    mirror_cmd = [
        "py",
        "-3",
        "scripts/python/forbid_mirror_path_refs.py",
        "--root",
        str(repo_root()),
    ]
    mirror_rc, mirror_out = run_cmd(mirror_cmd, cwd=repo_root(), timeout_sec=60)
    mirror_log = out_dir / "forbid-mirror-path-refs.log"
    write_text(mirror_log, mirror_out)
    if mirror_rc != 0:
        status = "fail"
        report = {**report, "mirror_path_refs": {"status": "fail", "rc": mirror_rc, "cmd": mirror_cmd, "log": str(mirror_log)}}
    else:
        report = {**report, "mirror_path_refs": {"status": "ok", "rc": mirror_rc, "cmd": mirror_cmd, "log": str(mirror_log)}}
    # If the script produced a report under logs/ci, also copy it next to the acceptance report for convenience.
    try:
        if mirror_json.exists():
            shutil.copy2(mirror_json, out_dir / mirror_json.name)
    except Exception:
        pass

    return StepResult(name="quality-rules", status=status, rc=0 if status == "ok" else 1, log=str(log_path), details=report)


def find_latest_headless_log() -> Path | None:
    ci_root = repo_root() / "logs" / "ci"
    if not ci_root.exists():
        return None
    candidates = list(ci_root.rglob("headless.log"))
    if not candidates:
        return None
    return max(candidates, key=lambda p: p.stat().st_mtime)


def step_perf_budget(out_dir: Path, *, max_p95_ms: int) -> StepResult:
    root = repo_root()
    headless_log = find_latest_headless_log()
    if not headless_log:
        details = {
            "status": "disabled" if max_p95_ms <= 0 else "enabled",
            "error": "no recent headless.log found under logs/ci (run smoke first)",
            "max_p95_ms": max_p95_ms,
        }
        write_json(out_dir / "perf-budget.json", details)
        return StepResult(name="perf-budget", status="skipped" if max_p95_ms <= 0 else "fail", details=details)

    content = headless_log.read_text(encoding="utf-8", errors="ignore")
    matches = list(PERF_METRICS_RE.finditer(content))
    if not matches:
        details = {
            "status": "disabled" if max_p95_ms <= 0 else "enabled",
            "error": "no [PERF] metrics found in headless.log",
            "headless_log": str(headless_log.relative_to(root)).replace("\\", "/"),
            "max_p95_ms": max_p95_ms,
        }
        write_json(out_dir / "perf-budget.json", details)
        return StepResult(name="perf-budget", status="skipped" if max_p95_ms <= 0 else "fail", details=details)

    last = matches[-1]
    frames = int(last.group(1))
    p95_ms = float(last.group(4))
    details = {
        "headless_log": str(headless_log.relative_to(root)).replace("\\", "/"),
        "frames": frames,
        "p95_ms": p95_ms,
        "max_p95_ms": max_p95_ms,
        "budget_status": ("disabled" if max_p95_ms <= 0 else ("pass" if p95_ms <= max_p95_ms else "fail")),
        "note": "Always extracts latest [PERF] metrics from headless.log; becomes a hard gate only when max_p95_ms > 0 (ADR-0015).",
    }
    write_json(out_dir / "perf-budget.json", details)
    if max_p95_ms <= 0:
        return StepResult(name="perf-budget", status="skipped", details=details)
    return StepResult(name="perf-budget", status="ok" if p95_ms <= max_p95_ms else "fail", details=details)
