#!/usr/bin/env python3
"""
Hard gate for repository line-ending policy.

Policy:
- Text files must not use CRLF in working tree, except approved extensions.
- Approved CRLF extensions default to: .ps1, .bat, .cmd

Windows usage:
  py -3 scripts/python/check_line_endings.py
  py -3 scripts/python/check_line_endings.py --summary-out logs/ci/2026-03-16/line-endings-summary.json
"""

from __future__ import annotations

import argparse
import datetime as dt
import io
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass


@dataclass
class EolEntry:
    path: str
    i_eol: str
    w_eol: str
    attr: str
    ext: str


def _run_git_ls_files_eol(repo_root: str) -> tuple[int, str]:
    proc = subprocess.run(
        ["git", "ls-files", "--eol"],
        cwd=repo_root,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return proc.returncode, proc.stdout


def _parse_entries(raw: str) -> list[EolEntry]:
    entries: list[EolEntry] = []
    for line in raw.splitlines():
        if "\t" not in line:
            continue
        meta, path = line.split("\t", 1)
        if "text" not in meta:
            continue
        # skip explicit binary markers
        if "attr/-text" in meta or "i/-text" in meta or "w/-text" in meta:
            continue
        i_match = re.search(r"\bi/([a-z-]+)\b", meta, flags=re.IGNORECASE)
        w_match = re.search(r"\bw/([a-z-]+)\b", meta, flags=re.IGNORECASE)
        attr_match = re.search(r"\battr/([^\s]+)\b", meta, flags=re.IGNORECASE)
        i_eol = (i_match.group(1).lower() if i_match else "unknown")
        w_eol = (w_match.group(1).lower() if w_match else "unknown")
        attr = (attr_match.group(1) if attr_match else "unknown")
        ext = os.path.splitext(path)[1].lower()
        entries.append(EolEntry(path=path, i_eol=i_eol, w_eol=w_eol, attr=attr, ext=ext))
    return entries


def _default_summary_path() -> str:
    date = dt.date.today().strftime("%Y-%m-%d")
    return os.path.join("logs", "ci", date, "line-endings-summary.json")


def _write_json(path: str, payload: dict) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with io.open(path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
        f.write("\n")


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate repository line-ending policy.")
    parser.add_argument("--repo-root", default=".", help="Repository root path.")
    parser.add_argument(
        "--allow-crlf-ext",
        default=".ps1,.bat,.cmd",
        help="Comma-separated extension allowlist for CRLF.",
    )
    parser.add_argument("--summary-out", default=_default_summary_path(), help="Summary JSON output path.")
    args = parser.parse_args()

    repo_root = os.path.abspath(args.repo_root)
    allow_crlf_ext = {
        ext.strip().lower()
        for ext in str(args.allow_crlf_ext).split(",")
        if ext.strip()
    }

    rc, out = _run_git_ls_files_eol(repo_root)
    if rc != 0:
        payload = {
            "status": "fail",
            "reason": "git ls-files --eol failed",
            "rc": rc,
            "allow_crlf_ext": sorted(allow_crlf_ext),
        }
        _write_json(args.summary_out, payload)
        print(f"LINE_ENDINGS status=fail rc={rc} reason=git_ls_files_failed")
        return 1

    entries = _parse_entries(out)
    violations: list[dict] = []
    checked = 0

    for item in entries:
        checked += 1
        if item.w_eol in ("-text", "unknown"):
            continue
        if item.ext in allow_crlf_ext:
            continue
        if item.w_eol in ("crlf", "mixed"):
            violations.append(
                {
                    "path": item.path,
                    "w_eol": item.w_eol,
                    "i_eol": item.i_eol,
                    "attr": item.attr,
                    "ext": item.ext,
                    "reason": "unexpected_crlf_or_mixed",
                }
            )

    payload = {
        "status": "ok" if not violations else "fail",
        "checked": checked,
        "violations": violations,
        "violations_count": len(violations),
        "allow_crlf_ext": sorted(allow_crlf_ext),
    }
    _write_json(args.summary_out, payload)

    if violations:
        print(
            f"LINE_ENDINGS status=fail checked={checked} violations={len(violations)} summary={args.summary_out}"
        )
        for row in violations[:50]:
            print(f"  - {row['path']} (w={row['w_eol']}, ext={row['ext']})")
        if len(violations) > 50:
            print(f"  ... ({len(violations) - 50} more)")
        return 1

    print(f"LINE_ENDINGS status=ok checked={checked} violations=0 summary={args.summary_out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

