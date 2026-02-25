#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from _taskmaster import default_paths, load_json


_MOJIBAKE_TOKENS: tuple[str, ...] = (
    "�",
    "Ã",
    "Â",
    "Ð",
    "Ñ",
    "æ",
    "å",
    "ç",
    "â€™",
    "â€œ",
    "â€",
    "ðŸ",
)

_CN_BREAK_Q_RE = re.compile(r"[\u4e00-\u9fff]\?[\u4e00-\u9fff]")
_MULTI_Q_RE = re.compile(r"\?{3,}")


def parse_task_ids_csv(value: str | None) -> set[int]:
    out: set[int] = set()
    if not value:
        return out
    for raw in str(value).split(","):
        token = str(raw or "").strip()
        if not token:
            continue
        try:
            out.add(int(token))
        except ValueError:
            continue
    return out


def _is_suspicious_text(text: str) -> bool:
    s = str(text or "")
    if not s:
        return False
    if any(token in s for token in _MOJIBAKE_TOKENS):
        return True
    if _CN_BREAK_Q_RE.search(s):
        return True
    if _MULTI_Q_RE.search(s):
        return True
    return False


def _safe_sample(text: str, *, max_chars: int) -> str:
    s = str(text or "").replace("\n", " ").strip()
    if len(s) <= max_chars:
        return s
    return s[: max_chars - 3] + "..."


def _iter_task_records(scope: str, payload: Any) -> list[dict[str, Any]]:
    if scope == "master":
        if not isinstance(payload, dict):
            return []
        master = payload.get("master") or {}
        tasks = master.get("tasks") or []
        return [x for x in tasks if isinstance(x, dict)]
    if scope in {"back", "gameplay"}:
        if not isinstance(payload, list):
            return []
        return [x for x in payload if isinstance(x, dict)]
    return []


def _task_id_of(scope: str, task: dict[str, Any]) -> int | None:
    raw = task.get("id") if scope == "master" else task.get("taskmaster_id")
    try:
        return int(raw)
    except (TypeError, ValueError):
        return None


def _scan_scope(
    *,
    scope: str,
    path: Path,
    task_ids: set[int] | None,
    max_sample_chars: int,
) -> dict[str, Any]:
    report: dict[str, Any] = {
        "scope": scope,
        "path": str(path).replace("\\", "/"),
        "utf8_decode": "ok",
        "json_parse": "ok",
        "task_count": 0,
        "checked_items": 0,
        "suspicious_hits": 0,
        "hits": [],
    }

    try:
        text = path.read_text(encoding="utf-8")
    except Exception as exc:  # noqa: BLE001
        report["utf8_decode"] = "fail"
        report["error"] = str(exc)
        return report

    try:
        payload = load_json(path)
    except Exception as exc:  # noqa: BLE001
        report["json_parse"] = "fail"
        report["error"] = str(exc)
        return report

    tasks = _iter_task_records(scope, payload)
    report["task_count"] = len(tasks)

    for task in tasks:
        task_id = _task_id_of(scope, task)
        if task_ids and task_id is not None and task_id not in task_ids:
            continue

        fields = ["title", "description", "details", "testStrategy", "test_strategy"]
        for field in fields:
            value = task.get(field)
            if not isinstance(value, str):
                continue
            report["checked_items"] += 1
            if not _is_suspicious_text(value):
                continue
            report["suspicious_hits"] += 1
            report["hits"].append(
                {
                    "task_id": task_id,
                    "entry_id": str(task.get("id") or ""),
                    "field": field,
                    "sample": _safe_sample(value, max_chars=max_sample_chars),
                }
            )

        acceptance = task.get("acceptance")
        if isinstance(acceptance, list):
            for idx, item in enumerate(acceptance, 1):
                line = str(item or "")
                report["checked_items"] += 1
                if not _is_suspicious_text(line):
                    continue
                report["suspicious_hits"] += 1
                report["hits"].append(
                    {
                        "task_id": task_id,
                        "entry_id": str(task.get("id") or ""),
                        "field": f"acceptance[{idx}]",
                        "sample": _safe_sample(line, max_chars=max_sample_chars),
                    }
                )

    return report


def scan_task_text_integrity(
    *,
    tasks_json_path: Path | None = None,
    tasks_back_path: Path | None = None,
    tasks_gameplay_path: Path | None = None,
    task_ids: set[int] | None = None,
    max_sample_chars: int = 200,
) -> dict[str, Any]:
    default_tasks_json, default_back, default_gameplay = default_paths()
    master_path = Path(tasks_json_path) if tasks_json_path else default_tasks_json
    back_path = Path(tasks_back_path) if tasks_back_path else default_back
    gameplay_path = Path(tasks_gameplay_path) if tasks_gameplay_path else default_gameplay

    scopes = [
        _scan_scope(
            scope="master",
            path=master_path,
            task_ids=task_ids,
            max_sample_chars=max_sample_chars,
        ),
        _scan_scope(
            scope="back",
            path=back_path,
            task_ids=task_ids,
            max_sample_chars=max_sample_chars,
        ),
        _scan_scope(
            scope="gameplay",
            path=gameplay_path,
            task_ids=task_ids,
            max_sample_chars=max_sample_chars,
        ),
    ]

    decode_errors = sum(1 for s in scopes if s.get("utf8_decode") != "ok")
    parse_errors = sum(1 for s in scopes if s.get("json_parse") != "ok")
    suspicious_hits = sum(int(s.get("suspicious_hits") or 0) for s in scopes)

    return {
        "summary": {
            "decode_errors": decode_errors,
            "parse_errors": parse_errors,
            "suspicious_hits": suspicious_hits,
            "task_filter": sorted(task_ids) if task_ids else [],
        },
        "scopes": scopes,
    }


def render_top_hits(report: dict[str, Any], *, limit: int = 8) -> list[str]:
    lines: list[str] = []
    for scope in report.get("scopes") or []:
        if not isinstance(scope, dict):
            continue
        scope_name = str(scope.get("scope") or "")
        for hit in scope.get("hits") or []:
            if not isinstance(hit, dict):
                continue
            tid = hit.get("task_id")
            field = str(hit.get("field") or "")
            sample = str(hit.get("sample") or "")
            lines.append(f"{scope_name}:T{tid} {field} -> {sample}")
            if len(lines) >= limit:
                return lines
    return lines

