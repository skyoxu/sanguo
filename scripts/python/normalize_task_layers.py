#!/usr/bin/env python3
"""
Normalize Taskmaster task `layer` values to the repo-allowed vocabulary.

Why:
- Deterministic gates (e.g. validate_task_master_triplet.py) treat `layer` as a hard rule.
- Historical/LLM-generated task views may contain legacy values like `ui`/`infra`/`scene`/`test`.

Allowed layers (SSoT for task views):
- docs
- core
- adapter
- ci

Legacy mapping policy (best-effort, deterministic):
- ui -> adapter
- scene -> adapter
- infra -> ci
- test -> inferred from refs:
    - any .gd / Tests.Godot / tests/Godot => adapter
    - otherwise => core

Usage:
  py -3 scripts/python/normalize_task_layers.py
  py -3 scripts/python/normalize_task_layers.py --write
  py -3 scripts/python/normalize_task_layers.py --task-file .taskmaster/tasks/tasks_back.json --write
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable


ALLOWED_LAYERS: set[str] = {"docs", "core", "adapter", "ci"}


@dataclass(frozen=True)
class Change:
    task_file: str
    task_id: str
    old_layer: str | None
    new_layer: str | None


def _load_json_list(path: Path) -> list[dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError(f"Expected a JSON list in {path}")
    return data


def _write_json_list(path: Path, tasks: list[dict[str, Any]]) -> None:
    path.write_text(json.dumps(tasks, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _iter_ref_strings(task: dict[str, Any]) -> Iterable[str]:
    for key in ("test_refs", "overlay_refs", "contract_refs", "acceptance"):
        value = task.get(key)
        if isinstance(value, list):
            for item in value:
                if isinstance(item, str):
                    yield item
        elif isinstance(value, str):
            yield value


def _infer_test_layer(task: dict[str, Any]) -> str:
    refs = " ".join(_iter_ref_strings(task)).lower()
    if ".gd" in refs or "tests.godot" in refs or "tests/godot" in refs or "tests\\godot" in refs:
        return "adapter"
    return "core"


def normalize_layer(task: dict[str, Any]) -> str | None:
    layer = task.get("layer")
    if layer is None:
        return None
    if not isinstance(layer, str):
        return layer

    if layer in ALLOWED_LAYERS:
        return layer

    legacy = layer.strip().lower()
    if legacy == "ui":
        return "adapter"
    if legacy == "scene":
        return "adapter"
    if legacy == "infra":
        return "ci"
    if legacy == "test":
        return _infer_test_layer(task)

    # Unknown legacy value: keep it so the validator can fail loudly.
    return layer


def run(task_files: list[Path], write: bool) -> list[Change]:
    changes: list[Change] = []

    for task_file in task_files:
        tasks = _load_json_list(task_file)

        file_changes: list[Change] = []
        for task in tasks:
            task_id = str(task.get("id", ""))
            old_layer = task.get("layer")
            new_layer = normalize_layer(task)
            if new_layer != old_layer:
                task["layer"] = new_layer
                file_changes.append(
                    Change(
                        task_file=task_file.as_posix(),
                        task_id=task_id,
                        old_layer=str(old_layer) if old_layer is not None else None,
                        new_layer=str(new_layer) if new_layer is not None else None,
                    )
                )

        if write and file_changes:
            _write_json_list(task_file, tasks)

        changes.extend(file_changes)

    return changes


def main() -> None:
    ap = argparse.ArgumentParser(description="Normalize task view layer values (deterministic).")
    ap.add_argument(
        "--task-file",
        action="append",
        default=[],
        help="Task view file to normalize (repeatable). Default: tasks_back.json + tasks_gameplay.json.",
    )
    ap.add_argument("--write", action="store_true", help="Write changes back to files.")
    args = ap.parse_args()

    root = Path(__file__).resolve().parents[2]
    default_files = [
        root / ".taskmaster" / "tasks" / "tasks_back.json",
        root / ".taskmaster" / "tasks" / "tasks_gameplay.json",
    ]

    task_files: list[Path] = []
    if args.task_file:
        for raw in args.task_file:
            task_files.append((root / raw).resolve() if not Path(raw).is_absolute() else Path(raw))
    else:
        task_files = default_files

    changes = run(task_files, write=bool(args.write))

    print(f"allowed_layers={sorted(ALLOWED_LAYERS)}")
    print(f"task_files={[p.as_posix() for p in task_files]}")
    print(f"write={'yes' if args.write else 'no'}")
    print(f"changes={len(changes)}")
    for ch in changes:
        print(f"- {ch.task_file}:{ch.task_id}: {ch.old_layer} -> {ch.new_layer}")

    if changes and not args.write:
        raise SystemExit(2)


if __name__ == "__main__":
    main()

