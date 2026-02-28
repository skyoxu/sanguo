#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Validate ADR/chapter/overlay/dependency references for task view files.

Scope:
- .taskmaster/tasks/tasks_back.json
- .taskmaster/tasks/tasks_gameplay.json

Validation levels:
1) Hard errors (fail gate):
   - Missing required fields
   - ADR ids that do not exist under docs/adr
   - Invalid chapter_refs format (must be CH01..CH12)
   - overlay_refs paths that do not exist
   - depends_on ids that do not exist in the same task file
2) Warnings (non-blocking):
   - chapter_refs differ from ADR->chapter mapping in ADR_FOR_CH
   - ADR present but not mapped in ADR_FOR_CH

This keeps hard-gate correctness strict while making chapter mapping drift visible
without over-blocking when ADR mapping evolves.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


# ADR -> chapter mapping for consistency warnings.
# Values are used as expected chapter refs. Missing/extra chapters are warnings.
ADR_FOR_CH: dict[str, list[str]] = {
    "ADR-0001": ["CH01", "CH07"],
    "ADR-0002": ["CH02"],
    "ADR-0003": ["CH03"],
    "ADR-0004": ["CH04"],
    "ADR-0005": ["CH07"],
    "ADR-0006": ["CH05"],
    "ADR-0007": ["CH05", "CH06"],
    "ADR-0008": ["CH10"],
    "ADR-0009": ["CH10"],
    "ADR-0010": ["CH10"],
    "ADR-0011": ["CH07", "CH10"],
    "ADR-0012": ["CH07"],
    "ADR-0015": ["CH09"],
    "ADR-0016": ["CH05"],
    "ADR-0017": ["CH07"],
    "ADR-0018": ["CH01", "CH06", "CH07"],
    "ADR-0019": ["CH02"],
    "ADR-0020": ["CH05", "CH06"],
    "ADR-0021": ["CH05", "CH06"],
    "ADR-0022": ["CH04"],
    "ADR-0023": ["CH05"],
    "ADR-0024": ["CH01", "CH07"],
    "ADR-0025": ["CH06", "CH07"],
    "ADR-0026": ["CH04", "CH06"],
    "ADR-0027": ["CH05", "CH06"],
    "ADR-0028": ["CH04"],
    "ADR-0029": ["CH06", "CH07"],
    "ADR-0030": ["CH06", "CH09"],
    "ADR-0031": ["CH07", "CH10"],
    "ADR-0032": ["CH05", "CH06", "CH07"],
    "ADR-0033": ["CH05", "CH06"],
}


REQUIRED_FIELDS = ["layer", "adr_refs", "chapter_refs", "overlay_refs", "depends_on"]
CHAPTER_RE = re.compile(r"^CH(0[1-9]|1[0-2])$")


def _norm(path: str) -> str:
    return path.replace("\\", "/")


def load_json_list(path: Path) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError(f"Task file must be JSON array: {_norm(str(path))}")
    return payload


def collect_adr_ids(root: Path) -> set[str]:
    adr_dir = root / "docs" / "adr"
    ids: set[str] = set()
    if not adr_dir.exists():
        return ids
    for file_path in adr_dir.glob("ADR-*.md"):
        match = re.match(r"ADR-(\d{4})", file_path.stem)
        if match:
            ids.add(f"ADR-{match.group(1)}")
    return ids


def collect_overlay_paths(root: Path) -> set[str]:
    overlay_paths: set[str] = set()
    overlays_root = root / "docs" / "architecture" / "overlays"
    if not overlays_root.exists():
        return overlay_paths

    for prd_dir in overlays_root.iterdir():
        if not prd_dir.is_dir():
            continue
        chapter_dir = prd_dir / "08"
        if not chapter_dir.exists():
            continue
        for item in chapter_dir.glob("*"):
            if item.is_file():
                overlay_paths.add(_norm(str(item.relative_to(root))))
    return overlay_paths


def _validate_task(
    task: dict[str, Any],
    known_ids: set[str],
    adr_ids: set[str],
    overlay_paths: set[str],
) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []

    task_id = str(task.get("id", ""))

    # Required fields existence/type
    for field in REQUIRED_FIELDS:
        if field not in task:
            errors.append(f"{task_id}: missing required field '{field}'")
            continue
        if field in {"adr_refs", "chapter_refs", "overlay_refs", "depends_on"} and not isinstance(task[field], list):
            errors.append(f"{task_id}: field '{field}' must be array")

    adr_refs = task.get("adr_refs") if isinstance(task.get("adr_refs"), list) else []
    chapter_refs = task.get("chapter_refs") if isinstance(task.get("chapter_refs"), list) else []
    overlay_refs = task.get("overlay_refs") if isinstance(task.get("overlay_refs"), list) else []
    depends_on = task.get("depends_on") if isinstance(task.get("depends_on"), list) else []

    # ADR refs must exist
    for adr in adr_refs:
        adr_id = str(adr)
        if adr_id not in adr_ids:
            errors.append(f"{task_id}: missing ADR file for '{adr_id}'")

    # Chapter format validity
    for chapter in chapter_refs:
        chapter_id = str(chapter)
        if not CHAPTER_RE.match(chapter_id):
            errors.append(f"{task_id}: invalid chapter ref '{chapter_id}' (expected CH01..CH12)")

    # Overlay path existence
    for overlay in overlay_refs:
        overlay_path = _norm(str(overlay))
        if overlay_path not in overlay_paths:
            errors.append(f"{task_id}: missing overlay file '{overlay_path}'")

    # depends_on local integrity
    for dep in depends_on:
        dep_id = str(dep)
        if dep_id not in known_ids:
            errors.append(f"{task_id}: depends_on references missing id '{dep_id}'")

    # Non-blocking chapter alignment warnings
    expected_chapters: set[str] = set()
    for adr in adr_refs:
        adr_id = str(adr)
        mapped = ADR_FOR_CH.get(adr_id)
        if mapped is None:
            warnings.append(f"{task_id}: ADR '{adr_id}' not mapped in ADR_FOR_CH")
            continue
        expected_chapters.update(mapped)

    current_chapters = {str(x) for x in chapter_refs}
    missing_ch = sorted(expected_chapters - current_chapters)
    extra_ch = sorted(current_chapters - expected_chapters)
    if missing_ch:
        warnings.append(f"{task_id}: missing chapter_refs from ADR map {missing_ch}")
    if extra_ch:
        warnings.append(f"{task_id}: extra chapter_refs not in ADR map {extra_ch}")

    return errors, warnings


def check_tasks(tasks: list[dict[str, Any]], adr_ids: set[str], overlay_paths: set[str], label: str) -> tuple[bool, list[str], list[str]]:
    print(f"\n=== Checking {label} ({len(tasks)} tasks) ===")

    known_ids = {str(item.get("id")) for item in tasks if item.get("id") is not None}
    all_errors: list[str] = []
    all_warnings: list[str] = []

    for task in sorted(tasks, key=lambda x: str(x.get("id", ""))):
        errors, warnings = _validate_task(task, known_ids, adr_ids, overlay_paths)
        all_errors.extend(errors)
        all_warnings.extend(warnings)

    for message in all_errors:
        print(f"- ERROR: {message}")
    for message in all_warnings:
        print(f"- WARN: {message}")

    failed = len(all_errors)
    warn_count = len(all_warnings)
    passed = len(tasks) - len({msg.split(':', 1)[0] for msg in all_errors})
    print(f"Summary for {label}: passed={passed}/{len(tasks)} errors={failed} warnings={warn_count}")

    return failed == 0, all_errors, all_warnings


def _write_summary(path: Path, summary: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def run_check_all(root: Path, max_warnings: int = -1, summary_out: Path | None = None) -> bool:
    adr_ids = collect_adr_ids(root)
    overlay_paths = collect_overlay_paths(root)

    back = load_json_list(root / ".taskmaster" / "tasks" / "tasks_back.json")
    gameplay = load_json_list(root / ".taskmaster" / "tasks" / "tasks_gameplay.json")

    print(f"known ADR ids (sample): {sorted(adr_ids)[:12]} ...")
    print(f"overlay files (08/*): {sorted(overlay_paths)}")

    ok_back, back_errors, back_warnings = check_tasks(back, adr_ids, overlay_paths, "tasks_back.json")
    ok_gameplay, gameplay_errors, gameplay_warnings = check_tasks(gameplay, adr_ids, overlay_paths, "tasks_gameplay.json")

    total_warnings = len(back_warnings) + len(gameplay_warnings)
    warning_budget_ok = True
    if max_warnings >= 0 and total_warnings > max_warnings:
        print(
            f"- ERROR: warning budget exceeded: warnings={total_warnings} budget={max_warnings}"
        )
        warning_budget_ok = False

    summary = {
        "action": "check-tasks-all-refs",
        "status": "ok" if (ok_back and ok_gameplay and warning_budget_ok) else "fail",
        "max_warnings": max_warnings,
        "total_warnings": total_warnings,
        "files": {
            "tasks_back.json": {
                "tasks": len(back),
                "errors": len(back_errors),
                "warnings": len(back_warnings),
            },
            "tasks_gameplay.json": {
                "tasks": len(gameplay),
                "errors": len(gameplay_errors),
                "warnings": len(gameplay_warnings),
            },
        },
    }
    if summary_out is not None:
        _write_summary(summary_out, summary)

    return ok_back and ok_gameplay and warning_budget_ok


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Validate ADR/chapter/overlay/dependency references for task view files.",
    )
    parser.add_argument(
        "--max-warnings",
        type=int,
        default=-1,
        help="Fail when total warning count exceeds this value; -1 disables budget check.",
    )
    parser.add_argument(
        "--summary-out",
        type=str,
        default="",
        help="Optional summary json output path.",
    )
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[2]
    summary_out = Path(args.summary_out) if args.summary_out else None
    ok = run_check_all(root, max_warnings=args.max_warnings, summary_out=summary_out)
    if not ok:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
