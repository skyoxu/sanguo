#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

from typing import Any


def build_obligations_input_fingerprint(
    *,
    prompt_version: str,
    runtime_code_fingerprint: str,
    task_id: str,
    title: str,
    details: str,
    test_strategy: str,
    subtasks: list[dict[str, str]],
    acceptance_by_view: dict[str, list[Any]],
    security_profile: str,
) -> dict[str, Any]:
    return {
        "prompt_version": str(prompt_version or "").strip(),
        "runtime_code_fingerprint": str(runtime_code_fingerprint or "").strip(),
        "task_id": str(task_id or "").strip(),
        "title": str(title or "").strip(),
        "details": str(details or ""),
        "test_strategy": str(test_strategy or ""),
        "subtasks": list(subtasks or []),
        "acceptance_by_view": dict(acceptance_by_view or {}),
        "security_profile": str(security_profile or "").strip(),
    }
