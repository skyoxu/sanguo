#!/usr/bin/env python3
"""
Shared StepResult data model for sc scripts.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class StepResult:
    name: str
    status: str  # ok|fail|skipped
    rc: int | None = None
    cmd: list[str] | None = None
    log: str | None = None
    details: dict[str, Any] | None = None

