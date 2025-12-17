#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sanitize legacy stack proper names in repo-root note files (outside docs/).

Rationale:
- Some historical note files live at repo root (e.g., changetogodot.txt).
- docs-only scans won't catch them, but humans/LLMs will still read them.

This script applies the same replacement mapping as docs sanitization:
  Electron -> LegacyDesktopShell
  React -> LegacyUIFramework
  Vite -> LegacyBuildTool
  Phaser -> Legacy2DEngine
  Playwright -> LegacyE2ERunner
  Vitest -> LegacyUnitTestRunner
  vitegame -> LegacyProject
  npm -> NodePkg

Usage:
  py -3 scripts/python/sanitize_root_legacy_terms.py --files changetogodot.txt
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Dict, List, Tuple


PROJECT_ROOT = Path(__file__).resolve().parents[2]

REPLACEMENTS: List[Tuple[str, re.Pattern, str]] = [
    ("vitegame", re.compile(r"vitegame", re.IGNORECASE), "LegacyProject"),
    ("electron", re.compile(r"electron", re.IGNORECASE), "LegacyDesktopShell"),
    ("phaser", re.compile(r"phaser", re.IGNORECASE), "Legacy2DEngine"),
    ("vite", re.compile(r"\bvite\b", re.IGNORECASE), "LegacyBuildTool"),
    ("react", re.compile(r"\breact\b", re.IGNORECASE), "LegacyUIFramework"),
    ("playwright", re.compile(r"playwright", re.IGNORECASE), "LegacyE2ERunner"),
    ("vitest", re.compile(r"vitest", re.IGNORECASE), "LegacyUnitTestRunner"),
    ("npm", re.compile(r"\bnpm\b", re.IGNORECASE), "NodePkg"),
]


@dataclass(frozen=True)
class FileChange:
    file: str
    replacements: Dict[str, int]


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser()
    ap.add_argument("--files", nargs="+", required=True, help="Repo-relative paths to sanitize.")
    return ap.parse_args()


def sanitize_text(text: str) -> tuple[str, Dict[str, int]]:
    counts: Dict[str, int] = {}
    for name, rx, repl in REPLACEMENTS:
        text, n = rx.subn(repl, text)
        if n:
            counts[name] = n
    return text, counts


def write_audit(changes: List[FileChange]) -> Path:
    out_dir = PROJECT_ROOT / "logs" / "ci" / date.today().isoformat()
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "root-legacy-term-sanitize.json"
    payload = {
        "generated": datetime.now().isoformat(),
        "changes": [c.__dict__ for c in changes],
    }
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return out_path


def main() -> int:
    args = parse_args()
    changes: List[FileChange] = []

    for rel in args.files:
        path = PROJECT_ROOT / rel
        if not path.exists():
            raise SystemExit(f"Missing: {rel}")
        original = path.read_text(encoding="utf-8")
        updated, counts = sanitize_text(original)
        if updated == original:
            continue
        path.write_text(updated, encoding="utf-8", newline="\n")
        changes.append(FileChange(file=rel.replace("\\", "/"), replacements=counts))
        print(f"[sanitize] {rel}: {counts}")

    audit = write_audit(changes)
    print(f"[audit] {audit}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

