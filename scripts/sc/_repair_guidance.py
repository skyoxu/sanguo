from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

from _repair_approval import apply_approval_to_recommendations
from _repair_recommendations import (
    build_runtime_recommendations,
    build_step_recommendations,
    extend_with_runtime_recommendations,
)
from _util import repo_root, today_str


def _run_git(args: list[str]) -> str:
    try:
        proc = subprocess.run(
            ["git", *args],
            cwd=str(repo_root()),
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            encoding="utf-8",
            errors="ignore",
            check=False,
        )
    except Exception:
        return ""
    return (proc.stdout or "").strip()


def _latest_markdown_file(root: Path) -> str:
    if not root.exists():
        return ""
    candidates = [path for path in root.rglob("*.md") if path.is_file()]
    if not candidates:
        return ""
    candidates.sort(key=lambda item: item.stat().st_mtime, reverse=True)
    return str(candidates[0])


def build_execution_context(
    *,
    task_id: str,
    requested_run_id: str,
    run_id: str,
    out_dir: Path,
    delivery_profile: str,
    security_profile: str,
    llm_review_context: dict[str, Any] | None,
    summary: dict[str, Any],
    marathon_state: dict[str, Any] | None = None,
    approval_state: dict[str, Any] | None = None,
) -> dict[str, Any]:
    branch = _run_git(["rev-parse", "--abbrev-ref", "HEAD"])
    head = _run_git(["rev-parse", "HEAD"])
    recent_log = [line for line in _run_git(["log", "--oneline", "-n", "8"]).splitlines() if line.strip()]
    status_short = [line for line in _run_git(["status", "--short"]).splitlines() if line.strip()]
    failed_step = next((step for step in summary.get("steps", []) if step.get("status") == "fail"), None)
    return {
        "schema_version": "1.0.0",
        "cmd": "sc-review-pipeline",
        "date": today_str(),
        "task_id": task_id,
        "requested_run_id": requested_run_id,
        "run_id": run_id,
        "status": str(summary.get("status") or "fail"),
        "delivery_profile": delivery_profile,
        "security_profile": security_profile,
        "failed_step": str(failed_step.get("name")) if isinstance(failed_step, dict) else "",
        "paths": {
            "repo_root": str(repo_root()),
            "out_dir": str(out_dir),
            "summary_json": str(out_dir / "summary.json"),
            "marathon_state_json": str(out_dir / "marathon-state.json"),
            "repair_guide_json": str(out_dir / "repair-guide.json"),
            "repair_guide_md": str(out_dir / "repair-guide.md"),
            "approval_request_json": str(out_dir / "approval-request.json"),
            "approval_response_json": str(out_dir / "approval-response.json"),
            "execution_plans_dir": str(repo_root() / "execution-plans"),
            "decision_logs_dir": str(repo_root() / "decision-logs"),
            "latest_execution_plan": _latest_markdown_file(repo_root() / "execution-plans"),
            "latest_decision_log": _latest_markdown_file(repo_root() / "decision-logs"),
            "agents_index": str(repo_root() / "docs" / "agents" / "00-index.md"),
            "agents_recovery": str(repo_root() / "docs" / "agents" / "01-session-recovery.md"),
            "technical_debt_register": str(repo_root() / "docs" / "technical-debt.md"),
            "llm_review_low_priority_findings_json": str(out_dir / "llm-review-low-priority-findings.json"),
        },
        "git": {
            "branch": branch,
            "head": head,
            "recent_log": recent_log,
            "status_short": status_short,
            "dirty": bool(status_short),
        },
        "recovery": {
            "resume_command": f"py -3 scripts/sc/run_review_pipeline.py --task-id {task_id} --resume",
            "abort_command": f"py -3 scripts/sc/run_review_pipeline.py --task-id {task_id} --abort",
            "fork_command": f"py -3 scripts/sc/run_review_pipeline.py --task-id {task_id} --fork",
        },
        "marathon": {
            "status": str((marathon_state or {}).get("status") or ""),
            "next_step_name": str((marathon_state or {}).get("next_step_name") or ""),
            "stop_reason": str((marathon_state or {}).get("stop_reason") or ""),
            "resume_count": int((marathon_state or {}).get("resume_count") or 0),
            "max_step_retries": int((marathon_state or {}).get("max_step_retries") or 0),
            "max_wall_time_sec": int((marathon_state or {}).get("max_wall_time_sec") or 0),
            "context_refresh_needed": bool((marathon_state or {}).get("context_refresh_needed") or False),
            "context_refresh_reasons": list((marathon_state or {}).get("context_refresh_reasons") or []),
            "forked_from_run_id": str((marathon_state or {}).get("forked_from_run_id") or ""),
            "diff_baseline_total_lines": int((((marathon_state or {}).get("diff_stats") or {}).get("baseline") or {}).get("total_lines") or 0),
            "diff_current_total_lines": int((((marathon_state or {}).get("diff_stats") or {}).get("current") or {}).get("total_lines") or 0),
            "diff_growth_total_lines": int((((marathon_state or {}).get("diff_stats") or {}).get("growth") or {}).get("total_lines") or 0),
            "diff_current_categories": list((((marathon_state or {}).get("diff_stats") or {}).get("current") or {}).get("categories") or []),
            "diff_current_axes": list((((marathon_state or {}).get("diff_stats") or {}).get("current") or {}).get("axes") or []),
            "diff_growth_new_categories": list((((marathon_state or {}).get("diff_stats") or {}).get("growth") or {}).get("new_categories") or []),
            "diff_growth_new_axes": list((((marathon_state or {}).get("diff_stats") or {}).get("growth") or {}).get("new_axes") or []),
        },
        "agent_review": {
            "review_verdict": str((((marathon_state or {}).get("agent_review") or {}).get("review_verdict") or "")),
            "recommended_action": str((((marathon_state or {}).get("agent_review") or {}).get("recommended_action") or "")),
            "recommended_refresh_reasons": list((((marathon_state or {}).get("agent_review") or {}).get("recommended_refresh_reasons") or [])),
        },
        "llm_review": dict(llm_review_context or {}),
        "approval": {
            "soft_gate": bool((approval_state or {}).get("soft_gate") or False),
            "required_action": str((approval_state or {}).get("required_action") or ""),
            "status": str((approval_state or {}).get("status") or "not-needed"),
            "decision": str((approval_state or {}).get("decision") or ""),
            "reason": str((approval_state or {}).get("reason") or ""),
            "request_id": str((approval_state or {}).get("request_id") or ""),
            "request_path": str((approval_state or {}).get("request_path") or ""),
            "response_path": str((approval_state or {}).get("response_path") or ""),
        },
    }


def _load_marathon_state(out_dir: Path) -> dict[str, Any] | None:
    state_path = out_dir / "marathon-state.json"
    if not state_path.exists():
        return None
    try:
        payload = json.loads(state_path.read_text(encoding="utf-8"))
    except Exception:
        return None
    return payload if isinstance(payload, dict) else None


def build_repair_guide(
    summary: dict[str, Any],
    *,
    task_id: str,
    out_dir: Path,
    marathon_state: dict[str, Any] | None = None,
    approval_state: dict[str, Any] | None = None,
) -> dict[str, Any]:
    runtime_state = marathon_state if isinstance(marathon_state, dict) else _load_marathon_state(out_dir)
    failed_step = next((step for step in summary.get("steps", []) if step.get("status") == "fail"), None)
    if not isinstance(failed_step, dict):
        recommendations = build_runtime_recommendations(task_id=task_id, out_dir=out_dir, runtime_state=runtime_state)
        recommendations, resolved_approval = apply_approval_to_recommendations(
            task_id=task_id,
            out_dir=out_dir,
            recommendations=recommendations,
            approval_state=approval_state,
        )
        return {
            "schema_version": "1.0.0",
            "status": "needs-fix" if recommendations else "not-needed",
            "task_id": task_id,
            "summary_status": str(summary.get("status") or "ok"),
            "failed_step": "",
            "approval": resolved_approval,
            "recommendations": recommendations,
            "generated_from": {"summary_json": str(out_dir / "summary.json")},
        }

    log_path = Path(str(failed_step.get("log") or ""))
    log_text = ""
    if log_path.exists():
        try:
            log_text = log_path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            log_text = ""
    step_name = str(failed_step.get("name") or "")
    recommendations = build_step_recommendations(task_id=task_id, step_name=step_name, step=failed_step, log_text=log_text)
    recommendations = extend_with_runtime_recommendations(
        task_id=task_id,
        step=failed_step,
        runtime_state=runtime_state,
        recommendations=recommendations,
    )
    recommendations, resolved_approval = apply_approval_to_recommendations(
        task_id=task_id,
        out_dir=out_dir,
        recommendations=recommendations,
        approval_state=approval_state,
    )
    return {
        "schema_version": "1.0.0",
        "status": "needs-fix",
        "task_id": task_id,
        "summary_status": str(summary.get("status") or "fail"),
        "failed_step": step_name,
        "approval": resolved_approval,
        "recommendations": recommendations,
        "generated_from": {
            "summary_json": str(out_dir / "summary.json"),
            "step_log": str(log_path) if log_path.exists() else "",
            "step_summary_file": str(failed_step.get("summary_file") or ""),
        },
    }


def render_repair_guide_markdown(payload: dict[str, Any]) -> str:
    lines: list[str] = []
    lines.append("# Repair Guide")
    lines.append("")
    lines.append(f"- status: {payload.get('status', 'unknown')}")
    lines.append(f"- task_id: {payload.get('task_id', '')}")
    lines.append(f"- summary_status: {payload.get('summary_status', '')}")
    lines.append(f"- failed_step: {payload.get('failed_step', '')}")
    lines.append("")
    approval = payload.get("approval") or {}
    approval_status = str(approval.get("status") or "").strip()
    if approval_status and approval_status != "not-needed":
        lines.append("## Approval")
        lines.append(f"- required_action: {approval.get('required_action', '')}")
        lines.append(f"- status: {approval_status}")
        lines.append(f"- decision: {approval.get('decision', '')}")
        reason = str(approval.get("reason") or "").strip()
        if reason:
            lines.append(f"- reason: {reason}")
        request_path = str(approval.get("request_path") or "").strip()
        response_path = str(approval.get("response_path") or "").strip()
        if request_path:
            lines.append(f"- request: `{request_path}`")
        if response_path:
            lines.append(f"- response: `{response_path}`")
        lines.append("")
    recommendations = payload.get("recommendations") or []
    if not recommendations:
        lines.append("No repair action is required. The pipeline either passed or only produced planned/skipped steps.")
        lines.append("")
        return "\n".join(lines)
    lines.append("## Recommendations")
    for item in recommendations:
        lines.append(f"- {item.get('id', '')}: {item.get('title', '')}")
        why = str(item.get("why") or "").strip()
        if why:
            lines.append(f"  Why: {why}")
        for command in item.get("commands") or []:
            lines.append(f"  Command: `{command}`")
        for file_path in item.get("files") or []:
            if str(file_path).strip():
                lines.append(f"  File: `{file_path}`")
    lines.append("")
    return "\n".join(lines)
