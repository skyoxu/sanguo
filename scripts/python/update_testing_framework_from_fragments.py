#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Update docs/testing-framework.md from repository fragments (UTF-8).

Why:
  - Keep docs/testing-framework.md aligned with real repo structure and gates.
  - Avoid manual edits drifting out of sync.

This script is deterministic and does NOT use any LLM.

Usage (Windows):
  py -3 scripts/python/update_testing_framework_from_fragments.py
"""

from __future__ import annotations

import re
from pathlib import Path


BEGIN = "<!-- BEGIN AUTO:TEST_ORG_NAMING_REFS -->"
END = "<!-- END AUTO:TEST_ORG_NAMING_REFS -->"
FRAGMENT = "docs/testing-framework.auto.test-org-naming-refs.zh.md"
TARGET = "docs/testing-framework.md"


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def write_text(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8", newline="\n")


def replace_block(*, text: str, begin: str, end: str, replacement: str) -> str:
    pattern = re.compile(
        re.escape(begin) + r".*?" + re.escape(end),
        flags=re.DOTALL,
    )
    m = pattern.search(text)
    if not m:
        raise ValueError(f"Markers not found: {begin} ... {end}")
    return pattern.sub(begin + "\n" + replacement.rstrip() + "\n" + end, text, count=1)


def main() -> int:
    root = repo_root()
    target_path = root / TARGET
    fragment_path = root / FRAGMENT

    if not target_path.exists():
        raise FileNotFoundError(f"Missing target: {TARGET}")
    if not fragment_path.exists():
        raise FileNotFoundError(f"Missing fragment: {FRAGMENT}")

    target = read_text(target_path)
    fragment = read_text(fragment_path)

    updated = replace_block(text=target, begin=BEGIN, end=END, replacement=fragment)
    if updated != target:
        write_text(target_path, updated)
        print(f"[OK] Updated {TARGET} from {FRAGMENT}")
    else:
        print(f"[OK] No changes needed in {TARGET}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

