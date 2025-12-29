#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Validate acceptance "Refs:" for a single Taskmaster task (triplet views).

Intent:
  Turn free-text acceptance into deterministic traceability checks by requiring:
    - Every acceptance item includes a "Refs:" suffix
    - Refs are repo-relative paths to test files
    - At refactor stage, referenced files exist and are included in test_refs

This script does NOT verify semantic correctness of tests.

Supported ref format (per acceptance item):
  "... Refs: path1 path2"
  "... Refs: path1, path2"
  "... Refs: `path1`, `path2`"

Usage (Windows):
  py -3 scripts/python/validate_acceptance_refs.py --task-id 11 --stage red --out logs/ci/<date>/.../acceptance-refs.json
  py -3 scripts/python/validate_acceptance_refs.py --task-id 11 --stage refactor --out logs/ci/<date>/.../acceptance-refs.json
"""

from __future__ import annotations

import argparse
import json
import os
import re
from pathlib import Path
from typing import Any


REFS_RE = re.compile(r"\bRefs\s*:\s*(.+)$", flags=re.IGNORECASE)


def _contains_token(text: str, token: str) -> bool:
    return token.lower() in str(text or "").lower()


def _has_ref_suffix(refs: list[str], suffix: str) -> bool:
    return any(str(r).lower().endswith(suffix.lower()) for r in refs)


def _has_ref_prefix(refs: list[str], prefix: str) -> bool:
    pfx = prefix.replace("\\", "/").lower()
    return any(str(r).replace("\\", "/").lower().startswith(pfx) for r in refs)


def validate_text_refs_consistency(text: str, refs: list[str]) -> list[str]:
    """
    Hard rules: keep acceptance text and referenced test types consistent.

    Rules (deterministic):
      1) If acceptance mentions xUnit, refs must include at least one .cs file.
      2) If acceptance mentions GdUnit4 or headless, refs must include at least one .gd file.
      3) If acceptance mentions Game.Core, refs must include at least one Game.Core.Tests/*.cs file.
    """
    errors: list[str] = []
    lower = str(text or "").lower()

    if "xunit" in lower and not _has_ref_suffix(refs, ".cs"):
        errors.append("acceptance mentions xUnit but refs do not include any .cs file")

    if ("gdunit4" in lower or "headless" in lower) and not _has_ref_suffix(refs, ".gd"):
        errors.append("acceptance mentions GdUnit4/headless but refs do not include any .gd file")

    if "game.core" in lower:
        if not (_has_ref_suffix(refs, ".cs") and _has_ref_prefix(refs, "Game.Core.Tests/")):
            errors.append("acceptance mentions Game.Core but refs do not include any Game.Core.Tests/*.cs file")

    return errors


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


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


def is_abs_path(p: str) -> bool:
    if not p:
        return False
    if os.path.isabs(p):
        return True
    if len(p) >= 2 and p[1] == ":":
        return True
    return False


def _split_refs_blob(blob: str) -> list[str]:
    # Normalize common separators; keep it simple (paths are expected to not contain spaces).
    s = blob.strip()
    s = s.replace("`", "")
    s = s.replace(",", " ")
    s = s.replace(";", " ")
    parts = [p.strip() for p in s.split() if p.strip()]
    return parts


def _is_allowed_test_path(p: str) -> bool:
    p = p.replace("\\", "/")
    if not (p.endswith(".cs") or p.endswith(".gd")):
        return False
    allowed_prefixes = (
        "Game.Core.Tests/",
        "Tests.Godot/tests/",
        "Tests/",
    )
    return p.startswith(allowed_prefixes)


def parse_acceptance_item(text: str) -> tuple[str, list[str]]:
    s = str(text or "").strip()
    m = REFS_RE.search(s)
    if not m:
        return s, []
    refs_blob = m.group(1).strip()
    refs = _split_refs_blob(refs_blob)
    return s, refs


def validate_view(
    *,
    root: Path,
    label: str,
    entry: dict[str, Any] | None,
    stage: str,
) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    items: list[dict[str, Any]] = []
    all_refs: list[str] = []

    if entry is None:
        warnings.append(f"{label}: mapped task not found by taskmaster_id (skip)")
        return {"label": label, "status": "skipped", "errors": errors, "warnings": warnings, "items": items, "refs": all_refs}

    acceptance = entry.get("acceptance")
    if not isinstance(acceptance, list) or not [str(x).strip() for x in acceptance if str(x).strip()]:
        errors.append(f"{label}: acceptance missing/empty (expected non-empty list)")
        return {"label": label, "status": "fail", "errors": errors, "warnings": warnings, "items": items, "refs": all_refs}

    test_refs = entry.get("test_refs")
    test_refs_list: list[str] = []
    if test_refs is None:
        errors.append(f"{label}: test_refs missing (expected list)")
    elif not isinstance(test_refs, list):
        errors.append(f"{label}: test_refs must be a list")
    else:
        test_refs_list = [str(x).strip().replace("\\", "/") for x in test_refs if str(x).strip()]

    for idx, raw in enumerate(acceptance):
        text, refs = parse_acceptance_item(str(raw))
        norm_refs = [r.replace("\\", "/") for r in refs]
        item = {"index": idx, "text": text, "refs": norm_refs, "status": "ok", "errors": []}

        if not norm_refs:
            item["status"] = "fail"
            item["errors"].append("missing Refs: in acceptance item")
        else:
            consistency_errors = validate_text_refs_consistency(text, norm_refs)
            if consistency_errors:
                item["status"] = "fail"
                item["errors"].extend(consistency_errors)

            for r in norm_refs:
                if is_abs_path(r):
                    item["status"] = "fail"
                    item["errors"].append(f"absolute path is not allowed: {r}")
                    continue
                if not _is_allowed_test_path(r):
                    item["status"] = "fail"
                    item["errors"].append(f"ref is not an allowed test path (.cs/.gd under test roots): {r}")
                    continue

                if stage == "refactor":
                    if not (root / r).exists():
                        item["status"] = "fail"
                        item["errors"].append(f"referenced file not found on disk: {r}")
                    if r not in test_refs_list:
                        item["status"] = "fail"
                        item["errors"].append(f"ref must be included in test_refs at refactor stage: {r}")

        if item["status"] != "ok":
            errors.extend([f"{label}: acceptance[{idx}]: {e}" for e in item["errors"]])
        items.append(item)
        all_refs.extend(norm_refs)

    # De-dup refs preserving order.
    seen = set()
    uniq = []
    for r in all_refs:
        if r in seen:
            continue
        seen.add(r)
        uniq.append(r)
    all_refs = uniq

    return {
        "label": label,
        "status": "ok" if not errors else "fail",
        "errors": errors,
        "warnings": warnings,
        "items": items,
        "refs": all_refs,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Validate acceptance Refs: mapping for one task.")
    ap.add_argument("--task-id", default=None, help="Task id (e.g. 11). Default: first status=in-progress in tasks.json.")
    ap.add_argument("--stage", choices=["red", "green", "refactor"], required=True)
    ap.add_argument("--out", required=True, help="Output JSON path.")
    args = ap.parse_args()

    root = repo_root()
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    tasks_json_path = root / ".taskmaster" / "tasks" / "tasks.json"
    back_path = root / ".taskmaster" / "tasks" / "tasks_back.json"
    gameplay_path = root / ".taskmaster" / "tasks" / "tasks_gameplay.json"

    tasks_json = load_json(tasks_json_path)
    task_id = str(args.task_id).strip() if args.task_id else resolve_current_task_id(tasks_json)

    back = load_json(back_path)
    gameplay = load_json(gameplay_path)
    if not isinstance(back, list) or not isinstance(gameplay, list):
        raise ValueError("tasks_back.json and tasks_gameplay.json must be JSON arrays")

    back_task = find_view_task(back, task_id)
    gameplay_task = find_view_task(gameplay, task_id)

    back_report = validate_view(root=root, label="tasks_back.json", entry=back_task, stage=args.stage)
    game_report = validate_view(root=root, label="tasks_gameplay.json", entry=gameplay_task, stage=args.stage)

    errors = []
    errors.extend(back_report.get("errors") or [])
    errors.extend(game_report.get("errors") or [])

    if back_task is None and gameplay_task is None:
        errors.append("both tasks_back.json and tasks_gameplay.json mapped tasks are missing; at least one view must exist")

    report = {
        "task_id": task_id,
        "stage": args.stage,
        "status": "ok" if not errors else "fail",
        "errors": errors,
        "views": {
            "back": back_report,
            "gameplay": game_report,
        },
    }

    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(f"ACCEPTANCE_REFS status={report['status']} errors={len(errors)} task_id={task_id} stage={args.stage}")
    return 0 if report["status"] == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())

