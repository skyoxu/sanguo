from __future__ import annotations

import hashlib
import os
import re
from pathlib import Path
from typing import Any, Callable


REFS_RE = re.compile(r"\bRefs\s*:\s*(.+)$", flags=re.IGNORECASE)

AUTO_BEGIN = "<!-- BEGIN AUTO:TEST_ORG_NAMING_REFS -->"
AUTO_END = "<!-- END AUTO:TEST_ORG_NAMING_REFS -->"

ALLOWED_TEST_PREFIXES = ("Game.Core.Tests/", "Tests.Godot/tests/", "Tests/")


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="strict")
    except UnicodeDecodeError:
        return path.read_text(encoding="utf-8", errors="replace")


def truncate(text: str, *, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 3] + "..."


def extract_testing_framework_excerpt(
    *,
    repo_root_fn: Callable[[], Path],
    read_text_fn: Callable[[Path], str],
) -> str:
    path = repo_root_fn() / "docs" / "testing-framework.md"
    if not path.exists():
        return ""
    text = read_text_fn(path)
    start = text.find(AUTO_BEGIN)
    end = text.find(AUTO_END)
    if start < 0 or end < 0 or end <= start:
        return ""
    return text[start + len(AUTO_BEGIN) : end].strip()


def split_refs_blob(blob: str) -> list[str]:
    text = str(blob or "").strip()
    text = text.replace("`", "")
    text = text.replace(",", " ")
    text = text.replace(";", " ")
    return [part.strip().replace("\\", "/") for part in text.split() if part.strip()]


def extract_acceptance_refs(acceptance: Any) -> dict[str, list[str]]:
    by_ref: dict[str, list[str]] = {}
    if not isinstance(acceptance, list):
        return by_ref
    for raw in acceptance:
        text = str(raw or "").strip()
        match = REFS_RE.search(text)
        if not match:
            continue
        for ref in split_refs_blob(match.group(1)):
            if not ref:
                continue
            by_ref.setdefault(ref, []).append(text)
    return by_ref


def extract_acceptance_refs_with_anchors(*, acceptance: Any, task_id: str) -> dict[str, list[dict[str, str]]]:
    by_ref: dict[str, list[dict[str, str]]] = {}
    if not isinstance(acceptance, list):
        return by_ref
    for index, raw in enumerate(acceptance, start=1):
        text = str(raw or "").strip()
        match = REFS_RE.search(text)
        if not match:
            continue
        anchor = f"ACC:T{task_id}.{index}"
        for ref in split_refs_blob(match.group(1)):
            normalized = str(ref or "").strip().replace("\\", "/")
            if not normalized:
                continue
            by_ref.setdefault(normalized, []).append({"anchor": anchor, "text": text})
    return by_ref


def artifact_token_for_ref(ref: str) -> str:
    normalized = str(ref or "").strip().replace("\\", "/")
    base = Path(normalized).name or "ref"
    safe_base = re.sub(r"[^A-Za-z0-9._-]+", "_", base)
    digest = hashlib.sha1(normalized.encode("utf-8")).hexdigest()[:10]
    return f"{safe_base}-{digest}"


def validate_anchor_binding(*, ref: str, content: str, required_anchors: list[str]) -> tuple[bool, str | None]:
    anchors = [anchor for anchor in required_anchors if str(anchor or "").strip()]
    if not anchors:
        return True, None

    lines = content.replace("\r\n", "\n").split("\n")
    if ref.lower().endswith(".gd"):
        marker = re.compile(r"^\s*func\s+test_[A-Za-z0-9_]*\s*\(")
    else:
        marker = re.compile(r"^\s*\[(?:Fact|Theory)(?:\s*\(.*\))?\]\s*$")

    missing: list[str] = []
    unbound: list[str] = []
    max_window = 5
    for anchor in anchors:
        positions = [idx for idx, line in enumerate(lines) if anchor in line]
        if not positions:
            missing.append(anchor)
            continue
        bound = False
        for pos in positions:
            start = pos + 1
            end = min(len(lines), pos + 1 + max_window)
            if any(marker.search(lines[i]) for i in range(start, end)):
                bound = True
                break
        if not bound:
            unbound.append(anchor)

    if not missing and not unbound:
        return True, None

    parts: list[str] = []
    if missing:
        parts.append("missing anchors: " + ", ".join(missing))
    if unbound:
        parts.append("anchors not bound near test marker: " + ", ".join(unbound))
    return False, "; ".join(parts)


def load_optional_prd_excerpt(
    *,
    include_prd_context: bool,
    prd_context_path: str,
    repo_root_fn: Callable[[], Path],
    read_text_fn: Callable[[Path], str],
    truncate_fn: Callable[[str], str],
) -> str:
    if not include_prd_context:
        return ""
    path = Path(prd_context_path)
    if not path.is_absolute():
        path = repo_root_fn() / path
    if not path.exists():
        return ""
    return truncate_fn(read_text_fn(path))


def is_allowed_test_path(path_text: str) -> bool:
    normalized = str(path_text or "").strip().replace("\\", "/")
    if not normalized:
        return False
    if os.path.isabs(normalized) or (len(normalized) >= 2 and normalized[1] == ":"):
        return False
    if not (normalized.endswith(".cs") or normalized.endswith(".gd")):
        return False
    return normalized.startswith(ALLOWED_TEST_PREFIXES)
