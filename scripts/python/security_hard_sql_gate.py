#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Deterministic hard gate: SQL injection anti-pattern scan (static scan).

This script fails only on clearly unsafe SQL construction patterns:
  - Interpolated SQL strings ($"...") used as SQL statements.
  - string.Format used to build SQL statements.

It does NOT attempt full dataflow analysis.

Scope:
  - Game.Godot/**.cs
  - Game.Core/**.cs
  (excluding bin/obj/.godot/logs)

Exit code:
  0 if ok
  1 if violations found
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


INTERP_CALL_RE = re.compile(r"\.\s*(Query|Execute)\s*\(\s*\$\"", re.IGNORECASE)
FORMAT_CALL_RE = re.compile(r"\.\s*(Query|Execute)\s*\(\s*string\.Format\s*\(", re.IGNORECASE)
INTERP_CMDTEXT_RE = re.compile(r"\bCommandText\s*=\s*\$\"", re.IGNORECASE)
FORMAT_CMDTEXT_RE = re.compile(r"\bCommandText\s*=\s*string\.Format\s*\(", re.IGNORECASE)


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def iter_cs_files(root: Path) -> list[Path]:
    roots = [root / "Game.Godot", root / "Game.Core"]
    files: list[Path] = []
    for r in roots:
        if not r.exists():
            continue
        for p in r.rglob("*.cs"):
            if any(seg in {"bin", "obj", ".godot", "logs"} for seg in p.parts):
                continue
            files.append(p)
    return sorted(files)


def main() -> int:
    ap = argparse.ArgumentParser(description="Hard gate: SQL injection anti-pattern scan (static scan).")
    ap.add_argument("--out", required=True, help="Output JSON path (under logs/ci/... recommended).")
    args = ap.parse_args()

    root = repo_root()
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    violations: list[dict] = []

    for p in iter_cs_files(root):
        text = p.read_text(encoding="utf-8", errors="ignore")
        rel = p.relative_to(root).as_posix()
        for i, line in enumerate(text.splitlines(), start=1):
            s = line.strip()
            if INTERP_CALL_RE.search(s) or INTERP_CMDTEXT_RE.search(s):
                # Allowlist: PRAGMA statements may require whitelisted dynamic tokens (e.g. journal_mode).
                if "PRAGMA " in s.upper():
                    continue
                violations.append({"rule": "no_interpolated_sql_statement", "file": rel, "line": i, "text": s})
                continue
            if FORMAT_CALL_RE.search(s) or FORMAT_CMDTEXT_RE.search(s):
                violations.append({"rule": "no_string_format_sql_statement", "file": rel, "line": i, "text": s})

    ok = len(violations) == 0
    report = {"ok": ok, "violations": violations, "counts": {"total": len(violations)}}
    out_path.write_text(json.dumps(report, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")
    print(f"SECURITY_SQL_GATE status={'ok' if ok else 'fail'} violations={len(violations)}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
