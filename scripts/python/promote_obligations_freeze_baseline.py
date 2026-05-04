#!/usr/bin/env python3
"""
Promote obligations freeze whitelist draft to immutable dated baseline.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
from datetime import timezone
from pathlib import Path


REQUIRED_TASK_SET_KEYS = (
    "stable_ok",
    "jitter_ok_majority",
    "jitter_fail_majority",
    "stable_fail",
)


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def resolve_repo_path(path_text: str) -> Path:
    path = Path(path_text)
    if path.is_absolute():
        return path
    return repo_root() / path


def parse_args() -> argparse.Namespace:
    today = dt.date.today().isoformat()
    parser = argparse.ArgumentParser(description="Promote freeze whitelist draft to immutable baseline.")
    parser.add_argument(
        "--draft",
        default=".taskmaster/config/obligations-freeze-whitelist.draft.json",
        help="Path to whitelist draft JSON.",
    )
    parser.add_argument(
        "--baseline-dir",
        default=".taskmaster/config/obligations-freeze-baselines",
        help="Directory to store immutable dated baselines.",
    )
    parser.add_argument(
        "--baseline-date",
        default=today,
        help="Baseline date (YYYY-MM-DD). Default: today.",
    )
    parser.add_argument(
        "--baseline-tag",
        default="",
        help="Optional baseline tag suffix, e.g. r1/r2/hotfix (letters, numbers, '_' or '-').",
    )
    parser.add_argument(
        "--current",
        default=".taskmaster/config/obligations-freeze-whitelist.baseline.current.json",
        help="Path to current promoted baseline pointer JSON.",
    )
    parser.add_argument(
        "--report",
        default=f"logs/ci/{today}/sc-obligations-freeze-promote.md",
        help="Path to promotion report markdown.",
    )
    return parser.parse_args()


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def ensure_task_sets(payload: dict) -> None:
    task_sets = payload.get("task_sets")
    if not isinstance(task_sets, dict):
        raise ValueError("draft JSON missing task_sets object")
    for key in REQUIRED_TASK_SET_KEYS:
        value = task_sets.get(key)
        if not isinstance(value, list):
            raise ValueError(f"draft JSON task_sets.{key} must be a list")


def normalize_iso_utc_now() -> str:
    return dt.datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def normalize_baseline_tag(raw: str) -> str:
    tag = (raw or "").strip()
    if not tag:
        return ""
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,31}", tag):
        raise ValueError("invalid --baseline-tag, allowed: [A-Za-z0-9][A-Za-z0-9_-]{0,31}")
    return tag


def make_baseline_payload(
    draft: dict,
    *,
    draft_path: Path,
    baseline_file_rel: str,
    baseline_date: str,
    baseline_slug: str,
    baseline_tag: str,
) -> dict:
    payload = dict(draft)
    payload["schema_version"] = "1.0-baseline"
    payload["promoted_at"] = normalize_iso_utc_now()
    payload["promoted_from"] = str(draft_path).replace("\\", "/")
    payload["baseline"] = {
        "id": f"obligations-freeze-whitelist-{baseline_slug}",
        "date": baseline_date,
        "tag": baseline_tag,
        "immutable": True,
        "baseline_file": baseline_file_rel,
    }
    return payload


def build_current_payload(
    baseline_payload: dict,
    *,
    baseline_file_rel: str,
    baseline_sha256: str,
) -> dict:
    payload = dict(baseline_payload)
    payload["current_pointer"] = {
        "updated_at": normalize_iso_utc_now(),
        "baseline_file": baseline_file_rel,
        "baseline_sha256": baseline_sha256,
    }
    return payload


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def format_task_count_list(task_sets: dict, key: str) -> str:
    items = task_sets.get(key, [])
    return f"{key}: {len(items)}"


def main() -> int:
    args = parse_args()

    draft_path = resolve_repo_path(args.draft)
    baseline_dir = resolve_repo_path(args.baseline_dir)
    current_path = resolve_repo_path(args.current)
    report_path = resolve_repo_path(args.report)

    baseline_date = args.baseline_date.strip()
    try:
        dt.date.fromisoformat(baseline_date)
    except ValueError:
        print(f"ERROR: invalid --baseline-date {baseline_date!r}, expected YYYY-MM-DD")
        return 2
    try:
        baseline_tag = normalize_baseline_tag(args.baseline_tag)
    except ValueError as exc:
        print(f"ERROR: {exc}")
        return 2

    if not draft_path.exists():
        print(f"ERROR: draft file not found: {draft_path.as_posix()}")
        return 2

    draft_payload = load_json(draft_path)
    ensure_task_sets(draft_payload)

    baseline_slug = baseline_date if not baseline_tag else f"{baseline_date}-{baseline_tag}"
    baseline_name = f"obligations-freeze-whitelist-{baseline_slug}.json"
    baseline_path = baseline_dir / baseline_name
    baseline_file_rel = str((Path(args.baseline_dir) / baseline_name)).replace("\\", "/")

    if baseline_path.exists():
        print(f"ERROR: immutable baseline already exists: {baseline_path.as_posix()}")
        return 3

    baseline_payload = make_baseline_payload(
        draft_payload,
        draft_path=Path(args.draft),
        baseline_file_rel=baseline_file_rel,
        baseline_date=baseline_date,
        baseline_slug=baseline_slug,
        baseline_tag=baseline_tag,
    )

    baseline_text = json.dumps(baseline_payload, ensure_ascii=False, indent=2) + "\n"
    baseline_sha256 = sha256_text(baseline_text)
    baseline_dir.mkdir(parents=True, exist_ok=True)
    baseline_path.write_text(baseline_text, encoding="utf-8")

    current_payload = build_current_payload(
        baseline_payload,
        baseline_file_rel=baseline_file_rel,
        baseline_sha256=baseline_sha256,
    )
    current_path.parent.mkdir(parents=True, exist_ok=True)
    current_path.write_text(json.dumps(current_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    task_sets = baseline_payload.get("task_sets", {})
    report_lines = [
        "# Obligations Freeze Baseline Promotion",
        "",
        f"- promoted_at: {baseline_payload.get('promoted_at', '')}",
        f"- draft: {str(Path(args.draft)).replace('\\\\', '/')}",
        f"- baseline: {baseline_file_rel}",
        f"- current: {str(Path(args.current)).replace('\\\\', '/')}",
        f"- baseline_sha256: {baseline_sha256}",
        "",
        "## Task Sets",
        f"- {format_task_count_list(task_sets, 'stable_ok')}",
        f"- {format_task_count_list(task_sets, 'jitter_ok_majority')}",
        f"- {format_task_count_list(task_sets, 'jitter_fail_majority')}",
        f"- {format_task_count_list(task_sets, 'stable_fail')}",
        "",
        "## Stop-Loss",
        "- Dated/tagged baseline file is immutable: rerunning same baseline-date + baseline-tag will fail.",
        "- Current pointer can move only via explicit promote command.",
    ]
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(report_lines) + "\n", encoding="utf-8")

    print(f"wrote {baseline_path.as_posix()}")
    print(f"wrote {current_path.as_posix()}")
    print(f"wrote {report_path.as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
