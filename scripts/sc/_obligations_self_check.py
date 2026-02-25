#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

from typing import Any, Callable


def run_self_check(
    *,
    build_source_text_blocks: Callable[..., list[str]],
    build_obligation_prompt: Callable[..., str],
) -> tuple[bool, dict[str, Any]]:
    """Run deterministic local checks for obligations extractor wiring."""

    issues: list[str] = []

    # 1) Deterministic source blocks must start with master.title.
    title = "Sample Task Title"
    blocks = build_source_text_blocks(
        title=title,
        details="Sample details",
        test_strategy="Sample test strategy",
        subtasks=[{"id": "1", "title": "S1", "details": "D1", "testStrategy": "TS1"}],
    )
    if not blocks:
        issues.append("SC_SOURCE_BLOCKS_EMPTY")
    elif blocks[0] != title:
        issues.append("SC_SOURCE_BLOCKS_FIRST_NOT_TITLE")

    # 2) Empty title must fail fast to prevent silent regression.
    try:
        build_source_text_blocks(title="", details="d", test_strategy="t", subtasks=[])
        issues.append("SC_EMPTY_TITLE_NOT_REJECTED")
    except ValueError:
        pass

    # 3) Prompt contract must explicitly include title in source-text rule and body.
    prompt = build_obligation_prompt(
        task_id="0",
        title=title,
        master_details="d",
        master_test_strategy="t",
        subtasks=[],
        acceptance_by_view={"back": ["A1"]},
        security_profile="host-safe",
        security_profile_context="- profile: host-safe",
    )
    if "master.title/details/testStrategy" not in prompt:
        issues.append("SC_PROMPT_RULE_MISSING_MASTER_TITLE")
    if "Master title:" not in prompt:
        issues.append("SC_PROMPT_BODY_MISSING_MASTER_TITLE")

    ok = not issues
    payload = {
        "cmd": "sc-llm-extract-task-obligations --self-check",
        "status": "ok" if ok else "fail",
        "issues": issues,
        "checks": {
            "source_blocks_first_is_title": bool(blocks and blocks[0] == title),
            "empty_title_rejected": "SC_EMPTY_TITLE_NOT_REJECTED" not in issues,
            "prompt_rule_contains_master_title": "SC_PROMPT_RULE_MISSING_MASTER_TITLE" not in issues,
            "prompt_body_contains_master_title": "SC_PROMPT_BODY_MISSING_MASTER_TITLE" not in issues,
        },
    }
    return ok, payload

