#!/usr/bin/env python3
"""
Soft warning: report whitelist entries nearing expiration.

This script never hard-fails by default. It writes warning artifacts to:
  logs/ci/<YYYY-MM-DD>/whitelist-expiry-warning.json
  logs/ci/<YYYY-MM-DD>/whitelist-expiry-warning.txt
"""

from __future__ import annotations

import argparse
import json
import os
from datetime import date, datetime
from pathlib import Path

from _whitelist_metadata import parse_whitelist


def _today_str() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def _write_utf8(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8", newline="\n")


def _parse_expire_date(raw: str) -> date | None:
    value = str(raw or "").strip()
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def _resolve_warn_days(cli_warn_days: int | None) -> tuple[int, str, str | None]:
    default_warn_days = 90
    if cli_warn_days is not None:
        value = int(cli_warn_days)
        if 1 <= value <= 365:
            return value, "cli", None
        return default_warn_days, "default", f"invalid_cli_warn_days:{cli_warn_days}"

    env_raw = str(os.environ.get("WHITELIST_WARN_DAYS") or "").strip()
    if env_raw:
        try:
            value = int(env_raw)
        except ValueError:
            return default_warn_days, "default", f"invalid_env_warn_days:{env_raw}"
        if 1 <= value <= 365:
            return value, "env", None
        return default_warn_days, "default", f"out_of_range_env_warn_days:{env_raw}"

    return default_warn_days, "default", None


def _build_report(*, root: Path, whitelist_rel: str, warn_days: int, warn_days_source: str, warn_days_warning: str | None) -> dict:
    whitelist_path = (root / whitelist_rel).resolve()
    _, entries, issues = parse_whitelist(whitelist_path, metadata_mode="warn")
    today = date.today()

    expiring_soon: list[dict] = []
    expired: list[dict] = []
    invalid_date: list[dict] = []

    for entry in entries:
        expire_raw = str(entry.get("expire_date") or "").strip()
        parsed = _parse_expire_date(expire_raw)
        if parsed is None:
            invalid_date.append(entry)
            continue
        delta = (parsed - today).days
        item = {**entry, "days_until_expire": delta}
        if delta < 0:
            expired.append(item)
        elif delta <= warn_days:
            expiring_soon.append(item)

    warn_issues = [i.__dict__ for i in issues if i.severity == "warn"]
    error_issues = [i.__dict__ for i in issues if i.severity == "error"]
    status = "warn" if (expired or expiring_soon or invalid_date or warn_issues or error_issues) else "ok"

    return {
        "status": status,
        "today": str(today),
        "warn_days": int(warn_days),
        "warn_days_source": warn_days_source,
        "warn_days_warning": warn_days_warning,
        "whitelist_file": str(whitelist_path.relative_to(root)).replace("\\", "/") if whitelist_path.exists() else whitelist_rel,
        "entries_count": len(entries),
        "expiring_soon_count": len(expiring_soon),
        "expired_count": len(expired),
        "invalid_date_count": len(invalid_date),
        "metadata_warn_count": len(warn_issues),
        "metadata_error_count": len(error_issues),
        "expiring_soon": expiring_soon,
        "expired": expired,
        "invalid_date": invalid_date,
        "metadata_warn_issues": warn_issues,
        "metadata_error_issues": error_issues,
    }


def _build_text(report: dict) -> str:
    lines: list[str] = []
    lines.append(f"status={report.get('status')} today={report.get('today')} warn_days={report.get('warn_days')}")
    lines.append(f"warn_days_source={report.get('warn_days_source')} warn_days_warning={report.get('warn_days_warning')}")
    lines.append(f"whitelist_file={report.get('whitelist_file')} entries={report.get('entries_count')}")
    lines.append(
        f"expiring_soon={report.get('expiring_soon_count')} expired={report.get('expired_count')} "
        f"invalid_date={report.get('invalid_date_count')}"
    )
    lines.append(
        f"metadata_warn={report.get('metadata_warn_count')} metadata_error={report.get('metadata_error_count')}"
    )

    if report.get("expiring_soon"):
        lines.append("")
        lines.append("[EXPIRING_SOON]")
        for item in report["expiring_soon"]:
            lines.append(
                f"{item.get('path')} owner={item.get('owner')} expire={item.get('expire_date')} "
                f"days_until_expire={item.get('days_until_expire')} reason={item.get('reason')}"
            )

    if report.get("expired"):
        lines.append("")
        lines.append("[EXPIRED]")
        for item in report["expired"]:
            lines.append(
                f"{item.get('path')} owner={item.get('owner')} expire={item.get('expire_date')} "
                f"days_until_expire={item.get('days_until_expire')} reason={item.get('reason')}"
            )

    if report.get("invalid_date"):
        lines.append("")
        lines.append("[INVALID_DATE]")
        for item in report["invalid_date"]:
            lines.append(
                f"{item.get('path')} owner={item.get('owner')} expire={item.get('expire_date')} reason={item.get('reason')}"
            )

    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Soft warning for whitelist expiry.")
    parser.add_argument("--root", default=".", help="Repository root path.")
    parser.add_argument(
        "--whitelist",
        default="docs/workflows/unified-pipeline-command-whitelist.txt",
        help="Whitelist file path relative to repo root.",
    )
    parser.add_argument(
        "--warn-days",
        type=int,
        default=None,
        help="Warn when entry expires within N days. Resolution order: CLI > WHITELIST_WARN_DAYS > default 90.",
    )
    parser.add_argument(
        "--fail-on-expired",
        action="store_true",
        help="Return non-zero when expired entries are present. Default off (soft warning).",
    )
    args = parser.parse_args(argv)

    root = Path(args.root).resolve()
    out_dir = root / "logs" / "ci" / _today_str()
    out_dir.mkdir(parents=True, exist_ok=True)
    out_json = out_dir / "whitelist-expiry-warning.json"
    out_txt = out_dir / "whitelist-expiry-warning.txt"

    resolved_warn_days, warn_days_source, warn_days_warning = _resolve_warn_days(args.warn_days)
    report = _build_report(
        root=root,
        whitelist_rel=str(args.whitelist),
        warn_days=resolved_warn_days,
        warn_days_source=warn_days_source,
        warn_days_warning=warn_days_warning,
    )
    _write_utf8(out_json, json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    _write_utf8(out_txt, _build_text(report))

    status = str(report.get("status") or "ok")
    print(
        f"whitelist_expiry_warning: status={status} warn_days={report.get('warn_days')} "
        f"source={report.get('warn_days_source')} expiring_soon={report.get('expiring_soon_count')} "
        f"expired={report.get('expired_count')} report={out_json.as_posix()}"
    )

    if bool(args.fail_on_expired) and int(report.get("expired_count") or 0) > 0:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
