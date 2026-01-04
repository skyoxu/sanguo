#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path
from typing import Any


UNWANTED_REFS = {
    "Game.Core.Tests/Services/SanguoEconomyManagerTests.cs",
    "Tests.Godot/tests/Security/Hard/test_settings_config_security.gd",
}


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")


def normalize_path(p: str) -> str:
    return str(p or "").strip().replace("\\", "/")


def split_refs_from_acceptance(text: str) -> tuple[str, list[str]]:
    s = str(text or "")
    marker = "Refs:"
    idx = s.lower().rfind(marker.lower())
    if idx < 0:
        return s.strip(), []
    prefix = s[:idx].rstrip()
    blob = s[idx + len(marker) :].strip().replace("`", " ").replace(",", " ").replace(";", " ")
    refs = [normalize_path(x) for x in blob.split() if normalize_path(x)]
    return prefix, refs


def format_acceptance(prefix: str, refs: list[str]) -> str:
    if not refs:
        return prefix.rstrip()
    return f"{prefix.rstrip()} Refs: {' '.join(refs)}"


def process_file(path: Path, task_ids: set[int], *, write: bool, out_dir: Path) -> dict[str, Any]:
    data = load_json(path)
    if not isinstance(data, list):
        raise SystemExit(f"Expected JSON array: {path}")

    if write:
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / f"{path.name}.bak").write_text(path.read_text(encoding="utf-8"), encoding="utf-8")

    changed: dict[int, Any] = {}

    for task in data:
        if not isinstance(task, dict):
            continue
        tid = task.get("taskmaster_id")
        if not isinstance(tid, int) or tid not in task_ids:
            continue

        acceptance = task.get("acceptance")
        if not isinstance(acceptance, list):
            continue

        acc_changes: list[dict[str, Any]] = []
        for i, raw in enumerate(list(acceptance)):
            if not isinstance(raw, str):
                continue
            prefix, refs = split_refs_from_acceptance(raw)
            before = list(refs)
            refs = [r for r in refs if normalize_path(r) not in UNWANTED_REFS]
            if refs != before:
                acceptance[i] = format_acceptance(prefix, refs)
                acc_changes.append({"index": i, "before_refs": before, "after_refs": refs})

        # Remove unwanted refs from test_refs as well.
        test_refs = task.get("test_refs")
        if isinstance(test_refs, list):
            before = [normalize_path(x) for x in test_refs if normalize_path(x)]
            after = [x for x in before if x not in UNWANTED_REFS]
            if after != before:
                task["test_refs"] = after
        else:
            before = None
            after = None

        if acc_changes or (before is not None and after is not None and before != after):
            changed[tid] = {"acceptance_changes": acc_changes, "test_refs_before": before, "test_refs_after": after}

    if write:
        write_json(path, data)

    return {"file": str(path.as_posix()), "changed_task_ids": sorted(changed.keys()), "details": changed}


def main() -> int:
    ap = argparse.ArgumentParser(description="Revert previously auto-added acceptance Refs (type mismatch fix) for specified tasks.")
    ap.add_argument("--tasks-back", default=".taskmaster/tasks/tasks_back.json")
    ap.add_argument("--tasks-gameplay", default=".taskmaster/tasks/tasks_gameplay.json")
    ap.add_argument("--task-ids", required=True, help="Comma-separated taskmaster_id list (e.g. 19,24,47,48).")
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--out-dir", default="", help="Output directory for backups/reports (default logs/ci/<date>/revert-acceptance-ref-type-mismatches).")
    args = ap.parse_args()

    root = repo_root()
    today = dt.date.today().strftime("%Y-%m-%d")
    out_dir = Path(args.out_dir) if args.out_dir else root / "logs" / "ci" / today / "revert-acceptance-ref-type-mismatches"
    out_dir.mkdir(parents=True, exist_ok=True)

    task_ids: set[int] = set()
    for part in args.task_ids.split(","):
        part = part.strip()
        if not part:
            continue
        task_ids.add(int(part))

    res_back = process_file(root / args.tasks_back, task_ids, write=bool(args.write), out_dir=out_dir)
    res_game = process_file(root / args.tasks_gameplay, task_ids, write=bool(args.write), out_dir=out_dir)
    summary = {"write": bool(args.write), "task_ids": sorted(task_ids), "results": [res_back, res_game]}
    write_json(out_dir / "summary.json", summary)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

