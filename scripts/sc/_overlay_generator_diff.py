from __future__ import annotations

import difflib
from pathlib import Path
from typing import Any


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def _build_diff_excerpt(filename: str, existing_text: str, generated_text: str, *, max_lines: int = 20) -> str:
    diff_lines = list(
        difflib.unified_diff(
            existing_text.splitlines(),
            generated_text.splitlines(),
            fromfile=f"existing/{filename}",
            tofile=f"generated/{filename}",
            lineterm="",
        )
    )
    if not diff_lines:
        return ""
    limited = diff_lines[:max_lines]
    if len(diff_lines) > max_lines:
        limited.append("... diff truncated ...")
    return "\n".join(limited)


def build_diff_summary(
    generated_dir: Path,
    existing_dir: Path,
    *,
    include_filenames: set[str] | None = None,
) -> dict[str, Any]:
    generated_files = {path.name: path for path in generated_dir.glob("*.md")} if generated_dir.exists() else {}
    existing_files = {path.name: path for path in existing_dir.glob("*.md")} if existing_dir.exists() else {}
    if include_filenames is not None:
        names = set(str(item) for item in include_filenames)
        generated_files = {name: path for name, path in generated_files.items() if name in names}
        existing_files = {name: path for name, path in existing_files.items() if name in names}
    all_names = sorted(set(generated_files.keys()) | set(existing_files.keys()))

    files: list[dict[str, Any]] = []
    unchanged_count = 0
    modified_count = 0
    added_count = 0
    removed_count = 0

    for name in all_names:
        generated_path = generated_files.get(name)
        existing_path = existing_files.get(name)

        if generated_path and not existing_path:
            generated_text = _read_text(generated_path)
            files.append(
                {
                    "filename": name,
                    "status": "added",
                    "similarity_ratio": 0.0,
                    "generated_chars": len(generated_text),
                    "existing_chars": 0,
                    "diff_excerpt": generated_text[:400],
                }
            )
            added_count += 1
            continue

        if existing_path and not generated_path:
            existing_text = _read_text(existing_path)
            files.append(
                {
                    "filename": name,
                    "status": "removed",
                    "similarity_ratio": 0.0,
                    "generated_chars": 0,
                    "existing_chars": len(existing_text),
                    "diff_excerpt": existing_text[:400],
                }
            )
            removed_count += 1
            continue

        assert generated_path is not None and existing_path is not None
        generated_text = _read_text(generated_path)
        existing_text = _read_text(existing_path)
        ratio = round(difflib.SequenceMatcher(None, existing_text, generated_text).ratio(), 4)
        if existing_text == generated_text:
            status = "unchanged"
            unchanged_count += 1
            diff_excerpt = ""
        else:
            status = "modified"
            modified_count += 1
            diff_excerpt = _build_diff_excerpt(name, existing_text, generated_text)

        files.append(
            {
                "filename": name,
                "status": status,
                "similarity_ratio": ratio,
                "generated_chars": len(generated_text),
                "existing_chars": len(existing_text),
                "diff_excerpt": diff_excerpt,
            }
        )

    return {
        "generated_count": len(generated_files),
        "existing_count": len(existing_files),
        "unchanged_count": unchanged_count,
        "modified_count": modified_count,
        "added_count": added_count,
        "removed_count": removed_count,
        "files": files,
    }


def render_diff_summary_markdown(summary: dict[str, Any], *, max_diff_blocks: int = 5) -> str:
    lines = [
        "# Overlay Diff Summary",
        "",
        f"- generated_count: {int(summary.get('generated_count') or 0)}",
        f"- existing_count: {int(summary.get('existing_count') or 0)}",
        f"- unchanged_count: {int(summary.get('unchanged_count') or 0)}",
        f"- modified_count: {int(summary.get('modified_count') or 0)}",
        f"- added_count: {int(summary.get('added_count') or 0)}",
        f"- removed_count: {int(summary.get('removed_count') or 0)}",
        "",
        "| File | Status | Similarity | Generated Chars | Existing Chars |",
        "| --- | --- | ---: | ---: | ---: |",
    ]

    for item in summary.get("files") or []:
        if not isinstance(item, dict):
            continue
        lines.append(
            f"| {item.get('filename', '')} | {item.get('status', '')} | "
            f"{item.get('similarity_ratio', 0.0)} | {item.get('generated_chars', 0)} | {item.get('existing_chars', 0)} |"
        )

    rendered_blocks = 0
    for item in summary.get("files") or []:
        if not isinstance(item, dict):
            continue
        if str(item.get("status") or "") != "modified":
            continue
        excerpt = str(item.get("diff_excerpt") or "").strip()
        if not excerpt:
            continue
        lines.extend(
            [
                "",
                f"## Diff Excerpt: {item.get('filename', '')}",
                "",
                "```diff",
                excerpt,
                "```",
            ]
        )
        rendered_blocks += 1
        if rendered_blocks >= max_diff_blocks:
            break

    return "\n".join(lines).strip() + "\n"
