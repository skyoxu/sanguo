#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Run grouped hard/soft gates for local and CI usage.

Modes:
- hard: fail on any gate failure
- soft: do not fail by default (unless --strict-soft)
- all : run hard then soft

Outputs:
- logs/ci/<YYYY-MM-DD>/gate-bundle/runs/<run-id>/<mode>/summary.json
- logs/ci/<YYYY-MM-DD>/gate-bundle/runs/<run-id>/<mode>/<gate>.log
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

try:
    from _delivery_profile import known_delivery_profiles, profile_gate_bundle_defaults, resolve_delivery_profile
except ImportError:
    _SC_DIR = Path(__file__).resolve().parents[1] / "sc"
    if str(_SC_DIR) not in sys.path:
        sys.path.insert(0, str(_SC_DIR))
    from _delivery_profile import known_delivery_profiles, profile_gate_bundle_defaults, resolve_delivery_profile

try:
    from gate_bundle_retention import prune_gate_bundle_runs
except ImportError:
    from scripts.python.gate_bundle_retention import prune_gate_bundle_runs


TASK_FILE_DEPENDENT_GATES = {
    "overlay_task_drift",
    "task_contract_refs_gate",
    "obligations_reuse_regression",
    "task_contract_test_matrix",
    "acceptance_stability_template",
    "check_tasks_all_refs_warning_budget",
    "llm_align_acceptance_self_check",
}

CONTRACT_INTERFACES_DIR = Path("Game.Core/Contracts/Interfaces")
PRD_GDD_CONSISTENCY_CONFIG = Path("scripts/python/config/prd-gdd-consistency-rules.json")
DELIVERY_PROFILE_CHOICES = tuple(sorted(known_delivery_profiles()))


def _configure_console_streams() -> None:
    for stream_name in ("stdout", "stderr"):
        stream = getattr(sys, stream_name, None)
        if stream is None or not hasattr(stream, "reconfigure"):
            continue
        try:
            stream.reconfigure(errors="replace")
        except Exception:
            continue


def _safe_print(text: str, *, end: str = "\n") -> None:
    try:
        print(text, end=end)
        return
    except UnicodeEncodeError:
        pass

    stream = getattr(sys, "stdout", None)
    encoding = getattr(stream, "encoding", None) or "utf-8"
    rendered = text.encode(encoding, errors="replace").decode(encoding, errors="replace")
    print(rendered, end=end)


def _existing_task_files(task_files: list[str], repo_root: Path) -> list[str]:
    existing: list[str] = []
    for item in task_files:
        candidate = (repo_root / str(item)).resolve()
        if candidate.exists() and candidate.is_file():
            existing.append(str(item))
    return existing


def _skip_reason_for_gate(name: str, *, repo_root: Path, task_files: list[str]) -> str | None:
    existing_task_files = _existing_task_files(task_files, repo_root)
    if name in TASK_FILE_DEPENDENT_GATES and not existing_task_files:
        return "missing_task_files"
    if name == "contract_interface_docs" and not (repo_root / CONTRACT_INTERFACES_DIR).exists():
        return "missing_contract_interfaces_dir"
    if name == "prd_gdd_semantic_consistency" and not (repo_root / PRD_GDD_CONSISTENCY_CONFIG).exists():
        return "missing_prd_gdd_consistency_config"
    return None


def _today() -> str:
    return dt.date.today().strftime("%Y-%m-%d")


def _default_run_id() -> str:
    gh_run = os.getenv("GITHUB_RUN_ID", "").strip()
    gh_attempt = os.getenv("GITHUB_RUN_ATTEMPT", "").strip()
    if gh_run:
        return f"gh-{gh_run}" + (f"-a{gh_attempt}" if gh_attempt else "")

    ci_pipeline = os.getenv("CI_PIPELINE_ID", "").strip()
    if ci_pipeline:
        return f"ci-{ci_pipeline}"

    build_id = os.getenv("BUILD_BUILDID", "").strip()
    if build_id:
        return f"build-{build_id}"

    ts = dt.datetime.now(dt.timezone.utc).strftime("%H%M%S-%f")
    return f"local-{ts}-{os.getpid()}"


def _default_out_root(run_id: str) -> Path:
    return Path("logs") / "ci" / _today() / "gate-bundle" / "runs" / run_id


def resolve_gate_bundle_runtime(*, delivery_profile: str | None, task_links_max_warnings: int | None = None, stability_template_hard: bool = False) -> dict[str, Any]:
    resolved_delivery_profile = resolve_delivery_profile(delivery_profile)
    defaults = profile_gate_bundle_defaults(resolved_delivery_profile)
    resolved_task_links_max_warnings = task_links_max_warnings
    if resolved_task_links_max_warnings is None:
        resolved_task_links_max_warnings = int(defaults.get("task_links_max_warnings", -1) or -1)
    resolved_stability_template_hard = bool(stability_template_hard or defaults.get("stability_template_hard", False))
    return {
        "delivery_profile": resolved_delivery_profile,
        "task_links_max_warnings": int(resolved_task_links_max_warnings),
        "stability_template_hard": resolved_stability_template_hard,
    }


def _resolve_gate_command(name: str, cmd: list[str], out_dir: Path) -> list[str]:
    resolved = [str(x) for x in cmd]
    if name == "task_contract_test_matrix":
        out_json = str((out_dir / "task-contract-test-matrix.json")).replace("\\", "/")
        out_md = str((out_dir / "task-contract-test-matrix.md")).replace("\\", "/")
        if "--out-json" not in resolved:
            resolved.extend(["--out-json", out_json])
        if "--out-md" not in resolved:
            resolved.extend(["--out-md", out_md])
    if name == "check_tasks_all_refs_warning_budget":
        out_json = str((out_dir / "check-tasks-all-refs-summary.json")).replace("\\", "/")
        if "--summary-out" not in resolved:
            resolved.extend(["--summary-out", out_json])
    return resolved


def _run_command(cmd: list[str], log_path: Path) -> tuple[int, str]:
    proc = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="ignore",
        check=False,
    )
    output = proc.stdout or ""
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.write_text(output, encoding="utf-8")
    return proc.returncode, output


def _hard_gate_commands(task_files: list[str], task_links_max_warnings: int = -1) -> list[dict[str, Any]]:
    commands = [
        {
            "name": "docs_utf8_integrity",
            "cmd": [
                "py",
                "-3",
                "scripts/python/check_docs_utf8_integrity.py",
                "--roots",
                "docs",
                ".github",
                ".taskmaster",
                "AGENTS.md",
            ],
        },
        {
            "name": "prd_gdd_semantic_consistency",
            "cmd": ["py", "-3", "scripts/python/check_prd_gdd_semantic_consistency.py"],
        },
        {
            "name": "overlay_task_drift",
            "cmd": ["py", "-3", "scripts/python/remind_overlay_task_drift.py"],
        },
        {
            "name": "task_contract_refs_gate",
            "cmd": [
                "py",
                "-3",
                "scripts/python/check_task_contract_refs.py",
                "--task-files",
                *task_files,
            ],
        },
        {
            "name": "no_hardcoded_core_events",
            "cmd": ["py", "-3", "scripts/python/check_no_hardcoded_core_events.py"],
        },
        {
            "name": "forbid_mirror_path_refs",
            "cmd": ["py", "-3", "scripts/python/forbid_mirror_path_refs.py", "--root", "."],
        },
        {
            "name": "validate_contracts",
            "cmd": ["py", "-3", "scripts/python/validate_contracts.py"],
        },
        {
            "name": "validate_recovery_docs",
            "cmd": ["py", "-3", "scripts/python/validate_recovery_docs.py"],
        },
        {
            "name": "check_domain_contracts",
            "cmd": ["py", "-3", "scripts/python/check_domain_contracts.py"],
        },
        {
            "name": "contract_interface_docs",
            "cmd": ["py", "-3", "scripts/python/check_contract_interface_docs.py"],
        },
        {
            "name": "check_test_naming",
            "cmd": [
                "py",
                "-3",
                "scripts/python/check_test_naming.py",
                "--style",
                "legacy",
            ],
        },
        {
            "name": "llm_obligations_self_check",
            "cmd": [
                "py",
                "-3",
                "scripts/sc/llm_extract_task_obligations.py",
                "--self-check",
            ],
        },
        {
            "name": "llm_align_acceptance_self_check",
            "cmd": [
                "py",
                "-3",
                "scripts/sc/llm_align_acceptance_semantics.py",
                "--self-check",
                "--strict-task-selection",
                "--garbled-gate",
                "off",
            ],
        },
        {
            "name": "llm_subtasks_coverage_self_check",
            "cmd": [
                "py",
                "-3",
                "scripts/sc/llm_check_subtasks_coverage.py",
                "--self-check",
            ],
        },
        {
            "name": "obligations_reuse_regression",
            "cmd": [
                "py",
                "-3",
                "scripts/python/check_obligations_reuse_regression.py",
                "--task-files",
                *task_files,
            ],
        },
        {
            "name": "obligations_unittest",
            "cmd": [
                "py",
                "-3",
                "-m",
                "unittest",
                "scripts.sc.tests.test_obligations_guard",
                "scripts.sc.tests.test_obligations_extract_helpers",
                "scripts.sc.tests.test_obligations_code_fingerprint",
                "scripts.sc.tests.test_obligations_output_contract",
                "scripts.sc.tests.test_obligations_cli_guards",
                "scripts.sc.tests.test_obligations_pipeline_order",
                "scripts.sc.tests.test_subtasks_coverage_cli_guards",
                "scripts.sc.tests.test_subtasks_coverage_schema",
                "scripts.sc.tests.test_subtasks_coverage_garbled_gate",
                "scripts.sc.tests.test_subtasks_coverage_selection_policy",
                "scripts.sc.tests.test_semantic_gate_all_contract",
                "scripts.sc.tests.test_semantic_gate_all_cli_guards",
                "scripts.sc.tests.test_fill_acceptance_refs_contract",
                "scripts.sc.tests.test_fill_acceptance_refs_cli_guards",
                "scripts.sc.tests.test_acceptance_task_requirements",
                "scripts.sc.tests.test_acceptance_steps_task_links_validate",
                "scripts.sc.tests.test_acceptance_check_runtime",
                "scripts.sc.tests.test_acceptance_check_cli_guards",
                "scripts.sc.tests.test_llm_review_cli_guards",
                "scripts.sc.tests.test_migrate_task_optional_hints",
                "-v",
            ],
        },
        {
            "name": "check_gate_bundle_consistency",
            "cmd": ["py", "-3", "scripts/python/check_gate_bundle_consistency.py"],
        },
        {
            "name": "check_workflow_gate_enforcement",
            "cmd": ["py", "-3", "scripts/python/check_workflow_gate_enforcement.py"],
        },
    ]
    if task_links_max_warnings >= 0:
        commands.append(
            {
                "name": "check_tasks_all_refs_warning_budget",
                "cmd": [
                    "py",
                    "-3",
                    "scripts/python/check_tasks_all_refs.py",
                    "--max-warnings",
                    str(task_links_max_warnings),
                ],
            }
        )
    return commands


def _acceptance_stability_gate(task_files: list[str]) -> dict[str, Any]:
    return {
        "name": "acceptance_stability_template",
        "cmd": [
            "py",
            "-3",
            "scripts/python/check_acceptance_stability_template.py",
            "--task-files",
            *task_files,
            "--targets-file",
            "scripts/python/config/acceptance-stability-targets.json",
        ],
    }


def _hard_gate_commands_with_options(
    task_files: list[str],
    stability_template_hard: bool,
    task_links_max_warnings: int = -1,
) -> list[dict[str, Any]]:
    commands = _hard_gate_commands(task_files, task_links_max_warnings)
    if stability_template_hard:
        commands.append(_acceptance_stability_gate(task_files))
    return commands


def _soft_gate_commands(task_files: list[str], stability_template_hard: bool) -> list[dict[str, Any]]:
    commands = [
        {
            "name": "task_contract_test_matrix",
            "cmd": [
                "py",
                "-3",
                "scripts/python/generate_task_contract_test_matrix.py",
                "--task-views",
                *task_files,
            ],
        },
    ]
    if not stability_template_hard:
        commands.append(_acceptance_stability_gate(task_files))
    return commands


def _append_github_step_summary(mode: str, summary: dict[str, Any], out_dir: Path) -> None:
    if mode != "soft":
        return

    step_summary = os.getenv("GITHUB_STEP_SUMMARY", "").strip()
    if not step_summary:
        return

    failed_gates = [g["name"] for g in summary.get("gates", []) if int(g.get("rc", 1)) != 0]
    lines = [
        "## Gate Bundle Soft Summary",
        f"- status: `{summary.get('status')}`",
        f"- failed: `{summary.get('failed')}/{summary.get('total')}`",
        f"- output: `{str((out_dir / 'summary.json')).replace('\\', '/')}`",
        f"- failed_gates: `{', '.join(failed_gates) if failed_gates else 'none'}`",
        "",
    ]

    step_path = Path(step_summary)
    step_path.parent.mkdir(parents=True, exist_ok=True)
    with step_path.open("a", encoding="utf-8") as fh:
        fh.write("\n".join(lines))


def _run_group(
    mode: str,
    commands: list[dict[str, Any]],
    strict_soft: bool,
    out_dir: Path,
    run_id: str,
    repo_root: Path,
    task_files: list[str],
) -> tuple[int, dict[str, Any]]:
    out_dir.mkdir(parents=True, exist_ok=True)

    gate_results: list[dict[str, Any]] = []
    failed = 0

    for item in commands:
        name = str(item["name"])
        cmd = _resolve_gate_command(name, [str(x) for x in item["cmd"]], out_dir)
        log_path = out_dir / f"{name}.log"

        skip_reason = _skip_reason_for_gate(name, repo_root=repo_root, task_files=task_files)
        if skip_reason:
            log_path.parent.mkdir(parents=True, exist_ok=True)
            skip_text = f"[gate-bundle] SKIP mode={mode} gate={name} reason={skip_reason}\n"
            log_path.write_text(skip_text, encoding="utf-8")
            _safe_print(skip_text, end="")
            gate_results.append(
                {
                    "name": name,
                    "rc": 0,
                    "command": cmd,
                    "log": str(log_path).replace("\\", "/"),
                    "skipped": True,
                    "skip_reason": skip_reason,
                }
            )
            continue

        _safe_print(f"[gate-bundle] START mode={mode} gate={name}")
        rc, output = _run_command(cmd, log_path)
        if output:
            _safe_print(output, end="" if output.endswith("\n") else "\n")
        _safe_print(f"[gate-bundle] END mode={mode} gate={name} rc={rc}")

        if rc != 0:
            failed += 1

        gate_results.append(
            {
                "name": name,
                "rc": rc,
                "command": cmd,
                "log": str(log_path).replace("\\", "/"),
            }
        )

    if mode == "hard":
        exit_code = 0 if failed == 0 else 1
    elif mode == "soft":
        exit_code = 0 if (failed == 0 or not strict_soft) else 1
    else:
        exit_code = 0 if failed == 0 else 1

    summary = {
        "ts": dt.datetime.now(dt.timezone.utc).isoformat(),
        "action": "gate-bundle",
        "run_id": run_id,
        "out_dir": str(out_dir).replace("\\", "/"),
        "mode": mode,
        "strict_soft": strict_soft,
        "total": len(gate_results),
        "failed": failed,
        "skipped": sum(1 for item in gate_results if item.get("skipped")),
        "status": "ok" if exit_code == 0 else "fail",
        "gates": gate_results,
    }

    if mode == "soft":
        failed_gates = [g["name"] for g in gate_results if int(g["rc"]) != 0]
        warning_summary = {
            "failed_gates": failed_gates,
            "failed_count": len(failed_gates),
            "is_warning": len(failed_gates) > 0,
        }
        summary["warning_summary"] = warning_summary
        warning_path = out_dir / "warning-summary.json"
        warning_path.write_text(
            json.dumps(warning_summary, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        if failed_gates:
            print(
                f"GATE_BUNDLE_SOFT_WARNING failed={len(failed_gates)} "
                f"gates={','.join(failed_gates)} out={str(warning_path).replace('\\', '/')}"
            )
            if os.getenv("GITHUB_ACTIONS", "").lower() == "true":
                print(
                    f"::warning title=Soft Gate Failures::"
                    f"{len(failed_gates)} soft gates failed: {', '.join(failed_gates)}"
                )
        else:
            print(
                f"GATE_BUNDLE_SOFT_WARNING failed=0 out={str(warning_path).replace('\\', '/')}"
            )

    (out_dir / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    _append_github_step_summary(mode, summary, out_dir)

    print(
        f"GATE_BUNDLE status={summary['status']} mode={mode} "
        f"failed={failed}/{len(gate_results)} out={str((out_dir / 'summary.json')).replace('\\', '/')}"
    )
    return exit_code, summary


def main() -> int:
    _configure_console_streams()
    env_task_links_budget = -1
    try:
        env_task_links_budget = int((os.getenv("TASK_LINKS_MAX_WARNINGS", "") or "-1").strip())
    except ValueError:
        env_task_links_budget = -1

    parser = argparse.ArgumentParser(description="Run grouped hard/soft gates.")
    parser.add_argument(
        "--mode",
        choices=["hard", "soft", "all"],
        default="all",
        help="Bundle mode: hard | soft | all",
    )
    parser.add_argument(
        "--strict-soft",
        action="store_true",
        help="When mode=soft/all, return non-zero if any soft gate fails",
    )
    parser.add_argument(
        "--delivery-profile",
        default=None,
        choices=DELIVERY_PROFILE_CHOICES,
        help="Delivery profile (default: env DELIVERY_PROFILE or fast-ship).",
    )
    parser.add_argument(
        "--task-links-max-warnings",
        type=int,
        default=None,
        help=(
            "Hard fail threshold for check_tasks_all_refs warnings. "
            "-1 disables this budget gate. Default reads TASK_LINKS_MAX_WARNINGS env, then delivery profile."
        ),
    )
    parser.add_argument(
        "--stability-template-hard",
        action="store_true",
        help=(
            "Move acceptance_stability_template from soft gates into hard gates. "
            "Default keeps it in soft gates."
        ),
    )
    parser.add_argument(
        "--task-files",
        nargs="*",
        default=[
            ".taskmaster/tasks/tasks_back.json",
            ".taskmaster/tasks/tasks_gameplay.json",
        ],
        help="Task view files passed to contract-related gates",
    )
    parser.add_argument(
        "--out-dir",
        default="",
        help="Optional output directory root. Default: logs/ci/<YYYY-MM-DD>/gate-bundle/runs/<run-id>",
    )
    parser.add_argument(
        "--run-id",
        default="",
        help="Optional run id. Default auto-derived from CI env vars or local timestamp.",
    )
    parser.add_argument(
        "--retention-days",
        type=int,
        default=14,
        help="Keep gate-bundle runs for at most N days (default: 14).",
    )
    parser.add_argument(
        "--max-runs-per-day",
        type=int,
        default=20,
        help="Keep at most N run directories per day (default: 20).",
    )
    parser.add_argument(
        "--skip-prune-runs",
        action="store_true",
        help="Skip post-run cleanup for gate-bundle/runs retention.",
    )
    args = parser.parse_args()

    task_links_max_warnings = args.task_links_max_warnings
    if task_links_max_warnings is None and env_task_links_budget >= 0:
        task_links_max_warnings = env_task_links_budget
    runtime = resolve_gate_bundle_runtime(
        delivery_profile=args.delivery_profile,
        task_links_max_warnings=task_links_max_warnings,
        stability_template_hard=bool(args.stability_template_hard),
    )
    os.environ["DELIVERY_PROFILE"] = str(runtime["delivery_profile"])

    if args.retention_days < 0:
        print("GATE_BUNDLE status=fail reason=invalid-retention-days")
        return 2
    if args.max_runs_per_day < 1:
        print("GATE_BUNDLE status=fail reason=invalid-max-runs-per-day")
        return 2

    run_id = args.run_id.strip() if isinstance(args.run_id, str) else ""
    if not run_id:
        run_id = _default_run_id()

    if args.out_dir:
        out_root = Path(args.out_dir)
    else:
        out_root = _default_out_root(run_id)

    hard_commands = _hard_gate_commands_with_options(
        args.task_files,
        bool(runtime["stability_template_hard"]),
        int(runtime["task_links_max_warnings"]),
    )
    soft_commands = _soft_gate_commands(args.task_files, bool(runtime["stability_template_hard"]))

    rc: int
    if args.mode == "hard":
        rc, _ = _run_group("hard", hard_commands, args.strict_soft, out_root / "hard", run_id, Path.cwd().resolve(), list(args.task_files))
    elif args.mode == "soft":
        rc, _ = _run_group("soft", soft_commands, args.strict_soft, out_root / "soft", run_id, Path.cwd().resolve(), list(args.task_files))
    else:
        hard_rc, hard_summary = _run_group("hard", hard_commands, args.strict_soft, out_root / "hard", run_id, Path.cwd().resolve(), list(args.task_files))
        soft_rc, soft_summary = _run_group("soft", soft_commands, args.strict_soft, out_root / "soft", run_id, Path.cwd().resolve(), list(args.task_files))

        combined = {
            "ts": dt.datetime.now(dt.timezone.utc).isoformat(),
            "action": "gate-bundle",
            "run_id": run_id,
            "out_dir": str(out_root).replace("\\", "/"),
            "mode": "all",
            "hard": hard_summary,
            "soft": soft_summary,
            "status": "ok" if hard_rc == 0 and soft_rc == 0 else "fail",
        }
        combined_path = out_root / "summary.json"
        combined_path.write_text(json.dumps(combined, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

        print(
            f"GATE_BUNDLE status={combined['status']} mode=all "
            f"hard_failed={hard_summary['failed']} soft_failed={soft_summary['failed']} "
            f"out={str(combined_path).replace('\\', '/')}"
        )
        rc = 0 if combined["status"] == "ok" else 1

    if not args.skip_prune_runs:
        prune = prune_gate_bundle_runs(
            Path("logs") / "ci",
            retention_days=args.retention_days,
            max_runs_per_day=args.max_runs_per_day,
            keep_run_id=run_id,
        )
        prune_path = out_root / "prune-summary.json"
        prune_path.parent.mkdir(parents=True, exist_ok=True)
        prune_path.write_text(json.dumps(prune, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(
            "GATE_BUNDLE_PRUNE "
            f"deleted={prune['deleted_count']} failed={prune['failed_count']} "
            f"out={str(prune_path).replace('\\', '/')}"
        )

    return rc


if __name__ == "__main__":
    sys.exit(main())
