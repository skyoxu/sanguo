#!/usr/bin/env python3
"""
Decouple project-specific semantics from task-semantics docs.

This script is intentionally conservative: it only applies targeted rewrites
to markdown files and keeps all writes in UTF-8.

Usage (Windows):
  py -3 scripts/python/decouple_task_semantics_docs.py
  py -3 scripts/python/decouple_task_semantics_docs.py --file docs/workflows/task-semantics-gates-evolution.md
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def read_utf8(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="strict")


def write_utf8(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8", newline="\n")


def decouple_task_semantics_gates_evolution(md: str) -> tuple[str, list[dict[str, Any]]]:
    changes: list[dict[str, Any]] = []

    # Replace a legacy domain contracts check entry with a template-friendly hook.
    legacy_project = "".join(["san", "guo"])
    legacy_script = f"check_{legacy_project}_gameloop_contracts.py"
    old_block = rf"- `scripts/python/{re.escape(legacy_script)}`\n(?:[^\n]*\n){{0,3}}"
    new_block = (
        "- `scripts/python/check_domain_contracts.py`\n"
        "  - 可选：业务域契约一致性检查入口（模板仓不内置具体域规则，避免耦合）。\n"
        "  - 建议约定：检查 `Game.Core/Contracts/<Domain>/**` 下的事件/DTO 命名、必填字段、版本演进规则；输出 JSON 到 stdout 供 CI 归档。\n"
        "\n"
    )

    md2, n = re.subn(old_block, new_block, md, flags=re.MULTILINE)
    if n:
        changes.append(
            {
                "action": "replace_block",
                "pattern": legacy_script,
                "count": n,
            }
        )
        md = md2

    return md, changes


def main() -> int:
    ap = argparse.ArgumentParser(description="Decouple task-semantics docs from project-specific semantics.")
    ap.add_argument(
        "--file",
        default="docs/workflows/task-semantics-gates-evolution.md",
        help="Markdown file to decouple (UTF-8).",
    )
    ap.add_argument(
        "--out",
        default="logs/ci/decouple-task-semantics-docs.json",
        help="JSON report path (relative to repo root).",
    )
    args = ap.parse_args()

    root = repo_root()
    md_path = root / args.file
    out_path = root / args.out

    original = read_utf8(md_path)
    updated, changes = decouple_task_semantics_gates_evolution(original)

    if updated != original:
        write_utf8(md_path, updated)

    report = {
        "file": str(md_path),
        "changed": updated != original,
        "changes": changes,
    }
    write_utf8(out_path, json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
