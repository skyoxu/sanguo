#!/usr/bin/env python3
"""
Acceptance check step implementations.
"""

from __future__ import annotations

import json
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
from _util import repo_root, today_str, write_json, write_text


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
    overlay_checks: list[StepResult] = []
    task_files: list[tuple[str, str]] = [(triplet.tasks_json_path, "master")]
    if triplet.back is not None:
        task_files.append((triplet.tasks_back_path, "back"))
    if triplet.gameplay is not None:
        task_files.append((triplet.tasks_gameplay_path, "gameplay"))

    seen: set[str] = set()
    for task_file, label in task_files:
        key = str(task_file).strip()
        if not key or key in seen:
            continue
        seen.add(key)
        overlay_checks.append(
            run_and_capture(
                out_dir,
                name=f"validate-task-overlays-{label}",
                cmd=[
                    "py",
                    "-3",
                    "scripts/python/validate_task_overlays.py",
                    "--task-file",
                    str(task_file),
                    "--task-id",
                    str(triplet.task_id),
                ],
                timeout_sec=180,
            )
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

    ok = all(item.status == "ok" for item in overlay_checks) and (test_refs is None or test_refs.status == "ok")
    aggregate_log = out_dir / "validate-task-overlays.log"
    write_text(
        aggregate_log,
        "\n".join(
            [
                f"{item.name} status={item.status} rc={item.rc} log={item.log}"
                for item in overlay_checks
            ]
        )
        + ("\n" if overlay_checks else ""),
    )
    details = {
        "primary": [item.__dict__ for item in overlay_checks],
        "test_refs": test_refs.__dict__ if test_refs else None,
        "overlay": overlay,
        "task_id": str(triplet.task_id),
    }
    write_json(out_dir / "overlay-validate.json", details)
    return StepResult(
        name="validate-task-overlays",
        status="ok" if ok else "fail",
        rc=0 if ok else 1,
        cmd=overlay_checks[0].cmd if overlay_checks else ["py", "-3", "scripts/python/validate_task_overlays.py"],
        log=str(aggregate_log),
        details=details,
    )


def _read_sc_test_summary_for_reuse(*, run_id: str | None, test_type: str, task_id: str | None) -> tuple[Path, dict[str, Any]] | None:
    override_summary = str(os.environ.get("SC_TEST_REUSE_SUMMARY") or "").strip()
    if override_summary:
        summary_path = Path(override_summary)
        if summary_path.exists():
            try:
                override_payload = json.loads(summary_path.read_text(encoding="utf-8"))
            except Exception:
                override_payload = {}
            if isinstance(override_payload, dict) and str(override_payload.get("status") or "").strip().lower() == "ok":
                actual_type = str(override_payload.get("type") or "").strip().lower()
                requested_type = str(test_type or "").strip().lower()
                requested_task = str(task_id or "").strip()
                if actual_type in {requested_type, "all"} and (not requested_task or str(override_payload.get("task_id") or "").strip() == requested_task):
                    return summary_path.parent, override_payload

    if not str(run_id or "").strip():
        return None
    sc_test_dir = repo_root() / "logs" / "ci" / today_str() / "sc-test"
    summary_path = sc_test_dir / "summary.json"
    run_id_path = sc_test_dir / "run_id.txt"
    if not summary_path.exists() or not run_id_path.exists():
        return None
    try:
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
    except Exception:
        return None
    if str(summary.get("status") or "").strip().lower() != "ok":
        return None
    if str(summary.get("run_id") or "").strip() != str(run_id).strip():
        return None
    if run_id_path.read_text(encoding="utf-8", errors="ignore").strip() != str(run_id).strip():
        return None
    actual_type = str(summary.get("type") or "").strip().lower()
    requested_type = str(test_type or "").strip().lower()
    if actual_type not in {requested_type, "all"}:
        return None
    requested_task = str(task_id or "").strip()
    if requested_task:
        if str(summary.get("task_id") or "").strip() != requested_task:
            return None
    return sc_test_dir, summary


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
        cmd=["py", "-3", "scripts/sc/build.py", "--type", "dev"],
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
    reused = _read_sc_test_summary_for_reuse(run_id=run_id, test_type=test_type, task_id=task_id)
    if reused is not None:
        sc_test_dir, summary = reused
        planned_cmd = [
            "py",
            "-3",
            "scripts/sc/test.py",
            "--type",
            test_type,
            "--no-coverage-gate",
            "--no-coverage-report",
        ]
        if str(task_id or "").strip():
            planned_cmd += ["--task-id", str(task_id).strip()]
        if run_id:
            planned_cmd += ["--run-id", run_id]
        if godot_bin and test_type != "unit":
            planned_cmd += ["--godot-bin", godot_bin]
        log_path = out_dir / "tests-all.log"
        write_text(log_path, f"[sc-acceptance-check] reused sc-test summary\nSC_TEST status=ok out={sc_test_dir}\n")
        return StepResult(
            name="tests-all",
            status="ok",
            rc=0,
            cmd=planned_cmd,
            log=str(log_path),
            details={
                "reused": True,
                "source_summary_file": str(sc_test_dir / "summary.json"),
                "source_run_id": str(summary.get("run_id") or ""),
                "source_test_type": str(summary.get("type") or ""),
            },
        )

    cmd = [
        "py",
        "-3",
        "scripts/sc/test.py",
        "--type",
        test_type,
        "--no-coverage-gate",
        "--no-coverage-report",
    ]
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
