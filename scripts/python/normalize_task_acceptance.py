#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any


REFS_RE = re.compile(r"\bRefs\s*:\s*(.+)$", flags=re.IGNORECASE)
ABSOLUTE_PATH_PATTERN = re.compile(r"(?i)(?:^|\s)([a-z]:\\|\\\\)")


@dataclass(frozen=True)
class MovedItem:
    taskmaster_id: int | None
    source_file: str
    original_index: int
    reason: str
    text: str


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")


def _ensure_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [x for x in value if isinstance(x, str)]
    if isinstance(value, str):
        return [value]
    return []


def _is_demo_or_absolute_path_acceptance(text: str) -> bool:
    stripped = text.strip()
    if stripped.lower().startswith("local demo references:"):
        return True
    return ABSOLUTE_PATH_PATTERN.search(stripped) is not None


def _is_optional_hardening(text: str) -> bool:
    stripped = text.strip()
    return "可选加固" in stripped


def _has_refs(text: str) -> bool:
    return REFS_RE.search(str(text or "")) is not None


def _append_to_test_strategy(task: dict[str, Any], moved_texts: list[str]) -> None:
    test_strategy = task.get("test_strategy")
    if not isinstance(test_strategy, list):
        test_strategy = _ensure_list(test_strategy)
    if moved_texts:
        test_strategy.append("---")
        test_strategy.extend(moved_texts)
    task["test_strategy"] = test_strategy


def normalize_file(
    *,
    path: Path,
    write: bool,
    out_dir: Path,
    dry_run_max_examples: int,
) -> dict[str, Any]:
    data = _read_json(path)
    if not isinstance(data, list):
        raise ValueError(f"Expected top-level JSON array in {path}, got {type(data).__name__}")

    moved: list[MovedItem] = []
    changed_tasks = 0
    empty_acceptance_tasks: list[int] = []

    for task in data:
        if not isinstance(task, dict):
            continue
        acceptance = task.get("acceptance")
        if not isinstance(acceptance, list):
            continue

        keep: list[Any] = []
        moved_texts: list[str] = []
        tid = task.get("taskmaster_id")

        for idx, item in enumerate(acceptance):
            if not isinstance(item, str):
                keep.append(item)
                continue

            reason = None
            if _is_demo_or_absolute_path_acceptance(item):
                reason = "demo_or_absolute_path"
            elif _is_optional_hardening(item):
                reason = "optional_hardening"
            elif not _has_refs(item):
                reason = "missing_refs"

            if reason:
                moved.append(
                    MovedItem(
                        taskmaster_id=tid if isinstance(tid, int) else None,
                        source_file=str(path.as_posix()),
                        original_index=idx,
                        reason=reason,
                        text=item,
                    )
                )
                moved_texts.append(f"[MIGRATED_FROM_ACCEPTANCE:{reason}] {item}")
            else:
                keep.append(item)

        if moved_texts:
            task["acceptance"] = keep
            _append_to_test_strategy(task, moved_texts)
            changed_tasks += 1

        if isinstance(tid, int):
            acc_now = task.get("acceptance")
            if isinstance(acc_now, list) and len(acc_now) == 0:
                empty_acceptance_tasks.append(tid)

    if write:
        out_dir.mkdir(parents=True, exist_ok=True)
        backup_path = out_dir / f"{path.name}.bak"
        backup_path.write_text(Path(path).read_text(encoding="utf-8"), encoding="utf-8")
        _write_json(path, data)

    examples_path = None
    if moved and dry_run_max_examples > 0:
        examples = moved[:dry_run_max_examples]
        examples_path = out_dir / f"{path.stem}--examples.txt"
        lines = []
        for m in examples:
            tid_val = m.taskmaster_id if m.taskmaster_id is not None else "unknown"
            lines.append(f"Task {tid_val} idx {m.original_index} reason={m.reason}: {m.text.strip()}")
        out_dir.mkdir(parents=True, exist_ok=True)
        examples_path.write_text("\n\n".join(lines) + "\n", encoding="utf-8")

    return {
        "file": str(path.as_posix()),
        "write": bool(write),
        "moved_items": len(moved),
        "changed_tasks": changed_tasks,
        "empty_acceptance_tasks": sorted(empty_acceptance_tasks),
        "examples_path": str(examples_path.as_posix()) if examples_path else None,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Normalize task acceptance[] to keep only hard-gatable items (Refs present; no demo/abs path; no optional hardening)."
    )
    parser.add_argument("--tasks-back", default=".taskmaster/tasks/tasks_back.json")
    parser.add_argument("--tasks-gameplay", default=".taskmaster/tasks/tasks_gameplay.json")
    parser.add_argument("--write", action="store_true", help="Apply changes in-place (writes backups to logs/).")
    parser.add_argument(
        "--out-dir",
        default="",
        help="Output directory for logs/backups (default logs/ci/<date>/normalize-task-acceptance).",
    )
    parser.add_argument(
        "--dry-run-max-examples",
        type=int,
        default=40,
        help="Write up to N examples per file to <out-dir> (0 disables).",
    )
    args = parser.parse_args()

    today = dt.date.today().strftime("%Y-%m-%d")
    out_dir = Path(args.out_dir) if args.out_dir else Path("logs/ci") / today / "normalize-task-acceptance"

    results: list[dict[str, Any]] = []
    results.append(
        normalize_file(
            path=Path(args.tasks_back),
            write=bool(args.write),
            out_dir=out_dir,
            dry_run_max_examples=args.dry_run_max_examples,
        )
    )
    results.append(
        normalize_file(
            path=Path(args.tasks_gameplay),
            write=bool(args.write),
            out_dir=out_dir,
            dry_run_max_examples=args.dry_run_max_examples,
        )
    )

    summary = {
        "write": bool(args.write),
        "out_dir": str(out_dir.as_posix()),
        "results": results,
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

