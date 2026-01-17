#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import argparse
import datetime as dt
import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class NormalizedResult:
    path: str
    changed: bool
    bytes_before: int
    bytes_after: int


def _today_ci_dir() -> Path:
    date = dt.date.today().strftime("%Y-%m-%d")
    return Path("logs") / "ci" / date / "normalize-eol-crlf"


def _normalize_to_crlf_utf8(path: Path) -> NormalizedResult:
    before_bytes = path.read_bytes()
    text = before_bytes.decode("utf-8", errors="strict")
    normalized = text.replace("\r\n", "\n").replace("\n", "\r\n")
    after_bytes = normalized.encode("utf-8")
    changed = before_bytes != after_bytes
    if changed:
        path.write_bytes(after_bytes)
    return NormalizedResult(
        path=str(path).replace("\\", "/"),
        changed=changed,
        bytes_before=len(before_bytes),
        bytes_after=len(after_bytes),
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Normalize working-tree UTF-8 text files to CRLF line endings.")
    parser.add_argument("paths", nargs="+", help="File paths to normalize")
    args = parser.parse_args()

    out_dir = _today_ci_dir()
    out_dir.mkdir(parents=True, exist_ok=True)

    results: list[NormalizedResult] = []
    changed_paths: list[str] = []

    for p_str in args.paths:
        p = Path(p_str)
        if not p.exists() or not p.is_file():
            raise FileNotFoundError(p_str)
        r = _normalize_to_crlf_utf8(p)
        results.append(r)
        if r.changed:
            changed_paths.append(r.path)

    report = {
        "ts": dt.datetime.now(dt.timezone.utc).isoformat(),
        "operation": "normalize_working_tree_eol_crlf",
        "changed_paths": changed_paths,
        "results": [r.__dict__ for r in results],
    }
    (out_dir / "summary.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"EOL_CRLF status=ok changed={len(changed_paths)} out={out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

