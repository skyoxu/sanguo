from __future__ import annotations

import os
import shutil
from pathlib import Path
from typing import Any

from _sc_test_refs import build_dotnet_filter_from_cs_refs, task_scoped_cs_refs, task_scoped_gdunit_refs
from _util import repo_root, run_cmd, today_str, write_text


def run_unit(
    out_dir: Path,
    solution: str,
    configuration: str,
    *,
    run_id: str,
    task_id: str | None = None,
    allow_full_unit_fallback: bool = False,
) -> dict[str, Any]:
    cmd = ["py", "-3", "scripts/python/run_dotnet.py", "--solution", solution, "--configuration", configuration]
    task_cs_refs = task_scoped_cs_refs(task_id=task_id)
    task_filter = build_dotnet_filter_from_cs_refs(task_cs_refs)
    if task_filter:
        cmd += ["--filter", task_filter]
    rc, out = run_cmd(cmd, cwd=repo_root(), timeout_sec=1_800)
    zero_coverage_failure = (
        bool(task_filter)
        and int(rc) == 2
        and "RUN_DOTNET status=coverage_failed" in str(out)
        and "line=0.0%" in str(out)
        and "branch=0.0" in str(out)
    )
    if allow_full_unit_fallback and zero_coverage_failure:
        fallback_cmd = ["py", "-3", "scripts/python/run_dotnet.py", "--solution", solution, "--configuration", configuration]
        fallback_rc, fallback_out = run_cmd(fallback_cmd, cwd=repo_root(), timeout_sec=1_800)
        out = (
            f"{str(out).rstrip()}\n\n"
            "[sc-test] task-scoped coverage is 0.0%; retrying unit without task filter.\n"
            f"fallback_cmd: {' '.join(fallback_cmd)}\n"
            f"fallback_rc: {int(fallback_rc)}\n"
            "--- fallback output ---\n"
            f"{str(fallback_out)}"
        ).rstrip() + "\n"
        if int(fallback_rc) == 0:
            rc = 0
            cmd = fallback_cmd
    elif zero_coverage_failure:
        out = (
            f"{str(out).rstrip()}\n\n"
            "[sc-test] task-scoped coverage is 0.0%; full-suite fallback is disabled.\n"
            "[sc-test] Re-run with --allow-full-unit-fallback only when you intentionally want a repo-wide retry.\n"
        ).rstrip() + "\n"
    log_path = out_dir / "unit.log"
    write_text(log_path, out)
    unit_artifacts_dir = repo_root() / "logs" / "unit" / today_str()
    write_text(unit_artifacts_dir / "run_id.txt", run_id + "\n")
    return {
        "name": "unit",
        "cmd": cmd,
        "rc": rc,
        "log": str(log_path),
        "artifacts_dir": str(unit_artifacts_dir),
        "status": "ok" if rc == 0 else "fail",
    }


def run_coverage_report(out_dir: Path, unit_artifacts_dir: Path) -> dict[str, Any]:
    reportgenerator = shutil.which("reportgenerator")
    if not reportgenerator:
        return {
            "name": "coverage-report",
            "status": "skipped",
            "reason": "reportgenerator not found (install once via: dotnet tool install --global dotnet-reportgenerator-globaltool)",
        }
    cobertura = unit_artifacts_dir / "coverage.cobertura.xml"
    if not cobertura.exists():
        return {
            "name": "coverage-report",
            "status": "skipped",
            "reason": f"coverage file not found: {cobertura}",
        }
    target_dir = unit_artifacts_dir / "coverage-report"
    cmd = [
        "reportgenerator",
        f"-reports:{cobertura}",
        f"-targetdir:{target_dir}",
        "-reporttypes:Html",
    ]
    rc, out = run_cmd(cmd, cwd=repo_root(), timeout_sec=300)
    log_path = out_dir / "coverage-report.log"
    write_text(log_path, out)
    return {
        "name": "coverage-report",
        "cmd": cmd,
        "rc": rc,
        "log": str(log_path),
        "report_dir": str(target_dir),
        "status": "ok" if rc == 0 else "fail",
    }


def run_csharp_test_conventions(out_dir: Path, *, task_id: str | None = None) -> dict[str, Any]:
    cmd = ["py", "-3", "scripts/python/check_csharp_test_conventions.py"]
    if str(task_id or "").strip():
        cmd += ["--task-id", str(task_id).strip()]
    rc, out = run_cmd(cmd, cwd=repo_root(), timeout_sec=300)
    log_path = out_dir / "csharp-test-conventions.log"
    write_text(log_path, out)
    return {
        "name": "csharp-test-conventions",
        "cmd": cmd,
        "rc": rc,
        "log": str(log_path),
        "status": "ok" if rc == 0 else "fail",
    }


def run_gdunit_hard(
    out_dir: Path,
    godot_bin: str,
    timeout_sec: int,
    *,
    run_id: str,
    task_id: str | None = None,
    require_task_scoped_refs: bool = False,
) -> dict[str, Any]:
    date = today_str()
    report_dir = Path("logs") / "e2e" / date / "sc-test" / "gdunit-hard"
    os.environ["AUDIT_LOG_ROOT"] = str(repo_root() / "logs" / "ci" / date)
    add_dirs: list[str] = []
    tests_project = repo_root() / "Tests.Godot"
    if str(task_id or "").strip():
        task_refs = task_scoped_gdunit_refs(task_id=task_id, tests_project=tests_project)
        if not task_refs and require_task_scoped_refs:
            log_path = out_dir / "gdunit-hard.log"
            write_text(
                log_path,
                "\n".join(
                    [
                        "SC_TEST_GDUNIT_HARD status=fail reason=missing_task_scoped_gd_refs",
                        f"task_id: {str(task_id).strip()}",
                        "error: no task-scoped .gd refs resolved from task view files",
                    ]
                )
                + "\n",
            )
            return {
                "name": "gdunit-hard",
                "cmd": [],
                "rc": 1,
                "log": str(log_path),
                "report_dir": str(report_dir),
                "error": "missing_task_scoped_gd_refs",
                "status": "fail",
            }
        if task_refs:
            for rel_ref in task_refs:
                if rel_ref not in add_dirs:
                    add_dirs.append(rel_ref)
    if not add_dirs:
        for rel in ["tests/Scenes", "tests/UI", "tests/Adapters/Config", "tests/Security/Hard"]:
            if (tests_project / rel).exists():
                add_dirs.append(rel)
            elif (repo_root() / rel).exists():
                add_dirs.append(rel)
    cmd = [
        "py",
        "-3",
        "scripts/python/run_gdunit.py",
        "--prewarm",
        "--godot-bin",
        godot_bin,
        "--project",
        "Tests.Godot",
    ]
    for add_dir in add_dirs:
        cmd += ["--add", add_dir]
    cmd += ["--timeout-sec", str(timeout_sec), "--rd", str(report_dir)]
    rc, out = run_cmd(cmd, cwd=repo_root(), timeout_sec=timeout_sec + 300)
    log_path = out_dir / "gdunit-hard.log"
    write_text(log_path, out)
    write_text(repo_root() / report_dir / "run_id.txt", run_id + "\n")
    return {
        "name": "gdunit-hard",
        "cmd": cmd,
        "rc": rc,
        "log": str(log_path),
        "report_dir": str(report_dir),
        "status": "ok" if rc == 0 else "fail",
    }


def run_smoke(out_dir: Path, godot_bin: str, scene: str, task_id: str | None = None, *, strict: bool = True) -> dict[str, Any]:
    if scene.startswith("res://"):
        disk_path = repo_root() / scene[len("res://") :]
        if not disk_path.exists():
            msg = f"[sc-test] ERROR: smoke scene not found on disk: {disk_path}\n"
            log_path = out_dir / "smoke.log"
            write_text(log_path, msg)
            return {
                "name": "smoke",
                "cmd": [],
                "rc": 2,
                "log": str(log_path),
                "error": "smoke_scene_missing",
                "status": "fail",
            }
    cmd = [
        "py",
        "-3",
        "scripts/python/smoke_headless.py",
        "--godot-bin",
        godot_bin,
        "--project-path",
        ".",
        "--scene",
        scene,
        "--timeout-sec",
        "5",
    ]
    if strict:
        cmd.append("--strict")
    if str(task_id or "").strip():
        cmd += ["--task-id", str(task_id).strip()]
    rc, out = run_cmd(cmd, cwd=repo_root(), timeout_sec=120)
    log_path = out_dir / "smoke.log"
    write_text(log_path, out)
    return {
        "name": "smoke",
        "cmd": cmd,
        "rc": rc,
        "log": str(log_path),
        "status": "ok" if rc == 0 else "fail",
    }
