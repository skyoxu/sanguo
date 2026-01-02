#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Fill missing "Refs:" for every acceptance item in tasks_back.json/tasks_gameplay.json.

This is a metadata hygiene tool to make acceptance criteria traceable to repo evidence.

Rules:
  - If an acceptance item already contains "Refs:", it is left unchanged.
  - Otherwise append: " Refs: <path>"
  - Refs are repo-relative paths.
  - Task-level test_refs is updated to include referenced paths.
  - Invalid existing test_refs entries (non-test artifacts) are moved into description
    under "Evidence Artifacts (not test_refs)" and removed from test_refs.

This script does NOT create test files. It only prepares deterministic mapping targets.

Windows:
  py -3 scripts/python/fill_acceptance_refs_from_prd.py
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from pathlib import Path
from typing import Any


REFS_RE = re.compile(r"\bRefs\s*:\s*(.+)$", flags=re.IGNORECASE)


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def load_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def is_abs_path(p: str) -> bool:
    s = (p or "").strip()
    if not s:
        return False
    if s.startswith(("/", "\\")):
        return True
    if len(s) >= 2 and s[1] == ":":
        return True
    return False


def is_allowed_test_ref(p: str) -> bool:
    s = (p or "").strip().replace("\\", "/")
    if is_abs_path(s):
        return False
    if not (s.endswith(".cs") or s.endswith(".gd")):
        return False
    allowed_prefixes = (
        "Game.Core.Tests/",
        "Tests.Godot/tests/",
        "Tests/",
    )
    return s.startswith(allowed_prefixes)


GD_KEYWORDS = (
    "gdunit",
    "headless",
    ".tscn",
    "hud",
    "boardview",
    "sanguoboardview",
    "signal",
    "tween",
    "animation",
    "control",
)


def should_use_gd_ref(*texts: str) -> bool:
    blob = " ".join([str(t or "") for t in texts]).lower()
    return any(k in blob for k in GD_KEYWORDS)


def default_cs_ref(task_id: int) -> str:
    return f"Game.Core.Tests/Tasks/Task{task_id}AcceptanceTests.cs"


def default_gd_ref(task_id: int) -> str:
    return f"Tests.Godot/tests/Scenes/Sanguo/test_task{task_id}_acceptance.gd"


def append_description_artifacts(description: str, artifacts: list[str]) -> str:
    artifacts = [a.strip() for a in artifacts if str(a).strip()]
    if not artifacts:
        return description
    desc = str(description or "").rstrip()
    marker = "Evidence Artifacts (not test_refs)"
    if marker in desc:
        return desc
    lines = [desc, "", f"{marker}:"]
    for a in artifacts:
        lines.append(f"- {a}")
    return "\n".join([l for l in lines if l is not None]).rstrip()


def fill_for_view(
    *,
    root: Path,
    view_path: Path,
    prd_text: str,
    rewrite_existing: bool,
    rebuild_test_refs: bool,
) -> dict[str, Any]:
    view = load_json(view_path)
    if not isinstance(view, list):
        raise ValueError(f"Expected list in {view_path}")

    changed_tasks = 0
    changed_acceptance_items = 0
    moved_invalid_test_refs = 0

    for entry in view:
        if not isinstance(entry, dict):
            continue
        task_id = entry.get("taskmaster_id")
        if not isinstance(task_id, int):
            continue

        layer = str(entry.get("layer") or "").strip().lower()
        title = str(entry.get("title") or "")
        description = str(entry.get("description") or "")
        test_strategy = entry.get("test_strategy") or []
        test_strategy_blob = " ".join([str(x) for x in test_strategy]) if isinstance(test_strategy, list) else str(test_strategy)

        cs_ref = default_cs_ref(task_id)
        gd_ref = default_gd_ref(task_id)

        prefer_gd = layer == "ui"

        # Normalize and sanitize test_refs
        test_refs = entry.get("test_refs")
        if not isinstance(test_refs, list):
            test_refs = []

        norm_refs = [str(x).strip().replace("\\", "/") for x in test_refs if str(x).strip()]
        invalid_refs = [r for r in norm_refs if not is_allowed_test_ref(r)]
        kept_refs = [r for r in norm_refs if is_allowed_test_ref(r)]

        if invalid_refs:
            entry["description"] = append_description_artifacts(description, invalid_refs)
            moved_invalid_test_refs += len(invalid_refs)

        entry["test_refs"] = kept_refs

        acceptance = entry.get("acceptance") or []
        if not isinstance(acceptance, list):
            continue

        updated = False
        new_acceptance: list[str] = []
        used_refs: list[str] = []
        for a in acceptance:
            s = str(a or "").strip()
            if not s:
                new_acceptance.append(s)
                continue

            if REFS_RE.search(s):
                if not rewrite_existing:
                    new_acceptance.append(s)
                    # Track existing refs so task-level test_refs can stay consistent if requested.
                    m = REFS_RE.search(s)
                    if m:
                        for rr in m.group(1).replace("`", "").replace(",", " ").replace(";", " ").split():
                            used_refs.append(rr.strip().replace("\\", "/"))
                    continue
                # Rewrite mode: strip the suffix and recompute.
                s = REFS_RE.sub("", s).rstrip()

            use_gd = prefer_gd or should_use_gd_ref(s)
            r = gd_ref if use_gd else cs_ref
            new_acceptance.append(f"{s} Refs: {r}")
            changed_acceptance_items += 1
            updated = True
            used_refs.append(r)

        # Rebuild / update task-level test_refs based on the refs actually used by acceptance items.
        if rebuild_test_refs:
            uniq: list[str] = []
            seen = set()
            for rr in used_refs:
                rr = str(rr).strip().replace("\\", "/")
                if not rr:
                    continue
                if rr in seen:
                    continue
                seen.add(rr)
                uniq.append(rr)
            entry["test_refs"] = [rr for rr in uniq if is_allowed_test_ref(rr)]
        else:
            for rr in used_refs:
                rr = str(rr).strip().replace("\\", "/")
                if not rr:
                    continue
                if rr not in entry["test_refs"] and is_allowed_test_ref(rr):
                    entry["test_refs"].append(rr)

        # Ensure at least one test_refs exists for the task.
        if not entry["test_refs"]:
            entry["test_refs"].append(gd_ref if prefer_gd else cs_ref)

        if updated:
            entry["acceptance"] = new_acceptance
            changed_tasks += 1

        # Note: moved invalid test_refs does not necessarily imply acceptance changed.

    save_json(view_path, view)
    return {
        "file": str(view_path.relative_to(root)).replace("\\", "/"),
        "changed_tasks": changed_tasks,
        "changed_acceptance_items": changed_acceptance_items,
        "moved_invalid_test_refs": moved_invalid_test_refs,
        "tasks_total": len(view),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Fill acceptance Refs: in tasks_back/tasks_gameplay using PRD context.")
    ap.add_argument("--prd", default="prd.txt", help="PRD file path (utf-8). Default: prd.txt")
    ap.add_argument("--prd-yuan", default="prd_yuan.md", help="Optional secondary PRD file path (utf-8). Default: prd_yuan.md")
    ap.add_argument(
        "--tasks-dir",
        default=".taskmaster/tasks",
        help="Taskmaster tasks dir. Default: .taskmaster/tasks",
    )
    ap.add_argument("--rewrite-existing", action="store_true", help="Rewrite existing acceptance Refs: based on heuristics.")
    ap.add_argument(
        "--rebuild-test-refs",
        action="store_true",
        help="Rebuild test_refs from acceptance-used Refs (recommended with --rewrite-existing).",
    )
    ap.add_argument("--write-logs", action="store_true", help="Write a summary JSON under logs/ci/<date>/fill-acceptance-refs/")
    args = ap.parse_args()

    root = repo_root()
    prd_path = root / args.prd
    prd_yuan_path = root / args.prd_yuan
    prd_text = (load_text(prd_path) + "\n" + load_text(prd_yuan_path)).strip()

    tasks_dir = root / args.tasks_dir
    back_path = tasks_dir / "tasks_back.json"
    gameplay_path = tasks_dir / "tasks_gameplay.json"

    back_summary = fill_for_view(
        root=root,
        view_path=back_path,
        prd_text=prd_text,
        rewrite_existing=bool(args.rewrite_existing),
        rebuild_test_refs=bool(args.rebuild_test_refs),
    )
    gameplay_summary = fill_for_view(
        root=root,
        view_path=gameplay_path,
        prd_text=prd_text,
        rewrite_existing=bool(args.rewrite_existing),
        rebuild_test_refs=bool(args.rebuild_test_refs),
    )

    summary = {
        "date": dt.date.today().strftime("%Y-%m-%d"),
        "prd_used": [str((root / args.prd).name), str((root / args.prd_yuan).name)],
        "prd_found": {"prd": prd_path.exists(), "prd_yuan": prd_yuan_path.exists()},
        "views": [back_summary, gameplay_summary],
    }

    if args.write_logs:
        out_dir = root / "logs" / "ci" / summary["date"] / "fill-acceptance-refs"
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
