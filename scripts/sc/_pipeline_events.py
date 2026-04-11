from __future__ import annotations

import datetime as dt
import json
import re
from pathlib import Path
from typing import Any

from _sidecar_schema import validate_run_event_payload
from _util import ensure_dir

SCHEMA_VERSION = "1.0.0"
_TURN_ID_RE = re.compile(r":turn-(\d+)$")


def run_events_path(out_dir: Path) -> Path:
    return out_dir / "run-events.jsonl"


def _utc_now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _event_family(event: str) -> str:
    text = str(event or "").strip().lower().replace("-", "_")
    if text.startswith("reviewer_") or text.startswith("agent_review_") or text.startswith("llm_review_"):
        return "reviewer"
    if text.startswith("sidecar_") or text.startswith("harness_"):
        return "sidecar"
    if text.startswith("latest_") or text.startswith("active_task_") or text.startswith("execution_context_") or text.startswith("repair_guide_"):
        return "sidecar"
    if text.startswith("step_"):
        return "step"
    if text.startswith("run_"):
        return "run"
    if text.startswith("approval_"):
        return "approval"
    if text.startswith("acceptance_preflight_"):
        return "acceptance-preflight"
    if text in {"rerun_blocked"}:
        return "recovery"
    if text in {"wall_time_exceeded"}:
        return "runtime-guard"
    return "custom"


def _normalize_turn_seq(turn_seq: int | None) -> int:
    try:
        parsed = int(turn_seq or 1)
    except (TypeError, ValueError):
        parsed = 1
    return max(1, parsed)


def build_turn_id(*, run_id: str, turn_seq: int | None = None) -> str:
    return f"{str(run_id or '').strip()}:turn-{_normalize_turn_seq(turn_seq)}"


def _infer_turn_seq(*, run_id: str, turn_id: str | None, turn_seq: int | None) -> int:
    if turn_seq is not None:
        return _normalize_turn_seq(turn_seq)
    text = str(turn_id or "").strip()
    if text:
        match = _TURN_ID_RE.search(text)
        if match:
            return _normalize_turn_seq(int(match.group(1)))
    return 1


def _item_taxonomy(
    *,
    task_id: str,
    run_id: str,
    event: str,
    event_family: str,
    step_name: str | None,
    details: dict[str, Any],
    item_kind: str | None,
    item_id: str | None,
) -> tuple[str, str]:
    explicit_kind = str(item_kind or "").strip()
    explicit_id = str(item_id or "").strip()
    if explicit_kind:
        return explicit_kind, explicit_id or explicit_kind
    if event_family == "approval":
        approval_id = str(details.get("request_id") or details.get("action") or event or "").strip()
        return "approval", approval_id or "approval"
    if event_family == "reviewer":
        reviewer_id = str(details.get("reviewer") or details.get("agent") or step_name or event or "").strip()
        return "reviewer", reviewer_id or "reviewer"
    if event_family == "sidecar":
        sidecar_id = str(details.get("sidecar") or details.get("artifact") or event or "").strip()
        return "sidecar", sidecar_id or "sidecar"
    if str(step_name or "").strip():
        return "step", str(step_name or "").strip()
    if event_family in {"run", "recovery", "runtime-guard"}:
        return "run", str(run_id or "").strip()
    return "task", str(task_id or "").strip()


def build_run_event(
    *,
    event: str,
    task_id: str,
    run_id: str,
    delivery_profile: str,
    security_profile: str,
    step_name: str | None = None,
    status: str | None = None,
    details: dict[str, Any] | None = None,
    turn_id: str | None = None,
    turn_seq: int | None = None,
    item_kind: str | None = None,
    item_id: str | None = None,
) -> dict[str, Any]:
    event_text = str(event).strip()
    task_text = str(task_id).strip()
    run_text = str(run_id).strip()
    step_text = step_name if step_name is None else str(step_name).strip()
    detail_payload = dict(details or {})
    event_family = _event_family(event_text)
    normalized_turn_seq = _infer_turn_seq(run_id=run_text, turn_id=turn_id, turn_seq=turn_seq)
    turn_text = str(turn_id or "").strip() or build_turn_id(run_id=run_text, turn_seq=normalized_turn_seq)
    resolved_item_kind, resolved_item_id = _item_taxonomy(
        task_id=task_text,
        run_id=run_text,
        event=event_text,
        event_family=event_family,
        step_name=step_text,
        details=detail_payload,
        item_kind=item_kind,
        item_id=item_id,
    )
    payload: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "ts": _utc_now_iso(),
        "event": event_text,
        "event_family": event_family,
        "task_id": task_text,
        "run_id": run_text,
        "turn_id": turn_text,
        "turn_seq": normalized_turn_seq,
        "delivery_profile": str(delivery_profile).strip(),
        "security_profile": str(security_profile).strip(),
        "item_kind": resolved_item_kind,
        "item_id": resolved_item_id,
        "step_name": step_text,
        "status": status if status is None else str(status).strip(),
        "details": detail_payload,
    }
    validate_run_event_payload(payload)
    return payload


def append_run_event(
    *,
    out_dir: Path,
    event: str,
    task_id: str,
    run_id: str,
    delivery_profile: str,
    security_profile: str,
    step_name: str | None = None,
    status: str | None = None,
    details: dict[str, Any] | None = None,
    turn_id: str | None = None,
    turn_seq: int | None = None,
    item_kind: str | None = None,
    item_id: str | None = None,
) -> dict[str, Any]:
    payload = build_run_event(
        event=event,
        task_id=task_id,
        run_id=run_id,
        delivery_profile=delivery_profile,
        security_profile=security_profile,
        step_name=step_name,
        status=status,
        details=details,
        turn_id=turn_id,
        turn_seq=turn_seq,
        item_kind=item_kind,
        item_id=item_id,
    )
    path = run_events_path(out_dir)
    ensure_dir(path.parent)
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False) + "\n")
    return payload
