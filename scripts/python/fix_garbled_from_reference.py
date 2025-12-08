#!/usr/bin/env python3
"""
Rebuild known garbled documentation files by copying content from a reference
repository (C:\\buildgame\\godotgame by default).

This script is intended for one-off or CI usage when encoding issues have
damaged documentation in this template clone.

It will:
1. Locate the current project root (two levels above this script).
2. Locate the reference root as sibling directory "godotgame".
3. For a fixed list of known garbled doc paths, copy UTF-8 text from the
   reference repo into the current repo.
4. Write an operation log under logs/ci/<timestamp>/encoding-fix/summary.json.

Usage (from project root):
  py -3 scripts/python/fix_garbled_from_reference.py

You can override roots via environment variables:
  ENCODING_FIX_PROJECT_ROOT, ENCODING_FIX_REF_ROOT
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List


# Relative paths of files that should be rebuilt from the reference repository.
# Intentionally excludes docs/architecture/base/ZZZ-encoding-fixture-bad.md
TARGET_FILES: List[str] = [
    "docs/PROJECT_DOCUMENTATION_INDEX.md",
    "docs/migration/MIGRATION_INDEX.md",
    "docs/migration/Phase-11-Scene-Integration-Tests.md",
    "docs/migration/Phase-11-Scene-Integration-Tests-REVISED.md",
    "docs/migration/Phase-14-Godot-Security-Baseline.md",
    "docs/migration/Phase-14-Godot-Security-Backlog.md",
    "docs/architecture/base/06-runtime-view-loops-state-machines-error-paths-v2.md",
]


def resolve_roots() -> Dict[str, Path]:
    script_path = Path(__file__).resolve()

    # scripts/python -> scripts -> project_root
    default_project_root = script_path.parents[2]
    project_root = Path(
        os.environ.get("ENCODING_FIX_PROJECT_ROOT", str(default_project_root))
    ).resolve()

    default_ref_root = project_root.parent / "godotgame"
    ref_root = Path(
        os.environ.get("ENCODING_FIX_REF_ROOT", str(default_ref_root))
    ).resolve()

    return {"project_root": project_root, "ref_root": ref_root}


def copy_file(src: Path, dst: Path) -> Dict[str, str]:
    result: Dict[str, str] = {
        "relative_path": "",
        "source": str(src),
        "destination": str(dst),
        "status": "",
        "error": "",
    }

    result["relative_path"] = str(
        dst.relative_to(dst.parents[0].parents[0]) if "docs" in dst.parts else dst
    )

    if not src.exists():
        result["status"] = "missing_source"
        result["error"] = "Reference file does not exist"
        return result

    try:
        text = src.read_text(encoding="utf-8")
    except Exception as exc:
        result["status"] = "read_error"
        result["error"] = f"{type(exc).__name__}: {exc}"
        return result

    try:
        dst.parent.mkdir(parents=True, exist_ok=True)
        # Write as UTF-8; newline normalization is acceptable for documentation.
        dst.write_text(text, encoding="utf-8", newline="\n")
    except Exception as exc:
        result["status"] = "write_error"
        result["error"] = f"{type(exc).__name__}: {exc}"
        return result

    result["status"] = "copied"
    return result


def main() -> int:
    roots = resolve_roots()
    project_root: Path = roots["project_root"]
    ref_root: Path = roots["ref_root"]

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    out_dir = project_root / "logs" / "ci" / timestamp / "encoding-fix"
    out_dir.mkdir(parents=True, exist_ok=True)

    operations: List[Dict[str, str]] = []

    for rel in TARGET_FILES:
        src = ref_root / rel.replace("/", os.sep)
        dst = project_root / rel.replace("/", os.sep)
        op = copy_file(src, dst)
        operations.append(op)

    summary = {
        "ts": timestamp,
        "project_root": str(project_root),
        "ref_root": str(ref_root),
        "operations": operations,
    }

    summary_path = out_dir / "summary.json"
    with summary_path.open("w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    copied = [op for op in operations if op["status"] == "copied"]
    missing = [op for op in operations if op["status"] == "missing_source"]
    errors = [op for op in operations if op["status"] not in ("copied", "missing_source")]

    print(f"[encoding-fix] project_root={project_root}")
    print(f"[encoding-fix] ref_root={ref_root}")
    print(f"[encoding-fix] operations log: {summary_path}")
    print(
        f"[encoding-fix] copied={len(copied)} "
        f"missing_source={len(missing)} "
        f"errors={len(errors)}"
    )

    if missing:
        print("[encoding-fix] Missing sources:")
        for op in missing:
            print(f"  - {op['relative_path']}: {op['source']}")

    if errors:
        print("[encoding-fix] Errors:")
        for op in errors:
            print(
                f"  - {op['relative_path']}: status={op['status']} "
                f"error={op['error']}"
            )

    # Non-zero exit only if we had hard errors; missing_source is tolerated.
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())

