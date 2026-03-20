from __future__ import annotations

from typing import Any


def build_base_page_from_profile(profile_page: dict[str, Any], page_context: dict[str, Any]) -> dict[str, Any]:
    task_ids: list[str] = []
    for key in ("master_task_ids", "back_task_ids", "gameplay_task_ids"):
        for item in page_context.get(key) or []:
            value = str(item).strip()
            if value and value not in task_ids:
                task_ids.append(value)

    sections = []
    for heading in profile_page.get("headings") or []:
        heading_value = str(heading).strip()
        if not heading_value:
            continue
        sections.append({"heading": heading_value, "bullets": []})

    return {
        "filename": str(profile_page.get("filename") or ""),
        "page_kind": str(profile_page.get("page_kind") or ""),
        "title": str(profile_page.get("current_title") or profile_page.get("filename") or ""),
        "purpose": "",
        "adr_refs": [],
        "arch_refs": [],
        "test_refs": [],
        "task_ids": task_ids,
        "sections": sections,
    }


def merge_page_patch(base_page: dict[str, Any], patch_payload: dict[str, Any]) -> dict[str, Any]:
    merged = dict(base_page)
    for key in ("title", "purpose"):
        value = str(patch_payload.get(key) or "").strip()
        if value:
            merged[key] = value

    for key in ("adr_refs", "arch_refs", "test_refs", "task_ids"):
        values = [str(item).strip() for item in patch_payload.get(key) or [] if str(item).strip()]
        if values:
            merged[key] = values

    sections = []
    for section in patch_payload.get("sections") or []:
        if not isinstance(section, dict):
            continue
        heading = str(section.get("heading") or "").strip()
        bullets = [str(item).strip() for item in section.get("bullets") or [] if str(item).strip()]
        if not heading:
            continue
        sections.append({"heading": heading, "bullets": bullets})
    if sections:
        merged["sections"] = sections

    merged["filename"] = str(base_page.get("filename") or "")
    merged["page_kind"] = str(base_page.get("page_kind") or "")
    return merged
