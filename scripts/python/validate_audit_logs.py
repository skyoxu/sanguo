#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Deterministic validator: audit JSONL schema from logs/ci/<date>/security-audit.jsonl.

Contract (minimal):
  - Input: logs/ci/<YYYY-MM-DD>/security-audit.jsonl
  - Output: JSON report (--out) written even on failure
  - Exit code: 0 ok, 1 fail/missing/invalid
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path
from typing import Any


REQUIRED_KEYS = ("ts", "action", "reason", "target", "caller")


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def validate_jsonl(path: Path) -> tuple[bool, list[dict[str, Any]]]:
    results: list[dict[str, Any]] = []
    ok = True

    lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
    line_no = 0
    for raw in lines:
        s = raw.strip()
        if not s:
            continue
        line_no += 1
        entry: dict[str, Any] = {"line": line_no, "ok": False, "error": None}
        try:
            obj = json.loads(s)
        except Exception as exc:  # noqa: BLE001
            entry["error"] = f"invalid_json:{exc}"
            ok = False
            results.append(entry)
            continue
        if not isinstance(obj, dict):
            entry["error"] = "line_not_object"
            ok = False
            results.append(entry)
            continue

        missing = [k for k in REQUIRED_KEYS if k not in obj]
        if missing:
            entry["error"] = "missing_keys:" + ",".join(missing)
            ok = False
            results.append(entry)
            continue

        entry["ok"] = True
        results.append(entry)

    return ok, results


def main() -> int:
    ap = argparse.ArgumentParser(description="Validate security-audit.jsonl line schema.")
    ap.add_argument("--date", default=None, help="Date folder (YYYY-MM-DD). Default: today.")
    ap.add_argument("--out", required=True, help="Output JSON path (under logs/ci/... recommended).")
    args = ap.parse_args()

    root = repo_root()
    date = args.date or dt.date.today().strftime("%Y-%m-%d")
    out_path = Path(args.out)

    audit_path = root / "logs" / "ci" / date / "security-audit.jsonl"
    report: dict[str, Any] = {
        "cmd": "validate_audit_logs",
        "date": date,
        "ok": False,
        "audit_path": audit_path.as_posix(),
        "required_keys": list(REQUIRED_KEYS),
        "nonempty_lines": 0,
        "valid_lines": 0,
        "results": [],
        "errors": [],
    }

    if not audit_path.exists():
        report["errors"].append("missing_audit_jsonl")
        write_json(out_path, report)
        print("VALIDATE_AUDIT_LOGS status=fail error=missing_audit_jsonl")
        return 1

    try:
        ok, results = validate_jsonl(audit_path)
    except Exception as exc:  # noqa: BLE001
        report["errors"].append(f"read_or_validate_error:{exc}")
        write_json(out_path, report)
        print("VALIDATE_AUDIT_LOGS status=fail error=read_or_validate_error")
        return 1

    report["results"] = results
    report["nonempty_lines"] = len(results)
    report["valid_lines"] = len([r for r in results if bool(r.get("ok"))])
    if report["nonempty_lines"] == 0:
        report["errors"].append("empty_audit_jsonl")
        ok = False
    if report["valid_lines"] == 0:
        report["errors"].append("no_valid_audit_entries")
        ok = False
    report["ok"] = bool(ok)
    write_json(out_path, report)
    print(
        f"VALIDATE_AUDIT_LOGS status={'ok' if ok else 'fail'} "
        f"lines={report['nonempty_lines']} valid={report['valid_lines']}"
    )
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
