#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Rebind acceptance "Refs:" for a small set of tasks to better, existing test files.

Why:
  Some tasks currently point UI/Godot acceptance items to C# "static string" tests,
  which weakens semantic coverage and violates the intent of docs/testing-framework.md.

This script:
  - Rewrites acceptance items in BOTH tasks_back.json and tasks_gameplay.json for the given task ids.
  - Does NOT generate tests.
  - Optionally syncs test_refs from acceptance refs via update_task_test_refs_from_acceptance_refs.py.

Windows:
  py -3 scripts/python/rebind_task_refs_manual.py --task-ids 9,10,22 --write --sync-test-refs
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path
from typing import Any


REFS_RE = re.compile(r"\bRefs\s*:\s*(.+)$", flags=re.IGNORECASE)


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")


def split_csv(s: str) -> list[int]:
    out: list[int] = []
    for raw in str(s or "").split(","):
        v = raw.strip()
        if not v:
            continue
        if not v.isdigit():
            raise ValueError(f"invalid task id: {v}")
        out.append(int(v))
    return out


def find_task(view: list[dict[str, Any]], tid: int) -> dict[str, Any] | None:
    for t in view:
        if not isinstance(t, dict):
            continue
        if t.get("taskmaster_id") == tid:
            return t
    return None


def set_acceptance_refs(entry: dict[str, Any], mapping: dict[int, list[str]]) -> int:
    acceptance = entry.get("acceptance")
    if not isinstance(acceptance, list):
        return 0
    updated = 0
    new_items: list[str] = []
    for idx, raw in enumerate(acceptance):
        text = str(raw or "").strip()
        if idx not in mapping:
            new_items.append(text)
            continue
        # strip existing refs suffix if present
        m = REFS_RE.search(text)
        if m:
            text = text[: m.start()].rstrip()
        paths = mapping[idx]
        new_items.append(text + " Refs: " + " ".join(paths))
        updated += 1
    entry["acceptance"] = new_items
    return updated


def run_cmd(cmd: list[str], *, cwd: Path, timeout_sec: int) -> tuple[int, str]:
    proc = subprocess.run(
        cmd,
        cwd=str(cwd),
        text=True,
        encoding="utf-8",
        errors="ignore",
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=timeout_sec,
    )
    return int(proc.returncode or 0), str(proc.stdout or "")


def main() -> int:
    ap = argparse.ArgumentParser(description="Rebind acceptance refs for specific task ids.")
    ap.add_argument("--task-ids", required=True, help="Comma-separated task ids (e.g. 9,10,22).")
    ap.add_argument("--write", action="store_true", help="Write changes to task views in-place.")
    ap.add_argument("--sync-test-refs", action="store_true", help="Sync test_refs from acceptance refs (replace).")
    args = ap.parse_args()

    root = repo_root()
    back_path = root / ".taskmaster" / "tasks" / "tasks_back.json"
    gameplay_path = root / ".taskmaster" / "tasks" / "tasks_gameplay.json"

    back = load_json(back_path)
    gameplay = load_json(gameplay_path)
    if not isinstance(back, list) or not isinstance(gameplay, list):
        raise ValueError("tasks_back.json and tasks_gameplay.json must be JSON arrays")

    tasks = split_csv(args.task_ids)

    # Hand-curated rebinding for known UI/Godot tasks.
    # NOTE: All file paths must exist in repo (deterministic policy for done tasks).
    per_task: dict[int, dict[int, list[str]]] = {
        9: {
            0: ["Tests.Godot/tests/UI/test_hud_scene.gd"],
            1: ["Tests.Godot/tests/UI/test_hud_updates_on_events.gd"],
            2: ["Tests.Godot/tests/UI/test_hud_scene.gd"],
            3: ["Game.Core.Tests/Domain/SanguoPlayerViewTests.cs"],
        },
        10: {
            0: ["Tests.Godot/tests/Scenes/Sanguo/test_sanguo_board_view_token_move.gd"],
            1: ["Tests.Godot/tests/Scenes/Sanguo/test_sanguo_board_view_token_move.gd"],
            2: ["Tests.Godot/tests/Scenes/Sanguo/test_sanguo_board_view_token_move.gd"],
            3: ["Tests.Godot/tests/Scenes/Sanguo/test_sanguo_board_view_token_move.gd"],
        },
        22: {
            0: ["Tests.Godot/tests/UI/test_hud_scene.gd"],
            1: ["Tests.Godot/tests/UI/test_hud_updates_on_events.gd"],
            2: ["Tests.Godot/tests/UI/test_hud_scene.gd"],
        },
        11: {
            0: ["Game.Core.Tests/Services/SanguoAiBehaviorTests.cs"],
            1: ["Game.Core.Tests/Services/SanguoAiBehaviorTests.cs"],
            2: ["Game.Core.Tests/Services/SanguoAiBehaviorTests.cs"],
            3: ["Game.Core.Tests/Domain/SanguoPlayerViewTests.cs"],
        },
    }

    # Sanity check referenced files exist.
    for tid in tasks:
        mapping = per_task.get(tid)
        if not mapping:
            continue
        for paths in mapping.values():
            for p in paths:
                disk = root / p
                if not disk.exists():
                    raise FileNotFoundError(f"referenced test file does not exist: {p} (task {tid})")

    updated_total = 0
    for tid in tasks:
        mapping = per_task.get(tid)
        if not mapping:
            continue
        for view_name, view in [("back", back), ("gameplay", gameplay)]:
            entry = find_task(view, tid)
            if not entry:
                continue
            updated = set_acceptance_refs(entry, mapping)
            updated_total += updated
            print(f"REBIND task_id={tid} view={view_name} updated={updated}")

    if not args.write:
        print(f"REBIND status=dry_run updated_total={updated_total}")
        return 0

    write_json(back_path, back)
    write_json(gameplay_path, gameplay)
    print(f"REBIND status=ok wrote=tasks_back.json,tasks_gameplay.json updated_total={updated_total}")

    if not args.sync_test_refs:
        return 0

    for tid in tasks:
        if tid not in per_task:
            continue
        cmd = [
            "py",
            "-3",
            "scripts/python/update_task_test_refs_from_acceptance_refs.py",
            "--task-id",
            str(tid),
            "--mode",
            "replace",
            "--write",
        ]
        rc, out = run_cmd(cmd, cwd=root, timeout_sec=60)
        print(out.strip())
        if rc != 0:
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
