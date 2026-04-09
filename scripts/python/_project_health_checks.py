#!/usr/bin/env python3
"""Project-health scan logic."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Any

from _project_health_common import (
    ALLOWED_BASE_08_FILES,
    GODOT_PATTERN,
    PRD_PATTERN,
    contract_files,
    has_task_triplet,
    overlay_indexes,
    repo_rel,
    resolve_root,
    task_status_counts,
    task_triplet_paths,
    unit_test_files,
    write_project_health_record,
)
from solution_resolver import resolve_solution_path


def detect_project_stage(root: Path | str | None = None) -> dict[str, Any]:
    resolved_root = resolve_root(root)
    real_triplet = task_triplet_paths(resolved_root, Path(".taskmaster") / "tasks")
    example_triplet = task_triplet_paths(resolved_root, Path("examples") / "taskmaster")
    signals = {
        "project_godot": (resolved_root / "project.godot").exists(),
        "readme": (resolved_root / "README.md").exists(),
        "agents": (resolved_root / "AGENTS.md").exists(),
        "real_task_triplet": has_task_triplet(real_triplet),
        "example_task_triplet": has_task_triplet(example_triplet),
        "overlay_indexes": len(overlay_indexes(resolved_root)),
        "contract_files": len(contract_files(resolved_root)),
        "unit_test_files": len(unit_test_files(resolved_root)),
    }
    stage = "bootstrap"
    status = "fail"
    summary = "bootstrap blockers remain"

    if not all([signals["project_godot"], signals["readme"], signals["agents"]]):
        summary = "repo bootstrap is incomplete"
    elif not signals["real_task_triplet"]:
        stage = "triplet-missing"
        status = "warn"
        summary = (
            "real task triplet is missing; repo is still relying on examples/taskmaster"
            if signals["example_task_triplet"]
            else "task triplet is missing"
        )
    elif signals["overlay_indexes"] == 0:
        stage = "overlay-baseline-needed"
        status = "warn"
        summary = "task triplet exists but overlay baseline is missing"
    elif signals["contract_files"] == 0 or signals["unit_test_files"] == 0:
        stage = "contracts-baseline-needed"
        status = "warn"
        summary = "overlay exists but contracts or test baseline is still missing"
    else:
        counts = task_status_counts(resolved_root)
        if counts["done"] > 0 and counts["in_progress"] == 0:
            stage = "convergence-ready"
            status = "ok"
            summary = "repo is in convergence mode; no in-progress tasks detected"
        else:
            stage = "daily-task-loop-ready"
            status = "ok"
            summary = "repo is ready for the daily task loop"
        signals["task_status_counts"] = counts

    return {
        "kind": "detect-project-stage",
        "status": status,
        "stage": stage,
        "summary": summary,
        "exit_code": 1 if status == "fail" else 0,
        "signals": signals,
        "paths": {
            "real_task_triplet": {name: repo_rel(path, root=resolved_root) for name, path in real_triplet.items()},
            "example_task_triplet": {name: repo_rel(path, root=resolved_root) for name, path in example_triplet.items()},
        },
    }


def doctor_check(
    *,
    check_id: str,
    status: str,
    path: str,
    summary: str,
    recommendation: str,
) -> dict[str, str]:
    return {
        "id": check_id,
        "status": status,
        "path": path,
        "summary": summary,
        "recommendation": recommendation,
    }


def doctor_project(root: Path | str | None = None) -> dict[str, Any]:
    resolved_root = resolve_root(root)
    real_triplet = task_triplet_paths(resolved_root, Path(".taskmaster") / "tasks")
    example_triplet = task_triplet_paths(resolved_root, Path("examples") / "taskmaster")
    resolved_solution_name = resolve_solution_path("auto", repo_root=resolved_root)
    resolved_solution_path = resolved_root / resolved_solution_name

    checks = [
        doctor_check(
            check_id="project-godot",
            status="ok" if (resolved_root / "project.godot").exists() else "fail",
            path="project.godot",
            summary="Godot project entry exists" if (resolved_root / "project.godot").exists() else "project.godot is missing",
            recommendation="keep current entry" if (resolved_root / "project.godot").exists() else "restore the Godot project entry",
        ),
        doctor_check(
            check_id="readme",
            status="ok" if (resolved_root / "README.md").exists() else "fail",
            path="README.md",
            summary="README exists" if (resolved_root / "README.md").exists() else "README.md is missing",
            recommendation="keep README indexed" if (resolved_root / "README.md").exists() else "restore README.md",
        ),
        doctor_check(
            check_id="agents",
            status="ok" if (resolved_root / "AGENTS.md").exists() else "fail",
            path="AGENTS.md",
            summary="AGENTS entry exists" if (resolved_root / "AGENTS.md").exists() else "AGENTS.md is missing",
            recommendation="keep AGENTS as the repo map" if (resolved_root / "AGENTS.md").exists() else "restore AGENTS.md",
        ),
        doctor_check(
            check_id="solution",
            status="ok" if resolved_solution_path.exists() else "fail",
            path=resolved_solution_name,
            summary="solution exists" if resolved_solution_path.exists() else f"{resolved_solution_name} is missing",
            recommendation="keep the .NET solution in repo root" if resolved_solution_path.exists() else f"restore or create {resolved_solution_name}",
        ),
        doctor_check(
            check_id="core-tests-csproj",
            status="ok" if (resolved_root / "Game.Core.Tests" / "Game.Core.Tests.csproj").exists() else "fail",
            path="Game.Core.Tests/Game.Core.Tests.csproj",
            summary="core test project exists"
            if (resolved_root / "Game.Core.Tests" / "Game.Core.Tests.csproj").exists()
            else "Game.Core.Tests/Game.Core.Tests.csproj is missing",
            recommendation="keep the domain test project wired"
            if (resolved_root / "Game.Core.Tests" / "Game.Core.Tests.csproj").exists()
            else "restore the core test project",
        ),
        doctor_check(
            check_id="task-triplet-real",
            status="ok" if has_task_triplet(real_triplet) else "warn",
            path=".taskmaster/tasks",
            summary="real task triplet exists" if has_task_triplet(real_triplet) else "real task triplet is missing",
            recommendation="keep task triplet updated"
            if has_task_triplet(real_triplet)
            else "create .taskmaster/tasks/tasks*.json before running task-scoped workflows",
        ),
        doctor_check(
            check_id="task-triplet-example",
            status="ok" if has_task_triplet(example_triplet) else "warn",
            path="examples/taskmaster",
            summary="example triplet exists" if has_task_triplet(example_triplet) else "example task triplet is missing",
            recommendation="keep example triplet aligned with the template"
            if has_task_triplet(example_triplet)
            else "restore example task triplet for template onboarding",
        ),
        doctor_check(
            check_id="overlay-indexes",
            status="ok" if overlay_indexes(resolved_root) else "warn",
            path="docs/architecture/overlays/*/08/_index.md",
            summary="overlay indexes exist" if overlay_indexes(resolved_root) else "overlay indexes are missing",
            recommendation="keep overlay indexes current"
            if overlay_indexes(resolved_root)
            else "create overlay 08 indexes before daily task work",
        ),
        doctor_check(
            check_id="contracts-baseline",
            status="ok" if contract_files(resolved_root) else "warn",
            path="Game.Core/Contracts",
            summary="contract baseline exists" if contract_files(resolved_root) else "contract baseline is missing",
            recommendation="keep contracts as the SSoT"
            if contract_files(resolved_root)
            else "restore minimal contract baseline under Game.Core/Contracts",
        ),
        doctor_check(
            check_id="workflow-docs",
            status="ok"
            if (resolved_root / "workflow.md").exists() and (resolved_root / "DELIVERY_PROFILE.md").exists()
            else "warn",
            path="workflow.md + DELIVERY_PROFILE.md",
            summary="workflow entry docs exist"
            if (resolved_root / "workflow.md").exists() and (resolved_root / "DELIVERY_PROFILE.md").exists()
            else "workflow entry docs are incomplete",
            recommendation="keep workflow docs indexed"
            if (resolved_root / "workflow.md").exists() and (resolved_root / "DELIVERY_PROFILE.md").exists()
            else "restore workflow.md and DELIVERY_PROFILE.md",
        ),
        doctor_check(
            check_id="godot-bin-env",
            status="ok" if os.environ.get("GODOT_BIN") else "warn",
            path="env:GODOT_BIN",
            summary="GODOT_BIN is set" if os.environ.get("GODOT_BIN") else "GODOT_BIN is not set",
            recommendation="keep GODOT_BIN configured for local engine checks"
            if os.environ.get("GODOT_BIN")
            else "set GODOT_BIN before running local hard checks with Godot",
        ),
    ]

    fail_count = sum(1 for item in checks if item["status"] == "fail")
    warn_count = sum(1 for item in checks if item["status"] == "warn")
    status = "fail" if fail_count else ("warn" if warn_count else "ok")
    summary = f"doctor checks: fail={fail_count} warn={warn_count} ok={len(checks) - fail_count - warn_count}"
    return {
        "kind": "doctor-project",
        "status": status,
        "summary": summary,
        "exit_code": 1 if fail_count else 0,
        "counts": {
            "fail": fail_count,
            "warn": warn_count,
            "ok": len(checks) - fail_count - warn_count,
        },
        "checks": checks,
    }


def scan_text_violations(root: Path, relative_dir: str, *, rule_id: str) -> list[dict[str, Any]]:
    base = root / relative_dir
    if not base.exists():
        return []
    violations: list[dict[str, Any]] = []
    for path in sorted(base.rglob("*.cs")):
        if any(part in {"bin", "obj"} for part in path.parts):
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        if GODOT_PATTERN.search(text):
            violations.append(
                {
                    "rule_id": rule_id,
                    "path": repo_rel(path, root=root),
                    "summary": "Godot API reference crossed a pure-code boundary",
                }
            )
    return violations


def scan_base_prd_leaks(root: Path) -> list[dict[str, Any]]:
    base = root / "docs" / "architecture" / "base"
    if not base.exists():
        return []
    violations: list[dict[str, Any]] = []
    for path in sorted(base.rglob("*.md")):
        text = path.read_text(encoding="utf-8", errors="ignore")
        if PRD_PATTERN.search(text):
            violations.append(
                {
                    "rule_id": "base-docs-no-prd-leak",
                    "path": repo_rel(path, root=root),
                    "summary": "PRD identifier leaked into base architecture docs",
                }
            )
    return violations


def scan_extra_base_08_files(root: Path) -> list[dict[str, Any]]:
    base = root / "docs" / "architecture" / "base"
    if not base.exists():
        return []
    warnings: list[dict[str, Any]] = []
    for path in sorted(base.glob("08-*.md")):
        if path.name in ALLOWED_BASE_08_FILES:
            continue
        warnings.append(
            {
                "rule_id": "base-08-template-only",
                "path": repo_rel(path, root=root),
                "summary": "feature-slice content should stay in overlays, not base/08",
            }
        )
    return warnings


def git_tracked_matches(root: Path, relative_path: str) -> list[str]:
    git_dir = root / ".git"
    if not git_dir.exists():
        return []
    try:
        proc = subprocess.run(
            ["git", "ls-files", relative_path],
            cwd=root,
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:
        return []
    if proc.returncode != 0:
        return []
    return [line.strip() for line in proc.stdout.splitlines() if line.strip()]


def check_directory_boundaries(root: Path | str | None = None) -> dict[str, Any]:
    resolved_root = resolve_root(root)
    violations: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []

    violations.extend(scan_text_violations(resolved_root, "Game.Core", rule_id="game-core-no-godot"))
    violations.extend(scan_text_violations(resolved_root, "Game.Core/Contracts", rule_id="contracts-no-godot"))
    violations.extend(scan_text_violations(resolved_root, "Scripts/Core", rule_id="scripts-core-no-godot"))
    violations.extend(scan_base_prd_leaks(resolved_root))
    warnings.extend(scan_extra_base_08_files(resolved_root))

    for tracked in git_tracked_matches(resolved_root, "taskdoc"):
        warnings.append(
            {
                "rule_id": "root-taskdoc-not-tracked",
                "path": tracked,
                "summary": "root taskdoc should not be git-tracked in this repository",
            }
        )

    status = "fail" if violations else ("warn" if warnings else "ok")
    summary = f"boundary checks: fail={len(violations)} warn={len(warnings)}"
    return {
        "kind": "check-directory-boundaries",
        "status": status,
        "summary": summary,
        "exit_code": 1 if violations else 0,
        "violations": violations,
        "warnings": warnings,
        "rules_checked": [
            "game-core-no-godot",
            "contracts-no-godot",
            "scripts-core-no-godot",
            "base-docs-no-prd-leak",
            "base-08-template-only",
            "root-taskdoc-not-tracked",
        ],
    }


def project_health_scan(root: Path | str | None = None) -> dict[str, Any]:
    resolved_root = resolve_root(root)
    results = [
        detect_project_stage(resolved_root),
        doctor_project(resolved_root),
        check_directory_boundaries(resolved_root),
    ]
    for item in results:
        write_project_health_record(root=resolved_root, kind=item["kind"], payload=item)
    exit_code = 1 if any(int(item.get("exit_code", 0)) != 0 for item in results) else 0
    overall = "ok"
    if any(item.get("status") == "fail" for item in results):
        overall = "fail"
    elif any(item.get("status") == "warn" for item in results):
        overall = "warn"
    return {
        "kind": "project-health-scan",
        "status": overall,
        "exit_code": exit_code,
        "results": results,
    }
