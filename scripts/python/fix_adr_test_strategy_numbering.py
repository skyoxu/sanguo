#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Resolve ADR numbering conflict introduced by syncing docs from a sibling repo.

In this repo:
  - ADR-0024 is reserved for "sanguo template lineage" (sanguo-specific).
  - Godot test strategy lives in ADR-0025.

Some synced docs assume "ADR-0024 = test strategy" and also introduced a stray file:
  docs/adr/ADR-0024-godot-test-strategy.md

This script:
1) Migrates the test strategy ADR content to ADR-0025 (overwrites the existing file with the richer version).
2) Deletes docs/adr/ADR-0024-godot-test-strategy.md (to keep ADR ids unique).
3) Rewrites documentation references from ADR-0024 -> ADR-0025 where ADR-0024 was intended as test strategy.

Safety:
- Does NOT touch overlays (docs/architecture/overlays/**) because they legitimately reference ADR-0024 (lineage).
- Does NOT touch docs/adr/ADR-0024-sanguo-template-lineage.md
- Does NOT touch docs/migration/Phase-23-Sanguo-Template-Notes.md (lineage references)

Logs:
  logs/ci/<YYYY-MM-DD>/adr-test-strategy-numbering-fix.json
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Dict, List


PROJECT_ROOT = Path(__file__).resolve().parents[2]

ADR_SRC = PROJECT_ROOT / "docs" / "adr" / "ADR-0024-godot-test-strategy.md"
ADR_DST = PROJECT_ROOT / "docs" / "adr" / "ADR-0025-godot-test-strategy.md"

LINEAGE_ADR = PROJECT_ROOT / "docs" / "adr" / "ADR-0024-sanguo-template-lineage.md"

EXCLUDE_FILES = {
    LINEAGE_ADR,
    PROJECT_ROOT / "docs" / "migration" / "Phase-23-Sanguo-Template-Notes.md",
}

EXCLUDE_DIRS = {
    PROJECT_ROOT / "docs" / "architecture" / "overlays",
}

TARGET_DIRS = [
    PROJECT_ROOT / "docs" / "architecture" / "base",
    PROJECT_ROOT / "docs" / "adr",
    PROJECT_ROOT / "docs" / "migration",
    PROJECT_ROOT / "docs" / "workflows",
]

ALLOWED_EXTS = {".md", ".txt", ".index", ".adoc", ".yml", ".yaml", ".json"}


@dataclass(frozen=True)
class FileChange:
    file: str
    action: str
    replacements: Dict[str, int]


def is_under_excluded_dir(path: Path) -> bool:
    for d in EXCLUDE_DIRS:
        try:
            path.relative_to(d)
            return True
        except ValueError:
            continue
    return False


def rewrite_adr_file() -> List[FileChange]:
    changes: List[FileChange] = []

    if ADR_SRC.exists():
        src_text = ADR_SRC.read_text(encoding="utf-8")
        migrated = src_text.replace("# ADR-0024:", "# ADR-0025:", 1)
        ADR_DST.write_text(migrated, encoding="utf-8", newline="\n")
        changes.append(
            FileChange(
                file=str(ADR_DST.relative_to(PROJECT_ROOT)).replace("\\", "/"),
                action="overwrite_from_0024",
                replacements={"header_id": 1},
            )
        )
        ADR_SRC.unlink()
        changes.append(
            FileChange(
                file=str(ADR_SRC.relative_to(PROJECT_ROOT)).replace("\\", "/"),
                action="delete_conflicting_file",
                replacements={},
            )
        )
    return changes


def iter_target_files() -> List[Path]:
    out: List[Path] = []
    for root in TARGET_DIRS:
        if not root.exists():
            continue
        for p in root.rglob("*"):
            if not p.is_file():
                continue
            if p.suffix.lower() not in ALLOWED_EXTS:
                continue
            if is_under_excluded_dir(p):
                continue
            if p in EXCLUDE_FILES:
                continue
            out.append(p)
    out.sort(key=lambda p: p.as_posix())
    return out


def apply_rewrites(text: str) -> tuple[str, Dict[str, int]]:
    repl: Dict[str, int] = {}

    before = text
    text2 = text.replace("docs/adr/ADR-0024-godot-test-strategy.md", "docs/adr/ADR-0025-godot-test-strategy.md")
    if text2 != text:
        repl["path_0024_to_0025"] = before.count("docs/adr/ADR-0024-godot-test-strategy.md")
        text = text2

    before = text
    text2 = text.replace("ADR-0024", "ADR-0025")
    if text2 != text:
        repl["adr_0024_to_0025"] = before.count("ADR-0024")
        text = text2

    return text, repl


def rewrite_references() -> List[FileChange]:
    changes: List[FileChange] = []
    for p in iter_target_files():
        rel = str(p.relative_to(PROJECT_ROOT)).replace("\\", "/")
        original = p.read_text(encoding="utf-8")
        updated, repl = apply_rewrites(original)
        if updated == original:
            continue
        p.write_text(updated, encoding="utf-8", newline="\n")
        changes.append(FileChange(file=rel, action="rewrite_refs", replacements=repl))
    return changes


def write_audit(changes: List[FileChange]) -> Path:
    out_dir = PROJECT_ROOT / "logs" / "ci" / date.today().isoformat()
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "adr-test-strategy-numbering-fix.json"
    payload = {"generated": datetime.now().isoformat(), "changes": [c.__dict__ for c in changes]}
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return out_path


def main() -> int:
    changes: List[FileChange] = []
    changes.extend(rewrite_adr_file())
    changes.extend(rewrite_references())
    audit = write_audit(changes)
    print(f"[adr-fix] changed_files={len(changes)} audit={audit}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

