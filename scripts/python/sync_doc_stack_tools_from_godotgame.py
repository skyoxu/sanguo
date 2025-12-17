#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sync documentation convergence tooling from the sibling repository (godotgame).

This repo's doc workflow expects the following scripts to exist and match the guide:
  - scripts/python/check_encoding.py (supports --root)
  - scripts/python/scan_doc_stack_terms.py
  - scripts/python/sanitize_legacy_stack_terms.py
  - scripts/python/sanitize_docs_no_emoji.py

We copy them from the local reference repository to keep behavior consistent and
avoid console encoding pitfalls by writing files as raw bytes.

Windows usage:
  py -3 scripts/python/sync_doc_stack_tools_from_godotgame.py
  py -3 scripts/python/sync_doc_stack_tools_from_godotgame.py --reference-root C:\\buildgame\\godotgame
"""

from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import List


PROJECT_ROOT = Path(__file__).resolve().parents[2]

DEFAULT_REFERENCE_ROOT = Path(r"C:\buildgame\godotgame")

FILES_TO_SYNC = [
    Path("scripts/python/check_encoding.py"),
    Path("scripts/python/scan_doc_stack_terms.py"),
    Path("scripts/python/sanitize_legacy_stack_terms.py"),
    Path("scripts/python/sanitize_docs_no_emoji.py"),
    Path("docs/workflows/doc-stack-convergence-guide.md"),
]


@dataclass(frozen=True)
class CopyRecord:
    source: str
    dest: str
    bytes: int
    sha256: str


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def read_bytes(path: Path) -> bytes:
    return path.read_bytes()


def write_bytes(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def copy_file(ref_root: Path, rel_path: Path) -> CopyRecord:
    src = ref_root / rel_path
    dst = PROJECT_ROOT / rel_path

    if not src.exists():
        raise FileNotFoundError(f"Missing in reference repo: {src}")

    data = read_bytes(src)
    write_bytes(dst, data)

    return CopyRecord(
        source=str(src),
        dest=str(dst),
        bytes=len(data),
        sha256=sha256_bytes(data),
    )


def write_audit(records: List[CopyRecord]) -> Path:
    out_dir = PROJECT_ROOT / "logs" / "ci" / date.today().isoformat()
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "doc-stack-sync-tools.json"

    payload = {
        "generated": datetime.now().isoformat(),
        "reference_root": None,
        "files": [r.__dict__ for r in records],
    }

    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return out_path


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser()
    ap.add_argument("--reference-root", default=str(DEFAULT_REFERENCE_ROOT))
    return ap.parse_args()


def main() -> int:
    args = parse_args()
    ref_root = Path(args.reference_root)
    if not ref_root.exists():
        raise SystemExit(f"Reference root does not exist: {ref_root}")

    records: List[CopyRecord] = []
    for rel in FILES_TO_SYNC:
        rec = copy_file(ref_root, rel)
        records.append(rec)
        print(f"[sync] {rel} -> ok ({rec.bytes} bytes)")

    audit = write_audit(records)
    print(f"[audit] {audit}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

