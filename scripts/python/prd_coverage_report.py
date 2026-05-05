#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Produce a soft PRD coverage report between:

- .taskmaster/docs/prd-*.txt
- .taskmaster/tasks/tasks*.json

This script does NOT act as a CI gate. It generates a heuristic report
showing, for each PRD file, roughly how many tasks appear to reference it
based on filename tokens.

Usage:
    py -3 scripts/python/prd_coverage_report.py

Output:
    - Human-readable summary printed to stdout
    - JSON report at logs/ci/<YYYY-MM-DD>/prd-coverage-report.json
"""

from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from datetime import date
from pathlib import Path
from typing import Dict, List


ROOT = Path(__file__).resolve().parents[2]
PRD_DIR = ROOT / ".taskmaster" / "docs"
TASKS_DIR = ROOT / ".taskmaster" / "tasks"


@dataclass
class PrdCoverage:
    prd_file: str
    tokens: List[str]
    task_counts: Dict[str, int]


def load_tasks(path: Path) -> List[dict]:
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, list):
        return [row for row in data if isinstance(row, dict)]
    if isinstance(data, dict):
        master = data.get("master")
        if isinstance(master, dict) and isinstance(master.get("tasks"), list):
            return [row for row in master["tasks"] if isinstance(row, dict)]
        if isinstance(data.get("tasks"), list):
            return [row for row in data["tasks"] if isinstance(row, dict)]
    return []


def discover_task_views() -> Dict[str, Path]:
    views: Dict[str, Path] = {}
    if not TASKS_DIR.exists():
        return views
    for path in sorted(TASKS_DIR.glob("tasks*.json")):
        if path.is_file():
            views[path.stem] = path
    return views


def extract_tokens_from_prd_name(name: str) -> List[str]:
    stem = name
    if stem.startswith("prd-"):
        stem = stem[len("prd-"):]
    if stem.endswith(".txt"):
        stem = stem[:-len(".txt")]
    raw_tokens = stem.replace("_", "-").split("-")
    repo_tokens = {part for part in ROOT.name.lower().replace("_", "-").split("-") if part}
    stop = {
        "and", "the", "for", "with", "game", "games", "project", "template",
        "godot", "csharp", "docs", "doc", "prd", "feature", "module",
    } | repo_tokens
    tokens: List[str] = []
    for tok in raw_tokens:
        tok = tok.strip().lower()
        if not tok or tok in stop or len(tok) <= 3:
            continue
        tokens.append(tok)
    return tokens


def task_text(task: dict) -> str:
    parts: List[str] = []
    for key in ("title", "description", "details", "acceptance", "acceptance_criteria"):
        val = task.get(key)
        if isinstance(val, str):
            parts.append(val)
        elif isinstance(val, list):
            parts.extend(str(x) for x in val)
    return " ".join(parts).lower()


def count_tasks_referencing_tokens(tasks: List[dict], tokens: List[str]) -> int:
    if not tokens or not tasks:
        return 0
    count = 0
    for task in tasks:
        txt = task_text(task)
        if any(tok in txt for tok in tokens):
            count += 1
    return count


def build_coverage() -> Dict[str, PrdCoverage]:
    prd_files = sorted(path for path in PRD_DIR.glob("prd-*.txt") if path.is_file())
    task_views = {name: load_tasks(path) for name, path in discover_task_views().items()}

    coverage: Dict[str, PrdCoverage] = {}
    for prd in prd_files:
        tokens = extract_tokens_from_prd_name(prd.name)
        task_counts = {
            view_name: count_tasks_referencing_tokens(tasks, tokens)
            for view_name, tasks in sorted(task_views.items())
        }
        coverage[prd.name] = PrdCoverage(
            prd_file=prd.name,
            tokens=tokens,
            task_counts=task_counts,
        )
    return coverage


def write_report(coverage: Dict[str, PrdCoverage]) -> Path:
    today = date.today().strftime("%Y-%m-%d")
    out_dir = ROOT / "logs" / "ci" / today
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "prd-coverage-report.json"
    payload = {name: asdict(cov) for name, cov in coverage.items()}
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    return out_path


def main() -> int:
    print("=== PRD Coverage Report (heuristic, non-blocking) ===")
    print(f"Project root: {ROOT}")

    coverage = build_coverage()
    views = sorted(discover_task_views().keys())
    print(f"Active task views: {views if views else '(none)'}")

    print("\nPRD file coverage (task counts by view):")
    for name, cov in sorted(coverage.items()):
        counts = ", ".join(f"{view}={count}" for view, count in sorted(cov.task_counts.items())) or "(no task views)"
        print(f"- {name}: {counts}, tokens={cov.tokens}")

    out_path = write_report(coverage)
    print(f"\nJSON report written to: {out_path}")
    print("Note: this report is heuristic and does not act as a CI gate.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

