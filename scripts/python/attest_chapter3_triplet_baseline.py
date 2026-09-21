#!/usr/bin/env python3
"""Run the Chapter 3 task-triplet baseline validators and emit bound evidence."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

DEFAULT_TASK_FILES = [
    ".taskmaster/tasks/tasks.json",
    ".taskmaster/tasks/tasks_back.json",
    ".taskmaster/tasks/tasks_gameplay.json",
]
CHECKS = [
    (
        "task_links_validate",
        ["scripts/python/task_links_validate.py", "--mode", "all"],
    ),
    (
        "check_tasks_all_refs",
        ["scripts/python/check_tasks_all_refs.py"],
    ),
    (
        "validate_task_master_triplet",
        ["scripts/python/validate_task_master_triplet.py"],
    ),
    (
        "validate_semantic_review_tier",
        ["scripts/python/validate_semantic_review_tier.py", "--mode", "conservative"],
    ),
]


def sha256_file(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def git_revision(root: Path) -> str | None:
    try:
        result = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=15,
            check=True,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    value = result.stdout.strip()
    return value if len(value) == 40 else None


def task_file_manifest(root: Path) -> dict[str, dict[str, Any]]:
    manifest: dict[str, dict[str, Any]] = {}
    for value in DEFAULT_TASK_FILES:
        path = root / value
        if not path.is_file():
            raise ValueError(f"missing task triplet file: {value}")
        manifest[value] = {
            "sha256": sha256_file(path),
            "size": path.stat().st_size,
        }
    return manifest


def run_check(root: Path, name: str, args: list[str]) -> dict[str, Any]:
    script = root / args[0]
    if not script.is_file():
        return {
            "name": name,
            "status": "failed",
            "returncode": 2,
            "reason": f"missing validator: {args[0]}",
        }
    result = subprocess.run(
        [sys.executable, str(script), *args[1:]],
        cwd=root,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=300,
        check=False,
    )
    output = (result.stdout or "") + (result.stderr or "")
    return {
        "name": name,
        "status": "passed" if result.returncode == 0 else "failed",
        "returncode": result.returncode,
        "output_tail": output[-4000:],
    }


def attest(root: Path) -> dict[str, Any]:
    try:
        task_files = task_file_manifest(root)
    except ValueError as exc:
        return {
            "schema_version": "chapter3.triplet-baseline-attestation.v1",
            "generated_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
            "repository_revision": git_revision(root),
            "status": "blocked",
            "task_files": {},
            "checks": [],
            "reason": str(exc),
        }

    checks = [run_check(root, name, args) for name, args in CHECKS]
    passed = all(row.get("returncode") == 0 for row in checks)
    return {
        "schema_version": "chapter3.triplet-baseline-attestation.v1",
        "generated_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "repository_revision": git_revision(root),
        "status": "passed" if passed else "blocked",
        "task_files": task_files,
        "checks": checks,
    }


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", default=".")
    parser.add_argument(
        "--out",
        default="logs/ci/task-generation/triplet-baseline-attestation.json",
    )
    args = parser.parse_args(argv)
    root = Path(args.repo_root).resolve()
    payload = attest(root)
    out = root / args.out
    write_json(out, payload)
    print(
        f"triplet_attestation={out} status={payload['status']} "
        f"checks={len(payload.get('checks', []))}"
    )
    return 0 if payload["status"] == "passed" else 2


if __name__ == "__main__":
    raise SystemExit(main())
