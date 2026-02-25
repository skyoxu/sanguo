#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import re
from typing import Any


def _truncate(text: str, *, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 3] + "..."


def _normalize_acceptance_text(raw: Any) -> str:
    return re.sub(r"\s+", " ", str(raw or "")).strip()


def _collect_acceptance_catalog(acceptance_by_view: dict[str, list[Any]]) -> tuple[dict[str, dict[str, Any]], list[str], dict[str, int], int]:
    catalog: dict[str, dict[str, Any]] = {}
    order: list[str] = []
    per_view_raw: dict[str, int] = {}
    raw_total = 0

    for view_name, values in acceptance_by_view.items():
        view = str(view_name or "").strip()
        count = 0
        for idx, raw in enumerate(values, start=1):
            text = _normalize_acceptance_text(raw)
            if not text:
                continue
            count += 1
            raw_total += 1
            key = text.casefold()
            if key not in catalog:
                catalog[key] = {"text": text, "sources": []}
                order.append(key)
            catalog[key]["sources"].append((view, int(idx)))
        per_view_raw[view] = count

    return catalog, order, per_view_raw, raw_total


def build_acceptance_prompt_blocks(acceptance_by_view: dict[str, list[Any]]) -> list[str]:
    """
    Build deduplicated acceptance blocks with source index mapping.

    Output format:
    - A1: <text>
      sources: back:1, gameplay:2
    """

    catalog, order, _, _ = _collect_acceptance_catalog(acceptance_by_view)

    lines: list[str] = [f"[acceptance] deduplicated items ({len(order)}):"]
    for i, key in enumerate(order, start=1):
        item = catalog[key]
        text = _truncate(str(item["text"]), max_chars=520)
        refs = ", ".join([f"{v}:{n}" for v, n in item["sources"]])
        lines.append(f"- A{i}: {text}")
        lines.append(f"  sources: {refs}")

    return lines


def compute_acceptance_dedup_stats(acceptance_by_view: dict[str, list[Any]]) -> dict[str, Any]:
    _, order, per_view_raw, raw_total = _collect_acceptance_catalog(acceptance_by_view)
    return {
        "raw_total": int(raw_total),
        "dedup_total": int(len(order)),
        "per_view_raw": {k: int(v) for k, v in sorted(per_view_raw.items())},
    }
