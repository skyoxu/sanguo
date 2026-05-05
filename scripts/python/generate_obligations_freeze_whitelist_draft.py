#!/usr/bin/env python3
"""
Generate obligations freeze whitelist draft from jitter summary.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
from datetime import timezone
from pathlib import Path


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def today_str() -> str:
    return dt.date.today().strftime("%Y-%m-%d")


def resolve_repo_path(path_text: str) -> Path:
    path = Path(path_text)
    if path.is_absolute():
        return path
    return repo_root() / path


def find_latest_jitter_summary() -> Path | None:
    root = repo_root()
    candidates = sorted(
        root.glob("logs/ci/*/sc-llm-obligations-jitter-batch5x3-summary.json"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    return candidates[0] if candidates else None


def format_task_ids(task_ids: list[int]) -> str:
    if not task_ids:
        return "-"
    return ", ".join(f"T{task_id}" for task_id in task_ids)


def parse_args() -> argparse.Namespace:
    today = today_str()
    parser = argparse.ArgumentParser(description="Generate obligations freeze whitelist draft from jitter summary.")
    parser.add_argument(
        "--summary",
        default="",
        help="Input jitter summary JSON path. Default: latest logs/ci/*/sc-llm-obligations-jitter-batch5x3-summary.json",
    )
    parser.add_argument(
        "--out-json",
        default=".taskmaster/config/obligations-freeze-whitelist.draft.json",
        help="Output whitelist draft JSON path (repo-relative or absolute).",
    )
    parser.add_argument(
        "--out-md",
        default=f"logs/ci/{today}/sc-obligations-freeze-whitelist-draft.md",
        help="Output markdown report path (repo-relative or absolute).",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = repo_root()

    source_summary = resolve_repo_path(args.summary) if str(args.summary).strip() else find_latest_jitter_summary()
    if source_summary is None or not source_summary.exists():
        print("ERROR: jitter summary not found. Use --summary to provide one explicitly.")
        return 2

    data = json.loads(source_summary.read_text(encoding="utf-8"))
    task_stats = data.get("task_stats", [])
    if not isinstance(task_stats, list):
        print("ERROR: invalid summary format, task_stats must be a list.")
        return 2

    stable_ok = sorted(int(task["task_id"]) for task in task_stats if task.get("stability") == "stable_ok")
    stable_fail = sorted(int(task["task_id"]) for task in task_stats if task.get("stability") == "stable_fail")
    jitter_ok_majority = sorted(
        int(task["task_id"]) for task in task_stats if task.get("stability") == "jitter_ok_majority"
    )
    jitter_fail_majority = sorted(
        int(task["task_id"]) for task in task_stats if task.get("stability") == "jitter_fail_majority"
    )

    draft_payload = {
        "schema_version": "1.0-draft",
        "generated_at": dt.datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "source": {
            "summary_file": str(source_summary.relative_to(root)).replace("\\", "/"),
            "method": "llm_extract_task_obligations batch_size=5 rounds=3",
        },
        "policy": {
            "default_mode": "single_run",
            "jitter_mode": "three_run_majority",
            "majority_pass_rule": "at least 2/3 runs verdict=ok",
            "majority_fail_rule": "at least 2/3 runs verdict=fail",
            "tie_rule": "mark_unknown_and_recheck",
            "freeze_invalidation": [
                "acceptance_changed",
                "master_details_changed",
                "tooling_or_prompt_changed",
            ],
        },
        "task_sets": {
            "stable_ok": stable_ok,
            "jitter_ok_majority": jitter_ok_majority,
            "jitter_fail_majority": jitter_fail_majority,
            "stable_fail": stable_fail,
        },
        "ops_recommendation": {
            "watchlist": sorted(set(jitter_fail_majority + stable_fail)),
            "auto_rerun_on_single_fail": jitter_ok_majority,
            "blocked_until_fix": sorted(set(jitter_fail_majority + stable_fail)),
            "notes": [
                "This is a draft whitelist baseline, not a permanent gate bypass.",
                "Any acceptance/content change invalidates the freeze baseline.",
            ],
        },
    }

    draft_json = resolve_repo_path(args.out_json)
    draft_json.parent.mkdir(parents=True, exist_ok=True)
    draft_json.write_text(json.dumps(draft_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    draft_md = resolve_repo_path(args.out_md)
    markdown_lines = [
        "# Obligations Freeze Whitelist Draft",
        "",
        f"- Source: {str(source_summary.relative_to(root)).replace('\\', '/')}",
        "- Method: llm_extract_task_obligations, batch_size=5, rounds=3",
        "",
        f"- stable_ok ({len(stable_ok)}): {format_task_ids(stable_ok)}",
        f"- jitter_ok_majority ({len(jitter_ok_majority)}): {format_task_ids(jitter_ok_majority)}",
        f"- jitter_fail_majority ({len(jitter_fail_majority)}): {format_task_ids(jitter_fail_majority)}",
        f"- stable_fail ({len(stable_fail)}): {format_task_ids(stable_fail)}",
        "",
        "## Draft Rules",
        "- Stable OK: run once by default; rerun only when acceptance/master content changes.",
        "- Jitter OK Majority: on first fail, auto-rerun to 3 rounds and use 2/3 majority.",
        "- Jitter/Stable Fail: block acceptance until semantic gap is fixed.",
        "- Any acceptance hash change invalidates frozen baseline.",
        "",
        "## Stop-Loss Note",
        "- This whitelist is an execution-stability baseline, not a semantic-quality bypass.",
        "- Do not use whitelist to skip obligations coverage checks.",
    ]
    draft_md.parent.mkdir(parents=True, exist_ok=True)
    draft_md.write_text("\n".join(markdown_lines) + "\n", encoding="utf-8")

    print(f"wrote {draft_json.as_posix()}")
    print(f"wrote {draft_md.as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
