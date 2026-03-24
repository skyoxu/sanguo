#!/usr/bin/env python
"""
Hard gate: forbid references to the mirror path `Tests.Godot/Game.Godot/**`.

Why:
- In this template, `Tests.Godot/Game.Godot` must be a Junction to the real `Game.Godot`
  (SSoT). If any code/tests reference the mirror path directly, CI behavior becomes
  inconsistent: it may pass locally (with a Junction) but fail in clean environments.

Scope (default):
- Scan code/test files under:
  - Game.Core.Tests/**/*.cs
  - Tests.Godot/**/*.gd, Tests.Godot/**/*.tscn, Tests.Godot/**/*.cs
  - Game.Godot/**/*.gd, Game.Godot/**/*.cs, Game.Godot/**/*.tscn
- Exclude:
  - scripts/**, docs/**, logs/**, bin/obj/.godot/TestResults
  - Tests.Godot/Game.Godot/** (Junction alias path)

Outputs:
- logs/ci/<YYYY-MM-DD>/forbid-mirror-path-refs.json
- logs/ci/<YYYY-MM-DD>/forbid-mirror-path-refs.txt
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable


EXCLUDE_DIR_NAMES = {
    ".git",
    ".godot",
    "bin",
    "obj",
    "logs",
    "TestResults",
}


DEFAULT_ROOTS = [
    "Game.Core.Tests",
    "Tests.Godot",
    "Game.Godot",
]


DEFAULT_EXTS = {".cs", ".gd", ".tscn"}


MIRROR_RE = re.compile(
    r"(?:^|[^A-Za-z0-9_])Tests\.Godot[\\/]+Game\.Godot[\\/]+",
    flags=re.IGNORECASE,
)


@dataclass(frozen=True)
class Hit:
    file: str
    line: int
    excerpt: str


def _today() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def _write_utf8(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def _iter_files(root: Path, *, roots: list[str], exts: set[str]) -> Iterable[Path]:
    for r in roots:
        base = (root / r).resolve()
        if not base.exists():
            continue
        for p in base.rglob("*"):
            if not p.is_file():
                continue
            if any(seg in EXCLUDE_DIR_NAMES for seg in p.parts):
                continue
            # Exclude the Junction alias path itself.
            rel = p.relative_to(root).as_posix()
            if rel.startswith("Tests.Godot/Game.Godot/"):
                continue
            if p.suffix.lower() not in exts:
                continue
            yield p


def _scan_file(root: Path, path: Path, max_hits_per_file: int) -> list[Hit]:
    rel = path.relative_to(root).as_posix()
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        text = path.read_text(encoding="utf-8", errors="ignore")

    hits: list[Hit] = []
    for i, line in enumerate(text.splitlines(), 1):
        if MIRROR_RE.search(line):
            excerpt = line.strip()
            if len(excerpt) > 240:
                excerpt = excerpt[:240] + "..."
            hits.append(Hit(file=rel, line=i, excerpt=excerpt))
            if len(hits) >= max_hits_per_file:
                break
    return hits


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Hard gate: forbid mirror path refs (Tests.Godot/Game.Godot).")
    ap.add_argument("--root", default=".", help="Repo root (default: .)")
    ap.add_argument(
        "--roots",
        default=",".join(DEFAULT_ROOTS),
        help="Comma-separated roots to scan (default: Game.Core.Tests,Tests.Godot,Game.Godot)",
    )
    ap.add_argument(
        "--exts",
        default=",".join(sorted(DEFAULT_EXTS)),
        help="Comma-separated file extensions to scan (default: .cs,.gd,.tscn)",
    )
    ap.add_argument("--max-hits", type=int, default=200, help="Max total hits recorded (default: 200)")
    ap.add_argument("--max-hits-per-file", type=int, default=20, help="Max hits per file (default: 20)")
    args = ap.parse_args(argv)

    root = Path(args.root).resolve()
    roots = [x.strip() for x in str(args.roots).split(",") if x.strip()]
    exts = {("." + x.strip().lstrip(".")).lower() for x in str(args.exts).split(",") if x.strip()}

    out_dir = root / "logs" / "ci" / _today()
    out_dir.mkdir(parents=True, exist_ok=True)
    out_json = out_dir / "forbid-mirror-path-refs.json"
    out_txt = out_dir / "forbid-mirror-path-refs.txt"

    all_hits: list[Hit] = []
    scanned_files = 0
    for p in _iter_files(root, roots=roots, exts=exts):
        scanned_files += 1
        hits = _scan_file(root, p, max_hits_per_file=int(args.max_hits_per_file))
        if hits:
            all_hits.extend(hits)
        if len(all_hits) >= int(args.max_hits):
            break

    ok = len(all_hits) == 0
    report = {
        "ok": ok,
        "roots": roots,
        "exts": sorted(exts),
        "scanned_files": scanned_files,
        "hits_count": len(all_hits),
        "hits": [h.__dict__ for h in all_hits],
        "rule": "forbid Tests.Godot/Game.Godot mirror refs; use Game.Godot (SSoT) or res://Game.Godot",
        "repair": [
            "Replace any Tests.Godot/Game.Godot/... references with Game.Godot/... (repo-relative) or res://Game.Godot/... (Godot).",
            "Never hardcode mirror/alias paths in tests; CI may not have a Junction in all contexts.",
        ],
    }

    _write_utf8(out_json, json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    if ok:
        _write_utf8(out_txt, "OK: no mirror path references found.\n")
    else:
        lines: list[str] = []
        lines.append("FAIL: mirror path references found (Tests.Godot/Game.Godot).")
        lines.append("")
        for h in all_hits:
            lines.append(f"{h.file}:{h.line} {h.excerpt}")
        lines.append("")
        lines.append("Repair:")
        for r in report["repair"]:
            lines.append(f"- {r}")
        lines.append("")
        _write_utf8(out_txt, "\n".join(lines))

    status = "OK" if ok else "FAIL"
    print(f"forbid_mirror_path_refs: {status} hits={len(all_hits)} scanned={scanned_files}")
    print(f"report={out_json.as_posix()}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())

