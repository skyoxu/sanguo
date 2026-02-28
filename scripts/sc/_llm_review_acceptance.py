#!/usr/bin/env python3
"""
Acceptance semantic context helpers for llm_review prompts.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from _taskmaster import TaskmasterTriplet
from _util import repo_root


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def truncate(text: str, *, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 3] + "..."


_EMOJI_RE = re.compile(
    "["
    "\U0001F300-\U0001FAFF"
    "\U00002700-\U000027BF"
    "\U00002600-\U000026FF"
    "\U0001F100-\U0001F1FF"
    "]",
    flags=re.UNICODE,
)


def strip_emoji(text: str) -> str:
    return _EMOJI_RE.sub("", str(text or ""))


REFS_RE = re.compile(r"\bRefs\s*:\s*(.+)$", flags=re.IGNORECASE)


def split_refs_blob(blob: str) -> list[str]:
    normalized = str(blob or "").replace("`", " ").replace(",", " ").replace(";", " ")
    out: list[str] = []
    for token in normalized.split():
        p = token.strip().replace("\\", "/")
        if not p:
            continue
        out.append(p)
    return out


def parse_refs_from_acceptance_line(line: str) -> list[str]:
    m = REFS_RE.search(str(line or "").strip())
    if not m:
        return []
    return split_refs_blob(m.group(1) or "")


def extract_anchor_context(*, lines: list[str], anchor: str, context_lines: int) -> list[tuple[int, list[str]]]:
    if not anchor:
        return []
    hits: list[int] = []
    for i, line in enumerate(lines):
        if anchor in line:
            hits.append(i)
    out: list[tuple[int, list[str]]] = []
    for idx0 in hits[:5]:
        start = max(0, idx0 - context_lines)
        end = min(len(lines), idx0 + context_lines + 1)
        excerpt = lines[start:end]
        out.append((start + 1, excerpt))
    return out


_CS_NEW_RE = re.compile(r"\bnew\s+([A-Za-z_][A-Za-z0-9_\.]*)\s*\(")
_CS_METHOD_CALL_RE = re.compile(r"\b([A-Za-z_][A-Za-z0-9_]*)\s*\.\s*([A-Za-z_][A-Za-z0-9_]*)\s*\(")
_CS_FACT_RE = re.compile(r"^\s*\[\s*(Fact|Theory)\s*(?:\(|\])", flags=re.IGNORECASE)
_CS_TEST_METHOD_RE = re.compile(r"^\s*public\s+.*\s+(Should[A-Za-z0-9_]+)\s*\(", flags=re.IGNORECASE)
_GD_TEST_FUNC_RE = re.compile(r"^\s*func\s+(test_[A-Za-z0-9_]+)\s*\(", flags=re.IGNORECASE)


def extract_cs_test_signals(text: str) -> dict[str, list[str]]:
    lines = text.splitlines()
    methods: list[str] = []
    for i, line in enumerate(lines):
        if _CS_FACT_RE.search(line):
            for j in range(i + 1, min(i + 6, len(lines))):
                m = _CS_TEST_METHOD_RE.search(lines[j])
                if m:
                    name = m.group(1)
                    if name not in methods:
                        methods.append(name)
                    break

    types: list[str] = []
    for m in _CS_NEW_RE.finditer(text):
        t = m.group(1).split(".")[-1]
        if t and t not in types:
            types.append(t)

    noisy_left = {
        "Assert",
        "FluentAssertions",
        "Substitute",
        "JsonSerializer",
        "Enumerable",
        "Task",
        "Path",
        "File",
        "Directory",
        "Guid",
        "DateTime",
        "DateTimeOffset",
        "Math",
        "GC",
        "Console",
    }
    noisy_right = {
        "Should",
        "Be",
        "NotBe",
        "BeNull",
        "NotBeNull",
        "BeTrue",
        "BeFalse",
        "Throw",
        "ThrowAsync",
        "Contain",
        "NotContain",
        "Match",
        "NotMatch",
        "GetAwaiter",
        "GetResult",
        "GetType",
        "ToString",
    }
    calls: list[str] = []
    for m in _CS_METHOD_CALL_RE.finditer(text):
        left = m.group(1)
        right = m.group(2)
        if left in noisy_left or right in noisy_right:
            continue
        sig = f"{left}.{right}"
        if sig not in calls:
            calls.append(sig)

    return {
        "test_methods": methods[:20],
        "new_types": types[:20],
        "calls": calls[:30],
    }


def extract_gd_test_signals(text: str) -> dict[str, list[str]]:
    funcs: list[str] = []
    for line in text.splitlines():
        m = _GD_TEST_FUNC_RE.search(line)
        if not m:
            continue
        name = m.group(1)
        if name not in funcs:
            funcs.append(name)
    return {"test_funcs": funcs[:30]}


def build_acceptance_semantic_context(
    triplet: TaskmasterTriplet, *, max_chars: int = 12_000, max_acceptance_items: int = 60, max_files: int = 12
) -> tuple[str, dict[str, Any]]:
    task_id = str(triplet.task_id)
    views: list[tuple[str, dict[str, Any] | None]] = [("back", triplet.back), ("gameplay", triplet.gameplay)]

    refs_to_anchors: dict[str, list[str]] = {}
    rendered_items: list[str] = []
    total_items = 0
    total_items_with_refs = 0

    for view_name, entry in views:
        if not isinstance(entry, dict):
            continue
        acceptance = entry.get("acceptance") or []
        if not isinstance(acceptance, list):
            continue

        rendered_items.append(f"### Acceptance items (view={view_name})")
        for idx, raw in enumerate(acceptance[:max_acceptance_items]):
            total_items += 1
            text = str(raw or "").strip()
            anchor = f"ACC:T{task_id}.{idx + 1}"
            refs = parse_refs_from_acceptance_line(text)
            if refs:
                total_items_with_refs += 1
                for r in refs:
                    refs_to_anchors.setdefault(r, [])
                    if anchor not in refs_to_anchors[r]:
                        refs_to_anchors[r].append(anchor)
            item_line = truncate(text, max_chars=800)
            suffix = f" (anchor: {anchor})"
            rendered_items.append(f"- {item_line}{suffix}")

    unique_refs = sorted(refs_to_anchors.keys())
    excerpts: list[str] = []
    missing_files: list[str] = []
    included_files = 0

    for rel in unique_refs[:max_files]:
        path = repo_root() / rel
        if not path.is_file():
            missing_files.append(rel)
            continue

        included_files += 1
        anchors = refs_to_anchors.get(rel, [])
        content = read_text(path)
        content_lines = content.splitlines()

        excerpts.append(f"### Referenced test: {rel}")
        if anchors:
            excerpts.append("Expected anchors: " + ", ".join(anchors[:20]))

        if rel.endswith(".cs"):
            sig = extract_cs_test_signals(content)
            if sig.get("test_methods"):
                excerpts.append("Test methods: " + ", ".join(sig["test_methods"]))
            if sig.get("new_types"):
                excerpts.append("Instantiated types: " + ", ".join(sig["new_types"]))
            if sig.get("calls"):
                excerpts.append("Notable calls: " + ", ".join(sig["calls"][:20]))
        elif rel.endswith(".gd"):
            sig = extract_gd_test_signals(content)
            if sig.get("test_funcs"):
                excerpts.append("Test funcs: " + ", ".join(sig["test_funcs"][:20]))

        anchor_excerpts: list[str] = []
        for a in anchors[:5]:
            blocks = extract_anchor_context(lines=content_lines, anchor=a, context_lines=20)
            for start_line, ex in blocks[:2]:
                anchor_excerpts.append(f"[anchor={a}] @L{start_line}")
                anchor_excerpts.extend(ex)
                anchor_excerpts.append("")

        head = "\n".join(content_lines[:80]).strip()
        head = truncate(head, max_chars=1_600)

        excerpts.append("```")
        if anchor_excerpts:
            excerpts.append("\n".join(anchor_excerpts).rstrip())
        else:
            excerpts.append(head or "(empty)")
        excerpts.append("```")

    meta = {
        "task_id": task_id,
        "acceptance_items_total": total_items,
        "acceptance_items_with_refs": total_items_with_refs,
        "unique_ref_files": len(unique_refs),
        "included_ref_files": included_files,
        "missing_ref_files": missing_files[:50],
        "max_acceptance_items": max_acceptance_items,
        "max_files": max_files,
    }

    blocks: list[str] = []
    blocks.append("## Acceptance Semantics (anchors + referenced tests)")
    blocks.append(
        "\n".join(
            [
                "Guidance:",
                "- Treat each acceptance item anchor as a coverage obligation.",
                "- Check that referenced tests contain behavior assertions (not only the anchor comment).",
                "- If tests look weak (e.g., static string matching), call it out and suggest stronger assertions.",
            ]
        )
    )
    if rendered_items:
        blocks.append("\n".join(rendered_items))
    if excerpts:
        blocks.append("\n".join(excerpts))
    if missing_files:
        blocks.append("Missing referenced test files (Refs points to non-existent paths):")
        blocks.append("\n".join([f"- {p}" for p in missing_files[:30]]))

    text = "\n\n".join([b for b in blocks if b.strip()]).strip() + "\n"
    return truncate(text, max_chars=max_chars), meta
