from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

from _overlay_generator_contract import REQUIRED_CHECKLIST_HEADINGS
from _overlay_generator_support import extract_json_object

def truncate(text: str, *, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 3] + "..."


def compact_companion_docs(companion_docs: list[dict[str, str]], *, excerpt_chars: int = 1200) -> list[dict[str, str]]:
    compacted: list[dict[str, str]] = []
    for item in companion_docs:
        compacted.append(
            {
                "path": str(item.get("path") or "").strip(),
                "excerpt": truncate(str(item.get("excerpt") or ""), max_chars=excerpt_chars),
            }
        )
    return compacted

def compact_task_digest(task_digest: dict[str, Any], *, max_tasks: int = 24, max_titles_per_cluster: int = 3) -> dict[str, Any]:
    master_tasks = []
    for task in list(task_digest.get("master_tasks") or [])[:max_tasks]:
        if not isinstance(task, dict):
            continue
        master_tasks.append(
            {
                "id": str(task.get("id") or ""),
                "title": str(task.get("title") or ""),
                "status": str(task.get("status") or ""),
                "priority": str(task.get("priority") or ""),
                "complexity": task.get("complexity"),
                "overlay": str(task.get("overlay") or ""),
                "adr_refs": list(task.get("adr_refs") or []),
                "arch_refs": list(task.get("arch_refs") or []),
            }
        )

    overlay_clusters = []
    for cluster in list(task_digest.get("overlay_clusters") or []):
        if not isinstance(cluster, dict):
            continue
        overlay_clusters.append(
            {
                "overlay_path": str(cluster.get("overlay_path") or ""),
                "master_task_ids": list(cluster.get("master_task_ids") or []),
                "back_task_ids": list(cluster.get("back_task_ids") or []),
                "gameplay_task_ids": list(cluster.get("gameplay_task_ids") or []),
                "titles": list(cluster.get("titles") or [])[:max_titles_per_cluster],
            }
        )

    return {
        "prd_id": str(task_digest.get("prd_id") or ""),
        "master_tasks": master_tasks,
        "overlay_clusters": overlay_clusters,
    }

def compact_profile(profile: list[dict[str, Any]]) -> list[dict[str, Any]]:
    compacted: list[dict[str, Any]] = []
    for item in profile:
        compacted.append(
            {
                "filename": str(item.get("filename") or ""),
                "page_kind": str(item.get("page_kind") or ""),
                "current_title": str(item.get("current_title") or ""),
                "headings": list(item.get("headings") or []),
            }
        )
    return compacted

def build_overlay_prompt(
    *,
    prd_path: Path,
    prd_text: str,
    prd_id: str,
    companion_docs: list[dict[str, str]],
    task_digest: dict[str, Any],
    profile: list[dict[str, Any]],
    profile_locked: bool,
) -> str:
    profile_json = json.dumps(compact_profile(profile), ensure_ascii=False, indent=2)
    companion_json = json.dumps(compact_companion_docs(companion_docs), ensure_ascii=False, indent=2)
    task_digest_json = json.dumps(compact_task_digest(task_digest), ensure_ascii=False, indent=2)
    checklist_note = (
        "Special rule for ACCEPTANCE_CHECKLIST.md: sections must contain exactly these headings: "
        "一、文档完整性验收 / 二、架构设计验收 / 三、代码实现验收 / 四、测试框架验收."
    )
    constraints = [
        "You are generating an overlay plan for docs/architecture/overlays/<PRD-ID>/08.",
        "Output must be JSON only. No Markdown fences. No prose before or after JSON.",
        "Schema:",
        '{"prd_id":"...", "pages":[{"filename":"...", "page_kind":"...", "title":"...", "purpose":"...", "adr_refs":["ADR-0004"], "arch_refs":["CH04"], "test_refs":["scripts/python/validate_task_overlays.py"], "task_ids":["66"], "sections":[{"heading":"...", "bullets":["..."]}]}]}',
        "All filenames must be unique.",
        "Keep each page concise: 2-4 sections per page, 2-4 bullets per section.",
        "Do not invent ADR ids or chapter refs not grounded in repository conventions.",
        "Do not invent shipped contracts. Planned contracts must be clearly framed as planned in bullets.",
        checklist_note,
    ]
    if profile_locked:
        constraints.append("You MUST return exactly one page for each provided profile filename. Do not rename, add, or remove pages.")
    else:
        constraints.append("Use the provided profile as a strong default, but you may adjust page grouping if the source clearly requires it.")

    source_blocks = [
        f"Primary PRD path: {prd_path.as_posix()}",
        "Primary PRD excerpt:",
        truncate(prd_text, max_chars=12_000),
        "",
        "Companion documents:",
        companion_json,
        "",
        "Task digest:",
        truncate(task_digest_json, max_chars=12_000),
        "",
        "Overlay profile:",
        profile_json,
        "",
        "Goal: produce a page plan that is close to the current overlay structure for this PRD, with stable filenames and task routing.",
    ]
    return "\n".join(constraints + [""] + source_blocks).strip() + "\n"


def build_overlay_page_prompt(
    *,
    prd_path: Path,
    prd_text: str,
    prd_id: str,
    companion_docs: list[dict[str, str]],
    page: dict[str, Any],
    page_context: dict[str, Any],
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
    checklist_note = (
        "If the target page is ACCEPTANCE_CHECKLIST.md, sections must contain exactly these headings: "
        + " / ".join(REQUIRED_CHECKLIST_HEADINGS)
    )
    constraints = [
        "You are updating a single overlay page for docs/architecture/overlays/<PRD-ID>/08.",
        "Output must be JSON only. No Markdown fences. No prose before or after JSON.",
        "Return exactly one page object with this schema:",
        '{"filename":"...", "page_kind":"...", "title":"...", "purpose":"...", "adr_refs":["ADR-0004"], "arch_refs":["CH04"], "test_refs":["scripts/python/validate_task_overlays.py"], "task_ids":["66"], "sections":[{"heading":"...", "bullets":["..."]}]}',
        "Filename must exactly match the target overlay page filename.",
        "Keep the page close to the current page shape and semantics; prefer minimal edits over rewrites.",
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
        "Companion documents:",
        companion_json,
        "",
        "Current page excerpt:",
        truncate(current_page_text, max_chars=5000),
    ]
    return "\n".join(constraints + [""] + source_blocks).strip() + "\n"


def build_overlay_page_patch_prompt(
    *,
    prd_path: Path,
    prd_text: str,
    prd_id: str,
    companion_docs: list[dict[str, str]],
    page: dict[str, Any],
    page_context: dict[str, Any],
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
    checklist_note = (
        "If the target page is ACCEPTANCE_CHECKLIST.md, sections must contain exactly these headings: "
        + " / ".join(REQUIRED_CHECKLIST_HEADINGS)
    )
    constraints = [
        "You are updating a single overlay page for docs/architecture/overlays/<PRD-ID>/08.",
        "Output must be JSON only. No Markdown fences. No prose before or after JSON.",
        "Return a minimal structured patch, not a full page rewrite.",
        'Schema: {"filename":"...", "patch":{"title":"...", "purpose":"...", "adr_refs":["ADR-0004"], "arch_refs":["CH04"], "test_refs":["scripts/python/validate_task_overlays.py"], "task_ids":["66"], "sections":[{"heading":"...", "bullets":["..."]}]}}',
        "Filename must exactly match the target overlay page filename.",
        "Patch should preserve current page structure where possible and only update fields that need change.",
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
        "Companion documents:",
        companion_json,
        "",
        "Current page excerpt:",
        truncate(current_page_text, max_chars=5000),
    ]
    return "\n".join(constraints + [""] + source_blocks).strip() + "\n"


def run_codex_exec(*, repo_root: Path, prompt: str, out_last_message: Path, timeout_sec: int) -> tuple[int, str, list[str]]:
    exe = shutil.which("codex")
    if not exe:
        return 127, "codex executable not found in PATH\n", ["codex"]
    out_last_message.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        exe,
        "exec",
        "-s",
        "read-only",
        "-C",
        str(repo_root),
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
            cwd=str(repo_root),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=timeout_sec,
        )
    except subprocess.TimeoutExpired:
        return 124, "codex exec timeout\n", cmd
    except Exception as exc:  # noqa: BLE001
        return 1, f"codex exec failed to start: {exc}\n", cmd
    return proc.returncode or 0, proc.stdout or "", cmd


def parse_and_validate_plan(
    *,
    raw_output: str,
    profile: list[dict[str, Any]],
    profile_locked: bool,
    expected_prd_id: str,
) -> dict[str, Any]:
    obj = extract_json_object(raw_output)
    pages = obj.get("pages")
    if not isinstance(pages, list) or not pages:
        raise ValueError("Model output must contain a non-empty 'pages' array.")

    expected_filenames = [str(item.get("filename") or "") for item in profile]
    expected_set = set(expected_filenames)
    actual_filenames = [str(item.get("filename") or "") for item in pages]
    if len(actual_filenames) != len(set(actual_filenames)):
        raise ValueError("Model output contains duplicate page filenames.")
    if profile_locked:
        if set(actual_filenames) != expected_set:
            raise ValueError("Locked profile mismatch: model output filenames do not match expected profile.")

    normalized_pages: list[dict[str, Any]] = []
    page_index = {str(item.get("filename") or ""): item for item in pages}
    iteration = expected_filenames if profile_locked else actual_filenames
    for filename in iteration:
        page = page_index.get(filename)
        if not isinstance(page, dict):
            continue
        normalized_pages.append(
            {
                "filename": filename,
                "page_kind": str(page.get("page_kind") or ""),
                "title": str(page.get("title") or filename),
                "purpose": str(page.get("purpose") or ""),
                "adr_refs": [str(item) for item in page.get("adr_refs") or [] if str(item).strip()],
                "arch_refs": [str(item) for item in page.get("arch_refs") or [] if str(item).strip()],
                "test_refs": [str(item) for item in page.get("test_refs") or [] if str(item).strip()],
                "task_ids": [str(item) for item in page.get("task_ids") or [] if str(item).strip()],
                "sections": [
                    {
                        "heading": str(section.get("heading") or "").strip(),
                        "bullets": [str(item).strip() for item in section.get("bullets") or [] if str(item).strip()],
                    }
                    for section in page.get("sections") or []
                    if isinstance(section, dict)
                ],
            }
        )

    return {
        "prd_id": str(obj.get("prd_id") or expected_prd_id),
        "pages": normalized_pages,
    }


def parse_and_validate_page(
    *,
    raw_output: str,
    expected_filename: str,
    expected_page_kind: str,
) -> dict[str, Any]:
    obj = extract_json_object(raw_output)
    page = obj.get("page") if isinstance(obj.get("page"), dict) else obj
    if not isinstance(page, dict):
        raise ValueError("Model output must be a page object.")

    filename = str(page.get("filename") or "").strip()
    if filename != str(expected_filename).strip():
        raise ValueError(f"Page filename mismatch: expected={expected_filename} got={filename}")

    return {
        "filename": filename,
        "page_kind": str(page.get("page_kind") or expected_page_kind),
        "title": str(page.get("title") or filename),
        "purpose": str(page.get("purpose") or ""),
        "adr_refs": [str(item) for item in page.get("adr_refs") or [] if str(item).strip()],
        "arch_refs": [str(item) for item in page.get("arch_refs") or [] if str(item).strip()],
        "test_refs": [str(item) for item in page.get("test_refs") or [] if str(item).strip()],
        "task_ids": [str(item) for item in page.get("task_ids") or [] if str(item).strip()],
        "sections": [
            {
                "heading": str(section.get("heading") or "").strip(),
                "bullets": [str(item).strip() for item in section.get("bullets") or [] if str(item).strip()],
            }
            for section in page.get("sections") or []
            if isinstance(section, dict)
        ],
    }


def parse_and_validate_page_patch(
    *,
    raw_output: str,
    expected_filename: str,
) -> dict[str, Any]:
    obj = extract_json_object(raw_output)
    filename = str(obj.get("filename") or "").strip()
    if filename != str(expected_filename).strip():
        raise ValueError(f"Patch filename mismatch: expected={expected_filename} got={filename}")
    patch = obj.get("patch")
    if not isinstance(patch, dict):
        raise ValueError("Model output must contain a 'patch' object.")
    return {
        "title": str(patch.get("title") or "").strip(),
        "purpose": str(patch.get("purpose") or "").strip(),
        "adr_refs": [str(item).strip() for item in patch.get("adr_refs") or [] if str(item).strip()],
        "arch_refs": [str(item).strip() for item in patch.get("arch_refs") or [] if str(item).strip()],
        "test_refs": [str(item).strip() for item in patch.get("test_refs") or [] if str(item).strip()],
        "task_ids": [str(item).strip() for item in patch.get("task_ids") or [] if str(item).strip()],
        "sections": [
            {
                "heading": str(section.get("heading") or "").strip(),
                "bullets": [str(item).strip() for item in section.get("bullets") or [] if str(item).strip()],
            }
            for section in patch.get("sections") or []
            if isinstance(section, dict)
        ],
    }
