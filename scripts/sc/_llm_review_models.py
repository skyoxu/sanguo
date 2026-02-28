#!/usr/bin/env python3
"""
Types for llm_review orchestration.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ReviewResult:
    agent: str
    status: str  # ok|fail|skipped
    rc: int | None = None
    cmd: list[str] | None = None
    output: str | None = None
    prompt_path: str | None = None
    output_path: str | None = None
    details: dict[str, Any] | None = None
