#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Callable

from _llm_backend import run_llm_exec


def run_codex_exec(
    *,
    backend: str = "codex-cli",
    prompt: str,
    out_last_message: Path,
    timeout_sec: int,
    repo_root_path: Path,
) -> tuple[int, str, list[str]]:
    return run_llm_exec(
        backend=backend,
        root=repo_root_path,
        prompt=prompt,
        output_last_message=out_last_message,
        timeout_sec=timeout_sec,
    )


def extract_json_object(text: str) -> dict[str, Any]:
    text = str(text or "").strip()
    try:
        obj = json.loads(text)
        if isinstance(obj, dict):
            return obj
    except Exception:
        pass
    match = re.search(r"\{.*\}", text, flags=re.DOTALL)
    if not match:
        raise ValueError("No JSON object found in model output.")
    obj = json.loads(match.group(0))
    if not isinstance(obj, dict):
        raise ValueError("Model output JSON is not an object.")
    return obj


def normalize_model_status(value: Any) -> str:
    status = str(value or "").strip().lower()
    return "ok" if status == "ok" else "fail"


def truncate_keep_ends(text: str, *, max_chars: int) -> str:
    payload = str(text or "")
    limit = max(80, int(max_chars))
    if len(payload) <= limit:
        return payload
    marker = "\n...[TRUNCATED_FOR_BUDGET]...\n"
    if len(marker) >= limit:
        return payload[:limit]
    tail_keep = min(max(80, limit // 3), max(1, limit - len(marker) - 40))
    head_keep = max(40, limit - len(marker) - tail_keep)
    if head_keep + len(marker) + tail_keep > limit:
        tail_keep = max(1, limit - len(marker) - head_keep)
    return payload[:head_keep] + marker + payload[-tail_keep:]


def format_acceptance(
    view_name: str,
    acceptance: list[Any],
    *,
    truncate_fn: Callable[[str, int], str],
) -> str:
    out = [f"[{view_name}] acceptance items ({len(acceptance)}):"]
    for idx, raw in enumerate(acceptance, start=1):
        text = truncate_fn(str(raw or "").strip(), 500)
        out.append(f"- {view_name}:{idx}: {text}")
    return "\n".join(out)


def build_prompt(
    *,
    task_id: str,
    title: str,
    subtasks: list[dict[str, Any]],
    acceptance_by_view: dict[str, list[Any]],
    delivery_profile_context: str,
    format_acceptance_fn: Callable[[str, list[Any]], str],
) -> str:
    sub_lines = []
    for subtask in subtasks:
        sid = str(subtask.get("id") or "").strip()
        stitle = str(subtask.get("title") or "").strip()
        sdetails = str(subtask.get("details") or "").strip()
        if sid and stitle:
            if sdetails:
                sdetails = re.sub(r"\s+", " ", sdetails).strip()
                sub_lines.append(f"- {sid}: {stitle} :: {sdetails}")
            else:
                sub_lines.append(f"- {sid}: {stitle}")

    acceptance_blocks = [format_acceptance_fn(view_name, items) for view_name, items in acceptance_by_view.items()]
    schema = """
Return JSON only (no Markdown).
Schema:
{
  "task_id": "<id>",
  "status": "ok" | "fail",
  "subtasks": [
    {
      "id": "<subtask id from tasks.json>",
      "title": "<subtask title>",
      "covered": true | false,
      "matches": [
        {"view": "back|gameplay", "acceptance_index": <1-based>, "acceptance_excerpt": "<short>"}
      ],
      "reason": "<one short sentence>"
    }
  ],
  "uncovered_subtask_ids": ["<id>", ...],
  "notes": ["<short>", ...]
}

Rules:
- Be conservative: mark a subtask covered ONLY if at least one acceptance item clearly implies it.
- Coverage is semantic (do not require exact wording), but do not guess.
- If ANY subtask is not covered => status must be "fail".
- Use BOTH subtask title and subtask details when judging coverage.
"""
    return "\n".join(
        [
            "You are a strict reviewer for a Godot + C# repo.",
            "Task subtasks are an implementation breakdown; acceptance criteria are the repository SSoT for gating.",
            "Decide whether each subtask is covered by >=1 acceptance item across the available views (back/gameplay).",
            "",
            f"Task: T{task_id} {title}",
            "",
            "Delivery profile context:",
            delivery_profile_context.strip() or "- profile: standard",
            "",
            "Subtasks (from tasks.json):",
            *(sub_lines or ["- (none)"]),
            "",
            "Acceptance criteria (from tasks_back/tasks_gameplay):",
            *acceptance_blocks,
            "",
            schema.strip(),
        ]
    )
