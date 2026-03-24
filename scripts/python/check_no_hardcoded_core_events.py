#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Hard gate: forbid hardcoded "core.*" event string literals in C# code,
except inside contract definition files.

Allowed files:
  - Game.Core/Contracts/EventTypes.cs
  - Game.Core/Contracts/DomainEvent.cs

Target scopes:
  - Game.Core/**/*.cs
  - Game.Godot/**/*.cs

Output:
  logs/ci/<YYYY-MM-DD>/no-hardcoded-core-events/summary.json
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
from pathlib import Path
from typing import Any


CORE_EVENT_LITERAL_RE = re.compile(r'"(core\.[a-z0-9_.-]+)"')

ALLOWED_FILES = {
    "Game.Core/Contracts/EventTypes.cs",
    "Game.Core/Contracts/DomainEvent.cs",
}

DEFAULT_GLOBS = [
    "Game.Core/**/*.cs",
    "Game.Godot/**/*.cs",
]


def _today_str() -> str:
    return dt.date.today().strftime("%Y-%m-%d")


def _posix(path: Path) -> str:
    return str(path).replace("\\", "/")


def _strip_comments(line: str) -> str:
    # Keep simple and conservative: remove line comments.
    idx = line.find("//")
    if idx >= 0:
        return line[:idx]
    return line


def _scan_file(repo_root: Path, file_path: Path) -> list[dict[str, Any]]:
    rel = _posix(file_path.relative_to(repo_root))
    if rel in ALLOWED_FILES or rel.startswith("Game.Core/Contracts/"):
        return []

    violations: list[dict[str, Any]] = []
    text = file_path.read_text(encoding="utf-8")
    for lineno, raw_line in enumerate(text.splitlines(), start=1):
        line = _strip_comments(raw_line)
        for match in CORE_EVENT_LITERAL_RE.finditer(line):
            violations.append(
                {
                    "path": rel,
                    "line": lineno,
                    "event": match.group(1),
                    "message": "Use Game.Core.Contracts.EventTypes constant instead of hardcoded core.* string",
                }
            )
    return violations


def main() -> int:
    parser = argparse.ArgumentParser(description="Hard gate for hardcoded core.* event literals")
    parser.add_argument("--out", default="", help="Optional summary output path")
    args = parser.parse_args()

    repo_root = Path.cwd().resolve()
    files: set[Path] = set()
    for pattern in DEFAULT_GLOBS:
        files.update((repo_root / ".").glob(pattern))

    violations: list[dict[str, Any]] = []
    scanned = 0
    for file_path in sorted(files):
        if not file_path.is_file():
            continue
        scanned += 1
        violations.extend(_scan_file(repo_root, file_path))

    out_default = Path("logs") / "ci" / _today_str() / "no-hardcoded-core-events" / "summary.json"
    out_path = Path(args.out) if args.out else out_default
    out_path.parent.mkdir(parents=True, exist_ok=True)

    summary = {
        "ts": dt.datetime.now(dt.timezone.utc).isoformat(),
        "action": "no-hardcoded-core-events",
        "reason": "enforce EventTypes constant usage for core.* events",
        "allowed_files": sorted(ALLOWED_FILES),
        "scanned": scanned,
        "failed": len(violations),
        "violations": violations,
    }
    out_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    status = "ok" if len(violations) == 0 else "fail"
    print(f"NO_HARDCODED_CORE_EVENTS status={status} scanned={scanned} failed={len(violations)} out={_posix(out_path)}")
    for item in violations[:30]:
        print(f" - {item['path']}:{item['line']} event={item['event']}")

    return 0 if len(violations) == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
