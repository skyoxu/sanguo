#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT / "scripts" / "python") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "scripts" / "python"))
if str(REPO_ROOT / "scripts" / "sc") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "scripts" / "sc"))

from inspect_run import inspect_run_artifacts  # noqa: E402
from validate_recovery_docs import extract_repo_paths, is_readme, is_template, parse_fields  # noqa: E402
from _active_task_sidecar import write_active_task_sidecar  # noqa: E402
from _chapter6_recovery_common import (  # noqa: E402
    compact_recommendation_fields,
    candidate_commands as _shared_candidate_commands,
    chapter6_stop_loss_note as _chapter6_stop_loss_note,
    extract_bottleneck_fields as _extract_bottleneck_fields,
    format_metric_map as _format_metric_map,
    forbidden_commands as _shared_forbidden_commands,
    recommended_command as _shared_recommended_command,
)


def _repo_rel(root: Path, path: Path | None) -> str:
    if path is None:
        return ""
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return str(path.resolve()).replace("\\", "/")


def _resolve_path(root: Path, raw: str) -> Path:
    path = Path(str(raw or "").strip())
    if not path.is_absolute():
        path = root / path
    return path.resolve()


def _today() -> str:
    return date.today().isoformat()


def _default_output_paths(root: Path, task_id: str) -> tuple[Path, Path]:
    slug = f"task-{task_id}" if task_id else "task-unknown"
    base = root / "logs" / "ci" / _today() / "task-resume"
    return base / f"{slug}-resume-summary.json", base / f"{slug}-resume-summary.md"


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"JSON payload must be an object: {path}")
    return payload


def _extract_scalar_tokens(value: str) -> list[str]:
    text = str(value or "").strip()
    if not text or text.lower().startswith("n/a"):
        return []
    tokens: list[str] = []
    for chunk in text.split(","):
        item = chunk.strip().strip("`").strip()
        if item:
            tokens.append(item)
    return tokens


def _doc_match_score(*, fields: dict[str, str], task_id: str, run_id: str, latest_rel: str) -> int:
    score = 0
    task_tokens = _extract_scalar_tokens(fields.get("Related task id(s)", ""))
    run_tokens = _extract_scalar_tokens(fields.get("Related run id", ""))
    latest_tokens = [item.replace("\\", "/").lstrip("./") for item in extract_repo_paths(fields.get("Related latest.json", ""))]
    if task_id and task_id in task_tokens:
        score += 100
    if run_id and run_id in run_tokens:
        score += 10
    if latest_rel and latest_rel in latest_tokens:
        score += 1
    return score


def _find_related_docs(root: Path, dir_name: str, *, task_id: str, run_id: str, latest_rel: str) -> list[str]:
    doc_dir = root / dir_name
    if not doc_dir.exists():
        return []
    matches: list[tuple[int, float, str]] = []
    for path in doc_dir.glob("*.md"):
        if is_readme(path) or is_template(path):
            continue
        fields = parse_fields(path)
        score = _doc_match_score(fields=fields, task_id=task_id, run_id=run_id, latest_rel=latest_rel)
        if score <= 0:
            continue
        matches.append((score, path.stat().st_mtime, _repo_rel(root, path)))
    matches.sort(key=lambda item: (item[0], item[1], item[2]), reverse=True)
    return [item[2] for item in matches]


def _load_optional_agent_review(root: Path, out_dir_rel: str) -> dict[str, Any]:
    if not out_dir_rel:
        return {}
    path = _resolve_path(root, f"{out_dir_rel}/agent-review.json")
    if not path.exists():
        return {}
    try:
        payload = _read_json(path)
    except Exception:
        return {}
    payload["_path"] = _repo_rel(root, path)
    return payload


def _active_task_json_path(root: Path, task_id: str) -> Path:
    return root / "logs" / "ci" / "active-tasks" / f"task-{task_id}.active.json"


def _resolve_latest_out_dir(root: Path, latest_payload: dict[str, Any]) -> Path | None:
    for key in ("latest_out_dir", "summary_path", "execution_context_path", "repair_guide_json_path", "repair_guide_md_path"):
        raw = str(latest_payload.get(key) or "").strip()
        if not raw:
            continue
        candidate = _resolve_path(root, raw)
        if key != "latest_out_dir":
            candidate = candidate.parent
        if candidate.exists():
            return candidate
    return None


def _load_active_task(root: Path, task_id: str) -> dict[str, Any]:
    if not task_id:
        return {}
    path = _active_task_json_path(root, task_id)
    if not path.exists():
        return {}
    try:
        payload = _read_json(path)
    except Exception:
        return {}
    payload["_path"] = _repo_rel(root, path)
    return payload


def _normalized_active_task_snapshot(active_task: dict[str, Any], *, inspection_latest: str) -> dict[str, Any]:
    paths = active_task.get("paths") if isinstance(active_task.get("paths"), dict) else {}
    reported_latest = str(paths.get("latest_json") or "").strip()
    resolved_latest = str(inspection_latest or "").strip() or reported_latest
    payload = {
        "path": str(active_task.get("_path") or ""),
        "status": str(active_task.get("status") or "").strip(),
        "recommended_action": str(active_task.get("recommended_action") or "").strip(),
        "recommended_action_why": str(active_task.get("recommended_action_why") or "").strip(),
        "latest_json": resolved_latest,
    }
    if reported_latest and reported_latest != resolved_latest:
        payload["reported_latest_json"] = reported_latest
        payload["latest_json_mismatch"] = True
    else:
        payload["reported_latest_json"] = reported_latest
        payload["latest_json_mismatch"] = False
    return payload


def _repair_active_task_latest_pointer(root: Path, *, task_id: str, resolved_latest: str) -> dict[str, Any]:
    if not task_id or not resolved_latest:
        return {"repaired": False}
    json_path = _active_task_json_path(root, task_id)
    if not json_path.exists():
        return {"repaired": False}
    try:
        payload = _read_json(json_path)
    except Exception:
        return {"repaired": False}
    paths = payload.get("paths") if isinstance(payload.get("paths"), dict) else {}
    reported_latest = str(paths.get("latest_json") or "").strip()
    if not reported_latest or reported_latest == resolved_latest:
        return {"repaired": False, "reported_latest_json": reported_latest, "latest_json": resolved_latest}
    latest_path = _resolve_path(root, resolved_latest)
    rebuilt = False
    if latest_path.exists():
        try:
            latest_payload = _read_json(latest_path)
        except Exception:
            latest_payload = {}
        rebuilt_out_dir = _resolve_latest_out_dir(root, latest_payload)
        rebuilt_run_id = str(latest_payload.get("run_id") or "").strip()
        rebuilt_status = str(latest_payload.get("status") or "").strip() or "ok"
        if rebuilt_out_dir is not None and rebuilt_run_id:
            try:
                write_active_task_sidecar(
                    task_id=task_id,
                    run_id=rebuilt_run_id,
                    status=rebuilt_status,
                    out_dir=rebuilt_out_dir,
                    latest_json_path=latest_path,
                    root=root,
                )
                rebuilt = True
            except Exception:
                rebuilt = False
    if rebuilt:
        try:
            rebuilt_payload = _read_json(json_path)
        except Exception:
            rebuilt_payload = {}
        if isinstance(rebuilt_payload, dict):
            rebuilt_payload["reported_latest_json"] = reported_latest
            rebuilt_payload["latest_json_mismatch"] = False
            rebuilt_payload["latest_json_repaired"] = True
            json_path.write_text(json.dumps(rebuilt_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
        return {
            "repaired": True,
            "reported_latest_json": reported_latest,
            "latest_json": resolved_latest,
            "path": _repo_rel(root, json_path),
            "rebuild_mode": "sidecar",
        }
    paths["latest_json"] = resolved_latest
    payload["paths"] = paths
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")

    md_path = json_path.with_suffix(".md")
    if md_path.exists():
        lines = md_path.read_text(encoding="utf-8").splitlines()
        updated_lines: list[str] = []
        replaced = False
        for line in lines:
            if line.startswith("- Latest pointer:"):
                updated_lines.append(f"- Latest pointer: `{resolved_latest}`")
                replaced = True
            else:
                updated_lines.append(line)
        if replaced:
            md_path.write_text("\n".join(updated_lines) + "\n", encoding="utf-8", newline="\n")
    return {
        "repaired": True,
        "reported_latest_json": reported_latest,
        "latest_json": resolved_latest,
        "path": _repo_rel(root, json_path),
    }


def _fallback_recommendation(inspection: dict[str, Any], task_id: str) -> tuple[str, str, str, list[str]]:
    failure = inspection.get("failure") or {}
    failure_code = str(failure.get("code") or "").strip().lower()
    failed_step = str(inspection.get("failed_step") or "").strip()
    repair_status = str(inspection.get("repair_status") or "").strip().lower()
    signals = [f"failure.code={failure_code or 'unknown'}"]
    if failed_step:
        signals.append(f"failed_step={failed_step}")
    if repair_status:
        signals.append(f"repair_status={repair_status}")
    if failure_code == "ok":
        return (
            "none",
            "inspection",
            "Inspection reported status=ok, so no follow-up action is required before continuing local work.",
            signals,
        )
    if failure_code in {"schema-invalid", "stale-latest", "artifact-missing", "artifact-incomplete"}:
        return (
            "rerun",
            "inspection",
            str(failure.get("message") or "Recovery artifacts are unreliable, so rerun the task pipeline from a clean producer run.").strip(),
            signals,
        )
    if failure_code in {"step-failed", "review-needs-fix"} and task_id:
        step_text = failed_step or "the first failing stage"
        return (
            "resume",
            "inspection",
            f"Inspection shows that {step_text} is the current blocking point, so resume is the lowest-cost recovery path after fixing that issue.",
            signals,
        )
    if failure_code == "aborted":
        return (
            "rerun",
            "inspection",
            "The latest task run was intentionally aborted, so restart from a fresh run instead of resuming the frozen artifact set.",
            signals,
        )
    return (
        "inspect",
        "inspection",
        str(failure.get("message") or "Inspect the latest artifacts before choosing resume or fork.").strip(),
        signals,
    )




def _recommendation_from_agent_review(agent_review: dict[str, Any]) -> tuple[str, str, list[str]] | None:
    explain = agent_review.get("explain") if isinstance(agent_review.get("explain"), dict) else {}
    recommended_action = str(explain.get("recommended_action") or agent_review.get("recommended_action") or "").strip().lower()
    if not recommended_action:
        return None
    summary = str(explain.get("summary") or "").strip()
    signals = [f"agent_review.recommended_action={recommended_action}"]
    review_verdict = str(agent_review.get("review_verdict") or "").strip().lower()
    if review_verdict:
        signals.append(f"agent_review.review_verdict={review_verdict}")
    reasons = [str(item).strip() for item in (explain.get("reasons") or []) if str(item).strip()]
    for item in reasons:
        signals.append(f"agent_review.reason={item}")
    return recommended_action, (summary or "Agent review supplied the recovery recommendation."), signals


def _recommendation_from_active_task(active_task: dict[str, Any]) -> tuple[str, str, list[str]] | None:
    recommended_action = str(active_task.get("recommended_action") or "").strip().lower()
    if not recommended_action or recommended_action in {"continue", "none"}:
        return None
    why = str(active_task.get("recommended_action_why") or "").strip()
    clean_state = active_task.get("clean_state") if isinstance(active_task.get("clean_state"), dict) else {}
    signals = [f"active_task.recommended_action={recommended_action}"]
    state = str(clean_state.get("state") or "").strip()
    if state:
        signals.append(f"active_task.clean_state={state}")
    llm_status = str(clean_state.get("llm_status") or "").strip()
    if llm_status:
        signals.append(f"active_task.llm_status={llm_status}")
    for agent in clean_state.get("needs_fix_agents") or []:
        signals.append(f"active_task.needs_fix_agent={agent}")
    for agent in clean_state.get("unknown_agents") or []:
        signals.append(f"active_task.unknown_agent={agent}")
    return recommended_action, (why or "Active task sidecar supplied the recovery recommendation."), signals


def _load_pipeline_summary_from_inspection(repo_root: Path, inspection: dict[str, Any]) -> dict[str, Any]:
    paths = inspection.get("paths") if isinstance(inspection.get("paths"), dict) else {}
    summary_rel = str(paths.get("summary") or "").strip()
    if not summary_rel:
        return {}
    try:
        return _read_json(_resolve_path(repo_root, summary_rel))
    except Exception:
        return {}


def _recommendation_from_pipeline_summary(summary_payload: dict[str, Any]) -> tuple[str, str, list[str]] | None:
    recommended_action = str(summary_payload.get("recommended_action") or "").strip().lower()
    if not recommended_action or recommended_action in {"continue", "none"}:
        return None
    why = str(summary_payload.get("recommended_action_why") or "").strip()
    signals = [f"pipeline_summary.recommended_action={recommended_action}"]
    latest_summary_signals = (
        summary_payload.get("latest_summary_signals")
        if isinstance(summary_payload.get("latest_summary_signals"), dict)
        else {}
    )
    reason = str(latest_summary_signals.get("reason") or "").strip()
    if reason:
        signals.append(f"pipeline_summary.latest_reason={reason}")
    chapter6_hints = summary_payload.get("chapter6_hints") if isinstance(summary_payload.get("chapter6_hints"), dict) else {}
    blocked_by = str(chapter6_hints.get("blocked_by") or "").strip()
    if blocked_by:
        signals.append(f"pipeline_summary.blocked_by={blocked_by}")
    return recommended_action, (why or "Pipeline summary supplied the recovery recommendation."), signals


def _recommendation_from_inspection(inspection: dict[str, Any]) -> tuple[str, str, list[str]] | None:
    recommended_action = str(inspection.get("recommended_action") or "").strip().lower()
    if not recommended_action or recommended_action in {"continue", "none"}:
        return None
    why = str(inspection.get("recommended_action_why") or "").strip()
    signals = [f"inspection.recommended_action={recommended_action}"]
    latest_summary_signals = inspection.get("latest_summary_signals") if isinstance(inspection.get("latest_summary_signals"), dict) else {}
    reason = str(latest_summary_signals.get("reason") or "").strip()
    if reason:
        signals.append(f"inspection.latest_reason={reason}")
    chapter6_hints = inspection.get("chapter6_hints") if isinstance(inspection.get("chapter6_hints"), dict) else {}
    blocked_by = str(chapter6_hints.get("blocked_by") or "").strip()
    if blocked_by:
        signals.append(f"inspection.blocked_by={blocked_by}")
    return recommended_action, (why or "Inspection payload supplied the recovery recommendation."), signals


def _candidate_commands(task_id: str, latest: str) -> dict[str, str]:
    return _shared_candidate_commands(task_id, latest)


def _recommended_command(
    recommended_action: str,
    commands: dict[str, str],
    chapter6_hints: dict[str, Any],
    approval: dict[str, Any] | None = None,
) -> str:
    return _shared_recommended_command(recommended_action, commands, chapter6_hints, approval)


def _forbidden_commands(
    *,
    recommended_action: str,
    commands: dict[str, str],
    chapter6_hints: dict[str, Any],
    approval: dict[str, Any] | None = None,
) -> list[str]:
    return _shared_forbidden_commands(
        recommended_action=recommended_action,
        commands=commands,
        chapter6_hints=chapter6_hints,
        approval=approval,
    )


def build_resume_payload(
    *,
    repo_root: Path,
    task_id: str,
    latest: str,
    run_id: str,
) -> tuple[int, dict[str, Any]]:
    active_task = _load_active_task(repo_root, task_id)
    inspection_rc, inspection = inspect_run_artifacts(
        repo_root=repo_root,
        latest=latest,
        kind="pipeline",
        task_id=task_id,
        run_id=run_id,
    )
    resolved_task_id = str(inspection.get("task_id") or task_id or "").strip()
    resolved_run_id = str(inspection.get("run_id") or run_id or "").strip()
    latest_rel = str(((inspection.get("paths") or {}).get("latest")) or "").strip()
    out_dir_rel = str(((inspection.get("paths") or {}).get("out_dir")) or "").strip()
    active_task = _load_active_task(repo_root, resolved_task_id)
    agent_review = _load_optional_agent_review(repo_root, out_dir_rel)
    pipeline_summary = _load_pipeline_summary_from_inspection(repo_root, inspection)
    inspection_latest_summary = inspection.get("latest_summary_signals") if isinstance(inspection.get("latest_summary_signals"), dict) else {}
    recent_failure_summary = inspection.get("recent_failure_summary") if isinstance(inspection.get("recent_failure_summary"), dict) else {}
    latest_reason = str(inspection_latest_summary.get("reason") or "").strip()
    latest_run_type = str(inspection_latest_summary.get("run_type") or "").strip()
    latest_reuse_mode = str(inspection_latest_summary.get("reuse_mode") or "").strip()
    latest_diagnostics_keys = [
        str(item).strip()
        for item in list(inspection_latest_summary.get("diagnostics_keys") or [])
        if str(item).strip()
    ]
    latest_artifact_integrity_kind = str(inspection_latest_summary.get("artifact_integrity_kind") or "").strip()
    if latest_rel and (
        not latest_reason
        or not latest_run_type
        or not latest_reuse_mode
        or not latest_diagnostics_keys
        or not latest_artifact_integrity_kind
    ):
        latest_path = _resolve_path(repo_root, latest_rel)
        if latest_path.exists():
            try:
                latest_payload = _read_json(latest_path)
            except Exception:
                latest_payload = {}
            latest_reason = latest_reason or str(latest_payload.get("reason") or "").strip()
            latest_run_type = latest_run_type or str(latest_payload.get("run_type") or "").strip()
            latest_reuse_mode = latest_reuse_mode or str(latest_payload.get("reuse_mode") or "").strip()
            latest_diagnostics = latest_payload.get("diagnostics") if isinstance(latest_payload.get("diagnostics"), dict) else {}
            if not latest_diagnostics_keys:
                latest_diagnostics_keys = [str(key).strip() for key in latest_diagnostics.keys() if str(key).strip()]
            if not latest_artifact_integrity_kind:
                latest_artifact_integrity = latest_diagnostics.get("artifact_integrity") if isinstance(latest_diagnostics.get("artifact_integrity"), dict) else {}
                latest_artifact_integrity_kind = str(latest_artifact_integrity.get("kind") or "").strip()
    diagnostics = inspection.get("diagnostics") if isinstance(inspection.get("diagnostics"), dict) else {}
    artifact_integrity = diagnostics.get("artifact_integrity") if isinstance(diagnostics.get("artifact_integrity"), dict) else {}
    latest_artifact_integrity_kind = str(artifact_integrity.get("kind") or "").strip() or latest_artifact_integrity_kind
    chapter6_hints = dict(inspection.get("chapter6_hints") or {}) if isinstance(inspection.get("chapter6_hints"), dict) else {}
    if not chapter6_hints and isinstance(pipeline_summary.get("chapter6_hints"), dict):
        chapter6_hints = dict(pipeline_summary.get("chapter6_hints") or {})
    inspection_candidate_commands = inspection.get("candidate_commands") if isinstance(inspection.get("candidate_commands"), dict) else {}
    candidate_commands = dict(inspection_candidate_commands) if inspection_candidate_commands else _candidate_commands(resolved_task_id, latest or latest_rel)
    summary_candidate_commands = (
        pipeline_summary.get("candidate_commands")
        if isinstance(pipeline_summary.get("candidate_commands"), dict)
        else {}
    )
    for key, value in summary_candidate_commands.items():
        key_text = str(key or "").strip()
        value_text = str(value or "").strip()
        if key_text and value_text:
            candidate_commands[key_text] = value_text
    inspection_signal = _recommendation_from_inspection(inspection)
    if inspection_signal is not None:
        recommended_action, recommendation_reason, blocking_signals = inspection_signal
        recommendation_source = "inspection"
    else:
        summary_signal = _recommendation_from_pipeline_summary(pipeline_summary)
        if summary_signal is not None:
            recommended_action, recommendation_reason, blocking_signals = summary_signal
            recommendation_source = "pipeline-summary"
        else:
            agent_review_signal = _recommendation_from_agent_review(agent_review)
            if agent_review_signal is not None:
                recommended_action, recommendation_reason, blocking_signals = agent_review_signal
                recommendation_source = "agent-review"
            else:
                active_task_signal = _recommendation_from_active_task(active_task)
                if active_task_signal is not None:
                    recommended_action, recommendation_reason, blocking_signals = active_task_signal
                    recommendation_source = "active-task"
                else:
                    recommended_action, recommendation_source, recommendation_reason, blocking_signals = _fallback_recommendation(inspection, resolved_task_id)
    if bool(recent_failure_summary.get("stop_full_rerun_recommended")):
        family = str(recent_failure_summary.get("latest_failure_family") or "").strip()
        same_family_count = int(recent_failure_summary.get("same_family_count") or 0)
        blocking_signals = list(blocking_signals) + [
            f"recent_failure.same_family_count={same_family_count}",
            f"recent_failure.stop_full_rerun_recommended={str(bool(recent_failure_summary.get('stop_full_rerun_recommended'))).lower()}",
        ]
        if family:
            blocking_signals.append(f"recent_failure.family={family}")
    plans = _find_related_docs(repo_root, "execution-plans", task_id=resolved_task_id, run_id=resolved_run_id, latest_rel=latest_rel)
    logs = _find_related_docs(repo_root, "decision-logs", task_id=resolved_task_id, run_id=resolved_run_id, latest_rel=latest_rel)
    active_task_snapshot = _normalized_active_task_snapshot(active_task, inspection_latest=latest_rel)
    bottleneck_fields = _extract_bottleneck_fields(inspection)
    if not bottleneck_fields:
        bottleneck_fields = _extract_bottleneck_fields(pipeline_summary)

    approval = inspection.get("approval") if isinstance(inspection.get("approval"), dict) else {}
    recommended_command = str(inspection.get("recommended_command") or "").strip() or str(pipeline_summary.get("recommended_command") or "").strip() or _recommended_command(
        recommended_action,
        candidate_commands,
        chapter6_hints,
        approval,
    )
    forbidden_commands = [str(item).strip() for item in list(inspection.get("forbidden_commands") or []) if str(item).strip()]
    if not forbidden_commands:
        forbidden_commands = [str(item).strip() for item in list(pipeline_summary.get("forbidden_commands") or []) if str(item).strip()]
    if not forbidden_commands:
        forbidden_commands = _forbidden_commands(
            recommended_action=recommended_action,
            commands=candidate_commands,
            chapter6_hints=chapter6_hints,
            approval=approval,
        )

    payload: dict[str, Any] = {
        "task_id": resolved_task_id,
        "run_id": resolved_run_id,
        "recommended_action": recommended_action,
        "recommended_action_why": recommendation_reason,
        "decision_basis": recommendation_source,
        "blocking_signals": blocking_signals,
        "recommendation_source": recommendation_source,
        "recommendation_reason": recommendation_reason,
        "candidate_commands": candidate_commands,

        "recommended_command": recommended_command,
        "forbidden_commands": forbidden_commands,

        "inspection_exit_code": inspection_rc,
        "inspection": inspection,
        "approval": approval,
        "recent_failure_summary": recent_failure_summary,
        "latest_summary_signals": {
            "reason": latest_reason,
            "run_type": latest_run_type,
            "reuse_mode": latest_reuse_mode,
            "artifact_integrity_kind": latest_artifact_integrity_kind,
            "diagnostics_keys": latest_diagnostics_keys,
        },
        "chapter6_hints": chapter6_hints,
        "related_execution_plans": plans,
        "latest_execution_plan": plans[0] if plans else "",
        "related_decision_logs": logs,
        "latest_decision_log": logs[0] if logs else "",
        "agent_review": {
            "path": str(agent_review.get("_path") or ""),
            "review_verdict": str(agent_review.get("review_verdict") or "").strip(),
            "recommended_action": str(((agent_review.get("explain") or {}).get("recommended_action") or agent_review.get("recommended_action") or "")).strip(),
            "summary": str(((agent_review.get("explain") or {}).get("summary") or "")).strip(),
        },
        "active_task": active_task_snapshot,
        **bottleneck_fields,
    }
    return inspection_rc, payload


def _render_markdown(payload: dict[str, Any]) -> str:
    inspection = payload.get("inspection") or {}
    failure = inspection.get("failure") or {}
    paths = inspection.get("paths") or {}
    commands = payload.get("candidate_commands") or {}
    latest_summary_signals = payload.get("latest_summary_signals") if isinstance(payload.get("latest_summary_signals"), dict) else {}
    chapter6_hints = payload.get("chapter6_hints") if isinstance(payload.get("chapter6_hints"), dict) else {}
    step_duration_totals = payload.get("step_duration_totals") if isinstance(payload.get("step_duration_totals"), dict) else {}
    step_duration_avg = payload.get("step_duration_avg") if isinstance(payload.get("step_duration_avg"), dict) else {}
    round_failure_kind_counts = payload.get("round_failure_kind_counts") if isinstance(payload.get("round_failure_kind_counts"), dict) else {}

    approval = payload.get("approval") if isinstance(payload.get("approval"), dict) else {}

    recommended_command = str(payload.get("recommended_command") or "").strip() or _recommended_command(
        str(payload.get("recommended_action") or ""),
        commands,
        chapter6_hints,

        approval,

    )
    forbidden_commands = [str(item).strip() for item in list(payload.get("forbidden_commands") or []) if str(item).strip()]
    if not forbidden_commands:
        forbidden_commands = _forbidden_commands(
            recommended_action=str(payload.get("recommended_action") or ""),
            commands=commands,
            chapter6_hints=chapter6_hints,

            approval=approval,

        )
    recent_failure_summary = payload.get("recent_failure_summary") if isinstance(payload.get("recent_failure_summary"), dict) else {}
    stop_loss_note = _chapter6_stop_loss_note(chapter6_hints, latest_summary_signals)
    def _line(key: str, value: str) -> str:
        return f"- {key}: {value}"
    lines = [
        "# Task Resume Summary",
        "",
        _line("Task id", f"`{payload.get('task_id')}`" if payload.get("task_id") else "n/a"),
        _line("Run id", f"`{payload.get('run_id')}`" if payload.get("run_id") else "n/a"),
        _line("Recommended action", str(payload.get("recommended_action") or "none")),
        _line("Recommended action why", str(payload.get("recommended_action_why") or "n/a")),
        _line("Decision basis", str(payload.get("decision_basis") or "inspection")),
        _line("Recommendation source", str(payload.get("recommendation_source") or "inspection")),
        _line("Recommendation reason", str(payload.get("recommendation_reason") or "n/a")),
        _line("Inspection status", str(inspection.get("status") or "unknown")),
        _line("Failure code", str(failure.get("code") or "unknown")),
        _line("Recommended command", f"`{recommended_command}`" if recommended_command else "n/a"),
        _line("Forbidden commands", ", ".join(f"`{item}`" for item in forbidden_commands) if forbidden_commands else "none"),
        _line("Latest pointer", f"`{paths.get('latest')}`" if paths.get("latest") else "n/a"),
        _line("Latest reason", str(latest_summary_signals.get("reason") or "n/a")),
        _line("Latest run type", str(latest_summary_signals.get("run_type") or "n/a")),
        _line("Latest reuse mode", str(latest_summary_signals.get("reuse_mode") or "n/a")),
        _line("Latest artifact integrity", str(latest_summary_signals.get("artifact_integrity_kind") or "none")),
        _line(
            "Latest diagnostics keys",
            ", ".join(f"`{item}`" for item in list(latest_summary_signals.get("diagnostics_keys") or []))
            if list(latest_summary_signals.get("diagnostics_keys") or [])
            else "none",
        ),
        _line("Dominant cost phase", str(payload.get("dominant_cost_phase") or "n/a")),
        _line("Step duration totals", _format_metric_map(step_duration_totals) or "none"),
        _line("Step duration avg", _format_metric_map(step_duration_avg) or "none"),
        _line("Round failure kind counts", _format_metric_map(round_failure_kind_counts) or "none"),
        _line("Chapter6 next action", str(chapter6_hints.get("next_action") or "n/a")),
        _line("Chapter6 can skip 6.7", "yes" if bool(chapter6_hints.get("can_skip_6_7")) else "no"),
        _line("Chapter6 can go to 6.8", "yes" if bool(chapter6_hints.get("can_go_to_6_8")) else "no"),
        _line("Chapter6 blocked by", str(chapter6_hints.get("blocked_by") or "n/a")),
        _line("Chapter6 rerun forbidden", "yes" if bool(chapter6_hints.get("rerun_forbidden")) else "no"),
        _line("Chapter6 rerun override", str(chapter6_hints.get("rerun_override_flag") or "n/a")),
        _line("Chapter6 stop-loss note", stop_loss_note or "n/a"),
        _line("Approval required action", str(approval.get("required_action") or "n/a")),
        _line("Approval status", str(approval.get("status") or "n/a")),
        _line("Approval decision", str(approval.get("decision") or "n/a")),
        _line("Approval recommended action", str(approval.get("recommended_action") or "n/a")),
        _line(
            "Approval allowed actions",
            ", ".join(str(item).strip() for item in list(approval.get("allowed_actions") or []) if str(item).strip()) or "none",
        ),
        _line(
            "Approval blocked actions",
            ", ".join(str(item).strip() for item in list(approval.get("blocked_actions") or []) if str(item).strip()) or "none",
        ),
        _line("Approval reason", str(approval.get("reason") or "n/a")),
        _line(
            "Recent failure family",
            str(recent_failure_summary.get("latest_failure_family") or "n/a"),
        ),
        _line(
            "Recent same-family count",
            str(int(recent_failure_summary.get("same_family_count") or 0)) if recent_failure_summary else "0",
        ),
        _line(
            "Recent stop-full-rerun",
            "yes" if bool(recent_failure_summary.get("stop_full_rerun_recommended")) else "no",
        ),
        _line("Pipeline out dir", f"`{paths.get('out_dir')}`" if paths.get("out_dir") else "n/a"),
        _line("Latest execution plan", f"`{payload.get('latest_execution_plan')}`" if payload.get("latest_execution_plan") else "none"),
        _line("Latest decision log", f"`{payload.get('latest_decision_log')}`" if payload.get("latest_decision_log") else "none"),
        _line("Inspect command", f"`{commands.get('inspect')}`" if commands.get("inspect") else "n/a"),
        _line("Resume command", f"`{commands.get('resume')}`" if commands.get("resume") else "n/a"),
        _line("Fork command", f"`{commands.get('fork')}`" if commands.get("fork") else "n/a"),
        _line("Rerun command", f"`{commands.get('rerun')}`" if commands.get("rerun") else "n/a"),
        _line("Needs Fix command", f"`{commands.get('needs_fix_fast')}`" if commands.get("needs_fix_fast") else "n/a"),
    ]
    agent_review = payload.get("agent_review") or {}
    active_task = payload.get("active_task") or {}
    if agent_review.get("path"):
        lines.extend(
            [
                _line("Agent review", f"`{agent_review.get('path')}`"),
                _line("Agent review verdict", str(agent_review.get("review_verdict") or "unknown")),
                _line("Agent review summary", str(agent_review.get("summary") or "n/a")),
            ]
        )
    if active_task.get("path"):
        lines.extend(
            [
                _line("Active task summary", f"`{active_task.get('path')}`"),
                _line("Active task status", str(active_task.get("status") or "unknown")),
                _line("Active task recommendation", str(active_task.get("recommended_action") or "n/a")),
                _line("Active task latest pointer", f"`{active_task.get('latest_json')}`" if active_task.get("latest_json") else "n/a"),
            ]
        )
        if bool(active_task.get("latest_json_repaired")) and active_task.get("reported_latest_json"):
            lines.append(
                _line(
                    "Active task latest pointer repaired from",
                    f"`{active_task.get('reported_latest_json')}`",
                )
            )
        if bool(active_task.get("latest_json_mismatch")) and active_task.get("reported_latest_json"):
            lines.append(
                _line(
                    "Active task reported latest pointer",
                    f"`{active_task.get('reported_latest_json')}`",
                )
            )
    related_plans = payload.get("related_execution_plans") or []
    related_logs = payload.get("related_decision_logs") or []
    blocking_signals = payload.get("blocking_signals") or []
    lines.append(_line("Blocking signals", ", ".join(f"`{item}`" for item in blocking_signals) if blocking_signals else "none"))
    lines.append(_line("Related execution plans", ", ".join(f"`{item}`" for item in related_plans) if related_plans else "none"))
    lines.append(_line("Related decision logs", ", ".join(f"`{item}`" for item in related_logs) if related_logs else "none"))
    lines.append("")
    return "\n".join(lines)


def _render_recommendation_only(payload: dict[str, Any]) -> str:
    fields = _compact_recommendation_payload(payload)
    return "\n".join(f"{key}={value}" for key, value in fields.items()) + "\n"


def _compact_recommendation_payload(payload: dict[str, Any]) -> dict[str, str]:
    return compact_recommendation_fields(payload)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build a task-scoped recovery summary from the latest pipeline artifacts.")
    parser.add_argument("--repo-root", default=str(REPO_ROOT))
    parser.add_argument("--task-id", default="", help="Taskmaster task id.")
    parser.add_argument("--run-id", default="", help="Optional run id filter.")
    parser.add_argument("--latest", default="", help="Optional latest.json path.")
    parser.add_argument("--out-json", default="", help="Optional output JSON path.")
    parser.add_argument("--out-md", default="", help="Optional output Markdown path.")
    parser.add_argument(
        "--recommendation-only",
        action="store_true",
        help="Print a compact recovery recommendation without writing default summary files.",
    )
    parser.add_argument(
        "--recommendation-format",
        default="kv",
        choices=["kv", "json"],
        help="Output format for --recommendation-only.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    task_id = str(args.task_id or "").strip()
    latest = str(args.latest or "").strip()
    if not task_id and not latest:
        print("ERROR: pass --task-id or --latest", file=sys.stderr)
        return 2
    root = Path(str(args.repo_root or REPO_ROOT)).resolve()
    try:
        _, payload = build_resume_payload(
            repo_root=root,
            task_id=task_id,
            latest=latest,
            run_id=str(args.run_id or "").strip(),
        )
    except Exception as exc:
        print(f"ERROR: failed to build task resume summary: {exc}", file=sys.stderr)
        return 2
    active_task = payload.get("active_task") if isinstance(payload.get("active_task"), dict) else {}
    repair = _repair_active_task_latest_pointer(
        root,
        task_id=str(payload.get("task_id") or task_id or "").strip(),
        resolved_latest=str((((payload.get("inspection") or {}).get("paths") or {}).get("latest")) or "").strip(),
    )
    if bool(repair.get("repaired")):
        active_task["latest_json"] = str(repair.get("latest_json") or active_task.get("latest_json") or "").strip()
        active_task["reported_latest_json"] = str(repair.get("reported_latest_json") or active_task.get("reported_latest_json") or "").strip()
        active_task["latest_json_mismatch"] = False
        active_task["latest_json_repaired"] = True
        payload["active_task"] = active_task

    if bool(args.recommendation_only):
        explicit_out_json = str(args.out_json or "").strip()
        explicit_out_md = str(args.out_md or "").strip()
        if explicit_out_json:
            out_json = _resolve_path(root, explicit_out_json)
            out_json.parent.mkdir(parents=True, exist_ok=True)
            out_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
        if explicit_out_md:
            out_md = _resolve_path(root, explicit_out_md)
            out_md.parent.mkdir(parents=True, exist_ok=True)
            out_md.write_text(_render_markdown(payload), encoding="utf-8", newline="\n")
        if str(args.recommendation_format or "kv").strip().lower() == "json":
            print(json.dumps(_compact_recommendation_payload(payload), ensure_ascii=False))
        else:
            print(_render_recommendation_only(payload), end="")
        return 0

    out_json, out_md = _default_output_paths(root, str(payload.get("task_id") or task_id or "unknown"))
    if str(args.out_json or "").strip():
        out_json = _resolve_path(root, str(args.out_json or "").strip())
    if str(args.out_md or "").strip():
        out_md = _resolve_path(root, str(args.out_md or "").strip())
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    out_md.write_text(_render_markdown(payload), encoding="utf-8", newline="\n")
    print(f"TASK_RESUME status=ok out_json={_repo_rel(root, out_json)} out_md={_repo_rel(root, out_md)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
