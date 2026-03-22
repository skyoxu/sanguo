#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Validate UTF-8 without BOM for approved text roots.

Default whitelist roots:
- docs
- .github
- .taskmaster
- Game.Core/Contracts

Outputs:
- logs/ci/<YYYY-MM-DD>/docs-utf8-guard/report.json
- logs/ci/<YYYY-MM-DD>/docs-utf8-guard/report.md
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path
from typing import Any


TEXT_EXTENSIONS = {
    ".md",
    ".txt",
    ".json",
    ".yml",
    ".yaml",
    ".xml",
    ".csv",
    ".tsv",
    ".svg",
    ".ps1",
    ".py",
    ".cs",
    ".gd",
    ".tscn",
    ".tres",
    ".cfg",
    ".ini",
    ".toml",
    ".props",
    ".targets",
}

ALLOWED_ROOTS = [
    "docs",
    ".github",
    ".taskmaster",
    "Game.Core/Contracts",
    "AGENTS.md",
]

ALLOWED_FAILURE_PATHS = {
    "docs/architecture/base/ZZZ-encoding-fixture-bad.md",
}


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def today_str() -> str:
    return dt.date.today().strftime("%Y-%m-%d")


def out_dir() -> Path:
    out = repo_root() / "logs" / "ci" / today_str() / "docs-utf8-guard"
    out.mkdir(parents=True, exist_ok=True)
    return out


def write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")


def write_text(path: Path, text: str) -> None:
    path.write_text(text.replace("\r\n", "\n") + "\n", encoding="utf-8", newline="\n")


def is_text_doc(path: Path) -> bool:
    return path.is_file() and path.suffix.lower() in TEXT_EXTENSIONS


def normalize_rel(path: Path, root: Path) -> str:
    return str(path.relative_to(root)).replace("\\", "/")


def ensure_roots_allowed(roots: list[str]) -> tuple[list[str], list[str]]:
    allowed = set(ALLOWED_ROOTS)
    bad = [r for r in roots if r not in allowed]
    return roots, bad


def iter_target_files(root: Path, roots: list[str]) -> list[Path]:
    files: set[Path] = set()
    for rel in roots:
        target = (root / rel).resolve()
        if not target.exists():
            continue
        if target.is_file() and is_text_doc(target):
            files.add(target)
            continue
        if target.is_dir():
            for p in target.rglob("*"):
                if is_text_doc(p):
                    files.add(p)
    return sorted(files)


def check_file(path: Path, root: Path) -> dict[str, Any]:
    raw = path.read_bytes()
    rel = normalize_rel(path, root)
    result = {
        "path": rel,
        "utf8_ok": True,
        "has_bom": raw.startswith(b"\xef\xbb\xbf"),
        "error": None,
    }
    try:
        raw.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        result["utf8_ok"] = False
        result["error"] = f"UnicodeDecodeError: {exc}"
    return result


def validate(root: Path, roots: list[str]) -> dict[str, Any]:
    files = iter_target_files(root, roots)
    details = [check_file(path, root) for path in files]

    decode_errors = [d for d in details if not d["utf8_ok"]]
    bom_errors = [d for d in details if d["has_bom"]]

    allowed_decode = [d for d in decode_errors if d["path"] in ALLOWED_FAILURE_PATHS]
    allowed_bom = [d for d in bom_errors if d["path"] in ALLOWED_FAILURE_PATHS]

    decode_errors = [d for d in decode_errors if d["path"] not in ALLOWED_FAILURE_PATHS]
    bom_errors = [d for d in bom_errors if d["path"] not in ALLOWED_FAILURE_PATHS]

    status = "ok" if not decode_errors and not bom_errors else "fail"
    return {
        "status": status,
        "roots": roots,
        "scanned": len(details),
        "decode_error_count": len(decode_errors),
        "bom_error_count": len(bom_errors),
        "decode_error_paths": [d["path"] for d in decode_errors],
        "bom_error_paths": [d["path"] for d in bom_errors],
        "allowed_failure_paths": sorted(ALLOWED_FAILURE_PATHS),
        "allowed_decode_paths": [d["path"] for d in allowed_decode],
        "allowed_bom_paths": [d["path"] for d in allowed_bom],
        "details": details,
    }


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# UTF-8/BOM Guard Report",
        "",
        f"- status: {report['status']}",
        f"- roots: {', '.join(report['roots'])}",
        f"- scanned: {report['scanned']}",
        f"- decode_error_count: {report['decode_error_count']}",
        f"- bom_error_count: {report['bom_error_count']}",
        f"- allowed_decode_count: {len(report.get('allowed_decode_paths', []))}",
        f"- allowed_bom_count: {len(report.get('allowed_bom_paths', []))}",
        "",
    ]

    allowed_paths = report.get("allowed_decode_paths", []) + report.get("allowed_bom_paths", [])
    if allowed_paths:
        lines.append("## Allowed Failures")
        for path in sorted(set(allowed_paths)):
            lines.append(f"- {path}")
        lines.append("")

    if report["decode_error_paths"]:
        lines.append("## Decode Errors")
        for path in report["decode_error_paths"]:
            lines.append(f"- {path}")
        lines.append("")

    if report["bom_error_paths"]:
        lines.append("## BOM Errors")
        for path in report["bom_error_paths"]:
            lines.append(f"- {path}")
        lines.append("")

    return "\n".join(lines).strip()


def main() -> int:
    ap = argparse.ArgumentParser(description="Validate UTF-8 and BOM policy for approved roots.")
    ap.add_argument(
        "--roots",
        nargs="+",
        default=ALLOWED_ROOTS,
        help="Approved roots to scan. Must be subset of whitelist.",
    )
    args = ap.parse_args()

    root = repo_root()
    roots, bad_roots = ensure_roots_allowed(args.roots)

    out = out_dir()
    report_json = out / "report.json"
    report_md = out / "report.md"

    if bad_roots:
        report = {
            "status": "fail",
            "roots": roots,
            "scanned": 0,
            "decode_error_count": 0,
            "bom_error_count": 0,
            "decode_error_paths": [],
            "bom_error_paths": [],
            "invalid_roots": bad_roots,
            "details": [],
        }
        write_json(report_json, report)
        write_text(report_md, "\n".join([
            "# UTF-8/BOM Guard Report",
            "",
            "- status: fail",
            f"- invalid_roots: {', '.join(bad_roots)}",
        ]))
        print(
            f"DOCS_UTF8_GUARD status=fail scanned=0 decode_errors=0 bom_errors=0 "
            f"invalid_roots={','.join(bad_roots)} out={out}"
        )
        return 1

    report = validate(root, roots)
    write_json(report_json, report)
    write_text(report_md, render_markdown(report))

    print(
        f"DOCS_UTF8_GUARD status={report['status']} scanned={report['scanned']} "
        f"decode_errors={report['decode_error_count']} bom_errors={report['bom_error_count']} out={out}"
    )

    return 0 if report["status"] == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
