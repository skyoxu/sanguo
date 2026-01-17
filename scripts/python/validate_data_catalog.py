"""
Data catalog validation hard gate (T50-T65 alignment).

This script is a thin CLI wrapper around scripts/python/data_catalog_rules_t50.py.
Writes evidence into logs/ci/<YYYY-MM-DD>/.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path

import data_catalog_rules_t50 as rules


def _write_logs(findings: list[object], out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    txt = out_dir / "data-catalog-validate.log"
    js = out_dir / "data-catalog-validate.json"

    failures = [getattr(f, "__dict__", {"raw": str(f)}) for f in findings if getattr(f, "level", "") == "fail"]
    warnings = [getattr(f, "__dict__", {"raw": str(f)}) for f in findings if getattr(f, "level", "") == "warn"]
    payload = {
        "failures": failures,
        "warnings": warnings,
        "counts": {"fail": len(failures), "warn": len(warnings)},
    }

    js.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )

    lines: list[str] = []
    lines.append(f"DATA_CATALOG_VALIDATE failures={payload['counts']['fail']} warnings={payload['counts']['warn']}")
    for f in findings:
        level = getattr(f, "level", "unknown").upper()
        code = getattr(f, "code", "UNKNOWN")
        target = getattr(f, "target", "")
        msg = getattr(f, "message", "")
        lines.append(f"{level:7} {code} target={target} msg={msg}")
    txt.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--strict", action="store_true", help="Fail on warnings as well (default: false).")
    args = ap.parse_args()

    repo_root = Path(".")
    findings = rules.collect_findings(repo_root)

    today = dt.date.today().strftime("%Y-%m-%d")
    out_dir = repo_root / "logs" / "ci" / today
    _write_logs(findings, out_dir)

    fail_count = sum(1 for f in findings if getattr(f, "level", "") == "fail")
    warn_count = sum(1 for f in findings if getattr(f, "level", "") == "warn")
    if fail_count > 0:
        return 1
    if args.strict and warn_count > 0:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

