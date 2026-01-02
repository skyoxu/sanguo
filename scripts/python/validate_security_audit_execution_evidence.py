#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Deterministic (runtime evidence) check for security-audit.jsonl.

Intent:
  When running sc-test with a specific run_id, verify that a security audit JSONL
  artifact was generated and follows the minimum schema:
    {ts, action, reason, target, caller}

Evidence sources (repo-relative):
  - logs/ci/<date>/security-audit.jsonl
  - logs/ci/<date>/sc-test/**/security-audit.jsonl
  - logs/e2e/<date>/sc-test/**/security-audit.jsonl

Exit code:
  0 if ok
  1 if missing/invalid
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


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")


def find_candidates(root: Path, date: str) -> list[Path]:
    cands: list[Path] = []
    cands.append(root / "logs" / "ci" / date / "security-audit.jsonl")

    ci_sc = root / "logs" / "ci" / date / "sc-test"
    if ci_sc.exists():
        cands.extend(list(ci_sc.rglob("security-audit.jsonl")))

    e2e_sc = root / "logs" / "e2e" / date / "sc-test"
    if e2e_sc.exists():
        cands.extend(list(e2e_sc.rglob("security-audit.jsonl")))

    # De-dup, keep existing only.
    uniq: list[Path] = []
    seen = set()
    for p in cands:
        if not p.exists():
            continue
        key = str(p.resolve()).lower()
        if key in seen:
            continue
        seen.add(key)
        uniq.append(p)
    return uniq


def validate_jsonl(path: Path) -> tuple[bool, str | None, int]:
    try:
        lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
    except Exception as exc:  # noqa: BLE001
        return False, f"read_error: {exc}", 0

    count = 0
    for raw in lines:
        s = raw.strip()
        if not s:
            continue
        count += 1
        try:
            obj = json.loads(s)
        except Exception as exc:  # noqa: BLE001
            return False, f"invalid_json: {exc}", count
        if not isinstance(obj, dict):
            return False, "line_not_object", count
        for k in REQUIRED_KEYS:
            if k not in obj:
                return False, f"missing_key:{k}", count
    return True, None, count


def main() -> int:
    ap = argparse.ArgumentParser(description="Validate security audit JSONL execution evidence (run_id bound).")
    ap.add_argument("--run-id", required=True, help="Expected run_id from sc-test.")
    ap.add_argument("--out", required=True, help="Output JSON path (under logs/ci/... recommended).")
    ap.add_argument("--date", default=None, help="Date folder (YYYY-MM-DD). Default: today.")
    args = ap.parse_args()

    root = repo_root()
    date = args.date or dt.date.today().strftime("%Y-%m-%d")
    out_path = Path(args.out)

    details: dict[str, Any] = {"date": date, "expected_run_id": args.run_id, "ok": False, "errors": [], "candidates": []}

    sc_summary = root / "logs" / "ci" / date / "sc-test" / "summary.json"
    if not sc_summary.exists():
        details["errors"].append("missing_sc_test_summary")
        write_json(out_path, details)
        print("SECURITY_AUDIT_EVIDENCE status=fail error=missing_sc_test_summary")
        return 1

    try:
        summary = load_json(sc_summary)
    except Exception as exc:  # noqa: BLE001
        details["errors"].append(f"invalid_sc_test_summary_json: {exc}")
        write_json(out_path, details)
        print("SECURITY_AUDIT_EVIDENCE status=fail error=invalid_sc_test_summary_json")
        return 1

    run_id_in_summary = summary.get("run_id") if isinstance(summary, dict) else None
    details["run_id_in_summary"] = run_id_in_summary
    if str(run_id_in_summary or "") != str(args.run_id):
        details["errors"].append("run_id_mismatch")
        write_json(out_path, details)
        print("SECURITY_AUDIT_EVIDENCE status=fail error=run_id_mismatch")
        return 1

    candidates = find_candidates(root, date)
    for p in candidates:
        ok, err, lines = validate_jsonl(p)
        details["candidates"].append({"path": p.relative_to(root).as_posix(), "ok": ok, "error": err, "nonempty_lines": lines})

    selected = next((c for c in details["candidates"] if c.get("ok")), None)
    if not selected:
        details["errors"].append("no_valid_security_audit_jsonl_found")
        write_json(out_path, details)
        print("SECURITY_AUDIT_EVIDENCE status=fail error=no_valid_security_audit_jsonl_found")
        return 1

    details["ok"] = True
    details["selected"] = selected
    write_json(out_path, details)
    print(f"SECURITY_AUDIT_EVIDENCE status=ok selected={selected.get('path')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

