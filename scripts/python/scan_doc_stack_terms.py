#!/usr/bin/env python3
"""
Scan docs for legacy tech stack terms that can mislead humans/LLMs (e.g., Electron/Vite/Phaser).

Writes reports under:
  logs/ci/<YYYY-MM-DD>/doc-stack-scan/scan.json
  logs/ci/<YYYY-MM-DD>/doc-stack-scan/summary.json

Usage (Windows):
  py -3 scripts/python/scan_doc_stack_terms.py
  py -3 scripts/python/scan_doc_stack_terms.py --root docs
  py -3 scripts/python/scan_doc_stack_terms.py --fail-on-hits
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


DEFAULT_ROOT = "docs"
ALLOWED_EXTS = {".md", ".txt", ".yml", ".yaml", ".json", ".xml", ".ini", ".cfg", ".index", ".adoc"}

# Case-insensitive for ASCII terms; keep as regex fragments (no leading/trailing slashes).
DEFAULT_TERMS: List[Tuple[str, str]] = [
    ("vitegame", r"vitegame"),
    ("electron", r"electron"),
    ("phaser", r"phaser"),
    ("vite", r"\bvite\b"),
    ("react", r"\breact\b"),
    ("playwright", r"playwright"),
    ("vitest", r"vitest"),
    ("npm", r"\bnpm\b"),
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


def read_text_utf8(path: str) -> Tuple[str, str | None]:
    try:
        with io.open(path, "rb") as f:
            raw = f.read()
        return raw.decode("utf-8", errors="strict"), None
    except Exception as e:
        # Keep scanning even if a single file is not UTF-8; record error and decode with replacement.
        try:
            with io.open(path, "rb") as f:
                raw = f.read()
            return raw.decode("utf-8", errors="replace"), f"{type(e).__name__}: {e}"
        except Exception as e2:
            return "", f"{type(e2).__name__}: {e2}"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=DEFAULT_ROOT)
    ap.add_argument("--out-dir", default=None)
    ap.add_argument("--fail-on-hits", action="store_true")
    args = ap.parse_args()

    terms: List[Tuple[str, re.Pattern]] = []
    for name, frag in DEFAULT_TERMS:
        terms.append((name, re.compile(frag, re.IGNORECASE)))

    files = iter_docs_files(args.root)
    date = dt.date.today().strftime("%Y-%m-%d")
    out_dir = args.out_dir or os.path.join("logs", "ci", date, "doc-stack-scan")
    os.makedirs(out_dir, exist_ok=True)

    hits: List[Dict] = []
    per_file: Dict[str, int] = {}
    decode_errors: Dict[str, str] = {}

    for path in files:
        text, err = read_text_utf8(path)
        if err:
            decode_errors[path] = err
        rel = os.path.relpath(path, os.getcwd()).replace("\\", "/")
        count = 0
        for i, line in enumerate(text.splitlines(), start=1):
            for name, rx in terms:
                if not rx.search(line):
                    continue
                count += 1
                if len(hits) < 5000:
                    hits.append(
                        {
                            "file": rel,
                            "line": i,
                            "term": name,
                            "preview": (line[:400] if line else ""),
                        }
                    )
        if count:
            per_file[rel] = count

    summary = {
        "root": os.path.abspath(args.root),
        "scanned_files": len(files),
        "hit_files": len(per_file),
        "hit_count": sum(per_file.values()),
        "top_files": sorted(per_file.items(), key=lambda kv: kv[1], reverse=True)[:50],
        "decode_error_files": len(decode_errors),
        "generated": dt.datetime.now().isoformat(),
    }

    with io.open(os.path.join(out_dir, "scan.json"), "w", encoding="utf-8") as f:
        json.dump({"hits": hits, "decode_errors": decode_errors}, f, ensure_ascii=False, indent=2)
    with io.open(os.path.join(out_dir, "summary.json"), "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    print(f"DOC_STACK_SCAN scanned_files={summary['scanned_files']} hit_files={summary['hit_files']} hits={summary['hit_count']} out={out_dir}")
    if args.fail_on_hits and summary["hit_count"] > 0:
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())

