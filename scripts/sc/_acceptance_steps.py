#!/usr/bin/env python3
"""
Acceptance check step implementations.
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

from _acceptance_steps_quality import (
    step_perf_budget,
    step_quality_rules,
    step_test_quality_soft,
)
from _acceptance_steps_runner import run_and_capture
from _acceptance_steps_security import (
    step_security_hard,
    step_security_soft,
    step_ui_event_security,
)
from _step_result import StepResult
from _subtasks_coverage_step import step_subtasks_coverage_llm
from _taskmaster import TaskmasterTriplet
from _util import repo_root, write_json


ADR_STATUS_RE = re.compile(r"^\s*-?\s*(?:Status|status)\s*:\s*([A-Za-z]+)\s*$", re.MULTILINE)


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
    raw_budget = (os.getenv("TASK_LINKS_MAX_WARNINGS", "") or "").strip()
    max_warnings = -1
    if raw_budget:
        try:
            max_warnings = int(raw_budget)
        except ValueError:
            max_warnings = -1

    cmd = ["py", "-3", "scripts/python/task_links_validate.py", "--mode", "all"]
    if max_warnings >= 0:
        cmd.extend(["--max-warnings", str(max_warnings)])
    cmd.extend(["--summary-out", str(out_dir / "task-links-validate-summary.json")])

    return run_and_capture(
        out_dir,
        name="task-links-validate",
        cmd=cmd,
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
        cmd=["py", "-3", "scripts/sc/build.py", "NewRouge.csproj", "--type", "dev"],
        timeout_sec=1_800,
    )


def step_tests_all(
    out_dir: Path,
    godot_bin: str | None,
    *,
    run_id: str | None = None,
    test_type: str = "all",
    task_id: str | None = None,
) -> StepResult:
    cmd = ["py", "-3", "scripts/sc/test.py", "--type", test_type]
    if str(task_id or "").strip():
        cmd += ["--task-id", str(task_id).strip()]
    if run_id:
        cmd += ["--run-id", run_id]
    if godot_bin and test_type != "unit":
        cmd += ["--godot-bin", godot_bin]
    return run_and_capture(out_dir, name="tests-all", cmd=cmd, timeout_sec=1_200)


__all__ = [
    "StepResult",
    "step_acceptance_anchors_validate",
    "step_acceptance_refs_validate",
    "step_adr_compliance",
    "step_architecture_boundary",
    "step_build_warnaserror",
    "step_contracts_validate",
    "step_overlay_validate",
    "step_perf_budget",
    "step_quality_rules",
    "step_security_hard",
    "step_security_soft",
    "step_subtasks_coverage_llm",
    "step_task_links_validate",
    "step_task_test_refs_validate",
    "step_test_quality_soft",
    "step_tests_all",
    "step_ui_event_security",
]
