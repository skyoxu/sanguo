#!/usr/bin/env python3
"""
Evaluate whether current obligations jitter results can be judged by a freeze whitelist.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


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


@dataclass
class TaskEvalResult:
    task_id: int
    whitelist_bucket: str
    observed_stability: str
    observed_majority_verdict: str
    decision: str
    reason: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate obligations freeze whitelist against observed jitter summary.")
    parser.add_argument(
        "--whitelist",
        default=".taskmaster/config/obligations-freeze-whitelist.baseline.current.json",
        help="Path to freeze whitelist baseline JSON.",
    )
    parser.add_argument(
        "--summary",
        default="",
        help="Path to observed jitter summary JSON. Default: latest logs/ci/*/sc-llm-obligations-jitter-batch5x3-summary.json",
    )
    parser.add_argument(
        "--out-dir",
        default="",
        help="Output directory. Default: logs/ci/<today>/sc-obligations-freeze-eval",
    )
    parser.add_argument(
        "--allow-draft",
        action="store_true",
        help="Allow evaluating a draft whitelist file. Disabled by default as stop-loss.",
    )
    return parser.parse_args()


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def build_whitelist_bucket_map(task_sets: dict) -> dict[int, str]:
    bucket_map: dict[int, str] = {}
    for bucket in ("stable_ok", "jitter_ok_majority", "jitter_fail_majority", "stable_fail"):
        for task_id in task_sets.get(bucket, []):
            task_id_int = int(task_id)
            if task_id_int in bucket_map:
                bucket_map[task_id_int] = "conflict"
            else:
                bucket_map[task_id_int] = bucket
    return bucket_map


def evaluate_task(bucket: str, observed_stability: str, observed_majority_verdict: str) -> tuple[str, str]:
    if bucket == "conflict":
        return "REVIEW", "Task appears in multiple whitelist buckets."
    if bucket == "unknown":
        return "UNKNOWN", "Task not present in whitelist."
    if bucket == "stable_ok":
        if observed_stability == "stable_ok" and observed_majority_verdict == "ok":
            return "PASS", "Observed result matches stable_ok baseline."
        return "REVIEW", "stable_ok baseline drift detected."
    if bucket == "jitter_ok_majority":
        if observed_majority_verdict == "ok" and observed_stability in {"jitter_ok_majority", "stable_ok"}:
            return "PASS", "Observed result satisfies jitter_ok_majority policy."
        if observed_majority_verdict == "fail":
            return "BLOCK", "Majority verdict became fail for jitter_ok_majority task."
        return "REVIEW", "Unexpected stability state for jitter_ok_majority task."
    if bucket in {"jitter_fail_majority", "stable_fail"}:
        if observed_majority_verdict == "fail" and observed_stability in {"jitter_fail_majority", "stable_fail"}:
            return "BLOCK", "Observed result stays in fail-majority baseline."
        if observed_majority_verdict == "ok":
            return "REVIEW", "Previously fail-bucket task now passes; requires manual promotion."
        return "REVIEW", "Unexpected state for fail-bucket task."
    return "UNKNOWN", "Unrecognized whitelist bucket."


def flatten_task_sets(task_sets: dict) -> Iterable[int]:
    for key in ("stable_ok", "jitter_ok_majority", "jitter_fail_majority", "stable_fail"):
        for task_id in task_sets.get(key, []):
            yield int(task_id)


def evaluate_all(whitelist: dict, summary: dict) -> tuple[list[TaskEvalResult], list[int]]:
    task_sets = whitelist.get("task_sets", {})
    bucket_map = build_whitelist_bucket_map(task_sets)
    task_stats = summary.get("task_stats", [])
    observed_task_ids = set()
    results: list[TaskEvalResult] = []

    for task in task_stats:
        if not isinstance(task, dict):
            continue
        task_id = int(task.get("task_id"))
        observed_task_ids.add(task_id)
        bucket = bucket_map.get(task_id, "unknown")
        observed_stability = str(task.get("stability", "unknown"))
        observed_majority_verdict = str(task.get("majority_verdict", "unknown"))
        decision, reason = evaluate_task(bucket, observed_stability, observed_majority_verdict)
        results.append(
            TaskEvalResult(
                task_id=task_id,
                whitelist_bucket=bucket,
                observed_stability=observed_stability,
                observed_majority_verdict=observed_majority_verdict,
                decision=decision,
                reason=reason,
            )
        )

    whitelist_task_ids = set(flatten_task_sets(task_sets))
    missing_in_observed = sorted(whitelist_task_ids - observed_task_ids)
    return sorted(results, key=lambda x: x.task_id), missing_in_observed


def build_summary_payload(
    results: list[TaskEvalResult], missing_in_observed: list[int], whitelist_path: Path, summary_path: Path
) -> dict:
    pass_count = sum(1 for result in results if result.decision == "PASS")
    block_count = sum(1 for result in results if result.decision == "BLOCK")
    review_count = sum(1 for result in results if result.decision == "REVIEW")
    unknown_count = sum(1 for result in results if result.decision == "UNKNOWN")
    judgable = review_count == 0 and unknown_count == 0 and len(missing_in_observed) == 0
    freeze_gate_pass = judgable and block_count == 0
    root = repo_root()
    return {
        "source": {
            "whitelist": str(whitelist_path.relative_to(root)).replace("\\", "/"),
            "summary": str(summary_path.relative_to(root)).replace("\\", "/"),
        },
        "aggregate": {
            "tasks_evaluated": len(results),
            "pass": pass_count,
            "block": block_count,
            "review": review_count,
            "unknown": unknown_count,
            "missing_in_observed": len(missing_in_observed),
            "judgable": judgable,
            "freeze_gate_pass": freeze_gate_pass,
        },
        "missing_in_observed": missing_in_observed,
        "rows": [
            {
                "task_id": result.task_id,
                "whitelist_bucket": result.whitelist_bucket,
                "observed_stability": result.observed_stability,
                "observed_majority_verdict": result.observed_majority_verdict,
                "decision": result.decision,
                "reason": result.reason,
            }
            for result in results
        ],
    }


def build_report_markdown(payload: dict) -> str:
    aggregate = payload["aggregate"]
    lines: list[str] = []
    lines.append("# Obligations Freeze Whitelist Evaluation")
    lines.append("")
    lines.append(f"- tasks_evaluated: {aggregate['tasks_evaluated']}")
    lines.append(f"- pass: {aggregate['pass']}")
    lines.append(f"- block: {aggregate['block']}")
    lines.append(f"- review: {aggregate['review']}")
    lines.append(f"- unknown: {aggregate['unknown']}")
    lines.append(f"- missing_in_observed: {aggregate['missing_in_observed']}")
    lines.append(f"- judgable: {aggregate['judgable']}")
    lines.append(f"- freeze_gate_pass: {aggregate['freeze_gate_pass']}")
    lines.append("")
    if payload["missing_in_observed"]:
        lines.append("## Missing In Observed")
        lines.append("- " + ", ".join(f"T{task_id}" for task_id in payload["missing_in_observed"]))
        lines.append("")
    lines.append("## Decisions")
    for row in payload["rows"]:
        lines.append(
            f"- T{row['task_id']}: decision={row['decision']}, bucket={row['whitelist_bucket']}, "
            f"observed={row['observed_stability']}/{row['observed_majority_verdict']}"
        )
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    args = parse_args()
    whitelist_path = resolve_repo_path(args.whitelist)
    summary_path = resolve_repo_path(args.summary) if str(args.summary).strip() else find_latest_jitter_summary()
    if summary_path is None:
        print("ERROR: jitter summary not found. Use --summary to provide one explicitly.")
        return 2
    if not args.allow_draft and ".draft." in whitelist_path.name:
        print(
            "ERROR: draft whitelist is blocked for evaluation. "
            "Use promoted baseline file or pass --allow-draft explicitly."
        )
        return 2
    if not whitelist_path.exists():
        print(f"ERROR: whitelist file not found: {whitelist_path.as_posix()}")
        return 2
    if not summary_path.exists():
        print(f"ERROR: summary file not found: {summary_path.as_posix()}")
        return 2

    whitelist = load_json(whitelist_path)
    summary = load_json(summary_path)
    results, missing_in_observed = evaluate_all(whitelist, summary)
    payload = build_summary_payload(results, missing_in_observed, whitelist_path, summary_path)

    out_dir = (
        resolve_repo_path(args.out_dir)
        if str(args.out_dir).strip()
        else resolve_repo_path(f"logs/ci/{today_str()}/sc-obligations-freeze-eval")
    )
    out_dir.mkdir(parents=True, exist_ok=True)
    summary_file = out_dir / "summary.json"
    report_file = out_dir / "report.md"
    summary_file.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    report_file.write_text(build_report_markdown(payload) + "\n", encoding="utf-8")

    print(f"wrote {summary_file.as_posix()}")
    print(f"wrote {report_file.as_posix()}")
    print(f"judgable={payload['aggregate']['judgable']}")
    print(f"freeze_gate_pass={payload['aggregate']['freeze_gate_pass']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
