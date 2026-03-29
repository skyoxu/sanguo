#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Coordinate workflow 5.1 light-lane runs across isolated shards, then merge summaries."""

from __future__ import annotations

import argparse
import datetime as dt
import importlib.util
import json
import math
import subprocess
import sys
from argparse import Namespace
from pathlib import Path
from typing import Any


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _load_local_module(name: str, filename: str):
    path = Path(__file__).resolve().with_name(filename)
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"failed to load module: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


_LANE = _load_local_module("single_task_light_lane_batch_lane", "run_single_task_light_lane.py")
_MERGE = _load_local_module("single_task_light_lane_batch_merge", "merge_single_task_light_lane_summaries.py")

_BATCH_PRESETS: dict[str, dict[str, Any]] = {
    "none": {},
    "stable-batch": {
        "batch_lane": "extract-first",
        "fill_refs_mode": "none",
        "downstream_on_extract_fail": "skip-soft",
        "downstream_on_extract_family_fail": "auto",
        "rolling_extract_policy": "degrade",
        "rolling_extract_rate_threshold": 0.45,
        "rolling_extract_min_observed_tasks": 8,
        "rolling_family_policy": "warn",
        "rolling_family_streak_threshold": 5,
        "rolling_timeout_backoff_threshold": 0.5,
        "rolling_timeout_backoff_min_observed_tasks": 4,
        "rolling_timeout_backoff_sec": 180,
        "rolling_timeout_backoff_max_llm_timeout_sec": 1200,
        "rolling_shard_reduction_factor": 0.5,
    },
    "long-batch": {
        "batch_lane": "extract-first",
        "fill_refs_mode": "none",
        "downstream_on_extract_fail": "skip-soft",
        "downstream_on_extract_family_fail": "auto",
        "rolling_extract_policy": "stop",
        "rolling_extract_rate_threshold": 0.4,
        "rolling_extract_min_observed_tasks": 6,
        "rolling_family_policy": "stop",
        "rolling_family_streak_threshold": 4,
        "rolling_timeout_backoff_threshold": 0.45,
        "rolling_timeout_backoff_min_observed_tasks": 4,
        "rolling_timeout_backoff_sec": 240,
        "rolling_timeout_backoff_max_llm_timeout_sec": 1500,
        "rolling_shard_reduction_factor": 0.5,
    },
}


def _today() -> str:
    return dt.date.today().strftime("%Y-%m-%d")


def _default_out_dir(root: Path) -> Path:
    return root / "logs" / "ci" / _today() / "single-task-light-lane-v2-batch"


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _load_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    return payload if isinstance(payload, dict) else None


def _split_task_ids(task_ids: list[int], shard_size: int) -> list[list[int]]:
    if shard_size <= 0:
        raise ValueError("shard_size must be > 0")
    return [task_ids[idx : idx + shard_size] for idx in range(0, len(task_ids), shard_size)]


def _selected_task_ids(root: Path, args: argparse.Namespace) -> list[int]:
    selector = Namespace(
        task_ids=str(args.task_ids),
        task_id_start=int(args.task_id_start),
        task_id_end=int(args.task_id_end),
        max_tasks=int(args.max_tasks),
    )
    return list(_LANE._select_task_ids(root, selector))


def _relative_to_root(root: Path, path: Path) -> str:
    try:
        return str(path.relative_to(root)).replace("\\", "/")
    except Exception:
        return str(path).replace("\\", "/")


def _build_shard_name(index: int, task_ids: list[int]) -> str:
    return f"shard-{index:03d}-t{task_ids[0]}-{task_ids[-1]}"


def _build_lane_command(args: argparse.Namespace, shard_task_ids: list[int], shard_out_dir: Path) -> list[str]:
    cmd = [
        sys.executable,
        str(Path(__file__).resolve().with_name("run_single_task_light_lane.py")),
        "--task-ids",
        ",".join(str(task_id) for task_id in shard_task_ids),
        "--delivery-profile",
        str(args.delivery_profile),
        "--out-dir",
        str(shard_out_dir),
        "--fill-refs-after-extract-fail",
        str(args.fill_refs_after_extract_fail),
        "--fill-refs-mode",
        str(args.fill_refs_mode),
        "--downstream-on-extract-fail",
        str(args.downstream_on_extract_fail),
        "--downstream-on-extract-family-fail",
        str(args.downstream_on_extract_family_fail),
        "--batch-lane",
        str(args.batch_lane),
        "--resume-failed-task-from",
        str(args.resume_failed_task_from),
    ]
    if args.timeout_sec is not None:
        cmd.extend(["--timeout-sec", str(int(args.timeout_sec))])
    if args.llm_timeout_sec is not None:
        cmd.extend(["--llm-timeout-sec", str(int(args.llm_timeout_sec))])
    if bool(args.no_resume):
        cmd.append("--no-resume")
    if bool(args.stop_on_step_failure):
        cmd.append("--stop-on-step-failure")
    if bool(args.no_align_apply):
        cmd.append("--no-align-apply")
    return cmd


def _copy_args_with_overrides(args: argparse.Namespace, **overrides: Any) -> argparse.Namespace:
    data = vars(args).copy()
    data.update(overrides)
    return Namespace(**data)


def _argv_has_option(argv: list[str], option: str) -> bool:
    return any(str(part).strip() == option for part in list(argv or []))


def _apply_batch_preset(args: argparse.Namespace, argv: list[str]) -> argparse.Namespace:
    preset_name = str(getattr(args, "batch_preset", "none") or "none")
    preset = dict(_BATCH_PRESETS.get(preset_name) or {})
    if not preset:
        return args
    option_map = {
        "batch_lane": "--batch-lane",
        "fill_refs_mode": "--fill-refs-mode",
        "downstream_on_extract_fail": "--downstream-on-extract-fail",
        "downstream_on_extract_family_fail": "--downstream-on-extract-family-fail",
        "rolling_extract_policy": "--rolling-extract-policy",
        "rolling_extract_rate_threshold": "--rolling-extract-rate-threshold",
        "rolling_extract_min_observed_tasks": "--rolling-extract-min-observed-tasks",
        "rolling_family_policy": "--rolling-family-policy",
        "rolling_family_streak_threshold": "--rolling-family-streak-threshold",
        "rolling_timeout_backoff_threshold": "--rolling-timeout-backoff-threshold",
        "rolling_timeout_backoff_min_observed_tasks": "--rolling-timeout-backoff-min-observed-tasks",
        "rolling_timeout_backoff_sec": "--rolling-timeout-backoff-sec",
        "rolling_timeout_backoff_max_llm_timeout_sec": "--rolling-timeout-backoff-max-llm-timeout-sec",
        "rolling_shard_reduction_factor": "--rolling-shard-reduction-factor",
    }
    overrides: dict[str, Any] = {}
    applied: dict[str, Any] = {}
    for key, value in preset.items():
        option = option_map.get(key)
        if option and _argv_has_option(argv, option):
            continue
        overrides[key] = value
        applied[key] = value
    if not overrides:
        setattr(args, "batch_preset_applied", {})
        return args
    updated = _copy_args_with_overrides(args, **overrides)
    setattr(updated, "batch_preset_applied", applied)
    return updated


def _run_command(root: Path, cmd: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=str(root), capture_output=True, text=True, encoding="utf-8")


def _shard_status_code(shard_summary: dict[str, Any] | None, rc: int) -> str:
    if isinstance(shard_summary, dict):
        status = str(shard_summary.get("status") or "").strip()
        if status:
            return status
    return "ok" if int(rc) == 0 else "fail"


def _run_shard(
    *,
    root: Path,
    args: argparse.Namespace,
    shard_task_ids: list[int],
    shard_index: int,
    shard_count: int,
    shards_root: Path,
) -> dict[str, Any]:
    shard_name = _build_shard_name(shard_index, shard_task_ids)
    shard_out_dir = shards_root / shard_name
    shard_out_dir.mkdir(parents=True, exist_ok=True)
    cmd = _build_lane_command(args, shard_task_ids, shard_out_dir)
    print(f"[shard {shard_index}/{shard_count}] tasks={len(shard_task_ids)} range=T{shard_task_ids[0]}-T{shard_task_ids[-1]}")
    proc = _run_command(root, cmd)
    summary_path = shard_out_dir / "summary.json"
    shard_summary = _load_json(summary_path)
    extract_metrics = _extract_metrics_from_summary(shard_summary)
    entry = {
        "index": shard_index,
        "name": shard_name,
        "task_ids": [int(task_id) for task_id in shard_task_ids],
        "task_id_start": int(shard_task_ids[0]),
        "task_id_end": int(shard_task_ids[-1]),
        "task_count": len(shard_task_ids),
        "cmd": [str(part) for part in cmd],
        "rc": int(proc.returncode),
        "status": _shard_status_code(shard_summary, proc.returncode),
        "out_dir": _relative_to_root(root, shard_out_dir),
        "summary_path": _relative_to_root(root, summary_path),
        "summary_exists": bool(isinstance(shard_summary, dict)),
        "stdout_tail": str(proc.stdout or "").splitlines()[-20:],
        "stderr_tail": str(proc.stderr or "").splitlines()[-20:],
        "extract_observed_tasks": int(extract_metrics.get("observed_tasks") or 0),
        "extract_failed_tasks": int(extract_metrics.get("failed_tasks") or 0),
        "extract_timeout_tasks": int(extract_metrics.get("timeout_tasks") or 0),
        "extract_fail_rate": float(extract_metrics.get("fail_rate") or 0.0),
        "extract_timeout_rate": float(extract_metrics.get("timeout_rate") or 0.0),
        "extract_failed_task_ids": list(extract_metrics.get("failed_task_ids") or []),
    }
    if isinstance(shard_summary, dict):
        for key in [
            "processed_tasks",
            "passed_tasks",
            "failed_tasks",
            "remaining_tasks",
            "last_task_id",
            "batch_lane_resolved",
            "fill_refs_mode_resolved",
            "downstream_on_extract_fail_resolved",
            "downstream_on_extract_family_fail_resolved",
            "failure_category_counts",
            "extract_fail_bucket_counts",
            "prompt_trimmed_count",
        ]:
            if key in shard_summary:
                entry[key] = shard_summary.get(key)
    return entry


def _extract_metrics_from_summary(shard_summary: dict[str, Any] | None) -> dict[str, Any]:
    observed = 0
    failed = 0
    timeouts = 0
    failed_task_ids: list[int] = []
    if not isinstance(shard_summary, dict):
        return {"observed_tasks": 0, "failed_tasks": 0, "timeout_tasks": 0, "fail_rate": 0.0, "timeout_rate": 0.0, "failed_task_ids": []}
    for row in shard_summary.get("results", []) or []:
        if not isinstance(row, dict):
            continue
        task_raw = str(row.get("task_id") or "").strip()
        for step in row.get("steps", []) or []:
            if not isinstance(step, dict):
                continue
            if str(step.get("step") or "").strip() != "extract":
                continue
            if bool(step.get("skipped")):
                break
            observed += 1
            if int(step.get("rc") or 0) != 0:
                failed += 1
                if int(step.get("rc") or 0) == 124:
                    timeouts += 1
                if task_raw.isdigit():
                    failed_task_ids.append(int(task_raw))
            break
    rate = (float(failed) / float(observed)) if observed > 0 else 0.0
    timeout_rate = (float(timeouts) / float(observed)) if observed > 0 else 0.0
    return {
        "observed_tasks": int(observed),
        "failed_tasks": int(failed),
        "timeout_tasks": int(timeouts),
        "fail_rate": rate,
        "timeout_rate": timeout_rate,
        "failed_task_ids": failed_task_ids,
    }


def _extract_family_events_from_summary(shard_summary: dict[str, Any] | None) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    if not isinstance(shard_summary, dict):
        return events
    rows: list[dict[str, Any]] = []
    for row in shard_summary.get("results", []) or []:
        if isinstance(row, dict):
            rows.append(row)
    rows.sort(key=lambda item: int(str(item.get("task_id") or "0").strip()) if str(item.get("task_id") or "").strip().isdigit() else 0)
    for row in rows:
        raw = str(row.get("task_id") or "").strip()
        if not raw.isdigit():
            continue
        task_id = int(raw)
        family = ""
        signature = ""
        for step in row.get("steps", []) or []:
            if not isinstance(step, dict):
                continue
            if str(step.get("step") or "").strip() != "extract":
                continue
            if bool(step.get("skipped")):
                break
            if int(step.get("rc") or 0) != 0:
                signature = str(_LANE._extract_fail_signature(step) or "")
                family = str(_LANE._extract_fail_signature_family(signature) or "")
            break
        events.append({"task_id": task_id, "family": family, "signature": signature})
    return events


def _recommended_action_for_extract_family(family: str) -> dict[str, str]:
    value = str(family or "").strip()
    if not value:
        return {
            "recommended_action": "inspect_extract_logs",
            "downstream_policy_hint": "manual",
            "reason": "extract failed but no stable failure family was detected",
        }
    if value == "timeout":
        return {
            "recommended_action": "raise_extract_timeout_or_reduce_batch_scope",
            "downstream_policy_hint": "skip-all",
            "reason": "extract timed out; retry extract first before spending more downstream work",
        }
    if value in {"stdout:sc_llm_obligations_status_fail", "stderr:sc_llm_obligations_status_fail"}:
        return {
            "recommended_action": "repair_obligations_or_task_context_before_downstream",
            "downstream_policy_hint": "skip-all",
            "reason": "extract already reported obligations failure; align/coverage/review are low-value until obligations recover",
        }
    if value in {"stdout:model_output_invalid", "stderr:model_output_invalid", "error:model_output_invalid"}:
        return {
            "recommended_action": "tighten_prompt_or_reduce_extract_scope_then_retry",
            "downstream_policy_hint": "skip-soft",
            "reason": "model output was invalid; fix extract prompt/scope first and only then continue downstream",
        }
    if value == "schema_error":
        return {
            "recommended_action": "repair_extract_schema_or_refs_then_retry",
            "downstream_policy_hint": "skip-soft",
            "reason": "extract output/schema was invalid; repair schema contract before downstream checks",
        }
    if value == "hard_uncovered":
        return {
            "recommended_action": "fill_required_obligations_or_acceptance_refs_then_retry",
            "downstream_policy_hint": "skip-soft",
            "reason": "required obligations were uncovered; finish mandatory refs before downstream work",
        }
    if value.startswith("error:"):
        return {
            "recommended_action": "inspect_extract_inner_summary_and_error",
            "downstream_policy_hint": "manual",
            "reason": "extract failed with an explicit error from inner summary",
        }
    return {
        "recommended_action": "inspect_extract_log_for_family",
        "downstream_policy_hint": "manual",
        "reason": "extract family is uncommon; inspect the shard log before changing downstream behavior",
    }


def _build_extract_family_recommended_actions(merged_payload: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not isinstance(merged_payload, dict):
        return []
    counts = merged_payload.get("extract_fail_family_counts")
    if not isinstance(counts, dict):
        return []
    task_ids_map = merged_payload.get("extract_fail_family_task_ids")
    out: list[dict[str, Any]] = []
    for family, raw_count in sorted(
        ((str(key), int(value or 0)) for key, value in counts.items() if str(key).strip()),
        key=lambda item: (-item[1], item[0]),
    ):
        action = _recommended_action_for_extract_family(family)
        task_ids = []
        if isinstance(task_ids_map, dict):
            task_ids = [int(task_id) for task_id in list(task_ids_map.get(family) or []) if str(task_id).strip().isdigit()]
        out.append(
            {
                "family": family,
                "count": int(raw_count),
                "task_ids": task_ids,
                **action,
            }
        )
    return out


def _new_rolling_extract_state(args: argparse.Namespace) -> dict[str, Any]:
    return {
        "policy": str(args.rolling_extract_policy),
        "threshold": float(args.rolling_extract_rate_threshold),
        "min_observed_tasks": int(args.rolling_extract_min_observed_tasks),
        "observed_tasks": 0,
        "failed_tasks": 0,
        "fail_rate": 0.0,
        "triggered": False,
        "trigger_shard_index": None,
        "trigger_reason": "",
        "action": "none",
        "degraded_mode_active": False,
        "warnings": [],
        "current_llm_timeout_sec": int(args.llm_timeout_sec) if args.llm_timeout_sec is not None else None,
        "current_max_tasks_per_shard": int(args.max_tasks_per_shard),
        "backoff_adjustment_count": 0,
        "backoff_history": [],
    }


def _new_rolling_family_state(args: argparse.Namespace) -> dict[str, Any]:
    return {
        "policy": str(args.rolling_family_policy),
        "streak_threshold": int(args.rolling_family_streak_threshold),
        "current_family": "",
        "current_signature": "",
        "current_streak": 0,
        "current_range_start": None,
        "current_range_end": None,
        "triggered": False,
        "trigger_shard_index": None,
        "trigger_reason": "",
        "action": "none",
        "warnings": [],
        "hotspots": [],
        "quarantine_ranges": [],
    }


def _rolling_extract_effective_args(args: argparse.Namespace, state: dict[str, Any]) -> argparse.Namespace:
    overrides: dict[str, Any] = {}
    current_llm_timeout_sec = state.get("current_llm_timeout_sec")
    if current_llm_timeout_sec is not None:
        overrides["llm_timeout_sec"] = int(current_llm_timeout_sec)
    if bool(state.get("degraded_mode_active")):
        overrides["no_align_apply"] = True
        overrides["fill_refs_mode"] = "none"
        overrides["downstream_on_extract_fail"] = "skip-all"
        overrides["downstream_on_extract_family_fail"] = "skip-all"
    if not overrides:
        return args
    return _copy_args_with_overrides(args, **overrides)


def _compute_next_shard_size(state: dict[str, Any], default_shard_size: int) -> int:
    current = int(state.get("current_max_tasks_per_shard") or default_shard_size or 1)
    return max(1, current)


def _append_family_hotspot(state: dict[str, Any]) -> dict[str, Any]:
    family = str(state.get("current_family") or "")
    start = state.get("current_range_start")
    end = state.get("current_range_end")
    streak = int(state.get("current_streak") or 0)
    threshold = int(state.get("streak_threshold") or 0)
    if not family or start is None or end is None or streak < max(1, threshold):
        return state
    hotspot = {
        "family": family,
        "signature": str(state.get("current_signature") or ""),
        "task_id_start": int(start),
        "task_id_end": int(end),
        "count": int(streak),
    }
    hotspots = list(state.get("hotspots") or [])
    if hotspots and hotspots[-1].get("family") == hotspot["family"] and int(hotspots[-1].get("task_id_start") or -1) == hotspot["task_id_start"]:
        hotspots[-1] = hotspot
    else:
        hotspots.append(hotspot)
    state["hotspots"] = hotspots
    quarantine = list(state.get("quarantine_ranges") or [])
    if quarantine and quarantine[-1].get("family") == hotspot["family"] and int(quarantine[-1].get("task_id_start") or -1) == hotspot["task_id_start"]:
        quarantine[-1] = {
            "family": hotspot["family"],
            "task_id_start": hotspot["task_id_start"],
            "task_id_end": hotspot["task_id_end"],
            "reason": f"family_streak>={threshold}",
        }
    else:
        quarantine.append(
            {
                "family": hotspot["family"],
                "task_id_start": hotspot["task_id_start"],
                "task_id_end": hotspot["task_id_end"],
                "reason": f"family_streak>={threshold}",
            }
        )
    state["quarantine_ranges"] = quarantine
    return state


def _reset_family_streak(state: dict[str, Any]) -> dict[str, Any]:
    state["current_family"] = ""
    state["current_signature"] = ""
    state["current_streak"] = 0
    state["current_range_start"] = None
    state["current_range_end"] = None
    return state


def _update_rolling_family_state(
    *,
    state: dict[str, Any],
    shard_entry: dict[str, Any],
    shard_summary: dict[str, Any] | None,
    shard_index: int,
) -> dict[str, Any]:
    threshold = max(1, int(state.get("streak_threshold") or 1))
    for event in _extract_family_events_from_summary(shard_summary):
        task_id = int(event.get("task_id") or 0)
        family = str(event.get("family") or "")
        signature = str(event.get("signature") or "")
        current_family = str(state.get("current_family") or "")
        if family and family == current_family:
            state["current_streak"] = int(state.get("current_streak") or 0) + 1
            state["current_range_end"] = task_id
            if signature:
                state["current_signature"] = signature
        else:
            state = _append_family_hotspot(state)
            state = _reset_family_streak(state)
            if family:
                state["current_family"] = family
                state["current_signature"] = signature
                state["current_streak"] = 1
                state["current_range_start"] = task_id
                state["current_range_end"] = task_id

        if family and int(state.get("current_streak") or 0) >= threshold:
            state = _append_family_hotspot(state)
            if not bool(state.get("triggered")):
                policy = str(state.get("policy") or "off")
                if policy in {"warn", "stop"}:
                    state["triggered"] = True
                    state["trigger_shard_index"] = int(shard_index)
                    state["action"] = policy
                    state["trigger_reason"] = (
                        f"extract_family={family} streak={int(state.get('current_streak') or 0)} "
                        f">= threshold={threshold}"
                    )
                    warnings = list(state.get("warnings") or [])
                    warnings.append(
                        {
                            "shard_index": int(shard_index),
                            "action": policy,
                            "family": family,
                            "task_id_start": int(state.get("current_range_start") or task_id),
                            "task_id_end": int(state.get("current_range_end") or task_id),
                            "reason": str(state.get("trigger_reason") or ""),
                        }
                    )
                    state["warnings"] = warnings
    return state


def _apply_timeout_backoff(
    *,
    state: dict[str, Any],
    shard_entry: dict[str, Any],
    args: argparse.Namespace,
    shard_index: int,
) -> dict[str, Any]:
    observed = int(shard_entry.get("extract_observed_tasks") or 0)
    timeout_rate = float(shard_entry.get("extract_timeout_rate") or 0.0)
    if observed < max(1, int(args.rolling_timeout_backoff_min_observed_tasks)):
        return state
    if timeout_rate < float(args.rolling_timeout_backoff_threshold):
        return state

    previous_timeout = state.get("current_llm_timeout_sec")
    if previous_timeout is None:
        previous_timeout = int(args.llm_timeout_sec) if args.llm_timeout_sec is not None else int(_LANE._profile_step_llm_timeout_sec(_repo_root(), step_name="extract", delivery_profile=str(args.delivery_profile)))
    next_timeout = min(
        int(args.rolling_timeout_backoff_max_llm_timeout_sec),
        int(previous_timeout) + int(args.rolling_timeout_backoff_sec),
    )
    previous_shard_size = int(state.get("current_max_tasks_per_shard") or int(args.max_tasks_per_shard))
    next_shard_size = max(
        1,
        min(
            previous_shard_size,
            int(math.floor(previous_shard_size * float(args.rolling_shard_reduction_factor))),
        ),
    )
    if next_shard_size == previous_shard_size and next_timeout == int(previous_timeout):
        return state

    history = list(state.get("backoff_history") or [])
    history.append(
        {
            "shard_index": int(shard_index),
            "reason": f"extract_timeout_rate={timeout_rate:.3f} >= threshold={float(args.rolling_timeout_backoff_threshold):.3f}",
            "previous_llm_timeout_sec": int(previous_timeout),
            "next_llm_timeout_sec": int(next_timeout),
            "previous_max_tasks_per_shard": int(previous_shard_size),
            "next_max_tasks_per_shard": int(next_shard_size),
        }
    )
    state["current_llm_timeout_sec"] = int(next_timeout)
    state["current_max_tasks_per_shard"] = int(next_shard_size)
    state["backoff_adjustment_count"] = int(state.get("backoff_adjustment_count") or 0) + 1
    state["backoff_history"] = history
    return state


def _update_rolling_extract_state(
    *,
    state: dict[str, Any],
    shard_entry: dict[str, Any],
    shard_index: int,
) -> dict[str, Any]:
    observed = int(shard_entry.get("extract_observed_tasks") or 0)
    failed = int(shard_entry.get("extract_failed_tasks") or 0)
    state["observed_tasks"] = int(state.get("observed_tasks") or 0) + observed
    state["failed_tasks"] = int(state.get("failed_tasks") or 0) + failed
    total_observed = int(state.get("observed_tasks") or 0)
    total_failed = int(state.get("failed_tasks") or 0)
    state["fail_rate"] = (float(total_failed) / float(total_observed)) if total_observed > 0 else 0.0

    if bool(state.get("triggered")):
        return state

    threshold = float(state.get("threshold") or 0.0)
    min_observed = int(state.get("min_observed_tasks") or 0)
    if total_observed < max(1, min_observed):
        return state
    if float(state.get("fail_rate") or 0.0) < threshold:
        return state

    policy = str(state.get("policy") or "off")
    state["triggered"] = True
    state["trigger_shard_index"] = int(shard_index)
    state["trigger_reason"] = (
        f"extract_fail_rate={float(state.get('fail_rate') or 0.0):.3f} "
        f">= threshold={threshold:.3f} after observed={total_observed}"
    )
    if policy == "degrade":
        state["action"] = "degrade"
        state["degraded_mode_active"] = True
    elif policy == "stop":
        state["action"] = "stop"
    elif policy == "warn":
        state["action"] = "warn"
    else:
        state["action"] = "none"
    warnings = list(state.get("warnings") or [])
    warnings.append(
        {
            "shard_index": int(shard_index),
            "action": str(state.get("action") or "none"),
            "reason": str(state.get("trigger_reason") or ""),
        }
    )
    state["warnings"] = warnings
    return state


def _summarize_shard_results(shards: list[dict[str, Any]]) -> dict[str, int]:
    counter: dict[str, int] = {}
    for shard in shards:
        status = str(shard.get("status") or "unknown")
        counter[status] = counter.get(status, 0) + 1
    return counter


def _merge_outputs(root: Path, out_dir: Path, shard_entries: list[dict[str, Any]]) -> dict[str, Any] | None:
    summary_paths: list[Path] = []
    for shard in shard_entries:
        if not bool(shard.get("summary_exists")):
            continue
        summary_paths.append(root / str(shard.get("summary_path")))
    if not summary_paths:
        return None
    merged = _MERGE.merge_summaries(root, summary_paths)
    if hasattr(_LANE, "_rebuild_counts"):
        _LANE._rebuild_counts(merged)
    merged["merged_by"] = "run_single_task_light_lane_batch"
    merged["source_summary_count"] = len(summary_paths)
    merged_dir = out_dir / "merged"
    merged_dir.mkdir(parents=True, exist_ok=True)
    merged_path = merged_dir / "summary.json"
    _write_json(merged_path, merged)
    return {
        "path": _relative_to_root(root, merged_path),
        "payload": merged,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Coordinate workflow 5.1 light-lane runs across isolated shards, then merge summaries.")
    parser.add_argument(
        "--batch-preset",
        default="none",
        choices=sorted(_BATCH_PRESETS.keys()),
        help="Recommended batch preset. Explicit flags still override preset values.",
    )
    parser.add_argument("--task-ids", default="", help="Optional CSV task ids override (e.g. 12,14,21).")
    parser.add_argument("--task-id-start", type=int, default=1)
    parser.add_argument("--task-id-end", type=int, default=0, help="0 means until max task id.")
    parser.add_argument("--max-tasks", type=int, default=0, help="0 means all selected tasks.")
    parser.add_argument("--max-tasks-per-shard", type=int, default=20, help="Maximum task count per shard.")
    parser.add_argument("--timeout-sec", type=int, default=None, help="Wrapper timeout per step in seconds.")
    parser.add_argument("--llm-timeout-sec", type=int, default=None, help="Forwarded inner timeout for LLM-backed 5.1 steps.")
    parser.add_argument("--out-dir", default="", help="Output directory. Default: logs/ci/<date>/single-task-light-lane-v2-batch")
    parser.add_argument("--no-resume", action="store_true", help="Pass through --no-resume to each shard run.")
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
        help="Pass-through fill-refs mode for each shard.",
    )
    parser.add_argument(
        "--downstream-on-extract-fail",
        default="auto",
        choices=["auto", "continue", "skip-soft", "skip-all"],
        help="Pass-through downstream behavior after extract fails.",
    )
    parser.add_argument(
        "--downstream-on-extract-family-fail",
        default="auto",
        choices=["auto", "off", "continue", "skip-soft", "skip-all"],
        help="Pass-through family-aware downstream behavior after extract fails.",
    )
    parser.add_argument(
        "--batch-lane",
        default="extract-first",
        choices=["auto", "standard", "extract-first"],
        help="Per-shard lane style. Default keeps extract-first for batch runs.",
    )
    parser.add_argument(
        "--resume-failed-task-from",
        default="first-failed-step",
        choices=["always-rerun", "first-failed-step"],
        help="When resuming inside one shard, rerun all steps or restart from first failed step.",
    )
    parser.add_argument("--stop-on-step-failure", action="store_true", help="Pass through --stop-on-step-failure to shard runs.")
    parser.add_argument("--no-align-apply", action="store_true", help="Do not pass --apply to align step (read-only mode).")
    parser.add_argument(
        "--delivery-profile",
        default="fast-ship",
        choices=["playable-ea", "fast-ship", "standard"],
        help="Delivery profile for light-lane LLM steps.",
    )
    parser.add_argument("--self-check", action="store_true", help="Print resolved shard plan, write summary.json, then exit.")
    parser.add_argument(
        "--rolling-extract-policy",
        default="warn",
        choices=["off", "warn", "degrade", "stop"],
        help="Rolling policy after cumulative extract failure rate crosses threshold.",
    )
    parser.add_argument(
        "--rolling-extract-rate-threshold",
        type=float,
        default=0.6,
        help="Trigger rolling extract policy when cumulative extract fail rate >= threshold.",
    )
    parser.add_argument(
        "--rolling-extract-min-observed-tasks",
        type=int,
        default=12,
        help="Minimum observed extract tasks before evaluating rolling extract policy.",
    )
    parser.add_argument(
        "--rolling-family-policy",
        default="off",
        choices=["off", "warn", "stop"],
        help="Rolling policy for repeated extract failure families across consecutive tasks.",
    )
    parser.add_argument(
        "--rolling-family-streak-threshold",
        type=int,
        default=5,
        help="Trigger rolling family policy when one extract failure family repeats across this many consecutive tasks.",
    )
    parser.add_argument(
        "--rolling-timeout-backoff-threshold",
        type=float,
        default=0.5,
        help="If one shard's extract timeout rate >= threshold, increase next shard timeout and reduce next shard size.",
    )
    parser.add_argument(
        "--rolling-timeout-backoff-min-observed-tasks",
        type=int,
        default=4,
        help="Minimum extract-observed tasks in one shard before timeout backoff can trigger.",
    )
    parser.add_argument(
        "--rolling-timeout-backoff-sec",
        type=int,
        default=180,
        help="LLM timeout increment for the next shard after timeout backoff triggers.",
    )
    parser.add_argument(
        "--rolling-timeout-backoff-max-llm-timeout-sec",
        type=int,
        default=1200,
        help="Upper bound for LLM timeout after repeated timeout backoff.",
    )
    parser.add_argument(
        "--rolling-shard-reduction-factor",
        type=float,
        default=0.5,
        help="Next shard size multiplier after timeout backoff triggers.",
    )
    return parser


def main() -> int:
    argv = list(sys.argv[1:])
    args = build_parser().parse_args()
    args = _apply_batch_preset(args, argv)
    root = _repo_root()
    selected = _selected_task_ids(root, args)
    if not selected:
        print("SINGLE_TASK_LIGHT_LANE_BATCH status=fail reason=no_selected_tasks")
        return 2
    if int(args.max_tasks_per_shard) <= 0:
        print("SINGLE_TASK_LIGHT_LANE_BATCH status=fail reason=invalid_max_tasks_per_shard")
        return 2

    out_dir = Path(args.out_dir) if str(args.out_dir).strip() else _default_out_dir(root)
    shards_root = out_dir / "shards"
    initial_shard_task_groups = _split_task_ids(selected, int(args.max_tasks_per_shard))
    summary_path = out_dir / "summary.json"

    summary: dict[str, Any] = {
        "cmd": "run_single_task_light_lane_batch",
        "started_at": dt.datetime.now().isoformat(timespec="seconds"),
        "status": "running",
        "out_dir": _relative_to_root(root, out_dir),
        "selected_task_ids": [int(task_id) for task_id in selected],
        "batch_preset": str(args.batch_preset),
        "batch_preset_applied": dict(getattr(args, "batch_preset_applied", {}) or {}),
        "task_id_start": int(selected[0]),
        "task_id_end": int(selected[-1]),
        "task_count": len(selected),
        "max_tasks_per_shard": int(args.max_tasks_per_shard),
        "delivery_profile": str(args.delivery_profile),
        "batch_lane": str(args.batch_lane),
        "fill_refs_mode": str(args.fill_refs_mode),
        "downstream_on_extract_fail": str(args.downstream_on_extract_fail),
        "downstream_on_extract_family_fail": str(args.downstream_on_extract_family_fail),
        "resume_failed_task_from": str(args.resume_failed_task_from),
        "rolling_extract": _new_rolling_extract_state(args),
        "rolling_family": _new_rolling_family_state(args),
        "shard_count": len(initial_shard_task_groups),
        "shards": [
            {
                "index": idx,
                "name": _build_shard_name(idx, shard_task_ids),
                "task_ids": [int(task_id) for task_id in shard_task_ids],
                "task_id_start": int(shard_task_ids[0]),
                "task_id_end": int(shard_task_ids[-1]),
                "task_count": len(shard_task_ids),
                "out_dir": _relative_to_root(root, shards_root / _build_shard_name(idx, shard_task_ids)),
            }
            for idx, shard_task_ids in enumerate(initial_shard_task_groups, start=1)
        ],
    }

    if bool(args.self_check):
        summary["status"] = "ok"
        summary["finished_at"] = dt.datetime.now().isoformat(timespec="seconds")
        _write_json(summary_path, summary)
        print(
            "SINGLE_TASK_LIGHT_LANE_BATCH_SELF_CHECK "
            f"status=ok tasks={len(selected)} shards={len(initial_shard_task_groups)} "
            f"range=T{selected[0]}-T{selected[-1]} out={_relative_to_root(root, summary_path)}"
        )
        return 0

    shard_entries: list[dict[str, Any]] = []
    skipped_planned_shards: list[dict[str, Any]] = []
    rolling_extract_state = dict(summary.get("rolling_extract") or _new_rolling_extract_state(args))
    rolling_family_state = dict(summary.get("rolling_family") or _new_rolling_family_state(args))
    pending_task_ids = list(selected)
    planned_shards: list[dict[str, Any]] = []
    shard_index = 0
    while pending_task_ids:
        shard_index += 1
        current_shard_size = _compute_next_shard_size(rolling_extract_state, int(args.max_tasks_per_shard))
        shard_task_ids = list(pending_task_ids[:current_shard_size])
        pending_task_ids = list(pending_task_ids[current_shard_size:])
        planned_shards.append(
            {
                "index": shard_index,
                "name": _build_shard_name(shard_index, shard_task_ids),
                "task_ids": [int(task_id) for task_id in shard_task_ids],
                "task_id_start": int(shard_task_ids[0]),
                "task_id_end": int(shard_task_ids[-1]),
                "task_count": len(shard_task_ids),
                "out_dir": _relative_to_root(root, shards_root / _build_shard_name(shard_index, shard_task_ids)),
            }
        )
        effective_args = _rolling_extract_effective_args(args, rolling_extract_state)
        entry = _run_shard(
            root=root,
            args=effective_args,
            shard_task_ids=shard_task_ids,
            shard_index=shard_index,
            shard_count=max(shard_index, shard_index + (1 if pending_task_ids else 0)),
            shards_root=shards_root,
        )
        entry["rolling_extract_mode"] = "degraded" if bool(rolling_extract_state.get("degraded_mode_active")) else "normal"
        shard_entries.append(entry)
        shard_summary = _load_json(root / str(entry.get("summary_path")))
        rolling_extract_state = _apply_timeout_backoff(
            state=rolling_extract_state,
            shard_entry=entry,
            args=args,
            shard_index=shard_index,
        )
        rolling_extract_state = _update_rolling_extract_state(
            state=rolling_extract_state,
            shard_entry=entry,
            shard_index=shard_index,
        )
        rolling_family_state = _update_rolling_family_state(
            state=rolling_family_state,
            shard_entry=entry,
            shard_summary=shard_summary,
            shard_index=shard_index,
        )
        summary["shards"] = shard_entries
        summary["planned_shards"] = planned_shards
        summary["last_shard_index"] = shard_index
        summary["last_task_id"] = int(shard_task_ids[-1])
        summary["last_updated_at"] = dt.datetime.now().isoformat(timespec="seconds")
        summary["shard_status_counts"] = _summarize_shard_results(shard_entries)
        summary["rolling_extract"] = rolling_extract_state
        summary["rolling_family"] = rolling_family_state
        summary["family_hotspots"] = list(rolling_family_state.get("hotspots") or [])
        summary["quarantine_ranges"] = list(rolling_family_state.get("quarantine_ranges") or [])
        summary["shard_count"] = len(planned_shards) + (1 if pending_task_ids else 0)
        _write_json(summary_path, summary)
        stop_reason = ""
        if str(rolling_family_state.get("action") or "") == "stop" and bool(rolling_family_state.get("triggered")):
            stop_reason = str(rolling_family_state.get("trigger_reason") or "rolling_family_stop")
        elif str(rolling_extract_state.get("action") or "") == "stop" and bool(rolling_extract_state.get("triggered")):
            stop_reason = str(rolling_extract_state.get("trigger_reason") or "rolling_extract_stop")
        if stop_reason:
            remaining = list(pending_task_ids)
            pending_index = shard_index + 1
            while remaining:
                next_size = _compute_next_shard_size(rolling_extract_state, int(args.max_tasks_per_shard))
                next_ids = list(remaining[:next_size])
                remaining = list(remaining[next_size:])
                skipped_planned_shards.append(
                    {
                        "index": pending_index,
                        "name": _build_shard_name(pending_index, next_ids),
                        "task_ids": [int(task_id) for task_id in next_ids],
                        "task_id_start": int(next_ids[0]),
                        "task_id_end": int(next_ids[-1]),
                        "task_count": len(next_ids),
                        "status": "skipped",
                        "skip_reason": stop_reason,
                    }
                )
                pending_index += 1
            break

    if skipped_planned_shards:
        summary["skipped_planned_shards"] = skipped_planned_shards
    rolling_family_state = _append_family_hotspot(rolling_family_state)
    summary["rolling_family"] = rolling_family_state
    summary["family_hotspots"] = list(rolling_family_state.get("hotspots") or [])
    summary["quarantine_ranges"] = list(rolling_family_state.get("quarantine_ranges") or [])
    summary["shard_count"] = len(shard_entries) + len(skipped_planned_shards)

    merged = _merge_outputs(root, out_dir, shard_entries)
    if merged is not None:
        merged_payload = merged["payload"]
        summary["merged_summary_path"] = str(merged["path"])
        summary["merge_validation"] = merged_payload.get("validation")
        summary["covered_count"] = int(merged_payload.get("covered_count") or 0)
        summary["missing_count"] = int(merged_payload.get("missing_count") or 0)
        summary["passed_count"] = int(merged_payload.get("passed_count") or 0)
        summary["failed_count"] = int(merged_payload.get("failed_count") or 0)
        for key in [
            "missing_task_ids",
            "failed_task_ids",
            "passed_task_ids",
            "failed_first_step_counter",
            "failure_category_counts",
            "failure_category_task_ids",
            "extract_fail_bucket_counts",
            "extract_fail_bucket_task_ids",
            "extract_fail_signature_counts",
            "extract_fail_signature_task_ids",
            "extract_fail_top_signatures",
            "extract_fail_family_counts",
            "extract_fail_family_task_ids",
            "extract_fail_top_families",
            "prompt_trimmed_task_ids",
            "semantic_gate_budget_hits",
            "overridden_task_ids",
        ]:
            if key in merged_payload:
                summary[key] = merged_payload.get(key)
        summary["extract_family_recommended_actions"] = _build_extract_family_recommended_actions(merged_payload)

    shard_rc_failures = [entry for entry in shard_entries if int(entry.get("rc") or 0) not in {0, 1}]
    shard_missing_summary = [entry for entry in shard_entries if not bool(entry.get("summary_exists"))]
    merged_missing = int(summary.get("missing_count") or 0) > 0
    merge_hard_issues = int(((summary.get("merge_validation") or {}).get("hard_issue_count") or 0))
    summary["status"] = (
        "ok"
        if not shard_rc_failures and not shard_missing_summary and not merged_missing and merge_hard_issues == 0 and int(summary.get("failed_count") or 0) == 0
        else "fail"
    )
    summary["finished_at"] = dt.datetime.now().isoformat(timespec="seconds")
    _write_json(summary_path, summary)
    print(
        "SINGLE_TASK_LIGHT_LANE_BATCH "
        f"status={summary['status']} shards={len(shard_entries)} tasks={len(selected)} "
        f"covered={summary.get('covered_count', 0)} failed={summary.get('failed_count', 0)} "
        f"out={_relative_to_root(root, summary_path)}"
    )
    return 0 if summary["status"] == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
