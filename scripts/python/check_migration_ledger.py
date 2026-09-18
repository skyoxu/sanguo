#!/usr/bin/env python3
"""Validate the upstream migration ledger and reject duplicate canonical migration PRs."""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.request
from pathlib import Path
from typing import Any

DEFAULT_LEDGER = Path("docs/migration/upstream-sync-ledger.json")
SCHEMA = "sanguo.upstream-migration-ledger.v1"
SHA_RE = re.compile(r"^[0-9a-f]{40}$")
KEY_RE = re.compile(r"^[^\s]+@[0-9a-f]{40}->[^\s]+$")
MARKER_RE = re.compile(r"(?mi)^Migration-Key:\s*(\S+)\s*$")
ACTIVE_STATUSES = {"open", "merged"}
ALL_STATUSES = ACTIVE_STATUSES | {"closed", "superseded"}
MODES = {"exact-copy", "adapted", "excluded"}


def load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError("ledger root must be an object")
    return payload


def extract_migration_key(body: str) -> str:
    match = MARKER_RE.search(body or "")
    return match.group(1) if match else ""


def validate_ledger(doc: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if doc.get("schema_version") != SCHEMA:
        errors.append("unsupported schema_version")
    source_repo = str(doc.get("source_repository") or "").strip()
    target_repo = str(doc.get("target_repository") or "").strip()
    if "/" not in source_repo or "/" not in target_repo:
        errors.append("source_repository and target_repository must be owner/name")
    records = doc.get("records")
    if not isinstance(records, list) or not records:
        return errors + ["records must be a non-empty array"]

    ids: set[str] = set()
    keys: set[str] = set()
    target_prs: set[int] = set()
    active_source_commits: dict[str, str] = {}

    for index, raw in enumerate(records):
        label = f"records[{index}]"
        if not isinstance(raw, dict):
            errors.append(f"{label}: must be an object")
            continue

        record_id = str(raw.get("id") or "")
        if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", record_id):
            errors.append(f"{label}: invalid id")
        elif record_id in ids:
            errors.append(f"{label}: duplicate id {record_id}")
        ids.add(record_id)

        key = str(raw.get("migration_key") or "")
        if not KEY_RE.fullmatch(key):
            errors.append(f"{label}: invalid migration_key")
        elif key in keys:
            errors.append(f"{label}: duplicate migration_key {key}")
        keys.add(key)

        source_commits = raw.get("source_commits")
        if not isinstance(source_commits, list) or not source_commits:
            errors.append(f"{label}: source_commits must be non-empty")
            source_commits = []
        for sha in source_commits:
            if not isinstance(sha, str) or not SHA_RE.fullmatch(sha):
                errors.append(f"{label}: invalid source commit {sha!r}")

        target_base = raw.get("target_base")
        if not isinstance(target_base, str) or not SHA_RE.fullmatch(target_base):
            errors.append(f"{label}: invalid target_base")

        target_pr = raw.get("target_pr")
        if type(target_pr) is not int or target_pr < 1:
            errors.append(f"{label}: target_pr must be a positive integer")
        elif target_pr in target_prs:
            errors.append(f"{label}: duplicate target_pr {target_pr}")
        else:
            target_prs.add(target_pr)

        branch = str(raw.get("target_branch") or "")
        if not branch or branch.startswith("/") or ".." in branch:
            errors.append(f"{label}: invalid target_branch")

        status = raw.get("status")
        if status not in ALL_STATUSES:
            errors.append(f"{label}: invalid status")
        mode = raw.get("mode")
        if mode not in MODES:
            errors.append(f"{label}: invalid mode")

        scope = raw.get("scope")
        if not isinstance(scope, list) or not scope or not all(isinstance(x, str) and x.strip() for x in scope):
            errors.append(f"{label}: scope must be a non-empty string array")
        excluded = raw.get("excluded")
        if not isinstance(excluded, list) or not all(isinstance(x, str) and x.strip() for x in excluded):
            errors.append(f"{label}: excluded must be a string array")

        if status in ACTIVE_STATUSES:
            for sha in source_commits:
                previous = active_source_commits.get(sha)
                if previous and previous != record_id:
                    errors.append(f"{label}: source commit {sha} already active in {previous}")
                active_source_commits[sha] = record_id

        if key and source_commits:
            expected_prefix = f"{source_repo}@{source_commits[-1]}->{target_repo}"
            if key != expected_prefix:
                errors.append(f"{label}: migration_key must bind the latest source commit")

    return errors


def current_pr_from_event(event_path: str) -> dict[str, Any]:
    if not event_path:
        return {}
    path = Path(event_path)
    if not path.is_file():
        return {}
    payload = load_json(path)
    pr = payload.get("pull_request")
    return pr if isinstance(pr, dict) else {}


def find_record_for_pr(doc: dict[str, Any], pr: dict[str, Any]) -> dict[str, Any] | None:
    number = pr.get("number")
    head = pr.get("head") if isinstance(pr.get("head"), dict) else {}
    branch = str(head.get("ref") or "")
    body_key = extract_migration_key(str(pr.get("body") or ""))
    candidates = [
        row for row in doc.get("records", [])
        if isinstance(row, dict)
        and (row.get("target_pr") == number or row.get("target_branch") == branch or row.get("migration_key") == body_key)
    ]
    if len(candidates) != 1:
        return None
    return candidates[0]


def list_open_prs(repository: str, token: str) -> list[dict[str, Any]]:
    if not repository or not token:
        raise ValueError("GITHUB_REPOSITORY and GITHUB_TOKEN are required for duplicate PR checks")
    output: list[dict[str, Any]] = []
    page = 1
    while True:
        url = f"https://api.github.com/repos/{repository}/pulls?state=open&per_page=100&page={page}"
        request = urllib.request.Request(
            url,
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
                "User-Agent": "sanguo-migration-ledger-check",
            },
        )
        with urllib.request.urlopen(request, timeout=20) as response:
            rows = json.loads(response.read().decode("utf-8"))
        if not isinstance(rows, list):
            raise ValueError("GitHub pulls response must be an array")
        output.extend(row for row in rows if isinstance(row, dict))
        if len(rows) < 100:
            break
        page += 1
    return output


def duplicate_pr_errors(record: dict[str, Any], current_pr: dict[str, Any],
                        open_prs: list[dict[str, Any]]) -> list[str]:
    errors: list[str] = []
    expected_key = str(record.get("migration_key") or "")
    current_key = extract_migration_key(str(current_pr.get("body") or ""))
    if current_key != expected_key:
        errors.append("current PR Migration-Key marker does not match ledger")
    matching = [
        row for row in open_prs
        if extract_migration_key(str(row.get("body") or "")) == expected_key
    ]
    if len(matching) != 1:
        numbers = [row.get("number") for row in matching]
        errors.append(f"expected exactly one open PR for migration_key; found {numbers}")
    elif matching[0].get("number") != current_pr.get("number"):
        errors.append("canonical open PR does not match current PR")
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ledger", default=str(DEFAULT_LEDGER))
    parser.add_argument("--check-open-prs", action="store_true")
    args = parser.parse_args(argv)

    try:
        doc = load_json(Path(args.ledger))
        errors = validate_ledger(doc)
        if args.check_open_prs:
            current_pr = current_pr_from_event(os.environ.get("GITHUB_EVENT_PATH", ""))
            if not current_pr:
                errors.append("pull_request event payload is required for duplicate PR checks")
            else:
                record = find_record_for_pr(doc, current_pr)
                if record is None:
                    errors.append("current PR does not map uniquely to a ledger record")
                else:
                    open_prs = list_open_prs(
                        os.environ.get("GITHUB_REPOSITORY", ""),
                        os.environ.get("GITHUB_TOKEN", ""),
                    )
                    errors.extend(duplicate_pr_errors(record, current_pr, open_prs))
        if errors:
            for error in errors:
                print(f"MIGRATION_LEDGER error={error}")
            return 1
        print(f"MIGRATION_LEDGER status=ok records={len(doc.get('records', []))}")
        return 0
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"MIGRATION_LEDGER error={exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
