#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sync documentation folders from the local reference repository (godotgame) to converge wording/stack.

This is a pragmatic convergence step:
- Overwrite shared template docs (base, migration, common ADRs/workflows) from the reference repo.
- Preserve repo-specific docs that do not exist in the reference repo (e.g., PRD-SANGUO overlays).
- Remove known legacy base artifacts that should not remain as current SSoT.

Windows usage:
  py -3 scripts/python/sync_docs_from_godotgame.py
  py -3 scripts/python/sync_docs_from_godotgame.py --reference-root C:\\buildgame\\godotgame
"""

from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Dict, Iterable, List, Tuple


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_REFERENCE_ROOT = Path(r"C:\buildgame\godotgame")

# Directories to sync (relative to repo root).
SYNC_DIRS = [
    Path("docs/architecture/base"),
    Path("docs/migration"),
    Path("docs/workflows"),
    Path("docs/adr"),
    Path("docs/adr/addenda"),
    Path("docs/contracts"),
    Path("docs/release"),
]

# Individual files to sync (relative to repo root).
SYNC_FILES = [
    Path("docs/PROJECT_CAPABILITIES_STATUS.md"),
    Path("docs/PROJECT_DOCUMENTATION_INDEX.md"),
]

# Legacy base artifacts to remove from this repo (no longer current SSoT).
DELETE_FILES = [
    Path("docs/architecture/base/02-security-baseline-electron-v2.md"),
    Path("docs/architecture/base/csp-policy-analysis.md"),
]


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


@dataclass(frozen=True)
class CopyRecord:
    rel: str
    source: str
    dest: str
    bytes: int
    sha256: str


@dataclass(frozen=True)
class DeleteRecord:
    rel: str
    path: str


def iter_files(root: Path) -> List[Path]:
    files: List[Path] = []
    if not root.exists():
        return files
    for p in root.rglob("*"):
        if p.is_file():
            files.append(p)
    files.sort()
    return files


def copy_bytes(src: Path, dst: Path) -> Tuple[int, str]:
    data = src.read_bytes()
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_bytes(data)
    return len(data), sha256_bytes(data)


def sync_dir(ref_root: Path, rel_dir: Path) -> List[CopyRecord]:
    src_dir = ref_root / rel_dir
    dst_dir = PROJECT_ROOT / rel_dir
    if not src_dir.exists():
        return []

    records: List[CopyRecord] = []
    for src_file in iter_files(src_dir):
        rel = src_file.relative_to(ref_root)
        dst_file = PROJECT_ROOT / rel
        size, digest = copy_bytes(src_file, dst_file)
        records.append(
            CopyRecord(
                rel=str(rel).replace("\\", "/"),
                source=str(src_file),
                dest=str(dst_file),
                bytes=size,
                sha256=digest,
            )
        )
    return records


def sync_file(ref_root: Path, rel_file: Path) -> CopyRecord | None:
    src = ref_root / rel_file
    if not src.exists():
        return None
    dst = PROJECT_ROOT / rel_file
    size, digest = copy_bytes(src, dst)
    return CopyRecord(
        rel=str(rel_file).replace("\\", "/"),
        source=str(src),
        dest=str(dst),
        bytes=size,
        sha256=digest,
    )


def delete_legacy_files() -> List[DeleteRecord]:
    records: List[DeleteRecord] = []
    for rel in DELETE_FILES:
        path = PROJECT_ROOT / rel
        if not path.exists():
            continue
        path.unlink()
        records.append(DeleteRecord(rel=str(rel).replace("\\", "/"), path=str(path)))
    return records


def write_audit(copies: List[CopyRecord], deletes: List[DeleteRecord], ref_root: Path) -> Path:
    out_dir = PROJECT_ROOT / "logs" / "ci" / date.today().isoformat()
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "doc-stack-sync-docs.json"

    payload: Dict = {
        "generated": datetime.now().isoformat(),
        "reference_root": str(ref_root),
        "copied_files": [c.__dict__ for c in copies],
        "deleted_files": [d.__dict__ for d in deletes],
        "counts": {"copied": len(copies), "deleted": len(deletes)},
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

    copies: List[CopyRecord] = []
    for rel_dir in SYNC_DIRS:
        copies.extend(sync_dir(ref_root, rel_dir))
        print(f"[sync-dir] {rel_dir} -> ok")

    for rel_file in SYNC_FILES:
        rec = sync_file(ref_root, rel_file)
        if rec:
            copies.append(rec)
            print(f"[sync-file] {rel_file} -> ok")

    deletes = delete_legacy_files()
    for d in deletes:
        print(f"[delete] {d.rel}")

    audit = write_audit(copies, deletes, ref_root)
    print(f"[audit] {audit}")
    print(f"[summary] copied={len(copies)} deleted={len(deletes)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

