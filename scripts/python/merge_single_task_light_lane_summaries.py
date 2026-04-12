#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Merge split workflow 5.1 summaries into one transparent merged report."""

from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path
from typing import Any


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _today() -> str:
    return dt.date.today().strftime("%Y-%m-%d")


def _default_logs_root(root: Path, date_str: str) -> Path:
    return root / "logs" / "ci" / date_str


def _default_out_dir(root: Path, date_str: str) -> Path:
    return _default_logs_root(root, date_str) / "single-task-light-lane-v2-merged"


def _load_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    return payload if isinstance(payload, dict) else None


def _result_task_ids(summary: dict[str, Any]) -> list[int]:
    task_ids: list[int] = []
    for row in summary.get("results", []) or []:
        if not isinstance(row, dict):
            continue
        raw = str(row.get("task_id") or "").strip()
        if raw.isdigit():
            task_ids.append(int(raw))
    return sorted(set(task_ids))


def _final_status(status: Any) -> bool:
    return str(status or "").strip() in {"ok", "fail"}


def _summary_declared_task_ids(summary: dict[str, Any]) -> list[int]:
    resume_scope = summary.get("resume_scope")
    if isinstance(resume_scope, dict):
        task_ids = []
        for item in resume_scope.get("task_ids") or []:
            raw = str(item).strip()
            if raw.isdigit():
                task_ids.append(int(raw))
        if task_ids:
            return sorted(set(task_ids))
    start = summary.get("task_id_start")
    end = summary.get("task_id_end")
    if start is not None and end is not None:
        try:
            start_i = int(start)
            end_i = int(end)
        except Exception:
            return []
        if start_i <= end_i:
            return list(range(start_i, end_i + 1))
    return []


def _discover_inputs(logs_root: Path, pattern: str) -> list[Path]:
    out: list[Path] = []
    for path in sorted(logs_root.glob(pattern)):
        summary_path = path / "summary.json" if path.is_dir() else path
        if not summary_path.is_file():
            continue
        if "-merged" in summary_path.as_posix():
            continue
        out.append(summary_path)
    return out


def _source_meta(root: Path, summary_path: Path, summary: dict[str, Any]) -> dict[str, Any]:
    declared = _summary_declared_task_ids(summary)
    result_ids = _result_task_ids(summary)
    declared_set = set(declared)
    result_set = set(result_ids)
    return {
        "path": str(summary_path.relative_to(root)).replace("\\", "/"),
        "status": summary.get("status"),
        "status_is_final": _final_status(summary.get("status")),
        "generated_at": summary.get("finished_at") or summary.get("last_updated_at") or summary.get("started_at"),
        "task_id_start": summary.get("task_id_start"),
        "task_id_end": summary.get("task_id_end"),
        "declared_task_count": len(declared),
        "result_task_count": len(result_set),
        "declared_missing_task_ids": sorted(declared_set.difference(result_set)),
        "unexpected_result_task_ids": sorted(result_set.difference(declared_set)) if declared_set else [],
        "processed_tasks": summary.get("processed_tasks"),
        "passed_tasks": summary.get("passed_tasks"),
        "failed_tasks": summary.get("failed_tasks"),
        "delivery_profile": summary.get("delivery_profile"),
        "fill_refs_mode_resolved": summary.get("fill_refs_mode_resolved"),
        "downstream_on_extract_fail_resolved": summary.get("downstream_on_extract_fail_resolved"),
        "batch_lane_resolved": summary.get("batch_lane_resolved"),
    }


def _row_sort_key(summary_path: Path, row: dict[str, Any]) -> tuple[float, int]:
    try:
        mtime = summary_path.stat().st_mtime
    except Exception:
        mtime = 0.0
    task_raw = str(row.get("task_id") or "").strip()
    task_id = int(task_raw) if task_raw.isdigit() else 0
    return (mtime, task_id)


def _issue(kind: str, *, level: str, **payload: Any) -> dict[str, Any]:
    issue = {"kind": str(kind), "level": str(level)}
    issue.update(payload)
    return issue


def _build_validation(
    *,
    invalid_inputs: list[str],
    duplicate_input_paths: list[str],
    source_entries: list[dict[str, Any]],
    all_declared_ids: set[int],
    covered_ids: list[int],
    missing_ids: list[int],
    candidate_sources: dict[int, list[str]],
) -> dict[str, Any]:
    hard_issues: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []

    if invalid_inputs:
        hard_issues.append(_issue("invalid_input_summary", level="hard", paths=list(invalid_inputs)))
    if duplicate_input_paths:
        warnings.append(_issue("duplicate_input_paths", level="warning", paths=list(duplicate_input_paths)))

    if not all_declared_ids and covered_ids:
        hard_issues.append(_issue("no_declared_task_ids", level="hard"))

    if missing_ids:
        hard_issues.append(_issue("missing_declared_tasks", level="hard", task_ids=list(missing_ids)))

    undeclared_result_task_ids = sorted(set(covered_ids).difference(all_declared_ids)) if all_declared_ids else []
    if undeclared_result_task_ids:
        hard_issues.append(_issue("undeclared_result_task_ids", level="hard", task_ids=list(undeclared_result_task_ids)))

    overlapping_task_ids = sorted(task_id for task_id, sources in candidate_sources.items() if len(set(sources)) > 1)
    if overlapping_task_ids:
        warnings.append(_issue("overlapping_task_ids", level="warning", task_ids=list(overlapping_task_ids)))

    for source in source_entries:
        path = str(source.get("path") or "")
        if not bool(source.get("status_is_final")):
            hard_issues.append(_issue("source_status_not_final", level="hard", path=path, status=source.get("status")))
        unexpected = list(source.get("unexpected_result_task_ids") or [])
        if unexpected:
            hard_issues.append(_issue("source_result_outside_declared_scope", level="hard", path=path, task_ids=unexpected))
        missing_local = list(source.get("declared_missing_task_ids") or [])
        if missing_local:
            warnings.append(_issue("source_declared_missing_results", level="warning", path=path, task_ids=missing_local))
        processed_tasks = source.get("processed_tasks")
        result_task_count = int(source.get("result_task_count") or 0)
        if processed_tasks is not None:
            try:
                processed_int = int(processed_tasks)
            except Exception:
                processed_int = None
            if processed_int is not None and processed_int != result_task_count:
                warnings.append(
                    _issue(
                        "source_processed_tasks_mismatch",
                        level="warning",
                        path=path,
                        processed_tasks=processed_int,
                        result_task_count=result_task_count,
                    )
                )

    return {
        "status": "ok" if not hard_issues else "fail",
        "hard_issue_count": len(hard_issues),
        "warning_count": len(warnings),
        "hard_issues": hard_issues,
        "warnings": warnings,
        "overlapping_task_ids": overlapping_task_ids,
        "undeclared_result_task_ids": undeclared_result_task_ids,
    }


def _build_duration_summary(results: list[dict[str, Any]]) -> dict[str, Any]:
    step_duration_totals: dict[str, float] = {}
    step_duration_counts: dict[str, int] = {}
    slowest_tasks: list[dict[str, Any]] = []
    for row in results:
        if not isinstance(row, dict):
            continue
        task_raw = str(row.get("task_id") or "").strip()
        task_duration_total = 0.0
        for step in row.get("steps", []) or []:
            if not isinstance(step, dict):
                continue
            step_name = str(step.get("step") or "").strip()
            if not step_name:
                continue
            try:
                duration_sec = float(step.get("duration_sec")) if step.get("duration_sec") is not None else None
            except Exception:
                duration_sec = None
            if duration_sec is None or duration_sec < 0:
                continue
            step_duration_totals[step_name] = step_duration_totals.get(step_name, 0.0) + duration_sec
            step_duration_counts[step_name] = step_duration_counts.get(step_name, 0) + 1
            task_duration_total += duration_sec
        if task_raw.isdigit() and task_duration_total > 0:
            slowest_tasks.append(
                {
                    "task_id": int(task_raw),
                    "duration_sec": round(task_duration_total, 3),
                    "first_failed_step": str(row.get("first_failed_step") or "").strip(),
                    "ok": bool(row.get("ok")),
                }
            )
    return {
        "step_duration_totals": {
            key: round(value, 3) for key, value in sorted(step_duration_totals.items(), key=lambda item: item[0])
        },
        "step_duration_avg": {
            key: round(step_duration_totals[key] / max(1, int(step_duration_counts.get(key) or 1)), 3)
            for key in sorted(step_duration_totals)
        },
        "step_duration_task_counts": {
            key: int(step_duration_counts.get(key) or 0) for key in sorted(step_duration_counts)
        },
        "slowest_tasks": sorted(
            slowest_tasks,
            key=lambda item: (-float(item.get("duration_sec") or 0.0), int(item.get("task_id") or 0)),
        )[:10],
    }


def merge_summaries(root: Path, input_paths: list[Path]) -> dict[str, Any]:
    source_entries: list[dict[str, Any]] = []
    all_declared_ids: set[int] = set()
    chosen_rows: dict[int, dict[str, Any]] = {}
    chosen_sources: dict[int, str] = {}
    candidate_sources: dict[int, list[str]] = {}
    invalid_inputs: list[str] = []
    seen_input_paths: set[str] = set()
    duplicate_input_paths: list[str] = []

    for summary_path in input_paths:
        summary = _load_json(summary_path)
        if not isinstance(summary, dict):
            try:
                invalid_inputs.append(str(summary_path.relative_to(root)).replace("\\", "/"))
            except Exception:
                invalid_inputs.append(str(summary_path).replace("\\", "/"))
            continue
        source_rel = str(summary_path.relative_to(root)).replace("\\", "/")
        if source_rel in seen_input_paths:
            duplicate_input_paths.append(source_rel)
        else:
            seen_input_paths.add(source_rel)
        source_entries.append(_source_meta(root, summary_path, summary))
        declared_ids = _summary_declared_task_ids(summary)
        all_declared_ids.update(declared_ids)
        for row in summary.get("results", []) or []:
            if not isinstance(row, dict):
                continue
            raw = str(row.get("task_id") or "").strip()
            if not raw.isdigit():
                continue
            task_id = int(raw)
            candidate_sources.setdefault(task_id, []).append(source_rel)
            current = chosen_rows.get(task_id)
            if current is None:
                chosen_rows[task_id] = dict(row)
                chosen_sources[task_id] = source_rel
                continue
            current_source = root / chosen_sources[task_id]
            if _row_sort_key(summary_path, row) >= _row_sort_key(current_source, current):
                chosen_rows[task_id] = dict(row)
                chosen_sources[task_id] = source_rel

    covered_ids = sorted(chosen_rows.keys())
    missing_ids = sorted(all_declared_ids.difference(set(covered_ids)))
    passed_ids: list[int] = []
    failed_ids: list[int] = []
    failed_first_step_counter: dict[str, int] = {"extract": 0, "align": 0, "coverage": 0, "semantic_gate": 0, "other": 0}

    results: list[dict[str, Any]] = []
    for task_id in covered_ids:
        row = dict(chosen_rows[task_id])
        row["merged_source"] = chosen_sources.get(task_id, "")
        row["merged_source_candidates"] = list(candidate_sources.get(task_id) or [])
        results.append(row)
        if bool(row.get("ok")):
            passed_ids.append(task_id)
        else:
            failed_ids.append(task_id)
            first_failed = str(row.get("first_failed_step") or "").strip()
            bucket = first_failed if first_failed in {"extract", "align", "coverage", "semantic_gate"} else "other"
            failed_first_step_counter[bucket] = failed_first_step_counter.get(bucket, 0) + 1

    overridden_task_ids = sorted(task_id for task_id, sources in candidate_sources.items() if len(set(sources)) > 1)
    validation = _build_validation(
        invalid_inputs=invalid_inputs,
        duplicate_input_paths=sorted(set(duplicate_input_paths)),
        source_entries=source_entries,
        all_declared_ids=all_declared_ids,
        covered_ids=covered_ids,
        missing_ids=missing_ids,
        candidate_sources=candidate_sources,
    )
    merged = {
        "cmd": "merge-single-task-light-lane-summaries",
        "generated_at": dt.datetime.now().isoformat(timespec="seconds"),
        "status": str(validation.get("status") or "fail"),
        "range": {
            "task_id_start": min(all_declared_ids) if all_declared_ids else None,
            "task_id_end": max(all_declared_ids) if all_declared_ids else None,
        },
        "source_summaries": source_entries,
        "task_source_map": {str(task_id): chosen_sources.get(task_id, "") for task_id in covered_ids},
        "task_source_candidates": {str(task_id): list(candidate_sources.get(task_id) or []) for task_id in sorted(candidate_sources)},
        "overridden_task_ids": overridden_task_ids,
        "covered_count": len(covered_ids),
        "missing_count": len(missing_ids),
        "missing_task_ids": missing_ids,
        "passed_count": len(passed_ids),
        "failed_count": len(failed_ids),
        "passed_task_ids": passed_ids,
        "failed_task_ids": failed_ids,
        "failed_first_step_counter": failed_first_step_counter,
        "validation": validation,
        "results": results,
    }
    merged.update(_build_duration_summary(results))
    return merged


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Merge split workflow 5.1 summaries into one transparent summary.")
    parser.add_argument("--date", default=_today(), help="Logs date folder under logs/ci/YYYY-MM-DD")
    parser.add_argument("--logs-root", default="", help="Override logs root. Default: logs/ci/<date>")
    parser.add_argument(
        "--pattern",
        default="single-task-light-lane-v2*/summary.json",
        help="Glob pattern under logs root. Merged summaries are ignored automatically.",
    )
    parser.add_argument("--input", action="append", default=[], help="Explicit summary.json path(s). Can be passed multiple times.")
    parser.add_argument("--out-dir", default="", help="Output directory. Default: logs/ci/<date>/single-task-light-lane-v2-merged")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    root = _repo_root()
    logs_root = Path(args.logs_root) if str(args.logs_root).strip() else _default_logs_root(root, str(args.date))
    input_paths = [Path(item) for item in list(args.input or []) if str(item).strip()]
    if not input_paths:
        input_paths = _discover_inputs(logs_root, str(args.pattern))
    input_paths = [path for path in input_paths if path.is_file()]
    if not input_paths:
        print("MERGE_SINGLE_TASK_LIGHT_LANE status=fail reason=no_inputs")
        return 2

    out_dir = Path(args.out_dir) if str(args.out_dir).strip() else _default_out_dir(root, str(args.date))
    out_dir.mkdir(parents=True, exist_ok=True)
    merged = merge_summaries(root, input_paths)
    summary_path = out_dir / "summary.json"
    summary_path.write_text(json.dumps(merged, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    status = str(merged.get("status") or "fail")
    print(
        "MERGE_SINGLE_TASK_LIGHT_LANE "
        f"status={status} sources={len(input_paths)} covered={merged.get('covered_count', 0)} "
        f"missing={merged.get('missing_count', 0)} hard_issues={((merged.get('validation') or {}).get('hard_issue_count') or 0)} "
        f"out={str(summary_path).replace('\\', '/')}"
    )
    return 0 if status == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
