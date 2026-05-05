#!/usr/bin/env python
"""
Sync and template-ize docs/workflows/acceptance-semantics-methodology.md from a sibling repo.

Goals:
- Read/write using UTF-8 (avoid console encoding issues).
- Remove sibling project semantics (e.g., "sanguo", "newguild") and domain-coupled examples.
- Keep paths and rule descriptions aligned with this template repo conventions.
- Produce an audit report under logs/ci/<YYYY-MM-DD>/.

This script is intentionally standard-library-only.
"""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime
from pathlib import Path


DOC_REL_PATH = Path("docs/workflows/acceptance-semantics-methodology.md")
SIBLING_DOC_REL_PATH = Path("docs/workflows/acceptance-semantics-methodology.md")


def _date_dir(root: Path) -> Path:
    return root / "logs" / "ci" / datetime.now().strftime("%Y-%m-%d")


def _read_utf8(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _write_utf8(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def _looks_corrupted(text: str) -> bool:
    # Heuristic: long runs of question marks typically indicate a prior bad console/codepage copy.
    return "????" in text or "???" in text


def _templateize(text: str) -> tuple[str, list[str]]:
    notes: list[str] = []

    # Normalize line endings for consistent diffs.
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    # 1) Remove sibling repo naming.
    # Keep scope tight: only replace obvious repo identifiers, not generic words.
    before = text
    text = re.sub(r"(?i)\\bnewguild\\b", "本模板仓库", text)
    text = re.sub(r"(?i)\\bsanguo\\b", "本模板仓库", text)
    if text != before:
        notes.append("replaced_sibling_repo_names")

    # 2) Replace domain-coupled examples with template-neutral examples.
    replacements = {
        "GuildCreated": "ExampleCreated",
        "SanguoCityBought": "ExamplePurchased",
        "GuildId": "EntityId",
        "公会": "示例模块",
        "三国": "示例模块",
    }
    for src, dst in replacements.items():
        if src in text:
            text = text.replace(src, dst)
            notes.append(f"example_rewrite:{src}->{dst}")

    # 3) Ensure Contracts SSoT wording matches template.
    # If the doc mentions alternative legacy paths, prefer Game.Core/Contracts/**.
    if "Game.Core/Contracts" not in text:
        notes.append("missing_contracts_ssot_reference")

    return text, notes


def _assert_decoupled(text: str) -> list[str]:
    # Hard fail on obvious repo coupling.
    forbidden_patterns = [
        r"(?i)\\bnewguild\\b",
        r"(?i)\\bsanguo\\b",
        r"\\bC:\\\\buildgame\\\\newguild\\b",
        r"\\bC:\\\\buildgame\\\\sanguo\\b",
    ]
    hits: list[str] = []
    for pat in forbidden_patterns:
        if re.search(pat, text):
            hits.append(pat)
    return hits


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Sync acceptance-semantics-methodology.md from a sibling repo and template-ize it."
    )
    parser.add_argument(
        "--root",
        default=".",
        help="Current repo root (default: .)",
    )
    parser.add_argument(
        "--sibling",
        default=r"C:\buildgame\newguild",
        help=r"Sibling repo root (default: C:\buildgame\newguild)",
    )
    parser.add_argument(
        "--fallback-sibling",
        default=r"C:\buildgame\sanguo",
        help=r"Fallback sibling repo root if the primary doc is missing/corrupted (default: C:\buildgame\sanguo)",
    )
    args = parser.parse_args(argv)

    root = Path(args.root).resolve()
    sibling = Path(args.sibling).resolve()
    fallback = Path(args.fallback_sibling).resolve()

    sources_tried: list[str] = []
    src_path = sibling / SIBLING_DOC_REL_PATH
    sources_tried.append(str(src_path))

    source_text: str | None = None
    chosen_source: str | None = None

    if src_path.exists():
        t = _read_utf8(src_path)
        if not _looks_corrupted(t):
            source_text = t
            chosen_source = str(src_path)

    if source_text is None:
        src2 = fallback / SIBLING_DOC_REL_PATH
        sources_tried.append(str(src2))
        if not src2.exists():
            raise FileNotFoundError(
                "Source doc not found in sibling repos: " + " | ".join(sources_tried)
            )
        t2 = _read_utf8(src2)
        if _looks_corrupted(t2):
            raise RuntimeError(
                "Source doc appears corrupted (contains long runs of '?'): " + str(src2)
            )
        source_text = t2
        chosen_source = str(src2)

    out_text, notes = _templateize(source_text)
    forbidden_hits = _assert_decoupled(out_text)

    out_path = root / DOC_REL_PATH
    _write_utf8(out_path, out_text)

    report = {
        "ok": not forbidden_hits,
        "chosen_source": chosen_source,
        "sources_tried": sources_tried,
        "output": str(out_path),
        "notes": notes,
        "forbidden_hits": forbidden_hits,
    }

    out_dir = _date_dir(root)
    out_dir.mkdir(parents=True, exist_ok=True)
    report_path = out_dir / "sync-acceptance-semantics-methodology.json"
    _write_utf8(report_path, json.dumps(report, ensure_ascii=False, indent=2) + "\n")

    # Print ASCII-only summary to avoid terminal codepage issues.
    status = "OK" if report["ok"] else "FAIL"
    print(f"sync_acceptance_semantics_methodology: {status}")
    print(f"source: {chosen_source}")
    print(f"output: {out_path.as_posix()}")
    print(f"report: {report_path.as_posix()}")

    return 0 if report["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
