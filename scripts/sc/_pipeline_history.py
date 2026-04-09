from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from _util import repo_root


def _read_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def _normalize_profile_value(value: Any) -> str:
    return str(value or "").strip().lower()


def _build_step_map(summary: dict[str, Any]) -> dict[str, dict[str, Any]]:
    steps = summary.get("steps") if isinstance(summary.get("steps"), list) else []
    return {
        str(step.get("name") or "").strip(): step
        for step in steps
        if isinstance(step, dict) and str(step.get("name") or "").strip()
    }


def _normalize_failure_fragment(value: Any, *, limit: int = 160) -> str:
    text = " ".join(str(value or "").strip().split())
    return text[:limit]


def _resolve_summary_path(raw_path: str) -> Path | None:
    text = str(raw_path or "").strip()
    if not text:
        return None
    path = Path(text)
    if not path.is_absolute():
        path = repo_root() / path
    return path.resolve() if path.exists() else None


def _derive_sc_test_failure_fingerprint_from_payload(payload: dict[str, Any]) -> str:
    steps = payload.get("steps") if isinstance(payload.get("steps"), list) else []
    for step in steps:
        if not isinstance(step, dict):
            continue
        if str(step.get("status") or "").strip().lower() != "fail":
            continue
        parts = [
            "sc-test",
            _normalize_failure_fragment(step.get("name")),
            str(int(step.get("rc") or 0)),
            _normalize_failure_fragment(step.get("reason")),
            _normalize_failure_fragment(step.get("error")),
        ]
        while parts and not parts[-1]:
            parts.pop()
        return "|".join(parts)
    status = _normalize_failure_fragment(payload.get("status"))
    return f"sc-test|summary|{status}" if status else ""


def _resolve_sc_test_failure_fingerprint(step: dict[str, Any]) -> str:
    summary_path = _resolve_summary_path(str(step.get("summary_file") or "").strip())
    if summary_path is not None:
        payload = _read_json(summary_path)
        fingerprint = _derive_sc_test_failure_fingerprint_from_payload(payload)
        if fingerprint:
            return fingerprint
    parts = [
        "sc-test",
        _normalize_failure_fragment(step.get("name")),
        str(int(step.get("rc") or 0)),
        _normalize_failure_fragment(step.get("status")),
    ]
    return "|".join(parts)


def derive_pipeline_failure_family(
    *,
    summary: dict[str, Any],
    repair_guide: dict[str, Any] | None = None,
) -> dict[str, Any]:
    repair_guide = repair_guide if isinstance(repair_guide, dict) else {}
    step_map = _build_step_map(summary)
    status = str(summary.get("status") or "").strip().lower()
    reason = str(summary.get("reason") or "").strip()
    repair_status = str(repair_guide.get("status") or "").strip().lower()
    failed_step = next(
        (
            str(step.get("name") or "").strip()
            for step in (summary.get("steps") if isinstance(summary.get("steps"), list) else [])
            if isinstance(step, dict) and str(step.get("status") or "").strip().lower() == "fail"
        ),
        "",
    )
    if status == "fail":
        if failed_step == "sc-test":
            fingerprint = _resolve_sc_test_failure_fingerprint(step_map.get("sc-test") or {})
            if fingerprint:
                return {
                    "family": f"step-failed:sc-test|{fingerprint}",
                    "status": status,
                    "reason": reason or "step_failed:sc-test",
                    "failed_step": failed_step,
                }
        family = f"step-failed:{failed_step or 'unknown'}"
        if reason:
            family = f"{family}|{reason}"
        return {
            "family": family,
            "status": status,
            "reason": reason or family,
            "failed_step": failed_step,
        }
    if repair_status == "needs-fix":
        llm_step = step_map.get("sc-llm-review") or {}
        llm_status = str(llm_step.get("status") or "").strip().lower()
        family = f"review-needs-fix|llm={llm_status or 'unknown'}"
        if reason:
            family = f"{family}|{reason}"
        return {
            "family": family,
            "status": "review-needs-fix",
            "reason": reason or "review-needs-fix",
            "failed_step": failed_step,
        }
    if status == "aborted":
        return {
            "family": "aborted",
            "status": status,
            "reason": reason or "aborted",
            "failed_step": failed_step,
        }
    return {
        "family": "",
        "status": status,
        "reason": reason,
        "failed_step": failed_step,
    }


def collect_recent_failure_summary(
    *,
    task_id: str,
    delivery_profile: str,
    security_profile: str,
    root: Path | None = None,
    limit: int = 3,
) -> dict[str, Any]:
    resolved_root = root.resolve() if root else repo_root()
    task_id_text = str(task_id or "").strip()
    if not task_id_text:
        return {}
    logs_root = resolved_root / "logs" / "ci"
    if not logs_root.exists():
        return {}
    candidates = sorted(
        [item for item in logs_root.rglob(f"sc-review-pipeline-task-{task_id_text}-*") if item.is_dir()],
        key=lambda item: item.stat().st_mtime,
        reverse=True,
    )
    history: list[dict[str, Any]] = []
    for candidate in candidates:
        summary_path = candidate / "summary.json"
        execution_context_path = candidate / "execution-context.json"
        if not summary_path.exists() or not execution_context_path.exists():
            continue
        summary = _read_json(summary_path)
        execution_context = _read_json(execution_context_path)
        if not summary or not execution_context:
            continue
        if delivery_profile and _normalize_profile_value(execution_context.get("delivery_profile")) != _normalize_profile_value(delivery_profile):
            continue
        if security_profile and _normalize_profile_value(execution_context.get("security_profile")) != _normalize_profile_value(security_profile):
            continue
        repair_guide = _read_json(candidate / "repair-guide.json")
        family_info = derive_pipeline_failure_family(summary=summary, repair_guide=repair_guide)
        family = str(family_info.get("family") or "").strip()
        if not family:
            continue
        history.append(
            {
                "run_id": str(execution_context.get("run_id") or summary.get("run_id") or "").strip(),
                "out_dir": str(candidate),
                "family": family,
                "status": str(family_info.get("status") or "").strip(),
                "reason": str(family_info.get("reason") or "").strip(),
                "failed_step": str(family_info.get("failed_step") or "").strip(),
            }
        )
        if len(history) >= max(1, int(limit or 1)):
            break
    if not history:
        return {}
    latest_family = str(history[0].get("family") or "").strip()
    same_family: list[dict[str, Any]] = []
    for item in history:
        if str(item.get("family") or "").strip() != latest_family:
            break
        same_family.append(item)
    repeated = len(same_family) >= 2
    return {
        "latest_failure_family": latest_family,
        "same_family_count": len(same_family),
        "recent_failure_count": len(history),
        "recent_window_size": max(1, int(limit or 1)),
        "repeated_recent_failure": repeated,
        "stop_full_rerun_recommended": repeated,
        "recommendation_basis": (
            f"same failure family repeated in {len(same_family)} consecutive recent failed runs"
            if repeated
            else "no repeated recent failure family detected"
        ),
        "recent_run_ids": [str(item.get("run_id") or "").strip() for item in history if str(item.get("run_id") or "").strip()],
        "same_family_run_ids": [str(item.get("run_id") or "").strip() for item in same_family if str(item.get("run_id") or "").strip()],
        "recent_failed_step": str(history[0].get("failed_step") or "").strip(),
    }
