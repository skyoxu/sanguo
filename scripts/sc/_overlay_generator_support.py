from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

from _overlay_generator_contract import (
    REQUIRED_CHECKLIST_HEADINGS,
    parse_prd_docs_csv,
    validate_required_prd_docs,
)

OVERLAY_ROOT_RE = re.compile(r"docs/architecture/overlays/([^/]+)/08", re.IGNORECASE)

def read_text(path: Path, *, max_chars: int | None = None) -> str:
    text = path.read_text(encoding="utf-8", errors="ignore")
    if max_chars is not None and len(text) > max_chars:
        return text[: max_chars - 3] + "..."
    return text


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")

def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def normalize_relpath(path: Path, *, root: Path) -> str:
    return str(path.resolve().relative_to(root.resolve())).replace("\\", "/")


def extract_json_object(text: str) -> dict[str, Any]:
    raw = text.strip()
    if not raw:
        raise ValueError("Empty model output.")
    try:
        obj = json.loads(raw)
        if isinstance(obj, dict):
            return obj
    except Exception:
        pass

    match = re.search(r"\{.*\}", raw, flags=re.DOTALL)
    if not match:
        raise ValueError("No JSON object found in model output.")
    obj = json.loads(match.group(0))
    if not isinstance(obj, dict):
        raise ValueError("Model output JSON must be an object.")
    return obj


def load_task_payloads(repo_root: Path) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    tasks_json_path = repo_root / ".taskmaster" / "tasks" / "tasks.json"
    tasks_back_path = repo_root / ".taskmaster" / "tasks" / "tasks_back.json"
    tasks_gameplay_path = repo_root / ".taskmaster" / "tasks" / "tasks_gameplay.json"
    tasks_json = json.loads(tasks_json_path.read_text(encoding="utf-8"))
    tasks_back = json.loads(tasks_back_path.read_text(encoding="utf-8"))
    tasks_gameplay = json.loads(tasks_gameplay_path.read_text(encoding="utf-8"))
    if not isinstance(tasks_back, list) or not isinstance(tasks_gameplay, list):
        raise ValueError("tasks_back.json and tasks_gameplay.json must be JSON arrays.")
    return tasks_json, tasks_back, tasks_gameplay


def infer_prd_id(
    provided: str | None,
    tasks_json: dict[str, Any],
    tasks_back: list[dict[str, Any]],
    tasks_gameplay: list[dict[str, Any]],
) -> str:
    if str(provided or "").strip():
        return str(provided).strip()

    counts: Counter[str] = Counter()

    master_tasks = []
    if isinstance(tasks_json, dict):
        master = tasks_json.get("master")
        if isinstance(master, dict):
            master_tasks = master.get("tasks") or []
    for task in master_tasks:
        if not isinstance(task, dict):
            continue
        overlay = str(task.get("overlay") or "").strip()
        match = OVERLAY_ROOT_RE.search(overlay)
        if match:
            counts[match.group(1)] += 1

    for collection in (tasks_back, tasks_gameplay):
        for task in collection:
            if not isinstance(task, dict):
                continue
            overlay_refs = task.get("overlay_refs") or []
            if not isinstance(overlay_refs, list):
                continue
            for overlay_ref in overlay_refs:
                match = OVERLAY_ROOT_RE.search(str(overlay_ref))
                if match:
                    counts[match.group(1)] += 1

    if counts:
        return counts.most_common(1)[0][0]
    raise ValueError("Unable to infer PRD-ID from task overlay references; pass --prd-id explicitly.")


def discover_companion_docs(
    prd_path: Path,
    *,
    repo_root: Path,
    explicit_paths: list[str],
) -> list[Path]:
    discovered: dict[str, Path] = {}

    for raw_path in explicit_paths:
        candidate = Path(raw_path)
        if not candidate.is_absolute():
            candidate = (repo_root / candidate).resolve()
        if candidate.exists() and candidate != prd_path.resolve():
            discovered[str(candidate)] = candidate

    current_stage = repo_root / "CURRENT_STAGE_FOR_BMAD.md"
    if current_stage.exists() and current_stage.resolve() != prd_path.resolve():
        discovered[str(current_stage.resolve())] = current_stage.resolve()

    return sorted(discovered.values(), key=lambda item: item.name.lower())


def classify_page_kind(filename: str) -> str:
    name = filename.lower()
    if filename == "_index.md":
        return "index"
    if filename == "ACCEPTANCE_CHECKLIST.md":
        return "acceptance-checklist"
    if "contracts" in name:
        return "contracts"
    if "governance" in name:
        return "governance"
    if "rules-freeze" in name or "routing" in name:
        return "routing"
    return "feature"


def _extract_title_and_headings(path: Path) -> tuple[str, list[str]]:
    text = read_text(path)
    title = ""
    headings: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("Title:") and not title:
            title = stripped.split(":", 1)[1].strip()
            continue
        if stripped.startswith("# "):
            if not title:
                title = stripped[2:].strip()
            continue
        if stripped.startswith("## "):
            headings.append(stripped[3:].strip())
    return title, headings[:6]


def discover_existing_overlay_profile(repo_root: Path, prd_id: str) -> list[dict[str, Any]]:
    overlay_dir = repo_root / "docs" / "architecture" / "overlays" / prd_id / "08"
    if not overlay_dir.exists():
        return []

    items: list[dict[str, Any]] = []
    for path in sorted(overlay_dir.glob("*.md"), key=lambda item: item.name.lower()):
        title, headings = _extract_title_and_headings(path)
        items.append(
            {
                "filename": path.name,
                "page_kind": classify_page_kind(path.name),
                "current_title": title or path.stem,
                "headings": headings,
                "path": normalize_relpath(path, root=repo_root),
            }
        )
    return items


def build_default_overlay_profile(prd_id: str) -> list[dict[str, Any]]:
    return [
        {"filename": "_index.md", "page_kind": "index", "current_title": f"{prd_id} Feature Slice Index", "headings": ["Directory Role", "Document Groups"]},
        {"filename": "ACCEPTANCE_CHECKLIST.md", "page_kind": "acceptance-checklist", "current_title": "Acceptance Checklist", "headings": REQUIRED_CHECKLIST_HEADINGS},
        {"filename": "08-rules-freeze-and-assertion-routing.md", "page_kind": "routing", "current_title": "Rules Freeze and Assertion Routing", "headings": ["Inputs", "Routing Rules"]},
        {"filename": "08-business-acceptance-scenarios.md", "page_kind": "feature", "current_title": "Business Acceptance Scenarios", "headings": ["Scenario Groups", "Acceptance Evidence"]},
        {"filename": "08-Contracts-Core-Events.md", "page_kind": "contracts", "current_title": "Contracts and Events", "headings": ["Current Contracts", "Planned Additions"]},
        {"filename": "08-Contracts-Security.md", "page_kind": "contracts", "current_title": "Security Contracts", "headings": ["Security Constraints", "Audit Requirements"]},
        {"filename": "08-Contracts-Quality-Metrics.md", "page_kind": "contracts", "current_title": "Quality and Metrics", "headings": ["Gate Entry Points", "Evidence"]},
        {"filename": "08-feature-slice-main-loop.md", "page_kind": "feature", "current_title": "Main Loop Feature Slice", "headings": ["Scope", "Task Coverage"]},
        {"filename": "08-governance-freeze-change-control.md", "page_kind": "governance", "current_title": "Freeze Change Control", "headings": ["Ownership", "Change Rules"]},
    ]


def build_task_digest(
    prd_id: str,
    tasks_json: dict[str, Any],
    tasks_back: list[dict[str, Any]],
    tasks_gameplay: list[dict[str, Any]],
) -> dict[str, Any]:
    overlay_prefix = f"docs/architecture/overlays/{prd_id}/08/"
    master_tasks = []
    if isinstance(tasks_json, dict):
        master = tasks_json.get("master")
        if isinstance(master, dict):
            master_tasks = master.get("tasks") or []

    relevant_master = [
        task
        for task in master_tasks
        if isinstance(task, dict) and str(task.get("overlay") or "").startswith(overlay_prefix)
    ]
    if not relevant_master:
        relevant_master = [task for task in master_tasks if isinstance(task, dict)]

    def compact_master(task: dict[str, Any]) -> dict[str, Any]:
        subtasks = task.get("subtasks") or []
        return {
            "id": str(task.get("id")),
            "title": str(task.get("title") or ""),
            "status": str(task.get("status") or ""),
            "priority": str(task.get("priority") or ""),
            "complexity": task.get("complexity"),
            "overlay": str(task.get("overlay") or ""),
            "adr_refs": list(task.get("adrRefs") or []),
            "arch_refs": list(task.get("archRefs") or []),
            "subtasks_count": len(subtasks) if isinstance(subtasks, list) else 0,
        }

    def relevant_view_tasks(collection: list[dict[str, Any]]) -> list[dict[str, Any]]:
        relevant = []
        for task in collection:
            if not isinstance(task, dict):
                continue
            overlay_refs = task.get("overlay_refs") or []
            if isinstance(overlay_refs, list) and any(str(item).startswith(overlay_prefix) for item in overlay_refs):
                relevant.append(task)
        return relevant or [task for task in collection if isinstance(task, dict)]

    def compact_view(task: dict[str, Any]) -> dict[str, Any]:
        return {
            "id": str(task.get("id") or ""),
            "taskmaster_id": str(task.get("taskmaster_id") or ""),
            "title": str(task.get("title") or ""),
            "status": str(task.get("status") or ""),
            "owner": str(task.get("owner") or ""),
            "layer": str(task.get("layer") or ""),
            "overlay_refs": list(task.get("overlay_refs") or []),
        }

    relevant_back = relevant_view_tasks(tasks_back)
    relevant_gameplay = relevant_view_tasks(tasks_gameplay)

    clusters: dict[str, dict[str, Any]] = {}

    def touch_cluster(overlay_path: str) -> dict[str, Any]:
        cluster = clusters.get(overlay_path)
        if cluster is None:
            cluster = {
                "overlay_path": overlay_path,
                "master_task_ids": [],
                "back_task_ids": [],
                "gameplay_task_ids": [],
                "titles": [],
            }
            clusters[overlay_path] = cluster
        return cluster

    for task in relevant_master:
        overlay = str(task.get("overlay") or "")
        if overlay.startswith(overlay_prefix):
            cluster = touch_cluster(overlay)
            cluster["master_task_ids"].append(str(task.get("id")))
            cluster["titles"].append(str(task.get("title") or ""))

    for bucket_name, collection in (("back_task_ids", relevant_back), ("gameplay_task_ids", relevant_gameplay)):
        for task in collection:
            overlay_refs = task.get("overlay_refs") or []
            if not isinstance(overlay_refs, list):
                continue
            for overlay_path in overlay_refs:
                overlay_value = str(overlay_path)
                if not overlay_value.startswith(overlay_prefix):
                    continue
                cluster = touch_cluster(overlay_value)
                cluster[bucket_name].append(str(task.get("taskmaster_id") or task.get("id") or ""))
                cluster["titles"].append(str(task.get("title") or ""))

    for cluster in clusters.values():
        cluster["master_task_ids"] = sorted(set(cluster["master_task_ids"]))
        cluster["back_task_ids"] = sorted(set(cluster["back_task_ids"]))
        cluster["gameplay_task_ids"] = sorted(set(cluster["gameplay_task_ids"]))
        cluster["titles"] = sorted({title for title in cluster["titles"] if title})

    return {
        "prd_id": prd_id,
        "master_tasks": [compact_master(task) for task in relevant_master],
        "tasks_back": [compact_view(task) for task in relevant_back],
        "tasks_gameplay": [compact_view(task) for task in relevant_gameplay],
        "overlay_clusters": [clusters[key] for key in sorted(clusters.keys())],
    }


def _render_front_matter(page: dict[str, Any], *, prd_id: str) -> str:
    adr_refs = list(page.get("adr_refs") or [])
    arch_refs = list(page.get("arch_refs") or [])
    test_refs = list(page.get("test_refs") or [])
    lines = [
        "---",
        f"PRD-ID: {prd_id}",
        f"Title: {str(page.get('title') or page.get('filename') or '').strip()}",
        "Status: Accepted",
        "ADR-Refs:",
    ]
    lines.extend([f"  - {item}" for item in adr_refs] or ["  - ADR-0004"])
    lines.append("Arch-Refs:")
    lines.extend([f"  - {item}" for item in arch_refs] or ["  - CH04"])
    lines.append("Test-Refs:")
    lines.extend([f"  - {item}" for item in test_refs] or ["  - scripts/python/validate_task_overlays.py"])
    lines.append("---")
    return "\n".join(lines)


def render_page_markdown(page: dict[str, Any], *, prd_id: str) -> str:
    front_matter = _render_front_matter(page, prd_id=prd_id)
    title = str(page.get("title") or page.get("filename") or "").strip()
    purpose = str(page.get("purpose") or "").strip()
    task_ids = [str(item) for item in page.get("task_ids") or [] if str(item).strip()]
    sections = list(page.get("sections") or [])

    body: list[str] = [front_matter, "", f"# {title}", ""]
    if purpose:
        body.extend([purpose, ""])
    if task_ids:
        body.extend(["Task coverage:", "", f"- {', '.join(task_ids)}", ""])

    if str(page.get("page_kind") or "") == "acceptance-checklist":
        section_map = {str(item.get("heading") or "").strip(): item for item in sections if isinstance(item, dict)}
        for heading in REQUIRED_CHECKLIST_HEADINGS:
            section = section_map.get(heading, {"bullets": [f"Review coverage for {heading}."]})
            body.append(f"## {heading}")
            body.append("")
            bullets = list(section.get("bullets") or [])
            if not bullets:
                bullets = [f"Review coverage for {heading}."]
            body.extend([f"- {bullet}" for bullet in bullets])
            body.append("")
        return "\n".join(body).strip() + "\n"

    for section in sections:
        if not isinstance(section, dict):
            continue
        heading = str(section.get("heading") or "").strip()
        bullets = [str(item).strip() for item in section.get("bullets") or [] if str(item).strip()]
        if not heading:
            continue
        body.append(f"## {heading}")
        body.append("")
        if bullets:
            body.extend([f"- {bullet}" for bullet in bullets])
        else:
            body.append("- Pending refinement.")
        body.append("")

    return "\n".join(body).strip() + "\n"


def compare_overlay_dirs(
    generated_dir: Path,
    existing_dir: Path,
    *,
    include_filenames: set[str] | None = None,
) -> dict[str, Any]:
    generated_files = sorted(path.name for path in generated_dir.glob("*.md")) if generated_dir.exists() else []
    existing_files = sorted(path.name for path in existing_dir.glob("*.md")) if existing_dir.exists() else []
    if include_filenames is not None:
        allowed = {str(item) for item in include_filenames}
        generated_files = [name for name in generated_files if name in allowed]
        existing_files = [name for name in existing_files if name in allowed]
    generated_set = set(generated_files)
    existing_set = set(existing_files)
    overlap = sorted(generated_set & existing_set)
    missing_in_generated = sorted(existing_set - generated_set)
    extra_in_generated = sorted(generated_set - existing_set)
    overlap_ratio = 0.0
    if existing_files:
        overlap_ratio = round(len(overlap) / len(existing_files), 4)
    return {
        "generated_count": len(generated_files),
        "existing_count": len(existing_files),
        "filename_overlap": len(overlap),
        "filename_overlap_ratio": overlap_ratio,
        "missing_in_generated": missing_in_generated,
        "extra_in_generated": extra_in_generated,
        "overlap_files": overlap,
    }
