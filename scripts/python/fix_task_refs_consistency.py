#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Fix consistency across Taskmaster triplet files:
  - .taskmaster/tasks/tasks.json
  - .taskmaster/tasks/tasks_back.json
  - .taskmaster/tasks/tasks_gameplay.json

Goals:
1) Keep existing schemas/field names unchanged.
2) For tasks mapped by taskmaster_id:
   - unify ADR refs across the three files (union, then sort),
   - ensure chapter refs include all chapters implied by ADR_FOR_CH
     (extra chapters are allowed; we only add missing ones).
3) Keep mirror fields in sync:
   - tasks_back.json: adr_refs <-> adrRefs, chapter_refs <-> archRefs
   - tasks_gameplay.json: adr_refs <-> adrRefs, chapter_refs <-> archRefs

This script uses Python for both reading and writing (UTF-8) per repo rules.

Usage (Windows, from repo root):
  py -3 scripts/python/fix_task_refs_consistency.py
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Set


PROJECT_ROOT = Path(__file__).resolve().parents[2]
TASKS_JSON_PATH = PROJECT_ROOT / ".taskmaster" / "tasks" / "tasks.json"
TASKS_BACK_PATH = PROJECT_ROOT / ".taskmaster" / "tasks" / "tasks_back.json"
TASKS_GAMEPLAY_PATH = PROJECT_ROOT / ".taskmaster" / "tasks" / "tasks_gameplay.json"


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _load_adr_for_ch() -> Dict[str, List[str]]:
    check_path = PROJECT_ROOT / "scripts" / "python" / "check_tasks_all_refs.py"
    spec = importlib.util.spec_from_file_location("check_tasks_all_refs", check_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to import ADR_FOR_CH from {check_path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore[attr-defined]
    adr_for_ch = getattr(mod, "ADR_FOR_CH", None)
    if not isinstance(adr_for_ch, dict):
        raise RuntimeError("ADR_FOR_CH not found or invalid in check_tasks_all_refs.py")
    return adr_for_ch


def _sort_adrs(adrs: Iterable[str]) -> List[str]:
    # Lexicographic sort keeps ADR-0001..ADR-9999 stable.
    return sorted({a for a in adrs if isinstance(a, str) and a})


def _sort_chapters(chapters: Iterable[str]) -> List[str]:
    def key(ch: str) -> tuple[int, str]:
        if isinstance(ch, str) and ch.startswith("CH") and len(ch) >= 4:
            try:
                return (int(ch[2:4]), ch)
            except ValueError:
                pass
        return (999, str(ch))

    uniq = {c for c in chapters if isinstance(c, str) and c}
    return sorted(uniq, key=key)


def _expected_chapters(adr_refs: Iterable[str], adr_for_ch: Dict[str, List[str]]) -> Set[str]:
    expected: Set[str] = set()
    for adr in adr_refs:
        expected.update(adr_for_ch.get(str(adr), []))
    return expected


def main() -> int:
    if not TASKS_JSON_PATH.exists():
        raise SystemExit(f"tasks.json not found: {TASKS_JSON_PATH}")
    if not TASKS_BACK_PATH.exists():
        raise SystemExit(f"tasks_back.json not found: {TASKS_BACK_PATH}")
    if not TASKS_GAMEPLAY_PATH.exists():
        raise SystemExit(f"tasks_gameplay.json not found: {TASKS_GAMEPLAY_PATH}")

    adr_for_ch = _load_adr_for_ch()

    tasks_json = _load_json(TASKS_JSON_PATH)
    master_tasks: List[Dict[str, Any]] = tasks_json.get("master", {}).get("tasks", [])
    master_by_id: Dict[int, Dict[str, Any]] = {int(t["id"]): t for t in master_tasks if "id" in t}

    tasks_back: List[Dict[str, Any]] = _load_json(TASKS_BACK_PATH)
    back_by_tm: Dict[int, Dict[str, Any]] = {
        int(t["taskmaster_id"]): t for t in tasks_back if t.get("taskmaster_id") is not None
    }

    tasks_gameplay: List[Dict[str, Any]] = _load_json(TASKS_GAMEPLAY_PATH)
    gameplay_by_tm: Dict[int, Dict[str, Any]] = {
        int(t["taskmaster_id"]): t for t in tasks_gameplay if t.get("taskmaster_id") is not None
    }

    # 1) Unify ADR refs for mapped tasks (union across files).
    for tm_id, master_task in master_by_id.items():
        back_task = back_by_tm.get(tm_id)
        gameplay_task = gameplay_by_tm.get(tm_id)

        master_adrs = set(master_task.get("adrRefs") or [])
        back_adrs = set(back_task.get("adr_refs") or []) if back_task else set()
        gameplay_adrs = set(gameplay_task.get("adr_refs") or []) if gameplay_task else set()

        unified_adrs = _sort_adrs(master_adrs | back_adrs | gameplay_adrs)

        master_task["adrRefs"] = unified_adrs

        if back_task is not None:
            back_task["adr_refs"] = unified_adrs
            back_task["adrRefs"] = unified_adrs

        if gameplay_task is not None:
            gameplay_task["adr_refs"] = unified_adrs
            gameplay_task["adrRefs"] = unified_adrs

    # 2) Ensure chapter refs include everything implied by ADR_FOR_CH (add missing only).
    for tm_id, master_task in master_by_id.items():
        unified_adrs = master_task.get("adrRefs") or []
        expected = _expected_chapters(unified_adrs, adr_for_ch)

        # tasks.json mirror: archRefs
        current_arch = set(master_task.get("archRefs") or [])
        master_task["archRefs"] = _sort_chapters(current_arch | expected)

        # tasks_back.json mirror: chapter_refs <-> archRefs
        back_task = back_by_tm.get(tm_id)
        if back_task is not None:
            current_ch = set(back_task.get("chapter_refs") or [])
            fixed = _sort_chapters(current_ch | expected)
            back_task["chapter_refs"] = fixed
            back_task["archRefs"] = fixed

        # tasks_gameplay.json mirror: chapter_refs <-> archRefs
        gameplay_task = gameplay_by_tm.get(tm_id)
        if gameplay_task is not None:
            current_ch = set(gameplay_task.get("chapter_refs") or [])
            fixed = _sort_chapters(current_ch | expected)
            gameplay_task["chapter_refs"] = fixed
            gameplay_task["archRefs"] = fixed

    _write_json(TASKS_JSON_PATH, tasks_json)
    _write_json(TASKS_BACK_PATH, tasks_back)
    _write_json(TASKS_GAMEPLAY_PATH, tasks_gameplay)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

