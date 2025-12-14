#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Produce a soft PRD coverage report between:

- .taskmaster/docs/prd-*.txt (PRD text files)
- .taskmaster/tasks/tasks_back.json
- .taskmaster/tasks/tasks_gameplay.json
- .taskmaster/tasks/tasks_newguild.json

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


PRD_DIR = Path(".taskmaster/docs")
TASKS_DIR = Path(".taskmaster/tasks")


@dataclass
class PrdCoverage:
    prd_file: str
    tokens: List[str]
    back_tasks: int
    gameplay_tasks: int
    newguild_tasks: int


def load_tasks(path: Path) -> List[dict]:
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, list):
        return data
    if isinstance(data, dict) and "tasks" in data:
        return data["tasks"]
    return []


def extract_tokens_from_prd_name(name: str) -> List[str]:
    """Derive heuristic tokens from a prd-*.txt filename."""

    stem = name
    if stem.startswith("prd-"):
        stem = stem[len("prd-") :]
    if stem.endswith(".txt"):
        stem = stem[: -len(".txt")]
    # split by '-' and ignore very short/common tokens
    raw_tokens = stem.replace("_", "-").split("-")
    tokens: List[str] = []
    stop = {"and", "the", "for", "with", "godot", "csharp", "newguild", "vitegame"}
    for tok in raw_tokens:
        tok = tok.strip().lower()
        if not tok:
            continue
        if tok in stop:
            continue
        if len(tok) <= 3:
            continue
        tokens.append(tok)
    return tokens


def task_text(task: dict) -> str:
    parts = []
    for key in ("title", "description", "details", "acceptance"):
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
    for t in tasks:
        txt = task_text(t)
        if any(tok in txt for tok in tokens):
            count += 1
    return count


def build_coverage() -> Dict[str, PrdCoverage]:
    prd_files = sorted(p for p in PRD_DIR.glob("prd-*.txt") if p.is_file())

    tasks_back = load_tasks(TASKS_DIR / "tasks_back.json")
    tasks_gameplay = load_tasks(TASKS_DIR / "tasks_gameplay.json")
    tasks_newguild = load_tasks(TASKS_DIR / "tasks_newguild.json")

    coverage: Dict[str, PrdCoverage] = {}

    for prd in prd_files:
        name = prd.name
        tokens = extract_tokens_from_prd_name(name)
        back_count = count_tasks_referencing_tokens(tasks_back, tokens)
        gm_count = count_tasks_referencing_tokens(tasks_gameplay, tokens)
        ng_count = count_tasks_referencing_tokens(tasks_newguild, tokens)
        coverage[name] = PrdCoverage(
            prd_file=name,
            tokens=tokens,
            back_tasks=back_count,
            gameplay_tasks=gm_count,
            newguild_tasks=ng_count,
        )

    return coverage


def write_report(coverage: Dict[str, PrdCoverage], root: Path) -> Path:
    today = date.today().strftime("%Y-%m-%d")
    out_dir = root / "logs" / "ci" / today
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "prd-coverage-report.json"
    payload = {name: asdict(cov) for name, cov in coverage.items()}
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return out_path


def main() -> int:
    root = Path(__file__).resolve().parents[2]
    print("=== PRD Coverage Report (heuristic, non-blocking) ===")
    print(f"Project root: {root}")

    coverage = build_coverage()

    print("\nPRD file coverage (task counts by source):")
    for name, cov in sorted(coverage.items()):
        print(
            f"- {name}: back={cov.back_tasks}, gameplay={cov.gameplay_tasks}, "
            f"tasks_newguild={cov.newguild_tasks}, tokens={cov.tokens}"
        )

    out_path = write_report(coverage, root)
    print(f"\nJSON report written to: {out_path}")
    print("Note: this report is heuristic and does not act as a CI gate.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

