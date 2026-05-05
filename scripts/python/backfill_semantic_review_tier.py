#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
SC_DIR = REPO_ROOT / "scripts" / "sc"
if str(SC_DIR) not in sys.path:
    sys.path.insert(0, str(SC_DIR))

from _llm_review_tier import suggest_llm_review_tier_writeback  # noqa: E402
from _semantic_review_tier_support import (  # noqa: E402
    ALLOWED_MODES,
    normalize_existing_tier,
    parse_task_ids,
    load_triplet_payloads,
    build_triplet,
    title_for_task,
    write_json_file,
)
from _taskmaster_paths import resolve_default_task_triplet_paths  # noqa: E402
from _util import ci_dir, write_json  # noqa: E402


DEFAULT_TASKS_JSON_PATH, DEFAULT_TASKS_BACK_PATH, DEFAULT_TASKS_GAMEPLAY_PATH = resolve_default_task_triplet_paths(REPO_ROOT)


@dataclass
class ViewUpdate:
    file_key: str
    task_id: int
    title: str
    before: str | None
    after: str
    reason: str

def _set_entry_tier(entry: dict[str, Any], *, tier: str) -> tuple[str | None, bool]:
    before = normalize_existing_tier(entry)
    changed = before != tier or "semanticReviewTier" in entry or "semantic_review_tier" not in entry
    entry["semantic_review_tier"] = tier
    entry.pop("semanticReviewTier", None)
    return before, changed


def _should_update_entry(entry: dict[str, Any], *, rewrite_existing: bool) -> bool:
    if "semanticReviewTier" in entry:
        return True
    if "semantic_review_tier" not in entry:
        return True
    current = normalize_existing_tier(entry)
    return rewrite_existing or current is None


def run_backfill(
    *,
    tasks_json_path: Path,
    tasks_back_path: Path,
    tasks_gameplay_path: Path,
    delivery_profile: str,
    mode: str,
    rewrite_existing: bool,
    task_ids: set[int] | None,
    write: bool,
) -> dict[str, Any]:
    if mode not in ALLOWED_MODES:
        raise ValueError(f"Unsupported mode: {mode}")

    _, tasks_back, tasks_gameplay, master_by_id, back_by_id, gameplay_by_id, candidate_ids = load_triplet_payloads(
        tasks_json_path=tasks_json_path,
        tasks_back_path=tasks_back_path,
        tasks_gameplay_path=tasks_gameplay_path,
    )
    if task_ids:
        candidate_ids = [task_id for task_id in candidate_ids if task_id in task_ids]

    updates: list[ViewUpdate] = []
    evaluations: list[dict[str, Any]] = []

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
        title = title_for_task(task_id, master_by_id.get(task_id), back_by_id.get(task_id), gameplay_by_id.get(task_id))
        evaluations.append(
            {
                "task_id": task_id,
                "title": title,
                "suggested_tier": suggestion["tier"],
                "reason": suggestion["reason"],
                "preview_effective_tier": suggestion["preview_effective_tier"],
                "preview_profile_default_tier": suggestion["preview_profile_default_tier"],
                "escalation_reasons": list(suggestion["escalation_reasons"]),
            }
        )

        for file_key, entry in (("tasks_back", back_by_id.get(task_id)), ("tasks_gameplay", gameplay_by_id.get(task_id))):
            if not isinstance(entry, dict):
                continue
            if not _should_update_entry(entry, rewrite_existing=rewrite_existing):
                continue
            before, changed = _set_entry_tier(entry, tier=str(suggestion["tier"]))
            if changed:
                updates.append(
                    ViewUpdate(
                        file_key=file_key,
                        task_id=task_id,
                        title=title,
                        before=before,
                        after=str(suggestion["tier"]),
                        reason=str(suggestion["reason"]),
                    )
                )

    if write and updates:
        write_json_file(tasks_back_path, tasks_back)
        write_json_file(tasks_gameplay_path, tasks_gameplay)

    return {
        "cmd": "backfill-semantic-review-tier",
        "delivery_profile": delivery_profile,
        "mode": mode,
        "rewrite_existing": rewrite_existing,
        "write": write,
        "tasks_evaluated": len(candidate_ids),
        "tasks_updated": len({item.task_id for item in updates}),
        "view_updates": [
            {
                "file": item.file_key,
                "task_id": item.task_id,
                "title": item.title,
                "before": item.before,
                "after": item.after,
                "reason": item.reason,
            }
            for item in updates
        ],
        "evaluations": evaluations,
        "status": "ok",
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Backfill semantic_review_tier into task view files.")
    parser.add_argument("--tasks-json-path", default=str(DEFAULT_TASKS_JSON_PATH))
    parser.add_argument("--tasks-back-path", default=str(DEFAULT_TASKS_BACK_PATH))
    parser.add_argument("--tasks-gameplay-path", default=str(DEFAULT_TASKS_GAMEPLAY_PATH))
    parser.add_argument("--delivery-profile", default=os.getenv("DELIVERY_PROFILE", "fast-ship"), help="Delivery profile used for preview or materialized mode.")
    parser.add_argument("--mode", choices=sorted(ALLOWED_MODES), default="conservative", help="conservative=write only explicit safe floors; materialize=write effective tier for the selected profile.")
    parser.add_argument("--task-ids", default="", help="Optional comma-separated task ids.")
    parser.add_argument("--write", action="store_true", help="Write updates in-place. Without this flag, run as dry-run.")
    parser.add_argument("--rewrite-existing", action="store_true", help="Rewrite existing semantic_review_tier values instead of filling only missing/invalid fields.")
    parser.add_argument("--summary-path", default="", help="Optional JSON summary output path.")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    task_ids = parse_task_ids(args.task_ids) if str(args.task_ids or "").strip() else None
    summary_path = Path(args.summary_path).resolve() if str(args.summary_path or "").strip() else ci_dir("semantic-review-tier") / "summary.json"

    summary = run_backfill(
        tasks_json_path=Path(args.tasks_json_path).resolve(),
        tasks_back_path=Path(args.tasks_back_path).resolve(),
        tasks_gameplay_path=Path(args.tasks_gameplay_path).resolve(),
        delivery_profile=str(args.delivery_profile).strip().lower(),
        mode=str(args.mode).strip().lower(),
        rewrite_existing=bool(args.rewrite_existing),
        task_ids=task_ids,
        write=bool(args.write),
    )
    write_json(summary_path, summary)
    print(
        "SEMANTIC_REVIEW_TIER status={status} mode={mode} write={write} tasks={tasks} updated={updated} summary={summary}".format(
            status=summary["status"],
            mode=summary["mode"],
            write=str(summary["write"]).lower(),
            tasks=summary["tasks_evaluated"],
            updated=summary["tasks_updated"],
            summary=str(summary_path),
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
