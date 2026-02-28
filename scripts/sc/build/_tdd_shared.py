#!/usr/bin/env python3
"""
Shared helpers for scripts/sc/build/tdd.py.
"""

from __future__ import annotations

import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

from _util import repo_root, write_text


def extract_run_dotnet_out_dir(output: str) -> Path | None:
    m = re.search(r"out=([A-Za-z]:\\[^\r\n]+)", output)
    if not m:
        return None
    return Path(m.group(1).strip())


def build_coverage_hotspots_report(coverage_xml: Path) -> list[str]:
    root = ET.fromstring(coverage_xml.read_text(encoding="utf-8"))
    items: list[tuple[float, int, int, float, str, str]] = []
    for cls in root.findall(".//class"):
        filename = (cls.get("filename") or "").replace("/", "\\")
        cls_name = cls.get("name") or ""
        br = float(cls.get("branch-rate") or 0.0)
        lr = float(cls.get("line-rate") or 0.0)
        branches_valid = 0
        branches_covered = 0
        for line in cls.findall(".//line"):
            cc = line.get("condition-coverage")
            if not cc:
                continue
            mm = re.search(r"\((\d+)/(\d+)\)", cc)
            if not mm:
                continue
            branches_covered += int(mm.group(1))
            branches_valid += int(mm.group(2))
        if branches_valid <= 0:
            continue
        items.append((br, branches_valid, branches_covered, lr, filename, cls_name))

    items.sort(key=lambda x: (x[0], -x[1], x[4], x[5]))

    lines: list[str] = []
    lines.append("Lowest branch-rate classes (top 25):")
    for br, bv, bc, lr, filename, cls_name in items[:25]:
        lines.append(
            f"{br*100:6.2f}%  branches {bc}/{bv}  lines {lr*100:6.2f}%  {filename}  ({cls_name})"
        )
    return lines


def write_coverage_hotspots(
    *,
    ci_out_dir: Path,
    run_dotnet_output: str,
) -> dict[str, Any]:
    name = "coverage_hotspots"
    log_path = ci_out_dir / "coverage-hotspots.txt"

    unit_out_dir = extract_run_dotnet_out_dir(run_dotnet_output)
    if not unit_out_dir:
        write_text(log_path, "SKIP: cannot parse unit out_dir from run_dotnet output.\n")
        return {"name": name, "cmd": ["internal"], "rc": 0, "log": str(log_path), "status": "skipped", "reason": "missing:out_dir"}

    coverage_xml = unit_out_dir / "coverage.cobertura.xml"
    unit_summary = unit_out_dir / "summary.json"
    header_lines: list[str] = [
        f"unit_out_dir={unit_out_dir}",
        f"coverage_xml={coverage_xml}",
        f"unit_summary={unit_summary}",
        "",
    ]

    if unit_summary.exists():
        try:
            payload = json.loads(unit_summary.read_text(encoding="utf-8"))
            cov = payload.get("coverage") or {}
            header_lines.insert(
                0,
                f"overall line={cov.get('line_pct', 'n/a')}% branch={cov.get('branch_pct', 'n/a')}% status={payload.get('status', 'n/a')}",
            )
        except Exception:
            pass

    if not coverage_xml.exists():
        write_text(log_path, "\n".join(header_lines + ["SKIP: coverage.cobertura.xml not found."]))
        return {"name": name, "cmd": ["internal"], "rc": 0, "log": str(log_path), "status": "skipped", "reason": "missing:coverage_xml"}

    try:
        report_lines = build_coverage_hotspots_report(coverage_xml)
        write_text(log_path, "\n".join(header_lines + report_lines) + "\n")
        return {"name": name, "cmd": ["internal"], "rc": 0, "log": str(log_path), "status": "ok", "unit_out_dir": str(unit_out_dir)}
    except Exception as ex:
        write_text(log_path, "\n".join(header_lines + [f"FAIL: exception while parsing cobertura: {ex}"]) + "\n")
        return {"name": name, "cmd": ["internal"], "rc": 0, "log": str(log_path), "status": "fail", "unit_out_dir": str(unit_out_dir)}


def snapshot_contract_files() -> set[str]:
    root = repo_root() / "Game.Core" / "Contracts"
    if not root.exists():
        return set()
    return {str(p.relative_to(repo_root())).replace("\\", "/") for p in root.rglob("*.cs")}


def assert_no_new_contract_files(before: set[str], *, allow_changes: bool = False) -> None:
    if allow_changes:
        return
    after = snapshot_contract_files()
    new_files = sorted(after - before)
    if new_files:
        joined = "\n".join(f"- {p}" for p in new_files)
        raise RuntimeError(f"New contract files were created, which is not allowed:\n{joined}")


def check_no_task_red_test_skeletons(out_dir: Path) -> dict[str, Any]:
    name = "check_no_task_red_test_skeletons"
    log_path = out_dir / f"{name}.log"

    tasks_dir = repo_root() / "Game.Core.Tests" / "Tasks"
    if not tasks_dir.exists():
        write_text(log_path, "OK: Game.Core.Tests/Tasks does not exist.\n")
        return {"name": name, "cmd": ["internal"], "rc": 0, "log": str(log_path), "status": "ok"}

    offenders = sorted(tasks_dir.glob("Task*RedTests.cs"))
    if not offenders:
        write_text(log_path, "OK: no Task<id>RedTests.cs files found.\n")
        return {"name": name, "cmd": ["internal"], "rc": 0, "log": str(log_path), "status": "ok"}

    rel_paths = [str(p.relative_to(repo_root())).replace("\\", "/") for p in offenders]
    details = "\n".join(f"- {p}" for p in rel_paths)

    message = (
        "[FAIL] Found task-scoped red test skeleton(s) which must NOT be kept at refactor stage.\n"
        "These files are generated by sc-build tdd --generate-red-test and should be migrated.\n"
        "Fix:\n"
        "  - Move assertions into stable class-scoped tests named {ClassName}Tests.cs (see docs/testing-framework.md)\n"
        "  - Delete Task<id>RedTests.cs after migration\n"
        "Found:\n"
        f"{details}\n"
    )
    write_text(log_path, message)
    return {"name": name, "cmd": ["internal"], "rc": 1, "log": str(log_path), "status": "fail", "offenders": rel_paths}
