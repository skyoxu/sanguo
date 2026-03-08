#!/usr/bin/env python3
"""
Build obligations jitter summary/report from raw batch rows.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def today_str() -> str:
    return dt.date.today().strftime("%Y-%m-%d")


def resolve_repo_path(path_text: str) -> Path:
    path = Path(path_text)
    if path.is_absolute():
        return path
    return repo_root() / path


def parse_args() -> argparse.Namespace:
    today = today_str()
    parser = argparse.ArgumentParser(description="Build obligations jitter summary from raw rows.")
    parser.add_argument(
        "--raw",
        required=True,
        help="Raw JSON path from batch run (repo-relative or absolute).",
    )
    parser.add_argument(
        "--out-summary",
        default=f"logs/ci/{today}/sc-llm-obligations-jitter-batch5x3-summary.json",
        help="Output summary JSON path (repo-relative or absolute).",
    )
    parser.add_argument(
        "--out-report",
        default=f"logs/ci/{today}/sc-llm-obligations-jitter-batch5x3-report.md",
        help="Output markdown report path (repo-relative or absolute).",
    )
    return parser.parse_args()


def decide_stability(verdict_sequence: list[str], majority_verdict: str) -> str:
    verdict_jitter = len(set(verdict_sequence)) > 1
    if majority_verdict == "ok" and not verdict_jitter:
        return "stable_ok"
    if majority_verdict == "fail" and not verdict_jitter:
        return "stable_fail"
    if majority_verdict == "ok" and verdict_jitter:
        return "jitter_ok_majority"
    if majority_verdict == "fail" and verdict_jitter:
        return "jitter_fail_majority"
    return "unknown"


def summarize_task(rows: list[dict[str, Any]]) -> dict[str, Any]:
    rows_sorted = sorted(rows, key=lambda row: (int(row["group"]), int(row["round"])))
    verdict_sequence = [str(row.get("verdict_status", "unknown")) for row in rows_sorted]
    summary_rc_sequence = [int(row.get("summary_rc", 0) or 0) for row in rows_sorted]
    uncovered_sequence = [int(row.get("uncovered_count", 0) or 0) for row in rows_sorted]
    uncovered_ids_sequence = []
    for row in rows_sorted:
        ids = row.get("uncovered_ids", [])
        if not isinstance(ids, list):
            ids = []
        uncovered_ids_sequence.append("[" + ",".join(str(item) for item in ids) + "]")

    verdict_counts = Counter(verdict_sequence)
    summary_rc_counts = Counter(str(value) for value in summary_rc_sequence)
    majority_verdict = verdict_counts.most_common(1)[0][0] if verdict_counts else "unknown"
    stability = decide_stability(verdict_sequence, majority_verdict)

    return {
        "task_id": int(rows_sorted[0]["task_id"]),
        "group": int(rows_sorted[0]["group"]),
        "runs": len(rows_sorted),
        "verdict_sequence": verdict_sequence,
        "summary_rc_sequence": summary_rc_sequence,
        "uncovered_sequence": uncovered_sequence,
        "uncovered_ids_sequence": uncovered_ids_sequence,
        "verdict_counts": dict(verdict_counts),
        "summary_rc_counts": dict(summary_rc_counts),
        "majority_verdict": majority_verdict,
        "verdict_jitter": len(set(verdict_sequence)) > 1,
        "summary_rc_jitter": len(set(summary_rc_sequence)) > 1,
        "uncovered_jitter": len(set(uncovered_sequence)) > 1 or len(set(uncovered_ids_sequence)) > 1,
        "stability": stability,
    }


def build_batch_stats(groups: list[list[int]], task_stats: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_group: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for task in task_stats:
        by_group[int(task["group"])].append(task)

    batch_stats: list[dict[str, Any]] = []
    for index, group in enumerate(groups, start=1):
        tasks = sorted(by_group.get(index, []), key=lambda item: int(item["task_id"]))
        batch_stats.append(
            {
                "group": index,
                "task_ids": group,
                "tasks": len(tasks),
                "stable_ok": sum(1 for task in tasks if task["stability"] == "stable_ok"),
                "stable_fail": sum(1 for task in tasks if task["stability"] == "stable_fail"),
                "jitter_ok_majority": sum(1 for task in tasks if task["stability"] == "jitter_ok_majority"),
                "jitter_fail_majority": sum(1 for task in tasks if task["stability"] == "jitter_fail_majority"),
                "jitter_tasks": [
                    task["task_id"]
                    for task in tasks
                    if task["verdict_jitter"] or task["uncovered_jitter"] or task["summary_rc_jitter"]
                ],
            }
        )
    return batch_stats


def build_aggregate(task_stats: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "rows_total": sum(int(task["runs"]) for task in task_stats),
        "tasks_total": len(task_stats),
        "rounds_per_task": int(task_stats[0]["runs"]) if task_stats else 0,
        "stable_ok": sum(1 for task in task_stats if task["stability"] == "stable_ok"),
        "stable_fail": sum(1 for task in task_stats if task["stability"] == "stable_fail"),
        "jitter_ok_majority": sum(1 for task in task_stats if task["stability"] == "jitter_ok_majority"),
        "jitter_fail_majority": sum(1 for task in task_stats if task["stability"] == "jitter_fail_majority"),
        "verdict_jitter_tasks": [task["task_id"] for task in task_stats if task["verdict_jitter"]],
        "uncovered_jitter_tasks": [task["task_id"] for task in task_stats if task["uncovered_jitter"]],
        "summary_rc_jitter_tasks": [task["task_id"] for task in task_stats if task["summary_rc_jitter"]],
    }


def build_report_markdown(aggregate: dict[str, Any], batch_stats: list[dict[str, Any]], task_stats: list[dict[str, Any]]) -> str:
    lines: list[str] = []
    lines.append("# Obligations Jitter Report (Batch=5, Rounds=3)")
    lines.append("")
    lines.append(f"- rows_total: {aggregate['rows_total']}")
    lines.append(f"- tasks_total: {aggregate['tasks_total']}")
    lines.append(f"- stable_ok: {aggregate['stable_ok']}")
    lines.append(f"- stable_fail: {aggregate['stable_fail']}")
    lines.append(f"- jitter_ok_majority: {aggregate['jitter_ok_majority']}")
    lines.append(f"- jitter_fail_majority: {aggregate['jitter_fail_majority']}")
    lines.append(
        "- verdict_jitter_tasks: "
        + (", ".join(f"T{task_id}" for task_id in aggregate["verdict_jitter_tasks"]) or "-")
    )
    lines.append(
        "- uncovered_jitter_tasks: "
        + (", ".join(f"T{task_id}" for task_id in aggregate["uncovered_jitter_tasks"]) or "-")
    )
    lines.append(
        "- summary_rc_jitter_tasks: "
        + (", ".join(f"T{task_id}" for task_id in aggregate["summary_rc_jitter_tasks"]) or "-")
    )
    lines.append("")
    lines.append("## Per Group")
    for batch in batch_stats:
        lines.append(
            f"- Group {batch['group']} {batch['task_ids']}: stable_ok={batch['stable_ok']}, "
            f"stable_fail={batch['stable_fail']}, jitter_ok_majority={batch['jitter_ok_majority']}, "
            f"jitter_fail_majority={batch['jitter_fail_majority']}, jitter_tasks={batch['jitter_tasks']}"
        )
    lines.append("")
    lines.append("## Jitter Task Details")
    for task in task_stats:
        if task["verdict_jitter"] or task["uncovered_jitter"] or task["summary_rc_jitter"]:
            lines.append(
                f"- T{task['task_id']} (G{task['group']}): stability={task['stability']}, "
                f"verdict_seq={task['verdict_sequence']}, uncovered_seq={task['uncovered_sequence']}, "
                f"rc_seq={task['summary_rc_sequence']}"
            )
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    args = parse_args()
    raw_path = resolve_repo_path(args.raw)
    out_summary = resolve_repo_path(args.out_summary)
    out_report = resolve_repo_path(args.out_report)

    if not raw_path.exists():
        print(f"ERROR: raw file not found: {raw_path.as_posix()}")
        return 2

    raw = json.loads(raw_path.read_text(encoding="utf-8"))
    rows = raw.get("rows", [])
    groups = raw.get("groups", [])
    if not isinstance(rows, list) or not isinstance(groups, list):
        print("ERROR: raw file must contain list fields: rows, groups")
        return 2

    by_task: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        if not isinstance(row, dict):
            continue
        if "task_id" not in row:
            continue
        by_task[int(row["task_id"])].append(row)

    task_stats = [summarize_task(task_rows) for _, task_rows in sorted(by_task.items(), key=lambda item: item[0])]
    batch_stats = build_batch_stats(groups, task_stats)
    aggregate = build_aggregate(task_stats)

    payload = {"aggregate": aggregate, "batch_stats": batch_stats, "task_stats": task_stats}

    out_summary.parent.mkdir(parents=True, exist_ok=True)
    out_summary.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    report = build_report_markdown(aggregate, batch_stats, task_stats)
    out_report.parent.mkdir(parents=True, exist_ok=True)
    out_report.write_text(report + "\n", encoding="utf-8")

    print(f"wrote {out_summary.as_posix()}")
    print(f"wrote {out_report.as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
