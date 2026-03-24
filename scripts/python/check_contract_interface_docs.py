#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Enforce documentation requirements for contract interfaces.

Rules (hard gate):
- Interface definitions under Game.Core/Contracts/Interfaces/**/*.cs must include XML <summary>.
- Interface definitions must include XML <remarks>.
- Remarks must include at least one ADR reference (ADR-xxxx).
- Remarks must include one overlay reference path under docs/architecture/overlays/.

Output:
  logs/ci/<YYYY-MM-DD>/contract-interface-docs/summary.json
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
from pathlib import Path
from typing import Any


INTERFACE_RE = re.compile(r"\bpublic\s+interface\s+([A-Za-z_][A-Za-z0-9_]*)\b")
SUMMARY_RE = re.compile(r"^\s*///\s*<summary>", re.MULTILINE)
REMARKS_RE = re.compile(r"^\s*///\s*<remarks>", re.MULTILINE)
ADR_RE = re.compile(r"\bADR-\d{4}\b")
OVERLAY_RE = re.compile(r"docs/architecture/overlays/[^\s<>\"`]+")


def _today() -> str:
    return dt.date.today().strftime("%Y-%m-%d")


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _default_out(root: Path) -> Path:
    return root / "logs" / "ci" / _today() / "contract-interface-docs" / "summary.json"


def _iter_interface_files(root: Path, interfaces_dir: Path) -> list[Path]:
    if not interfaces_dir.exists():
        return []
    files: list[Path] = []
    for path in interfaces_dir.rglob("*.cs"):
        if any(seg in {"bin", "obj"} for seg in path.parts):
            continue
        files.append(path)
    return sorted(files)


def _check_file(root: Path, file_path: Path) -> dict[str, Any]:
    text = file_path.read_text(encoding="utf-8", errors="strict")
    rel = file_path.relative_to(root).as_posix()

    interfaces = INTERFACE_RE.findall(text)
    if not interfaces:
        return {
            "file": rel,
            "interfaces": [],
            "status": "skipped",
            "issues": [],
        }

    issues: list[str] = []
    has_summary = bool(SUMMARY_RE.search(text))
    has_remarks = bool(REMARKS_RE.search(text))
    adrs = ADR_RE.findall(text)
    overlays = OVERLAY_RE.findall(text)

    if not has_summary:
        issues.append("missing_xml_summary")
    if not has_remarks:
        issues.append("missing_xml_remarks")
    if not adrs:
        issues.append("missing_adr_reference")
    if not overlays:
        issues.append("missing_overlay_reference")

    return {
        "file": rel,
        "interfaces": interfaces,
        "status": "ok" if not issues else "fail",
        "issues": issues,
        "has_summary": has_summary,
        "has_remarks": has_remarks,
        "adr_refs": sorted(set(adrs)),
        "overlay_refs": sorted(set(overlays)),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Check contract interface XML docs with ADR/Overlay refs.")
    parser.add_argument(
        "--interfaces-dir",
        default="Game.Core/Contracts/Interfaces",
        help="Interface contracts directory relative to repo root",
    )
    parser.add_argument(
        "--out",
        default="",
        help="Optional output summary path",
    )
    args = parser.parse_args()

    root = _repo_root()
    interfaces_dir = (root / args.interfaces_dir).resolve()
    out_path = Path(args.out).resolve() if args.out else _default_out(root)

    if not interfaces_dir.exists():
        summary = {
            "ts": dt.datetime.now(dt.timezone.utc).isoformat(),
            "action": "contract-interface-docs",
            "status": "fail",
            "reason": f"interfaces_dir_not_found: {interfaces_dir.as_posix()}",
            "interfaces_dir": interfaces_dir.as_posix(),
            "counts": {"files": 0, "failed": 0},
            "results": [],
        }
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"CONTRACT_INTERFACE_DOCS status=fail files=0 failed=0 out={out_path.as_posix()}")
        return 1

    results = [_check_file(root, p) for p in _iter_interface_files(root, interfaces_dir)]
    failed_results = [r for r in results if r.get("status") == "fail"]
    status = "ok" if not failed_results else "fail"

    summary = {
        "ts": dt.datetime.now(dt.timezone.utc).isoformat(),
        "action": "contract-interface-docs",
        "status": status,
        "interfaces_dir": interfaces_dir.relative_to(root).as_posix(),
        "counts": {
            "files": len(results),
            "failed": len(failed_results),
        },
        "results": results,
    }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        f"CONTRACT_INTERFACE_DOCS status={status} files={len(results)} "
        f"failed={len(failed_results)} out={out_path.as_posix()}"
    )
    return 0 if status == "ok" else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:  # noqa: BLE001
        print(f"CONTRACT_INTERFACE_DOCS status=fail error={exc}")
        raise SystemExit(2)
