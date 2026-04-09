#!/usr/bin/env python3
"""Common helpers for project-health scans and dashboard artifacts."""

from __future__ import annotations

import html
import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from _chapter6_recovery_common import chapter6_stop_loss_note as _chapter6_stop_loss_note

PROJECT_HEALTH_KINDS = (
    "detect-project-stage",
    "doctor-project",
    "check-directory-boundaries",
)

TASK_FILES = ("tasks.json", "tasks_back.json", "tasks_gameplay.json")
ALLOWED_BASE_08_FILES = {"08-crosscutting-and-feature-slices.base.md"}
GODOT_PATTERN = re.compile(r"\busing\s+Godot\b|\bGodot\.", re.MULTILINE)
PRD_PATTERN = re.compile(r"\bPRD-[A-Za-z0-9_-]+\b")


def now_local() -> datetime:
    return datetime.now().astimezone()


def today_str(now: datetime | None = None) -> str:
    stamp = now or now_local()
    return stamp.strftime("%Y-%m-%d")


def timestamp_str(now: datetime | None = None) -> str:
    stamp = now or now_local()
    return stamp.strftime("%H%M%S%f")


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def resolve_root(root: Path | str | None = None) -> Path:
    if root is None:
        return repo_root()
    return Path(root).resolve()


def to_posix(path: Path) -> str:
    return str(path).replace("\\", "/")


def repo_rel(path: Path, *, root: Path) -> str:
    try:
        return to_posix(path.resolve().relative_to(root.resolve()))
    except ValueError:
        return to_posix(path.resolve())


def _env_int(name: str, default: int) -> int:
    raw = str(os.environ.get(name) or "").strip()
    if not raw:
        return default
    try:
        return max(0, int(raw))
    except ValueError:
        return default


def _parse_iso8601_soft(value: Any) -> datetime | None:
    text = str(value or "").strip()
    if not text:
        return None
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    return parsed.astimezone() if parsed.tzinfo else parsed.replace(tzinfo=now_local().tzinfo)


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def history_dir(root: Path, *, now: datetime | None = None) -> Path:
    return root / "logs" / "ci" / today_str(now) / "project-health"


def latest_dir(root: Path) -> Path:
    return root / "logs" / "ci" / "project-health"


def task_triplet_paths(root: Path, parent: Path) -> dict[str, Path]:
    return {name: root / parent / name for name in TASK_FILES}


def has_task_triplet(paths: dict[str, Path]) -> bool:
    return all(path.exists() for path in paths.values())


def load_tasks_payload(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = read_json(path)
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(payload, dict):
        return {}
    return payload


def extract_tasks(payload: dict[str, Any]) -> list[dict[str, Any]]:
    candidates = []
    if isinstance(payload.get("tasks"), list):
        candidates = payload["tasks"]
    master = payload.get("master")
    if not candidates and isinstance(master, dict) and isinstance(master.get("tasks"), list):
        candidates = master["tasks"]
    return [item for item in candidates if isinstance(item, dict)]


def task_status_counts(root: Path) -> dict[str, int]:
    payload = load_tasks_payload(root / ".taskmaster" / "tasks" / "tasks.json")
    counts = {"in_progress": 0, "done": 0, "other": 0}
    for item in extract_tasks(payload):
        raw = str(item.get("status", "")).strip().lower().replace("-", "_")
        if raw in {"in_progress", "active", "working"}:
            counts["in_progress"] += 1
        elif raw in {"done", "completed", "closed"}:
            counts["done"] += 1
        else:
            counts["other"] += 1
    return counts


def overlay_indexes(root: Path) -> list[Path]:
    return sorted((root / "docs" / "architecture" / "overlays").glob("*/08/_index.md"))


def contract_files(root: Path) -> list[Path]:
    base = root / "Game.Core" / "Contracts"
    if not base.exists():
        return []
    return sorted(path for path in base.rglob("*.cs") if path.is_file())


def unit_test_files(root: Path) -> list[Path]:
    candidates = []
    for rel in ("Game.Core.Tests", "Tests"):
        base = root / rel
        if not base.exists():
            continue
        candidates.extend(path for path in base.rglob("*.cs") if path.is_file() and not path.name.endswith(".uid"))
    return sorted(set(candidates))


def record_markdown(payload: dict[str, Any]) -> str:
    lines = [
        f"# {payload['kind']}",
        "",
        f"- status: {payload.get('status', 'unknown')}",
        f"- summary: {payload.get('summary', '')}",
        f"- generated_at: {payload.get('generated_at', '')}",
    ]
    if "stage" in payload:
        lines.append(f"- stage: {payload['stage']}")
    if payload.get("history_json"):
        lines.append(f"- history_json: {payload['history_json']}")
    return "\n".join(lines).rstrip() + "\n"


def load_latest_records(root: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for kind in PROJECT_HEALTH_KINDS:
        path = latest_dir(root) / f"{kind}.latest.json"
        if path.exists():
            payload = read_json(path)
            if isinstance(payload, dict):
                records.append(payload)
    return records


def _normalize_report_value(value: Any, *, limit: int = 240) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    return text[:limit]


def _normalize_llm_verdict(value: Any) -> str:
    raw = str(value or "").strip().lower()
    if raw in {"ok", "pass", "passed"}:
        return "OK"
    if raw in {"needs fix", "needs_fix", "need fix", "fail", "failed"}:
        return "Needs Fix"
    return "Unknown"


def _resolve_report_path(raw: Any, *, root: Path) -> Path | None:
    text = str(raw or "").strip()
    if not text:
        return None
    candidate = Path(text)
    if not candidate.is_absolute():
        candidate = (root / candidate).resolve()
    return candidate if candidate.exists() else None




def _derive_clean_state_from_summary(summary_path: Path | None, *, root: Path) -> dict[str, Any]:
    if summary_path is None or not summary_path.exists():
        return {
            "state": "",
            "deterministic_ok": False,
            "llm_status": "",
            "needs_fix_agents": [],
            "unknown_agents": [],
            "timeout_agents": [],
        }
    try:
        summary = read_json(summary_path)
    except Exception:
        return {
            "state": "",
            "deterministic_ok": False,
            "llm_status": "",
            "needs_fix_agents": [],
            "unknown_agents": [],
            "timeout_agents": [],
        }
    steps = summary.get("steps") if isinstance(summary.get("steps"), list) else []
    step_map = {
        str(item.get("name") or "").strip(): item
        for item in steps
        if isinstance(item, dict) and str(item.get("name") or "").strip()
    }
    test_status = str((step_map.get("sc-test") or {}).get("status") or "").strip().lower()
    acceptance_status = str((step_map.get("sc-acceptance-check") or {}).get("status") or "").strip().lower()
    llm_step = step_map.get("sc-llm-review") or {}
    llm_status = str(llm_step.get("status") or "").strip().lower()
    llm_summary_path = _resolve_report_path(llm_step.get("summary_file"), root=root)
    needs_fix_agents: list[str] = []
    unknown_agents: list[str] = []
    timeout_agents: list[str] = []
    if llm_summary_path is not None:
        try:
            llm_summary = read_json(llm_summary_path)
        except Exception:
            llm_summary = {}
        results = llm_summary.get("results") if isinstance(llm_summary.get("results"), list) else []
        for row in results:
            if not isinstance(row, dict):
                continue
            agent = str(row.get("agent") or "").strip()
            details = row.get("details") if isinstance(row.get("details"), dict) else {}
            verdict = _normalize_llm_verdict(details.get("verdict"))
            rc = int(row.get("rc") or 0)
            status = str(row.get("status") or "").strip().lower()
            if verdict == "Needs Fix" and agent:
                needs_fix_agents.append(agent)
            if (verdict == "Unknown" or status not in {"ok", "skipped"} or rc != 0) and agent:
                unknown_agents.append(agent)
            if rc == 124 and agent:
                timeout_agents.append(agent)
    deterministic_ok = test_status == "ok" and acceptance_status == "ok"
    llm_clean = llm_status == "ok" and not needs_fix_agents and not unknown_agents
    if deterministic_ok and llm_clean:
        state = "clean"
    elif deterministic_ok and (needs_fix_agents or unknown_agents or llm_status == "fail"):
        state = "deterministic_ok_llm_not_clean"
    elif deterministic_ok and llm_status == "skipped":
        state = "deterministic_only"
    else:
        state = "not_clean"
    return {
        "state": state,
        "deterministic_ok": deterministic_ok,
        "llm_status": llm_status,
        "needs_fix_agents": sorted(needs_fix_agents),
        "unknown_agents": sorted(set(unknown_agents)),
        "timeout_agents": sorted(set(timeout_agents)),
    }


def _derive_waste_signals_from_summary(summary_path: Path | None, *, root: Path) -> dict[str, bool]:
    if summary_path is None or not summary_path.exists():
        return {"unit_failed_but_engine_lane_ran": False}
    try:
        summary = read_json(summary_path)
    except Exception:
        return {"unit_failed_but_engine_lane_ran": False}
    steps = summary.get("steps") if isinstance(summary.get("steps"), list) else []
    step_map = {
        str(item.get("name") or "").strip(): item
        for item in steps
        if isinstance(item, dict) and str(item.get("name") or "").strip()
    }
    sc_test_summary_path = _resolve_report_path((step_map.get("sc-test") or {}).get("summary_file"), root=root)
    if sc_test_summary_path is None:
        return {"unit_failed_but_engine_lane_ran": False}
    try:
        sc_test_summary = read_json(sc_test_summary_path)
    except Exception:
        return {"unit_failed_but_engine_lane_ran": False}
    sc_steps = sc_test_summary.get("steps") if isinstance(sc_test_summary.get("steps"), list) else []
    sc_step_map = {
        str(item.get("name") or "").strip(): item
        for item in sc_steps
        if isinstance(item, dict) and str(item.get("name") or "").strip()
    }
    unit_status = str((sc_step_map.get("unit") or {}).get("status") or "").strip().lower()
    engine_ran = any(
        str((sc_step_map.get(name) or {}).get("status") or "").strip().lower() in {"ok", "fail"}
        for name in ("gdunit-hard", "smoke")
    )
    return {
        "unit_failed_but_engine_lane_ran": unit_status == "fail" and engine_ran,
    }


def _derive_deterministic_bundle_from_summary(summary_path: Path | None, *, root: Path) -> dict[str, Any]:
    if summary_path is None or not summary_path.exists():
        return {}
    try:
        summary = read_json(summary_path)
    except Exception:
        return {}
    steps = summary.get("steps") if isinstance(summary.get("steps"), list) else []
    step_map = {
        str(item.get("name") or "").strip(): item
        for item in steps
        if isinstance(item, dict) and str(item.get("name") or "").strip()
    }
    sc_test_step = step_map.get("sc-test") if isinstance(step_map.get("sc-test"), dict) else {}
    acceptance_step = step_map.get("sc-acceptance-check") if isinstance(step_map.get("sc-acceptance-check"), dict) else {}
    test_summary_path = _resolve_report_path(sc_test_step.get("summary_file"), root=root)
    acceptance_summary_path = _resolve_report_path(acceptance_step.get("summary_file"), root=root)
    test_ok = str(sc_test_step.get("status") or "").strip().lower() in {"ok", "reused"}
    acceptance_ok = str(acceptance_step.get("status") or "").strip().lower() in {"ok", "reused"}
    if not (test_ok or acceptance_ok):
        return {}
    reported_dirs = []
    for step in (sc_test_step, acceptance_step):
        reported_out_dir = _resolve_report_path(step.get("reported_out_dir"), root=root)
        if reported_out_dir is not None:
            reported_dirs.append(repo_rel(reported_out_dir, root=root))
    return {
        "available": bool(test_ok or acceptance_ok),
        "test_summary": repo_rel(test_summary_path, root=root) if test_summary_path is not None else "",
        "acceptance_summary": repo_rel(acceptance_summary_path, root=root) if acceptance_summary_path is not None else "",
        "reported_out_dirs": reported_dirs,
        "reuse_mode": _normalize_report_value(summary.get("reuse_mode"), limit=60),
    }


def _compact_extract_family_actions(items: Any, *, limit: int = 6) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    if not isinstance(items, list):
        return out
    for item in items:
        if not isinstance(item, dict):
            continue
        out.append(
            {
                "family": _normalize_report_value(item.get("family"), limit=80),
                "count": int(item.get("count") or 0),
                "recommended_action": _normalize_report_value(item.get("recommended_action"), limit=120),
                "downstream_policy_hint": _normalize_report_value(item.get("downstream_policy_hint"), limit=40),
                "reason": _normalize_report_value(item.get("reason"), limit=200),
                "task_ids": [int(task_id) for task_id in list(item.get("task_ids") or [])[:12] if str(task_id).strip().isdigit()],
            }
        )
        if len(out) >= limit:
            break
    return out


def _compact_range_items(items: Any, *, limit: int = 6) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    if not isinstance(items, list):
        return out
    for item in items:
        if not isinstance(item, dict):
            continue
        out.append(
            {
                "family": _normalize_report_value(item.get("family"), limit=80),
                "task_id_start": int(item.get("task_id_start") or 0),
                "task_id_end": int(item.get("task_id_end") or 0),
                "count": int(item.get("count") or 0),
                "reason": _normalize_report_value(item.get("reason"), limit=160),
            }
        )
        if len(out) >= limit:
            break
    return out


def _extract_report_highlights(payload: dict[str, Any]) -> dict[str, Any]:
    highlights: dict[str, Any] = {}
    family_actions = _compact_extract_family_actions(payload.get("extract_family_recommended_actions"))
    if family_actions:
        highlights["extract_family_recommended_actions"] = family_actions
    hotspots = _compact_range_items(payload.get("family_hotspots"))
    if hotspots:
        highlights["family_hotspots"] = hotspots
    quarantine = _compact_range_items(payload.get("quarantine_ranges"))
    if quarantine:
        highlights["quarantine_ranges"] = quarantine
    if not highlights:
        return {}
    if "covered_count" in payload:
        highlights["covered_count"] = int(payload.get("covered_count") or 0)
    if "failed_count" in payload:
        highlights["failed_count"] = int(payload.get("failed_count") or 0)
    return highlights


def _active_task_latest_json_is_canonical(payload: dict[str, Any], *, root: Path) -> bool:
    paths = payload.get("paths") if isinstance(payload.get("paths"), dict) else {}
    latest_path = _resolve_report_path(paths.get("latest_json"), root=root)
    if latest_path is None or latest_path.name.lower() != "latest.json":
        return False
    return latest_path.parent.name.lower().startswith("sc-review-pipeline-task-")


def _active_task_is_stale_clean(payload: dict[str, Any], *, now: datetime) -> bool:
    clean_state = payload.get("clean_state") if isinstance(payload.get("clean_state"), dict) else {}
    chapter6_hints = payload.get("chapter6_hints") if isinstance(payload.get("chapter6_hints"), dict) else {}
    if str(payload.get("status") or "").strip().lower() != "ok":
        return False
    if str(clean_state.get("state") or "").strip().lower() != "clean":
        return False
    if str(payload.get("recommended_action") or "").strip().lower() != "continue":
        return False
    if str(chapter6_hints.get("blocked_by") or "").strip():
        return False
    updated_at = _parse_iso8601_soft(payload.get("updated_at_utc"))
    if updated_at is None:
        return False
    max_age_days = _env_int("PROJECT_HEALTH_ACTIVE_TASK_CLEAN_MAX_AGE_DAYS", 3)
    return (now - updated_at).total_seconds() > (max_age_days * 86400)


def load_active_task_records(root: Path, *, limit: int = 16) -> list[dict[str, Any]]:
    active_dir = root / "logs" / "ci" / "active-tasks"
    if not active_dir.exists():
        return []
    limit = max(1, _env_int("PROJECT_HEALTH_ACTIVE_TASK_LIMIT", limit))
    records: list[dict[str, Any]] = []
    now = now_local()
    for path in sorted(active_dir.glob("task-*.active.json"), key=lambda item: item.stat().st_mtime, reverse=True):
        try:
            payload = read_json(path)
        except Exception:
            continue
        if not isinstance(payload, dict):
            continue
        if not _active_task_latest_json_is_canonical(payload, root=root):
            continue
        if _active_task_is_stale_clean(payload, now=now):
            continue
        clean_state = payload.get("clean_state") if isinstance(payload.get("clean_state"), dict) else {}
        diagnostics = payload.get("diagnostics") if isinstance(payload.get("diagnostics"), dict) else {}
        paths = payload.get("paths") if isinstance(payload.get("paths"), dict) else {}
        if not str(clean_state.get("state") or "").strip():
            clean_state = _derive_clean_state_from_summary(
                _resolve_report_path(paths.get("summary_json"), root=root),
                root=root,
            )
        profile_drift = diagnostics.get("profile_drift") if isinstance(diagnostics.get("profile_drift"), dict) else {}
        waste_signals = diagnostics.get("waste_signals") if isinstance(diagnostics.get("waste_signals"), dict) else {}
        rerun_guard = diagnostics.get("rerun_guard") if isinstance(diagnostics.get("rerun_guard"), dict) else {}
        reuse_decision = diagnostics.get("reuse_decision") if isinstance(diagnostics.get("reuse_decision"), dict) else {}
        llm_timeout_memory = diagnostics.get("llm_timeout_memory") if isinstance(diagnostics.get("llm_timeout_memory"), dict) else {}
        llm_retry_stop_loss = diagnostics.get("llm_retry_stop_loss") if isinstance(diagnostics.get("llm_retry_stop_loss"), dict) else {}
        sc_test_retry_stop_loss = diagnostics.get("sc_test_retry_stop_loss") if isinstance(diagnostics.get("sc_test_retry_stop_loss"), dict) else {}
        artifact_integrity = diagnostics.get("artifact_integrity") if isinstance(diagnostics.get("artifact_integrity"), dict) else {}
        recent_failure_summary = diagnostics.get("recent_failure_summary") if isinstance(diagnostics.get("recent_failure_summary"), dict) else {}
        summary_path = _resolve_report_path(paths.get("summary_json"), root=root)
        if not waste_signals:
            waste_signals = _derive_waste_signals_from_summary(
                summary_path,
                root=root,
            )
        latest_summary_signals = payload.get("latest_summary_signals") if isinstance(payload.get("latest_summary_signals"), dict) else {}
        chapter6_hints = payload.get("chapter6_hints") if isinstance(payload.get("chapter6_hints"), dict) else {}
        rerun_forbidden = bool(chapter6_hints.get("rerun_forbidden"))
        rerun_override_flag = _normalize_report_value(chapter6_hints.get("rerun_override_flag"), limit=60)
        deterministic_bundle = _derive_deterministic_bundle_from_summary(summary_path, root=root)
        records.append(
            {
                "task_id": _normalize_report_value(payload.get("task_id"), limit=20),
                "run_id": _normalize_report_value(payload.get("run_id"), limit=40),
                "status": _normalize_report_value(payload.get("status"), limit=20),
                "updated_at_utc": _normalize_report_value(payload.get("updated_at_utc"), limit=40),
                "recommended_action": _normalize_report_value(payload.get("recommended_action"), limit=40),
                "recommended_action_why": _normalize_report_value(payload.get("recommended_action_why"), limit=200),
                "clean_state": {
                    "state": _normalize_report_value(clean_state.get("state"), limit=40),
                    "deterministic_ok": bool(clean_state.get("deterministic_ok")),
                    "llm_status": _normalize_report_value(clean_state.get("llm_status"), limit=20),
                    "needs_fix_agents": [_normalize_report_value(item, limit=40) for item in list(clean_state.get("needs_fix_agents") or [])[:6]],
                    "unknown_agents": [_normalize_report_value(item, limit=40) for item in list(clean_state.get("unknown_agents") or [])[:6]],
                    "timeout_agents": [_normalize_report_value(item, limit=40) for item in list(clean_state.get("timeout_agents") or [])[:6]],
                },
                "diagnostics": {
                    "profile_drift": {
                        "previous_delivery_profile": _normalize_report_value(profile_drift.get("previous_delivery_profile"), limit=20),
                        "previous_security_profile": _normalize_report_value(profile_drift.get("previous_security_profile"), limit=20),
                        "current_delivery_profile": _normalize_report_value(profile_drift.get("current_delivery_profile"), limit=20),
                        "current_security_profile": _normalize_report_value(profile_drift.get("current_security_profile"), limit=20),
                    }
                    if profile_drift
                    else {},
                    "waste_signals": {
                        "unit_failed_but_engine_lane_ran": bool(waste_signals.get("unit_failed_but_engine_lane_ran")),
                    },
                    "rerun_guard": {
                        "kind": _normalize_report_value(rerun_guard.get("kind"), limit=60),
                        "blocked": bool(rerun_guard.get("blocked")),
                        "recommended_path": _normalize_report_value(rerun_guard.get("recommended_path"), limit=40),
                    }
                    if rerun_guard
                    else {},
                    "reuse_decision": {
                        "mode": _normalize_report_value(reuse_decision.get("mode"), limit=60),
                        "blocked": bool(reuse_decision.get("blocked")),
                    }
                    if reuse_decision
                    else {},
                    "llm_timeout_memory": {
                        "overrides": {
                            _normalize_report_value(key, limit=40): int(value)
                            for key, value in dict(llm_timeout_memory.get("overrides") or {}).items()
                            if str(key).strip()
                        },
                    }
                    if llm_timeout_memory
                    else {},
                    "llm_retry_stop_loss": {
                        "blocked": bool(llm_retry_stop_loss.get("blocked")),
                        "step_name": _normalize_report_value(
                            llm_retry_stop_loss.get("step_name") or llm_retry_stop_loss.get("timed_out_step"),
                            limit=40,
                        ),
                        "kind": _normalize_report_value(llm_retry_stop_loss.get("kind"), limit=60),
                    }
                    if llm_retry_stop_loss
                    else {},
                    "sc_test_retry_stop_loss": {
                        "blocked": bool(sc_test_retry_stop_loss.get("blocked")),
                        "step_name": _normalize_report_value(sc_test_retry_stop_loss.get("step_name"), limit=40),
                        "kind": _normalize_report_value(sc_test_retry_stop_loss.get("kind"), limit=60),
                    }
                    if sc_test_retry_stop_loss
                    else {},
                    "artifact_integrity": {
                        "kind": _normalize_report_value(artifact_integrity.get("kind"), limit=40),
                        "blocked": bool(artifact_integrity.get("blocked")),
                    }
                    if artifact_integrity
                    else {},
                    "recent_failure_summary": {
                        "latest_failure_family": _normalize_report_value(
                            recent_failure_summary.get("latest_failure_family"),
                            limit=120,
                        ),
                        "same_family_count": int(recent_failure_summary.get("same_family_count") or 0),
                        "stop_full_rerun_recommended": bool(
                            recent_failure_summary.get("stop_full_rerun_recommended")
                        ),
                    }
                    if recent_failure_summary
                    else {},
                },
                "latest_summary_signals": {
                    "reason": _normalize_report_value(latest_summary_signals.get("reason"), limit=80),
                    "run_type": _normalize_report_value(latest_summary_signals.get("run_type"), limit=40),
                    "reuse_mode": _normalize_report_value(latest_summary_signals.get("reuse_mode"), limit=80),
                    "artifact_integrity_kind": _normalize_report_value(latest_summary_signals.get("artifact_integrity_kind"), limit=40),
                    "diagnostics_keys": [
                        _normalize_report_value(item, limit=40)
                        for item in list(latest_summary_signals.get("diagnostics_keys") or [])[:8]
                    ],
                },
                "chapter6_hints": {
                    "next_action": _normalize_report_value(chapter6_hints.get("next_action"), limit=40),
                    "can_skip_6_7": bool(chapter6_hints.get("can_skip_6_7")),
                    "can_go_to_6_8": bool(chapter6_hints.get("can_go_to_6_8")),
                    "blocked_by": _normalize_report_value(chapter6_hints.get("blocked_by"), limit=40),
                    "rerun_forbidden": rerun_forbidden,
                    "rerun_override_flag": rerun_override_flag,
                },
                "latest_json": _normalize_report_value(paths.get("latest_json"), limit=200),
                "reported_latest_json": _normalize_report_value(payload.get("reported_latest_json"), limit=200),
                "latest_json_mismatch": bool(payload.get("latest_json_mismatch")),
                "latest_json_repaired": bool(payload.get("latest_json_repaired")),
                "deterministic_bundle": deterministic_bundle,
                "path": repo_rel(path, root=root),
            }
        )
        if len(records) >= limit:
            break
    return records


def build_active_task_summary(root: Path) -> dict[str, Any]:
    records = load_active_task_records(root)
    top_records_limit = max(1, _env_int("PROJECT_HEALTH_ACTIVE_TASK_TOP_RECORDS", 8))
    top_records_limit = min(top_records_limit, len(records)) if records else 0
    summary = {
        "total": len(records),
        "clean": 0,
        "deterministic_ok_llm_not_clean": 0,
        "deterministic_only": 0,
        "not_clean": 0,
        "profile_drift": 0,
        "unit_failed_but_engine_lane_ran": 0,
        "rerun_guard_blocked": 0,
        "llm_retry_stop_loss_blocked": 0,
        "sc_test_retry_stop_loss_blocked": 0,
        "artifact_integrity_blocked": 0,
        "recent_failure_summary_blocked": 0,
        "artifact_integrity_planned_only_incomplete": 0,
        "latest_json_mismatch": 0,
        "latest_json_repaired": 0,
        "reuse_decision_present": 0,
        "rerun_forbidden": 0,
        "deterministic_bundle_available": 0,
        "run_type_planned_only": 0,
        "run_type_deterministic_only": 0,
        "run_type_full": 0,
        "run_type_llm_only": 0,
        "run_type_preflight_only": 0,
        "next_action_needs_fix_fast": 0,
        "next_action_inspect": 0,
        "next_action_resume": 0,
        "next_action_continue": 0,
        "chapter6_can_skip_6_7": 0,
        "chapter6_can_go_to_6_8": 0,
        "top_records": records[:top_records_limit],
    }
    for item in records:
        state = str(((item.get("clean_state") or {}).get("state")) or "").strip().lower()
        diagnostics = item.get("diagnostics") if isinstance(item.get("diagnostics"), dict) else {}
        chapter6_hints = item.get("chapter6_hints") if isinstance(item.get("chapter6_hints"), dict) else {}
        if isinstance(diagnostics.get("profile_drift"), dict) and diagnostics.get("profile_drift"):
            summary["profile_drift"] += 1
        waste_signals = diagnostics.get("waste_signals") if isinstance(diagnostics.get("waste_signals"), dict) else {}
        if bool(waste_signals.get("unit_failed_but_engine_lane_ran")):
            summary["unit_failed_but_engine_lane_ran"] += 1
        rerun_guard = diagnostics.get("rerun_guard") if isinstance(diagnostics.get("rerun_guard"), dict) else {}
        if bool(rerun_guard.get("blocked")):
            summary["rerun_guard_blocked"] += 1
        llm_retry_stop_loss = diagnostics.get("llm_retry_stop_loss") if isinstance(diagnostics.get("llm_retry_stop_loss"), dict) else {}
        if bool(llm_retry_stop_loss.get("blocked")):
            summary["llm_retry_stop_loss_blocked"] += 1
        sc_test_retry_stop_loss = diagnostics.get("sc_test_retry_stop_loss") if isinstance(diagnostics.get("sc_test_retry_stop_loss"), dict) else {}
        if bool(sc_test_retry_stop_loss.get("blocked")):
            summary["sc_test_retry_stop_loss_blocked"] += 1
        artifact_integrity = diagnostics.get("artifact_integrity") if isinstance(diagnostics.get("artifact_integrity"), dict) else {}
        if bool(artifact_integrity.get("blocked")):
            summary["artifact_integrity_blocked"] += 1
        recent_failure_summary = diagnostics.get("recent_failure_summary") if isinstance(diagnostics.get("recent_failure_summary"), dict) else {}
        if bool(recent_failure_summary.get("stop_full_rerun_recommended")):
            summary["recent_failure_summary_blocked"] += 1
        latest_summary_signals = item.get("latest_summary_signals") if isinstance(item.get("latest_summary_signals"), dict) else {}
        artifact_integrity_kind = str(
            latest_summary_signals.get("artifact_integrity_kind") or artifact_integrity.get("kind") or ""
        ).strip().lower()
        if artifact_integrity_kind == "planned_only_incomplete":
            summary["artifact_integrity_planned_only_incomplete"] += 1
        if bool(item.get("latest_json_mismatch")):
            summary["latest_json_mismatch"] += 1
        if bool(item.get("latest_json_repaired")):
            summary["latest_json_repaired"] += 1
        reuse_decision = diagnostics.get("reuse_decision") if isinstance(diagnostics.get("reuse_decision"), dict) else {}
        if reuse_decision:
            summary["reuse_decision_present"] += 1
        if bool(chapter6_hints.get("rerun_forbidden")):
            summary["rerun_forbidden"] += 1
        deterministic_bundle = item.get("deterministic_bundle") if isinstance(item.get("deterministic_bundle"), dict) else {}
        if bool(deterministic_bundle.get("available")):
            summary["deterministic_bundle_available"] += 1
        latest_run_type = str(latest_summary_signals.get("run_type") or "").strip().lower()
        if latest_run_type == "planned-only":
            summary["run_type_planned_only"] += 1
        elif latest_run_type == "deterministic-only":
            summary["run_type_deterministic_only"] += 1
        elif latest_run_type == "full":
            summary["run_type_full"] += 1
        elif latest_run_type == "llm-only":
            summary["run_type_llm_only"] += 1
        elif latest_run_type == "preflight-only":
            summary["run_type_preflight_only"] += 1
        next_action = str(chapter6_hints.get("next_action") or "").strip().lower()
        if next_action == "needs-fix-fast":
            summary["next_action_needs_fix_fast"] += 1
        elif next_action == "inspect":
            summary["next_action_inspect"] += 1
        elif next_action in {"resume", "fix-and-resume"}:
            summary["next_action_resume"] += 1
        elif next_action == "continue":
            summary["next_action_continue"] += 1
        if bool(chapter6_hints.get("can_skip_6_7")):
            summary["chapter6_can_skip_6_7"] += 1
        if bool(chapter6_hints.get("can_go_to_6_8")):
            summary["chapter6_can_go_to_6_8"] += 1
        if state == "clean":
            summary["clean"] += 1
        elif state == "deterministic_ok_llm_not_clean":
            summary["deterministic_ok_llm_not_clean"] += 1
        elif state == "deterministic_only":
            summary["deterministic_only"] += 1
        else:
            summary["not_clean"] += 1
    return summary


def build_report_catalog(root: Path) -> dict[str, Any]:
    """汇总 logs/ci 下可读取的 JSON 报告索引，供 latest.html 展示。"""
    logs_root = root / "logs" / "ci"
    if not logs_root.exists():
        return {"total_json": 0, "invalid_json": 0, "entries": []}

    entries: list[dict[str, Any]] = []
    invalid = 0
    for path in sorted(logs_root.rglob("*.json")):
        rel = repo_rel(path, root=root)
        try:
            stat = path.stat()
            modified_at = datetime.fromtimestamp(stat.st_mtime).astimezone().isoformat(timespec="seconds")
        except OSError:
            stat = None
            modified_at = ""

        kind = path.stem
        status = ""
        generated_at = ""
        summary = ""
        parse_error = ""
        try:
            payload = read_json(path)
            if isinstance(payload, dict):
                kind = _normalize_report_value(payload.get("kind") or payload.get("cmd") or kind, limit=120) or kind
                status = _normalize_report_value(payload.get("status") or payload.get("result"), limit=40)
                generated_at = _normalize_report_value(
                    payload.get("generated_at") or payload.get("timestamp") or payload.get("ts"),
                    limit=60,
                )
                summary = _normalize_report_value(payload.get("summary") or payload.get("message"), limit=200)
                highlights = _extract_report_highlights(payload)
            else:
                parse_error = "json-not-object"
                highlights = {}
        except Exception:
            invalid += 1
            parse_error = "invalid-json"
            highlights = {}

        entries.append(
            {
                "path": rel,
                "kind": kind,
                "status": status,
                "generated_at": generated_at,
                "summary": summary,
                "size_bytes": int(stat.st_size) if stat else 0,
                "modified_at": modified_at,
                "parse_error": parse_error,
                "highlights": highlights,
            }
        )

    entries.sort(key=lambda item: (item.get("modified_at", ""), item.get("path", "")), reverse=True)
    return {
        "total_json": len(entries),
        "invalid_json": invalid,
        "entries": entries,
    }


def dashboard_html(
    records: list[dict[str, Any]],
    *,
    generated_at: str,
    report_catalog: dict[str, Any],
    report_catalog_path: str,
    active_task_summary: dict[str, Any],
) -> str:
    overall = "ok"
    if any(item.get("status") == "fail" for item in records):
        overall = "fail"
    elif any(item.get("status") == "warn" for item in records):
        overall = "warn"

    cards = []
    for item in records:
        kind = html.escape(str(item.get("kind", "unknown")))
        status = html.escape(str(item.get("status", "unknown")))
        summary = html.escape(str(item.get("summary", "")))
        extra = []
        if item.get("stage"):
            extra.append(f"<div class=\"meta\">阶段: {html.escape(str(item['stage']))}</div>")
        if item.get("history_json"):
            extra.append(f"<div class=\"meta\">历史: {html.escape(str(item['history_json']))}</div>")
        cards.append(
            "\n".join(
                [
                    f"<section class=\"card {status}\">",
                    f"<h2>{kind}</h2>",
                    f"<div class=\"badge\">{status}</div>",
                    f"<p>{summary}</p>",
                    *extra,
                    f"<div class=\"meta\">latest json: {kind}.latest.json</div>",
                    "</section>",
                ]
            )
        )

    highlight_sections = []
    highlighted_entries = [
        item for item in report_catalog.get("entries", []) if isinstance(item, dict) and isinstance(item.get("highlights"), dict) and item.get("highlights")
    ][:4]
    for item in highlighted_entries:
        highlights = dict(item.get("highlights") or {})
        lines = [
            f"<section class=\"highlight-card\">",
            f"<h3>{html.escape(str(item.get('kind', 'unknown')))}</h3>",
            f"<div class=\"meta\">path: {html.escape(str(item.get('path', '')))}</div>",
            f"<div class=\"meta\">status: {html.escape(str(item.get('status', 'unknown') or 'unknown'))}</div>",
        ]
        if "covered_count" in highlights or "failed_count" in highlights:
            lines.append(
                f"<div class=\"meta\">covered={int(highlights.get('covered_count') or 0)} failed={int(highlights.get('failed_count') or 0)}</div>"
            )
        family_actions = highlights.get("extract_family_recommended_actions") or []
        if family_actions:
            lines.append("<div class=\"subhead\">Extract failure families</div>")
            for family_item in family_actions:
                lines.append("<div class=\"highlight-item\">")
                lines.append(
                    f"<div><strong>{html.escape(str(family_item.get('family') or 'unknown'))}</strong> "
                    f"(<span>{int(family_item.get('count') or 0)}</span>)</div>"
                )
                lines.append(
                    f"<div class=\"meta\">hint: {html.escape(str(family_item.get('downstream_policy_hint') or 'manual'))} | "
                    f"action: {html.escape(str(family_item.get('recommended_action') or 'inspect'))}</div>"
                )
                if family_item.get("task_ids"):
                    lines.append(f"<div class=\"meta\">tasks: {html.escape(','.join(str(task_id) for task_id in family_item['task_ids']))}</div>")
                if family_item.get("reason"):
                    lines.append(f"<div class=\"meta\">reason: {html.escape(str(family_item['reason']))}</div>")
                lines.append("</div>")
        hotspots = highlights.get("family_hotspots") or []
        if hotspots:
            lines.append("<div class=\"subhead\">Family hotspots</div>")
            for hotspot in hotspots:
                lines.append(
                    f"<div class=\"meta\">{html.escape(str(hotspot.get('family') or 'unknown'))}: "
                    f"T{int(hotspot.get('task_id_start') or 0)}-T{int(hotspot.get('task_id_end') or 0)} "
                    f"count={int(hotspot.get('count') or 0)}</div>"
                )
        quarantine = highlights.get("quarantine_ranges") or []
        if quarantine:
            lines.append("<div class=\"subhead\">Quarantine ranges</div>")
            for item_range in quarantine:
                lines.append(
                    f"<div class=\"meta\">{html.escape(str(item_range.get('family') or 'unknown'))}: "
                    f"T{int(item_range.get('task_id_start') or 0)}-T{int(item_range.get('task_id_end') or 0)} "
                    f"{html.escape(str(item_range.get('reason') or ''))}</div>"
                )
        lines.append("</section>")
        highlight_sections.append("\n".join(lines))

    report_rows = []
    for item in report_catalog.get("entries", []):
        parse_error = str(item.get("parse_error") or "")
        status_text = str(item.get("status") or "")
        status_cls = "invalid" if parse_error else ("ok" if status_text in {"ok", "pass", "passed"} else ("warn" if status_text == "warn" else ("fail" if status_text == "fail" else "unknown")))
        report_rows.append(
            "\n".join(
                [
                    "<tr>",
                    f"<td>{html.escape(str(item.get('modified_at', '')))}</td>",
                    f"<td>{html.escape(str(item.get('kind', '')))}</td>",
                    f"<td><span class=\"chip {status_cls}\">{html.escape(status_text or parse_error or 'n/a')}</span></td>",
                    f"<td>{html.escape(str(item.get('generated_at', '')))}</td>",
                    f"<td>{html.escape(str(item.get('path', '')))}</td>",
                    f"<td>{html.escape(str(item.get('summary', '')))}</td>",
                    "</tr>",
                ]
            )
        )

    report_total = int(report_catalog.get("total_json", 0))
    report_invalid = int(report_catalog.get("invalid_json", 0))
    report_catalog_path_escaped = html.escape(report_catalog_path)
    active_task_cards = []
    for item in list(active_task_summary.get("top_records") or []):
        clean_state = item.get("clean_state") if isinstance(item.get("clean_state"), dict) else {}
        diagnostics = item.get("diagnostics") if isinstance(item.get("diagnostics"), dict) else {}
        latest_summary_signals = item.get("latest_summary_signals") if isinstance(item.get("latest_summary_signals"), dict) else {}
        chapter6_hints = item.get("chapter6_hints") if isinstance(item.get("chapter6_hints"), dict) else {}
        profile_drift = diagnostics.get("profile_drift") if isinstance(diagnostics.get("profile_drift"), dict) else {}
        waste_signals = diagnostics.get("waste_signals") if isinstance(diagnostics.get("waste_signals"), dict) else {}
        rerun_guard = diagnostics.get("rerun_guard") if isinstance(diagnostics.get("rerun_guard"), dict) else {}
        reuse_decision = diagnostics.get("reuse_decision") if isinstance(diagnostics.get("reuse_decision"), dict) else {}
        llm_timeout_memory = diagnostics.get("llm_timeout_memory") if isinstance(diagnostics.get("llm_timeout_memory"), dict) else {}
        llm_retry_stop_loss = diagnostics.get("llm_retry_stop_loss") if isinstance(diagnostics.get("llm_retry_stop_loss"), dict) else {}
        sc_test_retry_stop_loss = diagnostics.get("sc_test_retry_stop_loss") if isinstance(diagnostics.get("sc_test_retry_stop_loss"), dict) else {}
        artifact_integrity = diagnostics.get("artifact_integrity") if isinstance(diagnostics.get("artifact_integrity"), dict) else {}
        recent_failure_summary = diagnostics.get("recent_failure_summary") if isinstance(diagnostics.get("recent_failure_summary"), dict) else {}
        deterministic_bundle = item.get("deterministic_bundle") if isinstance(item.get("deterministic_bundle"), dict) else {}
        chapter6_stop_loss_note = _chapter6_stop_loss_note(chapter6_hints, latest_summary_signals)
        diagnostic_lines: list[str] = []
        if profile_drift:
            diagnostic_lines.append(
                f"<div class=\"meta\">profile_drift: {html.escape(str(profile_drift.get('previous_delivery_profile') or 'unknown'))} -&gt; {html.escape(str(profile_drift.get('current_delivery_profile') or 'unknown'))}</div>"
            )
        if bool(waste_signals.get("unit_failed_but_engine_lane_ran")):
            diagnostic_lines.append("<div class=\"meta\">unit_failed_but_engine_lane_ran: true</div>")
        if rerun_guard:
            diagnostic_lines.append(
                f"<div class=\"meta\">rerun_guard: blocked={html.escape(str(bool(rerun_guard.get('blocked'))).lower())} kind={html.escape(str(rerun_guard.get('kind') or 'n/a'))}</div>"
            )
        if reuse_decision:
            diagnostic_lines.append(
                f"<div class=\"meta\">reuse_decision: {html.escape(str(reuse_decision.get('mode') or 'n/a'))}</div>"
            )
        if llm_timeout_memory:
            diagnostic_lines.append(
                f"<div class=\"meta\">llm_timeout_memory: {html.escape(','.join(str(key) for key in dict(llm_timeout_memory.get('overrides') or {}).keys()) or 'none')}</div>"
            )
        if llm_retry_stop_loss:
            diagnostic_lines.append(
                f"<div class=\"meta\">llm_retry_stop_loss: blocked={html.escape(str(bool(llm_retry_stop_loss.get('blocked'))).lower())} step_name={html.escape(str(llm_retry_stop_loss.get('step_name') or 'n/a'))} kind={html.escape(str(llm_retry_stop_loss.get('kind') or 'n/a'))}</div>"
            )
        if sc_test_retry_stop_loss:
            diagnostic_lines.append(
                f"<div class=\"meta\">sc_test_retry_stop_loss: blocked={html.escape(str(bool(sc_test_retry_stop_loss.get('blocked'))).lower())} step_name={html.escape(str(sc_test_retry_stop_loss.get('step_name') or 'n/a'))} kind={html.escape(str(sc_test_retry_stop_loss.get('kind') or 'n/a'))}</div>"
            )
        if artifact_integrity:
            diagnostic_lines.append(
                f"<div class=\"meta\">artifact_integrity: blocked={html.escape(str(bool(artifact_integrity.get('blocked'))).lower())} kind={html.escape(str(artifact_integrity.get('kind') or 'n/a'))}</div>"
            )
        if recent_failure_summary:
            diagnostic_lines.append(
                f"<div class=\"meta\">recent_failure_summary: family={html.escape(str(recent_failure_summary.get('latest_failure_family') or 'n/a'))} same_family_count={int(recent_failure_summary.get('same_family_count') or 0)} stop_full_rerun_recommended={bool(recent_failure_summary.get('stop_full_rerun_recommended'))}</div>"
            )
        if bool(chapter6_hints.get("rerun_forbidden")):
            diagnostic_lines.append(
                f"<div class=\"meta\">chapter6_rerun_forbidden: true override={html.escape(str(chapter6_hints.get('rerun_override_flag') or 'n/a'))}</div>"
            )
        if chapter6_stop_loss_note:
            diagnostic_lines.append(
                f"<div class=\"meta\">chapter6_stop_loss_note: {html.escape(chapter6_stop_loss_note)}</div>"
            )
        if deterministic_bundle:
            diagnostic_lines.append(
                f"<div class=\"meta\">deterministic_bundle: available={html.escape(str(bool(deterministic_bundle.get('available'))).lower())} reuse_mode={html.escape(str(deterministic_bundle.get('reuse_mode') or 'n/a'))}</div>"
            )
        if str((latest_summary_signals.get("artifact_integrity_kind") or artifact_integrity.get("kind") or "")).strip().lower() == "planned_only_incomplete":
            diagnostic_lines.append("<div class=\"meta\">planned_only_terminal_bundle: true</div>")
        active_task_cards.append(
            "\n".join(
                [
                    "<section class=\"highlight-card\">",
                    f"<h3>Task {html.escape(str(item.get('task_id') or 'unknown'))}</h3>",
                    f"<div class=\"meta\">clean_state: {html.escape(str(clean_state.get('state') or 'unknown'))}</div>",
                    f"<div class=\"meta\">deterministic_ok: {html.escape(str(clean_state.get('deterministic_ok')))}</div>",
                    f"<div class=\"meta\">llm_status: {html.escape(str(clean_state.get('llm_status') or 'unknown'))}</div>",
                    f"<div class=\"meta\">recommended_action: {html.escape(str(item.get('recommended_action') or 'inspect'))}</div>",
                    f"<div class=\"meta\">recommended_action_why: {html.escape(str(item.get('recommended_action_why') or 'n/a'))}</div>",
                    f"<div class=\"meta\">latest_reason: {html.escape(str(latest_summary_signals.get('reason') or 'n/a'))}</div>",
                    f"<div class=\"meta\">latest_run_type: {html.escape(str(latest_summary_signals.get('run_type') or 'n/a'))}</div>",
                    f"<div class=\"meta\">latest_reuse_mode: {html.escape(str(latest_summary_signals.get('reuse_mode') or 'n/a'))}</div>",
                    f"<div class=\"meta\">latest_artifact_integrity: {html.escape(str(latest_summary_signals.get('artifact_integrity_kind') or 'none'))}</div>",
                    f"<div class=\"meta\">latest_diagnostics_keys: {html.escape(','.join(str(x) for x in list(latest_summary_signals.get('diagnostics_keys') or [])) or 'none')}</div>",
                    f"<div class=\"meta\">chapter6_next_action: {html.escape(str(chapter6_hints.get('next_action') or 'n/a'))}</div>",
                    f"<div class=\"meta\">chapter6_can_skip_6_7: {html.escape(str(bool(chapter6_hints.get('can_skip_6_7'))).lower())}</div>",
                    f"<div class=\"meta\">chapter6_can_go_to_6_8: {html.escape(str(bool(chapter6_hints.get('can_go_to_6_8'))).lower())}</div>",
                    f"<div class=\"meta\">chapter6_blocked_by: {html.escape(str(chapter6_hints.get('blocked_by') or 'n/a'))}</div>",
                    f"<div class=\"meta\">chapter6_rerun_override: {html.escape(str(chapter6_hints.get('rerun_override_flag') or 'n/a'))}</div>",
                    f"<div class=\"meta\">latest_json: {html.escape(str(item.get('latest_json') or 'n/a'))}</div>",
                    f"<div class=\"meta\">reported_latest_json: {html.escape(str(item.get('reported_latest_json') or 'n/a'))}</div>",
                    f"<div class=\"meta\">latest_json_mismatch: {html.escape(str(bool(item.get('latest_json_mismatch'))).lower())}</div>",
                    f"<div class=\"meta\">latest_json_repaired: {html.escape(str(bool(item.get('latest_json_repaired'))).lower())}</div>",
                    f"<div class=\"meta\">needs_fix_agents: {html.escape(','.join(str(x) for x in list(clean_state.get('needs_fix_agents') or [])) or 'none')}</div>",
                    f"<div class=\"meta\">unknown_agents: {html.escape(','.join(str(x) for x in list(clean_state.get('unknown_agents') or [])) or 'none')}</div>",
                    f"<div class=\"meta\">timeout_agents: {html.escape(','.join(str(x) for x in list(clean_state.get('timeout_agents') or [])) or 'none')}</div>",
                    *diagnostic_lines,
                    f"<div class=\"meta\">path: {html.escape(str(item.get('path') or ''))}</div>",
                    "</section>",
                ]
            )
        )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Project Health Dashboard</title>
  <style>
    body {{ font-family: Segoe UI, Arial, sans-serif; background: #f4f6f8; color: #1f2933; margin: 0; }}
    main {{ max-width: 1100px; margin: 0 auto; padding: 24px; }}
    .hero {{ display: flex; justify-content: space-between; align-items: baseline; gap: 16px; }}
    .status {{ padding: 6px 12px; border-radius: 999px; font-weight: 700; text-transform: uppercase; }}
    .status.ok {{ background: #d1fae5; color: #065f46; }}
    .status.warn {{ background: #fef3c7; color: #92400e; }}
    .status.fail {{ background: #fee2e2; color: #991b1b; }}
    .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 16px; margin-top: 20px; }}
    .card {{ background: #ffffff; border: 1px solid #d2d6dc; border-left-width: 6px; border-radius: 12px; padding: 18px; box-shadow: 0 6px 20px rgba(15, 23, 42, 0.08); }}
    .card.ok {{ border-left-color: #10b981; }}
    .card.warn {{ border-left-color: #f59e0b; }}
    .card.fail {{ border-left-color: #ef4444; }}
    .card h2 {{ margin: 0 0 10px; font-size: 18px; }}
    .badge {{ display: inline-block; margin-bottom: 10px; font-size: 12px; font-weight: 700; text-transform: uppercase; }}
    .meta {{ color: #52606d; font-size: 12px; margin-top: 8px; word-break: break-all; }}
    .hint {{ margin-top: 20px; color: #52606d; font-size: 13px; }}
    .actions {{ display: flex; gap: 8px; margin-top: 8px; }}
    .btn {{ border: 1px solid #cbd2d9; border-radius: 8px; background: #fff; padding: 6px 10px; font-size: 13px; cursor: pointer; }}
    .btn:hover {{ background: #f8fafc; }}
    .table-wrap {{ margin-top: 18px; overflow: auto; background: #fff; border: 1px solid #d2d6dc; border-radius: 12px; }}
    .highlight-wrap {{ margin-top: 18px; display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 16px; }}
    .highlight-card {{ background: #fff; border: 1px solid #d2d6dc; border-radius: 12px; padding: 16px; box-shadow: 0 6px 20px rgba(15, 23, 42, 0.06); }}
    .highlight-card h3 {{ margin: 0 0 10px; font-size: 16px; }}
    .highlight-item {{ border-top: 1px solid #e5e7eb; padding-top: 10px; margin-top: 10px; }}
    .subhead {{ margin-top: 12px; font-size: 12px; font-weight: 700; text-transform: uppercase; color: #52606d; }}
    table {{ width: 100%; border-collapse: collapse; font-size: 12px; }}
    th, td {{ border-bottom: 1px solid #e5e7eb; text-align: left; padding: 8px; vertical-align: top; }}
    th {{ background: #f8fafc; position: sticky; top: 0; z-index: 1; }}
    .chip {{ display: inline-block; padding: 2px 6px; border-radius: 999px; font-weight: 700; }}
    .chip.ok {{ background: #d1fae5; color: #065f46; }}
    .chip.warn {{ background: #fef3c7; color: #92400e; }}
    .chip.fail {{ background: #fee2e2; color: #991b1b; }}
    .chip.invalid {{ background: #e5e7eb; color: #1f2933; }}
    .chip.unknown {{ background: #e0e7ff; color: #3730a3; }}
  </style>
</head>
<body>
  <!-- 仪表盘说明：本页面不自动刷新，避免阅读过程中跳页。 -->
  <!-- 报告索引说明：下方表格来自 logs/ci/** 的 JSON 报告聚合。 -->
  <main>
    <div class="hero">
      <div>
        <h1>项目健康总览</h1>
        <div>该页面聚合项目健康检查结果 + logs/ci 下可整合的 JSON 报告索引。</div>
        <div class="actions">
          <button class="btn" onclick="window.location.reload()">手动刷新</button>
        </div>
      </div>
      <div class="status {overall}">{overall}</div>
    </div>
    <div class="meta">generated_at: {generated_at}</div>
    <div class="grid">
      {''.join(cards)}
    </div>
    <details open>
      <summary>批量任务诊断摘录</summary>
      <div class="hint">这里优先展示报告 JSON 里可直接消费的高价值字段，例如 extract family 建议动作、family hotspot、quarantine 范围。</div>
      <div class="highlight-wrap">
        {''.join(highlight_sections) if highlight_sections else '<div class="meta">当前没有可直接展示的批量诊断摘要。</div>'}
      </div>
    </details>
    <details open>
      <summary>Active task clean state</summary>
      <div class="hint">Top active task sidecars are summarized here so deterministic-green-but-LLM-not-clean tasks are visible without opening each run directory.</div>
      <div class="hint">total={int(active_task_summary.get('total') or 0)} clean={int(active_task_summary.get('clean') or 0)} deterministic_ok_llm_not_clean={int(active_task_summary.get('deterministic_ok_llm_not_clean') or 0)} deterministic_only={int(active_task_summary.get('deterministic_only') or 0)} not_clean={int(active_task_summary.get('not_clean') or 0)} profile_drift={int(active_task_summary.get('profile_drift') or 0)} unit_failed_but_engine_lane_ran={int(active_task_summary.get('unit_failed_but_engine_lane_ran') or 0)} rerun_guard_blocked={int(active_task_summary.get('rerun_guard_blocked') or 0)} rerun_forbidden={int(active_task_summary.get('rerun_forbidden') or 0)} llm_retry_stop_loss_blocked={int(active_task_summary.get('llm_retry_stop_loss_blocked') or 0)} sc_test_retry_stop_loss_blocked={int(active_task_summary.get('sc_test_retry_stop_loss_blocked') or 0)} artifact_integrity_blocked={int(active_task_summary.get('artifact_integrity_blocked') or 0)} recent_failure_summary_blocked={int(active_task_summary.get('recent_failure_summary_blocked') or 0)} artifact_integrity_planned_only_incomplete={int(active_task_summary.get('artifact_integrity_planned_only_incomplete') or 0)} latest_json_mismatch={int(active_task_summary.get('latest_json_mismatch') or 0)} latest_json_repaired={int(active_task_summary.get('latest_json_repaired') or 0)} reuse_decision_present={int(active_task_summary.get('reuse_decision_present') or 0)} deterministic_bundle_available={int(active_task_summary.get('deterministic_bundle_available') or 0)} run_type_planned_only={int(active_task_summary.get('run_type_planned_only') or 0)} run_type_deterministic_only={int(active_task_summary.get('run_type_deterministic_only') or 0)} run_type_full={int(active_task_summary.get('run_type_full') or 0)} run_type_llm_only={int(active_task_summary.get('run_type_llm_only') or 0)} run_type_preflight_only={int(active_task_summary.get('run_type_preflight_only') or 0)} next_action_needs_fix_fast={int(active_task_summary.get('next_action_needs_fix_fast') or 0)} next_action_inspect={int(active_task_summary.get('next_action_inspect') or 0)} next_action_resume={int(active_task_summary.get('next_action_resume') or 0)} next_action_continue={int(active_task_summary.get('next_action_continue') or 0)} chapter6_can_skip_6_7={int(active_task_summary.get('chapter6_can_skip_6_7') or 0)} chapter6_can_go_to_6_8={int(active_task_summary.get('chapter6_can_go_to_6_8') or 0)}</div>
      <div class="highlight-wrap">
        {''.join(active_task_cards) if active_task_cards else '<div class="meta">No active task sidecars found.</div>'}
      </div>
    </details>
    <div class="hint">JSON 报告总数: {report_total}；解析失败: {report_invalid}；索引文件: {report_catalog_path_escaped}</div>
    <div class="hint">Auto-refresh is disabled. 页面不会自动刷新，请在执行扫描后手动刷新。</div>
    <details>
      <summary>展开查看全部 JSON 报告索引</summary>
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>modified_at</th>
              <th>kind</th>
              <th>status</th>
              <th>generated_at</th>
              <th>path</th>
              <th>summary</th>
            </tr>
          </thead>
          <tbody>
            {''.join(report_rows)}
          </tbody>
        </table>
      </div>
    </details>
  </main>
</body>
</html>
"""


def refresh_dashboard(root: Path | str | None = None, *, now: datetime | None = None) -> dict[str, Any]:
    resolved_root = resolve_root(root)
    stamp = now or now_local()
    records = load_latest_records(resolved_root)
    report_catalog = build_report_catalog(resolved_root)
    active_task_summary = build_active_task_summary(resolved_root)
    overall = "ok"
    if any(item.get("status") == "fail" for item in records):
        overall = "fail"
    elif any(item.get("status") == "warn" for item in records):
        overall = "warn"
    payload = {
        "kind": "project-health-dashboard",
        "status": overall,
        "generated_at": stamp.isoformat(timespec="seconds"),
        "records": [
            {
                "kind": item.get("kind", ""),
                "status": item.get("status", ""),
                "summary": item.get("summary", ""),
                "stage": item.get("stage", ""),
                "latest_json": f"{item.get('kind', '')}.latest.json",
                "history_json": item.get("history_json", ""),
            }
            for item in records
        ],
        "report_catalog_summary": {
            "total_json": int(report_catalog.get("total_json", 0)),
            "invalid_json": int(report_catalog.get("invalid_json", 0)),
            "catalog_json": "logs/ci/project-health/report-catalog.latest.json",
        },
        "active_task_summary": active_task_summary,
    }
    latest_root = latest_dir(resolved_root)
    report_catalog_path = latest_root / "report-catalog.latest.json"
    write_json(report_catalog_path, report_catalog)
    write_json(latest_root / "latest.json", payload)
    write_text(
        latest_root / "latest.html",
        dashboard_html(
            records,
            generated_at=payload["generated_at"],
            report_catalog=report_catalog,
            report_catalog_path=repo_rel(report_catalog_path, root=resolved_root),
            active_task_summary=active_task_summary,
        ),
    )
    return payload


def write_project_health_record(
    *,
    root: Path | str | None,
    kind: str,
    payload: dict[str, Any],
    now: datetime | None = None,
) -> dict[str, str]:
    resolved_root = resolve_root(root)
    stamp = now or now_local()
    history_root = history_dir(resolved_root, now=stamp)
    latest_root = latest_dir(resolved_root)
    history_json = history_root / f"{kind}-{timestamp_str(stamp)}.json"
    latest_json = latest_root / f"{kind}.latest.json"
    latest_md = latest_root / f"{kind}.latest.md"

    record = dict(payload)
    record["kind"] = kind
    record.setdefault("generated_at", stamp.isoformat(timespec="seconds"))
    record["history_json"] = repo_rel(history_json, root=resolved_root)
    record["latest_json"] = repo_rel(latest_json, root=resolved_root)

    write_json(history_json, record)
    write_json(latest_json, record)
    write_text(latest_md, record_markdown(record))
    refresh_dashboard(resolved_root, now=stamp)
    return {
        "history_json": repo_rel(history_json, root=resolved_root),
        "latest_json": repo_rel(latest_json, root=resolved_root),
        "latest_md": repo_rel(latest_md, root=resolved_root),
        "dashboard_html": repo_rel(latest_root / "latest.html", root=resolved_root),
    }
