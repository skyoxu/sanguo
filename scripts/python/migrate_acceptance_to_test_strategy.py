#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Batch-migrate non-verifiable acceptance items into test_strategy (details-like),
and keep deterministic gates consistent by reindexing ACC:T<id>.<n> anchors.

Why:
  Some acceptance items are not suitable for deterministic proof, e.g.:
    - "xUnit 测试用例存在并通过" (CI fact, not a per-task semantic)
    - "参考 Godot 官方演示项目…只借鉴…不复制" (not reliably provable)
    - "…并在 UI 中有清晰可追踪的反馈" (often belongs to UI tasks, not Core tasks)

If we remove these lines from acceptance[], the expected anchor indices shift.
This script:
  1) Moves matching acceptance lines into test_strategy[]
  2) Removes/renumbers ACC anchors in referenced test files to avoid collisions
  3) Writes an audit log under logs/ci/<date>/migrate-acceptance/

Usage (Windows):
  py -3 scripts/python/migrate_acceptance_to_test_strategy.py --apply
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable


REFS_RE = re.compile(r"\bRefs\s*:\s*(.+)$", flags=re.IGNORECASE)
ACC_ANCHOR_RE = re.compile(r"\bACC:T(?P<task>\d+)\.(?P<idx>\d+)\b")


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")


def today_ymd() -> str:
    return dt.date.today().strftime("%Y-%m-%d")


def _split_refs_blob(blob: str) -> list[str]:
    normalized = str(blob or "").replace("`", " ").replace(",", " ").replace(";", " ")
    out: list[str] = []
    for token in normalized.split():
        p = token.strip().replace("\\", "/")
        if not p:
            continue
        out.append(p)
    return out


def parse_refs_from_line(line: str) -> list[str]:
    m = REFS_RE.search(str(line or "").strip())
    if not m:
        return []
    return _split_refs_blob(m.group(1) or "")


def ensure_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(x) for x in value if str(x).strip()]
    if isinstance(value, str):
        s = value.strip()
        return [s] if s else []
    return [str(value)]


def is_comment_line(line: str) -> bool:
    s = line.strip()
    return s.startswith("//") or s.startswith("#")


def remove_anchor_from_line(line: str, anchor: str) -> tuple[str, bool]:
    if anchor not in line:
        return line, False
    new_line = line.replace(anchor, "").rstrip()
    # If this becomes an empty comment line, drop it.
    stripped = new_line.strip()
    if stripped in ("//", "#", "") and is_comment_line(line):
        return "", True
    return new_line, True


@dataclass(frozen=True)
class MigrationRule:
    name: str
    needle: str


RULES: list[MigrationRule] = [
    MigrationRule(name="tests_exist_ci_fact", needle="对应任务的 xUnit 测试用例存在并通过"),
    MigrationRule(name="godot_demo_nonverifiable", needle="参考 Godot 官方演示项目"),
    MigrationRule(name="ui_feedback_cross_slice", needle="并在 UI 中有清晰可追踪的反馈"),
    MigrationRule(name="future_evolution_not_acceptance", needle="后续演进"),
]


def should_migrate(line: str) -> str | None:
    for r in RULES:
        if r.needle in line:
            return r.name
    return None


def build_index_map(old_len: int, removed_indices_1based: set[int]) -> dict[int, int]:
    mapping: dict[int, int] = {}
    new_idx = 0
    for old_idx in range(1, old_len + 1):
        if old_idx in removed_indices_1based:
            continue
        new_idx += 1
        mapping[old_idx] = new_idx
    return mapping


def gather_ref_files(lines: Iterable[str]) -> set[str]:
    out: set[str] = set()
    for line in lines:
        for r in parse_refs_from_line(line):
            out.add(r)
    return out


def rewrite_test_file_for_task(
    *,
    root: Path,
    rel_path: str,
    task_id: int,
    removed: set[int],
    mapping: dict[int, int],
) -> dict[str, Any]:
    p = root / rel_path
    if not p.exists():
        return {"file": rel_path, "status": "missing"}

    original = p.read_text(encoding="utf-8", errors="ignore").splitlines()
    changed = False
    removed_hits = 0
    renamed_hits = 0

    def rewrite_line(line: str) -> str:
        nonlocal changed, removed_hits, renamed_hits
        # Remove anchors for removed indices to avoid collisions.
        for old_idx in sorted(removed, reverse=True):
            anchor = f"ACC:T{task_id}.{old_idx}"
            line2, did = remove_anchor_from_line(line, anchor)
            if did:
                removed_hits += 1
                changed = True
                line = line2
                if line == "":
                    return ""

        # Renumber anchors for kept indices.
        # Use regex callback to avoid chained replacements.
        def repl(m: re.Match[str]) -> str:
            nonlocal changed, renamed_hits
            if int(m.group("task")) != task_id:
                return m.group(0)
            old_idx = int(m.group("idx"))
            if old_idx in mapping and mapping[old_idx] != old_idx:
                renamed_hits += 1
                changed = True
                return f"ACC:T{task_id}.{mapping[old_idx]}"
            return m.group(0)

        line3 = ACC_ANCHOR_RE.sub(repl, line)
        return line3

    rewritten: list[str] = []
    for line in original:
        new_line = rewrite_line(line)
        if new_line == "":
            continue
        rewritten.append(new_line)

    if not changed:
        return {"file": rel_path, "status": "ok", "changed": False, "removed": 0, "renamed": 0}

    p.write_text("\n".join(rewritten) + "\n", encoding="utf-8", newline="\n")
    return {"file": rel_path, "status": "ok", "changed": True, "removed": removed_hits, "renamed": renamed_hits}


def migrate_view(
    *,
    root: Path,
    view_path: Path,
    log: dict[str, Any],
    apply: bool,
) -> tuple[list[dict[str, Any]], set[tuple[int, str]]]:
    view = load_json(view_path)
    if not isinstance(view, list):
        raise ValueError(f"Expected JSON array: {view_path}")

    view_changes: list[dict[str, Any]] = []
    touched_test_files: set[tuple[int, str]] = set()  # (task_id, file)

    for t in view:
        if not isinstance(t, dict):
            continue
        task_id = t.get("taskmaster_id")
        if not isinstance(task_id, int):
            continue
        acceptance = t.get("acceptance") or []
        if not isinstance(acceptance, list) or not acceptance:
            continue

        removed_indices: list[int] = []
        moved_lines: list[dict[str, Any]] = []

        for idx, raw in enumerate(acceptance, start=1):
            line = str(raw or "").strip()
            if not line:
                continue
            rule = should_migrate(line)
            if rule is None:
                continue
            removed_indices.append(idx)
            moved_lines.append({"index": idx, "rule": rule, "text": line})

        if not removed_indices:
            continue

        removed_set = set(removed_indices)
        mapping = build_index_map(len(acceptance), removed_set)

        # Collect referenced test files for this task from original acceptance lines.
        ref_files = gather_ref_files(acceptance)
        for rf in ref_files:
            touched_test_files.add((task_id, rf))

        new_acceptance = [line for i, line in enumerate(acceptance, start=1) if i not in removed_set]
        test_strategy = ensure_list(t.get("test_strategy"))

        migrated_block: list[str] = []
        migrated_block.append("（从 acceptance 迁移：非确定性/跨切面/CI事实条款，不作为硬验收）")
        for item in moved_lines:
            migrated_block.append(f"- {item['text']}")

        new_test_strategy = test_strategy + migrated_block

        view_changes.append(
            {
                "task_id": task_id,
                "acceptance_before": len(acceptance),
                "acceptance_after": len(new_acceptance),
                "removed_indices": removed_indices,
                "anchor_mapping": {str(k): v for k, v in mapping.items()},
                "moved_count": len(moved_lines),
                "moved_rules": sorted({x["rule"] for x in moved_lines}),
            }
        )

        if apply:
            t["acceptance"] = new_acceptance
            t["test_strategy"] = new_test_strategy

    if apply and view_changes:
        view_path.write_text(json.dumps(view, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")

    log["views"][view_path.name] = {"changed_tasks": view_changes}
    return view_changes, touched_test_files


def main() -> int:
    ap = argparse.ArgumentParser(description="Migrate selected acceptance items to test_strategy and fix anchors.")
    ap.add_argument("--apply", action="store_true", help="Apply changes in-place (default: dry-run).")
    args = ap.parse_args()

    root = repo_root()
    back_path = root / ".taskmaster/tasks/tasks_back.json"
    gameplay_path = root / ".taskmaster/tasks/tasks_gameplay.json"

    out_dir = root / "logs/ci" / today_ymd() / "migrate-acceptance"
    log: dict[str, Any] = {
        "date": today_ymd(),
        "apply": bool(args.apply),
        "rules": [r.__dict__ for r in RULES],
        "views": {},
        "touched_test_files": [],
        "test_file_rewrites": [],
    }

    # 1) Migrate acceptance -> test_strategy
    back_changes, back_files = migrate_view(root=root, view_path=back_path, log=log, apply=args.apply)
    game_changes, game_files = migrate_view(root=root, view_path=gameplay_path, log=log, apply=args.apply)

    # 2) Build per-task mapping from either view (prefer back if present)
    mapping_by_task: dict[int, dict[str, Any]] = {}
    for change in (back_changes + game_changes):
        tid = int(change["task_id"])
        mapping_by_task[tid] = change

    # 3) Rewrite referenced test files to avoid anchor collisions and keep indices aligned.
    touched = set(back_files) | set(game_files)
    for tid, rel in sorted(touched, key=lambda x: (x[0], x[1])):
        if tid not in mapping_by_task:
            continue
        removed = set(mapping_by_task[tid]["removed_indices"])
        mapping = {int(k): int(v) for k, v in mapping_by_task[tid]["anchor_mapping"].items()}
        result = rewrite_test_file_for_task(root=root, rel_path=rel, task_id=tid, removed=removed, mapping=mapping)
        if result.get("changed"):
            log["test_file_rewrites"].append(result)

    log["touched_test_files"] = [{"task_id": tid, "file": rel} for tid, rel in sorted(touched)]

    write_json(out_dir / "summary.json", log)
    print(f"MIGRATE_ACCEPTANCE status=ok apply={args.apply} out={out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
