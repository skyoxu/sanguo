#!/usr/bin/env python3
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from _taskmaster import resolve_triplet
from _util import repo_root, run_cmd, today_str, write_json, write_text
from _tdd_shared import check_no_task_red_test_skeletons


def default_task_test_path(task_id: str) -> Path:
    return repo_root() / "Game.Core.Tests" / "Tasks" / f"Task{task_id}RedTests.cs"


def ensure_red_test_exists(task_id: str, title: str, *, allow_create: bool, out_dir: Path) -> Path | None:
    target = default_task_test_path(task_id)
    if target.exists():
        return target
    if not allow_create:
        return None
    target.parent.mkdir(parents=True, exist_ok=True)
    class_name = f"Task{task_id}RedTests"
    safe_title = " ".join(str(title).split())
    content = f"""using FluentAssertions;
using Xunit;

namespace Game.Core.Tests.Tasks;

public class {class_name}
{{
    [Fact]
    public void Red_IsFailingUntilTaskIsImplemented()
    {{
        // This test is intentionally failing to start a TDD cycle.
        true.Should().BeFalse(\"Task {task_id} not implemented yet: {safe_title}\");
    }}
}}
"""
    target.write_text(content, encoding="utf-8")
    write_text(out_dir / "generated-red-test.txt", str(target))
    return target


def run_dotnet_test_filtered(task_id: str, *, solution: str, configuration: str, out_dir: Path) -> dict[str, Any]:
    filter_expr = f"FullyQualifiedName~Game.Core.Tests.Tasks.Task{task_id}"
    cmd = ["dotnet", "test", solution, "-c", configuration, "--filter", filter_expr]
    rc, out = run_cmd(cmd, cwd=repo_root(), timeout_sec=900)
    log_path = out_dir / "dotnet-test-filtered.log"
    write_text(log_path, out)
    return {"name": "dotnet-test-filtered", "cmd": cmd, "rc": rc, "log": str(log_path), "filter": filter_expr}


def run_sc_analyze_task_context(*, task_id: str, out_dir: Path) -> dict[str, Any]:
    cmd = [
        "py",
        "-3",
        "scripts/sc/analyze.py",
        "--task-id",
        str(task_id),
        "--focus",
        "all",
        "--depth",
        "quick",
        "--format",
        "json",
    ]
    rc, out = run_cmd(cmd, cwd=repo_root(), timeout_sec=900)
    log_path = out_dir / "sc-analyze.log"
    write_text(log_path, out)
    return {"name": "sc-analyze", "cmd": cmd, "rc": rc, "log": str(log_path), "status": "ok" if rc == 0 else "fail"}


def validate_task_context_required_fields(*, task_id: str, stage: str, out_dir: Path) -> dict[str, Any]:
    ctx_path = repo_root() / "logs" / "ci" / today_str() / "sc-analyze" / f"task_context.{task_id}.json"
    cmd = [
        "py",
        "-3",
        "scripts/python/validate_task_context_required_fields.py",
        "--task-id",
        str(task_id),
        "--stage",
        str(stage),
        "--context",
        str(ctx_path),
        "--out",
        str(out_dir / "task-context-required.json"),
    ]
    rc, out = run_cmd(cmd, cwd=repo_root(), timeout_sec=60)
    log_path = out_dir / "validate-task-context-required.log"
    write_text(log_path, out)
    return {"name": "validate_task_context_required_fields", "cmd": cmd, "rc": rc, "log": str(log_path), "status": "ok" if rc == 0 else "fail"}


def run_green_gate(
    *,
    solution: str,
    configuration: str,
    out_dir: Path,
    coverage_gate: bool,
    coverage_lines_min: int,
    coverage_branches_min: int,
) -> dict[str, Any]:
    if coverage_gate:
        os.environ["COVERAGE_LINES_MIN"] = str(coverage_lines_min)
        os.environ["COVERAGE_BRANCHES_MIN"] = str(coverage_branches_min)
    else:
        os.environ.pop("COVERAGE_LINES_MIN", None)
        os.environ.pop("COVERAGE_BRANCHES_MIN", None)
    cmd = ["py", "-3", "scripts/python/run_dotnet.py", "--solution", solution, "--configuration", configuration]
    rc, out = run_cmd(cmd, cwd=repo_root(), timeout_sec=1_800)
    log_path = out_dir / "run_dotnet.log"
    write_text(log_path, out)
    return {"name": "run_dotnet", "cmd": cmd, "rc": rc, "log": str(log_path), "stdout": out}


def run_refactor_checks(out_dir: Path, *, task_id: str) -> list[dict[str, Any]]:
    steps: list[dict[str, Any]] = [check_no_task_red_test_skeletons(out_dir)]
    test_refs_script = repo_root() / "scripts" / "python" / "validate_task_test_refs.py"
    test_refs_log = out_dir / "validate_task_test_refs.log"
    if not test_refs_script.exists():
        write_text(
            test_refs_log,
            "FAIL: missing scripts/python/validate_task_test_refs.py\n"
            "Fix:\n"
            "  - git pull (or restore the file)\n",
        )
        steps.append(
            {
                "name": "validate_task_test_refs",
                "cmd": ["py", "-3", "scripts/python/validate_task_test_refs.py"],
                "rc": 1,
                "log": str(test_refs_log),
                "status": "fail",
                "reason": "missing:validate_task_test_refs.py",
            }
        )
    else:
        cmd = [
            "py",
            "-3",
            "scripts/python/validate_task_test_refs.py",
            "--task-id",
            str(task_id),
            "--out",
            str(out_dir / "task-test-refs.json"),
            "--require-non-empty",
        ]
        rc, out = run_cmd(cmd, cwd=repo_root(), timeout_sec=60)
        write_text(test_refs_log, out)
        steps.append({"name": "validate_task_test_refs", "cmd": cmd, "rc": rc, "log": str(test_refs_log), "status": "ok" if rc == 0 else "fail"})

    candidates = [
        ("validate_acceptance_refs", ["py", "-3", "scripts/python/validate_acceptance_refs.py", "--task-id", str(task_id), "--stage", "refactor", "--out", str(out_dir / "acceptance-refs.json")], out_dir / "validate_acceptance_refs.log", 60),
        ("validate_acceptance_anchors", ["py", "-3", "scripts/python/validate_acceptance_anchors.py", "--task-id", str(task_id), "--stage", "refactor", "--out", str(out_dir / "acceptance-anchors.json")], out_dir / "validate_acceptance_anchors.log", 60),
        ("check_test_naming", ["py", "-3", "scripts/python/check_test_naming.py", "--task-id", str(task_id), "--style", "should_when"], out_dir / "check_test_naming.log", 900),
        ("check_tasks_all_refs", ["py", "-3", "scripts/python/check_tasks_all_refs.py"], out_dir / "check_tasks_all_refs.log", 900),
        ("validate_contracts", ["py", "-3", "scripts/python/validate_contracts.py"], out_dir / "validate_contracts.log", 900),
    ]
    required_paths = {
        "check_test_naming": "scripts/python/check_test_naming.py",
        "check_tasks_all_refs": "scripts/python/check_tasks_all_refs.py",
        "validate_contracts": "scripts/python/validate_contracts.py",
    }
    for name, cmd, log_path, timeout_sec in candidates:
        requires = required_paths.get(name)
        if requires and not (repo_root() / requires).exists():
            write_text(log_path, f"SKIP missing: {requires}\n")
            steps.append({"name": name, "cmd": cmd, "rc": 0, "log": str(log_path), "status": "skipped", "reason": f"missing:{requires}"})
            continue
        rc, out = run_cmd(cmd, cwd=repo_root(), timeout_sec=timeout_sec)
        write_text(log_path, out)
        steps.append({"name": name, "cmd": cmd, "rc": rc, "log": str(log_path), "status": "ok" if rc == 0 else "fail"})
    return steps


def build_summary(*, stage: str, allow_contract_changes: bool, triplet: Any) -> dict[str, Any]:
    return {
        "cmd": "sc-build-tdd",
        "stage": stage,
        "allow_contract_changes": bool(allow_contract_changes),
        "status": "fail",
        "steps": [],
        "task": {
            "task_id": triplet.task_id,
            "title": triplet.master.get("title"),
            "status": triplet.master.get("status"),
            "adrRefs": triplet.adr_refs(),
            "archRefs": triplet.arch_refs(),
            "overlay": triplet.overlay(),
            "taskdoc": triplet.taskdoc_path,
        },
    }


def write_summary(out_dir: Path, summary: dict[str, Any]) -> None:
    write_json(out_dir / "summary.json", summary)


def print_refactor_failure_hints(*, out_dir: Path, failed_count: int) -> None:
    print(f"SC_BUILD_TDD status=fail out={out_dir} failed_steps={failed_count}")
    def _print_top_errors(json_path: Path, *, label: str, max_items: int = 12) -> None:
        if not json_path.exists():
            return
        try:
            payload = json.loads(json_path.read_text(encoding="utf-8"))
        except Exception:
            return
        errs = payload.get("errors")
        if not isinstance(errs, list) or not errs:
            return
        print(f"{label}:")
        for item in [str(x) for x in errs[:max_items]]:
            print(f"  - {item}")
        if len(errs) > max_items:
            print(f"  ... ({len(errs) - max_items} more)")
    _print_top_errors(out_dir / "acceptance-refs.json", label="ACCEPTANCE_REFS_TOP_ERRORS")
    _print_top_errors(out_dir / "task-test-refs.json", label="TASK_TEST_REFS_TOP_ERRORS")
    print("Fix hints:")
    print(f"  - Check logs: {out_dir}")
    print("  - Ensure every acceptance item has 'Refs:' and referenced files exist")
    print("  - Ensure refs are included in test_refs (or run update_task_test_refs_from_acceptance_refs.py)")
