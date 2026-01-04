#!/usr/bin/env python3
"""
Acceptance check report writer (Markdown).

Kept separate from the CLI entrypoint to keep script sizes small.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from _acceptance_steps import StepResult
from _taskmaster import TaskmasterTriplet
from _util import repo_root, today_str, write_text


def write_markdown_report(out_dir: Path, task: TaskmasterTriplet, steps: list[StepResult], *, metrics: dict[str, Any] | None = None) -> None:
    lines: list[str] = []
    lines.append("# Acceptance Check Report")
    lines.append("")
    lines.append(f"- date: {today_str()}")
    lines.append(f"- task_id: {task.task_id}")
    lines.append(f"- title: {task.master.get('title')}")
    lines.append(f"- tasks_json: `{task.tasks_json_path}`")
    lines.append(f"- tasks_back: `{task.tasks_back_path}`")
    lines.append(f"- tasks_gameplay: `{task.tasks_gameplay_path}`")
    if task.taskdoc_path:
        lines.append(f"- taskdoc: `{task.taskdoc_path}`")
    if task.overlay():
        lines.append(f"- overlay: `{task.overlay()}`")
    lines.append("")

    if metrics:
        lines.append("## Key Metrics")
        unit = metrics.get("unit") if isinstance(metrics.get("unit"), dict) else None
        if unit:
            cov = unit.get("coverage") if isinstance(unit.get("coverage"), dict) else {}
            tests = unit.get("tests") if isinstance(unit.get("tests"), dict) else {}
            if tests:
                total = tests.get("total")
                passed = tests.get("passed")
                failed = tests.get("failed")
                not_executed = tests.get("notExecuted")
                parts = []
                if passed is not None and total is not None:
                    parts.append(f"passed={passed}/{total}")
                if failed is not None:
                    parts.append(f"failed={failed}")
                if not_executed is not None:
                    parts.append(f"notExecuted={not_executed}")
                lines.append(f"- unit tests: {', '.join(parts)}")
            if cov:
                lp = cov.get("line_pct")
                bp = cov.get("branch_pct")
                lines.append(f"- coverage: lines={lp}% branches={bp}% (threshold_ok={bool(unit.get('threshold_ok'))})")

        perf = metrics.get("perf") if isinstance(metrics.get("perf"), dict) else None
        if perf and perf.get("p95_ms") is not None:
            if perf.get("budget_status") in {"pass", "fail"}:
                lines.append(f"- perf: p95_ms={perf.get('p95_ms')} <= {perf.get('max_p95_ms')} (frames={perf.get('frames')})")
            else:
                lines.append(f"- perf: p95_ms={perf.get('p95_ms')} (frames={perf.get('frames')}, gate={perf.get('budget_status')})")
        lines.append("")

    lines.append("## Steps")
    for s in steps:
        lines.append(f"- {s.name}: {s.status}" + (f" (rc={s.rc})" if s.rc is not None else ""))
        if s.log:
            rel_log = str(Path(s.log).relative_to(repo_root())).replace("\\", "/")
            lines.append(f"  - log: `{rel_log}`")
    lines.append("")
    write_text(out_dir / "report.md", "\n".join(lines) + "\n")

