#!/usr/bin/env python3
"""Extract stable requirement anchors from planning documents.

This script is deterministic. It does not ask an LLM to invent tasks. It builds
an auditable requirements index that later task-candidate generation must cover.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
from pathlib import Path
from typing import Any

DEFAULT_SOURCE_GLOBS = [
    "docs/prd/**/*.md",
    "docs/gdd/**/*.md",
    "docs/epics/**/*.md",
    "docs/stories/**/*.md",
]
PRIORITY_RE = re.compile(r"\b(P0|P1|P2|P3)\b", re.IGNORECASE)
REQ_RE = re.compile(r"\b(REQ|AC|GDD|PRD|FR|NFR)[-_ ]?(\d{1,5})\b", re.IGNORECASE)
REFS_RE = re.compile(r"\bRefs:\s*(.+)$", re.IGNORECASE)
PATH_ONLY_RE = re.compile(r"^[-*]?\s*`?[\w./\\-]+\.(json|md|cs|gd|yml|yaml|txt|save)`?\s*$", re.IGNORECASE)
TASK_REF_ONLY_RE = re.compile(r"^[-*]?\s*T\d+\s+`[^`]+`\s*$", re.IGNORECASE)
REFS_ONLY_RE = re.compile(r"^[-*]?\s*[\w./\\-]+\s+(ADR-Refs|Test-Refs|Refs):\s*$", re.IGNORECASE)


def sha12(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8")).hexdigest()[:12]


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def rel(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def expand_source_arg(root: Path, value: str) -> list[str]:
    raw = Path(value)
    candidate = raw if raw.is_absolute() else root / raw
    if any(ch in value for ch in "*?[]"):
        return [value]
    if candidate.is_dir():
        rel = candidate.relative_to(root).as_posix() if candidate.is_relative_to(root) else candidate.as_posix()
        return [f"{rel}/**/*.md"]
    return [value]


def iter_sources(root: Path, patterns: list[str]) -> list[Path]:
    files: list[Path] = []
    for pattern in patterns:
        direct = Path(pattern)
        candidate = direct if direct.is_absolute() else root / direct
        if candidate.is_file():
            files.append(candidate)
            continue
        files.extend(p for p in root.glob(pattern) if p.is_file())
    return sorted(set(files))


def split_blocks(text: str) -> list[tuple[int, str]]:
    blocks: list[tuple[int, str]] = []
    current: list[str] = []
    start = 1
    for lineno, line in enumerate(text.splitlines(), 1):
        stripped = line.strip()
        starts_block = bool(stripped.startswith("#") or stripped.startswith("-") or re.match(r"\d+[.)]\s+", stripped))
        if starts_block and current:
            blocks.append((start, "\n".join(current).strip()))
            current = []
            start = lineno
        if stripped:
            if not current:
                start = lineno
            current.append(line.rstrip())
    if current:
        blocks.append((start, "\n".join(current).strip()))
    return blocks


def is_requirement_like(block: str) -> bool:
    stripped = block.strip()
    if is_reference_only_block(stripped):
        return False
    low = block.lower()
    signals = [
        "must ", "shall ", "should ", "acceptance", "refs:", "requirement", "scenario",
        "validate", "gate", "task", "feature", "player", "system", "p0", "p1",
    ]
    return any(signal in low for signal in signals) or bool(REQ_RE.search(block))


def is_reference_only_block(block: str) -> bool:
    """Skip traceability/list noise that does not describe a requirement."""
    lines = [line.strip() for line in block.splitlines() if line.strip()]
    if len(lines) != 1:
        return False
    line = lines[0]
    if REFS_ONLY_RE.match(line):
        return True
    if PATH_ONLY_RE.match(line):
        return True
    if TASK_REF_ONLY_RE.match(line):
        return True
    if line.startswith(("- ", "* ")) and re.fullmatch(r"[-*]\s*[\w./\\-]+", line):
        return True
    return False


def infer_priority(block: str) -> str:
    match = PRIORITY_RE.search(block)
    return match.group(1).upper() if match else "P2"


def infer_kind(path: Path, block: str) -> str:
    low = path.as_posix().lower() + "\n" + block.lower()
    if "acceptance" in low or "refs:" in low:
        return "acceptance"
    if "/gdd/" in low:
        return "gdd"
    if "/prd/" in low:
        return "prd"
    if "/epics/" in low or "epic" in low:
        return "epic"
    if "/stories/" in low or "story" in low:
        return "story"
    if "/overlays/" in low:
        return "overlay"
    if "/adr/" in low:
        return "adr"
    return "requirement"


def explicit_id(block: str) -> str | None:
    match = REQ_RE.search(block)
    if not match:
        return None
    return f"{match.group(1).upper()}-{int(match.group(2)):04d}"


def extract_refs(block: str) -> list[str]:
    refs: list[str] = []
    for line in block.splitlines():
        match = REFS_RE.search(line)
        if match:
            refs.extend(part.strip() for part in re.split(r"[,;]\s*|\s+", match.group(1)) if part.strip())
    return sorted(set(refs))


def extract(root: Path, patterns: list[str], mode: str) -> dict[str, Any]:
    anchors: list[dict[str, Any]] = []
    seen: set[str] = set()
    for path in iter_sources(root, patterns):
        text = read_text(path)
        for line_no, block in split_blocks(text):
            if not is_requirement_like(block):
                continue
            source_rel = rel(path, root)
            stable = explicit_id(block) or f"REQ-{sha12(source_rel + ':' + str(line_no) + ':' + block)}"
            if stable in seen:
                stable = f"{stable}-{sha12(block)}"
            seen.add(stable)
            anchors.append({
                "requirement_id": stable,
                "source_path": source_rel,
                "line": line_no,
                "kind": infer_kind(path, block),
                "priority": infer_priority(block),
                "text": re.sub(r"\s+", " ", block).strip()[:1200],
                "refs": extract_refs(block),
                "content_hash": sha12(block),
            })
    return {
        "schema": "task-generation.requirements-index.v1",
        "generated_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "mode": mode,
        "source_globs": patterns,
        "anchor_count": len(anchors),
        "anchors": anchors,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Extract requirement anchors for task triplet generation.")
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--source-glob", action="append", default=[], help="Explicit source glob or file path. May be repeated.")
    parser.add_argument("--prd-path", action="append", default=[], help="PRD directory, file, or glob. May be repeated.")
    parser.add_argument("--gdd-path", action="append", default=[], help="GDD directory, file, or glob. May be repeated.")
    parser.add_argument("--epics-path", action="append", default=[], help="Epics directory, file, or glob. May be repeated.")
    parser.add_argument("--stories-path", action="append", default=[], help="Stories directory, file, or glob. May be repeated.")
    parser.add_argument("--mode", choices=["init", "add"], default="init")
    parser.add_argument("--out", default="logs/ci/task-generation/requirements.index.json")
    args = parser.parse_args()
    root = Path(args.repo_root).resolve()
    typed_sources = []
    for values in [args.prd_path, args.gdd_path, args.epics_path, args.stories_path]:
        for value in values:
            typed_sources.extend(expand_source_arg(root, value))
    explicit_sources = []
    for value in args.source_glob:
        explicit_sources.extend(expand_source_arg(root, value))
    patterns = typed_sources + explicit_sources
    if not patterns:
        patterns = DEFAULT_SOURCE_GLOBS
    data = extract(root, patterns, args.mode)
    out = root / args.out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"requirements_index={out} anchors={data['anchor_count']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
