#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Domain contracts check (template-friendly, deterministic).

This script is designed to be reusable across projects based on this template.
It scans `Game.Core/Contracts/**/*.cs` and validates event contract conventions:

- Each `public const string EventType = "<type>"` must be a dot-separated, lowercase string.
- The first segment must match the configured domain prefix (default: "core").
- If the file contains an XML doc line like `Domain event: <type>`, it should match `EventType` (warning by default).
- EventType values should be unique across Contracts.

Outputs:
  - JSON report (default): logs/ci/<YYYY-MM-DD>/domain-contracts-check/summary.json

Exit codes:
  - 0: ok (or skipped when Contracts dir not found)
  - 1: issues found
  - 2: unexpected error
"""

from __future__ import annotations

import argparse
import json
import os
import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any


EVENT_TYPE_LITERAL_RE = re.compile(
    r"\bpublic\s+const\s+string\s+EventType\s*=\s*\"([^\"]+)\"\s*;",
    re.MULTILINE,
)
EVENT_TYPE_SYMBOL_RE = re.compile(
    r"\bpublic\s+const\s+string\s+EventType\s*=\s*EventTypes\.([A-Za-z_][A-Za-z0-9_]*)\s*;",
    re.MULTILINE,
)
EVENT_TYPES_MEMBER_RE = re.compile(
    r"\bpublic\s+const\s+string\s+([A-Za-z_][A-Za-z0-9_]*)\s*=\s*\"([^\"]+)\"\s*;",
    re.MULTILINE,
)
DOC_DOMAIN_EVENT_RE = re.compile(r"\bDomain\s+event:\s*([a-z0-9._]+)\b", re.IGNORECASE)


@dataclass(frozen=True)
class Finding:
    file: str
    event_type: str
    ok: bool
    issues: list[str]
    warnings: list[str]


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _to_posix(path: Path) -> str:
    return str(path).replace("\\", "/")


def _default_out_path(root: Path) -> Path:
    day = date.today().strftime("%Y-%m-%d")
    return root / "logs" / "ci" / day / "domain-contracts-check" / "summary.json"


def _iter_contract_files(contracts_dir: Path) -> list[Path]:
    files: list[Path] = []
    for p in contracts_dir.rglob("*.cs"):
        if not p.is_file():
            continue
        if any(seg in {"bin", "obj"} for seg in p.parts):
            continue
        files.append(p)
    return sorted(files)


def _load_event_types_map(contracts_dir: Path) -> dict[str, str]:
    mapping: dict[str, str] = {}
    event_types_path = contracts_dir / "EventTypes.cs"
    if not event_types_path.exists():
        return mapping

    text = event_types_path.read_text(encoding="utf-8", errors="ignore")
    for symbol, value in EVENT_TYPES_MEMBER_RE.findall(text):
        mapping[symbol] = value
    return mapping


def _validate_event_type(value: str, *, domain_prefix: str) -> list[str]:
    issues: list[str] = []
    s = value.strip()
    if s != value:
        issues.append("event type contains leading/trailing whitespace")

    token_re = re.compile(r"^[a-z][a-z0-9_]*$")
    parts = s.split(".")
    if len(parts) < 3:
        issues.append("event type must have >= 3 dot-separated segments (prefix.entity.action)")
        return issues

    for part in parts:
        if not token_re.fullmatch(part):
            issues.append(f"invalid segment: {part!r} (require [a-z][a-z0-9_]*)")

    if parts and parts[0] != domain_prefix:
        issues.append(f"domain prefix mismatch: expected '{domain_prefix}.'")

    return issues


def _doc_value_for_position(doc_matches: list[re.Match[str]], position: int) -> str | None:
    nearest: str | None = None
    for match in doc_matches:
        if match.start() > position:
            break
        nearest = match.group(1).strip()
    return nearest


def main() -> int:
    ap = argparse.ArgumentParser(description="Domain contracts check (template-friendly).")
    ap.add_argument("--contracts-dir", default="Game.Core/Contracts", help="Contracts root directory (relative to repo root).")
    ap.add_argument(
        "--domain-prefix",
        default=(os.environ.get("DOMAIN_PREFIX") or "core").strip() or "core",
        help="Expected event type prefix (default from env DOMAIN_PREFIX or 'core').",
    )
    ap.add_argument("--out", default=None, help="Output JSON path. Defaults to logs/ci/<date>/domain-contracts-check/summary.json")
    args = ap.parse_args()

    root = repo_root()
    contracts_dir = root / str(args.contracts_dir)
    out_path = Path(args.out) if args.out else _default_out_path(root)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    if not contracts_dir.exists():
        report = {
            "status": "skipped",
            "reason": f"contracts dir not found: {_to_posix(contracts_dir)}",
            "domain_prefix": args.domain_prefix,
            "findings": [],
        }
        out_path.write_text(json.dumps(report, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")
        print(f"DOMAIN_CONTRACTS_CHECK status=skipped out={_to_posix(out_path)}")
        return 0

    findings: list[Finding] = []
    all_event_types: dict[str, list[str]] = {}
    event_type_map = _load_event_types_map(contracts_dir)

    for cs in _iter_contract_files(contracts_dir):
        text = cs.read_text(encoding="utf-8", errors="ignore")
        doc_matches = list(DOC_DOMAIN_EVENT_RE.finditer(text))
        resolved_values: list[tuple[int, str]] = []

        for match in EVENT_TYPE_LITERAL_RE.finditer(text):
            resolved_values.append((match.start(), match.group(1)))

        for match in EVENT_TYPE_SYMBOL_RE.finditer(text):
            symbol = match.group(1)
            event_type = event_type_map.get(symbol)
            if event_type:
                resolved_values.append((match.start(), event_type))
                continue
            rel = _to_posix(cs.relative_to(root))
            findings.append(
                Finding(
                    file=rel,
                    event_type=f"EventTypes.{symbol}",
                    ok=False,
                    issues=[f"unresolved EventTypes symbol: {symbol}"],
                    warnings=[],
                )
            )

        for source_pos, event_type in resolved_values:
            issues = _validate_event_type(event_type, domain_prefix=args.domain_prefix)
            warnings: list[str] = []
            doc_value = _doc_value_for_position(doc_matches, source_pos)
            if doc_value and doc_value.lower() != event_type.strip().lower():
                warnings.append(f"doc 'Domain event' mismatch: doc={doc_value!r} const={event_type!r}")

            rel = _to_posix(cs.relative_to(root))
            ok = not issues
            findings.append(Finding(file=rel, event_type=event_type, ok=ok, issues=issues, warnings=warnings))
            all_event_types.setdefault(event_type, []).append(rel)

    duplicate_event_types = {k: v for k, v in all_event_types.items() if len(v) > 1}
    dup_issues: list[dict[str, Any]] = []
    if duplicate_event_types:
        for k, v in sorted(duplicate_event_types.items()):
            dup_issues.append({"event_type": k, "files": v})

    issues_count = sum(1 for f in findings if f.issues)
    warnings_count = sum(len(f.warnings) for f in findings)
    status = "ok" if (issues_count == 0 and not dup_issues) else "fail"

    report = {
        "status": status,
        "domain_prefix": args.domain_prefix,
        "contracts_dir": _to_posix(contracts_dir.relative_to(root)),
        "counts": {
            "files_scanned": len(_iter_contract_files(contracts_dir)),
            "event_type_constants": len(findings),
            "issues": issues_count + (1 if dup_issues else 0),
            "warnings": warnings_count,
        },
        "duplicate_event_types": dup_issues,
        "findings": [f.__dict__ for f in findings],
    }
    out_path.write_text(json.dumps(report, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")

    print(
        f"DOMAIN_CONTRACTS_CHECK status={status} events={len(findings)} "
        f"issues={report['counts']['issues']} warnings={warnings_count} out={_to_posix(out_path)}"
    )
    return 0 if status == "ok" else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:  # noqa: BLE001
        print(f"DOMAIN_CONTRACTS_CHECK status=fail error={exc}")
        raise SystemExit(2)
