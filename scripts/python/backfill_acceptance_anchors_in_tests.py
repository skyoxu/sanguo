#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Backfill ACC:T<id>.<n> acceptance anchors into referenced test files.

This script is deterministic and intended to retrofit existing repos after
introducing validate_acceptance_anchors.py.

Important:
  This is a one-time migration tool for legacy tasks. New tasks MUST add anchors
  directly in test files while implementing acceptance, before running refactor gates.

Scope:
  - Reads tasks_back.json/tasks_gameplay.json acceptance items and their Refs.
  - For each acceptance item n (1-based), computes anchor "ACC:T<id>.<n>".
  - Ensures at least one referenced test file contains that anchor by inserting
    a file-level comment block if needed.

Notes:
  - This does NOT attempt to prove assertions are strong. It only ensures the
    deterministic binding between acceptance lines and test files.
  - For acceptance items referencing multiple files, the anchor is inserted into
    the first existing referenced file by default (stable order).

Windows:
  py -3 scripts/python/backfill_acceptance_anchors_in_tests.py --task-ids 1,2,3 --write
  py -3 scripts/python/backfill_acceptance_anchors_in_tests.py --all-done --write
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any


REFS_RE = re.compile(r"\bRefs\s*:\s*(.+)$", flags=re.IGNORECASE)


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def today_str() -> str:
    return dt.date.today().strftime("%Y-%m-%d")


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def resolve_done_task_ids(tasks_json: dict[str, Any]) -> list[int]:
    tasks = (tasks_json.get("master") or {}).get("tasks") or []
    out: list[int] = []
    for t in tasks:
        if not isinstance(t, dict):
            continue
        if str(t.get("status")) != "done":
            continue
        try:
            out.append(int(str(t.get("id"))))
        except ValueError:
            continue
    return sorted(set(out))


def find_view_task(view: list[dict[str, Any]], task_id: int) -> dict[str, Any] | None:
    for t in view:
        if not isinstance(t, dict):
            continue
        if t.get("taskmaster_id") == int(task_id):
            return t
    return None


def split_refs_blob(blob: str) -> list[str]:
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
    return split_refs_blob(m.group(1) or "")


@dataclass(frozen=True)
class TargetAnchor:
    task_id: int
    index_1_based: int
    anchor: str
    source_view: str


def build_anchor_plan(*, root: Path, task_id: int, view_name: str, entry: dict[str, Any]) -> dict[str, list[TargetAnchor]]:
    acceptance = entry.get("acceptance") or []
    if not isinstance(acceptance, list):
        return {}

    per_file: dict[str, list[TargetAnchor]] = {}
    for idx, raw in enumerate(acceptance):
        text = str(raw or "").strip()
        if not text:
            continue
        refs = parse_refs_from_line(text)
        if not refs:
            continue
        anchor = f"ACC:T{task_id}.{idx + 1}"
        # choose the first existing file; else first ref path
        chosen: str | None = None
        for r in refs:
            rp = (root / r)
            if rp.exists():
                chosen = r
                break
        if not chosen:
            chosen = refs[0]
        chosen = chosen.replace("\\", "/")
        per_file.setdefault(chosen, []).append(TargetAnchor(task_id=task_id, index_1_based=idx + 1, anchor=anchor, source_view=view_name))
    return per_file


def _inject_block(text: str, *, comment_prefix: str, anchors: list[str]) -> str:
    anchors = [a.strip() for a in anchors if str(a).strip()]
    if not anchors:
        return text

    block_lines = [f"{comment_prefix} Acceptance anchors:"]
    for a in anchors:
        block_lines.append(f"{comment_prefix} {a}")
    block = "\n".join(block_lines) + "\n\n"

    lines = text.splitlines()
    # Insert before first non-empty, non-comment? keep it simple: insert at top.
    return block + "\n".join(lines).lstrip("\ufeff")


def apply_file_update(*, root: Path, rel_path: str, anchors: list[str], write: bool) -> dict[str, Any]:
    path = (root / rel_path)
    if not path.exists():
        return {"path": rel_path, "status": "missing"}

    try:
        original = path.read_text(encoding="utf-8", errors="ignore")
    except Exception:  # noqa: BLE001
        return {"path": rel_path, "status": "read_error"}

    missing = [a for a in anchors if a not in original]
    if not missing:
        return {"path": rel_path, "status": "ok", "updated": False, "added": 0}

    prefix = "//" if rel_path.endswith(".cs") else "#"
    updated = _inject_block(original, comment_prefix=prefix, anchors=sorted(set(missing)))
    if updated == original:
        return {"path": rel_path, "status": "ok", "updated": False, "added": 0}

    if write:
        path.write_text(updated, encoding="utf-8", newline="\n")
    return {"path": rel_path, "status": "ok", "updated": True, "added": len(sorted(set(missing)))}


def main() -> int:
    ap = argparse.ArgumentParser(description="Backfill acceptance anchors into referenced tests.")
    ap.add_argument("--task-ids", default=None, help="Comma-separated task ids.")
    ap.add_argument("--all-done", action="store_true", help="Process all status=done tasks from tasks.json.")
    ap.add_argument("--write", action="store_true", help="Write changes to files.")
    ap.add_argument(
        "--migration",
        action="store_true",
        help="Acknowledge this is a one-time migration tool (required with --write).",
    )
    args = ap.parse_args()

    if bool(args.write) and not bool(args.migration):
        raise SystemExit("Refusing to write without --migration acknowledgement.")

    root = repo_root()
    out_dir = root / "logs" / "ci" / today_str() / "backfill-acceptance-anchors"
    out_dir.mkdir(parents=True, exist_ok=True)

    tasks_json = load_json(root / ".taskmaster/tasks/tasks.json")
    back_view = load_json(root / ".taskmaster/tasks/tasks_back.json")
    gameplay_view = load_json(root / ".taskmaster/tasks/tasks_gameplay.json")
    if not isinstance(back_view, list) or not isinstance(gameplay_view, list):
        raise ValueError("Expected tasks_back.json/tasks_gameplay.json to be JSON arrays")

    if args.task_ids:
        task_ids = []
        for raw in str(args.task_ids).split(","):
            v = raw.strip()
            if not v:
                continue
            task_ids.append(int(v))
    elif args.all_done:
        task_ids = resolve_done_task_ids(tasks_json)
    else:
        raise SystemExit("Provide --task-ids or --all-done")

    plan_by_file: dict[str, list[TargetAnchor]] = {}
    for tid in task_ids:
        b = find_view_task(back_view, tid)
        g = find_view_task(gameplay_view, tid)
        if b:
            for f, anchors in build_anchor_plan(root=root, task_id=tid, view_name="back", entry=b).items():
                plan_by_file.setdefault(f, []).extend(anchors)
        if g:
            for f, anchors in build_anchor_plan(root=root, task_id=tid, view_name="gameplay", entry=g).items():
                plan_by_file.setdefault(f, []).extend(anchors)

    # Collapse per file -> unique anchor strings
    results: list[dict[str, Any]] = []
    updated_files = 0
    for rel_path, anchors in sorted(plan_by_file.items(), key=lambda kv: kv[0]):
        anchor_strings = sorted({a.anchor for a in anchors})
        r = apply_file_update(root=root, rel_path=rel_path, anchors=anchor_strings, write=bool(args.write))
        r["anchors"] = anchor_strings
        results.append(r)
        if r.get("updated"):
            updated_files += 1

    payload = {
        "status": "ok",
        "write": bool(args.write),
        "task_ids": task_ids,
        "files": len(results),
        "updated_files": updated_files,
        "results": results,
    }
    write_json(out_dir / "summary.json", payload)

    msg = f"BACKFILL_ACCEPTANCE_ANCHORS status=ok files={len(results)} updated_files={updated_files} out={out_dir}"
    write_text(out_dir / "run.log", msg + "\n")
    print(msg)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
