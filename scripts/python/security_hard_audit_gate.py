#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Deterministic hard gate: security audit logging presence & schema (static scan).

Goal:
  Ensure the repo contains at least one implementation that can emit
  logs/ci/<date>/security-audit.jsonl with the minimum required fields:
    {ts, action, reason, target, caller}

This does NOT prove runtime coverage; it only enforces that the mechanism exists
and uses the expected schema keys somewhere in runtime code.

Exit code:
  0 if ok
  1 if missing
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


AUDIT_FILE_RE = re.compile(r"security-audit\.jsonl", re.IGNORECASE)
REQUIRED_KEYS = ("\"ts\"", "\"action\"", "\"reason\"", "\"target\"", "\"caller\"")


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
    ap = argparse.ArgumentParser(description="Hard gate: security audit logging presence & schema (static scan).")
    ap.add_argument("--out", required=True, help="Output JSON path (under logs/ci/... recommended).")
    args = ap.parse_args()

    root = repo_root()
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    candidates: list[dict] = []

    for p in iter_cs_files(root):
        text = p.read_text(encoding="utf-8", errors="ignore")
        if not AUDIT_FILE_RE.search(text):
            continue
        rel = p.relative_to(root).as_posix()
        missing = [k for k in REQUIRED_KEYS if k not in text]
        candidates.append(
            {
                "file": rel,
                "mentions_audit_file": True,
                "has_all_required_keys": len(missing) == 0,
                "missing_keys": missing,
            }
        )

    ok = any(c.get("has_all_required_keys") for c in candidates)
    report = {"ok": ok, "candidates": candidates, "required_keys": list(REQUIRED_KEYS)}
    out_path.write_text(json.dumps(report, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")
    print(f"SECURITY_AUDIT_GATE status={'ok' if ok else 'fail'} candidates={len(candidates)}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())

