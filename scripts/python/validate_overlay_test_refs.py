#!/usr/bin/env python3
"""
Validate Test-Refs in an overlay markdown file (deterministic).

Rules (minimal, stop-loss friendly):
  - If the overlay file has no "Test-Refs" section => WARNING (not an error).
  - If a Test-Refs entry contains TODO/TBD => WARNING if the referenced file is missing.
  - Otherwise, a referenced file path must exist on disk => ERROR if missing.

Outputs:
  - Writes a JSON report to --out.
  - Prints a short ASCII summary for log capture.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


HEADING_RE = re.compile(r"^\s*(#{1,6})\s*Test-Refs\b", re.IGNORECASE)
BULLET_RE = re.compile(r"^\s*[-*]\s+(.*)$")
BACKTICK_RE = re.compile(r"`([^`]+)`")


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _to_posix(path: Path) -> str:
    return str(path).replace("\\", "/")


def _extract_test_refs(section_lines: list[str]) -> list[dict]:
    refs: list[dict] = []
    for line in section_lines:
        m = BULLET_RE.match(line)
        if not m:
            continue
        body = m.group(1).strip()
        is_todo = "TODO" in body.upper() or "TBD" in body.upper()
        candidates = BACKTICK_RE.findall(body)
        if candidates:
            for c in candidates:
                refs.append({"raw": body, "path": c.strip(), "todo": is_todo})
        else:
            # No backticks; keep as raw-only (cannot validate path reliably).
            refs.append({"raw": body, "path": None, "todo": is_todo})
    return refs


def _find_test_refs_section(lines: list[str]) -> tuple[int | None, int | None]:
    start = None
    level = None
    for i, line in enumerate(lines):
        m = HEADING_RE.match(line)
        if not m:
            continue
        start = i + 1
        level = len(m.group(1))
        break
    if start is None or level is None:
        return None, None

    end = len(lines)
    for j in range(start, len(lines)):
        m2 = re.match(r"^\s*(#{1,6})\s+", lines[j])
        if not m2:
            continue
        next_level = len(m2.group(1))
        if next_level <= level:
            end = j
            break
    return start, end


def main() -> int:
    ap = argparse.ArgumentParser(description="Validate Test-Refs section for a single overlay markdown file.")
    ap.add_argument("--overlay", required=True, help="Overlay markdown path (repo-relative or absolute).")
    ap.add_argument("--out", required=True, help="Output JSON path (under logs/ci/... recommended).")
    args = ap.parse_args()

    root = repo_root()
    overlay_path = Path(args.overlay)
    if not overlay_path.is_absolute():
        overlay_path = root / overlay_path

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    report = {
        "overlay": _to_posix(overlay_path.relative_to(root)) if overlay_path.exists() else _to_posix(overlay_path),
        "status": "fail",
        "errors": [],
        "warnings": [],
        "refs": [],
    }

    if not overlay_path.exists():
        report["errors"].append("overlay file not found")
        out_path.write_text(json.dumps(report, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")
        print("TEST_REFS status=fail errors=1 warnings=0")
        return 1

    lines = overlay_path.read_text(encoding="utf-8", errors="ignore").splitlines()
    start, end = _find_test_refs_section(lines)
    if start is None or end is None:
        report["status"] = "ok"
        report["warnings"].append("Test-Refs section not found")
        out_path.write_text(json.dumps(report, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")
        print("TEST_REFS status=ok errors=0 warnings=1 (no section)")
        return 0

    section_lines = lines[start:end]
    refs = _extract_test_refs(section_lines)
    report["refs"] = refs

    for r in refs:
        p = r.get("path")
        if not p:
            report["warnings"].append(f"unparseable Test-Refs entry (no backticks): {r.get('raw')}")
            continue
        disk = Path(p)
        if not disk.is_absolute():
            disk = root / disk
        exists = disk.exists()
        r["exists"] = bool(exists)
        if exists:
            continue
        if r.get("todo"):
            report["warnings"].append(f"TODO Test-Refs target missing: {p}")
        else:
            report["errors"].append(f"Test-Refs target missing: {p}")

    report["status"] = "ok" if not report["errors"] else "fail"
    out_path.write_text(json.dumps(report, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")

    print(f"TEST_REFS status={report['status']} errors={len(report['errors'])} warnings={len(report['warnings'])}")
    return 0 if report["status"] == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
