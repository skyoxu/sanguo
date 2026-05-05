#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
SC_DIR = REPO_ROOT / "scripts" / "sc"
if str(SC_DIR) not in sys.path:
    sys.path.insert(0, str(SC_DIR))

from _llm_review_tier import suggest_llm_review_tier_writeback  # noqa: E402
from _semantic_review_tier_support import (  # noqa: E402
    ALLOWED_MODES,
    ALLOWED_TIERS,
    build_triplet,
    load_triplet_payloads,
    normalize_existing_tier,
    parse_task_ids,
    title_for_task,
)
from _taskmaster_paths import resolve_default_task_triplet_paths  # noqa: E402
from _util import ci_dir, write_json  # noqa: E402


DEFAULT_TASKS_JSON_PATH, DEFAULT_TASKS_BACK_PATH, DEFAULT_TASKS_GAMEPLAY_PATH = resolve_default_task_triplet_paths(REPO_ROOT)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate semantic_review_tier values in task view files.")
    parser.add_argument("--tasks-json-path", default=str(DEFAULT_TASKS_JSON_PATH))
    parser.add_argument("--tasks-back-path", default=str(DEFAULT_TASKS_BACK_PATH))
    parser.add_argument("--tasks-gameplay-path", default=str(DEFAULT_TASKS_GAMEPLAY_PATH))
    parser.add_argument("--delivery-profile", default=os.getenv("DELIVERY_PROFILE", "fast-ship"), help="Delivery profile used to compute expected tier suggestions.")
    parser.add_argument("--mode", choices=sorted(ALLOWED_MODES), default="conservative", help="Validation mode; should match the writeback policy you enforce.")
    parser.add_argument("--task-ids", default="", help="Optional comma-separated task ids.")
    parser.add_argument("--allow-missing", action="store_true", help="Do not fail when semantic_review_tier is missing.")
    parser.add_argument("--summary-path", default="", help="Optional JSON summary output path.")
    return parser


def _entry_errors(
    *,
    file_key: str,
    task_id: int,
    title: str,
    entry: dict[str, Any] | None,
    expected_tier: str,
    allow_missing: bool,
) -> list[dict[str, Any]]:
    if not isinstance(entry, dict):
        return []

    errors: list[dict[str, Any]] = []
    if "semanticReviewTier" in entry:
        errors.append(
            {
                "file": file_key,
                "task_id": task_id,
                "title": title,
                "rule": "legacy_camel_case_field",
                "message": "Use semantic_review_tier; semanticReviewTier is not allowed.",
            }
        )

    raw_snake = entry.get("semantic_review_tier")
    if raw_snake is None:
        if not allow_missing:
            errors.append(
                {
                    "file": file_key,
                    "task_id": task_id,
                    "title": title,
                    "rule": "missing_semantic_review_tier",
                    "message": "semantic_review_tier is missing.",
                }
            )
        return errors

    current = normalize_existing_tier(entry)
    if current is None:
        errors.append(
            {
                "file": file_key,
                "task_id": task_id,
                "title": title,
                "rule": "invalid_semantic_review_tier",
                "message": f"semantic_review_tier must be one of {sorted(ALLOWED_TIERS)}.",
                "actual": raw_snake,
            }
        )
        return errors

    if current != expected_tier:
        errors.append(
            {
                "file": file_key,
                "task_id": task_id,
                "title": title,
                "rule": "semantic_review_tier_mismatch",
                "message": "semantic_review_tier does not match the computed suggestion.",
                "actual": current,
                "expected": expected_tier,
            }
        )
    return errors


def validate_semantic_review_tier(
    *,
    tasks_json_path: Path,
    tasks_back_path: Path,
    tasks_gameplay_path: Path,
    delivery_profile: str,
    mode: str,
    allow_missing: bool,
    task_ids: set[int] | None,
) -> dict[str, Any]:
    _, _, _, master_by_id, back_by_id, gameplay_by_id, candidate_ids = load_triplet_payloads(
        tasks_json_path=tasks_json_path,
        tasks_back_path=tasks_back_path,
        tasks_gameplay_path=tasks_gameplay_path,
    )
    if task_ids:
        candidate_ids = [task_id for task_id in candidate_ids if task_id in task_ids]

    errors: list[dict[str, Any]] = []
    checks: list[dict[str, Any]] = []

    for task_id in candidate_ids:
        triplet = build_triplet(
            task_id=task_id,
            master_by_id=master_by_id,
            back_by_id=back_by_id,
            gameplay_by_id=gameplay_by_id,
            tasks_json_path=tasks_json_path,
            tasks_back_path=tasks_back_path,
            tasks_gameplay_path=tasks_gameplay_path,
        )
        suggestion = suggest_llm_review_tier_writeback(
            delivery_profile=delivery_profile,
            triplet=triplet,
            mode=mode,
        )
        expected_tier = str(suggestion["tier"])
        title = title_for_task(task_id, master_by_id.get(task_id), back_by_id.get(task_id), gameplay_by_id.get(task_id))

        task_errors = []
        task_errors.extend(
            _entry_errors(
                file_key="tasks_back",
                task_id=task_id,
                title=title,
                entry=back_by_id.get(task_id),
                expected_tier=expected_tier,
                allow_missing=allow_missing,
            )
        )
        task_errors.extend(
            _entry_errors(
                file_key="tasks_gameplay",
                task_id=task_id,
                title=title,
                entry=gameplay_by_id.get(task_id),
                expected_tier=expected_tier,
                allow_missing=allow_missing,
            )
        )

        back_value = normalize_existing_tier(back_by_id.get(task_id) or {}) if isinstance(back_by_id.get(task_id), dict) else None
        gameplay_value = normalize_existing_tier(gameplay_by_id.get(task_id) or {}) if isinstance(gameplay_by_id.get(task_id), dict) else None
        if back_value and gameplay_value and back_value != gameplay_value:
            task_errors.append(
                {
                    "file": "tasks_back+tasks_gameplay",
                    "task_id": task_id,
                    "title": title,
                    "rule": "cross_view_tier_mismatch",
                    "message": "tasks_back and tasks_gameplay must use the same semantic_review_tier.",
                    "back": back_value,
                    "gameplay": gameplay_value,
                }
            )

        errors.extend(task_errors)
        checks.append(
            {
                "task_id": task_id,
                "title": title,
                "expected_tier": expected_tier,
                "reason": suggestion["reason"],
                "preview_effective_tier": suggestion["preview_effective_tier"],
                "preview_profile_default_tier": suggestion["preview_profile_default_tier"],
                "escalation_reasons": list(suggestion["escalation_reasons"]),
                "errors": len(task_errors),
            }
        )

    return {
        "cmd": "validate-semantic-review-tier",
        "delivery_profile": delivery_profile,
        "mode": mode,
        "allow_missing": allow_missing,
        "tasks_checked": len(candidate_ids),
        "error_count": len(errors),
        "errors": errors,
        "checks": checks,
        "status": "fail" if errors else "ok",
    }


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    task_ids = parse_task_ids(args.task_ids) if str(args.task_ids or "").strip() else None
    summary_path = Path(args.summary_path).resolve() if str(args.summary_path or "").strip() else ci_dir("validate-semantic-review-tier") / "summary.json"

    summary = validate_semantic_review_tier(
        tasks_json_path=Path(args.tasks_json_path).resolve(),
        tasks_back_path=Path(args.tasks_back_path).resolve(),
        tasks_gameplay_path=Path(args.tasks_gameplay_path).resolve(),
        delivery_profile=str(args.delivery_profile).strip().lower(),
        mode=str(args.mode).strip().lower(),
        allow_missing=bool(args.allow_missing),
        task_ids=task_ids,
    )
    write_json(summary_path, summary)
    print(
        "VALIDATE_SEMANTIC_REVIEW_TIER status={status} mode={mode} tasks={tasks} errors={errors} summary={summary}".format(
            status=summary["status"],
            mode=summary["mode"],
            tasks=summary["tasks_checked"],
            errors=summary["error_count"],
            summary=str(summary_path),
        )
    )
    return 1 if summary["status"] == "fail" else 0


if __name__ == "__main__":
    raise SystemExit(main())
