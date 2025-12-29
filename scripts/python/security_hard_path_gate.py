#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Deterministic hard gate: path safety invariants (static scan).

This script is intentionally conservative: it fails only on clearly unsafe patterns.
It does NOT prove that "100% of paths are validated".

Hard checks:
  1) Disallow absolute Windows drive path literals in runtime code (e.g. "C:\\...").
  2) Disallow path traversal literals ("../" or "..\\") in runtime code.
  3) ProjectSettings.GlobalizePath(...) must only be called with "user://" or "res://".

Scope (runtime code):
  - Game.Godot/** (excluding bin/obj/.godot/logs)
  - Game.Core/**  (excluding bin/obj/.godot/logs)

Exit code:
  0 if ok
  1 if violations found
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


ABS_WIN_PATH_RE = re.compile(r'"[A-Za-z]:\\\\[^"]+"')
TRAVERSAL_RE = re.compile(r'"[^"]*(?:\.\./|\.\.\\)[^"]*"')
GLOBALIZE_RE = re.compile(r"\bProjectSettings\.GlobalizePath\s*\(\s*\"([^\"]+)\"\s*\)")


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def iter_runtime_files(root: Path) -> list[Path]:
    roots = [root / "Game.Godot", root / "Game.Core"]
    files: list[Path] = []
    for r in roots:
        if not r.exists():
            continue
        for p in r.rglob("*"):
            if not p.is_file():
                continue
            if p.suffix.lower() not in {".cs", ".gd"}:
                continue
            if any(seg in {"bin", "obj", ".godot", "logs"} for seg in p.parts):
                continue
            files.append(p)
    return sorted(files)


def main() -> int:
    ap = argparse.ArgumentParser(description="Hard gate: path safety invariants (static scan).")
    ap.add_argument("--out", required=True, help="Output JSON path (under logs/ci/... recommended).")
    args = ap.parse_args()

    root = repo_root()
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    violations: list[dict] = []

    for p in iter_runtime_files(root):
        text = p.read_text(encoding="utf-8", errors="ignore")
        rel = p.relative_to(root).as_posix()

        for i, line in enumerate(text.splitlines(), start=1):
            if ABS_WIN_PATH_RE.search(line):
                violations.append({"rule": "no_absolute_windows_path_literal", "file": rel, "line": i, "text": line.strip()})
            # Only consider traversal tokens when the line appears to deal with filesystem paths.
            # (Scene tree NodePath like "../Root" is not a filesystem traversal.)
            if any(
                t in line
                for t in (
                    "System.IO.",
                    "File.",
                    "Directory.",
                    "Path.",
                    "FileAccess.",
                    "DirAccess.",
                    "ProjectSettings.GlobalizePath",
                    "GetFolderPath",
                )
            ):
                if TRAVERSAL_RE.search(line):
                    violations.append({"rule": "no_path_traversal_literal", "file": rel, "line": i, "text": line.strip()})

            m = GLOBALIZE_RE.search(line)
            if m:
                arg = (m.group(1) or "").strip()
                if not (arg.startswith("user://") or arg.startswith("res://")):
                    violations.append(
                        {
                            "rule": "globalize_path_only_user_or_res",
                            "file": rel,
                            "line": i,
                            "text": line.strip(),
                            "arg": arg,
                        }
                    )

    ok = len(violations) == 0
    report = {"ok": ok, "violations": violations, "counts": {"total": len(violations)}}
    out_path.write_text(json.dumps(report, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")
    print(f"SECURITY_PATH_GATE status={'ok' if ok else 'fail'} violations={len(violations)}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
