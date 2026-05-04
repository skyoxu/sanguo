#!/usr/bin/env python3
"""
Sync task-semantics gate scripts/docs from a sibling project repo.

Goals:
- Copy files referenced by docs/workflows/task-semantics-gates-evolution.md
  from the source repo into this template repo.
- Decouple any project-specific semantics in copied Markdown (UTF-8).
- Keep a reproducible audit report under logs/ci/<date>/.

Notes:
- This template repo may not include real .taskmaster/tasks/*.json; the synced
  scripts are allowed to fail fast when required inputs are missing.
- This tool does not install dependencies or access the network.

Usage (Windows):
  py -3 scripts/python/sync_task_semantics_assets_from_sibling_repo.py --source-root ..\\<project>
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any, Iterable


TEXT_EXTS = {".py", ".md", ".txt", ".yml", ".yaml", ".json", ".csv", ".xml"}


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def today_str() -> str:
    return date.today().isoformat()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def read_bytes(path: Path) -> bytes:
    return path.read_bytes()


def write_bytes(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def read_text_utf8(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="strict")


def write_text_utf8(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def extract_referenced_paths(md_text: str) -> list[str]:
    pat = re.compile(
        r"(?i)((?:scripts|docs|\.github)/[A-Za-z0-9_./-]+\.(?:py|md|txt|yml|yaml|json|csv|xml))"
    )
    paths = sorted(set(m.group(1) for m in pat.finditer(md_text)))
    return paths


def extract_llm_glob_patterns(md_text: str) -> list[str]:
    # Typical patterns: scripts/sc/llm_*.py
    pat = re.compile(r"(?i)(scripts/sc/llm_[A-Za-z0-9_*?-]+\.py)")
    raw = set(m.group(1) for m in pat.finditer(md_text))
    patterns: set[str] = set()
    for s in raw:
        # Keep only sane ASCII globs.
        s2 = "".join(ch for ch in s if ord(ch) < 128)
        patterns.add(s2)
    return sorted(patterns)


def expand_globs(source_root: Path, patterns: Iterable[str]) -> list[str]:
    out: set[str] = set()
    for pat in patterns:
        if "*" not in pat and "?" not in pat:
            continue
        matches = source_root.glob(pat)
        for m in matches:
            if m.is_file():
                out.add(m.as_posix())
    # Convert to repo-relative (scripts/...)
    rels = []
    for ap in sorted(out):
        try:
            rel = str(Path(ap).relative_to(source_root).as_posix())
        except Exception:
            # source_root.glob already yields absolute paths on Windows
            rel = ap
        rels.append(rel)
    return sorted(set(rels))


def decouple_markdown(text: str) -> tuple[str, list[dict[str, Any]]]:
    """
    Remove obvious project-name semantics from docs.
    This is not a translation tool; it applies targeted substitutions.
    """

    changes: list[dict[str, Any]] = []

    rules: list[tuple[str, str, str]] = [
        # Local path examples: keep the pattern but remove the concrete sibling name.
        (r"C:\\\\buildgame\\\\[A-Za-z0-9_-]+", r"C:\\buildgame\\<project>", "path:C:\\buildgame\\<name>-><project>"),
        # Common doc examples: replace domain folder names with a placeholder.
        (r"Game\\.Core/Contracts/[A-Z][A-Za-z0-9_-]+/", "Game.Core/Contracts/<Domain>/", "path:Contracts/<Name>/-><Domain>/"),
        (r"Tests\\.Godot/tests/Scenes/[A-Z][A-Za-z0-9_-]+/", "Tests.Godot/tests/Scenes/<Domain>/", "path:Scenes/<Name>/-><Domain>/"),
    ]

    out = text
    for pat, repl, name in rules:
        out2, n = re.subn(pat, repl, out)
        if n:
            changes.append({"rule": name, "count": n})
            out = out2

    return out, changes


@dataclass
class SyncRow:
    path: str
    action: str
    reason: str
    source_sha256: str | None = None
    target_sha256: str | None = None
    decouple_changes: list[dict[str, Any]] | None = None


def main() -> int:
    ap = argparse.ArgumentParser(description="Sync task-semantics assets from sibling repo and decouple docs.")
    ap.add_argument(
        "--source-root",
        default=None,
        help="Path to source repo directory. If omitted, auto-detect a sibling repo under repo parent.",
    )
    ap.add_argument(
        "--doc",
        default="docs/workflows/task-semantics-gates-evolution.md",
        help="Doc file used as the source-of-truth for referenced assets.",
    )
    ap.add_argument(
        "--out-dir",
        default=None,
        help="Output directory for report (default: logs/ci/<date>/sync-task-semantics-assets).",
    )
    args = ap.parse_args()

    root = repo_root()
    source_root = None
    if args.source_root:
        source_root = (root / args.source_root).resolve()
    else:
        # Auto-detect: find sibling dirs that look like a repo and contain at least one expected path.
        candidates: list[Path] = []
        parent = root.parent
        expected_any = [
            Path("scripts/sc/build.py"),
            Path("scripts/sc/build/tdd.py"),
            Path("scripts/sc/acceptance_check.py"),
            Path("scripts/python/validate_acceptance_refs.py"),
            Path("docs/workflows/task-semantics-gates-evolution.md"),
        ]
        for child in parent.iterdir():
            if not child.is_dir():
                continue
            if child.resolve() == root.resolve():
                continue
            if not (child / ".git").exists():
                continue
            if any((child / rel).exists() for rel in expected_any):
                candidates.append(child)
        if len(candidates) == 1:
            source_root = candidates[0].resolve()
        else:
            msg = {
                "error": "cannot_auto_detect_source_root",
                "hint": "Pass --source-root ..\\\\<project> explicitly.",
                "candidates": [str(c) for c in candidates],
            }
            out_dir = root / "logs" / "ci" / today_str() / "sync-task-semantics-assets"
            out_dir.mkdir(parents=True, exist_ok=True)
            write_text_utf8(out_dir / "report.json", json.dumps(msg, ensure_ascii=False, indent=2) + "\n")
            return 2
    doc_path = root / args.doc

    out_dir = Path(args.out_dir) if args.out_dir else (root / "logs" / "ci" / today_str() / "sync-task-semantics-assets")
    out_dir.mkdir(parents=True, exist_ok=True)

    if not source_root or not source_root.exists():
        write_text_utf8(out_dir / "report.json", json.dumps({"error": f"source_root missing: {source_root}"}, ensure_ascii=False, indent=2) + "\n")
        return 2

    md = read_text_utf8(doc_path)
    referenced = extract_referenced_paths(md)
    llm_patterns = extract_llm_glob_patterns(md)
    expanded = expand_globs(source_root, llm_patterns)

    # Merge and normalize to repo-relative paths.
    all_paths = sorted(set(referenced) | set(expanded))

    rows: list[SyncRow] = []
    skipped_missing_source: list[str] = []

    for rel in all_paths:
        target = root / rel
        source = source_root / rel

        if not source.exists():
            skipped_missing_source.append(rel)
            rows.append(SyncRow(path=rel, action="skip", reason="missing_in_source"))
            continue

        # Copy directory structure if needed.
        if source.is_dir():
            rows.append(SyncRow(path=rel, action="skip", reason="source_is_dir"))
            continue

        src_bytes = read_bytes(source)
        src_sha = sha256_bytes(src_bytes)
        tgt_sha = sha256_bytes(read_bytes(target)) if target.exists() else None

        if tgt_sha == src_sha:
            rows.append(SyncRow(path=rel, action="keep", reason="same_bytes", source_sha256=src_sha, target_sha256=tgt_sha))
            continue

        # For text files, normalize docs and enforce UTF-8 writes for markdown.
        decouple_changes: list[dict[str, Any]] | None = None
        if source.suffix.lower() in TEXT_EXTS:
            try:
                src_text = source.read_text(encoding="utf-8", errors="strict")
            except Exception:
                # fall back to byte copy if not strict utf-8
                write_bytes(target, src_bytes)
                rows.append(SyncRow(path=rel, action="copy", reason="copied_bytes_non_utf8", source_sha256=src_sha, target_sha256=tgt_sha))
                continue

            out_text = src_text
            # Strip UTF-8 BOM if it exists in the source text file to avoid Python parsing issues.
            if out_text.startswith("\ufeff"):
                out_text = out_text.lstrip("\ufeff")
            if source.suffix.lower() == ".md":
                out_text, decouple_changes = decouple_markdown(out_text)
                write_text_utf8(target, out_text)
            else:
                # keep as-is, but normalize newline to '\n' for determinism
                write_text_utf8(target, out_text.replace("\r\n", "\n"))

            rows.append(
                SyncRow(
                    path=rel,
                    action="copy",
                    reason="copied_text",
                    source_sha256=src_sha,
                    target_sha256=tgt_sha,
                    decouple_changes=decouple_changes,
                )
            )
            continue

        # Binary or unknown extension: copy bytes.
        write_bytes(target, src_bytes)
        rows.append(SyncRow(path=rel, action="copy", reason="copied_bytes", source_sha256=src_sha, target_sha256=tgt_sha))

    report = {
        "source_root": str(source_root),
        "target_root": str(root),
        "doc": str(doc_path),
        "referenced_count": len(referenced),
        "llm_patterns": llm_patterns,
        "expanded_llm_count": len(expanded),
        "total_paths": len(all_paths),
        "skipped_missing_source": skipped_missing_source,
        "rows": [r.__dict__ for r in rows],
    }

    write_text_utf8(out_dir / "report.json", json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
