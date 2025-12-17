#!/usr/bin/env python3
"""
Sanitize docs to avoid legacy tech stack proper names that can mislead humans/LLMs.

This script replaces a small, opinionated set of terms with neutral placeholders.
It is intentionally conservative: it only touches text files under --root and
only replaces known legacy stack tokens.

Reports are written under:
  logs/ci/<YYYY-MM-DD>/legacy-term-sanitize/summary.json
  logs/ci/<YYYY-MM-DD>/legacy-term-sanitize/changes.json

Usage (Windows):
  py -3 scripts/python/sanitize_legacy_stack_terms.py --root docs --write
"""

from __future__ import annotations

import argparse
import datetime as dt
import io
import json
import os
import re
import sys
from typing import Dict, List, Tuple


ALLOWED_EXTS = {".md", ".txt", ".yml", ".yaml", ".json", ".xml", ".ini", ".cfg", ".index", ".adoc"}

# Keep patterns aligned with scripts/python/scan_doc_stack_terms.py
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


def iter_docs_files(root: str) -> List[str]:
    root = os.path.abspath(root)
    out: List[str] = []
    for dirpath, _, filenames in os.walk(root):
        for name in filenames:
            ext = os.path.splitext(name)[1].lower()
            if ext not in ALLOWED_EXTS:
                continue
            out.append(os.path.join(dirpath, name))
    out.sort()
    return out


def read_utf8(path: str) -> str:
    with io.open(path, "rb") as f:
        raw = f.read()
    return raw.decode("utf-8", errors="strict")


def write_utf8(path: str, text: str) -> None:
    with io.open(path, "w", encoding="utf-8", newline="") as f:
        f.write(text)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default="docs")
    ap.add_argument("--out-dir", default=None)
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args()

    files = iter_docs_files(args.root)
    date = dt.date.today().strftime("%Y-%m-%d")
    out_dir = args.out_dir or os.path.join("logs", "ci", date, "legacy-term-sanitize")
    os.makedirs(out_dir, exist_ok=True)

    changes: List[Dict] = []
    by_term: Dict[str, int] = {name: 0 for name, _, _ in REPLACEMENTS}
    decode_errors: Dict[str, str] = {}

    for path in files:
        rel = os.path.relpath(path, os.getcwd()).replace("\\", "/")
        try:
            text = read_utf8(path)
        except Exception as e:
            decode_errors[rel] = f"{type(e).__name__}: {e}"
            continue

        original = text
        file_counts: Dict[str, int] = {}
        for name, rx, repl in REPLACEMENTS:
            text, n = rx.subn(repl, text)
            if n:
                file_counts[name] = n
                by_term[name] += n

        if text != original:
            changes.append({"file": rel, "replacements": file_counts})
            if args.write:
                write_utf8(path, text)

    summary = {
        "root": os.path.abspath(args.root),
        "scanned_files": len(files),
        "changed_files": len(changes),
        "total_replacements": sum(by_term.values()),
        "by_term": by_term,
        "decode_error_files": len(decode_errors),
        "generated": dt.datetime.now().isoformat(),
        "write": bool(args.write),
    }

    with io.open(os.path.join(out_dir, "summary.json"), "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    with io.open(os.path.join(out_dir, "changes.json"), "w", encoding="utf-8") as f:
        json.dump({"changes": changes, "decode_errors": decode_errors}, f, ensure_ascii=False, indent=2)

    print(
        "LEGACY_TERM_SANITIZE "
        f"scanned_files={summary['scanned_files']} "
        f"changed_files={summary['changed_files']} "
        f"replacements={summary['total_replacements']} "
        f"out={out_dir}"
    )
    if decode_errors:
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())

