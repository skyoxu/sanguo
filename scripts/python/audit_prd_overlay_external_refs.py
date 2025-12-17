#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Audit external references to an overlay PRD directory.

Goal:
  Before deleting an overlay directory (e.g. PRD-Guild-Manager), ensure there are
  no references to it from other files in the repo (docs/scripts/code/tasks).

Default behavior:
  - Search for substring "PRD-Guild-Manager" outside docs/architecture/overlays/PRD-Guild-Manager/**.
  - Ignore logs/**, .git/**, .godot/**, bin/obj, and vendor-like folders.
  - Write a JSON report to logs/ci/<YYYY-MM-DD>/overlay-audit/overlay-audit.json.

Exit code:
  - 0 if no external references found.
  - 1 otherwise.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


DEFAULT_PRD = "PRD-Guild-Manager"


SKIP_DIRS = {
    ".git",
    ".godot",
    ".serena",
    "logs",
    "bin",
    "obj",
    "__pycache__",
}


@dataclass(frozen=True)
class Hit:
    path: str
    line: int
    text: str


def should_skip(path: Path) -> bool:
    parts = set(path.parts)
    return any(p in parts for p in SKIP_DIRS)


def iter_text_files(root: Path) -> list[Path]:
    files: list[Path] = []
    for p in root.rglob("*"):
        if not p.is_file():
            continue
        if should_skip(p):
            continue
        if p.resolve() == Path(__file__).resolve():
            continue
        if p.suffix.lower() in {".png", ".jpg", ".jpeg", ".gif", ".ico", ".zip", ".pck", ".dll", ".exe"}:
            continue
        if p.suffix.lower() in {".pyc", ".pkl"}:
            continue
        files.append(p)
    return files


def scan(prd_id: str) -> list[Hit]:
    overlays_dir = ROOT / "docs" / "architecture" / "overlays" / prd_id
    hits: list[Hit] = []
    needle = prd_id

    for file_path in iter_text_files(ROOT):
        # Ignore files inside the overlay directory itself (it will be deleted).
        try:
            if overlays_dir.exists() and file_path.resolve().is_relative_to(overlays_dir.resolve()):
                continue
        except AttributeError:
            # Python < 3.9 fallback is unnecessary for this repo, but keep defensive.
            try:
                file_path.resolve().relative_to(overlays_dir.resolve())
                continue
            except Exception:  # noqa: BLE001
                pass

        try:
            text = file_path.read_text(encoding="utf-8", errors="ignore")
        except Exception:  # noqa: BLE001
            continue

        if needle not in text:
            continue

        for idx, line in enumerate(text.splitlines(), start=1):
            if needle in line:
                rel = file_path.relative_to(ROOT).as_posix()
                hits.append(Hit(path=rel, line=idx, text=line.strip()))

    return hits


def write_report(prd_id: str, hits: list[Hit]) -> Path:
    date_str = datetime.now().strftime("%Y-%m-%d")
    out_dir = ROOT / "logs" / "ci" / date_str / "overlay-audit"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "overlay-audit.json"

    payload = {
        "ts": datetime.now().astimezone().isoformat(timespec="seconds"),
        "prd_id": prd_id,
        "external_refs_count": len(hits),
        "external_refs": [
            {"path": h.path, "line": h.line, "text": h.text} for h in hits
        ],
    }
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return out_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit external references to a PRD overlay directory.")
    parser.add_argument("--prd-id", default=DEFAULT_PRD, help="Overlay PRD directory name (default: PRD-Guild-Manager)")
    args = parser.parse_args()

    hits = scan(args.prd_id)
    out = write_report(args.prd_id, hits)

    print(f"prd_id={args.prd_id} external_refs={len(hits)} report={out}")
    for h in hits[:50]:
        print(f"- {h.path}:{h.line} {h.text}")

    return 0 if not hits else 1


if __name__ == "__main__":
    raise SystemExit(main())
