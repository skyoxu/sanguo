from __future__ import annotations

import datetime as dt
import re
import shutil
from pathlib import Path

from _overlay_generator_model import parse_existing_page_markdown
from _overlay_generator_scaffold import build_scaffold_base_page
from _overlay_generator_support import parse_prd_docs_csv


def copy_generated_to_target(generated_dir: Path, target_dir: Path) -> None:
    target_dir.mkdir(parents=True, exist_ok=True)
    for path in generated_dir.glob("*.md"):
        shutil.copyfile(path, target_dir / path.name)


def reset_dir(path: Path) -> None:
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)


def artifact_name(filename: str) -> str:
    return filename.replace("\\", "_").replace("/", "_").replace(":", "_")


def select_pages(profile: list[dict[str, object]], page_filter_csv: str) -> list[dict[str, object]]:
    selected_names = set(parse_prd_docs_csv(page_filter_csv))
    if not selected_names:
        return list(profile)
    return [page for page in profile if str(page.get("filename") or "") in selected_names]


def slugify_run_suffix(value: str) -> str:
    slug = re.sub(r"[^a-z0-9._-]+", "-", str(value).strip().lower())
    slug = re.sub(r"-{2,}", "-", slug).strip("-")
    return slug or "run"


def default_run_suffix() -> str:
    return dt.datetime.now().strftime("run-%H%M%S-%f")


def build_output_dir_name(prd_id: str, run_suffix: str, *, default_suffix: str | None = None) -> str:
    prd_slug = str(prd_id).strip().lower().replace("/", "-").replace(" ", "-")
    suffix = slugify_run_suffix(run_suffix) if str(run_suffix).strip() else (default_suffix or default_run_suffix())
    return f"sc-llm-overlay-gen-{prd_slug}--{suffix}"


def build_page_context(task_digest: dict[str, object], page: dict[str, object]) -> dict[str, object]:
    target_path = str(page.get("path") or "")
    target_filename = str(page.get("filename") or "")
    overlay_clusters = list(task_digest.get("overlay_clusters") or [])
    for cluster in overlay_clusters:
        if not isinstance(cluster, dict):
            continue
        overlay_path = str(cluster.get("overlay_path") or "")
        if overlay_path == target_path or overlay_path.endswith("/" + target_filename):
            return cluster
    return {
        "overlay_path": target_path,
        "master_task_ids": [],
        "back_task_ids": [],
        "gameplay_task_ids": [],
        "titles": [],
    }


def prepare_page_runtime_state(
    *,
    selected_pages: list[dict[str, object]],
    current_dir: Path,
    task_digest: dict[str, object],
) -> dict[str, dict[str, object]]:
    state: dict[str, dict[str, object]] = {}
    for page in selected_pages:
        filename = str(page.get("filename") or "")
        current_page_path = current_dir / filename
        current_page_text = current_page_path.read_text(encoding="utf-8") if current_page_path.exists() else ""
        page_context = build_page_context(task_digest, page)
        current_page_model = (
            parse_existing_page_markdown(
                filename=filename,
                page_kind=str(page.get("page_kind") or ""),
                markdown_text=current_page_text,
            )
            if current_page_text.strip()
            else None
        )
        scaffold_base_page = build_scaffold_base_page(page, page_context, current_page=current_page_model)
        state[filename] = {
            "current_page_path": current_page_path,
            "current_page_text": current_page_text,
            "page_context": page_context,
            "current_page_model": current_page_model,
            "scaffold_base_page": scaffold_base_page,
        }
    return state
