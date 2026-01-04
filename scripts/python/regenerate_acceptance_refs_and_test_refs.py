#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Regenerate acceptance "Refs:" and task-level test_refs for task views.

Scope:
  - `.taskmaster/tasks/tasks_back.json`
  - `.taskmaster/tasks/tasks_gameplay.json`

Intent:
  - Ensure every acceptance item ends with a deterministic test evidence mapping:
      "... Refs: <repo-relative test path>"
  - Ensure `test_refs` is the union of all referenced paths (replace semantics).
  - Improve naming away from placeholder patterns.

This script is deterministic (no LLM). It uses:
  - Existing test files in repo as preferred refs when identifiers are present.
  - Fallback naming conventions from docs/testing-framework.md.

Windows:
  py -3 scripts/python/regenerate_acceptance_refs_and_test_refs.py --write
  py -3 scripts/python/regenerate_acceptance_refs_and_test_refs.py --exclude-task-ids 1,2,3 --write
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
BACKTICK_ID_RE = re.compile(r"`([A-Za-z_][A-Za-z0-9_]*)`")
PASCAL_ID_RE = re.compile(r"\b([A-Z][A-Za-z0-9]+)\b")
GODOT_HINT_RE = re.compile(r"\b(gdunit|headless|scene|signal|tscn|node)\b", flags=re.IGNORECASE)


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def today_str() -> str:
    return dt.date.today().strftime("%Y-%m-%d")


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def split_csv(s: str) -> set[int]:
    out: set[int] = set()
    for raw in str(s or "").split(","):
        v = raw.strip()
        if not v:
            continue
        if not v.isdigit():
            raise ValueError(f"invalid task id: {v}")
        out.add(int(v))
    return out


def snake(s: str) -> str:
    s = re.sub(r"[^A-Za-z0-9]+", "_", s.strip())
    s = re.sub(r"_+", "_", s).strip("_").lower()
    return s or "behavior"


def extract_identifiers(text: str) -> list[str]:
    s = str(text or "")
    ids: list[str] = []
    for m in BACKTICK_ID_RE.finditer(s):
        ids.append(m.group(1))
    # If no backticks, also try to capture well-known PascalCase identifiers.
    if not ids:
        for m in PASCAL_ID_RE.finditer(s):
            ids.append(m.group(1))
    # Dedup preserve order.
    seen = set()
    out: list[str] = []
    for x in ids:
        if x in seen:
            continue
        seen.add(x)
        out.append(x)
    return out


def strip_refs_suffix(text: str) -> str:
    s = str(text or "").rstrip()
    m = REFS_RE.search(s)
    if not m:
        return s
    return s[: m.start()].rstrip()


def collect_acceptance_refs(entry: dict[str, Any]) -> list[str]:
    out: list[str] = []
    for raw in entry.get("acceptance") or []:
        s = str(raw or "").strip()
        m = REFS_RE.search(s)
        if not m:
            continue
        blob = str(m.group(1) or "").replace("`", " ").replace(",", " ").replace(";", " ")
        for token in blob.split():
            p = token.strip().replace("\\", "/")
            if not p:
                continue
            if p not in out:
                out.append(p)
    return out


@dataclass(frozen=True)
class TaskContext:
    task_id: int
    master_title: str
    view_title: str
    layer: str
    full_text: str


def topic_pascal(ctx: TaskContext) -> str:
    # Lightweight, deterministic keyword-to-topic mapping.
    # NOTE: Keep this file ASCII-only (repo rule). Use unicode escape sequences for
    # any non-English terms that might appear in task titles.
    rules: list[tuple[str, str]] = [
        ("AI", "Ai"),
        ("ai", "Ai"),
        ("HUD", "Hud"),
        ("hud", "Hud"),
        ("\u56de\u5408", "Turn"),
        ("\u6708\u672b", "MonthEnd"),
        ("\u5b63\u5ea6", "Quarter"),
        ("\u5e74\u5ea6", "YearEnd"),
        ("\u5e74\u672b", "YearEnd"),
        ("\u5730\u4ef7", "Price"),
        ("\u8c03\u4ef7", "PriceAdjustment"),
        ("\u7ed3\u7b97", "Settlement"),
        ("\u9ab0\u5b50", "Dice"),
        ("\u68cb\u5b50", "Token"),
        ("\u79fb\u52a8", "Move"),
        ("\u68cb\u76d8", "Board"),
        ("\u57ce\u6c60", "City"),
        ("\u4e70\u5730", "BuyLand"),
        ("\u8d2d\u4e70", "Buy"),
        ("\u4e8b\u4ef6", "Event"),
        ("\u7ecf\u6d4e", "Economy"),
        ("\u5ba1\u8ba1", "Audit"),
        ("\u5b89\u5168", "Security"),
        ("\u6027\u80fd", "Performance"),
        ("\u95e8\u7981", "Gate"),
        ("\u5951\u7ea6", "Contracts"),
        ("\u65e5\u5fd7", "Logging"),
    ]

    # Do not use full acceptance text here; it often contains incidental words (e.g. "UI feedback")
    # that are not suitable for test file naming.
    src = " ".join([ctx.master_title, ctx.view_title])
    parts: list[str] = []
    for k, v in rules:
        if k in src and v not in parts:
            parts.append(v)
    # Only include Ui as a topic when the task itself is UI-layer.
    if ctx.layer == "ui" and "Ui" not in parts:
        parts.insert(0, "Ui")
    # Keep it short.
    parts = parts[:5]
    return "".join(parts) if parts else "Requirements"


def build_test_file_index(root: Path) -> dict[str, str]:
    # Map basename -> repo-relative path (prefer Game.Core.Tests then Tests.Godot).
    files = []
    for base in ["Game.Core.Tests", "Tests.Godot/tests"]:
        base_dir = root / base
        if not base_dir.exists():
            continue
        files.extend([p for p in base_dir.rglob("*") if p.is_file() and (p.suffix.lower() in [".cs", ".gd"])])

    idx: dict[str, str] = {}
    for p in files:
        rel = p.relative_to(root).as_posix()
        name = p.name
        if name not in idx:
            idx[name] = rel
            continue
        # Prefer Game.Core.Tests paths over others for same basename.
        if rel.startswith("Game.Core.Tests/") and not idx[name].startswith("Game.Core.Tests/"):
            idx[name] = rel
    return idx


def pick_ref_for_item(ctx: TaskContext, *, item_text: str, test_index: dict[str, str]) -> str:
    # Prefer existing tests when we can infer a subject identifier.
    ids = extract_identifiers(item_text)
    for ident in ids:
        candidates = []
        candidates.append(f"{ident}Tests.cs")
        if ident.startswith("I") and len(ident) >= 2 and ident[1].isupper():
            candidates.append(f"{ident[1:]}Tests.cs")
        for c in candidates:
            if c in test_index:
                return test_index[c]

    # UI/Godot hints: pick .gd under a conventional location.
    if ctx.layer == "ui" or GODOT_HINT_RE.search(item_text or ""):
        base = "Tests.Godot/tests/UI" if ("HUD" in ctx.master_title or "HUD" in ctx.view_title) else "Tests.Godot/tests/Scenes/Sanguo"
        topic = topic_pascal(ctx)
        scope = "hud" if ("HUD" in ctx.master_title or "HUD" in ctx.view_title or "Hud" in topic) else "ui"
        behavior = snake(topic.replace("Ui", "").replace("Hud", "") or topic)
        if base.endswith("/UI"):
            return f"{base}/test_{scope}_{behavior}_task{ctx.task_id}.gd"
        return f"{base}/test_sanguo_{behavior}_task{ctx.task_id}.gd"

    # Core fallback: task-scoped but non-placeholder.
    topic = topic_pascal(ctx)
    return f"Game.Core.Tests/Tasks/Task{ctx.task_id}{topic}Tests.cs"


def regenerate_entry(entry: dict[str, Any], *, ctx: TaskContext, test_index: dict[str, str]) -> dict[str, Any]:
    acceptance = entry.get("acceptance")
    if not isinstance(acceptance, list):
        return {"updated_acceptance": 0, "updated_test_refs": 0}

    new_acceptance: list[str] = []
    refs_union: list[str] = []
    updated = 0

    for raw in acceptance:
        text = str(raw or "").strip()
        base = strip_refs_suffix(text)
        ref = pick_ref_for_item(ctx, item_text=base, test_index=test_index)
        new_acceptance.append(base + " Refs: " + ref)
        if ref not in refs_union:
            refs_union.append(ref)
        updated += 1

    entry["acceptance"] = new_acceptance

    before = list(entry.get("test_refs") or []) if isinstance(entry.get("test_refs"), list) else []
    entry["test_refs"] = list(refs_union)
    updated_test_refs = 1 if before != entry["test_refs"] else 0
    return {"updated_acceptance": updated, "updated_test_refs": updated_test_refs}


def main() -> int:
    ap = argparse.ArgumentParser(description="Regenerate acceptance Refs and test_refs for task views.")
    ap.add_argument("--exclude-task-ids", default="", help="Comma-separated task ids to skip (e.g. 1,2,3).")
    ap.add_argument("--write", action="store_true", help="Write changes in-place.")
    args = ap.parse_args()

    root = repo_root()
    exclude = split_csv(args.exclude_task_ids)

    tasks_json = load_json(root / ".taskmaster" / "tasks" / "tasks.json")
    master_tasks = (tasks_json.get("master") or {}).get("tasks") or []
    master_by_id: dict[int, dict[str, Any]] = {}
    for t in master_tasks:
        if not isinstance(t, dict):
            continue
        try:
            tid = int(t.get("id"))
        except Exception:
            continue
        master_by_id[tid] = t

    back_path = root / ".taskmaster" / "tasks" / "tasks_back.json"
    gameplay_path = root / ".taskmaster" / "tasks" / "tasks_gameplay.json"
    back = load_json(back_path)
    gameplay = load_json(gameplay_path)
    if not isinstance(back, list) or not isinstance(gameplay, list):
        raise ValueError("tasks_back.json and tasks_gameplay.json must be JSON arrays")

    out_dir = root / "logs" / "ci" / today_str() / "task-refs-regenerate"
    out_dir.mkdir(parents=True, exist_ok=True)

    # Backup current state for forensics.
    write_json(out_dir / "tasks_back.before.json", back)
    write_json(out_dir / "tasks_gameplay.before.json", gameplay)

    test_index = build_test_file_index(root)

    report: dict[str, Any] = {"exclude_task_ids": sorted(exclude), "back": [], "gameplay": []}

    def _process(view: list[dict[str, Any]], *, view_name: str) -> None:
        for entry in view:
            if not isinstance(entry, dict):
                continue
            tid = entry.get("taskmaster_id")
            if not isinstance(tid, int):
                continue
            if tid in exclude:
                continue
            master = master_by_id.get(tid) or {}
            ctx = TaskContext(
                task_id=tid,
                master_title=str(master.get("title") or "").strip(),
                view_title=str(entry.get("title") or "").strip(),
                layer=str(entry.get("layer") or "").strip().lower(),
                full_text=" ".join([str(x or "") for x in (entry.get("acceptance") or [])])[:4000],
            )
            res = regenerate_entry(entry, ctx=ctx, test_index=test_index)
            report[view_name].append(
                {
                    "task_id": tid,
                    "layer": ctx.layer,
                    "updated_acceptance": res["updated_acceptance"],
                    "updated_test_refs": res["updated_test_refs"],
                    "test_refs": entry.get("test_refs"),
                }
            )

    _process(back, view_name="back")
    _process(gameplay, view_name="gameplay")

    write_json(out_dir / "report.json", report)

    if not args.write:
        print(f"TASK_REFS_REGENERATE status=dry_run out={out_dir}")
        return 0

    write_json(back_path, back)
    write_json(gameplay_path, gameplay)
    print(f"TASK_REFS_REGENERATE status=ok out={out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
