from __future__ import annotations

import datetime as dt
import json
from pathlib import Path
from typing import Any

from _sidecar_schema import validate_run_event_payload
from _util import ensure_dir

SCHEMA_VERSION = "1.0.0"


def run_events_path(out_dir: Path) -> Path:
    return out_dir / "run-events.jsonl"


def _utc_now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


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
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "ts": _utc_now_iso(),
        "event": str(event).strip(),
        "task_id": str(task_id).strip(),
        "run_id": str(run_id).strip(),
        "delivery_profile": str(delivery_profile).strip(),
        "security_profile": str(security_profile).strip(),
        "step_name": step_name if step_name is None else str(step_name).strip(),
        "status": status if status is None else str(status).strip(),
        "details": dict(details or {}),
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
    )
    path = run_events_path(out_dir)
    ensure_dir(path.parent)
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False) + "\n")
    return payload
