#!/usr/bin/env python3
"""
Acceptance-check artifact discovery + prompt-friendly summarization.

Goal:
  Reduce LLM review hallucination by injecting deterministic evidence
  (test/coverage/perf gates, overlay validation, security soft scan counts)
  into sc-llm-review prompts.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from _util import repo_root, today_str


def _to_posix(path: Path) -> str:
    return str(path).replace("\\", "/")


def find_latest_acceptance_dir(*, task_id: str | None) -> Path | None:
    ci_root = repo_root() / "logs" / "ci"
    if not ci_root.exists():
        return None

    candidates: list[Path] = []
    today_dir = ci_root / today_str()
    if today_dir.exists():
        for p in [today_dir / "sc-acceptance-check", *today_dir.glob("sc-acceptance-check-task-*")]:
            if (p / "summary.json").is_file():
                candidates.append(p)

    if not candidates:
        for summary in ci_root.rglob("summary.json"):
            parent = summary.parent
            if parent.name.startswith("sc-acceptance-check"):
                candidates.append(parent)

    best: Path | None = None
    best_mtime = -1.0
    for p in candidates:
        summary = p / "summary.json"
        try:
            data = json.loads(summary.read_text(encoding="utf-8"))
        except Exception:
            continue
        if task_id and str(data.get("task_id") or "") != str(task_id):
            continue
        try:
            mtime = summary.stat().st_mtime
        except OSError:
            mtime = 0.0
        if mtime > best_mtime:
            best_mtime = mtime
            best = p
    return best


def _read_json(path: Path) -> dict[str, Any] | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    return data if isinstance(data, dict) else None


def build_acceptance_evidence(*, task_id: str | None, max_chars: int = 4000) -> tuple[str, dict[str, Any]]:
    """
    Returns (markdown_snippet, meta).
    """
    acc_dir = find_latest_acceptance_dir(task_id=task_id)
    if not acc_dir:
        return "", {"status": "missing"}

    root = repo_root()
    summary_path = acc_dir / "summary.json"
    summary = _read_json(summary_path) or {}
    rel_dir = _to_posix(acc_dir.relative_to(root))

    status = str(summary.get("status") or "unknown")
    steps = summary.get("steps") if isinstance(summary.get("steps"), list) else []

    failing_steps: list[str] = []
    for s in steps:
        if not isinstance(s, dict):
            continue
        name = str(s.get("name") or "")
        st = str(s.get("status") or "")
        if name == "security-soft":
            continue
        if st == "fail":
            failing_steps.append(name)

    metrics = summary.get("metrics") if isinstance(summary.get("metrics"), dict) else {}
    unit = metrics.get("unit") if isinstance(metrics.get("unit"), dict) else {}
    cov = unit.get("coverage") if isinstance(unit.get("coverage"), dict) else {}
    tests = unit.get("tests") if isinstance(unit.get("tests"), dict) else {}
    perf = metrics.get("perf") if isinstance(metrics.get("perf"), dict) else {}

    findings_total = None
    soft_scan = acc_dir / "security-soft-scan.json"
    soft_scan_data = _read_json(soft_scan)
    if isinstance(soft_scan_data, dict):
        counts = soft_scan_data.get("counts")
        if isinstance(counts, dict):
            findings_total = counts.get("total")

    lines: list[str] = []
    lines.append("## Acceptance Evidence (deterministic)")
    lines.append(f"- source_dir: `{rel_dir}`")
    lines.append(f"- status: {status}")
    if failing_steps:
        lines.append(f"- failing_steps: {', '.join(sorted(set(failing_steps)))}")

    if tests:
        passed = tests.get("passed")
        total = tests.get("total")
        failed = tests.get("failed")
        if passed is not None and total is not None:
            lines.append(f"- unit_tests: passed={passed}/{total} failed={failed}")
    if cov and cov.get("line_pct") is not None and cov.get("branch_pct") is not None:
        lines.append(f"- coverage: lines={cov.get('line_pct')}% branches={cov.get('branch_pct')}% (threshold_ok={bool(unit.get('threshold_ok'))})")
    if perf and perf.get("budget_status") in {"pass", "fail"}:
        lines.append(f"- perf_budget: p95_ms={perf.get('p95_ms')} <= {perf.get('max_p95_ms')} (frames={perf.get('frames')})")
    if findings_total is not None:
        lines.append(f"- security_soft_findings: total={findings_total}")

    # Pointers for human triage (do not inline huge logs).
    lines.append("- logs:")
    lines.append(f"  - report: `{_to_posix((acc_dir / 'report.md').relative_to(root))}`")
    lines.append(f"  - summary: `{_to_posix(summary_path.relative_to(root))}`")

    md = "\n".join(lines).strip() + "\n"
    if len(md) > max_chars:
        md = md[: max_chars - 3] + "...\n"

    meta = {
        "status": "ok",
        "acceptance_dir": rel_dir,
        "acceptance_status": status,
        "failing_steps": failing_steps,
    }
    return md, meta

