from __future__ import annotations

import re


def _normalize_newlines(text: str) -> str:
    return text.replace("\r\n", "\n").replace("\r", "\n")


def _join_bullets(items: list[str]) -> str:
    cleaned = [str(item).strip() for item in items if str(item).strip()]
    if not cleaned:
        return ""
    return "".join(f"- {item}\n\n" for item in cleaned).rstrip() + "\n"


def _find_intro_bounds(text: str) -> tuple[int, int] | None:
    match = re.search(r"(?m)^# .*$", text)
    if not match:
        return None
    start = match.end()
    next_task = re.search(r"(?m)^Task coverage:\s*$", text[start:])
    next_section = re.search(r"(?m)^## .*$", text[start:])
    end_candidates = []
    if next_task:
        end_candidates.append(start + next_task.start())
    if next_section:
        end_candidates.append(start + next_section.start())
    end = min(end_candidates) if end_candidates else len(text)
    return start, end


def _intro_is_simple(block: str) -> bool:
    stripped = block.strip()
    if not stripped:
        return True
    forbidden = ("- ", "* ", "> ", "### ", "|", "```")
    for line in stripped.splitlines():
        line_stripped = line.strip()
        if not line_stripped:
            continue
        if any(line_stripped.startswith(prefix) for prefix in forbidden):
            return False
    return True


def _replace_simple_intro(text: str, purpose: str) -> str:
    if not purpose.strip():
        return text
    bounds = _find_intro_bounds(text)
    if bounds is None:
        return text
    start, end = bounds
    block = text[start:end]
    if not _intro_is_simple(block):
        return text
    replacement = "\n\n" + purpose.strip() + "\n\n"
    return text[:start] + replacement + text[end:]


def _find_task_coverage_bounds(text: str) -> tuple[int, int] | None:
    match = re.search(r"(?m)^Task coverage:\s*$", text)
    if not match:
        return None
    start = match.start()
    next_section = re.search(r"(?m)^## .*$", text[match.end() :])
    end = match.end() + next_section.start() if next_section else len(text)
    return start, end


def _task_coverage_is_simple(block: str) -> bool:
    lines = [line.strip() for line in block.splitlines() if line.strip()]
    if not lines or lines[0] != "Task coverage:":
        return False
    return all(line == "Task coverage:" or line.startswith("- ") for line in lines)


def _replace_simple_task_coverage(text: str, task_ids: list[str]) -> str:
    if not task_ids:
        return text
    bounds = _find_task_coverage_bounds(text)
    if bounds is None:
        return text
    start, end = bounds
    block = text[start:end]
    if not _task_coverage_is_simple(block):
        return text
    replacement = "Task coverage:\n\n- " + ", ".join(task_ids) + "\n\n"
    return text[:start] + replacement + text[end:]


def _find_section_bounds(text: str, heading: str) -> tuple[int, int, int] | None:
    pattern = re.compile(rf"(?m)^## {re.escape(heading)}\s*$")
    match = pattern.search(text)
    if not match:
        return None
    body_start = match.end()
    next_section = re.search(r"(?m)^## .*$", text[body_start:])
    end = body_start + next_section.start() if next_section else len(text)
    return match.start(), body_start, end


def _collect_h2_headings(text: str) -> list[str]:
    return [match.group(1).strip() for match in re.finditer(r"(?m)^## (.+?)\s*$", text)]


def _section_is_simple(block: str) -> bool:
    lines = [line.strip() for line in block.splitlines() if line.strip()]
    if not lines:
        return True
    for line in lines:
        if line.startswith("### ") or line.startswith("|") or line.startswith("```") or re.match(r"^\d+\.", line):
            return False
    return True


def _replace_simple_section(text: str, heading: str, bullets: list[str]) -> str:
    if not heading.strip() or not bullets:
        return text
    bounds = _find_section_bounds(text, heading)
    bullet_block = _join_bullets(bullets)
    if bounds is None:
        suffix = "" if text.endswith("\n") else "\n"
        return text + suffix + f"\n## {heading}\n\n" + bullet_block
    section_start, body_start, section_end = bounds
    current_body = text[body_start:section_end]
    if not _section_is_simple(current_body):
        return text
    replacement = f"\n\n{bullet_block}\n"
    return text[:body_start] + replacement + text[section_end:]


def apply_scaffold_update_to_existing_markdown(
    *,
    current_markdown: str,
    scaffold_update: dict[str, object],
) -> str:
    text = _normalize_newlines(current_markdown)
    update_sections = [
        section
        for section in scaffold_update.get("sections") or []
        if isinstance(section, dict) and str(section.get("heading") or "").strip()
    ]
    current_headings = _collect_h2_headings(text)
    if current_headings and update_sections:
        overlap = {
            str(section.get("heading") or "").strip()
            for section in update_sections
            if str(section.get("heading") or "").strip() in current_headings
        }
        if not overlap:
            return text
    purpose = str(scaffold_update.get("purpose") or "").strip()
    if purpose:
        text = _replace_simple_intro(text, purpose)
    task_ids = [str(item).strip() for item in scaffold_update.get("task_ids") or [] if str(item).strip()]
    if task_ids:
        text = _replace_simple_task_coverage(text, task_ids)
    for section in update_sections:
        heading = str(section.get("heading") or "").strip()
        bullets = [str(item).strip() for item in section.get("bullets") or [] if str(item).strip()]
        text = _replace_simple_section(text, heading, bullets)
    return text
