from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from _overlay_generator_contract import REQUIRED_CHECKLIST_HEADINGS
from _overlay_generator_prompting import compact_companion_docs, truncate
from _overlay_generator_support import extract_json_object


def build_overlay_page_scaffold_prompt(
    *,
    prd_path: Path,
    prd_text: str,
    prd_id: str,
    companion_docs: list[dict[str, str]],
    page: dict[str, Any],
    page_context: dict[str, Any],
    base_page: dict[str, Any],
    current_page_text: str,
) -> str:
    companion_json = json.dumps(compact_companion_docs(companion_docs, excerpt_chars=800), ensure_ascii=False, indent=2)
    page_context_json = json.dumps(page_context, ensure_ascii=False, indent=2)
    page_profile_json = json.dumps(
        {
            "filename": str(page.get("filename") or ""),
            "page_kind": str(page.get("page_kind") or ""),
            "current_title": str(page.get("current_title") or ""),
            "headings": list(page.get("headings") or []),
        },
        ensure_ascii=False,
        indent=2,
    )
    base_page_json = json.dumps(base_page, ensure_ascii=False, indent=2)
    checklist_note = (
        "If the target page is ACCEPTANCE_CHECKLIST.md, sections must contain exactly these headings: "
        + " / ".join(REQUIRED_CHECKLIST_HEADINGS)
    )
    constraints = [
        "You are updating a single overlay page for docs/architecture/overlays/<PRD-ID>/08.",
        "Output must be JSON only. No Markdown fences. No prose before or after JSON.",
        "Return a scaffold update object, not a full page rewrite.",
        'Schema: {"filename":"...", "update":{"purpose":"...", "adr_refs":["ADR-0004"], "arch_refs":["CH04"], "test_refs":["scripts/python/validate_task_overlays.py"], "task_ids":["66"], "sections":[{"heading":"...", "bullets":["..."]}]}}',
        "Filename must exactly match the target overlay page filename.",
        "The scaffold base page already owns filename, page_kind, title, and current section order.",
        "Do not rename the title. Do not change filename. Do not change page_kind.",
        "The update object is sparse: omit any field that does not need change.",
        "If an existing section already matches the supplied source, omit that section from update so the scaffold base page is preserved verbatim.",
        "When a section needs edits, preserve unchanged bullets verbatim and only change the minimum necessary bullets.",
        "Keep section headings aligned with the scaffold base page unless a new heading is strictly required by the supplied source.",
        "Prefer minimal edits that keep the generated page close to the current page structure and semantics.",
        "Do not invent ADR ids, chapter refs, shipped contracts, or test refs that are not grounded in the provided context.",
        checklist_note,
    ]
    source_blocks = [
        f"PRD-ID: {prd_id}",
        f"Primary PRD path: {prd_path.as_posix()}",
        "Primary PRD excerpt:",
        truncate(prd_text, max_chars=6000),
        "",
        f"Target overlay page: {str(page.get('filename') or '').strip()}",
        "Target page profile:",
        page_profile_json,
        "",
        "Relevant task/page context:",
        page_context_json,
        "",
        "Scaffold base page:",
        truncate(base_page_json, max_chars=7000),
        "",
        "Companion documents:",
        companion_json,
        "",
        "Current page excerpt:",
        truncate(current_page_text, max_chars=5000),
    ]
    return "\n".join(constraints + [""] + source_blocks).strip() + "\n"


def parse_and_validate_scaffold_update(
    *,
    raw_output: str,
    expected_filename: str,
) -> dict[str, Any]:
    obj = extract_json_object(raw_output)
    filename = str(obj.get("filename") or "").strip()
    if filename != str(expected_filename).strip():
        raise ValueError(f"Scaffold filename mismatch: expected={expected_filename} got={filename}")
    update = obj.get("update")
    if not isinstance(update, dict):
        raise ValueError("Model output must contain an 'update' object.")
    return {
        "purpose": str(update.get("purpose") or "").strip(),
        "adr_refs": [str(item).strip() for item in update.get("adr_refs") or [] if str(item).strip()],
        "arch_refs": [str(item).strip() for item in update.get("arch_refs") or [] if str(item).strip()],
        "test_refs": [str(item).strip() for item in update.get("test_refs") or [] if str(item).strip()],
        "task_ids": [str(item).strip() for item in update.get("task_ids") or [] if str(item).strip()],
        "sections": [
            {
                "heading": str(section.get("heading") or "").strip(),
                "bullets": [str(item).strip() for item in section.get("bullets") or [] if str(item).strip()],
            }
            for section in update.get("sections") or []
            if isinstance(section, dict)
        ],
    }
