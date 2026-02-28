#!/usr/bin/env python3
"""
Task requirement helpers for acceptance-check orchestration.
"""

from __future__ import annotations

import re
from typing import Any


REFS_RE = re.compile(r"\bRefs\s*:\s*(.+)$", flags=re.IGNORECASE)
ENV_EVIDENCE_TEST_TOKEN = "task1environmentevidencepersistencetests.cs"


def parse_task_id(value: str | None) -> str | None:
    if not value:
        return None
    s = str(value).strip()
    if not s:
        return None
    # Accept "10" or "10.3" and normalize to master task id ("10").
    return s.split(".", 1)[0]


def _split_refs_blob(blob: str) -> list[str]:
    s = str(blob or "").replace("`", " ").replace(",", " ").replace(";", " ")
    return [p.strip().replace("\\", "/") for p in s.split() if p.strip()]


def _iter_acceptance_refs(view: dict[str, Any]) -> list[str]:
    refs: list[str] = []
    acceptance = view.get("acceptance") or []
    if not isinstance(acceptance, list):
        return refs
    for raw in acceptance:
        text = str(raw or "").strip()
        m = REFS_RE.search(text)
        if not m:
            continue
        refs.extend(_split_refs_blob(m.group(1)))
    return refs


def _iter_test_refs(view: dict[str, Any]) -> list[str]:
    refs = view.get("test_refs") or []
    if not isinstance(refs, list):
        return []
    return [str(x).replace("\\", "/").strip() for x in refs if str(x).strip()]


def collect_task_refs(triplet: Any) -> list[str]:
    refs: list[str] = []
    for view in [getattr(triplet, "back", None), getattr(triplet, "gameplay", None)]:
        if not isinstance(view, dict):
            continue
        refs.extend(_iter_acceptance_refs(view))
        refs.extend(_iter_test_refs(view))
    # Deduplicate while preserving order.
    seen: set[str] = set()
    out: list[str] = []
    for ref in refs:
        key = ref.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(ref)
    return out


def task_requires_headless_e2e(triplet: Any) -> bool:
    refs = collect_task_refs(triplet)
    return any(ref.lower().endswith(".gd") for ref in refs)


def task_requires_env_evidence_preflight(triplet: Any) -> bool:
    refs = collect_task_refs(triplet)
    for ref in refs:
        if ENV_EVIDENCE_TEST_TOKEN in ref.lower():
            return True
    return False

