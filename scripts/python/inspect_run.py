#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
SC_DIR = REPO_ROOT / "scripts" / "sc"
if str(SC_DIR) not in sys.path:
    sys.path.insert(0, str(SC_DIR))

from _artifact_schema import (  # noqa: E402
    ArtifactSchemaError,
    validate_local_hard_checks_execution_context_payload,
    validate_local_hard_checks_latest_index_payload,
    validate_local_hard_checks_repair_guide_payload,
    validate_pipeline_execution_context_payload,
    validate_pipeline_latest_index_payload,
    validate_pipeline_repair_guide_payload,
)
from _failure_taxonomy import classify_run_failure  # noqa: E402
from _pipeline_helpers import derive_pipeline_run_type  # noqa: E402
from _pipeline_history import collect_recent_failure_summary  # noqa: E402
from _chapter6_recovery_common import (  # noqa: E402
    compact_recommendation_fields,
    candidate_commands as build_candidate_commands,
    forbidden_commands as build_forbidden_commands,
    recommended_command as build_recommended_command,
)
from _repair_approval import resolve_approval_state  # noqa: E402
from _summary_schema import (  # noqa: E402
    SummarySchemaError,
    validate_local_hard_checks_summary,
    validate_pipeline_summary,
)


_REPAIR_GUIDE_ACTION_MAP: dict[str, str] = {
    "approval-fork-approved": "fork",
    "approval-fork-denied": "resume",
    "approval-fork-pending": "pause",
    "approval-fork-invalid": "inspect",
    "chapter6-route-run-6-8": "needs-fix-fast",
    "chapter6-route-fix-deterministic": "fix-and-resume",
    "chapter6-route-repo-noise": "inspect",
    "chapter6-route-inspect-first": "inspect",
}


def _join_command(parts: list[str]) -> str:
    return " ".join(str(item).strip() for item in parts if str(item).strip())


def _local_hard_check_candidate_commands(*, latest: str, run_id: str, repair_guide: dict[str, Any]) -> dict[str, str]:
    inspect_cmd = ["py", "-3", "scripts/python/dev_cli.py", "inspect-run", "--kind", "local-hard-checks"]
    latest_value = str(latest or "").strip()
    if latest_value:
        inspect_cmd += ["--latest", latest_value]

    rerun_cmd = [str(item).strip() for item in list(repair_guide.get("rerun_command") or []) if str(item).strip()]
    if not rerun_cmd:
        rerun_cmd = ["py", "-3", "scripts/python/dev_cli.py", "run-local-hard-checks"]
        run_id_value = str(run_id or "").strip()
        if run_id_value:
            rerun_cmd += ["--run-id", run_id_value]

    return {
        "inspect": _join_command(inspect_cmd),
        "resume": "",
        "fork": "",
        "rerun": _join_command(rerun_cmd),
        "needs_fix_fast": "",
        "inspect_failed_step": _join_command(inspect_cmd),
    }


def _to_posix(root: Path, path: Path | None) -> str:
    if path is None:
        return ""
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return str(path.resolve()).replace("\\", "/")


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"JSON payload must be an object: {path}")
    return payload


def _load_json_soft(path: Path | None) -> dict[str, Any]:
    if path is None or not path.exists():
        return {}
    try:
        return _load_json(path)
    except Exception:
        return {}


def _load_jsonl_soft(path: Path | None) -> list[dict[str, Any]]:
    if path is None or not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            text = line.strip()
            if not text:
                continue
            try:
                payload = json.loads(text)
            except Exception:
                continue
            if isinstance(payload, dict):
                rows.append(payload)
    except Exception:
        return []
    return rows


def _normalize_legacy_pipeline_summary(payload: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(payload)
    if str(normalized.get("cmd") or "").strip() != "sc-review-pipeline":
        return normalized

    status = str(normalized.get("status") or "").strip().lower()
    if not isinstance(normalized.get("elapsed_sec"), int) or int(normalized.get("elapsed_sec") or 0) < 0:
        normalized["elapsed_sec"] = max(0, int(normalized.get("elapsed_sec") or 0))
    if not str(normalized.get("started_at_utc") or "").strip():
        normalized["started_at_utc"] = "unknown"
    if not isinstance(normalized.get("finished_at_utc"), str):
        normalized["finished_at_utc"] = ""
    if not str(normalized.get("run_type") or "").strip():
        normalized["run_type"] = derive_pipeline_run_type(normalized)
    run_type = str(normalized.get("run_type") or "").strip().lower()
    current_reason = str(normalized.get("reason") or "").strip().lower()
    if run_type == "planned-only" and str(normalized.get("finished_at_utc") or "").strip() and current_reason in {"", "in_progress", "dry_run", "dry-run", "pipeline_clean"}:
        normalized["reason"] = "planned_only_incomplete"
    if not str(normalized.get("reason") or "").strip():
        if run_type == "planned-only" and str(normalized.get("finished_at_utc") or "").strip():
            normalized["reason"] = "planned_only_incomplete"
        elif status == "ok":
            normalized["reason"] = "pipeline_clean"
        elif status == "aborted":
            normalized["reason"] = "aborted"
        elif status == "running":
            normalized["reason"] = "in_progress"
        else:
            normalized["reason"] = "step_failed"
    if not str(normalized.get("reuse_mode") or "").strip():
        normalized["reuse_mode"] = "none"
    return normalized


def _normalize_sidecar_payload(*, kind: str, key: str, payload: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(payload)
    if kind == "pipeline" and key == "summary":
        normalized = _normalize_legacy_pipeline_summary(normalized)
    return normalized


def _resolve_path(root: Path, raw_value: Any) -> Path | None:
    value = str(raw_value or "").strip()
    if not value:
        return None
    path = Path(value)
    if not path.is_absolute():
        path = root / path
    return path.resolve()


def _bundle_root_from_latest(latest_path: Path) -> Path | None:
    parts = latest_path.resolve().parts
    lower_parts = [part.lower() for part in parts]
    for index in range(len(lower_parts) - 1):
        if lower_parts[index] == "logs" and lower_parts[index + 1] == "ci" and index > 0:
            return Path(*parts[:index]).resolve()
    return None


def _detect_kind(*, latest_path: Path, latest_payload: dict[str, Any], requested_kind: str) -> str:
    kind = str(requested_kind or "").strip().lower()
    if kind in {"pipeline", "local-hard-checks"}:
        return kind
    if str(latest_payload.get("cmd") or "").strip() == "local-hard-checks":
        return "local-hard-checks"
    if "out_dir" in latest_payload and "latest_out_dir" not in latest_payload:
        return "local-hard-checks"
    if "latest_out_dir" in latest_payload:
        return "pipeline"
    latest_name = latest_path.name.lower()
    if latest_name == "local-hard-checks-latest.json":
        return "local-hard-checks"
    return "pipeline"


def _latest_candidates(root: Path, *, kind: str, task_id: str, run_id: str) -> list[Path]:
    candidates: list[Path] = []
    ci_root = root / "logs" / "ci"
    if kind in {"", "pipeline"}:
        if task_id:
            candidates.extend(ci_root.glob(f"*/sc-review-pipeline-task-{task_id}/latest.json"))
        else:
            candidates.extend(ci_root.glob("*/sc-review-pipeline-task-*/latest.json"))
    if kind in {"", "local-hard-checks"}:
        candidates.extend(ci_root.glob("*/local-hard-checks-latest.json"))
    if run_id:
        filtered: list[Path] = []
        for path in candidates:
            try:
                payload = _load_json(path)
            except Exception:
                continue
            if str(payload.get("run_id") or "").strip() == run_id:
                filtered.append(path)
        candidates = filtered
    unique_paths = {path.resolve() for path in candidates if path.is_file()}
    unique = sorted(
        unique_paths,
        key=lambda item: (_latest_candidate_priority(root=root, latest_path=item), item.stat().st_mtime),
        reverse=True,
    )
    return unique


def _looks_like_dry_run_pipeline_summary(payload: dict[str, Any]) -> bool:
    if str(payload.get("cmd") or "").strip() != "sc-review-pipeline":
        return False
    if str(payload.get("run_type") or "").strip().lower() == "planned-only" and str(payload.get("reason") or "").strip().lower() == "planned_only_incomplete":
        return True
    if str(payload.get("reason") or "").strip().lower() not in {"in_progress", "dry_run", "dry-run"}:
        return False
    steps = payload.get("steps") if isinstance(payload.get("steps"), list) else []
    if not steps:
        return False
    seen_planned = False
    for step in steps:
        if not isinstance(step, dict):
            return False
        status = str(step.get("status") or "").strip().lower()
        if status == "planned":
            seen_planned = True
            continue
        if status == "skipped":
            continue
        return False
    return seen_planned


def _latest_candidate_priority(*, root: Path, latest_path: Path) -> int:
    try:
        latest_payload = _load_json(latest_path)
    except Exception:
        return 0
    detected_kind = _detect_kind(latest_path=latest_path, latest_payload=latest_payload, requested_kind="")
    artifact_root, out_dir = _resolve_artifact_root(root, latest_path, latest_payload, detected_kind)
    sidecar_paths = _sidecar_paths(artifact_root, detected_kind, latest_payload, out_dir)
    summary_payload = _normalize_legacy_pipeline_summary(_load_json_soft(sidecar_paths.get("summary")))
    if detected_kind == "pipeline" and _looks_like_dry_run_pipeline_summary(summary_payload):
        return 0
    return 1


def _resolve_latest_path(root: Path, *, latest: str, kind: str, task_id: str, run_id: str) -> Path:
    explicit = str(latest or "").strip()
    if explicit:
        path = Path(explicit)
        if not path.is_absolute():
            path = root / path
        return path.resolve()
    candidates = _latest_candidates(root, kind=kind, task_id=task_id, run_id=run_id)
    if not candidates:
        raise FileNotFoundError("No latest run index found. Pass --latest or provide enough filters.")
    return candidates[0]


def _validate_latest(kind: str, payload: dict[str, Any]) -> None:
    if kind == "local-hard-checks":
        validate_local_hard_checks_latest_index_payload(payload)
        return
    validate_pipeline_latest_index_payload(payload)


def _validate_execution_context(kind: str, payload: dict[str, Any]) -> None:
    if kind == "local-hard-checks":
        validate_local_hard_checks_execution_context_payload(payload)
        return
    validate_pipeline_execution_context_payload(payload)


def _validate_repair_guide(kind: str, payload: dict[str, Any]) -> None:
    if kind == "local-hard-checks":
        validate_local_hard_checks_repair_guide_payload(payload)
        return
    validate_pipeline_repair_guide_payload(payload)


def _validate_summary(kind: str, payload: dict[str, Any]) -> None:
    if kind == "local-hard-checks":
        validate_local_hard_checks_summary(payload)
        return
    validate_pipeline_summary(payload)


def _default_sidecar_paths(root: Path, kind: str, out_dir: Path | None) -> dict[str, Path | None]:
    if out_dir is None:
        return {"summary": None, "execution_context": None, "repair_guide": None, "repair_guide_md": None, "run_events": None}
    return {
        "summary": (out_dir / "summary.json").resolve(),
        "execution_context": (out_dir / "execution-context.json").resolve(),
        "repair_guide": (out_dir / "repair-guide.json").resolve(),
        "repair_guide_md": (out_dir / "repair-guide.md").resolve(),
        "run_events": (out_dir / "run-events.jsonl").resolve(),
    }


def _sidecar_paths(root: Path, kind: str, latest_payload: dict[str, Any], out_dir: Path | None) -> dict[str, Path | None]:
    defaults = _default_sidecar_paths(root, kind, out_dir)
    if kind == "local-hard-checks":
        return {
            "summary": _resolve_path(root, latest_payload.get("summary_path")) or defaults["summary"],
            "execution_context": _resolve_path(root, latest_payload.get("execution_context_path")) or defaults["execution_context"],
            "repair_guide": _resolve_path(root, latest_payload.get("repair_guide_json_path")) or defaults["repair_guide"],
            "repair_guide_md": _resolve_path(root, latest_payload.get("repair_guide_md_path")) or defaults["repair_guide_md"],
            "run_events": _resolve_path(root, latest_payload.get("run_events_path")) or defaults["run_events"],
        }
    return {
        "summary": _resolve_path(root, latest_payload.get("summary_path")) or defaults["summary"],
        "execution_context": _resolve_path(root, latest_payload.get("execution_context_path")) or defaults["execution_context"],
        "repair_guide": _resolve_path(root, latest_payload.get("repair_guide_json_path")) or defaults["repair_guide"],
        "repair_guide_md": _resolve_path(root, latest_payload.get("repair_guide_md_path")) or defaults["repair_guide_md"],
        "run_events": _resolve_path(root, latest_payload.get("run_events_path")) or defaults["run_events"],
    }


def _has_run_completed_event(*, run_events_path: Path | None, run_id: str) -> bool:
    for payload in _load_jsonl_soft(run_events_path):
        if str(payload.get("event") or "").strip() != "run_completed":
            continue
        event_run_id = str(payload.get("run_id") or "").strip()
        if event_run_id and run_id and event_run_id != run_id:
            continue
        return True
    return False


def _summarize_run_events(run_events_path: Path | None) -> dict[str, Any]:
    events = _load_jsonl_soft(run_events_path)
    if not events:
        return {}
    latest_event = events[-1]
    turn_ids = [str(item.get("turn_id") or "").strip() for item in events if str(item.get("turn_id") or "").strip()]
    latest_turn_seq = max(int(item.get("turn_seq") or 1) for item in events)
    latest_turn_events = [item for item in events if int(item.get("turn_seq") or 1) == latest_turn_seq]
    latest_turn_id = str((latest_turn_events[-1] if latest_turn_events else latest_event).get("turn_id") or "").strip()
    return {
        "event_count": len(events),
        "turn_count": len(set(turn_ids)),
        "latest_turn_id": latest_turn_id,
        "latest_turn_seq": latest_turn_seq,
        "latest_event": str(latest_event.get("event") or "").strip(),
    }


def _resolve_artifact_root(root: Path, latest_path: Path, latest_payload: dict[str, Any], kind: str) -> tuple[Path, Path | None]:
    out_dir_key = "out_dir" if kind == "local-hard-checks" else "latest_out_dir"
    candidate_roots = [root]
    bundle_root = _bundle_root_from_latest(latest_path)
    if bundle_root is not None and bundle_root not in candidate_roots:
        candidate_roots.append(bundle_root)

    for candidate_root in candidate_roots:
        out_dir = _resolve_path(candidate_root, latest_payload.get(out_dir_key))
        if out_dir is not None and out_dir.exists():
            return candidate_root, out_dir
    return candidate_roots[0], _resolve_path(candidate_roots[0], latest_payload.get(out_dir_key))


def _collect_sidecars(
    *,
    kind: str,
    sidecar_paths: dict[str, Path | None],
    validation_errors: list[str],
    missing_artifacts: list[str],
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    loaded: dict[str, dict[str, Any]] = {}
    for key in ("summary", "execution_context", "repair_guide"):
        path = sidecar_paths.get(key)
        if path is None or not path.exists():
            missing_artifacts.append(key)
            continue
        try:
            payload = _normalize_sidecar_payload(kind=kind, key=key, payload=_load_json(path))
            if key == "summary":
                _validate_summary(kind, payload)
            elif key == "execution_context":
                _validate_execution_context(kind, payload)
            else:
                _validate_repair_guide(kind, payload)
            loaded[key] = payload
        except (OSError, ValueError, json.JSONDecodeError, SummarySchemaError, ArtifactSchemaError) as exc:
            validation_errors.append(f"{key}: {exc}")
    return loaded.get("summary", {}), loaded.get("execution_context", {}), loaded.get("repair_guide", {})


def _extract_latest_summary_signals(
    *,
    latest_payload: dict[str, Any],
    latest_path: Path,
    summary_payload: dict[str, Any],
    summary_path: Path | None,
    execution_context_payload: dict[str, Any],
    run_events_path: Path | None,
    run_id: str,
) -> dict[str, Any]:
    raw_summary_payload = _normalize_legacy_pipeline_summary(_load_json_soft(summary_path))
    raw_latest_payload = _load_json_soft(latest_path)
    source = dict(summary_payload or raw_summary_payload or raw_latest_payload or latest_payload)
    run_type = str(source.get("run_type") or "").strip() or derive_pipeline_run_type(source)
    has_run_completed = _has_run_completed_event(run_events_path=run_events_path, run_id=run_id)
    reason = str(source.get("reason") or "").strip()
    if str(run_type).strip().lower() == "planned-only" and has_run_completed and str(reason or "").strip().lower() in {"", "in_progress", "dry_run", "dry-run", "pipeline_clean"}:
        reason = "planned_only_incomplete"
    diagnostics: dict[str, Any] = {}
    for candidate in (
        execution_context_payload,
        latest_payload,
        raw_latest_payload,
        raw_summary_payload,
        summary_payload,
    ):
        if not isinstance(candidate, dict):
            continue
        payload_diagnostics = candidate.get("diagnostics")
        if isinstance(payload_diagnostics, dict) and payload_diagnostics:
            diagnostics.update(payload_diagnostics)
    artifact_integrity = diagnostics.get("artifact_integrity") if isinstance(diagnostics.get("artifact_integrity"), dict) else {}
    artifact_integrity_kind = str(artifact_integrity.get("kind") or "").strip()
    if not artifact_integrity_kind and str(run_type).strip().lower() == "planned-only" and has_run_completed:
        artifact_integrity_kind = "planned_only_incomplete"
    return {
        "reason": reason,
        "run_type": run_type,
        "reuse_mode": str(source.get("reuse_mode") or "").strip(),
        "artifact_integrity_kind": artifact_integrity_kind,
        "diagnostics_keys": sorted(str(key).strip() for key in diagnostics.keys() if str(key).strip()),
    }


def _resolve_approval(*, out_dir: Path | None, execution_context: dict[str, Any], repair_guide: dict[str, Any]) -> dict[str, Any]:
    base_state = repair_guide.get("approval")
    if not isinstance(base_state, dict):
        base_state = execution_context.get("approval") if isinstance(execution_context.get("approval"), dict) else {}
    if out_dir is None:
        normalized = {
            "soft_gate": bool(base_state.get("soft_gate") or False),
            "required_action": str(base_state.get("required_action") or "").strip(),
            "status": str(base_state.get("status") or "not-needed").strip(),
            "decision": str(base_state.get("decision") or "").strip(),
            "reason": str(base_state.get("reason") or "").strip(),
            "request_id": str(base_state.get("request_id") or "").strip(),
            "request_path": str(base_state.get("request_path") or "").strip(),
            "response_path": str(base_state.get("response_path") or "").strip(),
            "recommended_action": str(base_state.get("recommended_action") or "continue").strip(),
            "allowed_actions": [str(item).strip() for item in list(base_state.get("allowed_actions") or []) if str(item).strip()],
            "blocked_actions": [str(item).strip() for item in list(base_state.get("blocked_actions") or []) if str(item).strip()],
        }
        return normalized
    return resolve_approval_state(out_dir=out_dir, approval_state=base_state)


def _derive_chapter6_hints(
    *,
    failure: dict[str, Any],
    latest_summary_signals: dict[str, Any],
    recent_failure_summary: dict[str, Any],
    approval: dict[str, Any],
) -> dict[str, Any]:
    reason = str(latest_summary_signals.get("reason") or "").strip().lower()
    artifact_integrity_kind = str(latest_summary_signals.get("artifact_integrity_kind") or "").strip().lower()
    failure_code = str(failure.get("code") or "").strip().lower()
    approval_required_action = str(approval.get("required_action") or "").strip().lower()
    approval_status = str(approval.get("status") or "").strip().lower()
    approval_recommended_action = str(approval.get("recommended_action") or "").strip().lower()
    approval_allowed_actions = {
        str(item).strip().lower()
        for item in list(approval.get("allowed_actions") or [])
        if str(item).strip()
    }
    approval_blocked_actions = {
        str(item).strip().lower()
        for item in list(approval.get("blocked_actions") or [])
        if str(item).strip()
    }
    diagnostics_keys = {
        str(key).strip().lower()
        for key in (latest_summary_signals.get("diagnostics_keys") or [])
        if str(key).strip()
    }
    if approval_required_action == "fork":
        next_action = approval_recommended_action or "inspect"
        if next_action in approval_blocked_actions or (approval_allowed_actions and next_action not in approval_allowed_actions):
            return {
                "next_action": "inspect",
                "can_skip_6_7": False,
                "can_go_to_6_8": False,
                "blocked_by": "approval_invalid",
                "rerun_forbidden": True,
                "rerun_override_flag": "",
            }
        if approval_status == "pending":
            return {
                "next_action": next_action,
                "can_skip_6_7": False,
                "can_go_to_6_8": False,
                "blocked_by": "approval_pending",
                "rerun_forbidden": True,
                "rerun_override_flag": "",
            }
        if approval_status == "approved":
            return {
                "next_action": next_action,
                "can_skip_6_7": False,
                "can_go_to_6_8": False,
                "blocked_by": "approval_approved",
                "rerun_forbidden": True,
                "rerun_override_flag": "",
            }
        if approval_status == "denied":
            return {
                "next_action": next_action,
                "can_skip_6_7": False,
                "can_go_to_6_8": False,
                "blocked_by": "approval_denied",
                "rerun_forbidden": True,
                "rerun_override_flag": "",
            }
        if approval_status in {"invalid", "mismatched"}:
            return {
                "next_action": next_action,
                "can_skip_6_7": False,
                "can_go_to_6_8": False,
                "blocked_by": "approval_invalid",
                "rerun_forbidden": True,
                "rerun_override_flag": "",
            }
    if reason.startswith("rerun_blocked:chapter6_route_run_6_8"):
        return {
            "next_action": "needs-fix-fast",
            "can_skip_6_7": True,
            "can_go_to_6_8": True,
            "blocked_by": "rerun_guard",
            "rerun_forbidden": True,
            "rerun_override_flag": "--allow-full-rerun",
        }
    if reason.startswith("rerun_blocked:chapter6_route_fix_deterministic"):
        return {
            "next_action": "fix-and-resume",
            "can_skip_6_7": False,
            "can_go_to_6_8": False,
            "blocked_by": "rerun_guard",
            "rerun_forbidden": True,
            "rerun_override_flag": "--allow-full-rerun",
        }
    if reason.startswith("rerun_blocked:chapter6_route_repo_noise_stop"):
        return {
            "next_action": "inspect",
            "can_skip_6_7": False,
            "can_go_to_6_8": False,
            "blocked_by": "rerun_guard",
            "rerun_forbidden": True,
            "rerun_override_flag": "--allow-full-rerun",
        }
    if reason.startswith("rerun_blocked:chapter6_route_inspect_first"):
        return {
            "next_action": "inspect",
            "can_skip_6_7": False,
            "can_go_to_6_8": False,
            "blocked_by": "rerun_guard",
            "rerun_forbidden": True,
            "rerun_override_flag": "--allow-full-rerun",
        }
    if reason.startswith("rerun_blocked:deterministic_green_llm_not_clean"):
        return {
            "next_action": "needs-fix-fast",
            "can_skip_6_7": True,
            "can_go_to_6_8": True,
            "blocked_by": "rerun_guard",
            "rerun_forbidden": True,
            "rerun_override_flag": "--allow-full-rerun",
        }
    if reason.startswith("rerun_blocked:repeat_review_needs_fix"):
        return {
            "next_action": "needs-fix-fast",
            "can_skip_6_7": True,
            "can_go_to_6_8": True,
            "blocked_by": "rerun_guard",
            "rerun_forbidden": True,
            "rerun_override_flag": "--allow-full-rerun",
        }
    if reason.startswith("rerun_blocked:repeat_deterministic_failure"):
        return {
            "next_action": "inspect",
            "can_skip_6_7": False,
            "can_go_to_6_8": False,
            "blocked_by": "rerun_guard",
            "rerun_forbidden": True,
            "rerun_override_flag": "--allow-repeat-deterministic-failures",
        }
    if reason.startswith("rerun_blocked:dirty_worktree_unsafe_paths_ceiling") or reason.startswith("rerun_blocked:dirty_worktree_changed_paths_ceiling") or reason.startswith("rerun_blocked:profile_drift_change_scope_ceiling"):
        return {
            "next_action": "inspect",
            "can_skip_6_7": False,
            "can_go_to_6_8": False,
            "blocked_by": "rerun_guard",
            "rerun_forbidden": True,
            "rerun_override_flag": "--allow-large-change-scope-rerun",
        }
    if "llm_retry_stop_loss" in diagnostics_keys:
        return {
            "next_action": "needs-fix-fast",
            "can_skip_6_7": True,
            "can_go_to_6_8": True,
            "blocked_by": "llm_retry_stop_loss",
            "rerun_forbidden": True,
            "rerun_override_flag": "--allow-full-rerun",
        }
    if "sc_test_retry_stop_loss" in diagnostics_keys and failure_code == "step-failed":
        return {
            "next_action": "rerun",
            "can_skip_6_7": False,
            "can_go_to_6_8": False,
            "blocked_by": "sc_test_retry_stop_loss",
            "rerun_forbidden": True,
            "rerun_override_flag": "",
        }
    if "waste_signals" in diagnostics_keys and failure_code == "step-failed":
        return {
            "next_action": "resume",
            "can_skip_6_7": False,
            "can_go_to_6_8": False,
            "blocked_by": "waste_signals",
            "rerun_forbidden": True,
            "rerun_override_flag": "",
        }
    if bool(recent_failure_summary.get("stop_full_rerun_recommended")) and failure_code in {"step-failed", "review-needs-fix"}:
        return {
            "next_action": "inspect",
            "can_skip_6_7": False,
            "can_go_to_6_8": False,
            "blocked_by": "recent_failure_summary",
            "rerun_forbidden": True,
            "rerun_override_flag": "",
        }
    if reason == "planned_only_incomplete" or artifact_integrity_kind == "planned_only_incomplete":
        return {
            "next_action": "rerun",
            "can_skip_6_7": False,
            "can_go_to_6_8": False,
            "blocked_by": "artifact_integrity",
            "rerun_forbidden": False,
            "rerun_override_flag": "",
        }
    if failure_code == "ok":
        return {
            "next_action": "continue",
            "can_skip_6_7": True,
            "can_go_to_6_8": False,
            "blocked_by": "",
            "rerun_forbidden": False,
            "rerun_override_flag": "",
        }
    if failure_code == "step-failed":
        return {
            "next_action": "fix-and-resume",
            "can_skip_6_7": False,
            "can_go_to_6_8": False,
            "blocked_by": "deterministic_failure",
            "rerun_forbidden": False,
            "rerun_override_flag": "",
        }
    if failure_code in {"schema-invalid", "artifact-missing", "stale-latest", "artifact-incomplete"}:
        return {
            "next_action": "rerun",
            "can_skip_6_7": False,
            "can_go_to_6_8": False,
            "blocked_by": "artifact_integrity",
            "rerun_forbidden": False,
            "rerun_override_flag": "",
        }
    return {
        "next_action": "inspect",
        "can_skip_6_7": False,
        "can_go_to_6_8": False,
        "blocked_by": failure_code or "unknown",
        "rerun_forbidden": False,
        "rerun_override_flag": "",
    }


def _derive_recommended_action_why(
    *,
    failure: dict[str, Any],
    chapter6_hints: dict[str, Any],
    latest_summary_signals: dict[str, Any],
    approval: dict[str, Any],
) -> str:
    blocked_by = str(chapter6_hints.get("blocked_by") or "").strip().lower()
    next_action = str(chapter6_hints.get("next_action") or "").strip().lower()
    reason = str(latest_summary_signals.get("reason") or "").strip()
    artifact_integrity_kind = str(latest_summary_signals.get("artifact_integrity_kind") or "").strip().lower()
    failure_code = str(failure.get("code") or "").strip().lower()
    failure_message = str(failure.get("message") or "").strip()
    approval_reason = str(approval.get("reason") or "").strip()

    if blocked_by == "approval_pending":
        return approval_reason or "Fork approval is pending; pause recovery until the approval request is approved or denied."
    if blocked_by == "approval_approved":
        return approval_reason or "Fork approval is approved; continue with the fork path instead of resuming the current run."
    if blocked_by == "approval_denied":
        return approval_reason or "Fork approval was denied; continue by resuming the current run instead of forking."
    if blocked_by == "approval_invalid":
        return approval_reason or "Approval sidecars are invalid or mismatched; inspect and repair them before continuing recovery."

    if blocked_by == "rerun_guard":
        if reason.startswith("rerun_blocked:chapter6_route_run_6_8"):
            return "The latest Chapter 6 route already proved deterministic evidence is sufficient; continue with needs-fix-fast instead of reopening a full 6.7."
        if reason.startswith("rerun_blocked:chapter6_route_fix_deterministic"):
            return "The latest Chapter 6 route says a deterministic root cause still blocks progress; fix that first, then resume."
        if reason.startswith("rerun_blocked:chapter6_route_repo_noise_stop"):
            return "The latest Chapter 6 route classified this failure as repo noise or process contention; inspect the artifacts and environment before paying for another rerun."
        if reason.startswith("rerun_blocked:chapter6_route_inspect_first"):
            return "The latest Chapter 6 route requires inspection first; read the current artifacts before choosing 6.7 or 6.8."
        if reason.startswith("rerun_blocked:deterministic_green_llm_not_clean"):
            return "Deterministic evidence is already green; do not pay for another full 6.7. Continue with 6.8 or needs-fix-fast."
        if reason.startswith("rerun_blocked:repeat_review_needs_fix"):
            return "Recent reviewer-only reruns already repeated the same Needs Fix family; continue with needs-fix-fast or record the remaining findings instead of reopening 6.7."
        if reason.startswith("rerun_blocked:repeat_deterministic_failure"):
            return "Recent deterministic failures already repeated with the same fingerprint; inspect and fix the root cause before rerunning 6.7."
        if (
            reason.startswith("rerun_blocked:dirty_worktree_unsafe_paths_ceiling")
            or reason.startswith("rerun_blocked:dirty_worktree_changed_paths_ceiling")
            or reason.startswith("rerun_blocked:profile_drift_change_scope_ceiling")
        ):
            return "Current changes exceed the standard Chapter 6 safe scope; shrink the dirty worktree or inspect/reset the drift before paying for another full 6.7."
        return "A rerun guard is active; check the latest diagnostics before paying for another full rerun."
    if blocked_by == "llm_retry_stop_loss":
        return "This run already stopped after the first costly llm timeout; continue with the narrow llm-only closure path instead of reopening deterministic steps."
    if blocked_by == "sc_test_retry_stop_loss":
        return "The pipeline already proved the unit root cause and stopped the same-run retry; fix the unit issue first, then start a fresh run."
    if blocked_by == "waste_signals":
        return "Unit failure was already known before more expensive engine-lane work continued; fix the unit/root cause before paying that cost again."
    if blocked_by == "recent_failure_summary":
        return "Recent failed runs already repeat the same failure family; inspect the repeated fingerprint and fix the root cause before paying for another full rerun."
    if blocked_by == "artifact_integrity":
        if reason == "planned_only_incomplete" or artifact_integrity_kind == "planned_only_incomplete":
            return "The latest bundle only contains planned-only evidence; rerun 6.7 from a real producer bundle before trusting later Chapter 6 steps."
        return "Latest artifacts are incomplete or stale; rerun from a real producer bundle before trusting the recovery path."
    if failure_code == "ok":
        return "Inspection is green; continue local work without reopening the full review pipeline."
    if next_action == "fix-and-resume":
        return "Deterministic evidence found a concrete failing step; fix that root cause first, then resume from the existing task lane."
    if next_action == "resume":
        return "Resume is the lowest-cost path after fixing the current blocking issue in the existing artifact set."
    if next_action == "needs-fix-fast":
        return "Deterministic evidence is already sufficient; use the narrow needs-fix-fast closure path instead of paying for another full rerun."
    if next_action == "rerun":
        return failure_message or "Recovery artifacts are not reliable enough to continue, so rerun from a fresh producer bundle."
    return failure_message or "Inspect the latest artifacts before choosing resume or rerun."


def _merge_candidate_commands(base: dict[str, str], override: dict[str, Any]) -> dict[str, str]:
    merged = dict(base)
    for key, value in override.items():
        key_text = str(key or "").strip()
        value_text = str(value or "").strip()
        if key_text and value_text:
            merged[key_text] = value_text
    return merged


def _repair_guide_recommendation(repair_guide: dict[str, Any]) -> tuple[str, str, str]:
    recommendations = repair_guide.get("recommendations") if isinstance(repair_guide.get("recommendations"), list) else []
    if not recommendations:
        return "", "", ""
    for item in recommendations:
        if not isinstance(item, dict):
            continue
        rec_id = str(item.get("id") or "").strip()
        action = _REPAIR_GUIDE_ACTION_MAP.get(rec_id, "")
        if not action:
            continue
        commands = [str(cmd).strip() for cmd in list(item.get("commands") or []) if str(cmd).strip()]
        why = str(item.get("why") or "").strip() or str(item.get("title") or "").strip()
        return action, why, (commands[0] if commands else "")
    return "", "", ""


def _local_hard_check_recommendation(
    *,
    failure: dict[str, Any],
    repair_guide: dict[str, Any],
    candidate_commands: dict[str, str],
) -> tuple[str, str, list[str], str]:
    failure_code = str(failure.get("code") or "").strip().lower()
    if failure_code == "ok":
        inspect_cmd = str(candidate_commands.get("inspect") or "").strip()
        return (
            "inspect",
            "Repo-scoped hard checks are clean. Inspect the latest bundle only when you need to review the recorded evidence.",
            [],
            inspect_cmd,
        )

    failed_step = str(repair_guide.get("failed_step") or "").strip()
    rerun_cmd = str(candidate_commands.get("rerun") or "").strip()
    why = "Repo-scoped hard checks found a concrete failing step; fix that root cause first, then rerun the same entrypoint."
    if failed_step:
        why = f"Repo-scoped hard checks failed at {failed_step}; fix that root cause first, then rerun the same entrypoint."
    return ("rerun", why, [], rerun_cmd)


def inspect_run_artifacts(
    *,
    repo_root: Path,
    latest: str = "",
    kind: str = "",
    task_id: str = "",
    run_id: str = "",
) -> tuple[int, dict[str, Any]]:
    root = Path(repo_root).resolve()
    validation_errors: list[str] = []
    missing_artifacts: list[str] = []
    stale_latest = False
    incomplete_run = False

    latest_path = _resolve_latest_path(root, latest=latest, kind=kind, task_id=task_id, run_id=run_id)
    latest_payload: dict[str, Any] = {}
    detected_kind = str(kind or "").strip().lower() or "pipeline"
    try:
        latest_payload = _load_json(latest_path)
        detected_kind = _detect_kind(latest_path=latest_path, latest_payload=latest_payload, requested_kind=kind)
        _validate_latest(detected_kind, latest_payload)
    except FileNotFoundError:
        raise
    except (OSError, ValueError, json.JSONDecodeError, ArtifactSchemaError) as exc:
        validation_errors.append(f"latest: {exc}")

    artifact_root, out_dir = _resolve_artifact_root(root, latest_path, latest_payload, detected_kind)
    if out_dir is None or not out_dir.exists():
        stale_latest = True

    sidecar_paths = _sidecar_paths(artifact_root, detected_kind, latest_payload, out_dir)
    summary, execution_context, repair_guide = _collect_sidecars(
        kind=detected_kind,
        sidecar_paths=sidecar_paths,
        validation_errors=validation_errors,
        missing_artifacts=missing_artifacts,
    )

    latest_status = str(latest_payload.get("status") or "").strip()
    summary_status = str(summary.get("status") or latest_status or "").strip()
    repair_status = str(repair_guide.get("status") or "").strip()
    failed_step = str(summary.get("failed_step") or execution_context.get("failed_step") or repair_guide.get("failed_step") or "").strip()
    run_id_text = str(latest_payload.get("run_id") or summary.get("run_id") or execution_context.get("run_id") or run_id or "").strip()
    run_type = derive_pipeline_run_type(summary if isinstance(summary, dict) else {})
    has_run_completed = _has_run_completed_event(run_events_path=sidecar_paths.get("run_events"), run_id=run_id_text)
    if detected_kind == "pipeline" and latest_status == "ok":
        incomplete_run = (not has_run_completed) or (str(run_type).strip().lower() == "planned-only" and has_run_completed)
    failure = classify_run_failure(
        latest_status=latest_status,
        summary_status=summary_status,
        repair_status=repair_status,
        failed_step=failed_step,
        validation_errors=validation_errors,
        missing_artifacts=missing_artifacts,
        stale_latest=stale_latest,
        incomplete_run=incomplete_run,
    )
    recent_failure_summary = (
        collect_recent_failure_summary(
            task_id=str(latest_payload.get("task_id") or summary.get("task_id") or execution_context.get("task_id") or task_id or "").strip(),
            delivery_profile=str(execution_context.get("delivery_profile") or "").strip(),
            security_profile=str(execution_context.get("security_profile") or "").strip(),
            root=artifact_root,
            limit=3,
        )
        if detected_kind == "pipeline"
        else {}
    )
    approval = _resolve_approval(out_dir=out_dir, execution_context=execution_context, repair_guide=repair_guide)
    status = "aborted" if failure["code"] == "aborted" else ("ok" if failure["code"] == "ok" else "fail")
    payload = {
        "kind": "pipeline" if detected_kind == "pipeline" else "local-hard-checks",
        "status": status,
        "task_id": str(latest_payload.get("task_id") or summary.get("task_id") or execution_context.get("task_id") or task_id or "").strip(),
        "run_id": str(latest_payload.get("run_id") or summary.get("run_id") or execution_context.get("run_id") or run_id or "").strip(),
        "latest_status": latest_status,
        "summary_status": summary_status,
        "repair_status": repair_status or "unknown",
        "failed_step": failed_step,
        "failure": failure,
        "validation_errors": validation_errors,
        "missing_artifacts": missing_artifacts,
        "stale_latest": stale_latest,
        "incomplete_run": incomplete_run,
        "recent_failure_summary": recent_failure_summary,
        "approval": approval,
        "latest_summary_signals": _extract_latest_summary_signals(
            latest_payload=latest_payload,
            latest_path=latest_path,
            summary_payload=summary,
            summary_path=sidecar_paths.get("summary"),
            execution_context_payload=execution_context,
            run_events_path=sidecar_paths.get("run_events"),
            run_id=run_id_text,
        ),
        "run_event_summary": _summarize_run_events(sidecar_paths.get("run_events")),
        "paths": {
            "latest": _to_posix(root, latest_path),
            "out_dir": _to_posix(root, out_dir),
            "summary": _to_posix(root, sidecar_paths.get("summary")),
            "execution_context": _to_posix(root, sidecar_paths.get("execution_context")),
            "repair_guide": _to_posix(root, sidecar_paths.get("repair_guide")),
            "repair_guide_md": _to_posix(root, sidecar_paths.get("repair_guide_md")),
            "run_events": _to_posix(root, sidecar_paths.get("run_events")),
        },
    }
    payload["chapter6_hints"] = _derive_chapter6_hints(
        failure=failure,
        latest_summary_signals=payload["latest_summary_signals"],
        recent_failure_summary=recent_failure_summary,
        approval=approval,
    )
    summary_candidate_commands = summary.get("candidate_commands") if isinstance(summary.get("candidate_commands"), dict) else {}
    repair_action, repair_why, repair_command = _repair_guide_recommendation(repair_guide)
    if detected_kind == "local-hard-checks":
        payload["candidate_commands"] = _merge_candidate_commands(
            _local_hard_check_candidate_commands(
                latest=payload["paths"]["latest"],
                run_id=payload["run_id"],
                repair_guide=repair_guide,
            ),
            summary_candidate_commands,
        )
        (
            payload["recommended_action"],
            payload["recommended_action_why"],
            payload["forbidden_commands"],
            payload["recommended_command"],
        ) = _local_hard_check_recommendation(
            failure=failure,
            repair_guide=repair_guide,
            candidate_commands=payload["candidate_commands"],
        )
    else:
        payload["recommended_action"] = str(summary.get("recommended_action") or payload["chapter6_hints"].get("next_action") or "").strip()
        if not str(payload.get("recommended_action") or "").strip():
            payload["recommended_action"] = repair_action
        payload["candidate_commands"] = _merge_candidate_commands(
            build_candidate_commands(payload["task_id"], payload["paths"]["latest"]),
            summary_candidate_commands,
        )
        payload["recommended_command"] = str(summary.get("recommended_command") or "").strip() or repair_command or build_recommended_command(
            payload["recommended_action"],
            payload["candidate_commands"],
            payload["chapter6_hints"],
            approval,
        )
        summary_forbidden_commands = [str(item).strip() for item in list(summary.get("forbidden_commands") or []) if str(item).strip()]
        payload["forbidden_commands"] = summary_forbidden_commands or build_forbidden_commands(
            recommended_action=payload["recommended_action"],
            commands=payload["candidate_commands"],
            chapter6_hints=payload["chapter6_hints"],
            approval=approval,
        )
        payload["recommended_action_why"] = _derive_recommended_action_why(
            failure=failure,
            chapter6_hints=payload["chapter6_hints"],
            latest_summary_signals=payload["latest_summary_signals"],
            approval=approval,
        )
        if not str(summary.get("recommended_action") or "").strip() and repair_action and repair_why:
            payload["recommended_action_why"] = repair_why
    return (0 if failure["code"] == "ok" else 1), payload


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Inspect the latest local harness run and emit a stable JSON summary.")
    parser.add_argument("--repo-root", default=str(REPO_ROOT), help="Repository root used to resolve relative paths.")
    parser.add_argument("--latest", default="", help="Explicit latest index path.")
    parser.add_argument("--kind", default="", choices=["", "pipeline", "local-hard-checks"], help="Expected run kind.")
    parser.add_argument("--task-id", default="", help="Task id used to resolve the latest pipeline run.")
    parser.add_argument("--run-id", default="", help="Optional run id filter when resolving latest.json automatically.")
    parser.add_argument("--out-json", default="", help="Optional file path to persist the inspection payload.")
    parser.add_argument(
        "--recommendation-only",
        action="store_true",
        help="Print a compact recovery recommendation instead of the full JSON payload.",
    )
    parser.add_argument(
        "--recommendation-format",
        default="kv",
        choices=["kv", "json"],
        help="Output format for --recommendation-only.",
    )
    return parser


def _render_recommendation_only(payload: dict[str, Any]) -> str:
    fields = _compact_recommendation_payload(payload)
    return "\n".join(f"{key}={value}" for key, value in fields.items()) + "\n"


def _compact_recommendation_payload(payload: dict[str, Any]) -> dict[str, str]:
    return compact_recommendation_fields(payload)


def main() -> int:
    args = build_parser().parse_args()
    try:
        rc, payload = inspect_run_artifacts(
            repo_root=Path(str(args.repo_root or REPO_ROOT)),
            latest=str(args.latest or "").strip(),
            kind=str(args.kind or "").strip(),
            task_id=str(args.task_id or "").strip(),
            run_id=str(args.run_id or "").strip(),
        )
    except FileNotFoundError as exc:
        print(json.dumps({"status": "fail", "failure": {"code": "artifact-missing", "message": str(exc), "severity": "hard"}}, ensure_ascii=False, indent=2))
        return 2

    out_json = str(args.out_json or "").strip()
    if out_json:
        out_path = Path(out_json)
        if not out_path.is_absolute():
            out_path = Path(str(args.repo_root or REPO_ROOT)) / out_path
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    if bool(args.recommendation_only):
        if str(args.recommendation_format or "kv").strip().lower() == "json":
            print(json.dumps(_compact_recommendation_payload(payload), ensure_ascii=False))
        else:
            print(_render_recommendation_only(payload), end="")
    else:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
