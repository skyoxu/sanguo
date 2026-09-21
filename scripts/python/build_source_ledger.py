#!/usr/bin/env python3
"""Build a complete deterministic Chapter 3 source ledger."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
import subprocess
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

DEFAULT_SOURCE_GLOBS = [
    "docs/prd/**/*.md",
    "docs/gdd/**/*.md",
    "_bmad-output/gdd.md",
    "docs/epics/**/*.md",
    "docs/stories/**/*.md",
]
SUPPORTED_SUFFIXES = {".md", ".markdown", ".json", ".txt"}
HEADING_RE = re.compile(r"^(#{1,6})\s+(.*\S)\s*$")
LIST_RE = re.compile(r"^\s*(?:[-*+]\s+|\d+[.)]\s+)")
TABLE_SEPARATOR_RE = re.compile(r"^\s*\|?\s*:?-{3,}")
FENCE = chr(96) * 3
REQUIREMENT_HINTS = (
    "must ", "shall ", "should ", "requirement", "acceptance", "player", "system",
    "必须", "不得", "只能", "至少", "不可", "允许", "目标", "禁止", "应当", "需要",
)


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def canonical_sha(value: Any) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return sha256_text(raw)


def rel(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def current_git_revision(root: Path) -> str | None:
    try:
        result = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "HEAD"],
            capture_output=True, text=True, encoding="utf-8", timeout=10, check=True,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    value = result.stdout.strip()
    return value if re.fullmatch(r"[0-9a-f]{40}", value) else None


def expand_source_arg(root: Path, value: str) -> list[str]:
    candidate = Path(value)
    candidate = candidate if candidate.is_absolute() else root / candidate
    if any(ch in value for ch in "*?[]"):
        return [value]
    if candidate.is_dir():
        base = candidate.relative_to(root).as_posix() if candidate.is_relative_to(root) else candidate.as_posix()
        return [f"{base}/**/*"]
    return [value]


def resolve_sources(root: Path, patterns: list[str], explicit: bool) -> tuple[list[Path], list[str]]:
    files: list[Path] = []
    missing: list[str] = []
    for pattern in patterns:
        matches: list[Path] = []
        direct = Path(pattern)
        candidate = direct if direct.is_absolute() else root / direct
        if candidate.is_file() and candidate.suffix.lower() in SUPPORTED_SUFFIXES:
            matches.append(candidate)
        elif not candidate.is_file():
            matches.extend(
                path for path in root.glob(pattern)
                if path.is_file() and path.suffix.lower() in SUPPORTED_SUFFIXES
            )
        if explicit and not matches:
            missing.append(pattern)
        files.extend(matches)
    return sorted(set(files), key=lambda p: p.as_posix()), missing


def requirement_like_hint(text: str) -> bool:
    low = text.casefold()
    return any(signal.casefold() in low for signal in REQUIREMENT_HINTS) or bool(
        re.search(r"\b(?:FR|NFR|REQ|AC|GDD|PRD)[-_ ]?\d{1,5}\b", text, re.IGNORECASE)
    )


def append_block(
    blocks: list[dict[str, Any]],
    ordinals: dict[tuple[tuple[str, ...], str], int],
    source_path: str,
    source_sha: str,
    block_type: str,
    headings: list[str],
    line_start: int,
    line_end: int,
    raw_text: str,
    json_pointer: str | None = None,
    source_char_start: int | None = None,
    source_char_end_exclusive: int | None = None,
) -> None:
    raw = raw_text.rstrip()
    if not raw.strip():
        return
    key = (tuple(headings), block_type)
    ordinals[key] += 1
    identity = {
        "source_path": source_path,
        "heading_path": headings,
        "block_type": block_type,
        "ordinal": ordinals[key],
    }
    row = {
        "block_id": "SB-" + canonical_sha(identity)[:16].upper(),
        "source_path": source_path,
        "source_sha256": source_sha,
        "heading_path": list(headings),
        "block_type": block_type,
        "ordinal": ordinals[key],
        "line_start": line_start,
        "line_end": line_end,
        "content_hash": "sha256:" + sha256_text(raw),
        "raw_text": raw,
        "requirement_like_hint": requirement_like_hint(raw),
    }
    if json_pointer is not None:
        row["json_pointer"] = json_pointer
    if source_char_start is not None:
        row["source_char_start"] = source_char_start
    if source_char_end_exclusive is not None:
        row["source_char_end_exclusive"] = source_char_end_exclusive
    blocks.append(row)


def parse_markdown(source_path: str, source_sha: str, text: str) -> list[dict[str, Any]]:
    lines = text.splitlines()
    blocks: list[dict[str, Any]] = []
    ordinals: dict[tuple[tuple[str, ...], str], int] = defaultdict(int)
    headings: list[str] = []
    paragraph: list[str] = []
    paragraph_start = 0
    fence_lines: list[str] = []
    fence_start = 0
    in_fence = False

    def flush(end_line: int) -> None:
        nonlocal paragraph, paragraph_start
        if paragraph:
            append_block(
                blocks, ordinals, source_path, source_sha, "paragraph", headings,
                paragraph_start, end_line, "\n".join(paragraph),
            )
            paragraph = []
            paragraph_start = 0

    for index, line in enumerate(lines, 1):
        stripped = line.strip()
        if in_fence:
            fence_lines.append(line)
            if stripped.startswith(FENCE):
                append_block(
                    blocks, ordinals, source_path, source_sha, "code_fence", headings,
                    fence_start, index, "\n".join(fence_lines),
                )
                in_fence = False
                fence_lines = []
            continue
        if stripped.startswith(FENCE):
            flush(index - 1)
            in_fence = True
            fence_start = index
            fence_lines = [line]
            continue
        if not stripped:
            flush(index - 1)
            continue
        heading = HEADING_RE.match(line)
        if heading:
            flush(index - 1)
            level = len(heading.group(1))
            title = heading.group(2).strip()
            headings = headings[: level - 1] + [title]
            append_block(
                blocks, ordinals, source_path, source_sha, "heading", headings,
                index, index, line,
            )
            continue
        if LIST_RE.match(line):
            flush(index - 1)
            append_block(
                blocks, ordinals, source_path, source_sha, "list_item", headings,
                index, index, line,
            )
            continue
        if stripped.startswith(">"):
            flush(index - 1)
            append_block(
                blocks, ordinals, source_path, source_sha, "blockquote", headings,
                index, index, line,
            )
            continue
        if "|" in line or TABLE_SEPARATOR_RE.match(line):
            flush(index - 1)
            kind = "table_separator" if TABLE_SEPARATOR_RE.match(line) else "table_row"
            append_block(
                blocks, ordinals, source_path, source_sha, kind, headings,
                index, index, line,
            )
            continue
        if not paragraph:
            paragraph_start = index
        paragraph.append(line)
    flush(len(lines))
    if in_fence and fence_lines:
        append_block(
            blocks, ordinals, source_path, source_sha, "code_fence", headings,
            fence_start, len(lines), "\n".join(fence_lines),
        )
    return blocks


def parse_text(source_path: str, source_sha: str, text: str) -> list[dict[str, Any]]:
    blocks: list[dict[str, Any]] = []
    ordinals: dict[tuple[tuple[str, ...], str], int] = defaultdict(int)
    lines = text.splitlines()
    current: list[str] = []
    start = 0
    for index, line in enumerate(lines, 1):
        if line.strip():
            if not current:
                start = index
            current.append(line)
        elif current:
            append_block(
                blocks, ordinals, source_path, source_sha, "paragraph", [],
                start, index - 1, "\n".join(current),
            )
            current = []
    if current:
        append_block(
            blocks, ordinals, source_path, source_sha, "paragraph", [],
            start, len(lines), "\n".join(current),
        )
    return blocks


def _json_skip_ws(text: str, offset: int) -> int:
    while offset < len(text) and text[offset] in " \t\r\n":
        offset += 1
    return offset


def _json_line_at(text: str, offset: int) -> int:
    return text.count("\n", 0, max(0, offset)) + 1


def _json_span_lines(text: str, start: int, end_exclusive: int) -> tuple[int, int]:
    line_start = _json_line_at(text, start)
    last = start if end_exclusive <= start else end_exclusive - 1
    return line_start, _json_line_at(text, last)


def parse_json(source_path: str, source_sha: str, text: str) -> list[dict[str, Any]]:
    """Parse top-level JSON blocks while preserving exact authoritative source slices."""
    blocks: list[dict[str, Any]] = []
    ordinals: dict[tuple[tuple[str, ...], str], int] = defaultdict(int)
    line_end = max(1, len(text.splitlines()))
    decoder = json.JSONDecoder()
    try:
        value = json.loads(text)
    except json.JSONDecodeError:
        append_block(blocks, ordinals, source_path, source_sha, "json_invalid", [], 1, line_end, text)
        return blocks

    start = _json_skip_ws(text, 0)
    if isinstance(value, dict):
        offset = _json_skip_ws(text, start + 1)
        while offset < len(text) and text[offset] != "}":
            member_start = offset
            try:
                key, key_end = decoder.raw_decode(text, offset)
            except json.JSONDecodeError as exc:
                raise ValueError(f"failed to locate JSON member source span: {source_path}") from exc
            if not isinstance(key, str):
                raise ValueError(f"JSON object key is not a string: {source_path}")
            offset = _json_skip_ws(text, key_end)
            if offset >= len(text) or text[offset] != ":":
                raise ValueError(f"failed to locate JSON member separator: {source_path}")
            value_start = _json_skip_ws(text, offset + 1)
            try:
                _item, value_end = decoder.raw_decode(text, value_start)
            except json.JSONDecodeError as exc:
                raise ValueError(f"failed to locate JSON member value span: {source_path}") from exc
            member_end = value_end
            line_start, member_line_end = _json_span_lines(text, member_start, member_end)
            pointer = "/" + key.replace("~", "~0").replace("/", "~1")
            append_block(
                blocks, ordinals, source_path, source_sha, "json_member", [key],
                line_start, member_line_end, text[member_start:member_end], pointer,
                member_start, member_end,
            )
            offset = _json_skip_ws(text, value_end)
            if offset < len(text) and text[offset] == ",":
                offset = _json_skip_ws(text, offset + 1)
                continue
            if offset < len(text) and text[offset] == "}":
                break
            raise ValueError(f"failed to locate next JSON member boundary: {source_path}")
    elif isinstance(value, list):
        offset = _json_skip_ws(text, start + 1)
        index = 0
        while offset < len(text) and text[offset] != "]":
            item_start = offset
            try:
                _item, item_end = decoder.raw_decode(text, item_start)
            except json.JSONDecodeError as exc:
                raise ValueError(f"failed to locate JSON item source span: {source_path}") from exc
            line_start, item_line_end = _json_span_lines(text, item_start, item_end)
            append_block(
                blocks, ordinals, source_path, source_sha, "json_item", [],
                line_start, item_line_end, text[item_start:item_end], f"/{index}",
                item_start, item_end,
            )
            index += 1
            offset = _json_skip_ws(text, item_end)
            if offset < len(text) and text[offset] == ",":
                offset = _json_skip_ws(text, offset + 1)
                continue
            if offset < len(text) and text[offset] == "]":
                break
            raise ValueError(f"failed to locate next JSON item boundary: {source_path}")
    else:
        try:
            _item, value_end = decoder.raw_decode(text, start)
        except json.JSONDecodeError as exc:
            raise ValueError(f"failed to locate JSON value source span: {source_path}") from exc
        line_start, value_line_end = _json_span_lines(text, start, value_end)
        append_block(
            blocks, ordinals, source_path, source_sha, "json_value", [],
            line_start, value_line_end, text[start:value_end], "",
            start, value_end,
        )
    return blocks


def parse_source(path: Path, root: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    source_path = rel(path, root)
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError(f"authoritative source is not valid UTF-8: {source_path}") from exc
    source_sha = sha256_text(text)
    if path.suffix.lower() in {".md", ".markdown"}:
        source_type = "markdown"
        blocks = parse_markdown(source_path, source_sha, text)
    elif path.suffix.lower() == ".json":
        source_type = "json"
        blocks = parse_json(source_path, source_sha, text)
    else:
        source_type = "text"
        blocks = parse_text(source_path, source_sha, text)
    return {
        "path": source_path,
        "source_type": source_type,
        "sha256": source_sha,
        "line_count": max(1, len(text.splitlines())),
        "block_count": len(blocks),
    }, blocks


def _block_family(row: dict[str, Any]) -> tuple[str, tuple[str, ...], str]:
    return (
        str(row.get("source_path") or ""),
        tuple(str(x) for x in row.get("heading_path", [])),
        str(row.get("block_type") or ""),
    )


def stabilize_add_mode_ids(
    blocks: list[dict[str, Any]], previous: dict[str, Any] | None
) -> None:
    if not previous:
        return
    old_rows = [
        row for row in previous.get("blocks", [])
        if isinstance(row, dict) and row.get("block_id")
    ]
    used_old: set[str] = set()
    used_new: set[str] = set()
    matched_rows: set[int] = set()

    # First preserve ids for semantically identical blocks even when an insertion
    # shifted their ordinal within the same heading/type family.
    for row in blocks:
        family = _block_family(row)
        candidates = [
            old for old in old_rows
            if str(old.get("block_id")) not in used_old
            and _block_family(old) == family
            and old.get("content_hash") == row.get("content_hash")
        ]
        if not candidates:
            continue
        current_ordinal = int(row.get("ordinal") or 0)
        chosen = min(
            candidates,
            key=lambda old: (
                abs(int(old.get("ordinal") or 0) - current_ordinal),
                str(old.get("block_id")),
            ),
        )
        block_id = str(chosen["block_id"])
        row["block_id"] = block_id
        used_old.add(block_id)
        used_new.add(block_id)
        matched_rows.add(id(row))

    old_by_id = {str(row["block_id"]): row for row in old_rows}
    for row in blocks:
        block_id = str(row.get("block_id") or "")
        if id(row) in matched_rows:
            continue
        old = old_by_id.get(block_id)
        if old is not None and block_id not in used_old and _block_family(old) == _block_family(row):
            # Same logical slot with different content: retain id so delta reports changed.
            used_old.add(block_id)
            used_new.add(block_id)
            continue
        # A newly inserted block may have generated an id already reclaimed by an
        # unchanged shifted block. Give the insertion a deterministic content-bound id.
        seed = {
            "source_path": row.get("source_path"),
            "heading_path": row.get("heading_path", []),
            "block_type": row.get("block_type"),
            "content_hash": row.get("content_hash"),
            "line_start": row.get("line_start"),
        }
        candidate = "SB-" + canonical_sha(seed)[:16].upper()
        salt = 1
        while candidate in used_new:
            candidate = "SB-" + canonical_sha({**seed, "salt": salt})[:16].upper()
            salt += 1
        row["block_id"] = candidate
        used_new.add(candidate)


def compute_delta(blocks: list[dict[str, Any]], previous: dict[str, Any] | None) -> dict[str, Any]:
    if not previous:
        return {"unchanged": [], "changed": [], "added": [row["block_id"] for row in blocks], "removed": []}
    old = {str(row.get("block_id")): row for row in previous.get("blocks", []) if isinstance(row, dict)}
    new = {str(row.get("block_id")): row for row in blocks}
    unchanged = []
    changed = []
    added = []
    for block_id, row in new.items():
        if block_id not in old:
            added.append(block_id)
        elif old[block_id].get("content_hash") == row.get("content_hash"):
            unchanged.append(block_id)
        else:
            changed.append(block_id)
    return {
        "unchanged": sorted(unchanged),
        "changed": sorted(changed),
        "added": sorted(added),
        "removed": sorted(set(old) - set(new)),
    }


def build_ledger(
    root: Path,
    patterns: list[str],
    mode: str,
    explicit: bool = False,
    previous_ledger: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    files, missing = resolve_sources(root, patterns, explicit)
    if missing:
        raise ValueError("declared source patterns matched no supported files: " + ", ".join(missing))
    if not files:
        raise ValueError("no authoritative planning sources matched")
    sources = []
    blocks = []
    for path in files:
        source, parsed = parse_source(path, root)
        sources.append(source)
        blocks.extend(parsed)
    binding = [{"path": row["path"], "source_type": row["source_type"], "sha256": row["sha256"]} for row in sources]
    if mode == "add":
        stabilize_add_mode_ids(blocks, previous_ledger)

    manifest_sha = canonical_sha(binding)
    source_revision = "source-set:" + manifest_sha[:24]
    generated = dt.datetime.now(dt.timezone.utc).isoformat()
    manifest = {
        "schema_version": "chapter3.source-manifest.v1",
        "generated_at_utc": generated,
        "mode": mode,
        "source_revision": source_revision,
        "manifest_sha256": "sha256:" + manifest_sha,
        "repository_revision": current_git_revision(root),
        "source_count": len(sources),
        "block_count": len(blocks),
        "sources": sources,
    }
    ledger = {
        "schema_version": "newrouge.source-blocks.v1",
        "generated_at_utc": generated,
        "mode": mode,
        "source_revision": source_revision,
        "source_manifest_sha256": manifest["manifest_sha256"],
        "parser_inventory": dict(sorted(Counter(row["block_type"] for row in blocks).items())),
        "blocks": blocks,
        "delta": compute_delta(blocks, previous_ledger if mode == "add" else None),
    }
    return manifest, ledger


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")


def collect_patterns(root: Path, args: argparse.Namespace) -> tuple[list[str], bool]:
    values = list(args.prd_path) + list(args.gdd_path) + list(args.epics_path) + list(args.stories_path) + list(args.source_glob)
    patterns = []
    for value in values:
        patterns.extend(expand_source_arg(root, value))
    return (patterns or list(DEFAULT_SOURCE_GLOBS), bool(values))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--mode", choices=["init", "add"], default="init")
    parser.add_argument("--prd-path", action="append", default=[])
    parser.add_argument("--gdd-path", action="append", default=[])
    parser.add_argument("--epics-path", action="append", default=[])
    parser.add_argument("--stories-path", action="append", default=[])
    parser.add_argument("--source-glob", action="append", default=[])
    parser.add_argument("--previous-ledger", default="")
    parser.add_argument("--manifest-out", default="logs/ci/task-generation/source-manifest.v1.json")
    parser.add_argument("--out", default="logs/ci/task-generation/source-blocks.v1.json")
    args = parser.parse_args(argv)
    root = Path(args.repo_root).resolve()
    patterns, explicit = collect_patterns(root, args)
    out = root / args.out
    previous = None
    previous_path = root / args.previous_ledger if args.previous_ledger else out
    if args.mode == "add" and previous_path.is_file():
        previous = json.loads(previous_path.read_text(encoding="utf-8"))
    try:
        manifest, ledger = build_ledger(root, patterns, args.mode, explicit, previous)
    except ValueError as exc:
        print(f"source_ledger_error={exc}")
        return 2
    write_json(root / args.manifest_out, manifest)
    write_json(out, ledger)
    delta = ledger["delta"]
    print(
        f"source_ledger={out} sources={manifest['source_count']} blocks={manifest['block_count']} "
        f"unchanged={len(delta['unchanged'])} changed={len(delta['changed'])} "
        f"added={len(delta['added'])} removed={len(delta['removed'])}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
