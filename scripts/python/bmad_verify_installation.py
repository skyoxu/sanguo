#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
bmad_verify_installation

Goal:
  Verify BMAD (core + expansion pack) is available on this machine, and emit a
  reproducible audit artifact under logs/ci/<YYYY-MM-DD>/bmad-verify/.

This does NOT download or modify anything. It is a local verification helper.

Checks:
  - Find an ancestor directory containing ".bmad-core/install-manifest.yaml"
  - Optionally verify ".bmad-godot-game-dev/install-manifest.yaml" exists

Usage (Windows, PowerShell):
  py -3 scripts/python/bmad_verify_installation.py
  py -3 scripts/python/bmad_verify_installation.py --require-expansion bmad-godot-game-dev
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path
from typing import Any


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def today_str() -> str:
    return dt.date.today().strftime("%Y-%m-%d")


def ci_out_dir(name: str) -> Path:
    out = repo_root() / "logs" / "ci" / today_str() / name
    out.mkdir(parents=True, exist_ok=True)
    return out


def write_json(path: Path, obj: Any) -> None:
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")


def _find_bmad_root(start: Path) -> Path | None:
    cur = start.resolve()
    for _ in range(30):
        if (cur / ".bmad-core" / "install-manifest.yaml").is_file():
            return cur
        parent = cur.parent
        if parent == cur:
            break
        cur = parent
    return None


def main() -> int:
    ap = argparse.ArgumentParser(description="Verify local BMAD installation (core + optional expansion pack).")
    ap.add_argument(
        "--require-expansion",
        default="",
        help="Fail if this expansion pack is not found (e.g. bmad-godot-game-dev).",
    )
    args = ap.parse_args()

    out_dir = ci_out_dir("bmad-verify")
    root = repo_root()
    bmad_root = _find_bmad_root(root)

    result: dict[str, Any] = {
        "cmd": "bmad_verify_installation",
        "date": today_str(),
        "repo_root": str(root),
        "bmad_root": str(bmad_root) if bmad_root else None,
        "core_manifest": None,
        "expansion": {},
        "status": "ok",
        "warnings": [],
    }

    if not bmad_root:
        result["status"] = "warn"
        result["warnings"].append("bmad_core_not_found_in_ancestors")
        write_json(out_dir / "summary.json", result)
        print(f"BMAD_VERIFY status={result['status']} out={out_dir}")
        return 0

    core_manifest = bmad_root / ".bmad-core" / "install-manifest.yaml"
    result["core_manifest"] = str(core_manifest)

    require = str(args.require_expansion or "").strip()
    if require:
        exp_manifest = bmad_root / f".{require}" / "install-manifest.yaml"
        exists = exp_manifest.is_file()
        result["expansion"][require] = {"manifest": str(exp_manifest), "exists": bool(exists)}
        if not exists:
            result["status"] = "fail"
            result["warnings"].append(f"required_expansion_missing:{require}")

    write_json(out_dir / "summary.json", result)
    print(f"BMAD_VERIFY status={result['status']} out={out_dir}")
    return 0 if result["status"] != "fail" else 1


if __name__ == "__main__":
    raise SystemExit(main())

