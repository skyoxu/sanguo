#!/usr/bin/env python3
"""
sc-acceptance-check: Local, reproducible acceptance gate (Claude Code /acceptance-check equivalent).

This script does NOT call LLM subagents. Instead, it maps the 6 conceptual
"subagents" to deterministic checks already present in this repo, and writes
an auditable report to logs/ci/<YYYY-MM-DD>/sc-acceptance-check/.

Usage (Windows):
  py -3 scripts/sc/acceptance_check.py --task-id 10
  py -3 scripts/sc/acceptance_check.py --task-id 10.3 --godot-bin "%GODOT_BIN%"

Exit codes:
  0  all hard checks passed
  1  at least one hard check failed
  2  invalid usage / missing requirements
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path
from typing import Any

from _acceptance_report import write_markdown_report
from _acceptance_steps import (
    StepResult,
    step_acceptance_refs_validate,
    step_adr_compliance,
    step_architecture_boundary,
    step_build_warnaserror,
    step_contracts_validate,
    step_overlay_validate,
    step_perf_budget,
    step_quality_rules,
    step_security_soft,
    step_task_links_validate,
    step_task_test_refs_validate,
    step_test_quality_soft,
    step_tests_all,
)
from _taskmaster import resolve_triplet
from _unit_metrics import collect_unit_metrics
from _util import ci_dir, repo_root, today_str, write_json


def parse_task_id(value: str | None) -> str | None:
    if not value:
        return None
    s = str(value).strip()
    if not s:
        return None
    # Accept "10" or "10.3" and normalize to master task id ("10").
    return s.split(".", 1)[0]


def main() -> int:
    ap = argparse.ArgumentParser(description="sc-acceptance-check (reproducible acceptance gate)")
    ap.add_argument("--task-id", default=None, help="Taskmaster id (e.g. 10 or 10.3). Default: first status=in-progress task.")
    ap.add_argument("--godot-bin", default=None, help="Godot mono console path (or set env GODOT_BIN)")
    ap.add_argument("--perf-p95-ms", type=int, default=None, help="Enable perf hard gate by parsing [PERF] p95_ms from latest logs/ci/**/headless.log. 0 disables.")
    ap.add_argument("--require-perf", action="store_true", help="(legacy) enable perf hard gate using env PERF_P95_THRESHOLD_MS (or default 20ms)")
    ap.add_argument("--strict-adr-status", action="store_true", help="fail if any referenced ADR is not Accepted")
    ap.add_argument("--strict-test-quality", action="store_true", help="fail if deterministic test-quality heuristics report verdict=Needs Fix")
    ap.add_argument("--strict-quality-rules", action="store_true", help="fail if deterministic quality rules report verdict=Needs Fix")
    ap.add_argument("--require-task-test-refs", action="store_true", help="fail if tasks_back/tasks_gameplay test_refs is empty for the resolved task id")
    ap.add_argument(
        "--only",
        default=None,
        help="Comma-separated step filter (adr,links,overlay,contracts,arch,build,security,quality,rules,tests,perf). Default: all.",
    )
    args = ap.parse_args()

    task_id = parse_task_id(args.task_id)
    try:
        triplet = resolve_triplet(task_id=task_id)
    except Exception as exc:  # noqa: BLE001
        print(f"[sc-acceptance-check] ERROR: failed to resolve task: {exc}")
        return 2

    out_dir = ci_dir("sc-acceptance-check")
    only = None
    if args.only:
        only = {x.strip() for x in str(args.only).split(",") if x.strip()}

    def enabled(key: str) -> bool:
        return True if only is None else (key in only)

    steps: list[StepResult] = []

    if enabled("adr"):
        steps.append(step_adr_compliance(out_dir, triplet, strict_status=bool(args.strict_adr_status)))
    if enabled("links"):
        steps.append(step_task_links_validate(out_dir))
        steps.append(step_task_test_refs_validate(out_dir, triplet, require_non_empty=bool(args.require_task_test_refs)))
        steps.append(step_acceptance_refs_validate(out_dir, triplet))
    if enabled("overlay"):
        steps.append(step_overlay_validate(out_dir, triplet))
    if enabled("contracts"):
        steps.append(step_contracts_validate(out_dir))
    if enabled("arch"):
        steps.append(step_architecture_boundary(out_dir))
    if enabled("build"):
        steps.append(step_build_warnaserror(out_dir))
    if enabled("quality"):
        steps.append(step_test_quality_soft(out_dir, triplet, strict=bool(args.strict_test_quality)))
    if enabled("rules"):
        steps.append(step_quality_rules(out_dir, strict=bool(args.strict_quality_rules)))
    if enabled("security"):
        steps.append(step_security_soft(out_dir))

    godot_bin = args.godot_bin or os.environ.get("GODOT_BIN")
    if enabled("tests"):
        steps.append(step_tests_all(out_dir, godot_bin))

    env_v = os.environ.get("PERF_P95_THRESHOLD_MS")
    env_p95 = int(env_v) if (env_v and env_v.isdigit()) else None
    perf_p95_ms = max(0, int(args.perf_p95_ms)) if args.perf_p95_ms is not None else (env_p95 if env_p95 is not None else (20 if args.require_perf else 0))
    if enabled("perf"):
        steps.append(step_perf_budget(out_dir, max_p95_ms=perf_p95_ms))

    hard_failed = False
    for s in steps:
        if s.name == "security-soft":
            continue
        if s.status == "fail":
            hard_failed = True

    summary: dict[str, Any] = {
        "cmd": "sc-acceptance-check",
        "date": today_str(),
        "task_id": triplet.task_id,
        "title": triplet.master.get("title"),
        "only": args.only,
        "status": "fail" if hard_failed else "ok",
        "steps": [s.__dict__ for s in steps],
        "out_dir": str(out_dir),
    }

    metrics: dict[str, Any] = {}

    tests_step = next((s for s in steps if s.name == "tests-all" and s.log), None)
    tests_log = Path(tests_step.log) if (tests_step and tests_step.log) else None
    unit = collect_unit_metrics(
        tests_all_log=tests_log,
        fallback_unit_dir=(repo_root() / "logs" / "unit" / today_str()),
    )
    if unit:
        metrics["unit"] = unit

    perf_step = next((s for s in steps if s.name == "perf-budget" and isinstance(s.details, dict)), None)
    if perf_step and isinstance(perf_step.details, dict):
        metrics["perf"] = perf_step.details

    if metrics:
        summary["metrics"] = metrics

    write_json(out_dir / "summary.json", summary)
    write_markdown_report(out_dir, triplet, steps, metrics=metrics or None)

    print(f"SC_ACCEPTANCE status={summary['status']} out={out_dir}")
    return 0 if not hard_failed else 1


if __name__ == "__main__":
    raise SystemExit(main())

