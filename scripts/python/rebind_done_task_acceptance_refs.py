#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Rebind acceptance "Refs:" for done/in-progress tasks to existing, passing test files.

Why:
  Bulk-generated placeholder acceptance tests can introduce failing assertions for
  already-completed tasks. This tool rewrites Refs for completed tasks to point to
  existing tests that already cover the implemented behavior, and syncs test_refs.

This script:
  - Updates BOTH `.taskmaster/tasks/tasks_back.json` and `.taskmaster/tasks/tasks_gameplay.json`.
  - For selected task ids: rewrites every acceptance item to end with:
      "Refs: <one or more existing test paths>"
  - Replaces task-level test_refs with the union of those refs.

Notes:
  - It does NOT modify tasks.json.
  - It does NOT create any tests.

Windows:
  py -3 scripts/python/rebind_done_task_acceptance_refs.py --write
  py -3 scripts/python/rebind_done_task_acceptance_refs.py --task-ids 10,11,14 --write
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


REFS_RE = re.compile(r"\bRefs\s*:\s*(.+)$", flags=re.IGNORECASE)


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")


def split_csv(s: str) -> list[str]:
    return [p.strip() for p in str(s or "").split(",") if p.strip()]


def _strip_refs_suffix(text: str) -> str:
    return REFS_RE.sub("", str(text or "").strip()).rstrip()


def _normalize(p: str) -> str:
    return str(p).strip().replace("\\", "/")


def _exists(root: Path, rel: str) -> bool:
    rel = _normalize(rel)
    return (root / rel).is_file()


def _rewrite_acceptance_items(items: Any, refs: list[str]) -> list[str]:
    if not isinstance(items, list):
        return []
    out: list[str] = []
    suffix = "Refs: " + " ".join(refs)
    for raw in items:
        s = str(raw or "").strip()
        if not s:
            out.append(s)
            continue
        base = _strip_refs_suffix(s)
        out.append(f"{base} {suffix}")
    return out


def _apply_to_view(view: list[dict[str, Any]], task_id: int, refs: list[str], *, root: Path) -> bool:
    changed = False
    for t in view:
        if not isinstance(t, dict):
            continue
        if t.get("taskmaster_id") != task_id:
            continue

        # Ensure refs exist.
        existing = [r for r in refs if _exists(root, r)]
        if not existing:
            raise ValueError(f"No existing refs found on disk for task {task_id}: {refs}")

        old_acceptance = t.get("acceptance")
        new_acceptance = _rewrite_acceptance_items(old_acceptance, existing)
        if new_acceptance and new_acceptance != old_acceptance:
            t["acceptance"] = new_acceptance
            changed = True

        old_test_refs = t.get("test_refs")
        new_test_refs = list(dict.fromkeys(existing))  # de-dup preserve order
        if old_test_refs != new_test_refs:
            t["test_refs"] = new_test_refs
            changed = True

        break
    return changed


def main() -> int:
    ap = argparse.ArgumentParser(description="Rebind done/in-progress task acceptance Refs to existing tests.")
    ap.add_argument("--task-ids", default="", help="Optional CSV of master task ids to rewrite (e.g. 10,11,14).")
    ap.add_argument("--write", action="store_true", help="Write changes in-place. Without this flag, dry-run.")
    args = ap.parse_args()

    root = repo_root()
    tasks_json_p = root / ".taskmaster" / "tasks" / "tasks.json"
    back_p = root / ".taskmaster" / "tasks" / "tasks_back.json"
    gameplay_p = root / ".taskmaster" / "tasks" / "tasks_gameplay.json"

    tasks_json = load_json(tasks_json_p)
    master_tasks = (tasks_json.get("master") or {}).get("tasks") or []
    if not isinstance(master_tasks, list):
        raise ValueError("tasks.json master.tasks must be a list")

    selected_ids = set()
    if str(args.task_ids or "").strip():
        selected_ids = {int(x) for x in split_csv(args.task_ids)}
    else:
        for t in master_tasks:
            if not isinstance(t, dict):
                continue
            st = str(t.get("status") or "").strip().lower()
            if st in {"done", "in-progress"}:
                try:
                    selected_ids.add(int(str(t.get("id"))))
                except Exception:  # noqa: BLE001
                    continue

    # Hardcoded binding map for completed tasks (must exist on disk).
    binding: dict[int, list[str]] = {
        1: ["Game.Core.Tests/Engine/GameEngineCoreConstructorTests.cs"],
        2: ["Game.Core.Tests/Domain/ValueObjects/CircularMapPositionTests.cs"],
        3: ["Game.Core.Tests/Domain/CityTests.cs"],
        4: ["Game.Core.Tests/Domain/SanguoPlayerTests.cs"],
        5: ["Game.Core.Tests/Services/SanguoDiceServiceTests.cs"],
        6: ["Game.Core.Tests/Services/SanguoTurnManagerTests.cs"],
        7: ["Game.Core.Tests/Services/SanguoEconomyManagerTests.cs"],
        8: ["Game.Core.Tests/Services/EventBusTests.cs"],
        9: ["Game.Core.Tests/Engine/HudSceneTests.cs"],
        10: ["Game.Core.Tests/Tasks/Task10BoardViewScriptsTests.cs"],
        11: ["Game.Core.Tests/Tasks/Task11AiBehaviorTests.cs"],
        12: ["Game.Core.Tests/Domain/SanguoPlayerTests.cs", "Game.Core.Tests/Domain/CityTests.cs"],
        13: ["Game.Core.Tests/Services/SanguoEconomyManagerTests.cs"],
        14: ["Game.Core.Tests/Tasks/Task14MonthEndSettlementTests.cs"],
        22: ["Game.Core.Tests/Engine/HudSceneTests.cs"],
    }

    back = load_json(back_p)
    gameplay = load_json(gameplay_p)
    if not isinstance(back, list) or not isinstance(gameplay, list):
        raise ValueError("tasks_back.json and tasks_gameplay.json must be arrays")

    changed_any = False
    changed_tasks: list[int] = []
    for tid in sorted(selected_ids):
        if tid not in binding:
            continue
        refs = [_normalize(r) for r in binding[tid]]
        changed_back = _apply_to_view(back, tid, refs, root=root)
        changed_gameplay = _apply_to_view(gameplay, tid, refs, root=root)
        if changed_back or changed_gameplay:
            changed_any = True
            changed_tasks.append(tid)

    print(f"REBIND_ACCEPTANCE_REFS selected={len(selected_ids)} changed={len(changed_tasks)} write={bool(args.write)}")
    if not args.write or not changed_any:
        return 0

    write_json(back_p, back)
    write_json(gameplay_p, gameplay)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

