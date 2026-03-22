#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any, Callable


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
    except Exception as exc:
        return 1, f"codex exec failed to start: {exc}\n", cmd
    return proc.returncode or 0, proc.stdout or "", cmd


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
