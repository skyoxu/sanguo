#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any


def run_codex_exec(
    *,
    prompt: str,
    out_last_message: Path,
    timeout_sec: int,
    repo_root_path: Path,
) -> tuple[int, str, list[str]]:
    exe = shutil.which("codex")
    if not exe:
        return 127, "codex executable not found in PATH\n", ["codex"]
    cmd = [
        exe,
        "exec",
        "-s",
        "read-only",
        "-C",
        str(repo_root_path),
        "--output-last-message",
        str(out_last_message),
        "-",
    ]
    try:
        proc = subprocess.run(
            cmd,
            input=prompt,
            text=True,
            encoding="utf-8",
            errors="ignore",
            cwd=str(repo_root_path),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=timeout_sec,
        )
    except subprocess.TimeoutExpired:
        return 124, "codex exec timeout\n", cmd
    except Exception as exc:  # noqa: BLE001
        return 1, f"codex exec failed to start: {exc}\n", cmd
    return proc.returncode or 0, proc.stdout or "", cmd


def extract_json_object(text: str) -> dict[str, Any]:
    payload = str(text or "").strip()
    try:
        obj = json.loads(payload)
        if isinstance(obj, dict):
            return obj
    except Exception:
        pass
    match = re.search(r"\{.*\}", payload, flags=re.DOTALL)
    if not match:
        raise ValueError("No JSON object found in model output.")
    obj = json.loads(match.group(0))
    if not isinstance(obj, dict):
        raise ValueError("Model output JSON is not an object.")
    return obj


def truncate(text: str, *, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 3] + "..."


def normalize_subtasks(raw: Any) -> list[dict[str, str]]:
    if not isinstance(raw, list):
        return []
    out: list[dict[str, str]] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        sid = str(item.get("id") or "").strip()
        title = str(item.get("title") or "").strip()
        details = str(item.get("details") or "").strip()
        test_strategy = str(item.get("testStrategy") or "").strip()
        if not sid or not title:
            continue
        details = truncate(re.sub(r"\s+", " ", details).strip(), max_chars=520) if details else ""
        test_strategy = truncate(re.sub(r"\s+", " ", test_strategy).strip(), max_chars=320) if test_strategy else ""
        out.append(
            {
                "id": sid,
                "title": title,
                "details": details,
                "testStrategy": test_strategy,
            }
        )
    return out


def is_view_present(view: dict[str, Any] | None) -> bool:
    return isinstance(view, dict) and isinstance(view.get("acceptance"), list)


def build_source_text_blocks(
    *,
    title: str,
    details: str,
    test_strategy: str,
    subtasks: list[dict[str, str]],
) -> list[str]:
    """Build deterministic source corpus for source_excerpt checks.

    Guardrail: master.title must be present and kept as the first source block.
    """

    title_text = str(title or "").strip()
    if not title_text:
        raise ValueError("master.title is required in source_blocks")

    blocks: list[str] = [title_text, str(details or ""), str(test_strategy or "")]
    for item in subtasks:
        blocks.append(str(item.get("title") or ""))
        blocks.append(str(item.get("details") or ""))
        blocks.append(str(item.get("testStrategy") or ""))

    if not str(blocks[0] or "").strip():
        raise ValueError("source_blocks[0] must be non-empty master.title")
    return blocks


def collect_auto_escalation_reasons(run_results: list[dict[str, Any]], *, force_task: bool) -> list[str]:
    reasons: list[str] = []
    if force_task:
        reasons.append("forced_task")

    has_fail_vote = any(str(item.get("status") or "").strip().lower() != "ok" for item in run_results)
    if has_fail_vote:
        reasons.append("fail_vote")

    has_timeout = any(int(item.get("rc") or 0) == 124 for item in run_results)
    if has_timeout:
        reasons.append("timeout")

    has_invalid_json = any(str(item.get("error") or "").startswith("invalid_json") for item in run_results)
    if has_invalid_json:
        reasons.append("invalid_json")

    has_exec_or_empty = any(str(item.get("error") or "") == "codex_exec_failed_or_empty" for item in run_results)
    if has_exec_or_empty:
        reasons.append("exec_or_empty")

    ok_votes = sum(1 for item in run_results if str(item.get("status") or "").strip().lower() == "ok")
    fail_votes = len(run_results) - ok_votes
    if ok_votes > 0 and fail_votes > 0:
        reasons.append("jitter")

    seen: set[str] = set()
    out: list[str] = []
    for raw in reasons:
        value = str(raw or "").strip()
        if not value or value in seen:
            continue
        seen.add(value)
        out.append(value)
    return out


def validate_verdict_schema(raw_obj: dict[str, Any]) -> tuple[bool, list[str], dict[str, Any]]:
    """Strict validation for obligations LLM verdict payload."""

    errors: list[str] = []
    obj = dict(raw_obj or {})

    task_id = str(obj.get("task_id") or "").strip()
    if not task_id:
        errors.append("task_id_missing")
    else:
        obj["task_id"] = task_id

    status = str(obj.get("status") or "").strip().lower()
    if status not in {"ok", "fail"}:
        errors.append("status_invalid")
    else:
        obj["status"] = status

    obligations = obj.get("obligations")
    if not isinstance(obligations, list):
        errors.append("obligations_not_list")
        obligations = []
    normalized_obligations: list[dict[str, Any]] = []
    for idx, item in enumerate(obligations, start=1):
        if not isinstance(item, dict):
            errors.append(f"obligation_not_object:{idx}")
            continue
        oid = str(item.get("id") or "").strip()
        source = str(item.get("source") or "").strip()
        kind = str(item.get("kind") or "").strip()
        text = str(item.get("text") or "").strip()
        excerpt = str(item.get("source_excerpt") or "").strip()
        covered = item.get("covered")

        if not oid:
            errors.append(f"obligation_id_missing:{idx}")
        if not source:
            errors.append(f"obligation_source_missing:{idx}")
        if kind not in {"core", "godot", "meta"}:
            errors.append(f"obligation_kind_invalid:{idx}")
        if not text:
            errors.append(f"obligation_text_missing:{idx}")
        if not excerpt:
            errors.append(f"obligation_excerpt_missing:{idx}")
        if not isinstance(covered, bool):
            errors.append(f"obligation_covered_not_bool:{idx}")

        matches = item.get("matches", [])
        if not isinstance(matches, list):
            errors.append(f"obligation_matches_not_list:{idx}")
            matches = []
        else:
            for m_idx, m in enumerate(matches, start=1):
                if not isinstance(m, dict):
                    errors.append(f"match_not_object:{idx}.{m_idx}")
                    continue
                view = str(m.get("view") or "").strip()
                if view not in {"back", "gameplay", "back|gameplay"}:
                    errors.append(f"match_view_invalid:{idx}.{m_idx}")
                acceptance_index = m.get("acceptance_index")
                if not isinstance(acceptance_index, int) or acceptance_index < 1:
                    errors.append(f"match_acceptance_index_invalid:{idx}.{m_idx}")
                acceptance_excerpt = str(m.get("acceptance_excerpt") or "").strip()
                if not acceptance_excerpt:
                    errors.append(f"match_acceptance_excerpt_missing:{idx}.{m_idx}")

        reason = item.get("reason", "")
        if not isinstance(reason, str):
            errors.append(f"obligation_reason_not_string:{idx}")
        suggested = item.get("suggested_acceptance", [])
        if not isinstance(suggested, list) or any(not isinstance(x, str) for x in suggested):
            errors.append(f"obligation_suggested_acceptance_invalid:{idx}")

        normalized_obligations.append(item)
    obj["obligations"] = normalized_obligations

    uncovered = obj.get("uncovered_obligation_ids", [])
    if uncovered is None:
        uncovered = []
    if not isinstance(uncovered, list) or any(not str(x or "").strip() for x in uncovered):
        errors.append("uncovered_obligation_ids_invalid")
    else:
        obj["uncovered_obligation_ids"] = [str(x).strip() for x in uncovered]

    notes = obj.get("notes", [])
    if notes is None:
        notes = []
    if not isinstance(notes, list) or any(not isinstance(x, str) for x in notes):
        errors.append("notes_invalid")
    else:
        obj["notes"] = notes

    return not errors, errors, obj


def build_input_hash(payload: dict[str, Any]) -> str:
    """Stable SHA256 hash for obligations input fingerprint."""

    body = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


def limit_schema_errors(errors: list[str], *, max_count: int) -> list[str]:
    cap = max(1, int(max_count))
    return [str(x or "").strip() for x in errors if str(x or "").strip()][:cap]


def bucket_schema_errors(errors: list[str]) -> dict[str, int]:
    buckets: dict[str, int] = {}
    for raw in errors:
        text = str(raw or "").strip()
        if not text:
            continue
        key = text.split(":", 1)[0].strip() or "unknown"
        buckets[key] = int(buckets.get(key, 0)) + 1
    return dict(sorted(buckets.items(), key=lambda x: x[0]))


def extract_schema_error_codes(errors: list[str]) -> list[str]:
    return sorted(bucket_schema_errors(errors).keys())


def build_self_check_report(ok: bool, payload: dict[str, Any]) -> str:
    lines = [
        "# sc-llm-extract-task-obligations self-check",
        "",
        f"- status: {'ok' if ok else 'fail'}",
        "",
        "## Issues",
        "",
    ]
    lines.extend([f"- {x}" for x in payload.get("issues", [])] or ["- (none)"])
    return "\n".join(lines).strip() + "\n"
