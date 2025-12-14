#!/usr/bin/env python3
"""
Validate task overlay references and ACCEPTANCE_CHECKLIST.md front matter.

Checks:
1) Overlay paths exist (for `overlay` or `overlay_refs`).
2) If an overlay file is ACCEPTANCE_CHECKLIST.md:
   - YAML front matter exists.
   - Required fields exist: PRD-ID, Title, Status, ADR-Refs, Test-Refs.
   - ADR-Refs point to existing ADRs under docs/adr.
   - Required section headings exist (kept in Chinese in the checklist, but encoded here via \\u escapes).

Usage:
  py -3 scripts/python/validate_task_overlays.py
  py -3 scripts/python/validate_task_overlays.py --task-file .taskmaster/tasks/tasks_gameplay.json
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any, Optional


FRONT_MATTER_RE = re.compile(r"^---\s*\n(.*?)\n---", re.DOTALL)


def extract_front_matter(content: str) -> Optional[dict[str, Any]]:
    """Extract a minimal YAML front matter block from a Markdown file."""

    match = FRONT_MATTER_RE.match(content)
    if not match:
        return None

    fm_text = match.group(1)
    result: dict[str, Any] = {
        "PRD-ID": None,
        "Title": None,
        "Status": None,
        "ADR-Refs": [],
        "Test-Refs": [],
    }

    current_key: Optional[str] = None
    for raw_line in fm_text.split("\n"):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue

        if ":" in line and not line.startswith("-"):
            key, value = line.split(":", 1)
            key = key.strip()
            value = value.strip()

            if key in result:
                current_key = key
                if value:
                    if key in {"ADR-Refs", "Test-Refs"}:
                        result[key] = [value]
                    else:
                        result[key] = value
                else:
                    result[key] = []
            continue

        if line.startswith("-") and current_key:
            value = line[1:].strip()
            if "#" in value:
                value = value.split("#", 1)[0].strip()
            if value:
                result[current_key].append(value)

    return result


def collect_adr_ids(root: Path) -> set[str]:
    """Collect existing ADR ids under docs/adr."""

    adr_dir = root / "docs" / "adr"
    ids: set[str] = set()
    if not adr_dir.exists():
        return ids

    for file_path in adr_dir.glob("ADR-*.md"):
        match = re.match(r"ADR-(\d{4})", file_path.stem)
        if match:
            ids.add(f"ADR-{match.group(1)}")
    return ids


def validate_acceptance_checklist(checklist_path: Path, adr_ids: set[str]) -> list[str]:
    """Validate ACCEPTANCE_CHECKLIST.md schema and required content."""

    errors: list[str] = []

    if not checklist_path.exists():
        return [f"File not found: {checklist_path}"]

    try:
        content = checklist_path.read_text(encoding="utf-8")
    except Exception as exc:  # noqa: BLE001
        return [f"Failed to read file: {exc}"]

    fm = extract_front_matter(content)
    if not fm:
        return ["Missing YAML front matter block (--- ... ---)."]

    if not fm.get("PRD-ID"):
        errors.append("Front matter missing required field: PRD-ID")
    if not fm.get("Title"):
        errors.append("Front matter missing required field: Title")
    if not fm.get("Status"):
        errors.append("Front matter missing required field: Status")

    adr_refs = fm.get("ADR-Refs") or []
    if not adr_refs:
        errors.append("Front matter missing required field: ADR-Refs")
    else:
        for adr_ref in adr_refs:
            if adr_ref not in adr_ids:
                errors.append(f"ADR-Refs points to missing ADR: {adr_ref}")

    test_refs = fm.get("Test-Refs") or []
    if not test_refs:
        errors.append("Front matter missing required field: Test-Refs")

    required_sections = [
        "\u4e00\u3001\u6587\u6863\u5b8c\u6574\u6027\u9a8c\u6536",
        "\u4e8c\u3001\u67b6\u6784\u8bbe\u8ba1\u9a8c\u6536",
        "\u4e09\u3001\u4ee3\u7801\u5b9e\u73b0\u9a8c\u6536",
        "\u56db\u3001\u6d4b\u8bd5\u6846\u67b6\u9a8c\u6536",
    ]

    for section in required_sections:
        if section not in content:
            errors.append(f"Missing required section heading: {section}")

    return errors


def load_tasks_from_file(task_file: Path) -> list[dict[str, Any]]:
    """Load task list from a task JSON file."""

    if not task_file.exists():
        return []
    data = json.loads(task_file.read_text(encoding="utf-8"))
    if isinstance(data, list):
        return data
    if isinstance(data, dict) and isinstance(data.get("tasks"), list):
        return data["tasks"]
    return []


def validate_task_file(root: Path, task_file: Path, label: str, adr_ids: set[str]) -> tuple[int, int]:
    """Validate overlay references for a single task file.

    Returns: (tasks_with_overlays, tasks_passed)
    """

    tasks = load_tasks_from_file(task_file)
    if not tasks:
        print(f"\n{label}: no tasks found or file missing")
        return 0, 0

    print("\n" + "=" * 60)
    print(f"{label}: {len(tasks)} tasks")
    print("=" * 60)

    tasks_with_overlays = 0
    passed = 0

    for task in sorted(tasks, key=lambda x: str(x.get("id", ""))):
        tid = task.get("id")

        overlay_refs = task.get("overlay_refs")
        if overlay_refs:
            overlays = overlay_refs if isinstance(overlay_refs, list) else [overlay_refs]
        else:
            overlay = task.get("overlay")
            overlays = [overlay] if overlay else []

        if not overlays:
            continue

        tasks_with_overlays += 1
        print(f"\n== {tid} ==")

        task_ok = True
        for overlay_path in overlays:
            full_path = root / str(overlay_path)
            if not full_path.exists():
                print(f"  ERROR: overlay file does not exist: {overlay_path}")
                task_ok = False
                continue

            if full_path.name == "ACCEPTANCE_CHECKLIST.md":
                errors = validate_acceptance_checklist(full_path, adr_ids)
                if errors:
                    print("  ERROR: ACCEPTANCE_CHECKLIST.md validation failed:")
                    for err in errors:
                        print(f"    - {err}")
                    task_ok = False
                else:
                    print(f"  overlay OK: {overlay_path}")
            else:
                print(f"  overlay OK: {overlay_path}")

        if task_ok:
            passed += 1

    if tasks_with_overlays == 0:
        print("\n(no tasks contain overlay fields)")

    return tasks_with_overlays, passed


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate task overlay references and ACCEPTANCE_CHECKLIST.md front matter.",
    )
    parser.add_argument(
        "--task-file",
        type=str,
        help="Task file path to validate (default: all .taskmaster/tasks/*.json).",
    )

    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]

    adr_ids = collect_adr_ids(root)
    preview = sorted(list(adr_ids))[:10]
    print(f"Found {len(adr_ids)} ADR ids. Preview: {preview} ...")

    if args.task_file:
        task_files = [Path(args.task_file)]
    else:
        task_files = list((root / ".taskmaster" / "tasks").glob("*.json"))

    if not task_files:
        print("ERROR: no task files found")
        return 1

    total_checked = 0
    total_passed = 0
    for task_file in task_files:
        checked, passed = validate_task_file(root, task_file, task_file.name, adr_ids)
        total_checked += checked
        total_passed += passed

    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)
    print(f"Tasks checked (with overlays): {total_checked}")
    print(f"Tasks passed: {total_passed}")

    if total_checked == 0:
        print("NOTE: no tasks contain overlay fields")
        return 0
    if total_passed < total_checked:
        failed = total_checked - total_passed
        print(f"ERROR: {failed} tasks failed overlay validation")
        return 1

    print("All overlay validations passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

