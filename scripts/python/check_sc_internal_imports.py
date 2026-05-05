#!/usr/bin/env python3
"""
Validate scripts/sc internal module wiring.

This is a deterministic "stop-loss" check to prevent broken imports after syncing
scripts between sibling repos. It scans `scripts/sc/*.py` for:
  - `from _<name> import ...`
  - `import _<name>`
and asserts `scripts/sc/_<name>.py` exists.

It does NOT execute any scripts and does NOT require .taskmaster inputs.

Outputs:
  - JSON report to --out

Exit codes:
  - 0: ok
  - 1: missing internal modules
  - 2: unexpected error

Usage (Windows):
  py -3 scripts/python/check_sc_internal_imports.py --out logs/ci/<date>/sc-internal-imports.json
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


# Only match "single-underscore" internal modules (e.g., _taskmaster),
# and explicitly ignore dunder modules like __future__.
FROM_RE = re.compile(r"^\s*from\s+(_(?!_)[A-Za-z0-9_]+)\s+import\s+", re.MULTILINE)
IMPORT_RE = re.compile(r"^\s*import\s+(_(?!_)[A-Za-z0-9_]+)\b", re.MULTILINE)


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def main() -> int:
    ap = argparse.ArgumentParser(description="Check scripts/sc internal module imports.")
    ap.add_argument("--out", required=True, help="Output JSON path.")
    args = ap.parse_args()

    root = repo_root()
    sc_dir = root / "scripts" / "sc"
    out_path = root / args.out
    out_path.parent.mkdir(parents=True, exist_ok=True)

    if not sc_dir.exists():
        payload: dict[str, Any] = {"status": "skipped", "reason": "missing:scripts/sc", "missing": []}
        out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
        return 0

    imports: dict[str, set[str]] = {}
    for py in sc_dir.glob("*.py"):
        if py.name.startswith("__"):
            continue
        text = py.read_text(encoding="utf-8", errors="strict")
        mods = set(FROM_RE.findall(text)) | set(IMPORT_RE.findall(text))
        if mods:
            imports[py.name] = set(mods)

    missing: list[dict[str, Any]] = []
    for src, mods in sorted(imports.items()):
        for mod in sorted(mods):
            expected = sc_dir / f"{mod}.py"
            if not expected.exists():
                missing.append({"source": src, "module": mod, "expected": str(expected.relative_to(root).as_posix())})

    payload = {
        "status": "ok" if not missing else "fail",
        "sc_dir": str(sc_dir.relative_to(root).as_posix()),
        "sc_files_scanned": len(list(sc_dir.glob("*.py"))),
        "imports": {k: sorted(v) for k, v in sorted(imports.items())},
        "missing": missing,
    }
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    return 0 if not missing else 1


if __name__ == "__main__":
    raise SystemExit(main())
