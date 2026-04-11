#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
PYTHON_DIR = REPO_ROOT / "scripts" / "python"
SC_DIR = REPO_ROOT / "scripts" / "sc"
for candidate in (PYTHON_DIR, SC_DIR):
    if str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))

from _change_scope import classify_change_scope_between_snapshots  # noqa: E402
from _recovery_doc_scaffold import record_chapter6_residual_followup  # noqa: E402
from llm_review_needs_fix_fast import _changed_paths_hit_reviewer_anchors, current_git_fingerprint  # noqa: E402
from resume_task import build_resume_payload  # noqa: E402


_REPO_NOISE_TOKENS = (
    "being used by another process",
    "sharing violation",
    "file is locked",
    "access is denied",
    "permission denied",
    "could not find a part of the path",
    "network path was not found",
    "connection reset",
    "connection aborted",
    "unable to write to the transport connection",
)


def _contains_repo_noise_token(value: Any) -> bool:
    text = str(value or "").strip().lower()
    if not text:
        return False
    return any(token in text for token in _REPO_NOISE_TOKENS)


def _resolve_path(root: Path, raw_value: str) -> Path | None:
    value = str(raw_value or "").strip()
    if not value:
        return None
    path = Path(value)
    if not path.is_absolute():
        path = root / path
    return path.resolve()


def _read_json(path: Path | None) -> dict[str, Any]:
    if path is None or not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def _load_execution_context(root: Path, payload: dict[str, Any]) -> dict[str, Any]:
    inspection = payload.get("inspection") if isinstance(payload.get("inspection"), dict) else {}
    paths = inspection.get("paths") if isinstance(inspection.get("paths"), dict) else {}
    execution_context_path = _resolve_path(root, str(paths.get("execution_context") or ""))
    return _read_json(execution_context_path)


def _load_agent_review(root: Path, payload: dict[str, Any]) -> dict[str, Any]:
    inspection = payload.get("inspection") if isinstance(payload.get("inspection"), dict) else {}
    paths = inspection.get("paths") if isinstance(inspection.get("paths"), dict) else {}
    out_dir = _resolve_path(root, str(paths.get("out_dir") or ""))
    if out_dir is None:
        return {}
    return _read_json(out_dir / "agent-review.json")


def _load_low_priority_findings(root: Path, payload: dict[str, Any]) -> list[dict[str, str]]:
    inspection = payload.get("inspection") if isinstance(payload.get("inspection"), dict) else {}
    paths = inspection.get("paths") if isinstance(inspection.get("paths"), dict) else {}
    out_dir = _resolve_path(root, str(paths.get("out_dir") or ""))
    if out_dir is None:
        return []
    low_priority = _read_json(out_dir / "llm-review-low-priority-findings.json")
    findings = low_priority.get("findings")
    if not isinstance(findings, list):
        return []
    out: list[dict[str, str]] = []
    for item in findings:
        if not isinstance(item, dict):
            continue
        severity = str(item.get("severity") or "").strip().upper()
        message = str(item.get("message") or "").strip()
        agent = str(item.get("agent") or "").strip() or "unknown-agent"
        source_path = str(item.get("source_path") or "").strip()
        if severity and message:
            out.append(
                {
                    "severity": severity,
                    "message": message,
                    "agent": agent,
                    "source_path": source_path,
                }
            )
    return out


def _derive_change_scope(execution_context: dict[str, Any]) -> dict[str, Any]:
    previous_git = execution_context.get("git") if isinstance(execution_context.get("git"), dict) else {}
    current_git = current_git_fingerprint()
    if not previous_git:
        return {"changed_paths": list(current_git.get("status_short") or [])}
    return classify_change_scope_between_snapshots(previous_git=previous_git, current_git=current_git)


def _classify_repo_noise(payload: dict[str, Any]) -> tuple[str, str]:
    inspection = payload.get("inspection") if isinstance(payload.get("inspection"), dict) else {}
    failure = inspection.get("failure") if isinstance(inspection.get("failure"), dict) else {}
    latest_summary_signals = payload.get("latest_summary_signals") if isinstance(payload.get("latest_summary_signals"), dict) else {}
    chapter6_hints = payload.get("chapter6_hints") if isinstance(payload.get("chapter6_hints"), dict) else {}
    recent_failure_summary = payload.get("recent_failure_summary") if isinstance(payload.get("recent_failure_summary"), dict) else {}
    failure_code = str(failure.get("code") or "").strip().lower()
    latest_reason = str(latest_summary_signals.get("reason") or "").strip().lower()
    blocked_by = str(chapter6_hints.get("blocked_by") or "").strip().lower()

    if latest_reason.startswith("rerun_blocked:chapter6_route_repo_noise_stop"):
        return "repo-noise", "prior chapter6-route already classified this run as repo-noise"
    if blocked_by == "recent_failure_summary":
        latest_family = str(recent_failure_summary.get("latest_failure_family") or "").strip()
        recommendation_basis = str(recent_failure_summary.get("recommendation_basis") or "").strip()
        if _contains_repo_noise_token(latest_family) or _contains_repo_noise_token(recommendation_basis):
            return "repo-noise", "recent failure family repeats a repo-noise signature"

    message_parts = [
        str(failure_code or ""),
        str(failure.get("message") or ""),
        " ".join(str(item) for item in list(inspection.get("validation_errors") or [])),
        " ".join(str(item) for item in list(inspection.get("missing_artifacts") or [])),
        str(latest_summary_signals.get("reason") or ""),
        str(recent_failure_summary.get("latest_failure_family") or ""),
        str(recent_failure_summary.get("recommendation_basis") or ""),
    ]
    combined = " ".join(part.lower() for part in message_parts if part).strip()
    if _contains_repo_noise_token(combined):
        return "repo-noise", "high-confidence lock/transport/process contention signal detected"
    return "task-issue", ""


def _residual_reason_from_agent_review(agent_review: dict[str, Any]) -> tuple[bool, str]:
    findings = agent_review.get("findings")
    if not isinstance(findings, list) or not findings:
        return False, "no_agent_review_findings"
    severities = {str(item.get("severity") or "").strip().lower() for item in findings if isinstance(item, dict)}
    if "high" in severities:
        return False, "high_severity_finding_present"
    if severities & {"medium", "low"}:
        return True, "only_medium_or_low_findings_remain"
    return False, "no_low_priority_findings"


def _summarize_low_priority_findings(findings: list[dict[str, str]]) -> str:
    if not findings:
        return "No low priority findings were captured."
    parts: list[str] = []
    for item in findings[:5]:
        severity = str(item.get("severity") or "").strip()
        agent = str(item.get("agent") or "").strip()
        message = str(item.get("message") or "").strip()
        if severity and agent:
            parts.append(f"{severity} [{agent}] {message}")
        elif severity:
            parts.append(f"{severity} {message}")
        else:
            parts.append(message)
    if len(findings) > 5:
        parts.append(f"... and {len(findings) - 5} more")
    return "; ".join(parts)


def _record_residual_docs(
    *,
    root: Path,
    payload: dict[str, Any],
    low_priority_findings: list[dict[str, str]],
) -> dict[str, Any]:
    task_id = str(payload.get("task_id") or "").strip()
    run_id = str(payload.get("run_id") or "").strip()
    inspection = payload.get("inspection") if isinstance(payload.get("inspection"), dict) else {}
    paths = inspection.get("paths") if isinstance(inspection.get("paths"), dict) else {}
    latest_rel = str(paths.get("latest") or "").strip()
    findings_summary = _summarize_low_priority_findings(low_priority_findings)
    recorded = record_chapter6_residual_followup(
        root=root,
        task_id=task_id,
        run_id=run_id,
        latest_json=latest_rel,
        findings_summary=findings_summary,
        recommended_command=str(payload.get("recommended_command") or "").strip(),
    )

    return {
        "eligible": True,
        "reason": "recorded",
        "performed": True,
        "decision_log_path": str(recorded.get("decision_log_path") or "").strip(),
        "execution_plan_path": str(recorded.get("execution_plan_path") or "").strip(),
    }


def route_chapter6(
    *,
    repo_root: Path,
    task_id: str,
    latest: str = "",
    run_id: str = "",
    record_residual: bool = False,
) -> tuple[int, dict[str, Any]]:
    root = Path(repo_root).resolve()
    _, payload = build_resume_payload(
        repo_root=root,
        task_id=str(task_id or "").strip(),
        latest=str(latest or "").strip(),
        run_id=str(run_id or "").strip(),
    )
    execution_context = _load_execution_context(root, payload)
    change_scope = _derive_change_scope(execution_context)
    changed_paths = [str(item or "").strip().replace("\\", "/") for item in list(change_scope.get("changed_paths") or []) if str(item or "").strip()]
    reviewer_anchor_hit = _changed_paths_hit_reviewer_anchors(changed_paths)
    agent_review = _load_agent_review(root, payload)
    low_priority_findings = _load_low_priority_findings(root, payload)

    inspection = payload.get("inspection") if isinstance(payload.get("inspection"), dict) else {}
    failure = inspection.get("failure") if isinstance(inspection.get("failure"), dict) else {}
    latest_summary_signals = payload.get("latest_summary_signals") if isinstance(payload.get("latest_summary_signals"), dict) else {}
    chapter6_hints = payload.get("chapter6_hints") if isinstance(payload.get("chapter6_hints"), dict) else {}
    candidate_commands = payload.get("candidate_commands") if isinstance(payload.get("candidate_commands"), dict) else {}
    recommended_action = str(payload.get("recommended_action") or "").strip().lower()
    repo_noise_classification, repo_noise_reason = _classify_repo_noise(payload)
    six_eight_worthwhile = bool(chapter6_hints.get("can_go_to_6_8")) and recommended_action == "needs-fix-fast" and reviewer_anchor_hit
    full_67_recommended = (
        recommended_action in {"rerun", "fork"}
        and not bool(chapter6_hints.get("rerun_forbidden"))
        and str(chapter6_hints.get("blocked_by") or "").strip().lower() != "artifact_integrity"
        and str(latest_summary_signals.get("reason") or "").strip().lower() != "planned_only_incomplete"
    )

    residual_eligible, residual_reason = _residual_reason_from_agent_review(agent_review)
    residual_recording: dict[str, Any] = {
        "eligible": residual_eligible,
        "reason": residual_reason,
        "performed": False,
        "decision_log_path": "",
        "execution_plan_path": "",
    }

    preferred_lane = "inspect-first"
    recommended_command = str(payload.get("recommended_command") or "").strip() or str(candidate_commands.get("inspect") or "").strip()

    if repo_noise_classification == "repo-noise":
        preferred_lane = "repo-noise-stop"
        recommended_command = str(candidate_commands.get("inspect") or recommended_command)
    elif str(chapter6_hints.get("blocked_by") or "").strip().lower() == "artifact_integrity":
        preferred_lane = "inspect-first"
        recommended_command = str(candidate_commands.get("rerun") or recommended_command)
    elif str(failure.get("code") or "").strip().lower() == "step-failed" or str(chapter6_hints.get("blocked_by") or "").strip().lower() in {
        "deterministic_failure",
        "sc_test_retry_stop_loss",
        "waste_signals",
    }:
        preferred_lane = "fix-deterministic"
    elif six_eight_worthwhile:
        preferred_lane = "run-6.8"
        recommended_command = str(candidate_commands.get("needs_fix_fast") or recommended_command)
    elif record_residual and residual_eligible:
        residual_recording = _record_residual_docs(root=root, payload=payload, low_priority_findings=low_priority_findings)
        preferred_lane = "record-residual"
        recommended_command = str(candidate_commands.get("inspect") or recommended_command)
    elif full_67_recommended:
        preferred_lane = "run-6.7"
        recommended_command = str(candidate_commands.get("rerun") or recommended_command)

    route_payload = {
        "task_id": str(payload.get("task_id") or "").strip(),
        "run_id": str(payload.get("run_id") or "").strip(),
        "preferred_lane": preferred_lane,
        "recommended_command": recommended_command or "n/a",
        "forbidden_commands": [str(item).strip() for item in list(payload.get("forbidden_commands") or []) if str(item).strip()],
        "reviewer_anchor_hit": reviewer_anchor_hit,
        "changed_paths": changed_paths,
        "six_eight_worthwhile": six_eight_worthwhile,
        "full_67_recommended": full_67_recommended,
        "repo_noise_classification": repo_noise_classification,
        "repo_noise_reason": repo_noise_reason,
        "recommended_action": recommended_action or "none",
        "recommended_action_why": str(payload.get("recommended_action_why") or "").strip(),
        "latest_reason": str(latest_summary_signals.get("reason") or "").strip(),
        "chapter6_next_action": str(chapter6_hints.get("next_action") or "").strip(),
        "blocked_by": str(chapter6_hints.get("blocked_by") or "").strip(),
        "residual_recording": residual_recording,
    }
    return 0, route_payload


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Route Chapter 6 recovery decisions through a stable artifact-aware entrypoint.")
    parser.add_argument("--repo-root", default=str(REPO_ROOT))
    parser.add_argument("--task-id", default="", help="Taskmaster task id.")
    parser.add_argument("--run-id", default="", help="Optional run id filter.")
    parser.add_argument("--latest", default="", help="Optional latest.json path.")
    parser.add_argument("--record-residual", action="store_true", help="Write decision-log/execution-plan scaffolds when only low-priority findings remain.")
    parser.add_argument("--out-json", default="", help="Optional output JSON path.")
    parser.add_argument("--out-md", default="", help="Optional output Markdown path.")
    parser.add_argument("--recommendation-only", action="store_true", help="Print a compact route summary.")
    parser.add_argument("--recommendation-format", default="kv", choices=["kv", "json"], help="Output format for --recommendation-only.")
    return parser


def _render_markdown(payload: dict[str, Any]) -> str:
    residual = payload.get("residual_recording") if isinstance(payload.get("residual_recording"), dict) else {}
    lines = [
        "# Chapter6 Route",
        "",
        f"- Task id: `{payload.get('task_id') or 'n/a'}`",
        f"- Run id: `{payload.get('run_id') or 'n/a'}`",
        f"- Preferred lane: {payload.get('preferred_lane') or 'inspect-first'}",
        f"- Recommended command: `{payload.get('recommended_command')}`" if payload.get("recommended_command") else "- Recommended command: n/a",
        f"- Latest reason: {payload.get('latest_reason') or 'n/a'}",
        f"- Chapter6 next action: {payload.get('chapter6_next_action') or 'n/a'}",
        f"- Blocked by: {payload.get('blocked_by') or 'n/a'}",
        f"- Reviewer anchor hit: {'yes' if bool(payload.get('reviewer_anchor_hit')) else 'no'}",
        f"- 6.8 worthwhile: {'yes' if bool(payload.get('six_eight_worthwhile')) else 'no'}",
        f"- Full 6.7 recommended: {'yes' if bool(payload.get('full_67_recommended')) else 'no'}",
        f"- Repo noise classification: {payload.get('repo_noise_classification') or 'task-issue'}",
        f"- Repo noise reason: {payload.get('repo_noise_reason') or 'n/a'}",
        f"- Residual eligible: {'yes' if bool(residual.get('eligible')) else 'no'}",
        f"- Residual performed: {'yes' if bool(residual.get('performed')) else 'no'}",
    ]
    if residual.get("decision_log_path"):
        lines.append(f"- Decision log: `{residual.get('decision_log_path')}`")
    if residual.get("execution_plan_path"):
        lines.append(f"- Execution plan: `{residual.get('execution_plan_path')}`")
    return "\n".join(lines) + "\n"


def _compact_payload(payload: dict[str, Any]) -> dict[str, Any]:
    residual = payload.get("residual_recording") if isinstance(payload.get("residual_recording"), dict) else {}
    return {
        "task_id": str(payload.get("task_id") or "").strip() or "n/a",
        "run_id": str(payload.get("run_id") or "").strip() or "n/a",
        "preferred_lane": str(payload.get("preferred_lane") or "").strip() or "inspect-first",
        "recommended_command": str(payload.get("recommended_command") or "").strip() or "n/a",
        "latest_reason": str(payload.get("latest_reason") or "").strip() or "n/a",
        "chapter6_next_action": str(payload.get("chapter6_next_action") or "").strip() or "n/a",
        "blocked_by": str(payload.get("blocked_by") or "").strip() or "n/a",
        "reviewer_anchor_hit": "yes" if bool(payload.get("reviewer_anchor_hit")) else "no",
        "six_eight_worthwhile": "yes" if bool(payload.get("six_eight_worthwhile")) else "no",
        "repo_noise_classification": str(payload.get("repo_noise_classification") or "").strip() or "task-issue",
        "residual_recording": "performed" if bool(residual.get("performed")) else ("eligible" if bool(residual.get("eligible")) else "no"),
    }


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    task_id = str(args.task_id or "").strip()
    latest = str(args.latest or "").strip()
    if not task_id and not latest:
        print("ERROR: pass --task-id or --latest", file=sys.stderr)
        return 2
    root = Path(str(args.repo_root or REPO_ROOT)).resolve()
    try:
        _, payload = route_chapter6(
            repo_root=root,
            task_id=task_id,
            latest=latest,
            run_id=str(args.run_id or "").strip(),
            record_residual=bool(args.record_residual),
        )
    except Exception as exc:
        print(f"ERROR: failed to route chapter6 recovery: {exc}", file=sys.stderr)
        return 2

    out_json = str(args.out_json or "").strip()
    if out_json:
        out_json_path = _resolve_path(root, out_json)
        assert out_json_path is not None
        out_json_path.parent.mkdir(parents=True, exist_ok=True)
        out_json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    out_md = str(args.out_md or "").strip()
    if out_md:
        out_md_path = _resolve_path(root, out_md)
        assert out_md_path is not None
        out_md_path.parent.mkdir(parents=True, exist_ok=True)
        out_md_path.write_text(_render_markdown(payload), encoding="utf-8", newline="\n")

    if bool(args.recommendation_only):
        compact = _compact_payload(payload)
        if str(args.recommendation_format or "kv").strip().lower() == "json":
            print(json.dumps(compact, ensure_ascii=False))
        else:
            print("\n".join(f"{key}={value}" for key, value in compact.items()))
        return 0

    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
