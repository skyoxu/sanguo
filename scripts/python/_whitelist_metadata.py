#!/usr/bin/env python3
"""
Whitelist metadata parser for unified pipeline command guard.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path


@dataclass(frozen=True)
class WhitelistIssue:
    line: int
    code: str
    severity: str
    message: str
    raw: str


def normalize_rel(path_text: str) -> str:
    return path_text.replace("\\", "/").strip().lstrip("./")


def _severity_for_metadata_issue(mode: str) -> str:
    if mode == "require":
        return "error"
    if mode == "warn":
        return "warn"
    return "info"


def parse_whitelist(path: Path | None, *, metadata_mode: str) -> tuple[set[str], list[dict[str, str]], list[WhitelistIssue]]:
    allowed: set[str] = set()
    entries: list[dict[str, str]] = []
    issues: list[WhitelistIssue] = []
    if path is None or not path.exists():
        if metadata_mode == "require":
            issues.append(
                WhitelistIssue(
                    line=0,
                    code="WHITELIST_FILE_MISSING",
                    severity="error",
                    message="Whitelist file is required but missing.",
                    raw="",
                )
            )
        return allowed, entries, issues

    today_value = date.today()
    seen_paths: set[str] = set()
    for line_no, raw in enumerate(path.read_text(encoding="utf-8", errors="ignore").splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue

        parts = [p.strip() for p in line.split("|", 3)]
        path_value = ""
        owner = ""
        expire_date = ""
        reason = ""

        if len(parts) == 1:
            path_value = normalize_rel(parts[0])
            if metadata_mode != "off":
                issues.append(
                    WhitelistIssue(
                        line=line_no,
                        code="WHITELIST_METADATA_REQUIRED",
                        severity=_severity_for_metadata_issue(metadata_mode),
                        message="Whitelist entry must include path|owner|expire_date|reason.",
                        raw=raw,
                    )
                )
        elif len(parts) == 4:
            path_value = normalize_rel(parts[0])
            owner = parts[1]
            expire_date = parts[2]
            reason = parts[3]
        else:
            issues.append(
                WhitelistIssue(
                    line=line_no,
                    code="WHITELIST_ENTRY_MALFORMED",
                    severity="error" if metadata_mode == "require" else "warn",
                    message="Malformed whitelist entry. Expected path|owner|expire_date|reason.",
                    raw=raw,
                )
            )
            continue

        if not path_value:
            issues.append(
                WhitelistIssue(
                    line=line_no,
                    code="WHITELIST_PATH_EMPTY",
                    severity="error" if metadata_mode == "require" else "warn",
                    message="Whitelist entry path is empty.",
                    raw=raw,
                )
            )
            continue

        if path_value in seen_paths:
            issues.append(
                WhitelistIssue(
                    line=line_no,
                    code="WHITELIST_DUPLICATE_PATH",
                    severity="error" if metadata_mode == "require" else "warn",
                    message=f"Duplicate whitelist path: {path_value}",
                    raw=raw,
                )
            )
        seen_paths.add(path_value)
        allowed.add(path_value)

        if metadata_mode != "off":
            if not owner:
                issues.append(
                    WhitelistIssue(
                        line=line_no,
                        code="WHITELIST_OWNER_MISSING",
                        severity=_severity_for_metadata_issue(metadata_mode),
                        message="Whitelist owner is required.",
                        raw=raw,
                    )
                )
            if not reason:
                issues.append(
                    WhitelistIssue(
                        line=line_no,
                        code="WHITELIST_REASON_MISSING",
                        severity=_severity_for_metadata_issue(metadata_mode),
                        message="Whitelist reason is required.",
                        raw=raw,
                    )
                )

            parsed_date: date | None = None
            if expire_date:
                try:
                    parsed_date = date.fromisoformat(expire_date)
                except ValueError:
                    issues.append(
                        WhitelistIssue(
                            line=line_no,
                            code="WHITELIST_EXPIRE_DATE_INVALID",
                            severity=_severity_for_metadata_issue(metadata_mode),
                            message=f"expire_date must be YYYY-MM-DD: {expire_date}",
                            raw=raw,
                        )
                    )
            else:
                issues.append(
                    WhitelistIssue(
                        line=line_no,
                        code="WHITELIST_EXPIRE_DATE_MISSING",
                        severity=_severity_for_metadata_issue(metadata_mode),
                        message="Whitelist expire_date is required.",
                        raw=raw,
                    )
                )

            if parsed_date and parsed_date < today_value:
                issues.append(
                    WhitelistIssue(
                        line=line_no,
                        code="WHITELIST_ENTRY_EXPIRED",
                        severity=_severity_for_metadata_issue(metadata_mode),
                        message=f"Whitelist entry expired on {expire_date}.",
                        raw=raw,
                    )
                )

        entries.append(
            {
                "line": str(line_no),
                "path": path_value,
                "owner": owner,
                "expire_date": expire_date,
                "reason": reason,
            }
        )

    return allowed, entries, issues

