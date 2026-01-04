#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Deterministic (static) check for UI event JSON parsing guards.

Intent:
  Reduce obvious DoS risk when parsing event payload JSON in UI handlers by requiring:
    - A size guard for the parsed string (Length upper bound) near the parse call
    - A MaxDepth configuration somewhere in the file (JsonDocumentOptions/JsonSerializerOptions)

This script is conservative and heuristic; it does NOT prove full safety.

Exit code:
  0 if ok
  1 if violations found
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


PARSE_RE = re.compile(r"\bJsonDocument\.Parse\s*\(\s*([A-Za-z0-9_\.]+)", re.IGNORECASE)
DESER_RE = re.compile(r"\bJsonSerializer\.Deserialize\s*<[^>]+>\s*\(\s*([A-Za-z0-9_\.]+)", re.IGNORECASE)
LENGTH_GUARD_RE = re.compile(r"\.Length\s*(?:>=|>)\s*\d+", re.IGNORECASE)


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def iter_candidate_files(root: Path) -> list[Path]:
    base = root / "Game.Godot"
    if not base.exists():
        return []
    files: list[Path] = []
    for p in base.rglob("*.cs"):
        if any(seg in {"bin", "obj", ".godot", "logs"} for seg in p.parts):
            continue
        # Focus on likely UI/event handlers to minimize noise.
        if "/Scripts/" not in p.as_posix().replace("\\", "/"):
            continue
        files.append(p)
    return sorted(files)


def main() -> int:
    ap = argparse.ArgumentParser(description="Validate UI event JSON parsing guards (static scan).")
    ap.add_argument("--out", required=True, help="Output JSON path (under logs/ci/... recommended).")
    args = ap.parse_args()

    root = repo_root()
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    violations: list[dict] = []

    for p in iter_candidate_files(root):
        text = p.read_text(encoding="utf-8", errors="ignore")
        lines = text.splitlines()
        rel = p.relative_to(root).as_posix()

        has_max_depth = "MaxDepth" in text
        for i, line in enumerate(lines, start=1):
            m = PARSE_RE.search(line) or DESER_RE.search(line)
            if not m:
                continue
            arg = (m.group(1) or "").strip()

            # Require a size guard near the parse call.
            window = lines[max(0, i - 1 - 12) : i - 1]
            guarded = False
            for w in window:
                if arg in w and LENGTH_GUARD_RE.search(w):
                    guarded = True
                    break
                # Allow guarding a local copy, e.g. `var dataJson = ...; if (dataJson.Length > ...)`
                if "Length" in w and LENGTH_GUARD_RE.search(w):
                    guarded = True
                    break

            if not guarded:
                violations.append(
                    {
                        "rule": "json_size_guard_required",
                        "file": rel,
                        "line": i,
                        "arg": arg,
                        "text": line.strip(),
                    }
                )
            if not has_max_depth:
                violations.append(
                    {
                        "rule": "json_max_depth_required",
                        "file": rel,
                        "line": i,
                        "arg": arg,
                        "text": line.strip(),
                    }
                )

    ok = len(violations) == 0
    report = {"ok": ok, "violations": violations, "counts": {"total": len(violations)}}
    out_path.write_text(json.dumps(report, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")
    print(f"UI_EVENT_JSON_GUARDS status={'ok' if ok else 'fail'} violations={len(violations)}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())

