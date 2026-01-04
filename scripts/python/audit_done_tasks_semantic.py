#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Audit "done" tasks for semantic completeness and test evidence hygiene.

This tool is defensive and deterministic. It does NOT modify files.
It produces a report under logs/ci/<date>/task-audit-done/ to help decide:
  - Which tasks can remain done
  - Which tasks should be re-run under the new workflow

Heuristics (semantic, best-effort):
  - If acceptance mentions Godot/scene/UI/headless/GdUnit4, at least one .gd test ref must exist.
  - Flag suspicious "placeholder-like" test refs such as Task<id>AcceptanceTests.cs or test_task<id>_acceptance.gd.
  - Flag task-scoped tests that look like static string matching instead of behavior (File.ReadAllText + Contain()).

Deterministic checks:
  - validate_acceptance_refs.py stage=refactor
  - validate_task_test_refs.py --require-non-empty
  - check_test_naming.py --style strict --task-id <id> (task-scoped)

Windows:
  py -3 scripts/python/audit_done_tasks_semantic.py --task-ids 1,2,3
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any


REFS_RE = re.compile(r"\bRefs\s*:\s*(.+)$", flags=re.IGNORECASE)
GODOT_HINT_RE = re.compile(r"\b(gdunit|headless|scene|signal|tscn|node)\b", flags=re.IGNORECASE)
PLACEHOLDER_CS_RE = re.compile(r"/Task(\d+)AcceptanceTests\.cs$", flags=re.IGNORECASE)
PLACEHOLDER_GD_RE = re.compile(r"/test_task(\d+)_acceptance\.gd$", flags=re.IGNORECASE)
# NOTE: Keep this file ASCII-only (repo rule). Use unicode escape sequences for
# any non-English terms that might appear in acceptance/test strategy text.
MASTER_GODOT_HINT_RE = re.compile(
    r"(godot|tween|\u52a8\u753b|headless|gdunit)", flags=re.IGNORECASE
)


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def today_str() -> str:
    import datetime as dt

    return dt.date.today().strftime("%Y-%m-%d")


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


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


def split_csv(s: str) -> list[str]:
    items: list[str] = []
    for raw in str(s or "").split(","):
        v = raw.strip()
        if not v:
            continue
        items.append(v)
    return items


def find_view_task(view: list[dict[str, Any]], task_id: int) -> dict[str, Any] | None:
    for t in view:
        if not isinstance(t, dict):
            continue
        if t.get("taskmaster_id") == int(task_id):
            return t
    return None


def parse_refs_from_acceptance(entry: dict[str, Any] | None) -> list[str]:
    if not entry:
        return []
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


def acceptance_mentions_godot(entry: dict[str, Any] | None) -> bool:
    if not entry:
        return False
    def _is_reference_line(s: str) -> bool:
        ss = s.lower()
        if "local demo" in ss or "demo references" in ss:
            return True
        # "Godot official demo project" is a learning reference, not an acceptance requirement.
        if "\u6f14\u793a" in s or "\u5b98\u65b9\u6f14\u793a" in s:
            return True
        return False

    for raw in entry.get("acceptance") or []:
        s = str(raw or "")
        if _is_reference_line(s):
            continue
        if GODOT_HINT_RE.search(s):
            return True
    for raw in entry.get("test_strategy") or []:
        s = str(raw or "")
        if _is_reference_line(s):
            continue
        if GODOT_HINT_RE.search(s):
            return True
    return False


def view_layer_requires_godot(entry: dict[str, Any] | None) -> bool:
    # Governance: treat ui-layer tasks as requiring at least one GdUnit4/headless test ref.
    if not entry:
        return False
    return str(entry.get("layer") or "").strip().lower() == "ui"


def file_looks_like_static_string_test(path: Path) -> bool:
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return False
    if "File.ReadAllText" in text and ".Should().Contain(" in text:
        return True
    return False


@dataclass(frozen=True)
class TaskAudit:
    task_id: int
    status: str  # keep_done | redo
    reasons: list[str]
    missing_files: list[str]
    placeholder_refs: list[str]
    suspicious_tests: list[str]
    steps: list[dict[str, Any]]


def audit_task(*, task_id: int, back: list[dict[str, Any]], gameplay: list[dict[str, Any]], out_dir: Path) -> TaskAudit:
    root = repo_root()
    tasks_json = load_json(root / ".taskmaster" / "tasks" / "tasks.json")
    master_tasks = (tasks_json.get("master") or {}).get("tasks") or []
    master = next((t for t in master_tasks if isinstance(t, dict) and int(t.get("id", -1)) == int(task_id)), {})

    back_entry = find_view_task(back, task_id)
    game_entry = find_view_task(gameplay, task_id)

    reasons: list[str] = []
    missing_files: list[str] = []
    placeholder_refs: list[str] = []
    suspicious_tests: list[str] = []
    steps: list[dict[str, Any]] = []

    if back_entry is None and game_entry is None:
        return TaskAudit(
            task_id=task_id,
            status="redo",
            reasons=["missing mapping in both tasks_back.json and tasks_gameplay.json"],
            missing_files=[],
            placeholder_refs=[],
            suspicious_tests=[],
            steps=[],
        )

    # Deterministic evidence gates (refactor-stage).
    acc_out = out_dir / f"acceptance-refs.{task_id}.json"
    rc, out = run_cmd(
        ["py", "-3", "scripts/python/validate_acceptance_refs.py", "--task-id", str(task_id), "--stage", "refactor", "--out", str(acc_out)],
        cwd=root,
        timeout_sec=60,
    )
    write_text(out_dir / f"validate_acceptance_refs.{task_id}.log", out)
    steps.append({"name": "validate_acceptance_refs", "rc": rc, "out": str(acc_out)})

    tr_out = out_dir / f"task-test-refs.{task_id}.json"
    rc2, out2 = run_cmd(
        ["py", "-3", "scripts/python/validate_task_test_refs.py", "--task-id", str(task_id), "--require-non-empty", "--out", str(tr_out)],
        cwd=root,
        timeout_sec=60,
    )
    write_text(out_dir / f"validate_task_test_refs.{task_id}.log", out2)
    steps.append({"name": "validate_task_test_refs", "rc": rc2, "out": str(tr_out)})

    rc3, out3 = run_cmd(
        ["py", "-3", "scripts/python/check_test_naming.py", "--task-id", str(task_id), "--style", "strict"],
        cwd=root,
        timeout_sec=60,
    )
    write_text(out_dir / f"check_test_naming.{task_id}.log", out3)
    steps.append({"name": "check_test_naming", "rc": rc3})

    # Semantic heuristics on top of deterministic checks.
    refs = parse_refs_from_acceptance(back_entry) + [r for r in parse_refs_from_acceptance(game_entry) if r not in parse_refs_from_acceptance(back_entry)]
    for r in refs:
        disk = root / r
        if not disk.exists():
            missing_files.append(r)
        if PLACEHOLDER_CS_RE.search("/" + r) or PLACEHOLDER_GD_RE.search("/" + r):
            placeholder_refs.append(r)
        if disk.exists() and disk.suffix.lower() == ".cs" and file_looks_like_static_string_test(disk):
            suspicious_tests.append(r)

    def _master_requires_godot() -> bool:
        details = str(master.get("details") or "")
        test_strategy = str(master.get("testStrategy") or "")
        # Ignore demo paths in taskStrategy; only treat as requirement if it mentions engine behavior.
        text = "\n".join([details, test_strategy])
        if "Local demo" in text or "Local demo paths" in text:
            # keep scanning; demo references are not requirements
            pass
        return bool(MASTER_GODOT_HINT_RE.search(text))

    mentions_godot = (
        acceptance_mentions_godot(back_entry)
        or acceptance_mentions_godot(game_entry)
        or view_layer_requires_godot(back_entry)
        or view_layer_requires_godot(game_entry)
        or _master_requires_godot()
    )
    has_gd_ref = any(r.endswith(".gd") for r in refs)
    if mentions_godot and not has_gd_ref:
        reasons.append("acceptance/test_strategy mentions Godot behaviors but no .gd refs found")

    if missing_files:
        reasons.append("acceptance refs point to missing files")
    if placeholder_refs:
        reasons.append("placeholder-like refs detected (rename/rebind recommended)")
    if suspicious_tests:
        reasons.append("suspicious static string tests detected (may not satisfy acceptance semantics)")

    # Decide keep_done vs redo.
    status = "keep_done"
    if rc != 0 or rc2 != 0:
        status = "redo"
        reasons.append("deterministic refactor-stage gates failed")
    # If Godot is required but not present, mark redo.
    if mentions_godot and not has_gd_ref:
        status = "redo"

    return TaskAudit(
        task_id=task_id,
        status=status,
        reasons=reasons,
        missing_files=missing_files,
        placeholder_refs=placeholder_refs,
        suspicious_tests=suspicious_tests,
        steps=steps,
    )


def main() -> int:
    ap = argparse.ArgumentParser(description="Audit done tasks semantics and refs/test_refs hygiene.")
    ap.add_argument("--task-ids", required=True, help="Comma-separated task ids to audit (e.g. 1,2,3).")
    args = ap.parse_args()

    root = repo_root()
    out_dir = root / "logs" / "ci" / today_str() / "task-audit-done"
    out_dir.mkdir(parents=True, exist_ok=True)

    back = load_json(root / ".taskmaster" / "tasks" / "tasks_back.json")
    gameplay = load_json(root / ".taskmaster" / "tasks" / "tasks_gameplay.json")
    if not isinstance(back, list) or not isinstance(gameplay, list):
        raise ValueError("tasks_back.json and tasks_gameplay.json must be JSON arrays")

    task_ids: list[int] = []
    for s in split_csv(args.task_ids):
        if not s.isdigit():
            raise ValueError(f"invalid task id: {s}")
        task_ids.append(int(s))

    audits: list[dict[str, Any]] = []
    keep: list[int] = []
    redo: list[int] = []
    for tid in task_ids:
        a = audit_task(task_id=tid, back=back, gameplay=gameplay, out_dir=out_dir)
        audits.append(
            {
                "task_id": a.task_id,
                "status": a.status,
                "reasons": a.reasons,
                "missing_files": a.missing_files,
                "placeholder_refs": a.placeholder_refs,
                "suspicious_tests": a.suspicious_tests,
                "steps": a.steps,
            }
        )
        (keep if a.status == "keep_done" else redo).append(tid)

    summary = {"task_ids": task_ids, "keep_done": keep, "redo": redo, "audits": audits}
    write_json(out_dir / "summary.json", summary)

    # Human-readable report (English only; scripts must not output Chinese).
    lines: list[str] = []
    lines.append("# Done Task Audit Report (Semantics + Evidence Chain)")
    lines.append("")
    lines.append(f"- Task ids: {', '.join(str(x) for x in task_ids)}")
    lines.append(f"- Keep done: {', '.join(str(x) for x in keep) if keep else '(none)'}")
    lines.append(f"- Redo: {', '.join(str(x) for x in redo) if redo else '(none)'}")
    lines.append("")
    for item in audits:
        tid = item["task_id"]
        lines.append(f"## Task {tid}: {item['status']}")
        for r in item.get("reasons") or []:
            lines.append(f"- Reason: {r}")
        for r in item.get("missing_files") or []:
            lines.append(f"- Missing file: {r}")
        for r in item.get("placeholder_refs") or []:
            lines.append(f"- Placeholder-like Refs: {r}")
        for r in item.get("suspicious_tests") or []:
            lines.append(f"- Suspicious test (static string matching): {r}")
        lines.append("")

    write_text(out_dir / "report.md", "\n".join(lines).strip() + "\n")
    print(f"TASK_AUDIT_DONE status=ok keep={len(keep)} redo={len(redo)} out={out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
