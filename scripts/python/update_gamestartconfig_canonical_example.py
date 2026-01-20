#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Update docs/workflows/examples/gamestartconfig-canonical.example.json to match
the project's current character id conventions (Data/characters.json).

This script writes UTF-8 (no BOM) with LF newlines.
"""

from __future__ import annotations

import json
from pathlib import Path


def main() -> int:
    path = Path("docs/workflows/examples/gamestartconfig-canonical.example.json")
    obj = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(obj, dict):
        raise ValueError("Example JSON must be an object.")

    obj["players_count"] = 4
    obj["character_assignments"] = {
        "p1": "c_liu_bei",
        "ai-1": "c_cao_cao",
        "ai-2": "c_sun_quan",
        "ai-3": "c_yuan_shao",
    }

    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\r\n")
    print(f"UPDATED {path.as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
