#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Converge repo entry docs away from stale Electron-era references.

Scope:
  - AGENTS.md
  - CLAUDE.md
  - docs/architecture/acceptance/02-security.feature

This script is intentionally small and explicit (no fuzzy heuristics) to avoid
accidental rewrites of unrelated wording.

Logs:
  logs/ci/<YYYY-MM-DD>/entry-docs-converge.json
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import List, Tuple


PROJECT_ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class Change:
    file: str
    kind: str
    before: str
    after: str


def replace_all(text: str, replacements: List[Tuple[str, str]], changes: List[Change], rel: str) -> str:
    for before, after in replacements:
        if before not in text:
            continue
        text = text.replace(before, after)
        changes.append(Change(file=rel, kind="replace", before=before, after=after))
    return text


def write_audit(changes: List[Change]) -> Path:
    out_dir = PROJECT_ROOT / "logs" / "ci" / date.today().isoformat()
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "entry-docs-converge.json"
    payload = {
        "generated": datetime.now().isoformat(),
        "changes": [c.__dict__ for c in changes],
    }
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return out_path


def main() -> int:
    changes: List[Change] = []

    # 1) AGENTS.md / CLAUDE.md: update base file list and the "security baseline" ADR pointer.
    entry_files = [PROJECT_ROOT / "AGENTS.md", PROJECT_ROOT / "CLAUDE.md"]
    entry_replacements = [
        ("02-security-baseline-electron-v2.md", "02-security-baseline-godot-v2.md"),
        ("**ADR-0002-electron-security**：安全基线", "**ADR-0019-godot-security-baseline**：安全基线（Godot）"),
        ("ADR‑0002/0004/0005/0003", "ADR‑0019/0004/0005/0003"),
        ("ADR-0002/0004/0005/0003", "ADR-0019/0004/0005/0003"),
    ]
    for path in entry_files:
        rel = str(path.relative_to(PROJECT_ROOT)).replace("\\", "/")
        text = path.read_text(encoding="utf-8")
        new_text = replace_all(text, entry_replacements, changes, rel)
        if new_text != text:
            path.write_text(new_text, encoding="utf-8", newline="\n")

    # 2) Acceptance feature: rewrite to Godot security baseline wording (no Electron/Node/CSP).
    feature_path = PROJECT_ROOT / "docs" / "architecture" / "acceptance" / "02-security.feature"
    rel_feature = str(feature_path.relative_to(PROJECT_ROOT)).replace("\\", "/")
    feature_new = (
        "Feature: 02 Godot 安全基线\n"
        "  Scenario: 基线护栏启用\n"
        "    Given 应用以安全配置启动（GD_SECURE_MODE=1）\n"
        "    Then 仅允许 res:// 读取与 user:// 写入\n"
        "    And 外链仅允许 https 且主机必须在 ALLOWED_EXTERNAL_HOSTS 白名单中\n"
    )
    feature_old = feature_path.read_text(encoding="utf-8")
    if feature_old != feature_new:
        feature_path.write_text(feature_new, encoding="utf-8", newline="\n")
        changes.append(
            Change(
                file=rel_feature,
                kind="rewrite",
                before="(file content)",
                after="Godot security baseline scenario",
            )
        )

    audit = write_audit(changes)
    print(f"[entry-docs] changes={len(changes)} audit={audit}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

