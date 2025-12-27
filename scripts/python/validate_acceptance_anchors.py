#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Validate acceptance anchor coverage for a single Taskmaster task.

Why:
  validate_acceptance_refs.py ensures each acceptance item points to test files (Refs: ...),
  but it cannot prove that the referenced tests actually claim to cover that acceptance item.

This script adds a deterministic "semantic binding" gate:
  - For task T<id>, acceptance item index n (1-based) must have anchor: "ACC:T<id>.<n>"
  - At refactor stage, at least one referenced test file for that acceptance item
    must contain the corresponding anchor string (anywhere in the file).

Notes:
  - This is a coarse but deterministic gate. It does not evaluate whether assertions are strong.
  - Index n is computed per task view entry (back/gameplay) from acceptance[] order.

Usage (Windows):
  py -3 scripts/python/validate_acceptance_anchors.py --task-id 11 --stage refactor --out logs/ci/<date>/.../acceptance-anchors.json
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any


REFS_RE = re.compile(r"\bRefs\s*:\s*(.+)$", flags=re.IGNORECASE)


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")


def resolve_current_task_id(tasks_json: dict[str, Any]) -> str:
    tasks = (tasks_json.get("master") or {}).get("tasks") or []
    for t in tasks:
        if not isinstance(t, dict):
            continue
        if str(t.get("status")) == "in-progress":
            return str(t.get("id"))
    raise ValueError("No task with status=in-progress found in tasks.json")


def find_view_task(view: list[dict[str, Any]], task_id: str) -> dict[str, Any] | None:
    try:
        tid_int = int(str(task_id))
    except ValueError:
        return None
    for t in view:
        if not isinstance(t, dict):
            continue
        if t.get("taskmaster_id") == tid_int:
            return t
    return None


def _split_refs_blob(blob: str) -> list[str]:
    normalized = str(blob or "").replace("`", " ").replace(",", " ").replace(";", " ")
    out: list[str] = []
    for token in normalized.split():
        p = token.strip().replace("\\", "/")
        if not p:
            continue
        out.append(p)
    return out


def parse_refs_from_line(line: str) -> list[str]:
    m = REFS_RE.search(str(line or "").strip())
    if not m:
        return []
    return _split_refs_blob(m.group(1) or "")


@dataclass(frozen=True)
class ItemResult:
    index_1_based: int
    anchor: str
    refs: list[str]
    ok: bool
    reason: str | None


def validate_view_entry(*, root: Path, view_name: str, task_id: str, entry: dict[str, Any], stage: str) -> dict[str, Any]:
    acceptance = entry.get("acceptance") or []
    if not isinstance(acceptance, list):
        return {"view": view_name, "status": "skipped", "reason": "acceptance_not_list", "items": []}

    items: list[dict[str, Any]] = []
    errors: list[str] = []

    for idx, raw in enumerate(acceptance):
        text = str(raw or "").strip()
        if not text:
            # Empty acceptance lines are not actionable; keep them as skipped.
            items.append(
                {
                    "index": idx + 1,
                    "anchor": f"ACC:T{task_id}.{idx + 1}",
                    "refs": [],
                    "status": "skipped",
                    "reason": "empty_acceptance",
                }
            )
            continue

        anchor = f"ACC:T{task_id}.{idx + 1}"
        refs = parse_refs_from_line(text)
        if not refs:
            items.append({"index": idx + 1, "anchor": anchor, "refs": [], "status": "fail", "reason": "missing_refs"})
            errors.append(f"{view_name}: acceptance[{idx}] missing Refs: (required for anchors)")
            continue

        if stage != "refactor":
            items.append({"index": idx + 1, "anchor": anchor, "refs": refs, "status": "skipped", "reason": f"stage:{stage}"})
            continue

        existing_files: list[Path] = []
        missing: list[str] = []
        for r in refs:
            p = (root / r)
            if p.exists():
                existing_files.append(p)
            else:
                missing.append(r)

        if missing:
            items.append(
                {
                    "index": idx + 1,
                    "anchor": anchor,
                    "refs": refs,
                    "status": "fail",
                    "reason": "missing_ref_files",
                    "missing": missing,
                }
            )
            errors.append(f"{view_name}: acceptance[{idx}] refs missing files: {', '.join(missing)}")
            continue

        found_in: list[str] = []
        for p in existing_files:
            try:
                t = p.read_text(encoding="utf-8", errors="ignore")
            except Exception:  # noqa: BLE001
                t = ""
            if anchor in t:
                found_in.append(str(p.relative_to(root)).replace("\\", "/"))

        if not found_in:
            items.append(
                {
                    "index": idx + 1,
                    "anchor": anchor,
                    "refs": refs,
                    "status": "fail",
                    "reason": "anchor_not_found",
                }
            )
            errors.append(f"{view_name}: acceptance[{idx}] anchor not found in any referenced test file: {anchor}")
            continue

        items.append({"index": idx + 1, "anchor": anchor, "refs": refs, "status": "ok", "found_in": found_in})

    status = "ok" if not errors else "fail"
    return {"view": view_name, "status": status, "items": items, "errors": errors}


def main() -> int:
    ap = argparse.ArgumentParser(description="Validate acceptance anchors for one task.")
    ap.add_argument("--task-id", default=None, help="Task id (e.g. 11). Default: first status=in-progress in tasks.json.")
    ap.add_argument("--stage", choices=["red", "green", "refactor"], required=True)
    ap.add_argument("--out", required=True, help="Output JSON path.")
    args = ap.parse_args()

    root = repo_root()
    tasks_json = load_json(root / ".taskmaster/tasks/tasks.json")
    task_id = str(args.task_id or "").strip() or resolve_current_task_id(tasks_json)

    back_view = load_json(root / ".taskmaster/tasks/tasks_back.json")
    gameplay_view = load_json(root / ".taskmaster/tasks/tasks_gameplay.json")
    if not isinstance(back_view, list) or not isinstance(gameplay_view, list):
        raise ValueError("Expected tasks_back.json/tasks_gameplay.json to be JSON arrays")

    back_entry = find_view_task(back_view, task_id)
    game_entry = find_view_task(gameplay_view, task_id)

    results: list[dict[str, Any]] = []
    if back_entry is not None:
        results.append(validate_view_entry(root=root, view_name="back", task_id=task_id, entry=back_entry, stage=args.stage))
    if game_entry is not None:
        results.append(validate_view_entry(root=root, view_name="gameplay", task_id=task_id, entry=game_entry, stage=args.stage))

    if not results:
        payload = {"status": "fail", "task_id": task_id, "stage": args.stage, "error": "task_not_found_in_any_view"}
        write_json(Path(args.out), payload)
        print(f"ACCEPTANCE_ANCHORS status=fail task_id={task_id} stage={args.stage} errors=1")
        return 1

    errors = sum(len(r.get("errors") or []) for r in results)
    status = "ok" if errors == 0 else "fail"
    payload = {"status": status, "task_id": task_id, "stage": args.stage, "views": results, "errors": errors}
    write_json(Path(args.out), payload)
    print(f"ACCEPTANCE_ANCHORS status={status} task_id={task_id} stage={args.stage} errors={errors}")
    return 0 if status == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())

