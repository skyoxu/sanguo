#!/usr/bin/env python3
"""
Validate docs/workflows/_index.md consistency (hard gate).
Ensures every *.md under docs/workflows is listed in _index.md and no extra entries exist.
Writes evidence into logs/ci/<YYYY-MM-DD>/.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from pathlib import Path


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _collect_workflow_files(workflows_dir: Path) -> set[str]:
    files = set()
    for path in workflows_dir.glob("*.md"):
        if path.name == "_index.md":
            continue
        files.add(path.name)
    return files


def _parse_index(index_path: Path) -> set[str]:
    text = _read_text(index_path)
    matches = re.findall(r"`([^`]+\.md)`", text)
    return set(matches)


def _write_logs(out_dir: Path, payload: dict) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    log_txt = out_dir / "workflows-index-validate.log"
    log_json = out_dir / "workflows-index-validate.json"
    log_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")

    lines = []
    lines.append(f"WORKFLOWS_INDEX_VALIDATE missing={len(payload['missing'])} extra={len(payload['extra'])}")
    if payload["missing"]:
        lines.append(f"MISSING: {', '.join(sorted(payload['missing']))}")
    if payload["extra"]:
        lines.append(f"EXTRA: {', '.join(sorted(payload['extra']))}")
    log_txt.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--workflows-dir", default="docs/workflows")
    args = ap.parse_args()

    workflows_dir = Path(args.workflows_dir)
    index_path = workflows_dir / "_index.md"

    today = dt.date.today().strftime("%Y-%m-%d")
    out_dir = Path("logs") / "ci" / today

    if not workflows_dir.exists():
        payload = {"missing": [], "extra": [], "error": f"missing_dir:{workflows_dir.as_posix()}"}
        _write_logs(out_dir, payload)
        print(f"WORKFLOWS_INDEX_VALIDATE fail reason=missing_dir:{workflows_dir.as_posix()}")
        return 1

    if not index_path.exists():
        payload = {"missing": [], "extra": [], "error": f"missing_index:{index_path.as_posix()}"}
        _write_logs(out_dir, payload)
        print(f"WORKFLOWS_INDEX_VALIDATE fail reason=missing_index:{index_path.as_posix()}")
        return 1

    actual = _collect_workflow_files(workflows_dir)
    listed = _parse_index(index_path)

    missing = sorted(actual - listed)
    extra = sorted(listed - actual)

    payload = {"missing": missing, "extra": extra}
    _write_logs(out_dir, payload)

    print(f"WORKFLOWS_INDEX_VALIDATE missing={len(missing)} extra={len(extra)}")
    return 1 if missing or extra else 0


if __name__ == "__main__":
    raise SystemExit(main())
