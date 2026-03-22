from __future__ import annotations

import datetime as dt
import json
from pathlib import Path
from typing import Any

from _util import ensure_dir, repo_root


STEP_SEQUENCE = ("sc-test", "sc-acceptance-check", "sc-llm-review")
RUN_STATUSES = {"running", "ok", "fail", "aborted"}
STEP_STATUSES = {"pending", "planned", "skipped", "ok", "fail"}

def _now_iso() -> str:
    return dt.datetime.now().isoformat(timespec="seconds")

def marathon_state_path(out_dir: Path) -> Path:
    return out_dir / "marathon-state.json"

def _load_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None

def _step_template() -> dict[str, Any]:
    return {
        "status": "pending",
        "attempt_count": 0,
        "last_rc": 0,
        "cmd": [],
        "log": "",
        "reported_out_dir": "",
        "summary_file": "",
        "updated_at": "",
    }

def _normalize_int(value: Any, *, default: int = 0, minimum: int | None = None) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        parsed = default
    if minimum is not None:
        parsed = max(minimum, parsed)
    return parsed

def _normalize_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value or "").strip().lower() in {"1", "true", "yes", "on"}


def _normalize_step_status(value: Any) -> str:
    status = str(value or "").strip().lower()
    return status if status in STEP_STATUSES else "pending"


def _ensure_steps_map(state: dict[str, Any]) -> dict[str, dict[str, Any]]:
    raw = state.get("steps")
    steps: dict[str, dict[str, Any]] = raw if isinstance(raw, dict) else {}
    for name in STEP_SEQUENCE:
        current = steps.get(name)
        if not isinstance(current, dict):
            current = {}
        merged = _step_template()
        merged.update(current)
        merged["status"] = _normalize_step_status(merged.get("status"))
        merged["attempt_count"] = _normalize_int(merged.get("attempt_count"), minimum=0)
        merged["last_rc"] = _normalize_int(merged.get("last_rc"), minimum=0)
        merged["cmd"] = [str(x) for x in (merged.get("cmd") or []) if str(x).strip()]
        for key in ("log", "reported_out_dir", "summary_file", "updated_at"):
            merged[key] = str(merged.get(key) or "")
        steps[name] = merged
    state["steps"] = steps
    return steps


def _normalize_state_defaults(state: dict[str, Any]) -> dict[str, Any]:
    state["resume_count"] = _normalize_int(state.get("resume_count"), default=1, minimum=1)
    state["max_step_retries"] = _normalize_int(state.get("max_step_retries"), minimum=0)
    state["max_wall_time_sec"] = _normalize_int(state.get("max_wall_time_sec"), minimum=0)
    state["fork_depth"] = _normalize_int(state.get("fork_depth"), minimum=0)
    state["wall_time_exceeded"] = _normalize_bool(state.get("wall_time_exceeded"))
    state["context_refresh_needed"] = _normalize_bool(state.get("context_refresh_needed"))
    state["stop_reason"] = str(state.get("stop_reason") or "")
    state["aborted_reason"] = str(state.get("aborted_reason") or "")
    state["forked_from_run_id"] = str(state.get("forked_from_run_id") or "")
    state["forked_from_out_dir"] = str(state.get("forked_from_out_dir") or "")
    reasons = state.get("context_refresh_reasons")
    state["context_refresh_reasons"] = [str(x) for x in reasons] if isinstance(reasons, list) else []
    thresholds = state.get("context_refresh_thresholds")
    thresholds_dict = thresholds if isinstance(thresholds, dict) else {}
    state["context_refresh_thresholds"] = {
        "failure_threshold": _normalize_int(thresholds_dict.get("failure_threshold"), minimum=0),
        "resume_threshold": _normalize_int(thresholds_dict.get("resume_threshold"), minimum=0),
        "diff_lines_threshold": _normalize_int(thresholds_dict.get("diff_lines_threshold"), minimum=0),
        "diff_categories_threshold": _normalize_int(thresholds_dict.get("diff_categories_threshold"), minimum=0),
    }
    diff_stats = state.get("diff_stats")
    diff_dict = diff_stats if isinstance(diff_stats, dict) else {}
    def _list(path_block: Any, key: str) -> list[str]:
        block = path_block if isinstance(path_block, dict) else {}
        value = block.get(key)
        return sorted({str(item).strip() for item in value}) if isinstance(value, list) else []
    state["diff_stats"] = {
        "baseline": {
            "files_changed": _normalize_int(((diff_dict.get("baseline") or {}) if isinstance(diff_dict.get("baseline"), dict) else {}).get("files_changed"), minimum=0),
            "untracked_files": _normalize_int(((diff_dict.get("baseline") or {}) if isinstance(diff_dict.get("baseline"), dict) else {}).get("untracked_files"), minimum=0),
            "lines_added": _normalize_int(((diff_dict.get("baseline") or {}) if isinstance(diff_dict.get("baseline"), dict) else {}).get("lines_added"), minimum=0),
            "lines_deleted": _normalize_int(((diff_dict.get("baseline") or {}) if isinstance(diff_dict.get("baseline"), dict) else {}).get("lines_deleted"), minimum=0),
            "total_lines": _normalize_int(((diff_dict.get("baseline") or {}) if isinstance(diff_dict.get("baseline"), dict) else {}).get("total_lines"), minimum=0),
            "categories": _list(diff_dict.get("baseline"), "categories"),
            "axes": _list(diff_dict.get("baseline"), "axes"),
        },
        "current": {
            "files_changed": _normalize_int(((diff_dict.get("current") or {}) if isinstance(diff_dict.get("current"), dict) else {}).get("files_changed"), minimum=0),
            "untracked_files": _normalize_int(((diff_dict.get("current") or {}) if isinstance(diff_dict.get("current"), dict) else {}).get("untracked_files"), minimum=0),
            "lines_added": _normalize_int(((diff_dict.get("current") or {}) if isinstance(diff_dict.get("current"), dict) else {}).get("lines_added"), minimum=0),
            "lines_deleted": _normalize_int(((diff_dict.get("current") or {}) if isinstance(diff_dict.get("current"), dict) else {}).get("lines_deleted"), minimum=0),
            "total_lines": _normalize_int(((diff_dict.get("current") or {}) if isinstance(diff_dict.get("current"), dict) else {}).get("total_lines"), minimum=0),
            "categories": _list(diff_dict.get("current"), "categories"),
            "axes": _list(diff_dict.get("current"), "axes"),
        },
        "growth": {
            "files_changed": _normalize_int(((diff_dict.get("growth") or {}) if isinstance(diff_dict.get("growth"), dict) else {}).get("files_changed"), minimum=0),
            "untracked_files": _normalize_int(((diff_dict.get("growth") or {}) if isinstance(diff_dict.get("growth"), dict) else {}).get("untracked_files"), minimum=0),
            "lines_added": _normalize_int(((diff_dict.get("growth") or {}) if isinstance(diff_dict.get("growth"), dict) else {}).get("lines_added"), minimum=0),
            "lines_deleted": _normalize_int(((diff_dict.get("growth") or {}) if isinstance(diff_dict.get("growth"), dict) else {}).get("lines_deleted"), minimum=0),
            "total_lines": _normalize_int(((diff_dict.get("growth") or {}) if isinstance(diff_dict.get("growth"), dict) else {}).get("total_lines"), minimum=0),
            "new_categories": _list(diff_dict.get("growth"), "new_categories"),
            "new_axes": _list(diff_dict.get("growth"), "new_axes"),
        },
    }
    state["created_at"] = str(state.get("created_at") or _now_iso())
    state["updated_at"] = str(state.get("updated_at") or state["created_at"])
    return state


def _recompute_run_state(state: dict[str, Any], *, fallback_status: str = "running") -> dict[str, Any]:
    state = _normalize_state_defaults(state)
    steps = _ensure_steps_map(state)
    last_completed = ""
    last_failed = ""
    next_step = ""
    for name in STEP_SEQUENCE:
        step = steps[name]
        status = _normalize_step_status(step.get("status"))
        if status in {"ok", "skipped"}:
            last_completed = name
            continue
        if status == "fail":
            last_failed = name
            next_step = name
            break
        next_step = name
        break

    run_status = str(state.get("status") or fallback_status).strip().lower()
    if run_status == "aborted":
        next_step = ""
    elif last_failed or str(state.get("stop_reason") or "").strip().lower() == "wall_time_exceeded":
        run_status = "fail"
    elif not next_step:
        run_status = "ok"
    elif run_status not in RUN_STATUSES or (run_status == "ok" and next_step):
        run_status = fallback_status

    state["status"] = run_status if run_status in RUN_STATUSES else fallback_status
    state["last_completed_step"] = last_completed
    state["last_failed_step"] = last_failed
    state["next_step_name"] = next_step
    state["updated_at"] = _now_iso()
    return state


def _summary_steps_by_name(summary: dict[str, Any]) -> dict[str, dict[str, Any]]:
    latest_by_name: dict[str, dict[str, Any]] = {}
    for item in summary.get("steps") or []:
        if isinstance(item, dict):
            name = str(item.get("name") or "").strip()
            if name in STEP_SEQUENCE:
                latest_by_name[name] = item
    return latest_by_name


def build_initial_state(
    *,
    task_id: str,
    run_id: str,
    requested_run_id: str,
    max_step_retries: int,
    max_wall_time_sec: int,
    summary: dict[str, Any],
    resume_count: int = 1,
) -> dict[str, Any]:
    state: dict[str, Any] = {
        "schema_version": "1.0.0",
        "task_id": task_id,
        "run_id": run_id,
        "requested_run_id": requested_run_id,
        "status": "running",
        "resume_count": max(1, int(resume_count)),
        "max_step_retries": max(0, int(max_step_retries)),
        "max_wall_time_sec": max(0, int(max_wall_time_sec)),
        "last_completed_step": "",
        "last_failed_step": "",
        "next_step_name": STEP_SEQUENCE[0],
        "stop_reason": "",
        "aborted_reason": "",
        "wall_time_exceeded": False,
        "forked_from_run_id": "",
        "forked_from_out_dir": "",
        "fork_depth": 0,
        "context_refresh_needed": False,
        "context_refresh_reasons": [],
        "context_refresh_thresholds": {"failure_threshold": 0, "resume_threshold": 0, "diff_lines_threshold": 0, "diff_categories_threshold": 0},
        "diff_stats": {
            "baseline": {"files_changed": 0, "untracked_files": 0, "lines_added": 0, "lines_deleted": 0, "total_lines": 0, "categories": [], "axes": []},
            "current": {"files_changed": 0, "untracked_files": 0, "lines_added": 0, "lines_deleted": 0, "total_lines": 0, "categories": [], "axes": []},
            "growth": {"files_changed": 0, "untracked_files": 0, "lines_added": 0, "lines_deleted": 0, "total_lines": 0, "new_categories": [], "new_axes": []},
        },
        "created_at": _now_iso(),
        "updated_at": _now_iso(),
        "steps": {},
    }
    steps = _ensure_steps_map(state)
    for name, step in _summary_steps_by_name(summary).items():
        status = _normalize_step_status(step.get("status"))
        steps[name].update(
            {
                "status": status,
                "attempt_count": 1 if status in {"ok", "fail"} else 0,
                "last_rc": _normalize_int(step.get("rc"), minimum=0),
                "cmd": [str(x) for x in (step.get("cmd") or []) if str(x).strip()],
                "log": str(step.get("log") or ""),
                "reported_out_dir": str(step.get("reported_out_dir") or ""),
                "summary_file": str(step.get("summary_file") or ""),
                "updated_at": _now_iso(),
            }
        )
    return _recompute_run_state(state, fallback_status=str(summary.get("status") or "running"))


def build_forked_summary(source_summary: dict[str, Any], *, new_run_id: str, requested_run_id: str) -> dict[str, Any]:
    cloned_steps: list[dict[str, Any]] = []
    for name in STEP_SEQUENCE:
        step = _summary_steps_by_name(source_summary).get(name)
        if not isinstance(step, dict):
            break
        status = _normalize_step_status(step.get("status"))
        if status in {"ok", "skipped"}:
            cloned_steps.append(dict(step))
            continue
        break
    return {
        "cmd": "sc-review-pipeline",
        "task_id": str(source_summary.get("task_id") or ""),
        "requested_run_id": requested_run_id,
        "run_id": new_run_id,
        "allow_overwrite": False,
        "force_new_run_id": False,
        "status": "ok",
        "steps": cloned_steps,
    }


def build_forked_state(
    *,
    source_out_dir: Path,
    source_summary: dict[str, Any],
    source_state: dict[str, Any] | None,
    new_run_id: str,
    requested_run_id: str,
    max_step_retries: int,
    max_wall_time_sec: int,
) -> tuple[dict[str, Any], dict[str, Any]]:
    summary = build_forked_summary(source_summary, new_run_id=new_run_id, requested_run_id=requested_run_id)
    task_id = str(summary.get("task_id") or "")
    fork_depth = _normalize_int((source_state or {}).get("fork_depth"), minimum=0) + 1
    state = build_initial_state(
        task_id=task_id,
        run_id=new_run_id,
        requested_run_id=requested_run_id,
        max_step_retries=max_step_retries,
        max_wall_time_sec=max_wall_time_sec,
        summary=summary,
    )
    state["forked_from_run_id"] = str(source_summary.get("run_id") or "")
    state["forked_from_out_dir"] = str(source_out_dir)
    state["fork_depth"] = fork_depth
    return summary, _recompute_run_state(state, fallback_status="running")


def load_marathon_state(out_dir: Path) -> dict[str, Any] | None:
    state = _load_json(marathon_state_path(out_dir))
    if not isinstance(state, dict):
        return None
    return _recompute_run_state(state, fallback_status=str(state.get("status") or "running"))


def save_marathon_state(out_dir: Path, state: dict[str, Any]) -> Path:
    path = marathon_state_path(out_dir)
    ensure_dir(path.parent)
    path.write_text(json.dumps(_recompute_run_state(state), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def record_step_result(state: dict[str, Any], step: dict[str, Any]) -> dict[str, Any]:
    steps = _ensure_steps_map(state)
    name = str(step.get("name") or "").strip()
    if name not in STEP_SEQUENCE:
        return _recompute_run_state(state)
    target = steps[name]
    status = _normalize_step_status(step.get("status"))
    if status in {"ok", "fail"}:
        target["attempt_count"] = int(target.get("attempt_count") or 0) + 1
    target.update(
        {
            "status": status,
            "last_rc": _normalize_int(step.get("rc"), minimum=0),
            "cmd": [str(x) for x in (step.get("cmd") or []) if str(x).strip()],
            "log": str(step.get("log") or ""),
            "reported_out_dir": str(step.get("reported_out_dir") or ""),
            "summary_file": str(step.get("summary_file") or ""),
            "updated_at": _now_iso(),
        }
    )
    if status != "fail":
        state["stop_reason"] = ""
        state["wall_time_exceeded"] = False
    return _recompute_run_state(state, fallback_status="running")


def can_retry_failed_step(state: dict[str, Any], step_name: str) -> bool:
    steps = _ensure_steps_map(state)
    target = steps.get(step_name) or {}
    if _normalize_step_status(target.get("status")) != "fail":
        return False
    attempt_count = _normalize_int(target.get("attempt_count"), minimum=0)
    max_step_retries = _normalize_int(state.get("max_step_retries"), minimum=0)
    return attempt_count <= max_step_retries


def step_is_already_complete(state: dict[str, Any], step_name: str) -> bool:
    steps = _ensure_steps_map(state)
    status = _normalize_step_status((steps.get(step_name) or {}).get("status"))
    return status in {"ok", "skipped"}


def mark_aborted(state: dict[str, Any], *, reason: str) -> dict[str, Any]:
    state["status"] = "aborted"
    state["aborted_reason"] = str(reason or "").strip() or "operator_requested"
    state["next_step_name"] = ""
    state["updated_at"] = _now_iso()
    return _recompute_run_state(state, fallback_status="aborted")


def resume_state(
    state: dict[str, Any],
    *,
    max_step_retries: int | None = None,
    max_wall_time_sec: int | None = None,
) -> dict[str, Any]:
    state["resume_count"] = max(1, int(state.get("resume_count") or 1)) + 1
    if max_step_retries is not None:
        state["max_step_retries"] = max(0, int(max_step_retries))
    if max_wall_time_sec is not None:
        state["max_wall_time_sec"] = max(0, int(max_wall_time_sec))
    if str(state.get("status") or "").strip().lower() != "aborted":
        state["status"] = "running"
    state["updated_at"] = _now_iso()
    return _recompute_run_state(state, fallback_status="running")


def resolve_existing_out_dir(*, task_id: str, run_id: str | None, preferred_latest_index: Path | None = None) -> Path | None:
    if preferred_latest_index and preferred_latest_index.exists():
        latest = _load_json(preferred_latest_index) or {}
        latest_task_id = str(latest.get("task_id") or "").strip()
        latest_run_id = str(latest.get("run_id") or "").strip()
        latest_out_dir = Path(str(latest.get("latest_out_dir") or "")).resolve() if latest.get("latest_out_dir") else None
        if latest_task_id == task_id and latest_out_dir and latest_out_dir.exists():
            if not run_id or run_id == latest_run_id:
                return latest_out_dir
    logs_root = repo_root() / "logs" / "ci"
    if run_id:
        matches = sorted(logs_root.glob(f"*/sc-review-pipeline-task-{task_id}-{run_id}"), key=lambda item: item.stat().st_mtime, reverse=True)
        return matches[0] if matches else None
    latest_files = sorted(logs_root.glob(f"*/sc-review-pipeline-task-{task_id}/latest.json"), key=lambda item: item.stat().st_mtime, reverse=True)
    for latest_path in latest_files:
        latest = _load_json(latest_path) or {}
        candidate = Path(str(latest.get("latest_out_dir") or "")).resolve() if latest.get("latest_out_dir") else None
        if candidate and candidate.exists():
            return candidate
    return None
