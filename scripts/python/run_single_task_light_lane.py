#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Run workflow 5.1 single-task light lane with resilient full-step execution.

Key behavior:
- Runs all configured steps for each task by default (does not stop on step failure).
- Supports resume from summary.json.
- Writes per-step logs and rolling summary under logs/ci/<YYYY-MM-DD>/.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any

_FILL_REFS_TIMEOUT_SEC = 300
_TIMEOUT_BUFFER_SEC = 120
_RETRY_TIMEOUT_BOOST_SEC = 240
_RETRYABLE_TIMEOUT_STEPS = {"extract", "align"}
_FILL_REF_STEP_NAMES = {"fill_refs_dry", "fill_refs_write", "fill_refs_verify"}
_EARLY_GUARD_STEP_NAMES = {"preflight_extract_guard"}
_SKIP_SOFT_STEP_NAMES = {"coverage", "semantic_gate", *_FILL_REF_STEP_NAMES}
_EXTRACT_FAIL_FAMILY_AUTO_SKIP_ALL = {
    "timeout",
    "stdout:sc_llm_obligations_status_fail",
    "stderr:sc_llm_obligations_status_fail",
}
_EXTRACT_FAIL_FAMILY_AUTO_SKIP_SOFT = {
    "stdout:model_output_invalid",
    "stderr:model_output_invalid",
    "error:model_output_invalid",
}
_SNAPSHOT_PATTERNS = (
    "summary.json",
    "report.md",
    "verdict.json",
    "prompt.md",
    "output-last-message*.txt",
    "batch-*.tsv",
    "batch-*.trace.log",
    "trace-run-*.log",
)


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _today() -> str:
    return dt.date.today().strftime("%Y-%m-%d")


def _default_out_dir(root: Path) -> Path:
    return root / "logs" / "ci" / _today() / "single-task-light-lane-v2"


def _relative_to_root(root: Path, path: Path) -> str:
    try:
        return str(path.resolve().relative_to(root.resolve())).replace("\\", "/")
    except Exception:
        return str(path).replace("\\", "/")


def _parse_task_ids_csv(raw: str) -> list[int]:
    out: list[int] = []
    for token in str(raw or "").split(","):
        value = token.strip()
        if not value.isdigit():
            continue
        task_id = int(value)
        if task_id > 0:
            out.append(task_id)
    return sorted(set(out))


def _taskmaster_tasks_path(root: Path) -> Path:
    candidates = [
        root / ".taskmaster" / "tasks" / "tasks.json",
        root / "examples" / "taskmaster" / "tasks.json",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[0]


def _load_master_tasks(root: Path) -> list[dict[str, Any]]:
    path = _taskmaster_tasks_path(root)
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data.get("master"), dict) and isinstance(data["master"].get("tasks"), list):
        return [item for item in data["master"]["tasks"] if isinstance(item, dict)]
    if isinstance(data.get("tasks"), list):
        return [item for item in data["tasks"] if isinstance(item, dict)]
    return []


def _load_master_task_ids(root: Path) -> list[int]:
    task_ids: list[int] = []
    for item in _load_master_tasks(root):
        raw = str(item.get("id") or "").strip()
        if raw.isdigit():
            task_ids.append(int(raw))
    return sorted(set(task_ids))


def _load_in_progress_task_ids(root: Path) -> list[int]:
    task_ids: list[int] = []
    for item in _load_master_tasks(root):
        raw_id = str(item.get("id") or "").strip()
        if not raw_id.isdigit():
            continue
        status = str(item.get("status") or "").strip().lower().replace("-", "_")
        if status in {"in_progress", "active", "working"}:
            task_ids.append(int(raw_id))
    return sorted(set(task_ids))


def _delivery_profile_defaults(root: Path, delivery_profile: str) -> dict[str, Any]:
    config_path = root / "scripts" / "sc" / "config" / "delivery_profiles.json"
    if not config_path.exists():
        return {}
    data = json.loads(config_path.read_text(encoding="utf-8"))
    profiles = data.get("profiles") or {}
    payload = profiles.get(str(delivery_profile)) or {}
    return payload if isinstance(payload, dict) else {}


def _profile_step_llm_timeout_sec(root: Path, *, step_name: str, delivery_profile: str) -> int:
    if step_name == "preflight_extract_guard":
        return 60
    profile = _delivery_profile_defaults(root, delivery_profile)
    if step_name == "extract":
        llm_obligations = profile.get("llm_obligations") or {}
        return int(llm_obligations.get("timeout_sec", 240) or 240)
    if step_name in {"align", "coverage", "semantic_gate"}:
        llm_semantic_gate_all = profile.get("llm_semantic_gate_all") or {}
        return int(llm_semantic_gate_all.get("timeout_sec", 480) or 480)
    return _FILL_REFS_TIMEOUT_SEC


def _resolve_step_timeout_sec(
    step_name: str,
    *,
    delivery_profile: str,
    explicit_timeout_sec: int | None,
    llm_timeout_sec: int | None = None,
    root: Path | None = None,
) -> int:
    if explicit_timeout_sec is not None:
        return max(1, int(explicit_timeout_sec))
    inner_timeout = max(
        1,
        int(
            llm_timeout_sec
            if llm_timeout_sec is not None
            else _profile_step_llm_timeout_sec(root or _repo_root(), step_name=step_name, delivery_profile=delivery_profile)
        ),
    )
    return inner_timeout + _TIMEOUT_BUFFER_SEC


def _step_supports_inner_timeout(step_name: str) -> bool:
    return step_name in {
        "extract",
        "align",
        "coverage",
        "semantic_gate",
        "fill_refs_dry",
        "fill_refs_write",
        "fill_refs_verify",
    }


def _replace_or_append_timeout_arg(cmd: list[str], *, timeout_sec: int) -> list[str]:
    updated: list[str] = []
    idx = 0
    replaced = False
    while idx < len(cmd):
        part = cmd[idx]
        if part == "--timeout-sec":
            updated.extend(["--timeout-sec", str(int(timeout_sec))])
            idx += 2
            replaced = True
            continue
        updated.append(part)
        idx += 1
    if not replaced:
        updated.extend(["--timeout-sec", str(int(timeout_sec))])
    return updated


def _retry_inner_timeout_sec(
    step_name: str,
    *,
    delivery_profile: str,
    llm_timeout_sec: int | None,
    root: Path,
) -> int:
    base_inner = max(
        1,
        int(
            llm_timeout_sec
            if llm_timeout_sec is not None
            else _profile_step_llm_timeout_sec(root, step_name=step_name, delivery_profile=delivery_profile)
        ),
    )
    return max(base_inner + _RETRY_TIMEOUT_BOOST_SEC, int(base_inner * 2))


def _run_step_with_retry(
    *,
    root: Path,
    cmd: list[str],
    step_name: str,
    delivery_profile: str,
    explicit_timeout_sec: int | None,
    llm_timeout_sec: int | None,
) -> tuple[int, str, str, dict[str, Any]]:
    timeout_sec = _resolve_step_timeout_sec(
        step_name,
        delivery_profile=delivery_profile,
        explicit_timeout_sec=explicit_timeout_sec,
        llm_timeout_sec=llm_timeout_sec,
        root=root,
    )
    rc, stdout, stderr = _run_step(root, cmd, timeout_sec=timeout_sec)
    attempts: list[dict[str, Any]] = [
        {
            "attempt": 1,
            "rc": int(rc),
            "timeout_sec": int(timeout_sec),
            "cmd": list(cmd),
            "stdout": stdout,
            "stderr": stderr,
        }
    ]

    if int(rc) == 124 and step_name in _RETRYABLE_TIMEOUT_STEPS:
        retry_cmd = list(cmd)
        retry_inner_timeout = llm_timeout_sec
        if _step_supports_inner_timeout(step_name):
            retry_inner_timeout = _retry_inner_timeout_sec(
                step_name,
                delivery_profile=delivery_profile,
                llm_timeout_sec=llm_timeout_sec,
                root=root,
            )
            retry_cmd = _replace_or_append_timeout_arg(retry_cmd, timeout_sec=retry_inner_timeout)
        retry_wrapper_timeout = max(
            int(timeout_sec),
            _resolve_step_timeout_sec(
                step_name,
                delivery_profile=delivery_profile,
                explicit_timeout_sec=None,
                llm_timeout_sec=retry_inner_timeout,
                root=root,
            ),
        )
        rc, stdout, stderr = _run_step(root, retry_cmd, timeout_sec=retry_wrapper_timeout)
        attempts.append(
            {
                "attempt": 2,
                "rc": int(rc),
                "timeout_sec": int(retry_wrapper_timeout),
                "cmd": list(retry_cmd),
                "stdout": stdout,
                "stderr": stderr,
            }
        )

    metadata = {
        "retry_count": max(0, len(attempts) - 1),
        "retry_rcs": [int(item["rc"]) for item in attempts],
        "attempt_count": len(attempts),
        "attempts": attempts,
    }
    return int(rc), stdout, stderr, metadata


def _steps(*, align_apply: bool, delivery_profile: str, llm_timeout_sec: int | None) -> list[tuple[str, list[str]]]:
    align_cmd = [
        "py",
        "-3",
        "scripts/sc/llm_align_acceptance_semantics.py",
        "--task-ids",
        "{id}",
        "--strict-task-selection",
        "--delivery-profile",
        delivery_profile,
    ]
    if llm_timeout_sec is not None:
        align_cmd.extend(["--timeout-sec", str(int(llm_timeout_sec))])
    if align_apply:
        align_cmd.append("--apply")

    steps: list[tuple[str, list[str]]] = [
        (
            "preflight_extract_guard",
            [
                "py",
                "-3",
                "scripts/python/preflight_acceptance_extract_guard.py",
                "--task-id",
                "{id}",
            ],
        ),
        (
            "extract",
            [
                "py",
                "-3",
                "scripts/sc/llm_extract_task_obligations.py",
                "--task-id",
                "{id}",
                "--delivery-profile",
                delivery_profile,
                "--reuse-last-ok",
                "--explain-reuse-miss",
            ],
        ),
        ("align", align_cmd),
        (
            "coverage",
            [
                "py",
                "-3",
                "scripts/sc/llm_check_subtasks_coverage.py",
                "--task-id",
                "{id}",
                "--strict-view-selection",
                "--delivery-profile",
                delivery_profile,
            ],
        ),
        (
            "semantic_gate",
            [
                "py",
                "-3",
                "scripts/sc/llm_semantic_gate_all.py",
                "--task-ids",
                "{id}",
                "--max-needs-fix",
                "0",
                "--max-unknown",
                "3",
                "--delivery-profile",
                delivery_profile,
            ],
        ),
        (
            "fill_refs_dry",
            [
                "py",
                "-3",
                "scripts/sc/llm_fill_acceptance_refs.py",
                "--task-id",
                "{id}",
            ],
        ),
        (
            "fill_refs_write",
            [
                "py",
                "-3",
                "scripts/sc/llm_fill_acceptance_refs.py",
                "--task-id",
                "{id}",
                "--write",
            ],
        ),
        (
            "fill_refs_verify",
            [
                "py",
                "-3",
                "scripts/sc/llm_fill_acceptance_refs.py",
                "--task-id",
                "{id}",
            ],
        ),
    ]
    if llm_timeout_sec is not None:
        llm_timeout_parts = ["--timeout-sec", str(int(llm_timeout_sec))]
        step_names = {"extract", "coverage", "semantic_gate", "fill_refs_dry", "fill_refs_write", "fill_refs_verify"}
        steps = [
            (name, command + llm_timeout_parts if name in step_names else command)
            for name, command in steps
        ]
    return steps


def _resolve_fill_refs_mode(mode: str, *, selected_count: int) -> str:
    if str(mode) == "auto":
        return "none" if int(selected_count) > 1 else "write-verify"
    return str(mode)


def _apply_fill_refs_mode(
    steps: list[tuple[str, list[str]]],
    *,
    fill_refs_mode: str,
) -> list[tuple[str, list[str]]]:
    if fill_refs_mode == "write-verify":
        return list(steps)
    if fill_refs_mode == "dry":
        return [(name, cmd) for name, cmd in steps if name not in {"fill_refs_write", "fill_refs_verify"}]
    if fill_refs_mode == "none":
        return [(name, cmd) for name, cmd in steps if name not in _FILL_REF_STEP_NAMES]
    return list(steps)


def _resolve_downstream_on_extract_fail(policy: str, *, selected_count: int) -> str:
    if str(policy) == "auto":
        return "skip-soft" if int(selected_count) > 1 else "continue"
    return str(policy)


def _resolve_downstream_on_extract_family_fail(policy: str, *, extract_fail_family: str) -> str:
    family = str(extract_fail_family or "").strip().lower()
    value = str(policy or "").strip().lower()
    if not family or value in {"", "off", "continue"}:
        return ""
    if value in {"skip-soft", "skip-all"}:
        return value
    if value != "auto":
        return ""
    if family in _EXTRACT_FAIL_FAMILY_AUTO_SKIP_ALL:
        return "skip-all"
    if family in _EXTRACT_FAIL_FAMILY_AUTO_SKIP_SOFT:
        return "skip-soft"
    return ""


def _resolve_batch_lane(mode: str, *, selected_count: int) -> str:
    if str(mode) == "auto":
        return "extract-first" if int(selected_count) > 1 else "standard"
    return str(mode)


def _build_wrapper_command(
    *,
    selected: list[int],
    delivery_profile: str,
    align_apply: bool,
    fill_refs_after_extract_fail: str,
    fill_refs_mode: str,
    downstream_on_extract_fail: str,
    downstream_on_extract_family_fail: str,
    batch_lane: str,
    wrapper_timeout_sec: int | None,
    llm_timeout_sec: int | None,
    resume_failed_task_from: str | None = None,
) -> str:
    cmd: list[str] = [
        "py",
        "-3",
        "scripts/python/run_single_task_light_lane.py",
        "--task-ids",
        ",".join(str(task_id) for task_id in selected),
        "--delivery-profile",
        str(delivery_profile),
        "--fill-refs-after-extract-fail",
        str(fill_refs_after_extract_fail),
        "--fill-refs-mode",
        str(fill_refs_mode),
        "--downstream-on-extract-fail",
        str(downstream_on_extract_fail),
        "--downstream-on-extract-family-fail",
        str(downstream_on_extract_family_fail),
        "--batch-lane",
        str(batch_lane),
    ]
    if not bool(align_apply):
        cmd.append("--no-align-apply")
    if wrapper_timeout_sec is not None:
        cmd.extend(["--timeout-sec", str(int(wrapper_timeout_sec))])
    if llm_timeout_sec is not None:
        cmd.extend(["--llm-timeout-sec", str(int(llm_timeout_sec))])
    if str(resume_failed_task_from or "").strip():
        cmd.extend(["--resume-failed-task-from", str(resume_failed_task_from)])
    return " ".join(cmd)


def _boosted_llm_timeout_sec(
    *,
    root: Path,
    delivery_profile: str,
    llm_timeout_sec: int | None,
) -> int:
    base_timeout = int(llm_timeout_sec) if llm_timeout_sec is not None else _profile_step_llm_timeout_sec(
        root,
        step_name="extract",
        delivery_profile=delivery_profile,
    )
    return max(1, int(base_timeout)) + _RETRY_TIMEOUT_BOOST_SEC


def _derive_route_contract(
    summary: dict[str, Any],
    *,
    selected: list[int],
    delivery_profile: str,
    align_apply: bool,
    fill_refs_after_extract_fail: str,
    fill_refs_mode: str,
    downstream_on_extract_fail: str,
    downstream_on_extract_family_fail: str,
    batch_lane: str,
    wrapper_timeout_sec: int | None,
    llm_timeout_sec: int | None,
    root: Path,
) -> dict[str, Any]:
    base_command = _build_wrapper_command(
        selected=selected,
        delivery_profile=delivery_profile,
        align_apply=align_apply,
        fill_refs_after_extract_fail=fill_refs_after_extract_fail,
        fill_refs_mode=fill_refs_mode,
        downstream_on_extract_fail=downstream_on_extract_fail,
        downstream_on_extract_family_fail=downstream_on_extract_family_fail,
        batch_lane=batch_lane,
        wrapper_timeout_sec=wrapper_timeout_sec,
        llm_timeout_sec=llm_timeout_sec,
    )
    failure_category_counts = summary.get("failure_category_counts") if isinstance(summary.get("failure_category_counts"), dict) else {}
    categories = {str(key).strip() for key, value in failure_category_counts.items() if str(key).strip() and int(value or 0) > 0}
    processed_tasks = int(summary.get("processed_tasks") or 0)
    failed_tasks = int(summary.get("failed_tasks") or 0)

    preferred_lane = "run-5.1"
    recommended_action = "continue"
    recommended_command = base_command
    forbidden_commands: list[str] = []
    latest_reason = "lane_clean"
    blocked_by = ""
    artifact_integrity = ""
    residual_recording = "no"

    if processed_tasks <= 0:
        preferred_lane = "inspect-first"
        recommended_action = "inspect"
        recommended_command = ""
        latest_reason = "no_processed_tasks"
        blocked_by = "n/a"
    elif failed_tasks <= 0:
        preferred_lane = "run-5.1"
        recommended_action = "continue"
        latest_reason = "lane_clean"
    elif "timeout" in categories:
        preferred_lane = "timeout-backoff-then-rerun"
        recommended_action = "rerun"
        recommended_command = _build_wrapper_command(
            selected=selected,
            delivery_profile=delivery_profile,
            align_apply=align_apply,
            fill_refs_after_extract_fail=fill_refs_after_extract_fail,
            fill_refs_mode=fill_refs_mode,
            downstream_on_extract_fail=downstream_on_extract_fail,
            downstream_on_extract_family_fail=downstream_on_extract_family_fail,
            batch_lane=batch_lane,
            wrapper_timeout_sec=wrapper_timeout_sec,
            llm_timeout_sec=_boosted_llm_timeout_sec(root=root, delivery_profile=delivery_profile, llm_timeout_sec=llm_timeout_sec),
            resume_failed_task_from="first-failed-step",
        )
        forbidden_commands = [base_command]
        latest_reason = "extract_timeout"
    elif categories and categories <= {"model-fail"}:
        preferred_lane = "retry-extract-only"
        recommended_action = "rerun"
        recommended_command = _build_wrapper_command(
            selected=selected,
            delivery_profile=delivery_profile,
            align_apply=align_apply,
            fill_refs_after_extract_fail=fill_refs_after_extract_fail,
            fill_refs_mode=fill_refs_mode,
            downstream_on_extract_fail=downstream_on_extract_fail,
            downstream_on_extract_family_fail=downstream_on_extract_family_fail,
            batch_lane=batch_lane,
            wrapper_timeout_sec=wrapper_timeout_sec,
            llm_timeout_sec=llm_timeout_sec,
            resume_failed_task_from="first-failed-step",
        )
        latest_reason = "extract_model_fail"
    elif categories and categories <= {"coverage-gap", "semantic-needs-fix"}:
        preferred_lane = "retry-soft-steps-only"
        recommended_action = "rerun"
        recommended_command = _build_wrapper_command(
            selected=selected,
            delivery_profile=delivery_profile,
            align_apply=align_apply,
            fill_refs_after_extract_fail=fill_refs_after_extract_fail,
            fill_refs_mode=fill_refs_mode,
            downstream_on_extract_fail=downstream_on_extract_fail,
            downstream_on_extract_family_fail=downstream_on_extract_family_fail,
            batch_lane=batch_lane,
            wrapper_timeout_sec=wrapper_timeout_sec,
            llm_timeout_sec=llm_timeout_sec,
            resume_failed_task_from="first-failed-step",
        )
        latest_reason = "soft_steps_failed"
    elif categories and categories <= {"preflight-gap"}:
        preferred_lane = "inspect-first"
        recommended_action = "inspect"
        recommended_command = ""
        latest_reason = "preflight_gap"
        blocked_by = "deterministic_failure"
    elif failed_tasks > 0:
        preferred_lane = "inspect-first"
        recommended_action = "inspect"
        recommended_command = ""
        latest_reason = "mixed_failure_families"
        blocked_by = "recent_failure_summary"

    return {
        "preferred_lane": preferred_lane,
        "recommended_action": recommended_action,
        "recommended_command": recommended_command,
        "forbidden_commands": forbidden_commands,
        "latest_reason": latest_reason,
        "blocked_by": blocked_by,
        "artifact_integrity": artifact_integrity,
        "residual_recording": residual_recording,
    }


def _derive_route_explanation(route_contract: dict[str, Any]) -> str:
    reason = str(route_contract.get("latest_reason") or "").strip().lower()
    if reason == "lane_clean":
        return "Current summary is clean; continue with the normal 5.1 lane."
    if reason == "extract_timeout":
        return "Extract timed out; rerun failed tasks from the first failed step with a larger LLM timeout."
    if reason == "extract_model_fail":
        return "Only model-family extract failures were observed; rerun failed tasks from the first failed step."
    if reason == "soft_steps_failed":
        return "Only coverage or semantic soft steps failed; rerun failed tasks from the first failed step."
    if reason == "preflight_gap":
        return "Deterministic acceptance preflight failed; inspect task views and refs before rerunning 5.1."
    if reason == "mixed_failure_families":
        return "Mixed failure families were observed; inspect the latest summary before spending more LLM cost."
    if reason == "no_processed_tasks":
        return "No task has been processed yet."
    return "Inspect the latest summary before deciding whether to rerun 5.1."


def _refresh_route_contract(
    summary: dict[str, Any],
    *,
    root: Path,
    selected: list[int],
    delivery_profile: str,
    align_apply: bool,
    fill_refs_after_extract_fail: str,
    fill_refs_mode: str,
    downstream_on_extract_fail: str,
    downstream_on_extract_family_fail: str,
    batch_lane: str,
    wrapper_timeout_sec: int | None,
    llm_timeout_sec: int | None,
    planning_mode: bool = False,
) -> dict[str, Any]:
    if planning_mode:
        route_contract = {
            "preferred_lane": "run-5.1",
            "recommended_action": "continue",
            "recommended_command": _build_wrapper_command(
                selected=selected,
                delivery_profile=delivery_profile,
                align_apply=align_apply,
                fill_refs_after_extract_fail=fill_refs_after_extract_fail,
                fill_refs_mode=fill_refs_mode,
                downstream_on_extract_fail=downstream_on_extract_fail,
                downstream_on_extract_family_fail=downstream_on_extract_family_fail,
                batch_lane=batch_lane,
                wrapper_timeout_sec=wrapper_timeout_sec,
                llm_timeout_sec=llm_timeout_sec,
            ),
            "forbidden_commands": [],
            "latest_reason": "self_check",
            "blocked_by": "n/a",
            "artifact_integrity": "",
            "residual_recording": "no",
        }
    else:
        route_contract = _derive_route_contract(
            summary,
            selected=selected,
            delivery_profile=delivery_profile,
            align_apply=align_apply,
            fill_refs_after_extract_fail=fill_refs_after_extract_fail,
            fill_refs_mode=fill_refs_mode,
            downstream_on_extract_fail=downstream_on_extract_fail,
            downstream_on_extract_family_fail=downstream_on_extract_family_fail,
            batch_lane=batch_lane,
            wrapper_timeout_sec=wrapper_timeout_sec,
            llm_timeout_sec=llm_timeout_sec,
            root=root,
        )
    summary["preferred_lane"] = str(route_contract.get("preferred_lane") or "").strip()
    summary["recommended_action"] = str(route_contract.get("recommended_action") or "").strip()
    summary["recommended_command"] = str(route_contract.get("recommended_command") or "").strip()
    summary["forbidden_commands"] = [
        str(item).strip()
        for item in list(route_contract.get("forbidden_commands") or [])
        if str(item).strip()
    ]
    summary["latest_reason"] = str(route_contract.get("latest_reason") or "").strip()
    summary["blocked_by"] = str(route_contract.get("blocked_by") or "").strip()
    summary["artifact_integrity"] = str(route_contract.get("artifact_integrity") or "").strip()
    summary["residual_recording"] = str(route_contract.get("residual_recording") or "").strip() or "no"
    summary["recommended_action_why"] = _derive_route_explanation(route_contract)
    return route_contract


def _skip_reason_for_step_after_extract_fail(
    step_name: str,
    *,
    fill_refs_after_extract_fail: str,
    downstream_on_extract_fail: str,
    downstream_on_extract_family_fail: str,
    extract_fail_family: str,
) -> str:
    family_policy = _resolve_downstream_on_extract_family_fail(
        downstream_on_extract_family_fail,
        extract_fail_family=extract_fail_family,
    )
    if family_policy == "skip-all" and step_name != "extract":
        return "extract_failed_family_policy_skip_all"
    if family_policy == "skip-soft" and step_name in _SKIP_SOFT_STEP_NAMES:
        return "extract_failed_family_policy_skip_soft"
    if downstream_on_extract_fail == "skip-all" and step_name != "extract":
        return "extract_failed_downstream_policy_skip_all"
    if downstream_on_extract_fail == "skip-soft" and step_name in _SKIP_SOFT_STEP_NAMES:
        return "extract_failed_downstream_policy_skip_soft"
    if step_name in _FILL_REF_STEP_NAMES and str(fill_refs_after_extract_fail) == "skip":
        return "extract_failed_fill_refs_policy"
    return ""


def _run_step(root: Path, cmd: list[str], *, timeout_sec: int) -> tuple[int, str, str]:
    try:
        proc = subprocess.run(
            cmd,
            cwd=str(root),
            text=True,
            encoding="utf-8",
            errors="replace",
            capture_output=True,
            timeout=max(1, int(timeout_sec)),
        )
        return int(proc.returncode), proc.stdout or "", proc.stderr or ""
    except subprocess.TimeoutExpired as exc:
        stdout = str(exc.stdout or "") if exc.stdout is not None else ""
        stderr = str(exc.stderr or "") if exc.stderr is not None else ""
        return 124, stdout, stderr


def _load_summary(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    return payload if isinstance(payload, dict) else None


def _index_results(results: list[dict[str, Any]]) -> dict[int, dict[str, Any]]:
    indexed: dict[int, dict[str, Any]] = {}
    for row in results:
        task_raw = str(row.get("task_id") or "").strip()
        if task_raw.isdigit():
            indexed[int(task_raw)] = row
    return indexed


def _rebuild_counts(summary: dict[str, Any]) -> None:
    results = [row for row in summary.get("results", []) if isinstance(row, dict)]
    failed_step_counts: dict[str, int] = {}
    timeout_step_counts: dict[str, int] = {}
    failure_category_counts: dict[str, int] = {}
    failure_category_task_ids: dict[str, list[int]] = {}
    failure_category_by_task: dict[str, str] = {}
    extract_fail_bucket_counts: dict[str, int] = {}
    extract_fail_bucket_task_ids: dict[str, list[int]] = {}
    extract_fail_bucket_by_task: dict[str, str] = {}
    extract_fail_signature_counts: dict[str, int] = {}
    extract_fail_signature_task_ids: dict[str, list[int]] = {}
    extract_fail_signature_by_task: dict[str, str] = {}
    extract_fail_family_counts: dict[str, int] = {}
    extract_fail_family_task_ids: dict[str, list[int]] = {}
    extract_fail_family_by_task: dict[str, str] = {}
    prompt_trimmed_task_ids: list[int] = []
    semantic_gate_budget_hits: list[dict[str, Any]] = []
    skipped_step_counts: dict[str, int] = {}
    skipped_step_reason_counts: dict[str, int] = {}
    step_duration_totals: dict[str, float] = {}
    step_duration_counts: dict[str, int] = {}
    slowest_tasks: list[dict[str, Any]] = []
    passed_tasks = 0
    failed_tasks = 0
    for row in results:
        task_raw = str(row.get("task_id") or "").strip()
        task_duration_total = 0.0
        for step in row.get("steps", []) or []:
            if not isinstance(step, dict):
                continue
            step_name = str(step.get("step") or "").strip()
            try:
                duration_sec = float(step.get("duration_sec")) if step.get("duration_sec") is not None else None
            except Exception:
                duration_sec = None
            if step_name and duration_sec is not None and duration_sec >= 0:
                step_duration_totals[step_name] = step_duration_totals.get(step_name, 0.0) + duration_sec
                step_duration_counts[step_name] = step_duration_counts.get(step_name, 0) + 1
                task_duration_total += duration_sec
            if bool(step.get("skipped")):
                key = step_name
                reason = str(step.get("skip_reason") or "").strip()
                if key:
                    skipped_step_counts[key] = skipped_step_counts.get(key, 0) + 1
                if reason:
                    skipped_step_reason_counts[reason] = skipped_step_reason_counts.get(reason, 0) + 1
            if int(step.get("rc") or 0) == 124:
                key = step_name
                if key:
                    timeout_step_counts[key] = timeout_step_counts.get(key, 0) + 1
            if step_name == "semantic_gate":
                inner_summary = step.get("inner_summary")
                if isinstance(inner_summary, dict) and bool(inner_summary.get("prompt_trimmed")) and task_raw.isdigit():
                    task_id = int(task_raw)
                    if task_id not in prompt_trimmed_task_ids:
                        prompt_trimmed_task_ids.append(task_id)
                        semantic_gate_budget_hits.append(
                            {
                                "task_id": task_id,
                                "prompt_trimmed": True,
                                "task_brief_budget": inner_summary.get("task_brief_budget"),
                                "prompt_chars": inner_summary.get("prompt_chars"),
                            }
                        )
            if step_name == "extract" and int(step.get("rc") or 0) != 0 and task_raw.isdigit():
                bucket = _classify_extract_fail_bucket(step)
                if bucket:
                    extract_fail_bucket_counts[bucket] = extract_fail_bucket_counts.get(bucket, 0) + 1
                    extract_fail_bucket_task_ids.setdefault(bucket, []).append(int(task_raw))
                    extract_fail_bucket_by_task[task_raw] = bucket
                signature = _extract_fail_signature(step)
                if signature:
                    extract_fail_signature_counts[signature] = extract_fail_signature_counts.get(signature, 0) + 1
                    extract_fail_signature_task_ids.setdefault(signature, []).append(int(task_raw))
                    extract_fail_signature_by_task[task_raw] = signature
                    family = _extract_fail_signature_family(signature)
                    if family:
                        extract_fail_family_counts[family] = extract_fail_family_counts.get(family, 0) + 1
                        extract_fail_family_task_ids.setdefault(family, []).append(int(task_raw))
                        extract_fail_family_by_task[task_raw] = family
        if bool(row.get("ok")):
            passed_tasks += 1
        else:
            failed_tasks += 1
            category = _classify_failed_task(row)
            if category and task_raw.isdigit():
                failure_category_counts[category] = failure_category_counts.get(category, 0) + 1
                failure_category_task_ids.setdefault(category, []).append(int(task_raw))
                failure_category_by_task[task_raw] = category
            for step in row.get("failed_steps", []) or []:
                key = str(step).strip()
                if not key:
                    continue
                failed_step_counts[key] = failed_step_counts.get(key, 0) + 1
        if task_raw.isdigit() and task_duration_total > 0:
            slowest_tasks.append(
                {
                    "task_id": int(task_raw),
                    "duration_sec": round(task_duration_total, 3),
                    "first_failed_step": str(row.get("first_failed_step") or "").strip(),
                    "ok": bool(row.get("ok")),
                }
            )
    summary["processed_tasks"] = len(results)
    summary["passed_tasks"] = passed_tasks
    summary["failed_tasks"] = failed_tasks
    summary["failed_step_counts"] = failed_step_counts
    summary["timeout_step_counts"] = timeout_step_counts
    summary["failure_category_counts"] = failure_category_counts
    summary["failure_category_task_ids"] = failure_category_task_ids
    summary["failure_category_by_task"] = failure_category_by_task
    summary["extract_fail_bucket_counts"] = extract_fail_bucket_counts
    summary["extract_fail_bucket_task_ids"] = extract_fail_bucket_task_ids
    summary["extract_fail_bucket_by_task"] = extract_fail_bucket_by_task
    summary["extract_fail_signature_counts"] = extract_fail_signature_counts
    summary["extract_fail_signature_task_ids"] = extract_fail_signature_task_ids
    summary["extract_fail_signature_by_task"] = extract_fail_signature_by_task
    summary["extract_fail_family_counts"] = extract_fail_family_counts
    summary["extract_fail_family_task_ids"] = extract_fail_family_task_ids
    summary["extract_fail_family_by_task"] = extract_fail_family_by_task
    summary["extract_fail_top_signatures"] = [
        {
            "signature": signature,
            "count": int(count),
            "task_ids": list(extract_fail_signature_task_ids.get(signature) or []),
        }
        for signature, count in sorted(
            extract_fail_signature_counts.items(),
            key=lambda item: (-int(item[1]), str(item[0])),
        )[:10]
    ]
    summary["extract_fail_top_families"] = [
        {
            "family": family,
            "count": int(count),
            "task_ids": list(extract_fail_family_task_ids.get(family) or []),
        }
        for family, count in sorted(
            extract_fail_family_counts.items(),
            key=lambda item: (-int(item[1]), str(item[0])),
        )[:10]
    ]
    summary["prompt_trimmed_task_ids"] = prompt_trimmed_task_ids
    summary["prompt_trimmed_count"] = len(prompt_trimmed_task_ids)
    summary["semantic_gate_budget_hits"] = semantic_gate_budget_hits
    summary["skipped_step_counts"] = skipped_step_counts
    summary["skipped_step_reason_counts"] = skipped_step_reason_counts
    summary["step_duration_totals"] = {
        key: round(value, 3) for key, value in sorted(step_duration_totals.items(), key=lambda item: item[0])
    }
    summary["step_duration_avg"] = {
        key: round(step_duration_totals[key] / max(1, int(step_duration_counts.get(key) or 1)), 3)
        for key in sorted(step_duration_totals)
    }
    summary["step_duration_task_counts"] = {
        key: int(step_duration_counts.get(key) or 0) for key in sorted(step_duration_counts)
    }
    summary["slowest_tasks"] = sorted(
        slowest_tasks,
        key=lambda item: (-float(item.get("duration_sec") or 0.0), int(item.get("task_id") or 0)),
    )[:10]
    next_action = _derive_summary_next_action(summary)
    summary["recommended_next_action"] = str(next_action.get("action") or "")
    summary["recommended_next_action_why"] = str(next_action.get("why") or "")


def _derive_summary_next_action(summary: dict[str, Any]) -> dict[str, str]:
    if int(summary.get("failed_tasks") or 0) <= 0:
        return {
            "action": "continue-next-selected-slice",
            "why": "Current 5.1 slice is clean; continue to the next selected task range or lane.",
        }
    extract_buckets = summary.get("extract_fail_bucket_counts") if isinstance(summary.get("extract_fail_bucket_counts"), dict) else {}
    failure_categories = summary.get("failure_category_counts") if isinstance(summary.get("failure_category_counts"), dict) else {}
    timeout_steps = summary.get("timeout_step_counts") if isinstance(summary.get("timeout_step_counts"), dict) else {}
    failed_step_counts = summary.get("failed_step_counts") if isinstance(summary.get("failed_step_counts"), dict) else {}
    top_family = ""
    top_families = summary.get("extract_fail_top_families")
    if isinstance(top_families, list) and top_families:
        first = top_families[0]
        if isinstance(first, dict):
            top_family = str(first.get("family") or "").strip()
    if int(extract_buckets.get("hard_uncovered") or 0) > 0:
        return {
            "action": "fix-acceptance-then-rerun-extract",
            "why": "Extract reported hard uncovered obligations; complete required acceptance/refs before rerunning downstream steps.",
        }
    if int(timeout_steps.get("extract") or 0) > 0:
        return {
            "action": "retry-extract-only-with-timeout-backoff",
            "why": "Extract timed out; retry extract first with a larger timeout or smaller task slice before spending more downstream work.",
        }
    if int(failure_categories.get("coverage-gap") or 0) > 0:
        return {
            "action": "fix-coverage-then-rerun-coverage",
            "why": "Coverage gaps were detected; add or align task coverage before rerunning semantic checks.",
        }
    if int(failure_categories.get("semantic-needs-fix") or 0) > 0:
        return {
            "action": "fix-semantic-findings-then-rerun-soft-steps",
            "why": "Semantic gate returned needs-fix; repair the flagged task text or refs, then rerun from the first soft failure.",
        }
    if top_family:
        return {
            "action": "inspect-dominant-extract-family",
            "why": f"Most failures cluster under extract family '{top_family}'; inspect that family first and rerun only the affected slice.",
        }
    if int(failed_step_counts.get("align") or 0) > 0:
        return {
            "action": "resume-from-align",
            "why": "Align is the first failing deterministic step; rerun from align instead of replaying the whole slice.",
        }
    return {
        "action": "inspect-failed-tasks",
        "why": "Failures are mixed; inspect the failed task rows before choosing a narrower rerun strategy.",
    }


def _select_task_ids(root: Path, args: argparse.Namespace) -> list[int]:
    all_ids = _load_master_task_ids(root)
    if not all_ids:
        return []
    if str(args.task_ids).strip():
        selected = [task_id for task_id in _parse_task_ids_csv(args.task_ids) if task_id in set(all_ids)]
    else:
        in_progress = _load_in_progress_task_ids(root)
        if in_progress:
            selected = in_progress
        else:
            start = max(1, int(args.task_id_start))
            end = int(args.task_id_end) if int(args.task_id_end) > 0 else max(all_ids)
            selected = [task_id for task_id in all_ids if start <= task_id <= end]
    if int(args.max_tasks) > 0:
        selected = selected[: int(args.max_tasks)]
    return selected


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _extract_inner_out_dir(stdout: str, stderr: str) -> Path | None:
    lines: list[str] = []
    for blob in (stdout, stderr):
        lines.extend(str(blob or "").splitlines())
    for line in reversed(lines):
        if "out=" not in line:
            continue
        raw = line.split("out=", 1)[1].strip().strip("\"'")
        if raw:
            return Path(raw)
    return None


def _copy_file_set(source_dir: Path, artifact_dir: Path) -> list[str]:
    copied: list[str] = []
    for pattern in _SNAPSHOT_PATTERNS:
        for path in sorted(source_dir.glob(pattern)):
            if not path.is_file():
                continue
            target = artifact_dir / path.name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, target)
            copied.append(str(target.name))
    return copied


def _summarize_inner_summary(step_name: str, payload: dict[str, Any]) -> dict[str, Any]:
    summary: dict[str, Any] = {}
    for key in ("cmd", "status", "error", "schema_version"):
        value = payload.get(key)
        if value is not None:
            summary[key] = value
    if step_name == "semantic_gate":
        batch_meta = payload.get("batch_meta")
        if isinstance(batch_meta, list) and batch_meta:
            first = batch_meta[0]
            if isinstance(first, dict):
                for key in ("prompt_chars", "prompt_trimmed", "task_brief_budget", "task_count"):
                    value = first.get(key)
                    if value is not None:
                        summary[key] = value
    elif step_name == "coverage":
        summary["uncovered_subtask_ids"] = list(payload.get("uncovered_subtask_ids") or [])
        votes = payload.get("consensus_votes")
        if isinstance(votes, dict):
            summary["consensus_votes"] = votes
    elif step_name == "extract":
        for key in ("hard_uncovered_count", "advisory_uncovered_count", "excerpt_prefix_stripped_matches", "schema_error_count"):
            value = payload.get(key)
            if value is not None:
                summary[key] = value
        auto_escalate = payload.get("auto_escalate")
        if isinstance(auto_escalate, dict):
            summary["auto_escalate"] = {
                "triggered": bool(auto_escalate.get("triggered")),
                "reasons": list(auto_escalate.get("reasons") or []),
            }
    elif step_name == "preflight_extract_guard":
        for key in ("issue_count", "issue_ids", "acceptance_item_counts", "views_present"):
            value = payload.get(key)
            if value is not None:
                summary[key] = value
    elif step_name.startswith("fill_refs"):
        for key in ("task_count", "changed_tasks", "written_tasks", "skipped_tasks"):
            value = payload.get(key)
            if value is not None:
                summary[key] = value
    return summary


def _snapshot_inner_artifacts(
    *,
    root: Path,
    wrapper_out_dir: Path,
    task_id: int,
    step_name: str,
    stdout: str,
    stderr: str,
) -> dict[str, Any]:
    inner_out_dir = _extract_inner_out_dir(stdout, stderr)
    if inner_out_dir is None:
        return {}
    source_dir = inner_out_dir if inner_out_dir.is_absolute() else (root / inner_out_dir)
    if not source_dir.exists():
        return {"inner_out_dir": str(inner_out_dir).replace("\\", "/"), "inner_artifacts_missing": True}

    artifact_dir = wrapper_out_dir / f"t{task_id:04d}--{step_name}.artifacts"
    artifact_dir.mkdir(parents=True, exist_ok=True)
    copied = _copy_file_set(source_dir, artifact_dir)

    task_subdir_names = [f"task-{task_id}", f"task-{task_id:04d}"]
    copied_task_dirs: list[str] = []
    for name in task_subdir_names:
        source_task_dir = source_dir / name
        if not source_task_dir.is_dir():
            continue
        target_task_dir = artifact_dir / name
        shutil.copytree(source_task_dir, target_task_dir, dirs_exist_ok=True)
        copied_task_dirs.append(name)

    metadata: dict[str, Any] = {
        "inner_out_dir": str(source_dir).replace("\\", "/"),
        "artifact_dir": _relative_to_root(root, artifact_dir),
        "artifacts_copied": copied,
    }
    if copied_task_dirs:
        metadata["task_dirs_copied"] = copied_task_dirs
    summary_path = source_dir / "summary.json"
    if summary_path.is_file():
        try:
            payload = json.loads(summary_path.read_text(encoding="utf-8"))
        except Exception:
            payload = None
        if isinstance(payload, dict):
            metadata["inner_summary"] = _summarize_inner_summary(step_name, payload)
    return metadata


def _classify_failed_task(row: dict[str, Any]) -> str | None:
    steps = row.get("steps")
    if not isinstance(steps, list):
        return None

    for step in steps:
        if isinstance(step, dict) and int(step.get("rc") or 0) == 124:
            return "timeout"

    for step in steps:
        if not isinstance(step, dict):
            continue
        if str(step.get("step") or "").strip() == "preflight_extract_guard" and int(step.get("rc") or 0) != 0:
            return "preflight-gap"

    for step in steps:
        if not isinstance(step, dict):
            continue
        if str(step.get("step") or "").strip() != "coverage" or int(step.get("rc") or 0) == 0:
            continue
        inner_summary = step.get("inner_summary")
        if isinstance(inner_summary, dict):
            uncovered = inner_summary.get("uncovered_subtask_ids") or []
            if isinstance(uncovered, list):
                return "coverage-gap"
        return "coverage-gap"

    for step in steps:
        if not isinstance(step, dict):
            continue
        if str(step.get("step") or "").strip() == "semantic_gate" and int(step.get("rc") or 0) != 0:
            return "semantic-needs-fix"

    for step in steps:
        if not isinstance(step, dict):
            continue
        if int(step.get("rc") or 0) != 0:
            return "model-fail"
    return None


def _classify_extract_fail_bucket(step: dict[str, Any]) -> str | None:
    rc = int(step.get("rc") or 0)
    if rc == 0:
        return None
    if rc == 124:
        return "timeout"
    inner_summary = step.get("inner_summary")
    if isinstance(inner_summary, dict):
        if int(inner_summary.get("schema_error_count") or 0) > 0:
            return "schema_error"
        schema_errors = inner_summary.get("schema_errors")
        if isinstance(schema_errors, list) and schema_errors:
            return "schema_error"
        if int(inner_summary.get("hard_uncovered_count") or 0) > 0:
            return "hard_uncovered"
    return "model_fail"


def _normalize_extract_signature_text(value: Any) -> str:
    text = str(value or "").strip().lower()
    if not text:
        return ""
    text = text.replace("\\", "/")
    text = re.sub(r"[a-z]:/[^\s'\"]+", "<path>", text)
    text = re.sub(r"https?://\S+", "<url>", text)
    text = re.sub(r"\b\d+\b", "<num>", text)
    text = re.sub(r"\s+", " ", text).strip(" .,:;|/-")
    if len(text) > 96:
        text = text[:96].rstrip()
    return text


def _extract_fail_signature_family(signature: str) -> str:
    value = str(signature or "").strip().lower()
    if not value:
        return ""
    if value in {"timeout", "schema_error", "hard_uncovered"}:
        return value
    if value.startswith("error:"):
        return value
    if value.startswith("auto_escalate:"):
        return "auto_escalate"
    if value == "auto_escalate":
        return value
    if value.startswith("rc:"):
        return value
    if value.startswith("stdout:") or value.startswith("stderr:"):
        channel, raw = value.split(":", 1)
        text = str(raw or "").strip()
        text = re.sub(r"\bout=<path>\b", "", text).strip()
        text = re.sub(r"\btask[-_/]<num>\b", "task", text)
        text = re.sub(r"\s+", " ", text).strip(" .,:;|/-")
        if text.startswith("sc_llm_obligations status=fail"):
            return f"{channel}:sc_llm_obligations_status_fail"
        if text.startswith("sc_llm_obligations status=ok"):
            return f"{channel}:sc_llm_obligations_status_ok"
        if "model output invalid" in text:
            return f"{channel}:model_output_invalid"
        if "schema error" in text:
            return f"{channel}:schema_error"
        if "hard uncovered" in text:
            return f"{channel}:hard_uncovered"
        head = text[:48].strip() if text else "unknown"
        return f"{channel}:{head}"
    return value


def _extract_fail_signature(step: dict[str, Any]) -> str | None:
    rc = int(step.get("rc") or 0)
    if rc == 0:
        return None
    if rc == 124:
        return "timeout"
    inner_summary = step.get("inner_summary")
    if isinstance(inner_summary, dict):
        error_text = _normalize_extract_signature_text(inner_summary.get("error"))
        if error_text:
            return f"error:{error_text}"
        if int(inner_summary.get("schema_error_count") or 0) > 0:
            return "schema_error"
        schema_errors = inner_summary.get("schema_errors")
        if isinstance(schema_errors, list) and schema_errors:
            return "schema_error"
        if int(inner_summary.get("hard_uncovered_count") or 0) > 0:
            return "hard_uncovered"
        auto_escalate = inner_summary.get("auto_escalate")
        if isinstance(auto_escalate, dict) and bool(auto_escalate.get("triggered")):
            reasons = [
                item
                for item in (_normalize_extract_signature_text(part) for part in list(auto_escalate.get("reasons") or []))
                if item
            ]
            if reasons:
                return f"auto_escalate:{'+'.join(sorted(set(reasons))[:2])}"
            return "auto_escalate"
    stderr_tail = _normalize_extract_signature_text(step.get("stderr_tail"))
    if stderr_tail:
        return f"stderr:{stderr_tail}"
    stdout_tail = _normalize_extract_signature_text(step.get("stdout_tail"))
    if stdout_tail:
        return f"stdout:{stdout_tail}"
    return f"rc:{rc}"


def _build_resume_scope(
    *,
    selected: list[int],
    delivery_profile: str,
    align_apply: bool,
    fill_refs_after_extract_fail: str,
    downstream_on_extract_fail: str,
    downstream_on_extract_family_fail: str,
    fill_refs_mode: str,
    batch_lane: str,
) -> dict[str, Any]:
    step_names = [
        name
        for name, _ in _apply_fill_refs_mode(
            _steps(align_apply=align_apply, delivery_profile=delivery_profile, llm_timeout_sec=None),
            fill_refs_mode=fill_refs_mode,
        )
    ]
    return {
        "task_ids": [int(task_id) for task_id in selected],
        "delivery_profile": str(delivery_profile),
        "align_apply": bool(align_apply),
        "fill_refs_after_extract_fail": str(fill_refs_after_extract_fail),
        "downstream_on_extract_fail": str(downstream_on_extract_fail),
        "downstream_on_extract_family_fail": str(downstream_on_extract_family_fail),
        "fill_refs_mode": str(fill_refs_mode),
        "batch_lane": str(batch_lane),
        "step_names": step_names,
    }


def _summary_scope_matches(summary: dict[str, Any], scope: dict[str, Any]) -> bool:
    current = summary.get("resume_scope")
    return bool(isinstance(current, dict) and current == scope)


def _row_is_complete(row: dict[str, Any] | None, *, step_names: list[str]) -> bool:
    if not isinstance(row, dict) or not bool(row.get("ok")):
        return False
    steps = row.get("steps")
    if not isinstance(steps, list):
        return False
    actual_names = [str(item.get("step")) for item in steps if isinstance(item, dict)]
    return actual_names == list(step_names)


def _prepare_failed_row_resume(
    row: dict[str, Any] | None,
    *,
    step_names: list[str],
    resume_failed_task_from: str,
) -> tuple[dict[str, dict[str, Any]], int, str, list[str]]:
    if resume_failed_task_from != "first-failed-step" or not isinstance(row, dict) or bool(row.get("ok")):
        return {}, 0, "", []

    first_failed_step = str(row.get("first_failed_step") or "").strip()
    if not first_failed_step:
        for item in row.get("failed_steps", []) or []:
            first_failed_step = str(item).strip()
            if first_failed_step:
                break
    if not first_failed_step or first_failed_step not in step_names:
        return {}, 0, "", []

    resume_index = step_names.index(first_failed_step)
    if resume_index <= 0:
        return {}, 0, "", []

    prior_names = list(step_names[:resume_index])
    steps = row.get("steps")
    if not isinstance(steps, list):
        return {}, 0, "", []

    existing_by_name: dict[str, dict[str, Any]] = {}
    for step in steps:
        if not isinstance(step, dict):
            continue
        name = str(step.get("step") or "").strip()
        if name and name not in existing_by_name:
            existing_by_name[name] = dict(step)

    prefix: dict[str, dict[str, Any]] = {}
    for name in prior_names:
        existing = existing_by_name.get(name)
        existing_rc = None if not isinstance(existing, dict) else existing.get("rc")
        if not isinstance(existing, dict) or existing_rc is None or int(existing_rc) != 0:
            return {}, 0, "", []
        prefix[name] = existing
    return prefix, resume_index, first_failed_step, prior_names


def _existing_step_map(row: dict[str, Any] | None) -> dict[str, dict[str, Any]]:
    if not isinstance(row, dict):
        return {}
    out: dict[str, dict[str, Any]] = {}
    for step in row.get("steps", []) or []:
        if not isinstance(step, dict):
            continue
        name = str(step.get("step") or "").strip()
        if name:
            out[name] = dict(step)
    return out


def _prepare_phase_resume(
    row: dict[str, Any] | None,
    *,
    target_step_names: list[str],
) -> tuple[dict[str, dict[str, Any]], int, list[str], str]:
    existing_map = _existing_step_map(row)
    preserved: dict[str, dict[str, Any]] = {}
    reused: list[str] = []
    for name, step in existing_map.items():
        if name not in target_step_names:
            preserved[name] = dict(step)
    start_idx = 0
    for idx, name in enumerate(target_step_names):
        step = existing_map.get(name)
        if isinstance(step, dict) and not bool(step.get("skipped")) and int(step.get("rc") or 0) == 0:
            preserved[name] = dict(step)
            reused.append(name)
            start_idx = idx + 1
            continue
        break
    resumed_from = target_step_names[start_idx] if reused and start_idx < len(target_step_names) else ""
    return preserved, start_idx, reused, resumed_from


def _make_skipped_step(step_name: str, *, skip_reason: str) -> dict[str, Any]:
    return {
        "step": step_name,
        "skipped": True,
        "skip_reason": skip_reason,
    }


def _collect_failed_steps(step_map: dict[str, dict[str, Any]], *, ordered_step_names: list[str]) -> list[str]:
    failed: list[str] = []
    for name in ordered_step_names:
        step = step_map.get(name)
        if not isinstance(step, dict) or bool(step.get("skipped")):
            continue
        if int(step.get("rc") or 0) != 0:
            failed.append(name)
    return failed


def _run_named_steps_for_task(
    *,
    root: Path,
    out_dir: Path,
    task_id: int,
    step_map: dict[str, dict[str, Any]],
    step_items: list[tuple[str, list[str]]],
    delivery_profile: str,
    explicit_timeout_sec: int | None,
    llm_timeout_sec: int | None,
    fill_refs_after_extract_fail: str,
    downstream_on_extract_fail: str,
    downstream_on_extract_family_fail: str,
    stop_on_step_failure: bool,
) -> list[str]:
    failed_steps: list[str] = []
    for step_name, template in step_items:
        guard_step = next(
            (
                step_map.get(name)
                for name in _EARLY_GUARD_STEP_NAMES
                if isinstance(step_map.get(name), dict)
                and not bool(step_map.get(name, {}).get("skipped"))
                and int(step_map.get(name, {}).get("rc") or 0) != 0
            ),
            None,
        )
        if isinstance(guard_step, dict) and str(guard_step.get("step") or "").strip() != step_name:
            step_map[step_name] = _make_skipped_step(step_name, skip_reason="preflight_extract_guard_failed")
            issue_ids = list((guard_step.get("inner_summary") or {}).get("issue_ids") or [])
            if issue_ids:
                step_map[step_name]["preflight_issue_ids"] = issue_ids
            continue

        extract_step = step_map.get("extract")
        extract_failed = isinstance(extract_step, dict) and not bool(extract_step.get("skipped")) and int(extract_step.get("rc") or 0) != 0
        if extract_failed:
            extract_fail_signature = _extract_fail_signature(extract_step) or ""
            extract_fail_family = _extract_fail_signature_family(extract_fail_signature)
            skip_reason = _skip_reason_for_step_after_extract_fail(
                step_name,
                fill_refs_after_extract_fail=fill_refs_after_extract_fail,
                downstream_on_extract_fail=downstream_on_extract_fail,
                downstream_on_extract_family_fail=downstream_on_extract_family_fail,
                extract_fail_family=extract_fail_family,
            )
            if skip_reason:
                step_map[step_name] = _make_skipped_step(step_name, skip_reason=skip_reason)
                if extract_fail_signature:
                    step_map[step_name]["extract_fail_signature"] = extract_fail_signature
                if extract_fail_family:
                    step_map[step_name]["extract_fail_family"] = extract_fail_family
                continue

        cmd = [part.format(id=task_id) for part in template]
        step_started = dt.datetime.now()
        step_started_monotonic = time.monotonic()
        rc, stdout, stderr, retry_meta = _run_step_with_retry(
            root=root,
            cmd=cmd,
            step_name=step_name,
            delivery_profile=delivery_profile,
            explicit_timeout_sec=explicit_timeout_sec,
            llm_timeout_sec=llm_timeout_sec,
        )
        duration_sec = round(max(0.0, time.monotonic() - step_started_monotonic), 3)
        log_path = out_dir / f"t{task_id:04d}--{step_name}.log"
        attempts = retry_meta.get("attempts") or []
        if isinstance(attempts, list) and attempts:
            log_chunks: list[str] = []
            for attempt in attempts:
                if not isinstance(attempt, dict):
                    continue
                log_chunks.extend(
                    [
                        f"attempt: {int(attempt.get('attempt') or 0)}",
                        f"cmd: {' '.join(list(attempt.get('cmd') or []))}",
                        f"timeout_sec: {int(attempt.get('timeout_sec') or 0)}",
                        f"rc: {int(attempt.get('rc') or 0)}",
                        "--- stdout ---",
                        str(attempt.get("stdout") or ""),
                        "--- stderr ---",
                        str(attempt.get("stderr") or ""),
                        "",
                    ]
                )
            log_body = "\n".join(log_chunks).rstrip() + "\n"
            snapshot_stdout = "\n".join(str(attempt.get("stdout") or "") for attempt in attempts if isinstance(attempt, dict))
            snapshot_stderr = "\n".join(str(attempt.get("stderr") or "") for attempt in attempts if isinstance(attempt, dict))
        else:
            log_body = "\n".join(
                [
                    f"cmd: {' '.join(cmd)}",
                    f"rc: {rc}",
                    "--- stdout ---",
                    stdout or "",
                    "--- stderr ---",
                    stderr or "",
                ]
            )
            snapshot_stdout = stdout
            snapshot_stderr = stderr
        log_path.write_text(log_body, encoding="utf-8")
        step_map[step_name] = {
            "step": step_name,
            "rc": rc,
            "started_at": step_started.isoformat(timespec="seconds"),
            "duration_sec": duration_sec,
            "log": _relative_to_root(root, log_path),
            "stdout_tail": stdout.strip().splitlines()[-1] if stdout.strip() else "",
            "stderr_tail": stderr.strip().splitlines()[-1] if stderr.strip() else "",
            "retry_count": int(retry_meta.get("retry_count") or 0),
            "retry_rcs": [int(item) for item in list(retry_meta.get("retry_rcs") or [])],
            "attempt_count": int(retry_meta.get("attempt_count") or 1),
        }
        step_map[step_name].update(
            _snapshot_inner_artifacts(
                root=root,
                wrapper_out_dir=out_dir,
                task_id=task_id,
                step_name=step_name,
                stdout=snapshot_stdout,
                stderr=snapshot_stderr,
            )
        )
        if rc != 0:
            failed_steps.append(step_name)
            if stop_on_step_failure:
                break
    return failed_steps


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run workflow 5.1 single-task light lane with full-step execution.")
    parser.add_argument("--task-ids", default="", help="Optional CSV task ids override (e.g. 12,14,21).")
    parser.add_argument("--task-id-start", type=int, default=1)
    parser.add_argument("--task-id-end", type=int, default=0, help="0 means until max task id.")
    parser.add_argument("--max-tasks", type=int, default=0, help="0 means all selected tasks.")
    parser.add_argument("--timeout-sec", type=int, default=None, help="Wrapper timeout per step in seconds (default: auto > inner step timeout).")
    parser.add_argument("--llm-timeout-sec", type=int, default=None, help="Forwarded inner timeout for LLM-backed 5.1 steps.")
    parser.add_argument("--out-dir", default="", help="Output directory. Default: logs/ci/<date>/single-task-light-lane-v2")
    parser.add_argument("--no-resume", action="store_true", help="Ignore existing summary.json and rerun from scratch.")
    parser.add_argument(
        "--fill-refs-after-extract-fail",
        default="skip",
        choices=["skip", "continue"],
        help="Whether fill-refs steps should still run after extract fails.",
    )
    parser.add_argument(
        "--fill-refs-mode",
        default="auto",
        choices=["auto", "none", "dry", "write-verify"],
        help="Whether batch runs should skip fill-refs entirely, keep dry only, or run write+verify. 'auto' => none for multi-task and write-verify for single-task.",
    )
    parser.add_argument(
        "--downstream-on-extract-fail",
        default="auto",
        choices=["auto", "continue", "skip-soft", "skip-all"],
        help="How later steps should behave after extract fails. 'auto' resolves to continue for one task and skip-soft for multi-task batches.",
    )
    parser.add_argument(
        "--downstream-on-extract-family-fail",
        default="auto",
        choices=["auto", "off", "continue", "skip-soft", "skip-all"],
        help="Family-aware override after extract fails. 'auto' skip-all for timeout / obligations-fail and skip-soft for model-output-invalid families.",
    )
    parser.add_argument(
        "--batch-lane",
        default="auto",
        choices=["auto", "standard", "extract-first"],
        help="Batch execution style. 'auto' resolves to extract-first for multi-task batches and standard for one task.",
    )
    parser.add_argument(
        "--resume-failed-task-from",
        default="always-rerun",
        choices=["always-rerun", "first-failed-step"],
        help="When resuming a failed task, rerun all steps or reuse the successful prefix and restart from the first failed step.",
    )
    parser.add_argument("--stop-on-step-failure", action="store_true", help="Stop remaining steps in one task when one step fails.")
    parser.add_argument("--no-align-apply", action="store_true", help="Do not pass --apply to align step (read-only mode).")
    parser.add_argument(
        "--delivery-profile",
        default=str(os.environ.get("DELIVERY_PROFILE") or "fast-ship"),
        choices=["playable-ea", "fast-ship", "standard"],
        help="Delivery profile for light-lane LLM steps.",
    )
    parser.add_argument("--self-check", action="store_true", help="Print resolved task range and step names, then exit.")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    root = _repo_root()
    selected = _select_task_ids(root, args)
    if not selected:
        print("SINGLE_TASK_LIGHT_LANE status=fail reason=no_selected_tasks")
        return 2

    out_dir = Path(args.out_dir) if str(args.out_dir).strip() else _default_out_dir(root)
    out_dir.mkdir(parents=True, exist_ok=True)
    summary_path = out_dir / "summary.json"
    align_apply = not bool(args.no_align_apply)
    fill_refs_mode_resolved = _resolve_fill_refs_mode(str(args.fill_refs_mode), selected_count=len(selected))
    batch_lane_resolved = _resolve_batch_lane(str(args.batch_lane), selected_count=len(selected))
    steps = _apply_fill_refs_mode(
        _steps(
            align_apply=align_apply,
            delivery_profile=str(args.delivery_profile),
            llm_timeout_sec=args.llm_timeout_sec,
        ),
        fill_refs_mode=fill_refs_mode_resolved,
    )
    downstream_on_extract_fail_resolved = _resolve_downstream_on_extract_fail(
        str(args.downstream_on_extract_fail),
        selected_count=len(selected),
    )
    downstream_on_extract_family_fail_resolved = str(args.downstream_on_extract_family_fail)
    if batch_lane_resolved == "extract-first" and downstream_on_extract_fail_resolved == "continue":
        downstream_on_extract_fail_resolved = "skip-soft"
    step_lookup = {name: cmd for name, cmd in steps}
    phase1_step_names = [name for name in ["preflight_extract_guard", "extract", "align"] if name in step_lookup]
    phase2_step_names = [name for name, _cmd in steps if name not in phase1_step_names]
    step_names = [name for name, _ in steps]
    resume_scope = _build_resume_scope(
        selected=selected,
        delivery_profile=str(args.delivery_profile),
        align_apply=align_apply,
        fill_refs_after_extract_fail=str(args.fill_refs_after_extract_fail),
        downstream_on_extract_fail=downstream_on_extract_fail_resolved,
        downstream_on_extract_family_fail=downstream_on_extract_family_fail_resolved,
        fill_refs_mode=fill_refs_mode_resolved,
        batch_lane=batch_lane_resolved,
    )

    if bool(args.self_check):
        payload = {
            "status": "ok",
            "task_count": len(selected),
            "task_id_start": selected[0],
            "task_id_end": selected[-1],
            "steps": step_names,
            "delivery_profile": str(args.delivery_profile),
            "out_dir": str(out_dir).replace("\\", "/"),
            "resume_scope": resume_scope,
            "resume_failed_task_from": str(args.resume_failed_task_from),
            "fill_refs_after_extract_fail": str(args.fill_refs_after_extract_fail),
            "fill_refs_mode_requested": str(args.fill_refs_mode),
            "fill_refs_mode_resolved": fill_refs_mode_resolved,
            "downstream_on_extract_fail_requested": str(args.downstream_on_extract_fail),
            "downstream_on_extract_fail_resolved": downstream_on_extract_fail_resolved,
            "downstream_on_extract_family_fail_requested": str(args.downstream_on_extract_family_fail),
            "downstream_on_extract_family_fail_resolved": downstream_on_extract_family_fail_resolved,
            "batch_lane_requested": str(args.batch_lane),
            "batch_lane_resolved": batch_lane_resolved,
            "phase1_step_names": phase1_step_names,
            "phase2_step_names": phase2_step_names,
        }
        _refresh_route_contract(
            payload,
            root=root,
            selected=selected,
            delivery_profile=str(args.delivery_profile),
            align_apply=align_apply,
            fill_refs_after_extract_fail=str(args.fill_refs_after_extract_fail),
            fill_refs_mode=fill_refs_mode_resolved,
            downstream_on_extract_fail=downstream_on_extract_fail_resolved,
            downstream_on_extract_family_fail=downstream_on_extract_family_fail_resolved,
            batch_lane=batch_lane_resolved,
            wrapper_timeout_sec=args.timeout_sec,
            llm_timeout_sec=args.llm_timeout_sec,
            planning_mode=True,
        )
        next_action = _derive_summary_next_action(payload)
        payload["recommended_next_action"] = str(next_action.get("action") or "")
        payload["recommended_next_action_why"] = str(next_action.get("why") or "")
        _write_json(summary_path, payload)
        print(
            f"SINGLE_TASK_LIGHT_LANE_SELF_CHECK status=ok tasks={len(selected)} "
            f"range=T{selected[0]}-T{selected[-1]} out={str(summary_path).replace('\\', '/')}"
        )
        return 0

    old_summary = None if bool(args.no_resume) else _load_summary(summary_path)
    summary: dict[str, Any]
    if isinstance(old_summary, dict) and _summary_scope_matches(old_summary, resume_scope):
        summary = old_summary
    else:
        summary = {}
    if not isinstance(summary.get("results"), list):
        summary["results"] = []
    summary.setdefault("cmd", "run_single_task_light_lane")
    summary.setdefault("started_at", dt.datetime.now().isoformat(timespec="seconds"))
    summary["task_id_start"] = selected[0]
    summary["task_id_end"] = selected[-1]
    summary["task_count"] = len(selected)
    summary["delivery_profile"] = str(args.delivery_profile)
    summary["align_apply"] = align_apply
    summary["out_dir"] = str(out_dir).replace("\\", "/")
    summary["status"] = "running"
    summary["resume_scope"] = resume_scope
    summary["resume_failed_task_from"] = str(args.resume_failed_task_from)
    summary["fill_refs_after_extract_fail"] = str(args.fill_refs_after_extract_fail)
    summary["fill_refs_mode_requested"] = str(args.fill_refs_mode)
    summary["fill_refs_mode_resolved"] = fill_refs_mode_resolved
    summary["downstream_on_extract_fail_requested"] = str(args.downstream_on_extract_fail)
    summary["downstream_on_extract_fail_resolved"] = downstream_on_extract_fail_resolved
    summary["downstream_on_extract_family_fail_requested"] = str(args.downstream_on_extract_family_fail)
    summary["downstream_on_extract_family_fail_resolved"] = downstream_on_extract_family_fail_resolved
    summary["batch_lane_requested"] = str(args.batch_lane)
    summary["batch_lane_resolved"] = batch_lane_resolved
    summary["phase1_step_names"] = phase1_step_names
    summary["phase2_step_names"] = phase2_step_names
    summary["llm_timeout_sec"] = int(args.llm_timeout_sec) if args.llm_timeout_sec is not None else None
    summary["wrapper_timeout_sec"] = int(args.timeout_sec) if args.timeout_sec is not None else None
    summary["resume_reused"] = bool(isinstance(old_summary, dict) and _summary_scope_matches(old_summary, resume_scope))
    summary["resume_scope_reset"] = bool(isinstance(old_summary, dict) and not _summary_scope_matches(old_summary, resume_scope))

    existing = _index_results(summary["results"])
    updated: dict[int, dict[str, Any]] = {task_id: row for task_id, row in existing.items() if task_id in set(selected)}
    skipped_completed = 0
    def _flush_summary(*, last_task_id: int) -> None:
        summary["results"] = [updated[key] for key in sorted(updated.keys())]
        _rebuild_counts(summary)
        summary["remaining_tasks"] = max(0, len(selected) - int(summary.get("processed_tasks", 0)))
        summary["last_task_id"] = last_task_id
        summary["last_updated_at"] = dt.datetime.now().isoformat(timespec="seconds")
        summary["skipped_completed_tasks"] = skipped_completed
        _refresh_route_contract(
            summary,
            root=root,
            selected=selected,
            delivery_profile=str(args.delivery_profile),
            align_apply=align_apply,
            fill_refs_after_extract_fail=str(args.fill_refs_after_extract_fail),
            fill_refs_mode=fill_refs_mode_resolved,
            downstream_on_extract_fail=downstream_on_extract_fail_resolved,
            downstream_on_extract_family_fail=downstream_on_extract_family_fail_resolved,
            batch_lane=batch_lane_resolved,
            wrapper_timeout_sec=args.timeout_sec,
            llm_timeout_sec=args.llm_timeout_sec,
        )
        _write_json(summary_path, summary)

    if batch_lane_resolved == "extract-first" and len(selected) > 1:
        summary["phase"] = "phase1"
        phase1_items = [(name, step_lookup[name]) for name in phase1_step_names]
        for idx, task_id in enumerate(selected, start=1):
            existing_row = updated.get(task_id)
            if _row_is_complete(existing_row, step_names=step_names):
                skipped_completed += 1
                _flush_summary(last_task_id=task_id)
                continue
            print(f"[phase1 {idx}/{len(selected)}] run task {task_id}")
            row = dict(existing_row) if isinstance(existing_row, dict) else {"task_id": task_id, "steps": []}
            step_map, phase_start_index, reused_successful_steps, resumed_from_step = _prepare_phase_resume(
                existing_row,
                target_step_names=phase1_step_names,
            )
            if resumed_from_step:
                row["phase1_resumed_from_step"] = resumed_from_step
            if reused_successful_steps:
                row["phase1_reused_successful_steps"] = list(reused_successful_steps)
            _run_named_steps_for_task(
                root=root,
                out_dir=out_dir,
                task_id=task_id,
                step_map=step_map,
                step_items=phase1_items[phase_start_index:],
                delivery_profile=str(args.delivery_profile),
                explicit_timeout_sec=args.timeout_sec,
                llm_timeout_sec=args.llm_timeout_sec,
                fill_refs_after_extract_fail=str(args.fill_refs_after_extract_fail),
                downstream_on_extract_fail=downstream_on_extract_fail_resolved,
                downstream_on_extract_family_fail=downstream_on_extract_family_fail_resolved,
                stop_on_step_failure=bool(args.stop_on_step_failure),
            )
            ordered = [step_map[name] for name in step_names if name in step_map]
            failed_steps = _collect_failed_steps(step_map, ordered_step_names=step_names)
            row["steps"] = ordered
            row["failed_steps"] = failed_steps
            row["first_failed_step"] = failed_steps[0] if failed_steps else ""
            row["ok"] = (len(failed_steps) == 0 and len(ordered) == len(steps))
            updated[task_id] = row
            _flush_summary(last_task_id=task_id)

        phase2_candidates: list[int] = []
        for task_id in selected:
            row = updated.get(task_id)
            if _row_is_complete(row, step_names=step_names):
                continue
            extract_step = _existing_step_map(row).get("extract")
            if isinstance(extract_step, dict) and not bool(extract_step.get("skipped")) and int(extract_step.get("rc") or 0) == 0:
                phase2_candidates.append(task_id)
        summary["phase"] = "phase2"
        summary["phase2_candidate_task_ids"] = [int(task_id) for task_id in phase2_candidates]
        phase2_items = [(name, step_lookup[name]) for name in phase2_step_names]
        for idx, task_id in enumerate(phase2_candidates, start=1):
            existing_row = updated.get(task_id)
            print(f"[phase2 {idx}/{len(phase2_candidates)}] run task {task_id}")
            row = dict(existing_row) if isinstance(existing_row, dict) else {"task_id": task_id, "steps": []}
            step_map, phase_start_index, reused_successful_steps, resumed_from_step = _prepare_phase_resume(
                existing_row,
                target_step_names=phase2_step_names,
            )
            if resumed_from_step:
                row["phase2_resumed_from_step"] = resumed_from_step
            if reused_successful_steps:
                row["phase2_reused_successful_steps"] = list(reused_successful_steps)
            _run_named_steps_for_task(
                root=root,
                out_dir=out_dir,
                task_id=task_id,
                step_map=step_map,
                step_items=phase2_items[phase_start_index:],
                delivery_profile=str(args.delivery_profile),
                explicit_timeout_sec=args.timeout_sec,
                llm_timeout_sec=args.llm_timeout_sec,
                fill_refs_after_extract_fail=str(args.fill_refs_after_extract_fail),
                downstream_on_extract_fail=downstream_on_extract_fail_resolved,
                downstream_on_extract_family_fail=downstream_on_extract_family_fail_resolved,
                stop_on_step_failure=bool(args.stop_on_step_failure),
            )
            ordered = [step_map[name] for name in step_names if name in step_map]
            failed_steps = _collect_failed_steps(step_map, ordered_step_names=step_names)
            row["steps"] = ordered
            row["failed_steps"] = failed_steps
            row["first_failed_step"] = failed_steps[0] if failed_steps else ""
            row["ok"] = (len(failed_steps) == 0 and len(ordered) == len(steps))
            updated[task_id] = row
            _flush_summary(last_task_id=task_id)
        summary.pop("phase", None)
    else:
        for idx, task_id in enumerate(selected, start=1):
            existing_row = updated.get(task_id)
            if _row_is_complete(existing_row, step_names=step_names):
                skipped_completed += 1
                _flush_summary(last_task_id=task_id)
                continue

            print(f"[{idx}/{len(selected)}] run task {task_id}")
            row = {"task_id": task_id, "steps": []}
            step_map, resume_start_index, resumed_from_step, reused_successful_steps = _prepare_failed_row_resume(
                existing_row,
                step_names=step_names,
                resume_failed_task_from=str(args.resume_failed_task_from),
            )
            if resumed_from_step:
                row["resumed_from_step"] = resumed_from_step
                row["reused_successful_steps"] = list(reused_successful_steps)
            else:
                resume_start_index = 0

            _run_named_steps_for_task(
                root=root,
                out_dir=out_dir,
                task_id=task_id,
                step_map=step_map,
                step_items=steps[resume_start_index:],
                delivery_profile=str(args.delivery_profile),
                explicit_timeout_sec=args.timeout_sec,
                llm_timeout_sec=args.llm_timeout_sec,
                fill_refs_after_extract_fail=str(args.fill_refs_after_extract_fail),
                downstream_on_extract_fail=downstream_on_extract_fail_resolved,
                downstream_on_extract_family_fail=downstream_on_extract_family_fail_resolved,
                stop_on_step_failure=bool(args.stop_on_step_failure),
            )

            ordered = [step_map[name] for name in step_names if name in step_map]
            failed_steps = _collect_failed_steps(step_map, ordered_step_names=step_names)
            row["steps"] = ordered
            row["failed_steps"] = failed_steps
            row["first_failed_step"] = failed_steps[0] if failed_steps else ""
            row["ok"] = (len(failed_steps) == 0 and len(ordered) == len(steps))
            updated[task_id] = row
            _flush_summary(last_task_id=task_id)

    _rebuild_counts(summary)
    summary["remaining_tasks"] = max(0, len(selected) - int(summary.get("processed_tasks", 0)))
    summary["status"] = "ok" if int(summary.get("failed_tasks", 0)) == 0 else "fail"
    summary["finished_at"] = dt.datetime.now().isoformat(timespec="seconds")
    summary["skipped_completed_tasks"] = skipped_completed
    _refresh_route_contract(
        summary,
        root=root,
        selected=selected,
        delivery_profile=str(args.delivery_profile),
        align_apply=align_apply,
        fill_refs_after_extract_fail=str(args.fill_refs_after_extract_fail),
        fill_refs_mode=fill_refs_mode_resolved,
        downstream_on_extract_fail=downstream_on_extract_fail_resolved,
        downstream_on_extract_family_fail=downstream_on_extract_family_fail_resolved,
        batch_lane=batch_lane_resolved,
        wrapper_timeout_sec=args.timeout_sec,
        llm_timeout_sec=args.llm_timeout_sec,
    )
    _write_json(summary_path, summary)
    print(
        "SINGLE_TASK_LIGHT_LANE "
        f"status={summary['status']} processed={summary.get('processed_tasks', 0)}/{len(selected)} "
        f"passed={summary.get('passed_tasks', 0)} failed={summary.get('failed_tasks', 0)} "
        f"out={str(summary_path).replace('\\', '/')}"
    )
    return 0 if summary["status"] == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
