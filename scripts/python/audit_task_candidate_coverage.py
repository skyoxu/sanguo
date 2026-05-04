#!/usr/bin/env python3
"""Audit requirement coverage by generated task candidates."""

from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path
from typing import Any

BLOCKING_PRIORITIES = {"P0", "P1"}


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def audit(requirements: dict[str, Any], candidates: dict[str, Any]) -> dict[str, Any]:
    by_req: dict[str, list[str]] = {}
    for task in candidates.get("candidates", []):
        tid = str(task.get("id", ""))
        for rid in task.get("requirement_ids", []):
            by_req.setdefault(str(rid), []).append(tid)
    rows = []
    missing_blocking = []
    for anchor in requirements.get("anchors", []):
        rid = str(anchor.get("requirement_id"))
        covered = sorted(set(by_req.get(rid, [])))
        priority = str(anchor.get("priority", "P2")).upper()
        status = "covered" if covered else "missing"
        row = {
            "requirement_id": rid,
            "priority": priority,
            "kind": anchor.get("kind"),
            "source": f"{anchor.get('source_path')}:{anchor.get('line')}",
            "coverage_status": status,
            "covered_by_tasks": covered,
        }
        rows.append(row)
        if status == "missing" and priority in BLOCKING_PRIORITIES:
            missing_blocking.append(row)
    return {
        "schema": "task-generation.coverage-report.v1",
        "generated_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "requirement_count": len(rows),
        "candidate_count": len(candidates.get("candidates", [])),
        "missing_count": sum(1 for r in rows if r["coverage_status"] == "missing"),
        "missing_blocking_count": len(missing_blocking),
        "status": "ok" if not missing_blocking else "blocked",
        "coverage": rows,
        "missing_blocking": missing_blocking,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit task candidate coverage against requirement anchors.")
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--requirements", default="logs/ci/task-generation/requirements.index.json")
    parser.add_argument("--candidates", default="logs/ci/task-generation/task-candidates.enriched.json")
    parser.add_argument("--out", default="logs/ci/task-generation/coverage-report.json")
    parser.add_argument("--allow-missing-p1", action="store_true")
    args = parser.parse_args()
    root = Path(args.repo_root).resolve()
    result = audit(load_json(root / args.requirements), load_json(root / args.candidates))
    out = root / args.out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"coverage_report={out} status={result['status']} missing_blocking={result['missing_blocking_count']}")
    if result["status"] != "ok" and not args.allow_missing_p1:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

