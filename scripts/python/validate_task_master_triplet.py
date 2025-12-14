#!/usr/bin/env python3
"""
Validate consistency between the three Taskmaster task files:

- .taskmaster/tasks/tasks_back.json      (NG backbone, architecture/infra)
- .taskmaster/tasks/tasks_gameplay.json  (GM gameplay tasks)
- .taskmaster/tasks/tasks.json           (Taskmaster/MCP view)

Checks performed:
- ADR/Chapter/Overlay links for tasks_back/tasks_gameplay via check_tasks_all_refs.
- layer field is present and within the allowed set.
- depends_on only references existing task ids (across NG/GM).
- taskmaster_exported/taskmaster_id mapping is consistent with tasks.json.

Usage:
    py -3 scripts/python/validate_task_master_triplet.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Dict, List, Set, Tuple

import check_tasks_all_refs


ALLOWED_LAYERS: Set[str] = {"docs", "core", "adapter", "ci"}


def load_json_list(path: Path) -> List[dict]:
    """Load a JSON file that is expected to contain a list."""

    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, list):
        return data
    if isinstance(data, dict) and "tasks" in data:
        # tasks.json style container
        return data["tasks"]
    raise ValueError(f"Unexpected JSON structure in {path}")


def validate_layers(tasks: List[dict], label: str) -> Tuple[int, int]:
    """Validate layer field for the given tasks.

    Returns (total, passed).
    """

    total = 0
    passed = 0

    print(f"\n[Layer] Validating layer field for {label}")
    for t in tasks:
        tid = t.get("id")
        layer = t.get("layer")
        # Only consider tasks that declare a layer
        if layer is None:
            continue
        total += 1
        if layer not in ALLOWED_LAYERS:
            print(f"  - {label}:{tid}: invalid layer '{layer}' (allowed: {sorted(ALLOWED_LAYERS)})")
        else:
            passed += 1

    print(f"  Layer summary for {label}: {passed}/{total} tasks passed")
    return total, passed


def validate_depends_on(tasks_back: List[dict], tasks_gameplay: List[dict]) -> Tuple[int, int]:
    """Validate depends_on references across NG/GM tasks.

    Returns (total_references, valid_references).
    """

    all_tasks = tasks_back + tasks_gameplay
    id_index: Dict[str, dict] = {t.get("id"): t for t in all_tasks if t.get("id")}

    total_refs = 0
    valid_refs = 0

    print("\n[DependsOn] Validating depends_on references across tasks_back/tasks_gameplay")
    for t in all_tasks:
        tid = t.get("id")
        deps = t.get("depends_on") or []
        if not isinstance(deps, list):
            # If someone encoded a single string, normalise to list for reporting
            deps = [deps]

        for dep in deps:
            if not dep:
                continue
            total_refs += 1
            if dep == tid:
                print(f"  - {tid}: depends_on self-reference '{dep}'")
                continue
            if dep not in id_index:
                print(f"  - {tid}: depends_on unknown id '{dep}'")
                continue
            valid_refs += 1

    print(f"  DependsOn summary: {valid_refs}/{total_refs} references point to known, non-self ids")
    return total_refs, valid_refs


def detect_dep_cycles(tasks_back: List[dict], tasks_gameplay: List[dict]) -> List[List[str]]:
    """Detect simple cycles in depends_on graph across NG/GM tasks.

    Returns a list of cycles, each represented as a list of task ids.
    """

    all_tasks = tasks_back + tasks_gameplay
    graph: Dict[str, List[str]] = {}
    for t in all_tasks:
        tid = t.get("id")
        if not tid:
            continue
        deps = t.get("depends_on") or []
        if not isinstance(deps, list):
            deps = [deps]
        graph[tid] = [d for d in deps if isinstance(d, str)]

    visited: Dict[str, int] = {}  # 0=unvisited,1=visiting,2=done
    stack: List[str] = []
    cycles: List[List[str]] = []

    def dfs(node: str) -> None:
        state = visited.get(node, 0)
        if state == 1:
            # Found a cycle; slice stack
            if node in stack:
                idx = stack.index(node)
                cycles.append(stack[idx:] + [node])
            return
        if state == 2:
            return
        visited[node] = 1
        stack.append(node)
        for nei in graph.get(node, []):
            if nei in graph:  # only follow known tasks
                dfs(nei)
        stack.pop()
        visited[node] = 2

    for tid in graph.keys():
        if visited.get(tid, 0) == 0:
            dfs(tid)

    return cycles


def load_tasks_json(path: Path) -> List[dict]:
    """Load the master.tasks array from tasks.json."""

    data = json.loads(path.read_text(encoding="utf-8"))
    master = data.get("master", {})
    tasks = master.get("tasks", [])
    if not isinstance(tasks, list):
        raise ValueError("tasks.json: master.tasks is not a list")
    return tasks


def validate_taskmaster_mapping(
    tasks_back: List[dict],
    tasks_gameplay: List[dict],
    tasks_master: List[dict],
) -> Tuple[int, int]:
    """Validate that taskmaster_exported tasks in back/gameplay map to tasks.json entries.

    Returns (total_mapped, ok_mapped).
    """

    exported: Dict[int, dict] = {}
    for t in tasks_back + tasks_gameplay:
        if not t.get("taskmaster_exported"):
            continue
        tm_id = t.get("taskmaster_id")
        if tm_id is None:
            print(f"  - {t.get('id')}: taskmaster_exported is true but taskmaster_id is missing")
            continue
        if not isinstance(tm_id, int):
            print(f"  - {t.get('id')}: taskmaster_id should be int, got {type(tm_id)}")
            continue
        if tm_id in exported:
            other = exported[tm_id].get("id")
            print(f"  - taskmaster_id {tm_id} is used by multiple tasks: {other} and {t.get('id')}")
            continue
        exported[tm_id] = t

    id_to_master: Dict[str, dict] = {
        str(t.get("id")): t for t in tasks_master if isinstance(t, dict) and "id" in t
    }

    total = len(exported)
    ok = 0

    print("\n[Mapping] Validating mapping from tasks_back/tasks_gameplay to tasks.json (master)")
    for tm_id, src in sorted(exported.items(), key=lambda kv: kv[0]):
        tm_id_str = str(tm_id)
        src_id = src.get("id")
        m = id_to_master.get(tm_id_str)
        if not m:
            print(f"  - {src_id}: taskmaster_id={tm_id} not found in tasks.json master.tasks")
            continue
        # Optional: lightweight title consistency check
        src_title = src.get("title", "").strip()
        master_title = m.get("title", "").strip()
        if src_title and master_title and src_title != master_title:
            print(f"  - {src_id}: title mismatch between back/gameplay and tasks.json")
            print(f"       back/gameplay: {src_title}")
            print(f"       tasks.json   : {master_title}")
        ok += 1

    print(f"  Mapping summary: {ok}/{total} exported tasks have a master.tasks entry")
    return total, ok


def main() -> int:
    root = Path(__file__).resolve().parents[2]

    print("=== Taskmaster Triplet Validation ===")
    print(f"Project root: {root}")

    # 1) Reuse existing ADR/Chapter/Overlay checks (tasks_back + tasks_gameplay)
    print("\n[Links] Running ADR/Chapter/Overlay validation via check_tasks_all_refs")
    links_ok = check_tasks_all_refs.run_check_all(root)
    if not links_ok:
        print("LINK VALIDATION FAILED (see details above)")

    # 2) Load NG/GM tasks
    back_path = root / ".taskmaster" / "tasks" / "tasks_back.json"
    gm_path = root / ".taskmaster" / "tasks" / "tasks_gameplay.json"
    tasks_back = load_json_list(back_path)
    tasks_gameplay = load_json_list(gm_path)

    # 3) Layer checks
    _tb_total, _tb_passed = validate_layers(tasks_back, "tasks_back.json")
    _tg_total, _tg_passed = validate_layers(tasks_gameplay, "tasks_gameplay.json")

    # 4) depends_on checks
    _dep_total, _dep_valid = validate_depends_on(tasks_back, tasks_gameplay)
    dep_cycles = detect_dep_cycles(tasks_back, tasks_gameplay)
    if dep_cycles:
        print("\n[DependsOn] Detected dependency cycles:")
        for idx, cycle in enumerate(dep_cycles, start=1):
            print(f"  Cycle {idx}: {' -> '.join(cycle)}")
    else:
        print("\n[DependsOn] No dependency cycles detected")

    # 5) Mapping to tasks.json
    tasks_json_path = root / ".taskmaster" / "tasks" / "tasks.json"
    tasks_master = load_tasks_json(tasks_json_path)
    _map_total, _map_ok = validate_taskmaster_mapping(tasks_back, tasks_gameplay, tasks_master)

    # Exit code summary
    no_cycles = not dep_cycles
    ok = links_ok and _dep_total == _dep_valid and _map_total == _map_ok and no_cycles
    if not ok:
        print("\nOverall result: FAILED")
        return 1

    print("\nOverall result: OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
