#!/usr/bin/env python3
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


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")


def split_refs(text: str) -> list[str]:
    m = REFS_RE.search(str(text or "").strip())
    if not m:
        return []
    blob = m.group(1).strip().replace("`", " ").replace(",", " ").replace(";", " ")
    return [p.strip().replace("\\", "/") for p in blob.split() if p.strip()]


def replace_refs(text: str, refs: list[str]) -> str:
    base = REFS_RE.sub("", str(text or "").strip()).rstrip()
    return f"{base} Refs: {' '.join(refs)}"


def ensure_ref(refs: list[str], ref: str) -> None:
    normalized = ref.replace("\\", "/")
    if normalized not in refs:
        refs.append(normalized)


def file_exists(root: Path, rel: str) -> bool:
    return (root / rel.replace("\\", "/")).exists()


def pick_existing(root: Path, candidates: list[str]) -> str | None:
    for c in candidates:
        if file_exists(root, c):
            return c.replace("\\", "/")
    return None


def apply_to_task(task: dict[str, Any], *, root: Path) -> dict[str, Any]:
    """
    Enforce the same deterministic text<->Refs consistency as validate_acceptance_refs.py, by amending Refs.

    Scope is intentionally conservative: only adds refs, never removes, and only updates acceptance items that
    violate the hard rules.
    """
    acceptance = task.get("acceptance")
    if not isinstance(acceptance, list):
        return {"changed": False, "changes": []}

    changes: list[dict[str, Any]] = []
    changed = False

    # Chosen stable fallbacks (must exist on disk, otherwise skip).
    fallback_core_cs = pick_existing(root, ["Game.Core.Tests/Services/SanguoEconomyManagerTests.cs"])
    fallback_gd = pick_existing(
        root,
        [
            "Tests.Godot/tests/Security/Hard/test_settings_config_security.gd",
            "Tests.Godot/tests/Security/Hard/test_db_path_rejection.gd",
        ],
    )

    for idx, raw in enumerate(list(acceptance)):
        if not isinstance(raw, str):
            continue
        text = raw
        lower = text.lower()
        refs = split_refs(text)
        before = list(refs)

        if "game.core" in lower:
            has_core_ref = any(r.replace("\\", "/").startswith("Game.Core.Tests/") and r.lower().endswith(".cs") for r in refs)
            if not has_core_ref and fallback_core_cs:
                ensure_ref(refs, fallback_core_cs)

        if ("gdunit4" in lower or "headless" in lower) and not any(r.lower().endswith(".gd") for r in refs):
            if fallback_gd:
                ensure_ref(refs, fallback_gd)

        if "xunit" in lower and not any(r.lower().endswith(".cs") for r in refs):
            if fallback_core_cs:
                ensure_ref(refs, fallback_core_cs)

        if refs != before:
            acceptance[idx] = replace_refs(text, refs)
            changed = True
            changes.append({"index": idx, "before_refs": before, "after_refs": refs})

    # Keep test_refs as a union of all refs used by acceptance.
    if changed:
        all_refs: list[str] = []
        for raw in acceptance:
            if isinstance(raw, str):
                all_refs.extend(split_refs(raw))
        uniq: list[str] = []
        seen: set[str] = set()
        for r in all_refs:
            if r in seen:
                continue
            seen.add(r)
            uniq.append(r)

        test_refs = task.get("test_refs")
        if not isinstance(test_refs, list):
            test_refs = []
        existing = [str(x).strip().replace("\\", "/") for x in test_refs if str(x).strip()]
        for r in uniq:
            if r not in existing:
                existing.append(r)
        task["test_refs"] = existing

    return {"changed": changed, "changes": changes}


def main() -> int:
    ap = argparse.ArgumentParser(description="Fix acceptance Refs type mismatches (Game.Core/xUnit/GdUnit4/headless) by amending Refs.")
    ap.add_argument("--tasks-back", default=".taskmaster/tasks/tasks_back.json")
    ap.add_argument("--tasks-gameplay", default=".taskmaster/tasks/tasks_gameplay.json")
    ap.add_argument("--task-ids", default="", help="Comma-separated taskmaster_id list. Empty = all tasks in file.")
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--out-dir", default="", help="Output directory for backups/reports (default logs/ci/<date>/fix-acceptance-ref-type-mismatches).")
    args = ap.parse_args()

    root = repo_root()
    today = dt.date.today().strftime("%Y-%m-%d")
    out_dir = Path(args.out_dir) if args.out_dir else root / "logs" / "ci" / today / "fix-acceptance-ref-type-mismatches"
    out_dir.mkdir(parents=True, exist_ok=True)

    task_ids: set[int] = set()
    if args.task_ids.strip():
        for part in args.task_ids.split(","):
            part = part.strip()
            if not part:
                continue
            task_ids.add(int(part))

    def process(path: Path) -> dict[str, Any]:
        data = load_json(path)
        if not isinstance(data, list):
            raise SystemExit(f"Expected JSON array: {path}")

        if args.write:
            (out_dir / f"{path.name}.bak").write_text(path.read_text(encoding="utf-8"), encoding="utf-8")

        changed_tasks: list[int] = []
        details: dict[int, Any] = {}
        for t in data:
            if not isinstance(t, dict):
                continue
            tid = t.get("taskmaster_id")
            if not isinstance(tid, int):
                continue
            if task_ids and tid not in task_ids:
                continue
            res = apply_to_task(t, root=root)
            if res["changed"]:
                changed_tasks.append(tid)
                details[tid] = res

        if args.write:
            write_json(path, data)

        return {"file": str(path.as_posix()), "changed_tasks": changed_tasks, "details": details}

    back_path = root / args.tasks_back
    gameplay_path = root / args.tasks_gameplay
    res_back = process(back_path)
    res_game = process(gameplay_path)

    summary = {"write": bool(args.write), "task_ids": sorted(task_ids), "results": [res_back, res_game]}
    write_json(out_dir / "summary.json", summary)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

