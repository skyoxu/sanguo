#!/usr/bin/env python
"""Sync Taskmaster view files from the master tasks.json (SSoT).

Repo rules (AGENTS.md):
- Windows-first; write UTF-8.
- Output audit artifacts to logs/ci/<YYYY-MM-DD>/.

This script:
1) Syncs status fields in view files to match `.taskmaster/tasks/tasks.json`.
2) Optionally enriches view-only `contractRefs` based on simple heuristics and known event contracts.

It intentionally does NOT rewrite titles/descriptions/etc. to avoid noisy diffs.
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Set, Tuple


REPO_DEFAULT_MASTER = Path(".taskmaster/tasks/tasks.json")
REPO_DEFAULT_BACK = Path(".taskmaster/tasks/tasks_back.json")
REPO_DEFAULT_GAMEPLAY = Path(".taskmaster/tasks/tasks_gameplay.json")
CONTRACTS_ROOT = Path("Game.Core/Contracts")


_EVENT_TYPE_RE = re.compile(r'\bEventType\s*=\s*"([^"]+)"')


@dataclass(frozen=True)
class SyncChange:
    taskmaster_id: int
    field: str
    before: Any
    after: Any


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, obj: Any) -> None:
    path.write_text(
        json.dumps(obj, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def load_master_status_map(master_path: Path) -> Dict[str, str]:
    doc = read_json(master_path)
    tasks = doc.get("master", {}).get("tasks", [])
    out: Dict[str, str] = {}
    for t in tasks:
        if not isinstance(t, dict):
            continue
        tid = t.get("id")
        status = t.get("status")
        if isinstance(tid, str) and isinstance(status, str):
            out[tid] = status
    return out


def extract_known_event_types(contracts_root: Path) -> Set[str]:
    known: Set[str] = set()
    if not contracts_root.exists():
        return known
    for cs in contracts_root.rglob("*.cs"):
        text = cs.read_text(encoding="utf-8")
        for m in _EVENT_TYPE_RE.findall(text):
            known.add(m)
    return known


def normalize_contract_refs(value: Any) -> List[str] | None:
    if value is None:
        return None
    if not isinstance(value, list):
        return None
    out: List[str] = []
    for x in value:
        if isinstance(x, str) and x.strip():
            out.append(x.strip())
    return out


def should_include_player_eliminated(task: Dict[str, Any]) -> bool:
    blob = "\n".join(
        str(x)
        for x in [
            task.get("title", ""),
            task.get("description", ""),
            task.get("test_strategy", ""),
            task.get("test_strategy", ""),
            task.get("acceptance", ""),
        ]
    )
    # Chinese + English keywords; keep narrow to avoid noisy changes.
    keywords = ["出局", "破产", "bankrupt", "eliminat"]
    return any(k in blob for k in keywords)


def should_include_city_toll_paid(task: Dict[str, Any]) -> bool:
    blob = "\n".join(
        str(x)
        for x in [
            task.get("title", ""),
            task.get("description", ""),
            task.get("acceptance", ""),
        ]
    )
    keywords = ["过路费", "toll"]
    return any(k in blob for k in keywords)


def sync_view_file(
    view_path: Path,
    master_status_by_id: Dict[str, str],
    known_event_types: Set[str],
    *,
    add_contractrefs: bool,
) -> Tuple[List[SyncChange], List[str]]:
    view = read_json(view_path)
    if not isinstance(view, list):
        raise ValueError(f"Expected JSON array at {view_path.as_posix()}")

    changes: List[SyncChange] = []
    warnings: List[str] = []

    for entry in view:
        if not isinstance(entry, dict):
            continue

        taskmaster_id = entry.get("taskmaster_id")
        if not isinstance(taskmaster_id, int):
            continue

        master_key = str(taskmaster_id)
        master_status = master_status_by_id.get(master_key)
        if isinstance(master_status, str):
            before = entry.get("status")
            if before != master_status:
                entry["status"] = master_status
                changes.append(SyncChange(taskmaster_id, "status", before, master_status))
        else:
            warnings.append(f"taskmaster_id={taskmaster_id} missing in master; view={view_path.as_posix()}")

        if not add_contractrefs:
            continue

        refs = normalize_contract_refs(entry.get("contractRefs")) or []
        ref_set = set(refs)

        if should_include_player_eliminated(entry) and "core.sanguo.player.eliminated" in known_event_types:
            if "core.sanguo.player.eliminated" not in ref_set:
                refs.append("core.sanguo.player.eliminated")
                changes.append(
                    SyncChange(taskmaster_id, "contractRefs+=", None, "core.sanguo.player.eliminated")
                )

        if should_include_city_toll_paid(entry) and "core.sanguo.city.toll.paid" in known_event_types:
            if "core.sanguo.city.toll.paid" not in ref_set:
                refs.append("core.sanguo.city.toll.paid")
                changes.append(
                    SyncChange(taskmaster_id, "contractRefs+=", None, "core.sanguo.city.toll.paid")
                )

        if "contractRefs" in entry:
            entry["contractRefs"] = refs

    write_json(view_path, view)
    return changes, warnings


def scan_replacement_chars(paths: Iterable[Path]) -> Dict[str, int]:
    out: Dict[str, int] = {}
    for p in paths:
        text = p.read_text(encoding="utf-8")
        out[p.as_posix()] = text.count("\ufffd")
    return out


def write_report(root: Path, report: Dict[str, Any]) -> Path:
    date_str = datetime.now().strftime("%Y-%m-%d")
    out_dir = root / "logs" / "ci" / date_str
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "task-view-sync.json"
    out_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return out_path


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Sync Taskmaster view files (tasks_back/tasks_gameplay) from master tasks.json.")
    parser.add_argument("--master", default=str(REPO_DEFAULT_MASTER))
    parser.add_argument("--back", default=str(REPO_DEFAULT_BACK))
    parser.add_argument("--gameplay", default=str(REPO_DEFAULT_GAMEPLAY))
    parser.add_argument("--no-contractrefs", action="store_true", help="Do not adjust view-only contractRefs.")
    args = parser.parse_args(argv)

    root = Path(".").resolve()
    master_path = Path(args.master)
    back_path = Path(args.back)
    gameplay_path = Path(args.gameplay)

    master_status_by_id = load_master_status_map(master_path)
    known_event_types = extract_known_event_types(CONTRACTS_ROOT)

    changes_back, warnings_back = sync_view_file(
        back_path,
        master_status_by_id,
        known_event_types,
        add_contractrefs=not args.no_contractrefs,
    )
    changes_gameplay, warnings_gameplay = sync_view_file(
        gameplay_path,
        master_status_by_id,
        known_event_types,
        add_contractrefs=not args.no_contractrefs,
    )

    replacement_counts = scan_replacement_chars([master_path, back_path, gameplay_path])

    report = {
        "master": master_path.as_posix(),
        "views": {
            "back": back_path.as_posix(),
            "gameplay": gameplay_path.as_posix(),
        },
        "status_sync": {
            "master_tasks_count": len(master_status_by_id),
            "known_event_types": sorted(known_event_types),
        },
        "changes": {
            "back": [c.__dict__ for c in changes_back],
            "gameplay": [c.__dict__ for c in changes_gameplay],
        },
        "warnings": warnings_back + warnings_gameplay,
        "replacement_char_counts": replacement_counts,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
    }

    out_path = write_report(root, report)
    print(f"Task view sync report written to: {out_path}")

    # Hard fail if any file contains replacement characters: this is semantic mojibake.
    bad = {k: v for k, v in replacement_counts.items() if v > 0}
    if bad:
        print("Detected UTF-8 replacement characters (\\ufffd) in task files; please fix source content:")
        for k, v in bad.items():
            print(f"- {k}: {v}")
        return 2

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

