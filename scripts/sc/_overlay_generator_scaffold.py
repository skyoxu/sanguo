from __future__ import annotations

from typing import Any


def _collect_task_ids(page_context: dict[str, Any]) -> list[str]:
    task_ids: list[str] = []
    for key in ("master_task_ids", "back_task_ids", "gameplay_task_ids"):
        for item in page_context.get(key) or []:
            value = str(item).strip()
            if value and value not in task_ids:
                task_ids.append(value)
    return task_ids


def build_scaffold_base_page(
    profile_page: dict[str, Any],
    page_context: dict[str, Any],
    *,
    current_page: dict[str, Any] | None,
) -> dict[str, Any]:
    if current_page is not None:
        return {
            "filename": str(current_page.get("filename") or profile_page.get("filename") or ""),
            "page_kind": str(current_page.get("page_kind") or profile_page.get("page_kind") or ""),
            "title": str(current_page.get("title") or ""),
            "purpose": str(current_page.get("purpose") or ""),
            "adr_refs": list(current_page.get("adr_refs") or []),
            "arch_refs": list(current_page.get("arch_refs") or []),
            "test_refs": list(current_page.get("test_refs") or []),
            "task_ids": list(current_page.get("task_ids") or []),
            "sections": [dict(section) for section in current_page.get("sections") or []],
        }

    sections = []
    for heading in profile_page.get("headings") or []:
        heading_value = str(heading).strip()
        if heading_value:
            sections.append({"heading": heading_value, "bullets": []})
    return {
        "filename": str(profile_page.get("filename") or ""),
        "page_kind": str(profile_page.get("page_kind") or ""),
        "title": str(profile_page.get("current_title") or profile_page.get("filename") or ""),
        "purpose": "",
        "adr_refs": [],
        "arch_refs": [],
        "test_refs": [],
        "task_ids": _collect_task_ids(page_context),
        "sections": sections,
    }


def merge_scaffold_update(base_page: dict[str, Any], update: dict[str, Any]) -> dict[str, Any]:
    merged = dict(base_page)

    purpose = str(update.get("purpose") or "").strip()
    if purpose:
        merged["purpose"] = purpose

    for key in ("adr_refs", "arch_refs", "test_refs", "task_ids"):
        values = [str(item).strip() for item in update.get(key) or [] if str(item).strip()]
        if values:
            merged[key] = values

    update_sections = {
        str(section.get("heading") or "").strip(): [str(item).strip() for item in section.get("bullets") or [] if str(item).strip()]
        for section in update.get("sections") or []
        if isinstance(section, dict) and str(section.get("heading") or "").strip()
    }
    if update_sections:
        merged_sections: list[dict[str, Any]] = []
        seen: set[str] = set()
        for section in merged.get("sections") or []:
            heading = str(section.get("heading") or "").strip()
            if not heading:
                continue
            bullets = update_sections.get(heading, list(section.get("bullets") or []))
            merged_sections.append({"heading": heading, "bullets": bullets})
            seen.add(heading)
        for heading, bullets in update_sections.items():
            if heading in seen:
                continue
            merged_sections.append({"heading": heading, "bullets": bullets})
        merged["sections"] = merged_sections

    merged["filename"] = str(base_page.get("filename") or "")
    merged["page_kind"] = str(base_page.get("page_kind") or "")
    merged["title"] = str(base_page.get("title") or "")
    return merged


def select_pages_by_family(profile: list[dict[str, Any]], family: str) -> list[dict[str, Any]]:
    family_value = str(family or "all").strip().lower()
    if family_value in {"", "all"}:
        return list(profile)
    if family_value == "core":
        return [
            page
            for page in profile
            if str(page.get("page_kind") or "") in {"index", "acceptance-checklist", "routing"}
        ]
    return [page for page in profile if str(page.get("page_kind") or "") == family_value]
