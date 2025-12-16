#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Validate ADR/chapter/overlay refs for all Taskmaster tasks.

This script extends the logic of check_tasks_back_references.py to
cover all tasks in tasks_back.json and tasks_gameplay.json so that
we can reproduce the kind of report you saw in Claude Code.

It only reads JSON/ADR/overlay files and prints a summary; it does
not modify any files.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Dict, List, Set


ADR_FOR_CH: Dict[str, List[str]] = {
    # Repo-level baseline / template lineage
    # Note: ADR-0001 in this repo may contain legacy content; we still map it
    # to the minimal CH set used by tasks to keep traceability checks consistent.
    "ADR-0001": ["CH01", "CH07"],

    "ADR-0002": ["CH02"],
    "ADR-0019": ["CH02"],
    "ADR-0003": ["CH03"],
    "ADR-0004": ["CH04"],
    "ADR-0006": ["CH05"],
    "ADR-0007": ["CH05", "CH06"],
    "ADR-0005": ["CH07"],
    "ADR-0011": ["CH07", "CH10"],
    "ADR-0008": ["CH10"],
    "ADR-0015": ["CH09"],
    "ADR-0018": ["CH01", "CH06", "CH07"],
    "ADR-0020": ["CH05", "CH06"],
    "ADR-0025": ["CH06", "CH07"],
    "ADR-0023": ["CH05"],

    # Sanguo-specific ADRs (phase docs / template rules)
    "ADR-0021": ["CH05", "CH06"],
    "ADR-0022": ["CH04"],
    "ADR-0024": ["CH01", "CH07"],
}


def load_json_list(path: Path) -> list[dict]:
    return json.loads(path.read_text(encoding="utf-8"))


def collect_adr_ids(root: Path) -> Set[str]:
    adr_dir = root / "docs" / "adr"
    ids: Set[str] = set()
    if not adr_dir.exists():
        return ids
    for f in adr_dir.glob("ADR-*.md"):
        m = re.match(r"ADR-(\d{4})", f.stem)
        if m:
            ids.add(f"ADR-{m.group(1)}")
    return ids


def collect_overlay_paths(root: Path) -> Set[str]:
    """
    Collect overlay 08/* paths for all overlays under docs/architecture/overlays.
    """
    overlay_paths: Set[str] = set()

    overlays_root = root / "docs" / "architecture" / "overlays"
    if not overlays_root.exists():
        return overlay_paths

    for prd_dir in overlays_root.iterdir():
        if not prd_dir.is_dir():
            continue
        chapter_dir = prd_dir / "08"
        if not chapter_dir.exists():
            continue
        for p in chapter_dir.glob("*"):
            rel = p.relative_to(root)
            overlay_paths.add(str(rel).replace("\\", "/"))

    return overlay_paths


def check_tasks(tasks: list[dict], adr_ids: Set[str], overlay_paths: Set[str], label: str) -> bool:
    total = len(tasks)
    ok_count = 0
    print(f"\n=== Checking {label} ({total} tasks) ===")

    # For depends_on validation we need the set of known ids within this file.
    known_ids: Set[str] = {str(t.get("id")) for t in tasks if "id" in t}

    for t in sorted(tasks, key=lambda x: x.get("id", "")):
        tid = t.get("id")
        story_id = t.get("story_id")
        has_error = False

        # ADR refs
        missing_adrs = [a for a in t.get("adr_refs", []) if a not in adr_ids]
        if missing_adrs:
            print(f"- {tid}: missing ADRs {missing_adrs}")
            has_error = True

        # chapter_refs vs ADR_FOR_CH
        expected_ch: set[str] = set()
        for adr in t.get("adr_refs", []):
            expected_ch.update(ADR_FOR_CH.get(adr, []))
        current_ch = set(t.get("chapter_refs", []))
        missing_ch = expected_ch - current_ch
        extra_ch = current_ch - expected_ch
        if missing_ch:
            print(f"- {tid}: missing chapter_refs (from ADR): {sorted(missing_ch)}")
            has_error = True
        if extra_ch:
            # Optional improvement (A+B): allow extra chapters as warnings.
            print(f"- {tid}: WARN extra chapter_refs (not implied by ADR map): {sorted(extra_ch)}")

        # overlay_refs only for tasks_back (label heuristic)
        if label.startswith("tasks_back"):
            refs = [p.replace("\\", "/") for p in t.get("overlay_refs", [])]
            if refs:
                missing_overlays = [p for p in refs if p not in overlay_paths]
                if missing_overlays:
                    print(f"- {tid}: missing overlays {missing_overlays}")
                    has_error = True

        # depends_on: ensure all referenced ids exist in the same task file.
        # This is a local consistency check; cross-file mapping is handled elsewhere.
        deps = [str(d) for d in t.get("depends_on") or []]
        missing_deps = [d for d in deps if d not in known_ids]
        if missing_deps:
            print(f"- {tid}: depends_on references missing ids {missing_deps}")
            has_error = True

        if not has_error:
            ok_count += 1

    print(f"Summary for {label}: {ok_count}/{total} tasks passed")
    return ok_count == total


def run_check_all(root: Path) -> bool:
    """Run full ADR/CH/overlay checks for all task files."""
    adr_ids = collect_adr_ids(root)
    overlay_paths = collect_overlay_paths(root)

    back = load_json_list(root / ".taskmaster" / "tasks" / "tasks_back.json")
    gameplay = load_json_list(root / ".taskmaster" / "tasks" / "tasks_gameplay.json")

    print(f"known ADR ids (sample): {sorted(adr_ids)[:10]} ...")
    print(f"overlay files (08/*): {sorted(overlay_paths)}")

    ok_back = check_tasks(back, adr_ids, overlay_paths, label="tasks_back.json")
    ok_gameplay = check_tasks(gameplay, adr_ids, overlay_paths, label="tasks_gameplay.json")
    return ok_back and ok_gameplay


def main() -> None:
    root = Path(__file__).resolve().parents[2]
    ok = run_check_all(root)
    if not ok:
        raise SystemExit(1)


if __name__ == "__main__":  # pragma: no cover
    main()
