from __future__ import annotations

import re
from typing import Any


FRONT_MATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n?", re.DOTALL)


def _extract_front_matter(text: str) -> tuple[dict[str, list[str] | str], str]:
    result: dict[str, list[str] | str] = {
        "PRD-ID": "",
        "Title": "",
        "Status": "",
        "ADR-Refs": [],
        "Arch-Refs": [],
        "Test-Refs": [],
    }
    match = FRONT_MATTER_RE.match(text)
    if not match:
        return result, text

    fm_text = match.group(1)
    current_key = ""
    for raw_line in fm_text.splitlines():
        line = raw_line.rstrip()
        stripped = line.strip()
        if not stripped:
            continue
        if ":" in stripped and not stripped.startswith("-"):
            key, value = stripped.split(":", 1)
            key = key.strip()
            value = value.strip()
            current_key = key
            if key in {"ADR-Refs", "Arch-Refs", "Test-Refs"}:
                result[key] = [value] if value else []
            elif key in result:
                result[key] = value
            continue
        if stripped.startswith("-") and current_key in {"ADR-Refs", "Arch-Refs", "Test-Refs"}:
            value = stripped[1:].strip()
            if value:
                refs = list(result.get(current_key) or [])
                refs.append(value)
                result[current_key] = refs

    return result, text[match.end() :]


def parse_existing_page_markdown(*, filename: str, page_kind: str, markdown_text: str) -> dict[str, Any]:
    front_matter, body = _extract_front_matter(markdown_text)
    title = str(front_matter.get("Title") or "").strip()
    purpose_lines: list[str] = []
    task_ids: list[str] = []
    sections: list[dict[str, Any]] = []
    current_section: dict[str, Any] | None = None
    capture_purpose = False
    capture_task_ids = False

    for raw_line in body.splitlines():
        line = raw_line.rstrip()
        stripped = line.strip()
        if stripped.startswith("# "):
            if not title:
                title = stripped[2:].strip()
            capture_purpose = True
            capture_task_ids = False
            continue
        if stripped.startswith("## "):
            capture_purpose = False
            capture_task_ids = False
            current_section = {"heading": stripped[3:].strip(), "bullets": []}
            sections.append(current_section)
            continue
        if stripped == "Task coverage:":
            capture_purpose = False
            capture_task_ids = True
            continue
        if capture_purpose:
            if stripped:
                purpose_lines.append(stripped)
            elif purpose_lines:
                capture_purpose = False
            continue
        if capture_task_ids:
            if stripped.startswith("-"):
                payload = stripped[1:].strip()
                for item in payload.split(","):
                    task_id = item.strip()
                    if task_id:
                        task_ids.append(task_id)
                continue
            if stripped:
                capture_task_ids = False
        if current_section is not None and stripped.startswith("-"):
            current_section["bullets"].append(stripped[1:].strip())

    return {
        "filename": filename,
        "page_kind": page_kind,
        "title": title or filename,
        "purpose": " ".join(purpose_lines).strip(),
        "adr_refs": [str(item).strip() for item in front_matter.get("ADR-Refs") or [] if str(item).strip()],
        "arch_refs": [str(item).strip() for item in front_matter.get("Arch-Refs") or [] if str(item).strip()],
        "test_refs": [str(item).strip() for item in front_matter.get("Test-Refs") or [] if str(item).strip()],
        "task_ids": task_ids,
        "sections": sections,
    }
