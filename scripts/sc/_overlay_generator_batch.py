from __future__ import annotations

import datetime as dt
import re
from pathlib import Path
from typing import Any

from _overlay_generator_contract import parse_prd_docs_csv
from _overlay_generator_scaffold import select_pages_by_family
from _overlay_generator_support import build_default_overlay_profile, discover_existing_overlay_profile


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9._-]+", "-", str(value).strip().lower())
    slug = re.sub(r"-{2,}", "-", slug).strip("-")
    return slug or "batch"


def default_batch_suffix() -> str:
    return dt.datetime.now().strftime("batch-%H%M%S-%f")


def build_batch_run_name(prd_id: str, batch_suffix: str) -> str:
    prd_slug = str(prd_id).strip().lower().replace("/", "-").replace(" ", "-")
    return f"sc-llm-overlay-gen-batch-{prd_slug}--{_slugify(batch_suffix)}"


def build_page_run_suffix(batch_suffix: str, page_filename: str) -> str:
    page_slug = _slugify(page_filename).replace(".", "-")
    return f"{_slugify(batch_suffix)}--{page_slug}"


def resolve_target_pages(
    *,
    repo_root: Path,
    prd_id: str,
    page_family: str,
    pages_csv: str,
) -> list[str]:
    explicit_pages = parse_prd_docs_csv(pages_csv)
    if explicit_pages:
        return explicit_pages
    profile = discover_existing_overlay_profile(repo_root, prd_id)
    if not profile:
        profile = build_default_overlay_profile(prd_id)
    selected = select_pages_by_family(profile, page_family)
    return [str(page.get("filename") or "") for page in selected if str(page.get("filename") or "").strip()]


def classify_child_failure(
    *,
    rc: int,
    child_status: str,
    child_summary: dict[str, Any],
) -> dict[str, str]:
    if str(child_status or "") == "ok" and int(rc) == 0:
        return {"failure_type": "", "child_error": ""}

    child_error = str(child_summary.get("error") or "").strip()
    child_rc = int(child_summary.get("rc") or rc or 0)

    if child_rc == 124:
        failure_type = "timeout"
    elif child_error == "invalid_page_output":
        failure_type = "model_error"
    else:
        failure_type = "script_error"

    return {"failure_type": failure_type, "child_error": child_error}


def render_batch_report_markdown(summary: dict[str, Any]) -> str:
    lines = [
        f"# Overlay Batch Summary ({summary.get('prd_id', '')})",
        "",
        f"- Status: {summary.get('status', '')}",
        f"- Page count: {summary.get('page_count', 0)}",
        f"- Success count: {summary.get('success_count', 0)}",
        f"- Failure count: {summary.get('failure_count', 0)}",
        "",
        "| Page | Child Status | Failure Type | Diff Status | Similarity | Output |",
        "|---|---|---|---|---:|---|",
    ]
    for item in summary.get("results") or []:
        similarity = item.get("similarity_ratio")
        similarity_text = f"{float(similarity):.4f}" if similarity is not None else ""
        lines.append(
            "| {page} | {child_status} | {failure_type} | {diff_status} | {similarity} | {child_out_dir} |".format(
                page=str(item.get("page") or ""),
                child_status=str(item.get("child_status") or ""),
                failure_type=str(item.get("failure_type") or ""),
                diff_status=str(item.get("diff_status") or ""),
                similarity=similarity_text,
                child_out_dir=str(item.get("child_out_dir") or ""),
            )
        )
    return "\n".join(lines).strip() + "\n"
