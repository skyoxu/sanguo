#!/usr/bin/env python3
"""
Security soft scan (heuristic, deterministic).

This is NOT a vulnerability proof. It is a stop-loss helper that scans for
high-risk API patterns and writes findings to logs for review.

Design:
  - Deterministic string/pattern matching only.
  - Default exit code is 0 (soft gate). Unexpected errors return 2.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Rule:
    name: str
    severity: str  # info|warn
    file_globs: tuple[str, ...]
    pattern: re.Pattern[str]


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _to_posix(path: Path) -> str:
    return str(path).replace("\\", "/")


def iter_code_files(root: Path, globs: tuple[str, ...]) -> list[Path]:
    files: list[Path] = []
    for g in globs:
        files.extend(root.rglob(g))
    filtered: list[Path] = []
    for p in files:
        if not p.is_file():
            continue
        if any(seg in {".git", ".godot", "bin", "obj", "logs"} for seg in p.parts):
            continue
        filtered.append(p)
    return sorted(set(filtered))


def find_matches(path: Path, rule: Rule) -> list[dict]:
    text = path.read_text(encoding="utf-8", errors="ignore")
    findings: list[dict] = []
    for i, line in enumerate(text.splitlines(), start=1):
        if rule.pattern.search(line):
            findings.append({"file": _to_posix(path), "line": i, "rule": rule.name, "severity": rule.severity, "text": line.strip()})
    return findings


def main() -> int:
    ap = argparse.ArgumentParser(description="Heuristic security soft scan (deterministic).")
    ap.add_argument("--out", required=True, help="Output JSON path (under logs/ci/... recommended).")
    args = ap.parse_args()

    root = repo_root()
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    rules = [
        Rule(
            name="py.os_expandvars",
            severity="warn",
            file_globs=("scripts/**/*.py",),
            pattern=re.compile(r"\bos\.expandvars\s*\("),
        ),
        Rule(
            name="py.subprocess_shell_true",
            severity="warn",
            file_globs=("scripts/**/*.py",),
            pattern=re.compile(r"\bshell\s*=\s*True\b"),
        ),
        Rule(
            name="cs.process_start",
            severity="warn",
            file_globs=("**/*.cs",),
            pattern=re.compile(r"\bProcess\.(Start|StartInfo)\b"),
        ),
        Rule(
            name="cs.dllimport",
            severity="warn",
            file_globs=("**/*.cs",),
            pattern=re.compile(r"\bDllImport\b"),
        ),
        Rule(
            name="gd.os_execute",
            severity="warn",
            file_globs=("**/*.gd",),
            pattern=re.compile(r"\bOS\.execute\b"),
        ),
        Rule(
            name="http.plain_http_url",
            severity="warn",
            file_globs=("**/*.cs", "**/*.gd", "scripts/**/*.py"),
            pattern=re.compile(r"http://", re.IGNORECASE),
        ),
    ]

    findings: list[dict] = []
    for rule in rules:
        for p in iter_code_files(root, rule.file_globs):
            findings.extend(find_matches(p, rule))

    report = {
        "status": "ok",
        "note": "Soft scan only; findings require human triage.",
        "rules": [r.name for r in rules],
        "findings": findings,
        "counts": {
            "total": len(findings),
            "warn": sum(1 for f in findings if f.get("severity") == "warn"),
            "info": sum(1 for f in findings if f.get("severity") == "info"),
        },
    }

    out_path.write_text(json.dumps(report, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")
    print(f"SECURITY_SOFT_SCAN status=ok findings={len(findings)}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:  # noqa: BLE001
        print(f"SECURITY_SOFT_SCAN status=fail error={exc}", file=sys.stderr)
        raise SystemExit(2)
