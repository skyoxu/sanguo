#!/usr/bin/env python3
"""
Refresh obligations jitter summary by overriding selected tasks with newer rerun results.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
from collections import Counter, defaultdict
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


def parse_args() -> argparse.Namespace:
    today = today_str()
    parser = argparse.ArgumentParser(description="Refresh jitter summary with targeted rerun overrides.")
    parser.add_argument(
        "--base-summary",
        default="",
        help="Base full jitter summary JSON. Default: latest logs/ci/*/sc-llm-obligations-jitter-batch5x3-summary.json",
    )
    parser.add_argument(
        "--override-rerun",
        required=True,
        help="Targeted rerun JSON containing rows with task_id/round/verdict_status.",
    )
    parser.add_argument(
        "--out-summary",
        default=f"logs/ci/{today}/sc-llm-obligations-jitter-batch5x3-summary-refreshed.json",
        help="Output refreshed summary JSON path.",
    )
    parser.add_argument(
        "--out-report",
        default=f"logs/ci/{today}/sc-llm-obligations-jitter-batch5x3-refreshed-report.md",
        help="Output refreshed markdown report path.",
    )
    return parser.parse_args()


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def decide_stability(verdict_seq: list[str], majority_verdict: str) -> str:
    verdict_jitter = len(set(verdict_seq)) > 1
    if majority_verdict == "ok" and not verdict_jitter:
        return "stable_ok"
    if majority_verdict == "fail" and not verdict_jitter:
        return "stable_fail"
    if majority_verdict == "ok" and verdict_jitter:
        return "jitter_ok_majority"
    if majority_verdict == "fail" and verdict_jitter:
        return "jitter_fail_majority"
    return "unknown"


def refresh_task_stat(existing: dict, rerun_rows: list[dict]) -> dict:
    rerun_rows = sorted(rerun_rows, key=lambda item: int(item.get("round", 0)))
    verdict_sequence = [str(item.get("verdict_status", "unknown")) for item in rerun_rows]
    summary_rc_sequence = [int(item.get("summary_rc", 0)) for item in rerun_rows]
    uncovered_sequence = [int(item.get("uncovered_count", 0)) for item in rerun_rows]
    uncovered_ids_sequence = []
    for item in rerun_rows:
        ids = item.get("uncovered_ids", [])
        if not isinstance(ids, list):
            ids = []
        uncovered_ids_sequence.append("[" + ",".join(str(x) for x in ids) + "]")

    verdict_counts = Counter(verdict_sequence)
    summary_rc_counts = Counter(str(value) for value in summary_rc_sequence)
    majority_verdict = verdict_counts.most_common(1)[0][0] if verdict_counts else "unknown"
    stability = decide_stability(verdict_sequence, majority_verdict)

    refreshed = dict(existing)
    refreshed["runs"] = len(rerun_rows)
    refreshed["verdict_sequence"] = verdict_sequence
    refreshed["summary_rc_sequence"] = summary_rc_sequence
    refreshed["uncovered_sequence"] = uncovered_sequence
    refreshed["uncovered_ids_sequence"] = uncovered_ids_sequence
    refreshed["verdict_counts"] = dict(verdict_counts)
    refreshed["summary_rc_counts"] = dict(summary_rc_counts)
    refreshed["majority_verdict"] = majority_verdict
    refreshed["verdict_jitter"] = len(set(verdict_sequence)) > 1
    refreshed["summary_rc_jitter"] = len(set(summary_rc_sequence)) > 1
    refreshed["uncovered_jitter"] = len(set(uncovered_sequence)) > 1 or len(set(uncovered_ids_sequence)) > 1
    refreshed["stability"] = stability
    return refreshed


def recompute_aggregate(task_stats: list[dict]) -> dict:
    return {
        "rows_total": sum(int(task.get("runs", 0)) for task in task_stats),
        "tasks_total": len(task_stats),
        "rounds_per_task": int(task_stats[0].get("runs", 0)) if task_stats else 0,
        "stable_ok": sum(1 for task in task_stats if task.get("stability") == "stable_ok"),
        "stable_fail": sum(1 for task in task_stats if task.get("stability") == "stable_fail"),
        "jitter_ok_majority": sum(1 for task in task_stats if task.get("stability") == "jitter_ok_majority"),
        "jitter_fail_majority": sum(1 for task in task_stats if task.get("stability") == "jitter_fail_majority"),
        "verdict_jitter_tasks": [task["task_id"] for task in task_stats if task.get("verdict_jitter")],
        "uncovered_jitter_tasks": [task["task_id"] for task in task_stats if task.get("uncovered_jitter")],
        "summary_rc_jitter_tasks": [task["task_id"] for task in task_stats if task.get("summary_rc_jitter")],
    }


def recompute_batch_stats(base_batch_stats: list[dict], task_stats: list[dict]) -> list[dict]:
    tasks_by_group: dict[int, list[dict]] = defaultdict(list)
    for task in task_stats:
        group = int(task.get("group", 0))
        tasks_by_group[group].append(task)

    refreshed_batches: list[dict] = []
    for batch in sorted(base_batch_stats, key=lambda item: int(item.get("group", 0))):
        group = int(batch.get("group", 0))
        items = sorted(tasks_by_group.get(group, []), key=lambda task: int(task.get("task_id", 0)))
        refreshed_batches.append(
            {
                "group": group,
                "task_ids": batch.get("task_ids", []),
                "tasks": len(items),
                "stable_ok": sum(1 for task in items if task.get("stability") == "stable_ok"),
                "stable_fail": sum(1 for task in items if task.get("stability") == "stable_fail"),
                "jitter_ok_majority": sum(1 for task in items if task.get("stability") == "jitter_ok_majority"),
                "jitter_fail_majority": sum(1 for task in items if task.get("stability") == "jitter_fail_majority"),
                "jitter_tasks": [
                    task["task_id"]
                    for task in items
                    if task.get("verdict_jitter") or task.get("uncovered_jitter") or task.get("summary_rc_jitter")
                ],
            }
        )
    return refreshed_batches


def build_report(aggregate: dict, batch_stats: list[dict], task_stats: list[dict], overridden_ids: list[int]) -> str:
    lines: list[str] = []
    lines.append("# Obligations Jitter Report (Refreshed)")
    lines.append("")
    lines.append(f"- overridden_tasks: {', '.join(f'T{task_id}' for task_id in overridden_ids)}")
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
            f"- Group {batch['group']} {batch['task_ids']}: "
            f"stable_ok={batch['stable_ok']}, stable_fail={batch['stable_fail']}, "
            f"jitter_ok_majority={batch['jitter_ok_majority']}, jitter_fail_majority={batch['jitter_fail_majority']}, "
            f"jitter_tasks={batch['jitter_tasks']}"
        )
    lines.append("")
    lines.append("## Overridden Task Details")
    for task in sorted(
        (task for task in task_stats if int(task.get("task_id")) in overridden_ids),
        key=lambda x: int(x["task_id"]),
    ):
        lines.append(
            f"- T{task['task_id']}: stability={task['stability']}, majority={task['majority_verdict']}, "
            f"verdict_seq={task['verdict_sequence']}, uncovered_seq={task['uncovered_sequence']}, "
            f"rc_seq={task['summary_rc_sequence']}"
        )
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    args = parse_args()
    base_summary_path = resolve_repo_path(args.base_summary) if str(args.base_summary).strip() else find_latest_jitter_summary()
    override_path = resolve_repo_path(args.override_rerun)
    out_summary_path = resolve_repo_path(args.out_summary)
    out_report_path = resolve_repo_path(args.out_report)

    if base_summary_path is None or not base_summary_path.exists():
        print("ERROR: base summary not found. Use --base-summary to provide one explicitly.")
        return 2
    if not override_path.exists():
        print(f"ERROR: override rerun file not found: {override_path.as_posix()}")
        return 2

    base_summary = load_json(base_summary_path)
    override = load_json(override_path)

    task_stats = base_summary.get("task_stats", [])
    task_map: dict[int, dict] = {int(task["task_id"]): task for task in task_stats}

    override_rows = override.get("rows", [])
    rows_by_task: dict[int, list[dict]] = defaultdict(list)
    for row in override_rows:
        rows_by_task[int(row.get("task_id"))].append(row)

    overridden_ids = sorted(rows_by_task.keys())
    for task_id, rows in rows_by_task.items():
        if task_id not in task_map:
            continue
        task_map[task_id] = refresh_task_stat(task_map[task_id], rows)

    refreshed_task_stats = [task_map[task_id] for task_id in sorted(task_map.keys())]
    refreshed_aggregate = recompute_aggregate(refreshed_task_stats)
    refreshed_batches = recompute_batch_stats(base_summary.get("batch_stats", []), refreshed_task_stats)

    refreshed = {
        "source": {
            "base_summary": str(base_summary_path.relative_to(repo_root())).replace("\\", "/"),
            "override_rerun": str(override_path.relative_to(repo_root())).replace("\\", "/"),
        },
        "aggregate": refreshed_aggregate,
        "batch_stats": refreshed_batches,
        "task_stats": refreshed_task_stats,
        "overridden_task_ids": overridden_ids,
    }

    out_summary_path.parent.mkdir(parents=True, exist_ok=True)
    out_summary_path.write_text(json.dumps(refreshed, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    report_text = build_report(refreshed_aggregate, refreshed_batches, refreshed_task_stats, overridden_ids)
    out_report_path.parent.mkdir(parents=True, exist_ok=True)
    out_report_path.write_text(report_text + "\n", encoding="utf-8")

    print(f"wrote {out_summary_path.as_posix()}")
    print(f"wrote {out_report_path.as_posix()}")
    print(f"overridden_tasks={overridden_ids}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
