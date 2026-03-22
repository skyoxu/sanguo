from __future__ import annotations

from typing import Any

from _util import today_str


REVIEW_VERDICTS = {"pass", "needs-fix", "block"}
FINDING_SEVERITIES = {"low", "medium", "high"}
RECOMMENDED_ACTIONS = {"none", "resume", "refresh", "fork"}
APPROVAL_STATUSES = {"not-needed", "pending", "approved", "denied", "invalid", "mismatched"}


def _default_explain() -> dict[str, Any]:
    return {
        "recommended_action": "none",
        "summary": "No follow-up action is required because the reviewer did not detect a blocking or repairable issue.",
        "reasons": [],
        "owner_steps": [],
        "categories": [],
        "semantic_axes": [],
        "approval_status": "not-needed",
        "approval_required_action": "",
        "approval_reason": "",
        "approval_blocks_recommended_action": False,
    }


def _default_approval() -> dict[str, Any]:
    return {
        "required_action": "",
        "status": "not-needed",
        "decision": "",
        "reason": "",
        "request_path": "",
        "response_path": "",
    }


def make_review_payload(
    *,
    task_id: str,
    run_id: str,
    pipeline_out_dir: str,
    pipeline_status: str,
    failed_step: str,
    review_verdict: str,
    findings: list[dict[str, Any]],
    explain: dict[str, Any] | None = None,
    approval: dict[str, Any] | None = None,
    reviewer: str = "artifact-reviewer",
) -> dict[str, Any]:
    merged_explain = _default_explain()
    if isinstance(explain, dict):
        merged_explain.update(explain)
    merged_approval = _default_approval()
    if isinstance(approval, dict):
        merged_approval.update(approval)
    return {
        "schema_version": "1.0.0",
        "cmd": "sc-agent-review",
        "date": today_str(),
        "reviewer": reviewer,
        "task_id": str(task_id or "").strip(),
        "run_id": str(run_id or "").strip(),
        "pipeline_out_dir": str(pipeline_out_dir or "").strip(),
        "pipeline_status": str(pipeline_status or "").strip(),
        "failed_step": str(failed_step or "").strip(),
        "review_verdict": str(review_verdict or "").strip(),
        "explain": merged_explain,
        "approval": merged_approval,
        "findings": findings,
    }


def validate_review_payload(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if not isinstance(payload, dict):
        return ["$: payload must be an object"]

    required = {
        "schema_version",
        "cmd",
        "date",
        "reviewer",
        "task_id",
        "run_id",
        "pipeline_out_dir",
        "pipeline_status",
        "failed_step",
        "review_verdict",
        "explain",
        "approval",
        "findings",
    }
    for key in required:
        if key not in payload:
            errors.append(f"$.{key}: missing required property")

    if payload.get("cmd") != "sc-agent-review":
        errors.append("$.cmd: must equal 'sc-agent-review'")
    if str(payload.get("schema_version") or "") != "1.0.0":
        errors.append("$.schema_version: must equal '1.0.0'")
    if not str(payload.get("date") or "").strip():
        errors.append("$.date: must be non-empty string")
    if not str(payload.get("reviewer") or "").strip():
        errors.append("$.reviewer: must be non-empty string")
    if not str(payload.get("task_id") or "").strip():
        errors.append("$.task_id: must be non-empty string")
    if not str(payload.get("run_id") or "").strip():
        errors.append("$.run_id: must be non-empty string")
    if not str(payload.get("pipeline_out_dir") or "").strip():
        errors.append("$.pipeline_out_dir: must be non-empty string")
    if not str(payload.get("pipeline_status") or "").strip():
        errors.append("$.pipeline_status: must be non-empty string")
    if str(payload.get("review_verdict") or "").strip() not in REVIEW_VERDICTS:
        errors.append(f"$.review_verdict: must be one of {sorted(REVIEW_VERDICTS)}")
    explain = payload.get("explain")
    if not isinstance(explain, dict):
        errors.append("$.explain: must be an object")
    else:
        required_explain = {
            "recommended_action",
            "summary",
            "reasons",
            "owner_steps",
            "categories",
            "semantic_axes",
            "approval_status",
            "approval_required_action",
            "approval_reason",
            "approval_blocks_recommended_action",
        }
        for key in required_explain:
            if key not in explain:
                errors.append(f"$.explain.{key}: missing required property")
        if str(explain.get("recommended_action") or "").strip() not in RECOMMENDED_ACTIONS:
            errors.append(f"$.explain.recommended_action: must be one of {sorted(RECOMMENDED_ACTIONS)}")
        if not str(explain.get("summary") or "").strip():
            errors.append("$.explain.summary: must be non-empty string")
        for key in ("reasons", "owner_steps", "categories", "semantic_axes"):
            value = explain.get(key)
            if not isinstance(value, list) or any(not str(item or "").strip() for item in value):
                errors.append(f"$.explain.{key}: must be an array of non-empty strings")
        if str(explain.get("approval_status") or "").strip() not in APPROVAL_STATUSES:
            errors.append(f"$.explain.approval_status: must be one of {sorted(APPROVAL_STATUSES)}")
        if not isinstance(explain.get("approval_blocks_recommended_action"), bool):
            errors.append("$.explain.approval_blocks_recommended_action: must be boolean")
        for key in ("approval_required_action", "approval_reason"):
            value = explain.get(key)
            if not isinstance(value, str):
                errors.append(f"$.explain.{key}: must be a string")

    approval = payload.get("approval")
    if not isinstance(approval, dict):
        errors.append("$.approval: must be an object")
    else:
        required_approval = {"required_action", "status", "decision", "reason", "request_path", "response_path"}
        for key in required_approval:
            if key not in approval:
                errors.append(f"$.approval.{key}: missing required property")
        if str(approval.get("status") or "").strip() not in APPROVAL_STATUSES:
            errors.append(f"$.approval.status: must be one of {sorted(APPROVAL_STATUSES)}")
        for key in ("required_action", "decision", "reason", "request_path", "response_path"):
            if not isinstance(approval.get(key), str):
                errors.append(f"$.approval.{key}: must be a string")

    findings = payload.get("findings")
    if not isinstance(findings, list):
        errors.append("$.findings: must be an array")
        return errors

    allowed_finding = {
        "finding_id",
        "severity",
        "category",
        "owner_step",
        "evidence_path",
        "message",
        "suggested_fix",
        "commands",
    }
    for index, finding in enumerate(findings):
        base = f"$.findings[{index}]"
        if not isinstance(finding, dict):
            errors.append(f"{base}: must be an object")
            continue
        for key in ("finding_id", "severity", "category", "owner_step", "evidence_path", "message", "suggested_fix", "commands"):
            if key not in finding:
                errors.append(f"{base}.{key}: missing required property")
        for key in finding.keys():
            if key not in allowed_finding:
                errors.append(f"{base}.{key}: unexpected property")
        if not str(finding.get("finding_id") or "").strip():
            errors.append(f"{base}.finding_id: must be non-empty string")
        if str(finding.get("severity") or "").strip() not in FINDING_SEVERITIES:
            errors.append(f"{base}.severity: must be one of {sorted(FINDING_SEVERITIES)}")
        for key in ("category", "owner_step", "evidence_path", "message", "suggested_fix"):
            if not str(finding.get(key) or "").strip():
                errors.append(f"{base}.{key}: must be non-empty string")
        commands = finding.get("commands")
        if not isinstance(commands, list) or any(not str(item or "").strip() for item in commands):
            errors.append(f"{base}.commands: must be an array of non-empty strings")
    return errors


def render_review_markdown(payload: dict[str, Any]) -> str:
    lines: list[str] = []
    lines.append("# Agent Review")
    lines.append("")
    lines.append(f"- reviewer: {payload.get('reviewer', '')}")
    lines.append(f"- task_id: {payload.get('task_id', '')}")
    lines.append(f"- run_id: {payload.get('run_id', '')}")
    lines.append(f"- pipeline_status: {payload.get('pipeline_status', '')}")
    lines.append(f"- failed_step: {payload.get('failed_step', '')}")
    lines.append(f"- review_verdict: {payload.get('review_verdict', '')}")
    explain = payload.get("explain") or {}
    lines.append(f"- recommended_action: {explain.get('recommended_action', '')}")
    if str(explain.get("summary") or "").strip():
        lines.append(f"- explain: {explain.get('summary', '')}")
    lines.append(f"- approval_status: {explain.get('approval_status', '')}")
    if bool(explain.get("approval_blocks_recommended_action")):
        lines.append("- approval_blocks_recommended_action: true")
    lines.append("")
    approval = payload.get("approval") or {}
    if str(approval.get("status") or "").strip() != "not-needed":
        lines.append("## Approval")
        lines.append(f"- required_action: {approval.get('required_action', '')}")
        lines.append(f"- status: {approval.get('status', '')}")
        lines.append(f"- decision: {approval.get('decision', '')}")
        if str(approval.get("reason") or "").strip():
            lines.append(f"- reason: {approval.get('reason', '')}")
        if str(approval.get("request_path") or "").strip():
            lines.append(f"- request: `{approval.get('request_path', '')}`")
        if str(approval.get("response_path") or "").strip():
            lines.append(f"- response: `{approval.get('response_path', '')}`")
        lines.append("")
    findings = payload.get("findings") or []
    if not findings:
        lines.append("No findings.")
        lines.append("")
        return "\n".join(lines)
    lines.append("## Findings")
    for finding in findings:
        lines.append(
            f"- {finding.get('finding_id', '')}: severity={finding.get('severity', '')}, "
            f"category={finding.get('category', '')}, owner_step={finding.get('owner_step', '')}"
        )
        lines.append(f"  Message: {finding.get('message', '')}")
        lines.append(f"  Evidence: `{finding.get('evidence_path', '')}`")
        lines.append(f"  Suggested fix: {finding.get('suggested_fix', '')}")
        for command in finding.get("commands") or []:
            lines.append(f"  Command: `{command}`")
    lines.append("")
    return "\n".join(lines)
