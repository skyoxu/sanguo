#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from _acceptance_refs_helpers import ALLOWED_TEST_PREFIXES, ItemKey, read_text, truncate


AUTO_BEGIN = "<!-- BEGIN AUTO:TEST_ORG_NAMING_REFS -->"
AUTO_END = "<!-- END AUTO:TEST_ORG_NAMING_REFS -->"


def _extract_testing_framework_excerpt(*, root: Path) -> str:
    path = root / "docs" / "testing-framework.md"
    if not path.exists():
        return ""
    text = read_text(path)
    start = text.find(AUTO_BEGIN)
    end = text.find(AUTO_END)
    if start < 0 or end < 0 or end <= start:
        return ""
    return text[start + len(AUTO_BEGIN) : end].strip()


def build_prompt(
    *,
    root: Path,
    prd_excerpt: str,
    task_id: int,
    master: dict[str, Any] | None,
    back: dict[str, Any] | None,
    gameplay: dict[str, Any] | None,
    missing_items: dict[ItemKey, str],
    existing_candidates: list[str],
    max_refs_per_item: int,
) -> str:
    title = str((master or {}).get("title") or "").strip()
    master_details = truncate(str((master or {}).get("details") or ""), max_chars=2_000)
    input_items = [{"view": k.view, "index": k.index, "text": text} for k, text in sorted(missing_items.items(), key=lambda kv: (kv[0].view, kv[0].index))]
    constraints = [
        "Output MUST be a single JSON object (no markdown fences).",
        "Each input item MUST map to 1..N paths (array of strings).",
        f"Max paths per item: {max_refs_per_item}.",
        f"Paths MUST be repo-relative .cs/.gd under: {', '.join(ALLOWED_TEST_PREFIXES)}.",
        "Prefer existing candidate test files when they fit.",
        "Do NOT use placeholder-like names with Task<id>Acceptance/Requirements.",
        "Use .cs for core/domain/service logic; use .gd for scene/UI/headless/signal behavior.",
    ]
    testing_excerpt = truncate(_extract_testing_framework_excerpt(root=root), max_chars=6_000)
    return "\n\n".join(
        [
            "Role: acceptance-refs-planner",
            "You will propose test file refs for acceptance items.",
            "Constraints:\n- " + "\n- ".join(constraints),
            "Repository testing conventions excerpt (docs/testing-framework.md):\n" + (testing_excerpt or "(missing)"),
            "PRD (truncated excerpt):\n" + (prd_excerpt or "(empty)"),
            f"Task Context:\n- task_id: {task_id}\n- title: {title or '(empty)'}\n- master.details: {master_details or '(empty)'}",
            f"Triplet hints:\n- back.layer: {str((back or {}).get('layer') or '')}\n- gameplay.layer: {str((gameplay or {}).get('layer') or '')}",
            "Existing candidates:\n" + ("\n".join([f"- {p}" for p in existing_candidates]) if existing_candidates else "(none)"),
            "Input acceptance items needing Refs:\n" + json.dumps(input_items, ensure_ascii=False, indent=2),
            "Return JSON schema:\n" + json.dumps({"task_id": task_id, "items": [{"view": "back", "index": 0, "paths": ["Game.Core.Tests/Domain/ExampleTests.cs"]}]}, ensure_ascii=False, indent=2),
        ]
    ).strip() + "\n"

