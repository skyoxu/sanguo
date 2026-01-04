#!/usr/bin/env python3
"""
Deterministic architecture boundary checks (Windows friendly).

Checks:
  1) Game.Core source code must not reference Godot APIs (using Godot / Godot.).
  2) Game.Core.csproj must not reference Godot-related packages or outer-layer projects.

Outputs:
  - Writes a JSON report to the path provided by --out.
  - Prints a short ASCII summary to stdout for log capture.
"""

from __future__ import annotations

import argparse
import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _to_posix(path: Path) -> str:
    return str(path).replace("\\", "/")


def scan_core_sources(root: Path) -> list[str]:
    core_dir = root / "Game.Core"
    if not core_dir.exists():
        return []

    violations: list[str] = []
    for p in core_dir.rglob("*.cs"):
        if any(seg in {"bin", "obj"} for seg in p.parts):
            continue
        text = p.read_text(encoding="utf-8", errors="ignore")
        if "using Godot" in text or "Godot." in text:
            violations.append(_to_posix(p.relative_to(root)))
    return violations


def _strip_ns(tag: str) -> str:
    return tag.split("}", 1)[-1]


def scan_core_csproj(root: Path) -> dict:
    csproj = root / "Game.Core" / "Game.Core.csproj"
    if not csproj.exists():
        return {
            "csproj": None,
            "status": "skipped",
            "reason": "Game.Core/Game.Core.csproj not found",
            "forbidden_project_refs": [],
            "forbidden_package_refs": [],
            "project_refs": [],
            "package_refs": [],
        }

    project_refs: list[str] = []
    package_refs: list[str] = []
    parse_error: str | None = None
    try:
        tree = ET.parse(csproj)
        root_el = tree.getroot()
        for elem in root_el.iter():
            tag = _strip_ns(elem.tag)
            if tag == "ProjectReference":
                inc = (elem.attrib.get("Include") or "").strip()
                if inc:
                    project_refs.append(inc)
            if tag == "PackageReference":
                inc = (elem.attrib.get("Include") or elem.attrib.get("Update") or "").strip()
                if inc:
                    package_refs.append(inc)
    except ET.ParseError as exc:
        parse_error = str(exc)

    forbidden_project_refs: list[str] = []
    for inc in project_refs:
        name = Path(inc.replace("\\", "/")).name.lower()
        if "godot" in name:
            forbidden_project_refs.append(inc)

    forbidden_package_refs: list[str] = []
    for inc in package_refs:
        name = inc.strip().lower()
        if name == "godot" or name.startswith("godot"):
            forbidden_package_refs.append(inc)

    return {
        "csproj": _to_posix(csproj.relative_to(root)),
        "status": "ok" if not parse_error else "fail",
        "parse_error": parse_error,
        "project_refs": project_refs,
        "package_refs": package_refs,
        "forbidden_project_refs": forbidden_project_refs,
        "forbidden_package_refs": forbidden_package_refs,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Check Game.Core architecture boundary constraints.")
    ap.add_argument("--out", required=True, help="Output JSON path (under logs/ci/... recommended).")
    args = ap.parse_args()

    root = repo_root()
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    source_violations = scan_core_sources(root)
    csproj_report = scan_core_csproj(root)

    ok = True
    errors: list[str] = []

    if source_violations:
        ok = False
        errors.append("Game.Core source references Godot APIs (forbidden).")

    if csproj_report.get("status") == "fail":
        ok = False
        errors.append(f"Failed to parse {csproj_report.get('csproj')} (invalid XML).")

    if csproj_report.get("forbidden_project_refs"):
        ok = False
        errors.append("Game.Core.csproj has forbidden ProjectReference(s) containing 'godot'.")

    if csproj_report.get("forbidden_package_refs"):
        ok = False
        errors.append("Game.Core.csproj has forbidden PackageReference(s) starting with 'Godot'.")

    report = {
        "ok": ok,
        "errors": errors,
        "source_violations": source_violations,
        "csproj": csproj_report,
    }

    out_path.write_text(json.dumps(report, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")

    print(f"ARCH_BOUNDARY status={'ok' if ok else 'fail'} source_violations={len(source_violations)}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())

