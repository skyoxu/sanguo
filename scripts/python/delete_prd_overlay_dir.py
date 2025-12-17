#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Delete an overlay PRD directory safely, with an audit log.

This repo keeps overlay docs under:
  docs/architecture/overlays/<PRD-ID>/

This script deletes exactly that directory (and only that directory) and writes
an audit log to:
  logs/ci/<YYYY-MM-DD>/overlay-delete/

Safety guardrails:
  - Reject PRD IDs with path separators or traversal patterns.
  - Require explicit --yes to perform deletion.
  - Emit a full file list to the audit log before deletion.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
OVERLAYS_ROOT = ROOT / "docs" / "architecture" / "overlays"

PRD_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


def validate_prd_id(prd_id: str) -> None:
    if not prd_id or not PRD_ID_RE.fullmatch(prd_id):
        raise ValueError(f"Invalid PRD id: {prd_id!r}")
    if any(sep in prd_id for sep in ("/", "\\", ":", "..")):
        raise ValueError(f"Unsafe PRD id: {prd_id!r}")


def list_entries(target: Path) -> list[str]:
    entries: list[str] = []
    for p in sorted(target.rglob("*")):
        try:
            rel = p.relative_to(ROOT).as_posix()
        except Exception:  # noqa: BLE001
            rel = str(p)
        entries.append(rel)
    return entries


def write_audit(prd_id: str, target: Path, entries: list[str], mode: str) -> Path:
    date_str = datetime.now().strftime("%Y-%m-%d")
    out_dir = ROOT / "logs" / "ci" / date_str / "overlay-delete"
    out_dir.mkdir(parents=True, exist_ok=True)

    out_path = out_dir / f"delete-{prd_id}.json"
    payload = {
        "ts": datetime.now().astimezone().isoformat(timespec="seconds"),
        "prd_id": prd_id,
        "mode": mode,
        "target": target.relative_to(ROOT).as_posix(),
        "entries_count": len(entries),
        "entries": entries,
    }
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return out_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Delete docs/architecture/overlays/<PRD-ID>/ safely.")
    parser.add_argument("--prd-id", required=True, help="Overlay PRD directory name, e.g. PRD-SANGUO-T2")
    parser.add_argument("--yes", action="store_true", help="Actually delete (required).")
    args = parser.parse_args()

    try:
        validate_prd_id(args.prd_id)
    except ValueError as exc:
        print(f"error={exc}")
        return 2

    target = OVERLAYS_ROOT / args.prd_id
    if not target.exists():
        print(f"status=missing path={target}")
        write_audit(args.prd_id, target, [], mode="missing")
        return 0
    if not target.is_dir():
        print(f"error=not_a_directory path={target}")
        return 2

    entries = list_entries(target)
    write_audit(args.prd_id, target, entries, mode="pre-delete")

    if not args.yes:
        print(f"status=dry-run prd_id={args.prd_id} entries={len(entries)} path={target}")
        return 0

    shutil.rmtree(target)
    write_audit(args.prd_id, target, entries, mode="deleted")
    print(f"status=deleted prd_id={args.prd_id} entries={len(entries)} path={target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
