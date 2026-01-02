#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import json
import subprocess
from pathlib import Path
from typing import Any


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")


def run(cmd: list[str], cwd: Path) -> tuple[int, str]:
    p = subprocess.Popen(cmd, cwd=str(cwd), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="ignore")
    out, _ = p.communicate()
    return p.returncode or 0, out


def collect_task_ids(back: list[dict[str, Any]], gameplay: list[dict[str, Any]]) -> list[int]:
    ids: set[int] = set()
    for view in (back, gameplay):
        for t in view:
            if not isinstance(t, dict):
                continue
            tid = t.get("taskmaster_id")
            if isinstance(tid, int):
                ids.add(tid)
    return sorted(ids)


def main() -> int:
    ap = argparse.ArgumentParser(description="Bulk audit acceptance gates (Refs/Anchors) for all tasks in tasks_back/tasks_gameplay.")
    ap.add_argument("--out-dir", default="", help="Output directory (default logs/ci/<date>/audit-acceptance-gates).")
    ap.add_argument("--stage", default="refactor", choices=["red", "green", "refactor"])
    ap.add_argument("--limit", type=int, default=0, help="Limit to first N tasks (0 = all).")
    args = ap.parse_args()

    root = repo_root()
    today = dt.date.today().strftime("%Y-%m-%d")
    if args.out_dir:
        out_dir = Path(args.out_dir)
        if not out_dir.is_absolute():
            out_dir = (root / out_dir).resolve()
    else:
        out_dir = root / "logs" / "ci" / today / "audit-acceptance-gates"
    out_dir.mkdir(parents=True, exist_ok=True)

    back = load_json(root / ".taskmaster/tasks/tasks_back.json")
    gameplay = load_json(root / ".taskmaster/tasks/tasks_gameplay.json")
    if not isinstance(back, list) or not isinstance(gameplay, list):
        raise SystemExit("Expected tasks_back.json/tasks_gameplay.json to be JSON arrays.")

    task_ids = collect_task_ids(back, gameplay)
    if args.limit and args.limit > 0:
        task_ids = task_ids[: args.limit]

    per_task: list[dict[str, Any]] = []
    counts = {
        "total": len(task_ids),
        "refs_ok": 0,
        "refs_fail": 0,
        "anchors_ok": 0,
        "anchors_fail": 0,
    }

    for tid in task_ids:
        tdir = out_dir / f"task-{tid}"
        tdir.mkdir(parents=True, exist_ok=True)

        refs_out = tdir / "acceptance-refs.json"
        anchors_out = tdir / "acceptance-anchors.json"

        refs_cmd = [
            "py",
            "-3",
            "scripts/python/validate_acceptance_refs.py",
            "--task-id",
            str(tid),
            "--stage",
            args.stage,
            "--out",
            str(refs_out),
        ]
        anchors_cmd = [
            "py",
            "-3",
            "scripts/python/validate_acceptance_anchors.py",
            "--task-id",
            str(tid),
            "--stage",
            args.stage,
            "--out",
            str(anchors_out),
        ]

        rc_refs, out_refs = run(refs_cmd, cwd=root)
        (tdir / "acceptance-refs.log").write_text(out_refs, encoding="utf-8", newline="\n")
        rc_anchors, out_anchors = run(anchors_cmd, cwd=root)
        (tdir / "acceptance-anchors.log").write_text(out_anchors, encoding="utf-8", newline="\n")

        refs_ok = rc_refs == 0
        anchors_ok = rc_anchors == 0
        counts["refs_ok" if refs_ok else "refs_fail"] += 1
        counts["anchors_ok" if anchors_ok else "anchors_fail"] += 1

        per_task.append(
            {
                "task_id": tid,
                "refs": {"rc": rc_refs, "out": str(refs_out.relative_to(root)).replace("\\", "/")},
                "anchors": {"rc": rc_anchors, "out": str(anchors_out.relative_to(root)).replace("\\", "/")},
            }
        )

    summary = {"date": today, "stage": args.stage, "counts": counts, "tasks": per_task, "out_dir": str(out_dir.relative_to(root)).replace("\\", "/")}
    write_json(out_dir / "summary.json", summary)

    # Quick human-readable report.
    lines: list[str] = []
    lines.append("# Audit acceptance gates (bulk)")
    lines.append("")
    lines.append(f"- date: {today}")
    lines.append(f"- stage: {args.stage}")
    lines.append(f"- total: {counts['total']}")
    lines.append(f"- refs_ok: {counts['refs_ok']} refs_fail: {counts['refs_fail']}")
    lines.append(f"- anchors_ok: {counts['anchors_ok']} anchors_fail: {counts['anchors_fail']}")
    lines.append("")
    lines.append("## Failures")
    for t in per_task:
        if t["refs"]["rc"] == 0 and t["anchors"]["rc"] == 0:
            continue
        lines.append(f"- T{t['task_id']}: refs_rc={t['refs']['rc']} anchors_rc={t['anchors']['rc']}")
    (out_dir / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
