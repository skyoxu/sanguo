#!/usr/bin/env python3
"""Compatibility adapter from the full Chapter 3 source ledger to legacy anchors.

The complete source ledger is always built first. Requirement-like detection is
retained only as a compatibility hint for older downstream consumers and never
removes a source block from the ledger.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from pathlib import Path
from typing import Any

from build_source_ledger import (
    DEFAULT_SOURCE_GLOBS,
    build_ledger,
    collect_patterns,
    requirement_like_hint,
    write_json,
)

PRIORITY_RE = re.compile(r"\b(P0|P1|P2|P3)\b", re.IGNORECASE)
REQ_RE = re.compile(r"\b(REQ|AC|GDD|PRD|FR|NFR)[-_ ]?(\d{1,5})\b", re.IGNORECASE)
REFS_RE = re.compile(r"\bRefs:\s*(.+)$", re.IGNORECASE)
PATH_ONLY_RE = re.compile(r"^[-*]?\s*[\w./\\-]+\.(json|md|cs|gd|yml|yaml|txt|save)\s*$", re.IGNORECASE)
TASK_REF_ONLY_RE = re.compile(r"^[-*]?\s*T\d+\s+.+$", re.IGNORECASE)
REFS_ONLY_RE = re.compile(r"^[-*]?\s*[\w./\\-]+\s+(ADR-Refs|Test-Refs|Refs):\s*$", re.IGNORECASE)


def is_reference_only_block(block: str) -> bool:
    lines = [line.strip() for line in block.splitlines() if line.strip()]
    if len(lines) != 1:
        return False
    line = lines[0]
    if REFS_ONLY_RE.match(line) or PATH_ONLY_RE.match(line) or TASK_REF_ONLY_RE.match(line):
        return True
    if line.startswith(("- ", "* ")) and re.fullmatch(r"[-*]\s*[\w./\\-]+", line):
        return True
    return False


def is_requirement_like(block: str) -> bool:
    if is_reference_only_block(block.strip()):
        return False
    return requirement_like_hint(block)


def infer_priority(block: str) -> str:
    match = PRIORITY_RE.search(block)
    return match.group(1).upper() if match else "P2"


def infer_kind(source_path: str) -> str:
    low = source_path.replace("\\", "/").lower()
    if "/gdd/" in low or low.endswith("/gdd.md"):
        return "gdd"
    if "/prd/" in low:
        return "prd"
    if "/epics/" in low or "epic" in low:
        return "epic"
    if "/stories/" in low or "story" in low:
        return "story"
    return "requirement"


def explicit_id(block: str) -> str | None:
    match = REQ_RE.search(block)
    if not match:
        return None
    return f"{match.group(1).upper()}-{int(match.group(2)):04d}"


def extract_refs(block: str) -> list[str]:
    refs = []
    for line in block.splitlines():
        match = REFS_RE.search(line)
        if match:
            refs.extend(part.strip() for part in re.split(r"[,;]\s*|\s+", match.group(1)) if part.strip())
    return sorted(set(refs))


def anchors_from_ledger(ledger: dict[str, Any]) -> list[dict[str, Any]]:
    anchors = []
    seen = set()
    for block in ledger.get("blocks", []):
        if not isinstance(block, dict):
            continue
        raw = str(block.get("raw_text") or "")
        if not is_requirement_like(raw):
            continue
        source_path = str(block.get("source_path") or "")
        stable = explicit_id(raw) or "REQ-" + str(block.get("block_id", "SB-UNKNOWN")).removeprefix("SB-")
        if stable in seen:
            stable = stable + "-" + str(block.get("content_hash", ""))[-8:].upper()
        seen.add(stable)
        anchors.append({
            "requirement_id": stable,
            "source_block_id": block.get("block_id"),
            "source_path": source_path,
            "line": int(block.get("line_start") or 1),
            "line_end": int(block.get("line_end") or block.get("line_start") or 1),
            "kind": infer_kind(source_path),
            "priority": infer_priority(raw),
            "text": " ".join(raw.split())[:1200],
            "refs": extract_refs(raw),
            "content_hash": str(block.get("content_hash") or "").removeprefix("sha256:")[:12],
            "requirement_like_hint": True,
        })
    return anchors


def extract(root: Path, patterns: list[str], mode: str) -> dict[str, Any]:
    manifest, ledger = build_ledger(root, patterns or DEFAULT_SOURCE_GLOBS, mode)
    anchors = anchors_from_ledger(ledger)
    return {
        "schema": "task-generation.requirements-index.v1",
        "generated_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "mode": mode,
        "source_revision": ledger.get("source_revision"),
        "source_manifest_sha256": manifest.get("manifest_sha256"),
        "source_block_count": len(ledger.get("blocks", [])),
        "anchor_count": len(anchors),
        "compatibility_filter": "requirement-like-hint-only",
        "anchors": anchors,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--source-glob", action="append", default=[])
    parser.add_argument("--prd-path", action="append", default=[])
    parser.add_argument("--gdd-path", action="append", default=[])
    parser.add_argument("--epics-path", action="append", default=[])
    parser.add_argument("--stories-path", action="append", default=[])
    parser.add_argument("--mode", choices=["init", "add"], default="init")
    parser.add_argument("--previous-ledger", default="")
    parser.add_argument("--ledger-input", default="")
    parser.add_argument("--manifest-out", default="logs/ci/task-generation/source-manifest.v1.json")
    parser.add_argument("--source-blocks-out", default="logs/ci/task-generation/source-blocks.v1.json")
    parser.add_argument("--out", default="logs/ci/task-generation/requirements.index.json")
    args = parser.parse_args(argv)
    root = Path(args.repo_root).resolve()
    if args.ledger_input:
        ledger_path = root / args.ledger_input
        if not ledger_path.is_file():
            print(f"requirements_adapter_error=ledger input not found: {ledger_path}")
            return 2
        ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
        manifest = {
            "manifest_sha256": ledger.get("source_manifest_sha256"),
            "source_revision": ledger.get("source_revision"),
        }
    else:
        patterns, explicit = collect_patterns(root, args)
        previous = None
        previous_path = root / args.previous_ledger if args.previous_ledger else root / args.source_blocks_out
        if args.mode == "add" and previous_path.is_file():
            previous = json.loads(previous_path.read_text(encoding="utf-8"))
        try:
            manifest, ledger = build_ledger(root, patterns, args.mode, explicit, previous)
        except ValueError as exc:
            print(f"requirements_adapter_error={exc}")
            return 2
        write_json(root / args.manifest_out, manifest)
        write_json(root / args.source_blocks_out, ledger)
    anchors = anchors_from_ledger(ledger)
    index = {
        "schema": "task-generation.requirements-index.v1",
        "generated_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "mode": args.mode,
        "source_revision": ledger.get("source_revision"),
        "source_manifest_sha256": manifest.get("manifest_sha256"),
        "source_block_count": len(ledger.get("blocks", [])),
        "anchor_count": len(anchors),
        "compatibility_filter": "requirement-like-hint-only",
        "anchors": anchors,
    }
    write_json(root / args.out, index)
    print(
        f"requirements_index={root / args.out} anchors={len(anchors)} "
        f"source_blocks={len(ledger.get('blocks', []))}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
