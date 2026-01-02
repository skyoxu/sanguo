#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


def bootstrap_imports() -> None:
    sys.path.insert(0, str(Path(__file__).resolve().parent))


bootstrap_imports()

from _taskmaster import default_paths, iter_master_tasks, load_json  # noqa: E402
from _util import repo_root, write_text  # noqa: E402


REFS_RE = re.compile(r"\bRefs\s*:\s*(.+)$", flags=re.IGNORECASE)


@dataclass(frozen=True)
class ViewInput:
    view: str  # back|gameplay
    taskmaster_id: int
    title: str
    description: str
    acceptance: list[str]


@dataclass(frozen=True)
class MasterTaskInput:
    task_id: int
    status: str
    title: str
    description: str
    details: str


def split_refs(line: str) -> tuple[str, str | None]:
    text = str(line or "")
    m = REFS_RE.search(text)
    if not m:
        return text.strip(), None
    prefix = text[: m.start()].rstrip()
    refs_blob = m.group(0).strip()  # keep exact "Refs: ..." substring
    return prefix.strip(), refs_blob


def normalize_acceptance_lines(lines: list[Any]) -> list[str]:
    out: list[str] = []
    for x in lines or []:
        out.append(str(x or "").strip())
    return out


def load_master_index(scope: str) -> dict[int, MasterTaskInput]:
    tasks_json_path, _, _ = default_paths()
    tasks_json = load_json(tasks_json_path)
    tasks = iter_master_tasks(tasks_json)
    out: dict[int, MasterTaskInput] = {}
    for t in tasks:
        tid = str(t.get("id") or "").strip()
        if not tid.isdigit():
            continue
        status = str(t.get("status") or "").strip().lower()
        if scope == "all":
            pass
        elif scope == "done" and status == "done":
            pass
        elif scope == "not-done" and status != "done":
            pass
        else:
            continue

        tid_i = int(tid)
        out[tid_i] = MasterTaskInput(
            task_id=tid_i,
            status=status,
            title=str(t.get("title") or "").strip(),
            description=str(t.get("description") or "").strip(),
            details=str(t.get("details") or "").strip(),
        )
    return out


def find_view_entry(view: list[dict[str, Any]], task_id: int) -> dict[str, Any] | None:
    for t in view:
        if not isinstance(t, dict):
            continue
        if t.get("taskmaster_id") == task_id:
            return t
    return None


def render_task_context(
    *,
    master: MasterTaskInput,
    view_inputs: list[ViewInput],
    mode: str,
    align_view_descriptions: bool,
    semantic_hint: str | None,
) -> str:
    lines: list[str] = []
    lines.append(f"TaskId: {master.task_id}")
    lines.append(f"MasterStatus: {master.status}")
    lines.append(f"MasterTitle: {master.title}")
    lines.append(f"MasterDescription: {master.description}")
    lines.append("MasterDetails:")
    lines.append(master.details)
    lines.append("")
    lines.append("Rulebook:")
    lines.append("- Treat master.description/details as the semantic source of truth.")
    lines.append("- Preserve existing Refs: suffix tokens verbatim for existing items.")
    lines.append("- Prefer wording that is observable/testable (state/event/output), avoid binding to implementation internals.")
    lines.append("- Do not introduce new obligations unrelated to the master description/details.")
    lines.append(f"- Mode: {mode}")
    lines.append(f"- Align view descriptions to master: {bool(align_view_descriptions)}")
    if semantic_hint:
        lines.append(f"- Semantic-audit hint: {semantic_hint}")
    lines.append("")
    for v in view_inputs:
        lines.append(f"View: {v.view}")
        lines.append(f"ViewTitle: {v.title}")
        lines.append(f"ViewDescription: {v.description}")
        lines.append("Acceptance:")
        if not v.acceptance:
            lines.append("  (empty)")
        for i, a in enumerate(v.acceptance, 1):
            prefix, refs = split_refs(a)
            if refs:
                lines.append(f"  {i}. {prefix} {refs}")
            else:
                lines.append(f"  {i}. {prefix}")
        lines.append("")
    return "\n".join(lines).strip() + "\n"


def build_prompt(task_context: str) -> str:
    blocks: list[str] = []
    blocks.append("Role: acceptance-semantics-aligner")
    blocks.append("")
    blocks.append("Goal: rewrite acceptance items so they are semantically equivalent to the task description/details.")
    blocks.append("Hard constraints:")
    blocks.append("- Output must be STRICT JSON (no markdown).")
    blocks.append("- Preserve existing Refs: suffix tokens verbatim for existing acceptance items.")
    blocks.append("- Do NOT add new Refs: tokens in this step (acceptance-only phase).")
    blocks.append("")
    blocks.append("Mode rules:")
    blocks.append('- rewrite-only: for each view, output acceptance array with EXACT SAME LENGTH as input and do NOT reorder items.')
    blocks.append('- append-only: for each view, output acceptance array with LENGTH >= input; keep the first N items in-place; append new items at the end.')
    blocks.append("")
    blocks.append("Output JSON schema:")
    blocks.append("{")
    blocks.append('  "task_id": <int>,')
    blocks.append('  "mode": "rewrite-only" | "append-only" | "allow-structural-edits",')
    blocks.append('  "back": { "description": <string>|null, "acceptance": [<string>...] } | null,')
    blocks.append('  "gameplay": { "description": <string>|null, "acceptance": [<string>...] } | null,')
    blocks.append('  "notes": [<string>...]')
    blocks.append("}")
    blocks.append("")
    blocks.append("Task context:")
    blocks.append(task_context)
    return "\n".join(blocks).strip() + "\n"


def run_codex_exec(*, prompt: str, out_last_message: Path, timeout_sec: int) -> tuple[int, str]:
    exe = shutil.which("codex")
    if not exe:
        return 127, "codex executable not found in PATH\n"
    cmd = [
        exe,
        "exec",
        "-s",
        "read-only",
        "-C",
        str(repo_root()),
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
            cwd=str(repo_root()),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=timeout_sec,
        )
    except subprocess.TimeoutExpired:
        return 124, "codex exec timeout\n"
    except Exception as exc:  # noqa: BLE001
        return 1, f"codex exec failed to start: {exc}\n"
    return proc.returncode or 0, proc.stdout or ""


def safe_parse_json(text: str) -> dict[str, Any] | None:
    try:
        obj = json.loads(text)
    except Exception:  # noqa: BLE001
        return None
    return obj if isinstance(obj, dict) else None


def validate_output(
    *,
    task_id: int,
    mode: str,
    view_inputs: list[ViewInput],
    out_obj: dict[str, Any],
    align_view_descriptions: bool,
) -> tuple[bool, str]:
    if int(out_obj.get("task_id") or -1) != int(task_id):
        return False, "task_id_mismatch"
    if str(out_obj.get("mode") or "") != mode:
        return False, "mode_mismatch"

    for v in view_inputs:
        key = v.view
        payload = out_obj.get(key)
        if payload is None:
            continue
        if not isinstance(payload, dict):
            return False, f"{key}:not_object"
        if align_view_descriptions:
            d = payload.get("description", None)
            if d is not None and not isinstance(d, str):
                return False, f"{key}:description_not_string"
        acc = payload.get("acceptance")
        if not isinstance(acc, list):
            return False, f"{key}:acceptance_not_list"
        if mode == "rewrite-only" and len(acc) != len(v.acceptance):
            return False, f"{key}:length_changed"
        if mode == "append-only" and len(acc) < len(v.acceptance):
            return False, f"{key}:shrunk_in_append_only"

        # Preserve Refs: token verbatim for existing items; forbid Refs in appended items.
        for i, new_line in enumerate(acc):
            new_s = str(new_line)
            if i < len(v.acceptance):
                old = v.acceptance[i]
                _old_prefix, old_refs = split_refs(old)
                _new_prefix, new_refs = split_refs(new_s)
                if old_refs and new_refs != old_refs:
                    return False, f"{key}:refs_changed_at_{i+1}"
                if (not old_refs) and new_refs:
                    return False, f"{key}:unexpected_refs_added_at_{i+1}"
            else:
                _p, refs = split_refs(new_s)
                if refs:
                    return False, f"{key}:unexpected_refs_in_appended_item_{i+1}"

    return True, "ok"


def apply_acceptance(entry: dict[str, Any], new_acceptance: list[str]) -> None:
    entry["acceptance"] = normalize_acceptance_lines([str(x) for x in new_acceptance])


def apply_description(entry: dict[str, Any], description: str | None) -> None:
    if description is None:
        return
    entry["description"] = str(description).strip()


def load_semantic_hints(path: str | None) -> dict[int, str]:
    if not path:
        return {}
    p = Path(path)
    if not p.exists():
        return {}
    try:
        obj = json.loads(p.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return {}
    findings = obj.get("findings") or []
    out: dict[int, str] = {}
    if isinstance(findings, list):
        for f in findings:
            if not isinstance(f, dict):
                continue
            if str(f.get("verdict") or "").strip() != "Needs Fix":
                continue
            tid = f.get("task_id")
            try:
                tid_i = int(tid)
            except Exception:  # noqa: BLE001
                continue
            reason = str(f.get("reason") or "").strip()
            if reason:
                out[tid_i] = reason
    return out

