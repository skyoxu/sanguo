#!/usr/bin/env python3
"""
Normalize local review artifacts into a stable agent-to-agent review contract.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from _artifact_schema import (
    ArtifactSchemaError,
    validate_pipeline_execution_context_payload,
    validate_pipeline_latest_index_payload,
    validate_pipeline_repair_guide_payload,
)
from _agent_review_contract import make_review_payload, render_review_markdown, validate_review_payload
from _agent_review_policy import build_agent_review_explain, summarize_agent_review
from _util import repo_root, write_json, write_text

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build an agent-to-agent review contract from local review artifacts.")
    parser.add_argument("--pipeline-out-dir", default="", help="Explicit sc-review-pipeline output directory.")
    parser.add_argument("--task-id", default="", help="Task id used to resolve the latest pipeline run when --pipeline-out-dir is omitted.")
    parser.add_argument("--run-id", default="", help="Optional run id to resolve a specific pipeline run.")
    parser.add_argument("--reviewer", default="artifact-reviewer", help="Reviewer identity written into the contract.")
    parser.add_argument("--strict", action="store_true", help="Return non-zero on `needs-fix` as well as `block`.")
    return parser

def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _resolve_optional_file_path(raw_path: Any) -> Path | None:
    candidate = str(raw_path or "").strip()
    if not candidate:
        return None
    path = Path(candidate)
    if not path.is_absolute():
        path = (repo_root() / path).resolve()
    if not path.exists() or not path.is_file():
        return None
    return path


def _latest_index_candidates(task_id: str) -> list[Path]:
    root = repo_root() / "logs" / "ci"
    pattern = f"*/sc-review-pipeline-task-{task_id}/latest.json"
    candidates = [path for path in root.glob(pattern) if path.is_file()]
    candidates.sort(key=lambda item: item.stat().st_mtime, reverse=True)
    return candidates


def _build_block_payload(*, out_dir: Path, reviewer: str, errors: list[str], message: str, suggested_fix: str) -> dict[str, Any]:
    signal = summarize_agent_review(
        {
            "review_verdict": "block",
            "findings": [
                _build_finding(
                    finding_id="artifact-integrity",
                    severity="high",
                    category="artifact-integrity",
                    owner_step="producer-pipeline",
                    evidence_path=str(out_dir),
                    message=message,
                    suggested_fix=suggested_fix,
                    commands=[],
                )
            ],
        }
    )
    return make_review_payload(
        task_id="unknown",
        run_id="unknown",
        pipeline_out_dir=str(out_dir),
        pipeline_status="artifact-integrity",
        failed_step="",
        review_verdict="block",
        reviewer=reviewer,
        explain=build_agent_review_explain(signal),
        findings=[
            _build_finding(
                finding_id="artifact-integrity",
                severity="high",
                category="artifact-integrity",
                owner_step="producer-pipeline",
                evidence_path=str(out_dir),
                message=message,
                suggested_fix=suggested_fix,
                commands=[],
            )
        ],
    )


def _pipeline_dir_candidates(task_id: str, run_id: str) -> list[Path]:
    root = repo_root() / "logs" / "ci"
    pattern = f"*/sc-review-pipeline-task-{task_id}-{run_id}"
    candidates = [path for path in root.glob(pattern) if path.is_dir()]
    candidates.sort(key=lambda item: item.stat().st_mtime, reverse=True)
    return candidates


def resolve_pipeline_out_dir(args: argparse.Namespace) -> Path:
    explicit = str(args.pipeline_out_dir or "").strip()
    if explicit:
        path = Path(explicit)
        return path if path.is_absolute() else (repo_root() / path).resolve()

    task_id = str(args.task_id or "").strip()
    run_id = str(args.run_id or "").strip()
    if task_id and run_id:
        candidates = _pipeline_dir_candidates(task_id, run_id)
        if candidates:
            return candidates[0]
    if task_id:
        indexes = _latest_index_candidates(task_id)
        for candidate in indexes:
            try:
                latest = _load_json(candidate)
                validate_pipeline_latest_index_payload(latest)
            except (OSError, ValueError, json.JSONDecodeError, ArtifactSchemaError):
                continue
            out_dir = Path(str(latest.get("latest_out_dir") or "").strip())
            if out_dir.is_absolute():
                return out_dir
            return (repo_root() / out_dir).resolve()
    raise FileNotFoundError("Unable to resolve pipeline output directory. Use --pipeline-out-dir or provide --task-id.")


def _build_finding(
    *,
    finding_id: str,
    severity: str,
    category: str,
    owner_step: str,
    evidence_path: str,
    message: str,
    suggested_fix: str,
    commands: list[str],
) -> dict[str, Any]:
    return {
        "finding_id": finding_id,
        "severity": severity,
        "category": category,
        "owner_step": owner_step,
        "evidence_path": evidence_path,
        "message": message,
        "suggested_fix": suggested_fix,
        "commands": commands,
    }


def _build_step_failure_finding(step: dict[str, Any], repair: dict[str, Any]) -> dict[str, Any]:
    step_name = str(step.get("name") or "")
    severity = "high" if step_name in {"sc-test", "sc-acceptance-check"} else "medium"
    recommendations = repair.get("recommendations") or []
    first_rec = recommendations[0] if recommendations else {}
    commands = [str(cmd) for cmd in (first_rec.get("commands") or []) if str(cmd).strip()]
    suggested_fix = str(first_rec.get("title") or "Open repair-guide.md and fix the first failing step.")
    message = f"{step_name} failed in the producer pipeline."
    return _build_finding(
        finding_id=f"{step_name}-failed",
        severity=severity,
        category="pipeline-step-failed",
        owner_step=step_name,
        evidence_path=str(step.get("log") or step.get("summary_file") or ""),
        message=message,
        suggested_fix=suggested_fix,
        commands=commands,
    )


def _build_llm_findings(llm_summary: dict[str, Any]) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    for result in llm_summary.get("results") or []:
        if not isinstance(result, dict):
            continue
        details = result.get("details") or {}
        verdict = str(details.get("verdict") or "").strip()
        if verdict in {"", "OK"}:
            continue
        agent = str(result.get("agent") or "unknown-agent")
        evidence_path = str(result.get("output_path") or details.get("trace") or "")
        findings.append(
            _build_finding(
                finding_id=f"llm-{agent}-{verdict.lower().replace(' ', '-')}",
                severity="medium",
                category="llm-review",
                owner_step="sc-llm-review",
                evidence_path=evidence_path,
                message=f"{agent} reported verdict `{verdict}`.",
                suggested_fix="Review the agent output, address the referenced issue, then rerun llm_review or the full pipeline.",
                commands=[],
            )
        )
    return findings


def _normalize_approval(repair_guide: dict[str, Any], execution_context: dict[str, Any]) -> dict[str, Any]:
    payload = repair_guide.get("approval")
    if not isinstance(payload, dict):
        payload = execution_context.get("approval")
    source = payload if isinstance(payload, dict) else {}
    return {
        "required_action": str(source.get("required_action") or "").strip(),
        "status": str(source.get("status") or "not-needed").strip(),
        "decision": str(source.get("decision") or "").strip(),
        "reason": str(source.get("reason") or "").strip(),
        "request_path": str(source.get("request_path") or "").strip(),
        "response_path": str(source.get("response_path") or "").strip(),
    }


def _merge_approval_into_explain(explain: dict[str, Any], approval: dict[str, Any]) -> dict[str, Any]:
    merged = dict(explain)
    approval_status = str(approval.get("status") or "not-needed").strip() or "not-needed"
    approval_required_action = str(approval.get("required_action") or "").strip()
    approval_reason = str(approval.get("reason") or "").strip()
    recommended_action = str(merged.get("recommended_action") or "").strip()
    blocks = bool(
        approval_required_action
        and approval_required_action == recommended_action
        and approval_status in {"pending", "denied", "invalid", "mismatched"}
    )
    merged["approval_status"] = approval_status
    merged["approval_required_action"] = approval_required_action
    merged["approval_reason"] = approval_reason
    merged["approval_blocks_recommended_action"] = blocks

    if approval_required_action:
        suffix = f" Approval status is {approval_status} for `{approval_required_action}`."
        if approval_reason:
            suffix += f" Reason: {approval_reason}"
        summary = str(merged.get("summary") or "").strip()
        if suffix.strip() not in summary:
            merged["summary"] = (summary + suffix).strip()
        reasons = [str(item) for item in (merged.get("reasons") or []) if str(item).strip()]
        reasons.append(f"approval:{approval_required_action}:{approval_status}")
        if approval_reason:
            reasons.append(f"approval_reason:{approval_reason}")
        merged["reasons"] = list(dict.fromkeys(reasons))
    return merged


def build_agent_review(*, out_dir: Path, reviewer: str) -> tuple[dict[str, Any], list[str]]:
    errors: list[str] = []
    summary_path = out_dir / "summary.json"
    execution_context_path = out_dir / "execution-context.json"
    repair_guide_path = out_dir / "repair-guide.json"
    if not summary_path.exists():
        errors.append(f"missing required file: {summary_path}")
    if not execution_context_path.exists():
        errors.append(f"missing required file: {execution_context_path}")
    if not repair_guide_path.exists():
        errors.append(f"missing required file: {repair_guide_path}")
    if errors:
        payload = _build_block_payload(
            out_dir=out_dir,
            reviewer=reviewer,
            errors=errors,
            message="The reviewer could not find the required producer artifacts.",
            suggested_fix="Re-run scripts/sc/run_review_pipeline.py so summary, execution-context, and repair-guide are regenerated.",
        )
        return payload, errors

    summary = _load_json(summary_path)
    try:
        execution_context = _load_json(execution_context_path)
        validate_pipeline_execution_context_payload(execution_context)
        repair_guide = _load_json(repair_guide_path)
        validate_pipeline_repair_guide_payload(repair_guide)
    except (OSError, ValueError, json.JSONDecodeError, ArtifactSchemaError) as exc:
        errors.append(f"sidecar schema validation failed: {exc}")
        payload = _build_block_payload(
            out_dir=out_dir,
            reviewer=reviewer,
            errors=errors,
            message="The reviewer rejected producer sidecars because execution-context.json or repair-guide.json drifted from the consumed contract.",
            suggested_fix="Regenerate the pipeline artifacts so execution-context.json and repair-guide.json match the current consumer contract.",
        )
        return payload, errors
    approval = _normalize_approval(repair_guide, execution_context)
    failed_step = next((step for step in summary.get("steps", []) if step.get("status") == "fail"), None)

    findings: list[dict[str, Any]] = []
    if isinstance(failed_step, dict):
        findings.append(_build_step_failure_finding(failed_step, repair_guide))

    llm_step = next((step for step in summary.get("steps", []) if step.get("name") == "sc-llm-review"), None)
    llm_summary_path = _resolve_optional_file_path(llm_step.get("summary_file")) if isinstance(llm_step, dict) else None
    if llm_summary_path:
        try:
            llm_summary = _load_json(llm_summary_path)
            findings.extend(_build_llm_findings(llm_summary))
        except Exception as exc:  # noqa: BLE001
            findings.append(
                _build_finding(
                    finding_id="llm-summary-invalid",
                    severity="medium",
                    category="artifact-integrity",
                    owner_step="sc-llm-review",
                    evidence_path=str(llm_summary_path),
                    message=f"Could not parse llm review summary: {exc}",
                    suggested_fix="Regenerate the llm review output before relying on reviewer verdicts.",
                    commands=[],
                )
            )

    pipeline_status = str(summary.get("status") or "fail")
    failed_step_name = str(execution_context.get("failed_step") or "")
    review_verdict = "pass"
    if any(f.get("category") == "artifact-integrity" and f.get("severity") == "high" for f in findings):
        review_verdict = "block"
    elif pipeline_status == "fail" and failed_step_name in {"sc-test", "sc-acceptance-check"}:
        review_verdict = "block"
    elif findings:
        review_verdict = "needs-fix"

    signal = summarize_agent_review(
        {
            "review_verdict": review_verdict,
            "findings": findings,
        }
    )
    payload = make_review_payload(
        task_id=str(summary.get("task_id") or execution_context.get("task_id") or ""),
        run_id=str(summary.get("run_id") or execution_context.get("run_id") or ""),
        pipeline_out_dir=str(out_dir),
        pipeline_status=pipeline_status,
        failed_step=failed_step_name,
        review_verdict=review_verdict,
        explain=_merge_approval_into_explain(build_agent_review_explain(signal), approval),
        approval=approval,
        findings=findings,
        reviewer=reviewer,
    )
    return payload, errors


def write_agent_review(*, out_dir: Path, reviewer: str) -> tuple[dict[str, Any], list[str], list[str]]:
    payload, resolve_errors = build_agent_review(out_dir=out_dir, reviewer=reviewer)
    validation_errors = validate_review_payload(payload)
    report_path = out_dir / "agent-review.json"
    report_md_path = out_dir / "agent-review.md"

    write_json(report_path, payload)
    write_text(report_md_path, render_review_markdown(payload))
    _update_latest_index(payload, out_dir=out_dir)
    return payload, resolve_errors, validation_errors


def _update_latest_index(payload: dict[str, Any], *, out_dir: Path) -> None:
    task_id = str(payload.get("task_id") or "").strip()
    if not task_id:
        return
    latest_candidates = _latest_index_candidates(task_id)
    if not latest_candidates:
        return
    latest_path = latest_candidates[0]
    try:
        latest = _load_json(latest_path)
        validate_pipeline_latest_index_payload(latest)
    except Exception:
        return
    latest["agent_review_json_path"] = str(out_dir / "agent-review.json")
    latest["agent_review_md_path"] = str(out_dir / "agent-review.md")
    write_json(latest_path, latest)


def main() -> int:
    args = build_parser().parse_args()
    out_dir = resolve_pipeline_out_dir(args)
    payload, resolve_errors, validation_errors = write_agent_review(
        out_dir=out_dir,
        reviewer=str(args.reviewer or "artifact-reviewer").strip(),
    )

    if resolve_errors:
        for item in resolve_errors:
            print(f"[sc-agent-review] ERROR: {item}")
    if validation_errors:
        for item in validation_errors:
            print(f"[sc-agent-review] ERROR: {item}")
        print(f"SC_AGENT_REVIEW status=block out={out_dir}")
        return 2

    print(f"SC_AGENT_REVIEW status={payload['review_verdict']} out={out_dir}")
    if payload["review_verdict"] == "block":
        return 1
    if payload["review_verdict"] == "needs-fix" and bool(args.strict):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
