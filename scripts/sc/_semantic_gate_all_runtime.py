#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from _util import repo_root


PROMPT_HEADER = """Role: semantic-equivalence-auditor (batch)

Goal: for each task below, judge whether the acceptance set is semantically equivalent to the task description.
Scope: stage-2 only. Do NOT re-check deterministic gates (refs existence, anchors, ADR/security/static scans).
Important: DO NOT infer requirements from any test file names/paths; treat refs as non-semantic metadata.

Output format (STRICT, no markdown fences):
For each task, output exactly one TSV line:
T<id>\\tOK|Needs Fix\\t<short reason (<=120 chars)>

Rules:
- Verdict OK if acceptance covers all REQUIRED behaviors/invariants/failure-semantics implied by the master description/details, and does not CONTRADICT them.
- Extra refinements are allowed if they are consistent with the task intent; do NOT mark Needs Fix only because acceptance is more detailed.
- Mark Needs Fix only if: described behavior missing, contradiction, or clearly unrelated feature.
- If the task has both back/gameplay acceptance, treat the union as the acceptance set.
- If back/gameplay descriptions conflict with master, master is source of truth.
- If unsure, choose OK (do not guess).

Tasks:
""".strip()


def _strip_refs_clause(text: str) -> str:
    s = str(text or "").strip()
    idx = s.lower().find("refs:")
    if idx >= 0:
        s = s[:idx].rstrip()
    return re.sub(r"\s+", " ", s).strip()


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _truncate(text: str, *, max_chars: int) -> str:
    s = str(text or "")
    if len(s) <= max_chars:
        return s
    return s[: max_chars - 3] + "..."


def _view_items_as_list(view_obj: Any) -> list[dict[str, Any]]:
    if isinstance(view_obj, list):
        return [x for x in view_obj if isinstance(x, dict)]
    if isinstance(view_obj, dict):
        items = view_obj.get("tasks") or view_obj.get("master", {}).get("tasks") or []
        if isinstance(items, list):
            return [x for x in items if isinstance(x, dict)]
    return []


def load_task_maps() -> tuple[list[int], dict[int, dict[str, Any]], dict[int, dict[str, Any]], dict[int, dict[str, Any]]]:
    root = repo_root()
    tasks_json = _read_json(root / ".taskmaster" / "tasks" / "tasks.json")
    tasks = (tasks_json.get("master") or {}).get("tasks") or []
    master_by_id: dict[int, dict[str, Any]] = {}
    ids: list[int] = []
    for item in tasks:
        if not isinstance(item, dict):
            continue
        try:
            tid = int(str(item.get("id") or "").strip())
        except ValueError:
            continue
        master_by_id[tid] = item
        ids.append(tid)

    def _load_view_map(path: Path) -> dict[int, dict[str, Any]]:
        if not path.exists():
            return {}
        view_obj = _read_json(path)
        out: dict[int, dict[str, Any]] = {}
        for item in _view_items_as_list(view_obj):
            try:
                tid = int(str(item.get("taskmaster_id") or "").strip())
            except ValueError:
                continue
            out[tid] = item
        return out

    back_by_id = _load_view_map(root / ".taskmaster" / "tasks" / "tasks_back.json")
    gameplay_by_id = _load_view_map(root / ".taskmaster" / "tasks" / "tasks_gameplay.json")
    return sorted(set(ids)), master_by_id, back_by_id, gameplay_by_id


def _task_brief(
    task_id: int,
    *,
    max_acceptance_items: int,
    master: dict[str, Any] | None,
    back: dict[str, Any] | None,
    gameplay: dict[str, Any] | None,
) -> str:
    master = master or {}
    back = back or {}
    gameplay = gameplay or {}

    def _list(entry: dict[str, Any], key: str) -> list[str]:
        raw = entry.get(key) or []
        if not isinstance(raw, list):
            return []
        out: list[str] = []
        for x in raw:
            s = str(x or "").strip()
            if s and s not in out:
                out.append(s)
        return out

    def _acc(entry: dict[str, Any]) -> list[str]:
        raw = entry.get("acceptance") or []
        if not isinstance(raw, list):
            return []
        items = [_strip_refs_clause(x) for x in raw]
        return [s for s in items if s][:max_acceptance_items]

    lines = [
        f"### Task {task_id}: {str(master.get('title') or '').strip()}",
        f"- master.description: {_truncate(master.get('description') or '', max_chars=400)}",
        f"- master.details: {_truncate(master.get('details') or '', max_chars=800)}",
        f"- back.description: {_truncate(back.get('description') or '', max_chars=400)}",
        f"- gameplay.description: {_truncate(gameplay.get('description') or '', max_chars=400)}",
    ]
    overlay_refs = sorted(set(_list(back, "overlay_refs") + _list(gameplay, "overlay_refs")))
    contract_refs = sorted(set(_list(back, "contractRefs") + _list(gameplay, "contractRefs")))
    labels = sorted(set(_list(back, "labels") + _list(gameplay, "labels")))
    if overlay_refs:
        lines.append(f"- overlay_refs: {', '.join(overlay_refs[:12])}{' ...' if len(overlay_refs) > 12 else ''}")
    if contract_refs:
        lines.append(f"- contractRefs: {', '.join(contract_refs[:20])}{' ...' if len(contract_refs) > 20 else ''}")
    if labels:
        lines.append(f"- labels: {', '.join(labels[:20])}{' ...' if len(labels) > 20 else ''}")
    back_acc = _acc(back)
    gameplay_acc = _acc(gameplay)
    if back_acc:
        lines.append("- acceptance (view=back):")
        lines.extend([f"  - {a}" for a in back_acc])
    if gameplay_acc:
        lines.append("- acceptance (view=gameplay):")
        lines.extend([f"  - {a}" for a in gameplay_acc])
    if not back_acc and not gameplay_acc:
        lines.append("- acceptance: (missing in both views)")
    return "\n".join(lines).strip()


def _build_batch_prompt(
    *,
    batch: list[int],
    max_acceptance_items: int,
    max_task_brief_chars: int,
    master_by_id: dict[int, dict[str, Any]],
    back_by_id: dict[int, dict[str, Any]],
    gameplay_by_id: dict[int, dict[str, Any]],
) -> str:
    blocks = [PROMPT_HEADER, ""]
    for tid in batch:
        brief = _task_brief(
            tid,
            max_acceptance_items=max_acceptance_items,
            master=master_by_id.get(tid),
            back=back_by_id.get(tid),
            gameplay=gameplay_by_id.get(tid),
        )
        blocks.append(_truncate(brief, max_chars=max_task_brief_chars))
        blocks.append("")
    return "\n".join(blocks).strip() + "\n"


def build_prompt_with_budget(
    *,
    batch: list[int],
    max_acceptance_items: int,
    max_prompt_chars: int,
    master_by_id: dict[int, dict[str, Any]],
    back_by_id: dict[int, dict[str, Any]],
    gameplay_by_id: dict[int, dict[str, Any]],
) -> tuple[str, bool, int]:
    budget = 3200
    prompt = _build_batch_prompt(
        batch=batch,
        max_acceptance_items=max_acceptance_items,
        max_task_brief_chars=budget,
        master_by_id=master_by_id,
        back_by_id=back_by_id,
        gameplay_by_id=gameplay_by_id,
    )
    if len(prompt) <= max_prompt_chars:
        return prompt, False, budget

    trimmed = True
    header_len = len(
        _build_batch_prompt(
            batch=[],
            max_acceptance_items=max_acceptance_items,
            max_task_brief_chars=budget,
            master_by_id=master_by_id,
            back_by_id=back_by_id,
            gameplay_by_id=gameplay_by_id,
        )
    )
    budget = max(250, int((max_prompt_chars - header_len) / max(1, len(batch))))
    for _ in range(6):
        prompt = _build_batch_prompt(
            batch=batch,
            max_acceptance_items=max_acceptance_items,
            max_task_brief_chars=budget,
            master_by_id=master_by_id,
            back_by_id=back_by_id,
            gameplay_by_id=gameplay_by_id,
        )
        if len(prompt) <= max_prompt_chars:
            break
        budget = max(120, int(budget * 0.8))
    if len(prompt) > max_prompt_chars:
        prompt = _build_batch_prompt(
            batch=batch,
            max_acceptance_items=max_acceptance_items,
            max_task_brief_chars=120,
            master_by_id=master_by_id,
            back_by_id=back_by_id,
            gameplay_by_id=gameplay_by_id,
        )
    return prompt, trimmed, budget

