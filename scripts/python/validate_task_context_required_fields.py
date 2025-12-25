#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Validate required fields in logs/ci/<YYYY-MM-DD>/sc-analyze/task_context.json.

Goal:
  Prevent "done but not real" caused by missing task semantics context.

Important:
  - This is a deterministic metadata gate, NOT a gameplay semantic verifier.
  - It validates the presence and basic shape of:
      tasks.json (master) + tasks_back.json + tasks_gameplay.json mapped entry
      + acceptance/test_strategy/overlay_refs/test_refs (view-specific).

Usage (Windows):
  py -3 scripts/python/validate_task_context_required_fields.py --task-id 11 --stage red --out logs/ci/<date>/.../task-context-req.json
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path
from typing import Any


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def today_str() -> str:
    return dt.date.today().strftime("%Y-%m-%d")


def default_context_path() -> Path:
    # Prefer task-scoped context when present; otherwise fall back to the legacy alias.
    # The caller can always override via --context.
    return repo_root() / "logs" / "ci" / today_str() / "sc-analyze" / "task_context.json"


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def is_non_empty_str(v: Any) -> bool:
    return isinstance(v, str) and v.strip() != ""


def is_str_list(v: Any) -> bool:
    return isinstance(v, list) and all(isinstance(x, str) for x in v)


def normalize_str_list(v: Any) -> list[str]:
    if not isinstance(v, list):
        return []
    return [str(x).strip() for x in v if str(x).strip()]


def validate_overlay_refs(root: Path, label: str, overlay_refs: Any) -> list[str]:
    errors: list[str] = []
    refs = normalize_str_list(overlay_refs)
    if not refs:
        errors.append(f"{label}: overlay_refs missing/empty")
        return errors
    for r in refs:
        p = root / r
        if not p.exists():
            errors.append(f"{label}: overlay_refs path missing on disk: {r}")
    return errors


def validate_view_block(root: Path, label: str, view: Any, *, stage: str) -> list[str]:
    errors: list[str] = []
    # Note: mapping absence is handled by the caller (may be warning/skip as long as the other view exists).
    if not isinstance(view, dict):
        errors.append(f"{label}: view entry must be an object")
        return errors

    errors.extend(validate_overlay_refs(root, label, view.get("overlay_refs")))

    test_strategy = view.get("test_strategy")
    acceptance = view.get("acceptance")

    # These are the "semantic" checklist fields the team relies on. Missing them means the task
    # cannot be implemented reliably, regardless of compilation/tests.
    if not is_str_list(test_strategy) or not normalize_str_list(test_strategy):
        errors.append(f"{label}: test_strategy missing/empty (expected non-empty string list)")
    if not is_str_list(acceptance) or not normalize_str_list(acceptance):
        errors.append(f"{label}: acceptance missing/empty (expected non-empty string list)")

    # test_refs is stage-dependent:
    # - red/green: may be empty (tests may not exist yet)
    # - refactor: must be non-empty (enforced elsewhere as a hard gate)
    test_refs = view.get("test_refs")
    if test_refs is None:
        errors.append(f"{label}: test_refs field missing (expected list; may be empty before refactor)")
    elif not isinstance(test_refs, list):
        errors.append(f"{label}: test_refs must be a list")
    elif stage == "refactor" and not normalize_str_list(test_refs):
        # Keep this as a redundant check; the authoritative hard gate is validate_task_test_refs.py.
        errors.append(f"{label}: test_refs empty at refactor stage (expected non-empty)")

    return errors


def main() -> int:
    ap = argparse.ArgumentParser(description="Validate required fields in sc-analyze task_context.json.")
    ap.add_argument("--task-id", required=True, help="Task id (master id, e.g. 11).")
    ap.add_argument("--stage", choices=["red", "green", "refactor"], required=True)
    ap.add_argument("--context", default="", help="Override task_context.json path.")
    ap.add_argument("--out", required=True, help="Output JSON report path.")
    args = ap.parse_args()

    root = repo_root()
    if args.context:
        ctx_path = Path(args.context)
    else:
        scoped = repo_root() / "logs" / "ci" / today_str() / "sc-analyze" / f"task_context.{args.task_id}.json"
        ctx_path = scoped if scoped.exists() else default_context_path()

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    errors: list[str] = []
    warnings: list[str] = []

    if not ctx_path.exists():
        errors.append(f"context file missing: {ctx_path}")
        report = {
            "task_id": str(args.task_id),
            "stage": args.stage,
            "context": str(ctx_path),
            "status": "fail",
            "errors": errors,
            "warnings": warnings,
        }
        out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
        print(f"TASK_CONTEXT_REQ status=fail errors={len(errors)} task_id={args.task_id} stage={args.stage}")
        return 1

    payload = load_json(ctx_path)
    if not isinstance(payload, dict):
        errors.append("context json must be an object")
        payload = {}

    # Master + mapped views are produced by scripts/sc/analyze.py via scripts/sc/_taskmaster.py (resolve_triplet).
    task_id = str(payload.get("task_id") or "")
    if task_id != str(args.task_id):
        errors.append(f"task_id mismatch: expected {args.task_id} but context has {task_id}")

    master = payload.get("master")
    back = payload.get("back")
    gameplay = payload.get("gameplay")

    if not isinstance(master, dict):
        errors.append("master task missing/invalid in context")
        master = {}

    title = master.get("title")
    status = master.get("status")
    overlay = master.get("overlay")
    adr_refs = master.get("adrRefs")
    arch_refs = master.get("archRefs")
    details = master.get("details")
    test_strategy = master.get("testStrategy")

    if not is_non_empty_str(title):
        errors.append("master.title missing/empty")
    if not is_non_empty_str(status):
        errors.append("master.status missing/empty")
    if not is_non_empty_str(overlay):
        errors.append("master.overlay missing/empty")
    else:
        if not (root / str(overlay)).exists():
            errors.append(f"master.overlay path missing on disk: {overlay}")
    if not is_str_list(adr_refs) or not normalize_str_list(adr_refs):
        errors.append("master.adrRefs missing/empty (expected non-empty string list)")
    if not is_str_list(arch_refs) or not normalize_str_list(arch_refs):
        errors.append("master.archRefs missing/empty (expected non-empty string list)")

    # details/testStrategy may legitimately be short, but should exist to avoid "blank task".
    if details is None or not is_non_empty_str(details):
        warnings.append("master.details missing/empty")
    if test_strategy is None or not is_non_empty_str(test_strategy):
        warnings.append("master.testStrategy missing/empty")

    back_missing = back is None
    gameplay_missing = gameplay is None
    if back_missing and gameplay_missing:
        errors.append("both tasks_back.json and tasks_gameplay.json mapped tasks are missing; at least one view must exist")
    else:
        if back_missing:
            warnings.append("tasks_back.json: mapped task missing (taskmaster_id not found); skipping view validation")
        else:
            errors.extend(validate_view_block(root, "tasks_back.json", back, stage=args.stage))

        if gameplay_missing:
            warnings.append("tasks_gameplay.json: mapped task missing (taskmaster_id not found); skipping view validation")
        else:
            errors.extend(validate_view_block(root, "tasks_gameplay.json", gameplay, stage=args.stage))

    report = {
        "task_id": str(args.task_id),
        "stage": args.stage,
        "context": str(ctx_path),
        "status": "ok" if not errors else "fail",
        "errors": errors,
        "warnings": warnings,
    }

    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(f"TASK_CONTEXT_REQ status={report['status']} errors={len(errors)} warnings={len(warnings)} task_id={args.task_id} stage={args.stage}")
    return 0 if report["status"] == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
