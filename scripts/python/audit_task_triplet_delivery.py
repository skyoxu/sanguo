#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Audit (proxy) task delivery against the Taskmaster triplet:
  - .taskmaster/tasks/tasks.json (master)
  - .taskmaster/tasks/tasks_back.json (back view)
  - .taskmaster/tasks/tasks_gameplay.json (gameplay view)

This is NOT a semantic verifier.
It is a deterministic "evidence integrity" audit to reduce the risk of:
  - Task implemented but metadata (test_refs / overlay_refs / ADR refs) missing
  - Task description drift between master/back/gameplay views

Outputs (logs/ci/<YYYY-MM-DD>/task-triplet-audit/):
  - report.json
  - report.md

Usage (Windows):
  py -3 scripts/python/audit_task_triplet_delivery.py --task-id 10 --task-id 12 --task-id 14
  py -3 scripts/python/audit_task_triplet_delivery.py --task-ids 10,12,14
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
from pathlib import Path
from typing import Any


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def today_str() -> str:
    return dt.date.today().strftime("%Y-%m-%d")


def ci_dir(name: str) -> Path:
    out = repo_root() / "logs" / "ci" / today_str() / name
    out.mkdir(parents=True, exist_ok=True)
    return out


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def iter_master_tasks(tasks_json: dict[str, Any]) -> list[dict[str, Any]]:
    master = tasks_json.get("master") or {}
    tasks = master.get("tasks") or []
    if not isinstance(tasks, list):
        return []
    return [t for t in tasks if isinstance(t, dict)]


def find_master_task(tasks_json: dict[str, Any], task_id: str) -> dict[str, Any] | None:
    for t in iter_master_tasks(tasks_json):
        if str(t.get("id")) == str(task_id):
            return t
    return None


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


def validate_test_refs(
    root: Path, label: str, entry: dict[str, Any] | None, *, require_non_empty: bool
) -> tuple[list[str], list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    normalized: list[str] = []

    if entry is None:
        errors.append(f"{label}: mapped task not found by taskmaster_id")
        return errors, warnings, normalized

    raw = entry.get("test_refs")
    if raw is None:
        errors.append(f"{label}: test_refs field missing")
        return errors, warnings, normalized

    if not isinstance(raw, list):
        errors.append(f"{label}: test_refs must be a list")
        return errors, warnings, normalized

    normalized = [str(x).strip() for x in raw if str(x).strip()]
    if require_non_empty and not normalized:
        errors.append(f"{label}: test_refs is empty (hard gate expected at refactor stage)")
        return errors, warnings, normalized

    for r in normalized:
        if is_abs_path(r):
            errors.append(f"{label}: absolute path is not allowed in test_refs: {r}")
            continue
        if not (root / r).exists():
            errors.append(f"{label}: referenced file not found: {r}")

    return errors, warnings, normalized


def auto_discover_task_tests(root: Path, task_id: str) -> list[str]:
    # Conservative heuristic: only discover files that clearly indicate the task id in filename.
    candidates: list[Path] = []
    for base in ["Game.Core.Tests", "Tests", "Tests.Godot"]:
        d = root / base
        if not d.exists():
            continue
        candidates.extend(d.rglob(f"*{task_id}*Test*.cs"))
        candidates.extend(d.rglob(f"*Task{task_id}*Tests.cs"))
        candidates.extend(d.rglob(f"*task_{task_id}*.gd"))
        candidates.extend(d.rglob(f"*Task{task_id}*.gd"))
    rel = {str(p.relative_to(root)).replace("\\", "/") for p in candidates if p.is_file()}
    return sorted(rel)


def main() -> int:
    ap = argparse.ArgumentParser(description="Audit task delivery evidence across tasks.json/back/gameplay.")
    ap.add_argument("--task-id", action="append", default=[], help="Task id (repeatable).")
    ap.add_argument("--task-ids", default="", help="Comma-separated task ids.")
    ap.add_argument(
        "--require-non-empty-test-refs",
        action="store_true",
        help="Treat empty test_refs as errors (matches refactor-stage hard gate).",
    )
    args = ap.parse_args()

    raw_ids: list[str] = []
    raw_ids.extend([str(x).strip() for x in (args.task_id or []) if str(x).strip()])
    raw_ids.extend([x.strip() for x in str(args.task_ids or "").split(",") if x.strip()])
    task_ids = sorted(set(raw_ids), key=lambda x: int(x) if x.isdigit() else x)
    if not task_ids:
        print("TASK_TRIPLET_AUDIT ERROR: no task ids provided")
        return 2

    root = repo_root()
    out_dir = ci_dir("task-triplet-audit")

    tasks_json_path = root / ".taskmaster" / "tasks" / "tasks.json"
    back_path = root / ".taskmaster" / "tasks" / "tasks_back.json"
    gameplay_path = root / ".taskmaster" / "tasks" / "tasks_gameplay.json"

    tasks_json = load_json(tasks_json_path)
    back = load_json(back_path)
    gameplay = load_json(gameplay_path)
    if not isinstance(back, list) or not isinstance(gameplay, list):
        raise ValueError("tasks_back.json and tasks_gameplay.json must be JSON arrays")

    per_task: list[dict[str, Any]] = []
    any_errors = False

    for tid in task_ids:
        master = find_master_task(tasks_json, tid)
        back_task = find_view_task(back, tid)
        gameplay_task = find_view_task(gameplay, tid)

        errors: list[str] = []
        warnings: list[str] = []

        if master is None:
            errors.append("tasks.json: master task not found by id")

        overlay = str((master or {}).get("overlay") or "")
        overlay_exists = bool(overlay and (root / overlay).exists())
        if overlay and not overlay_exists:
            errors.append(f"tasks.json: overlay path missing on disk: {overlay}")

        adr_refs = (master or {}).get("adrRefs") or []
        arch_refs = (master or {}).get("archRefs") or []
        if not adr_refs:
            warnings.append("tasks.json: adrRefs missing/empty (repo rule expects >=1 Accepted ADR for code changes)")
        if not arch_refs:
            warnings.append("tasks.json: archRefs missing/empty")

        e1, w1, back_refs = validate_test_refs(
            root,
            "tasks_back.json",
            back_task,
            require_non_empty=bool(args.require_non_empty_test_refs),
        )
        e2, w2, gameplay_refs = validate_test_refs(
            root,
            "tasks_gameplay.json",
            gameplay_task,
            require_non_empty=bool(args.require_non_empty_test_refs),
        )
        errors.extend(e1)
        errors.extend(e2)
        warnings.extend(w1)
        warnings.extend(w2)

        discovered = auto_discover_task_tests(root, tid)
        if not discovered:
            warnings.append("repo scan: no obvious test files discovered by task-id heuristic")

        red_skeleton = root / "Game.Core.Tests" / "Tasks" / f"Task{tid}RedTests.cs"
        if red_skeleton.exists():
            errors.append(f"red skeleton must not exist at refactor stage: {red_skeleton.relative_to(root)}")

        if errors:
            any_errors = True

        per_task.append(
            {
                "task_id": tid,
                "title": (master or {}).get("title"),
                "status": (master or {}).get("status"),
                "master": {
                    "details": (master or {}).get("details"),
                    "testStrategy": (master or {}).get("testStrategy"),
                    "overlay": overlay or None,
                },
                "back": {
                    "mapped": bool(back_task),
                    "details": (back_task or {}).get("details"),
                    "test_strategy": (back_task or {}).get("test_strategy"),
                    "acceptance": (back_task or {}).get("acceptance"),
                    "overlay_refs": (back_task or {}).get("overlay_refs"),
                    "test_refs": back_refs,
                },
                "gameplay": {
                    "mapped": bool(gameplay_task),
                    "details": (gameplay_task or {}).get("details"),
                    "test_strategy": (gameplay_task or {}).get("test_strategy"),
                    "acceptance": (gameplay_task or {}).get("acceptance"),
                    "overlay_refs": (gameplay_task or {}).get("overlay_refs"),
                    "test_refs": gameplay_refs,
                },
                "evidence": {
                    "overlay_exists": overlay_exists,
                    "discovered_test_files": discovered,
                },
                "errors": errors,
                "warnings": warnings,
                "status_eval": "ok" if not errors else "fail",
            }
        )

    report = {
        "cmd": "task-triplet-audit",
        "date": today_str(),
        "task_ids": task_ids,
        "require_non_empty_test_refs": bool(args.require_non_empty_test_refs),
        "status": "ok" if not any_errors else "fail",
        "tasks": per_task,
        "note": "Deterministic evidence audit only (not a semantic verifier). Use sc-acceptance-check + llm_review for semantic review.",
    }

    (out_dir / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")

    md_lines: list[str] = []
    md_lines.append("# Task triplet delivery audit (proxy)")
    md_lines.append("")
    md_lines.append(f"- date: {report['date']}")
    md_lines.append(f"- status: {report['status']}")
    md_lines.append(f"- require_non_empty_test_refs: {report['require_non_empty_test_refs']}")
    md_lines.append(f"- tasks: {', '.join(task_ids)}")
    md_lines.append("")
    for t in per_task:
        md_lines.append(f"## Task {t['task_id']}: {t.get('title')}")
        md_lines.append("")
        md_lines.append(f"- status: {t.get('status')}")
        md_lines.append(f"- overlay: {t['master'].get('overlay')} (exists={t['evidence'].get('overlay_exists')})")
        md_lines.append(f"- back.mapped: {t['back'].get('mapped')} gameplay.mapped: {t['gameplay'].get('mapped')}")
        md_lines.append(f"- back.test_refs: {len(t['back'].get('test_refs') or [])} gameplay.test_refs: {len(t['gameplay'].get('test_refs') or [])}")
        md_lines.append(f"- discovered_test_files: {len(t['evidence'].get('discovered_test_files') or [])}")
        if t["errors"]:
            md_lines.append("")
            md_lines.append("### Errors")
            for e in t["errors"]:
                md_lines.append(f"- {e}")
        if t["warnings"]:
            md_lines.append("")
            md_lines.append("### Warnings")
            for w in t["warnings"]:
                md_lines.append(f"- {w}")
        md_lines.append("")
    (out_dir / "report.md").write_text("\n".join(md_lines).rstrip() + "\n", encoding="utf-8", newline="\n")

    print(f"TASK_TRIPLET_AUDIT status={report['status']} out={out_dir}")
    return 0 if report["status"] == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())

