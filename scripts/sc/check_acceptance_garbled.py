#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
sc-check-acceptance-garbled

Hard gate for task text integrity:
  - UTF-8 decode must pass
  - JSON parse must pass
  - No suspicious garbled text tokens in master/back/gameplay task artifacts

Output:
  logs/ci/<YYYY-MM-DD>/sc-check-acceptance-garbled/summary.json
"""

from __future__ import annotations

import argparse

from _garbled_gate import parse_task_ids_csv, render_top_hits, scan_task_text_integrity
from _util import ci_dir, write_json


def main() -> int:
    parser = argparse.ArgumentParser(description="Hard gate for garbled acceptance/task text.")
    parser.add_argument("--task-ids", default="", help="Optional CSV task ids filter (for example: 8,11,12).")
    parser.add_argument("--max-sample-chars", type=int, default=200)
    parser.add_argument("--max-print-hits", type=int, default=10)
    args = parser.parse_args()

    task_ids = parse_task_ids_csv(str(args.task_ids).strip())
    report = scan_task_text_integrity(
        task_ids=task_ids if task_ids else None,
        max_sample_chars=max(80, int(args.max_sample_chars)),
    )

    out_dir = ci_dir("sc-check-acceptance-garbled")
    out_file = out_dir / "summary.json"
    write_json(out_file, report)

    summary = report.get("summary") or {}
    decode_errors = int(summary.get("decode_errors") or 0)
    parse_errors = int(summary.get("parse_errors") or 0)
    suspicious_hits = int(summary.get("suspicious_hits") or 0)
    ok = decode_errors == 0 and parse_errors == 0 and suspicious_hits == 0

    print(
        "SC_GARBLED_GATE "
        f"status={'ok' if ok else 'fail'} decode_errors={decode_errors} parse_errors={parse_errors} "
        f"suspicious_hits={suspicious_hits} out={str(out_file).replace('\\', '/')}"
    )

    for line in render_top_hits(report, limit=max(1, int(args.max_print_hits))):
        print(f" - {line}")

    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
