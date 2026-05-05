#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Check consistency between gate-bundle documentation and runtime bundle script.

Validates that gate script names listed in:
  docs/workflows/gate-bundle.md
match the names defined in:
  scripts/python/run_gate_bundle.py

Output:
  logs/ci/<YYYY-MM-DD>/gate-bundle-consistency/summary.json
"""

from __future__ import annotations

import argparse
import datetime as dt
import importlib.util
import json
import re
import sys
from pathlib import Path
from typing import Any


DOC_PATH = Path("docs/workflows/gate-bundle.md")
BUNDLE_PATH = Path("scripts/python/run_gate_bundle.py")


def _today() -> str:
    return dt.date.today().strftime("%Y-%m-%d")


def _extract_doc_sections(text: str) -> tuple[list[str], list[str]]:
    hard: list[str] = []
    soft: list[str] = []
    section: str | None = None

    bullet_re = re.compile(r"^\s*-\s+`([^`]+)`")

    for raw_line in text.splitlines():
        line = raw_line.rstrip()
        stripped = line.strip()

        if stripped.startswith("### "):
            title = stripped[4:].strip().lower()
            if title == "hard gates":
                section = "hard"
            elif title == "soft gates":
                section = "soft"
            else:
                section = None
            continue

        if section is None:
            continue

        match = bullet_re.match(line)
        if not match:
            continue

        value = match.group(1).strip()
        if value.endswith(".py"):
            if section == "hard":
                hard.append(value)
            else:
                soft.append(value)

    return hard, soft


def _load_bundle_module(repo_root: Path):
    path = repo_root / BUNDLE_PATH
    spec = importlib.util.spec_from_file_location("run_gate_bundle_module", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load module from {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # type: ignore[assignment]
    return module


def _extract_script_names(commands: list[dict[str, Any]]) -> list[str]:
    names: list[str] = []
    for item in commands:
        cmd = [str(x) for x in item.get("cmd", [])]
        py_candidates = [Path(x).name for x in cmd if str(x).lower().endswith(".py")]
        if not py_candidates:
            continue
        names.append(py_candidates[0])
    return names


def _compare(doc_list: list[str], code_list: list[str]) -> dict[str, Any]:
    doc_set = set(doc_list)
    code_set = set(code_list)
    return {
        "doc": doc_list,
        "code": code_list,
        "missing_in_doc": sorted(code_set - doc_set),
        "extra_in_doc": sorted(doc_set - code_set),
        "order_match": doc_list == code_list,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Check gate-bundle doc/script consistency")
    parser.add_argument("--out", default="", help="Optional output summary path")
    args = parser.parse_args()

    repo_root = Path.cwd().resolve()
    doc_file = repo_root / DOC_PATH
    bundle_file = repo_root / BUNDLE_PATH

    if not doc_file.exists():
        print(f"GATE_BUNDLE_DOC_SYNC status=fail reason=missing-doc path={DOC_PATH.as_posix()}")
        return 1
    if not bundle_file.exists():
        print(f"GATE_BUNDLE_DOC_SYNC status=fail reason=missing-script path={BUNDLE_PATH.as_posix()}")
        return 1

    doc_text = doc_file.read_text(encoding="utf-8")
    doc_hard, doc_soft = _extract_doc_sections(doc_text)

    module = _load_bundle_module(repo_root)
    task_files = [".taskmaster/tasks/tasks_back.json", ".taskmaster/tasks/tasks_gameplay.json"]

    if hasattr(module, "_hard_gate_commands_with_options"):
        hard_commands = module._hard_gate_commands_with_options(task_files, False)
    else:
        hard_commands = module._hard_gate_commands(task_files)

    try:
        soft_commands = module._soft_gate_commands(task_files, False)
    except TypeError:
        soft_commands = module._soft_gate_commands(task_files)

    code_hard = _extract_script_names(hard_commands)
    code_soft = _extract_script_names(soft_commands)

    hard_cmp = _compare(doc_hard, code_hard)
    soft_cmp = _compare(doc_soft, code_soft)

    hard_ok = not hard_cmp["missing_in_doc"] and not hard_cmp["extra_in_doc"] and hard_cmp["order_match"]
    soft_ok = not soft_cmp["missing_in_doc"] and not soft_cmp["extra_in_doc"] and soft_cmp["order_match"]
    ok = hard_ok and soft_ok

    summary = {
        "ts": dt.datetime.now(dt.timezone.utc).isoformat(),
        "action": "gate-bundle-doc-sync",
        "status": "ok" if ok else "fail",
        "doc": DOC_PATH.as_posix(),
        "script": BUNDLE_PATH.as_posix(),
        "hard": hard_cmp,
        "soft": soft_cmp,
    }

    if args.out:
        out_path = Path(args.out)
    else:
        out_path = Path("logs") / "ci" / _today() / "gate-bundle-consistency" / "summary.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(
        f"GATE_BUNDLE_DOC_SYNC status={'ok' if ok else 'fail'} "
        f"hard_missing={len(hard_cmp['missing_in_doc'])} hard_extra={len(hard_cmp['extra_in_doc'])} "
        f"soft_missing={len(soft_cmp['missing_in_doc'])} soft_extra={len(soft_cmp['extra_in_doc'])} "
        f"out={out_path.as_posix()}"
    )

    if not ok:
        if hard_cmp["missing_in_doc"]:
            print(f" - hard missing_in_doc: {hard_cmp['missing_in_doc']}")
        if hard_cmp["extra_in_doc"]:
            print(f" - hard extra_in_doc: {hard_cmp['extra_in_doc']}")
        if not hard_cmp["order_match"]:
            print(" - hard order mismatch")

        if soft_cmp["missing_in_doc"]:
            print(f" - soft missing_in_doc: {soft_cmp['missing_in_doc']}")
        if soft_cmp["extra_in_doc"]:
            print(f" - soft extra_in_doc: {soft_cmp['extra_in_doc']}")
        if not soft_cmp["order_match"]:
            print(" - soft order mismatch")

    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
