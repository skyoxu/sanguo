#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Compare task files checksum snapshot with overlay index baseline.

Usage (Windows):
  py -3 scripts/python/remind_overlay_task_drift.py
  py -3 scripts/python/remind_overlay_task_drift.py --write
  py -3 scripts/python/remind_overlay_task_drift.py --overlay-index docs/architecture/overlays/PRD-EXAMPLE/08/_index.md
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any


DEFAULT_OVERLAY_INDEX: Path | None = None
OVERLAYS_ROOT = Path("docs/architecture/overlays")
TASK_FILES = [
    Path(".taskmaster/tasks/tasks.json"),
    Path(".taskmaster/tasks/tasks_back.json"),
    Path(".taskmaster/tasks/tasks_gameplay.json"),
]

BASELINE_RE = re.compile(
    r"(<!-- TASK_BASELINE_START -->\s*```json\s*)(.*?)(\s*```\s*<!-- TASK_BASELINE_END -->)",
    re.DOTALL,
)


def _sha256(path: Path) -> str:
    data = _canonical_bytes(path)
    return hashlib.sha256(data).hexdigest()


def _canonical_bytes(path: Path) -> bytes:
    """Return canonical content bytes for cross-platform stable hashing."""
    data = path.read_bytes()
    return data.replace(b"\r\n", b"\n")


def _build_baseline(repo_root: Path) -> dict[str, Any]:
    entries: list[dict[str, Any]] = []
    for rel in TASK_FILES:
        full_path = repo_root / rel
        if not full_path.exists():
            entries.append(
                {
                    "path": str(rel).replace("\\", "/"),
                    "exists": False,
                    "sha256": None,
                    "bytes": 0,
                }
            )
            continue

        entries.append(
            {
                "path": str(rel).replace("\\", "/"),
                "exists": True,
                "sha256": _sha256(full_path),
                "bytes": len(_canonical_bytes(full_path)),
            }
        )

    return {
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "files": entries,
    }


def _existing_overlay_indexes(repo_root: Path) -> list[Path]:
    overlays_root = repo_root / OVERLAYS_ROOT
    if not overlays_root.exists():
        return []
    return sorted(p.relative_to(repo_root) for p in overlays_root.glob('*/08/_index.md') if p.is_file())


def _candidate_index_from_doc_path(path_str: str) -> Path | None:
    normalized = str(path_str or '').strip().replace('\\', '/')
    if not normalized:
        return None
    candidate = Path(normalized)
    if candidate.name == '_index.md':
        return candidate
    if candidate.suffix.lower() == '.md' and '/08/' in normalized:
        return candidate.parent / '_index.md'
    return None


def _task_derived_overlay_indexes(repo_root: Path) -> list[Path]:
    candidates: list[Path] = []
    seen: set[str] = set()
    for rel in TASK_FILES:
        full_path = repo_root / rel
        if not full_path.exists():
            continue
        try:
            payload = json.loads(full_path.read_text(encoding='utf-8'))
        except Exception:
            continue

        items: list[dict[str, Any]] = []
        if isinstance(payload, dict):
            items = [x for x in ((payload.get('master') or {}).get('tasks') or []) if isinstance(x, dict)]
        elif isinstance(payload, list):
            items = [x for x in payload if isinstance(x, dict)]

        for item in items:
            overlay = _candidate_index_from_doc_path(str(item.get('overlay') or ''))
            if overlay is not None:
                key = overlay.as_posix()
                if key not in seen:
                    seen.add(key)
                    candidates.append(overlay)
            refs = item.get('overlay_refs')
            if not isinstance(refs, list):
                continue
            for ref in refs:
                overlay_ref = _candidate_index_from_doc_path(str(ref or ''))
                if overlay_ref is None:
                    continue
                key = overlay_ref.as_posix()
                if key in seen:
                    continue
                seen.add(key)
                candidates.append(overlay_ref)
    return candidates


def _resolve_overlay_index(repo_root: Path, explicit: str | None) -> Path:
    explicit_text = str(explicit or '').strip()
    if explicit_text:
        explicit_path = Path(explicit_text)
        full_path = (repo_root / explicit_path).resolve() if not explicit_path.is_absolute() else explicit_path
        if full_path.exists() and full_path.is_file():
            return full_path.relative_to(repo_root) if full_path.is_absolute() and str(full_path).startswith(str(repo_root)) else explicit_path
        raise FileNotFoundError(f'overlay index not found: {full_path}')

    if DEFAULT_OVERLAY_INDEX is not None:
        default_path = repo_root / DEFAULT_OVERLAY_INDEX
        if default_path.exists():
            return DEFAULT_OVERLAY_INDEX

    derived = [p for p in _task_derived_overlay_indexes(repo_root) if (repo_root / p).exists()]
    unique_derived = sorted({p.as_posix(): p for p in derived}.values(), key=lambda p: p.as_posix())
    if len(unique_derived) == 1:
        return unique_derived[0]

    discovered = _existing_overlay_indexes(repo_root)
    if len(discovered) == 1:
        return discovered[0]

    if discovered:
        listed = ', '.join(p.as_posix() for p in discovered)
        raise FileNotFoundError(f'multiple overlay indexes found; use --overlay-index. candidates={listed}')
    raise FileNotFoundError('overlay index not found under docs/architecture/overlays/*/08/_index.md')


def _load_index(repo_root: Path, overlay_index: Path) -> str:
    full_path = repo_root / overlay_index
    if not full_path.exists():
        raise FileNotFoundError(f'overlay index not found: {full_path}')
    return full_path.read_text(encoding='utf-8')


def _extract_embedded_baseline(index_text: str) -> dict[str, Any] | None:
    match = BASELINE_RE.search(index_text)
    if not match:
        return None
    payload = match.group(2).strip()
    try:
        return json.loads(payload)
    except json.JSONDecodeError:
        return None


def _replace_embedded_baseline(index_text: str, baseline: dict[str, Any]) -> str:
    rendered = json.dumps(baseline, ensure_ascii=False, indent=2)

    def _sub(match: re.Match[str]) -> str:
        return f"{match.group(1)}{rendered}{match.group(3)}"

    if not BASELINE_RE.search(index_text):
        raise ValueError('TASK_BASELINE block not found in overlay index')
    return BASELINE_RE.sub(_sub, index_text, count=1)


def _normalized_entries(entries: list[dict[str, Any]]) -> list[tuple[str, bool, str | None, int]]:
    normalized: list[tuple[str, bool, str | None, int]] = []
    for item in entries:
        normalized.append(
            (
                str(item.get('path') or ''),
                bool(item.get('exists')),
                item.get('sha256'),
                int(item.get('bytes') or 0),
            )
        )
    return sorted(normalized)


def main() -> int:
    parser = argparse.ArgumentParser(description='Overlay task-drift reminder based on embedded checksum baseline.')
    parser.add_argument('--write', action='store_true', help='Update baseline in overlay index with current checksums.')
    parser.add_argument('--overlay-index', default='', help='Optional overlay index path override.')
    args = parser.parse_args()

    repo_root = Path.cwd().resolve()
    overlay_index = _resolve_overlay_index(repo_root, args.overlay_index)
    index_path = repo_root / overlay_index

    current = _build_baseline(repo_root)
    index_text = _load_index(repo_root, overlay_index)
    embedded = _extract_embedded_baseline(index_text)

    if args.write:
        updated_text = _replace_embedded_baseline(index_text, current)
        index_path.write_text(updated_text, encoding='utf-8')
        print(f'OVERLAY_TASK_BASELINE status=updated file={overlay_index.as_posix()}')
        return 0

    if not embedded:
        print(f'OVERLAY_TASK_BASELINE status=missing file={overlay_index.as_posix()} action=run-with---write')
        return 1

    embedded_entries = _normalized_entries(list(embedded.get('files') or []))
    current_entries = _normalized_entries(list(current.get('files') or []))

    if embedded_entries == current_entries:
        print(f'OVERLAY_TASK_BASELINE status=ok file={overlay_index.as_posix()} drift=false')
        return 0

    print(f'OVERLAY_TASK_BASELINE status=drift file={overlay_index.as_posix()} drift=true action=run-with---write')
    for old, new in zip(embedded_entries, current_entries):
        if old != new:
            print(f' - changed old={old} new={new}')
    if len(embedded_entries) != len(current_entries):
        print(f' - entries_count old={len(embedded_entries)} new={len(current_entries)}')
    return 2


if __name__ == '__main__':
    sys.exit(main())
