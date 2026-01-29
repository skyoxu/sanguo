#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Validate alignment of i18n string keys between two JSON catalogs.

Default targets:
  - Data/i18n/zh_cn.json (base)
  - Data/i18n/en_us.json (compare)

Writes a JSON report to logs/ci/<YYYY-MM-DD>/i18n-keys-validate.json.
Exit code:
  0 if keys align
  1 if missing/extra keys are found or inputs are invalid
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from pathlib import Path


def _read_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise RuntimeError(f"Failed to read JSON: {path} ({exc})") from exc


def _extract_strings(obj: dict, path: Path) -> dict:
    strings = obj.get("strings")
    if not isinstance(strings, dict):
        raise RuntimeError(f"Invalid strings map in {path}")
    return strings


def _log_path() -> Path:
    date = dt.date.today().strftime("%Y-%m-%d")
    return Path("logs") / "ci" / date / "i18n-keys-validate.json"


def _write_report(path: Path, report: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default="Data/i18n/zh_cn.json", help="Base locale JSON path")
    parser.add_argument("--compare", default="Data/i18n/en_us.json", help="Compare locale JSON path")
    args = parser.parse_args()

    base_path = Path(args.base)
    compare_path = Path(args.compare)

    report: dict = {
        "base": str(base_path).replace("\\", "/"),
        "compare": str(compare_path).replace("\\", "/"),
        "timestamp": dt.datetime.now(dt.UTC).isoformat().replace("+00:00", "Z"),
        "ok": False,
        "base_count": 0,
        "compare_count": 0,
        "missing_in_compare": [],
        "extra_in_compare": [],
        "errors": [],
    }

    try:
        base_json = _read_json(base_path)
        compare_json = _read_json(compare_path)
        base_strings = _extract_strings(base_json, base_path)
        compare_strings = _extract_strings(compare_json, compare_path)
    except Exception as exc:
        report["errors"].append(str(exc))
        _write_report(_log_path(), report)
        print(f"[i18n-keys] error: {exc}")
        return 1

    base_keys = set(base_strings.keys())
    compare_keys = set(compare_strings.keys())
    missing = sorted(base_keys - compare_keys)
    extra = sorted(compare_keys - base_keys)

    report["base_count"] = len(base_keys)
    report["compare_count"] = len(compare_keys)
    report["missing_in_compare"] = missing
    report["extra_in_compare"] = extra
    report["ok"] = not missing and not extra

    _write_report(_log_path(), report)

    if report["ok"]:
        print(f"[i18n-keys] ok: {len(base_keys)} keys aligned")
        return 0

    print(f"[i18n-keys] mismatch: missing={len(missing)} extra={len(extra)}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
