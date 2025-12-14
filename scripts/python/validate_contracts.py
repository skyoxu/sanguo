#!/usr/bin/env python
"""Validate contract references between overlay docs and Contracts directory.

This script is designed for the newguild Godot + C# template.

Responsibilities:
- Scan overlay 08 docs under docs/architecture/overlays/**/08/.
- Extract contract paths like `Game.Core/Contracts/...cs`.
- Check that referenced contract files exist.
- Optionally detect contracts that are not referenced by any overlay doc.
- Write a JSON report to logs/ci/<YYYY-MM-DD>/contracts-validate.json.

Exit code:
- 0 if no blocking issues are found.
- 1 if missing contract files or docs without any contract references are detected.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List


CONTRACTS_PREFIX = "Game.Core/Contracts/"


def find_overlay_docs(root: Path) -> List[Path]:
    """Return all overlay 08 markdown files under docs/architecture/overlays.

    Only files inside an "08" subdirectory are considered.
    """

    overlays_root = root / "docs" / "architecture" / "overlays"
    if not overlays_root.exists():
        return []

    docs: List[Path] = []
    for prd_dir in overlays_root.iterdir():
        if not prd_dir.is_dir():
            continue
        chapter_dir = prd_dir / "08"
        if not chapter_dir.exists():
            continue
        for md in chapter_dir.glob("*.md"):
            docs.append(md)
    return docs


def extract_contract_paths(md_path: Path) -> List[str]:
    """Extract contract paths from a markdown file.

    Contract references are expected in backticks, e.g.
    `Game.Core/Contracts/Guild/GuildCreated.cs`.
    Returned paths use forward slashes.
    """

    text = md_path.read_text(encoding="utf-8")
    pattern = re.compile(r"`(" + re.escape(CONTRACTS_PREFIX) + r"[^`]+?\.cs)`")
    matches = pattern.findall(text)
    # Deduplicate while preserving order
    seen = set()
    results: List[str] = []
    for m in matches:
        if m not in seen:
            seen.add(m)
            results.append(m)
    return results


def find_all_contract_files(root: Path) -> List[str]:
    """Return all contract .cs files under Game.Core/Contracts.

    Returned paths are relative to project root and use forward slashes.
    """

    contracts_root = root / "Game.Core" / "Contracts"
    if not contracts_root.exists():
        return []

    results: List[str] = []
    for cs_file in contracts_root.rglob("*.cs"):
        rel = cs_file.relative_to(root)
        results.append(rel.as_posix())
    results.sort()
    return results


def build_report(root: Path) -> Dict[str, object]:
    """Build validation report for contracts and overlay docs."""

    overlay_docs = find_overlay_docs(root)

    doc_contracts: Dict[str, List[str]] = {}
    for md in overlay_docs:
        rel_doc = md.relative_to(root).as_posix()
        doc_contracts[rel_doc] = extract_contract_paths(md)

    # Flatten referenced contracts
    referenced_contracts: List[str] = []
    for contracts in doc_contracts.values():
        for c in contracts:
            if c not in referenced_contracts:
                referenced_contracts.append(c)

    all_contracts = find_all_contract_files(root)

    # Contracts that are referenced in docs but missing on disk
    missing_contract_files: List[Dict[str, str]] = []
    for doc, contracts in doc_contracts.items():
        for contract_path in contracts:
            contract_rel = contract_path.replace("\\", "/")
            if not (root / contract_rel).exists():
                missing_contract_files.append(
                    {"doc": doc, "contract": contract_rel}
                )

    # Docs that do not reference any contract at all
    docs_without_contracts = [
        doc for doc, contracts in doc_contracts.items() if not contracts
    ]

    # Contracts that are present on disk but not referenced by any overlay doc
    contracts_without_docs = [
        c for c in all_contracts if c not in referenced_contracts
    ]

    ok = not missing_contract_files

    return {
        "ok": ok,
        "overlay_docs_count": len(overlay_docs),
        "referenced_contracts_count": len(referenced_contracts),
        "all_contracts_count": len(all_contracts),
        "missing_contract_files": missing_contract_files,
        "docs_without_contracts": docs_without_contracts,
        "contracts_without_docs": contracts_without_docs,
    }


def write_report(root: Path, report: Dict[str, object]) -> Path:
    """Write JSON report to logs/ci/<YYYY-MM-DD>/contracts-validate.json."""

    date_str = datetime.now().strftime("%Y-%m-%d")
    out_dir = root / "logs" / "ci" / date_str
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "contracts-validate.json"
    out_path.write_text(
        json.dumps(report, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return out_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Validate that overlay docs reference existing contract files "
            "and that Contracts directory is linked from overlays."
        )
    )
    parser.add_argument(
        "--root",
        default=".",
        help="Project root directory (default: current directory)",
    )

    args = parser.parse_args(argv)
    root = Path(args.root).resolve()

    report = build_report(root)
    out_path = write_report(root, report)

    print(f"Contracts validation report written to: {out_path}")
    if not report.get("ok", False):
        print("Contracts validation detected issues; see JSON report for details.")
        return 1

    print("Contracts validation passed.")
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
