#!/usr/bin/env python3
"""
Acceptance check step implementations.

Why:
  Keep scripts under the repo's single-file size guideline (<= 400 lines) by
  moving step implementations out of the CLI entrypoint.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from _quality_rules import scan_quality_rules
from _taskmaster import TaskmasterTriplet
from _test_quality import assess_test_quality
from _util import repo_root, run_cmd, write_json, write_text


ADR_STATUS_RE = re.compile(r"^\s*-?\s*(?:Status|status)\s*:\s*([A-Za-z]+)\s*$", re.MULTILINE)
PERF_METRICS_RE = re.compile(
    r"\[PERF\]\s*frames=(\d+)\s+avg_ms=([0-9]+(?:\.[0-9]+)?)\s+p50_ms=([0-9]+(?:\.[0-9]+)?)\s+p95_ms=([0-9]+(?:\.[0-9]+)?)\s+p99_ms=([0-9]+(?:\.[0-9]+)?)"
)


@dataclass(frozen=True)
class StepResult:
    name: str
    status: str  # ok|fail|skipped
    rc: int | None = None
    cmd: list[str] | None = None
    log: str | None = None
    details: dict[str, Any] | None = None


def find_adr_file(root: Path, adr_id: str) -> Path | None:
    adr_dir = root / "docs" / "adr"
    if not adr_dir.exists():
        return None
    matches = sorted(adr_dir.glob(f"{adr_id}-*.md"))
    if matches:
        return matches[0]
    exact = adr_dir / f"{adr_id}.md"
    if exact.exists():
        return exact
    return None


def read_adr_status(path: Path) -> str | None:
    text = path.read_text(encoding="utf-8", errors="ignore")
    m = ADR_STATUS_RE.search(text)
    if not m:
        return None
    return m.group(1).strip()


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


def step_adr_compliance(out_dir: Path, triplet: TaskmasterTriplet, *, strict_status: bool) -> StepResult:
    root = repo_root()
    adr_refs = triplet.adr_refs()
    arch_refs = triplet.arch_refs()
    overlay = triplet.overlay()

    details: dict[str, Any] = {
        "task_id": triplet.task_id,
        "title": triplet.master.get("title"),
        "adrRefs": adr_refs,
        "archRefs": arch_refs,
        "overlay": overlay,
        "adrStatus": {},
        "errors": [],
        "warnings": [],
        "strict_status": bool(strict_status),
    }

    if not adr_refs:
        details["errors"].append("missing adrRefs in tasks.json (master task)")
    if not arch_refs:
        details["errors"].append("missing archRefs in tasks.json (master task)")

    accepted_count = 0
    for adr in adr_refs:
        adr_path = find_adr_file(root, adr)
        if not adr_path:
            details["errors"].append(f"ADR file missing on disk: {adr}")
            continue
        status = read_adr_status(adr_path)
        details["adrStatus"][adr] = {"path": str(adr_path.relative_to(root)).replace("\\", "/"), "status": status}
        if not status:
            details["warnings"].append(f"ADR status not found (no 'status:' or 'Status:' line): {adr}")
        elif status.lower() == "accepted":
            accepted_count += 1
        else:
            msg = f"ADR not Accepted: {adr} (status={status})"
            if strict_status:
                details["errors"].append(msg)
            else:
                details["warnings"].append(msg)

    if adr_refs and accepted_count == 0:
        details["errors"].append("no Accepted ADR found in adrRefs (require >= 1 Accepted ADR)")

    if overlay:
        overlay_path = root / overlay
        if not overlay_path.exists():
            details["errors"].append(f"overlay path missing on disk: {overlay}")

    ok = len(details["errors"]) == 0
    write_json(out_dir / "adr-compliance.json", details)
    return StepResult(name="adr-compliance", status="ok" if ok else "fail", details=details)


def step_task_links_validate(out_dir: Path) -> StepResult:
    # Validates tasks_back/tasks_gameplay refs (ADR/CH/overlay/depends_on).
    return run_and_capture(
        out_dir,
        name="task-links-validate",
        cmd=["py", "-3", "scripts/python/task_links_validate.py"],
        timeout_sec=300,
    )


def step_task_test_refs_validate(out_dir: Path, triplet: TaskmasterTriplet, *, require_non_empty: bool) -> StepResult:
    cmd = [
        "py",
        "-3",
        "scripts/python/validate_task_test_refs.py",
        "--task-id",
        str(triplet.task_id),
        "--out",
        str(out_dir / "task-test-refs.json"),
    ]
    if require_non_empty:
        cmd.append("--require-non-empty")
    return run_and_capture(out_dir, name="task-test-refs", cmd=cmd, timeout_sec=60)


def step_acceptance_refs_validate(out_dir: Path, triplet: TaskmasterTriplet) -> StepResult:
    # Hard gate (deterministic): acceptance items must declare "Refs:" and be consistent with test_refs at refactor stage.
    cmd = [
        "py",
        "-3",
        "scripts/python/validate_acceptance_refs.py",
        "--task-id",
        str(triplet.task_id),
        "--stage",
        "refactor",
        "--out",
        str(out_dir / "acceptance-refs.json"),
    ]
    return run_and_capture(out_dir, name="acceptance-refs", cmd=cmd, timeout_sec=60)


def step_acceptance_anchors_validate(out_dir: Path, triplet: TaskmasterTriplet) -> StepResult:
    # Hard gate (deterministic): referenced tests must contain ACC:T<id>.<n> anchors.
    cmd = [
        "py",
        "-3",
        "scripts/python/validate_acceptance_anchors.py",
        "--task-id",
        str(triplet.task_id),
        "--stage",
        "refactor",
        "--out",
        str(out_dir / "acceptance-anchors.json"),
    ]
    return run_and_capture(out_dir, name="acceptance-anchors", cmd=cmd, timeout_sec=60)


def step_overlay_validate(out_dir: Path, triplet: TaskmasterTriplet) -> StepResult:
    primary = run_and_capture(
        out_dir,
        name="validate-task-overlays",
        cmd=["py", "-3", "scripts/python/validate_task_overlays.py"],
        timeout_sec=300,
    )
    overlay = triplet.overlay()
    test_refs = None
    if overlay:
        test_refs = run_and_capture(
            out_dir,
            name="validate-test-refs",
            cmd=[
                "py",
                "-3",
                "scripts/python/validate_overlay_test_refs.py",
                "--overlay",
                overlay,
                "--out",
                str(out_dir / "validate-test-refs.json"),
            ],
            timeout_sec=60,
        )

    ok = primary.status == "ok" and (test_refs is None or test_refs.status == "ok")
    details = {"primary": primary.__dict__, "test_refs": test_refs.__dict__ if test_refs else None, "overlay": overlay}
    write_json(out_dir / "overlay-validate.json", details)
    return StepResult(
        name="validate-task-overlays",
        status="ok" if ok else "fail",
        rc=0 if ok else 1,
        cmd=primary.cmd,
        log=primary.log,
        details=details,
    )


def step_contracts_validate(out_dir: Path) -> StepResult:
    return run_and_capture(
        out_dir,
        name="validate-contracts",
        cmd=["py", "-3", "scripts/python/validate_contracts.py"],
        timeout_sec=300,
    )


def step_architecture_boundary(out_dir: Path) -> StepResult:
    return run_and_capture(
        out_dir,
        name="architecture-boundary",
        cmd=["py", "-3", "scripts/python/check_architecture_boundary.py", "--out", str(out_dir / "architecture-boundary.json")],
        timeout_sec=60,
    )


def step_build_warnaserror(out_dir: Path) -> StepResult:
    return run_and_capture(
        out_dir,
        name="dotnet-build-warnaserror",
        cmd=["py", "-3", "scripts/sc/build.py", "GodotGame.csproj", "--type", "dev"],
        timeout_sec=1_800,
    )


def step_security_soft(out_dir: Path) -> StepResult:
    # Soft checks: do not block, but record output.
    steps = []
    steps.append(run_and_capture(out_dir, "check-sentry-secrets", ["py", "-3", "scripts/python/check_sentry_secrets.py"], 60))
    steps.append(run_and_capture(out_dir, "check-sanguo-gameloop-contracts", ["py", "-3", "scripts/python/check_sanguo_gameloop_contracts.py"], 60))
    steps.append(
        run_and_capture(
            out_dir,
            "security-soft-scan",
            ["py", "-3", "scripts/python/security_soft_scan.py", "--out", str(out_dir / "security-soft-scan.json")],
            120,
        )
    )
    # Optional: encoding scan (soft)
    steps.append(run_and_capture(out_dir, "check-encoding-since-today", ["py", "-3", "scripts/python/check_encoding.py", "--since-today"], 300))

    # Soft gate: always ok, but include failures in details.
    details = {"steps": [s.__dict__ for s in steps]}
    write_json(out_dir / "security-soft.json", details)
    return StepResult(name="security-soft", status="ok", details=details)


def step_tests_all(out_dir: Path, godot_bin: str | None) -> StepResult:
    cmd = ["py", "-3", "scripts/sc/test.py", "--type", "all"]
    if godot_bin:
        cmd += ["--godot-bin", godot_bin]
    return run_and_capture(out_dir, name="tests-all", cmd=cmd, timeout_sec=1_200)


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

