#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Deterministic (static) check for UI domain event source verification.

Intent:
  If an event handler accepts a `source` argument, require that the method body
  references `source` (e.g., allowlist/validation/logging). This reduces obvious
  event spoofing risks noted in security audits.

This is a heuristic. It does NOT prove the source validation is sufficient.

Exit code:
  0 if ok
  1 if violations found
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


METHOD_SIG_RE = re.compile(
    r"^\s*(?:public|private|protected|internal)\s+(?:static\s+)?(?:async\s+)?(?:void|Task(?:<[^>]+>)?)\s+([A-Za-z_][A-Za-z0-9_]*)\s*\((.*?)\)\s*$"
)
HAS_SOURCE_PARAM_RE = re.compile(r"\bstring\s*\??\s*source\b", re.IGNORECASE)


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
        if "/Scripts/" not in p.as_posix().replace("\\", "/"):
            continue
        files.append(p)
    return sorted(files)


def _extract_method_body(lines: list[str], sig_index: int) -> tuple[int, int] | None:
    """
    Return (start_line_index, end_line_index) inclusive indices in `lines`.
    Naive brace matching starting from the signature line.
    """
    brace = 0
    started = False
    start = None
    for i in range(sig_index, min(len(lines), sig_index + 400)):
        line = lines[i]
        if "{" in line:
            brace += line.count("{")
            if not started:
                started = True
                start = i
        if "}" in line and started:
            brace -= line.count("}")
            if brace <= 0 and start is not None:
                return (start, i)
    return None


def main() -> int:
    ap = argparse.ArgumentParser(description="Validate UI event source verification (static scan).")
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

        for idx, line in enumerate(lines):
            m = METHOD_SIG_RE.match(line)
            if not m:
                continue
            params = m.group(2) or ""
            if not HAS_SOURCE_PARAM_RE.search(params):
                continue

            body = _extract_method_body(lines, idx)
            if not body:
                continue
            start, end = body
            body_text = "\n".join(lines[start + 1 : end])
            # Require at least one usage of the identifier in the body (beyond signature).
            if re.search(r"\bsource\b", body_text) is None:
                violations.append(
                    {
                        "rule": "event_source_must_be_used",
                        "file": rel,
                        "line": idx + 1,
                        "method": m.group(1),
                        "text": line.strip(),
                    }
                )

    ok = len(violations) == 0
    report = {"ok": ok, "violations": violations, "counts": {"total": len(violations)}}
    out_path.write_text(json.dumps(report, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")
    print(f"UI_EVENT_SOURCE_VERIFY status={'ok' if ok else 'fail'} violations={len(violations)}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())

