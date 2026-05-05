#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Deterministic validator: performance P95 budget from logs/perf/<date>/summary.json.

Contract (minimal):
  - Input: logs/perf/<YYYY-MM-DD>/summary.json
  - Output: JSON report (--out) written even on failure
  - Exit code: 0 ok, 1 fail/missing/invalid

This script is intentionally pure-Python and file-based, to keep it runnable in CI.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
from pathlib import Path
from typing import Any

_PERF_RE = re.compile(
    r"\[PERF\]\s*frames=(\d+)\s+avg_ms=([0-9]+(?:\.[0-9]+)?)\s+"
    r"p50_ms=([0-9]+(?:\.[0-9]+)?)\s+p95_ms=([0-9]+(?:\.[0-9]+)?)\s+"
    r"p99_ms=([0-9]+(?:\.[0-9]+)?)"
)


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _as_float(value: str | None, *, default: float) -> float:
    try:
        return float(str(value or "").strip())
    except Exception:
        return default


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def _extract_perf_from_text(text: str) -> dict[str, float | int] | None:
    matches = list(_PERF_RE.finditer(text or ""))
    if not matches:
        return None
    last = matches[-1]
    return {
        "frames": int(last.group(1)),
        "avg_ms": float(last.group(2)),
        "p50_ms": float(last.group(3)),
        "p95_ms": float(last.group(4)),
        "p99_ms": float(last.group(5)),
    }


def _find_latest_perf_from_headless_logs(root: Path, date: str) -> tuple[dict[str, float | int] | None, Path | None]:
    ci_date_dir = root / "logs" / "ci" / date
    if not ci_date_dir.exists():
        return None, None
    candidates = [p for p in ci_date_dir.rglob("headless.log") if p.is_file()]
    if not candidates:
        return None, None
    candidates.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    for log_path in candidates:
        try:
            metrics = _extract_perf_from_text(log_path.read_text(encoding="utf-8", errors="ignore"))
        except Exception:
            metrics = None
        if metrics is not None:
            return metrics, log_path
    return None, None


def main() -> int:
    ap = argparse.ArgumentParser(description="Validate perf summary p95_ms against budget.")
    ap.add_argument("--date", default=None, help="Date folder (YYYY-MM-DD). Default: today.")
    ap.add_argument("--out", required=True, help="Output JSON path (under logs/ci/... recommended).")
    ap.add_argument(
        "--max-p95-ms",
        default=None,
        help="Maximum allowed p95_ms (ms). Default: env PERF_P95_THRESHOLD_MS or 16.6.",
    )
    args = ap.parse_args()

    root = repo_root()
    date = args.date or dt.date.today().strftime("%Y-%m-%d")
    out_path = Path(args.out)

    max_p95_ms = _as_float(args.max_p95_ms, default=_as_float(os.environ.get("PERF_P95_THRESHOLD_MS"), default=16.6))

    perf_summary_path = root / "logs" / "perf" / date / "summary.json"
    report: dict[str, Any] = {
        "cmd": "validate_perf",
        "date": date,
        "ok": False,
        "max_p95_ms": max_p95_ms,
        "perf_summary_path": perf_summary_path.as_posix(),
        "metrics": None,
        "errors": [],
    }

    if not perf_summary_path.exists():
        fallback_metrics, fallback_log = _find_latest_perf_from_headless_logs(root, date)
        if fallback_metrics is None:
            report["errors"].append("missing_perf_summary")
            write_json(out_path, report)
            print("VALIDATE_PERF status=fail error=missing_perf_summary")
            return 1
        fallback_payload = {
            "date": date,
            "source": (fallback_log.as_posix() if fallback_log else ""),
            **fallback_metrics,
        }
        perf_summary_path.parent.mkdir(parents=True, exist_ok=True)
        write_json(perf_summary_path, fallback_payload)

    try:
        payload = load_json(perf_summary_path)
    except Exception as exc:  # noqa: BLE001
        report["errors"].append(f"invalid_json:{exc}")
        write_json(out_path, report)
        print("VALIDATE_PERF status=fail error=invalid_json")
        return 1

    if not isinstance(payload, dict):
        report["errors"].append("summary_not_object")
        write_json(out_path, report)
        print("VALIDATE_PERF status=fail error=summary_not_object")
        return 1

    p95 = payload.get("p95_ms")
    try:
        p95_ms = float(p95)
    except Exception:
        report["errors"].append("missing_or_invalid:p95_ms")
        report["metrics"] = payload
        write_json(out_path, report)
        print("VALIDATE_PERF status=fail error=missing_or_invalid_p95_ms")
        return 1

    report["metrics"] = payload
    report["p95_ms"] = p95_ms
    report["ok"] = p95_ms <= max_p95_ms
    write_json(out_path, report)
    print(f"VALIDATE_PERF status={'ok' if report['ok'] else 'fail'} p95_ms={p95_ms:.2f} max_p95_ms={max_p95_ms:.2f}")
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
