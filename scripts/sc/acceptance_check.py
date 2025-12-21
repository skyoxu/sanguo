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
import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from _taskmaster import TaskmasterTriplet, resolve_triplet
from _util import ci_dir, repo_root, run_cmd, today_str, write_json, write_text


ADR_STATUS_RE = re.compile(r"^\s*-?\s*(?:Status|status)\s*:\s*([A-Za-z]+)\s*$", re.MULTILINE)
PERF_METRICS_RE = re.compile(
    r"\[PERF\]\s*frames=(\d+)\s+avg_ms=([0-9]+(?:\.[0-9]+)?)\s+p50_ms=([0-9]+(?:\.[0-9]+)?)\s+p95_ms=([0-9]+(?:\.[0-9]+)?)\s+p99_ms=([0-9]+(?:\.[0-9]+)?)"
)


@dataclass(frozen=True)
class StepResult:
    name: str
    status: str  # ok|fail|skipped
    rc: int | None = None
    cmd: list[str] | None = None
    log: str | None = None
    details: dict[str, Any] | None = None


def parse_task_id(value: str | None) -> str | None:
    if not value:
        return None
    s = str(value).strip()
    if not s:
        return None
    # Accept "10" or "10.3" and normalize to master task id ("10").
    return s.split(".", 1)[0]


def find_adr_file(root: Path, adr_id: str) -> Path | None:
    adr_dir = root / "docs" / "adr"
    if not adr_dir.exists():
        return None
    matches = sorted(adr_dir.glob(f"{adr_id}-*.md"))
    if matches:
        return matches[0]
    exact = adr_dir / f"{adr_id}.md"
    if exact.exists():
        return exact
    return None


def read_adr_status(path: Path) -> str | None:
    text = path.read_text(encoding="utf-8", errors="ignore")
    m = ADR_STATUS_RE.search(text)
    if not m:
        return None
    return m.group(1).strip()


def run_and_capture(out_dir: Path, name: str, cmd: list[str], timeout_sec: int) -> StepResult:
    rc, out = run_cmd(cmd, cwd=repo_root(), timeout_sec=timeout_sec)
    log_path = out_dir / f"{name}.log"
    write_text(log_path, out)
    return StepResult(
        name=name,
        status="ok" if rc == 0 else "fail",
        rc=rc,
        cmd=cmd,
        log=str(log_path),
    )


def step_adr_compliance(out_dir: Path, triplet: TaskmasterTriplet, *, strict_status: bool) -> StepResult:
    root = repo_root()
    adr_refs = triplet.adr_refs()
    arch_refs = triplet.arch_refs()
    overlay = triplet.overlay()

    details: dict[str, Any] = {
        "task_id": triplet.task_id,
        "title": triplet.master.get("title"),
        "adrRefs": adr_refs,
        "archRefs": arch_refs,
        "overlay": overlay,
        "adrStatus": {},
        "errors": [],
        "warnings": [],
        "strict_status": bool(strict_status),
    }

    if not adr_refs:
        details["errors"].append("missing adrRefs in tasks.json (master task)")
    if not arch_refs:
        details["errors"].append("missing archRefs in tasks.json (master task)")

    accepted_count = 0
    for adr in adr_refs:
        adr_path = find_adr_file(root, adr)
        if not adr_path:
            details["errors"].append(f"ADR file missing on disk: {adr}")
            continue
        status = read_adr_status(adr_path)
        details["adrStatus"][adr] = {"path": str(adr_path.relative_to(root)).replace("\\", "/"), "status": status}
        if not status:
            details["warnings"].append(f"ADR status not found (no 'status:' or 'Status:' line): {adr}")
        elif status.lower() == "accepted":
            accepted_count += 1
        else:
            msg = f"ADR not Accepted: {adr} (status={status})"
            if strict_status:
                details["errors"].append(msg)
            else:
                details["warnings"].append(msg)

    if adr_refs and accepted_count == 0:
        details["errors"].append("no Accepted ADR found in adrRefs (require >= 1 Accepted ADR)")

    if overlay:
        overlay_path = root / overlay
        if not overlay_path.exists():
            details["errors"].append(f"overlay path missing on disk: {overlay}")

    ok = len(details["errors"]) == 0
    write_json(out_dir / "adr-compliance.json", details)
    return StepResult(name="adr-compliance", status="ok" if ok else "fail", details=details)


def step_task_links_validate(out_dir: Path) -> StepResult:
    # Validates tasks_back/tasks_gameplay refs (ADR/CH/overlay/depends_on).
    return run_and_capture(
        out_dir,
        name="task-links-validate",
        cmd=["py", "-3", "scripts/python/task_links_validate.py"],
        timeout_sec=300,
    )


def step_overlay_validate(out_dir: Path, triplet: TaskmasterTriplet) -> StepResult:
    primary = run_and_capture(
        out_dir,
        name="validate-task-overlays",
        cmd=["py", "-3", "scripts/python/validate_task_overlays.py"],
        timeout_sec=300,
    )
    overlay = triplet.overlay()
    test_refs = None
    if overlay:
        test_refs = run_and_capture(out_dir, name="validate-test-refs", cmd=["py", "-3", "scripts/python/validate_overlay_test_refs.py", "--overlay", overlay, "--out", str(out_dir / "validate-test-refs.json")], timeout_sec=60)

    ok = primary.status == "ok" and (test_refs is None or test_refs.status == "ok")
    details = {"primary": primary.__dict__, "test_refs": test_refs.__dict__ if test_refs else None, "overlay": overlay}
    write_json(out_dir / "overlay-validate.json", details)
    return StepResult(name="validate-task-overlays", status="ok" if ok else "fail", rc=0 if ok else 1, cmd=primary.cmd, log=primary.log, details=details)


def step_contracts_validate(out_dir: Path) -> StepResult:
    return run_and_capture(
        out_dir,
        name="validate-contracts",
        cmd=["py", "-3", "scripts/python/validate_contracts.py"],
        timeout_sec=300,
    )


def step_architecture_boundary(out_dir: Path) -> StepResult:
    return run_and_capture(out_dir, name="architecture-boundary", cmd=["py", "-3", "scripts/python/check_architecture_boundary.py", "--out", str(out_dir / "architecture-boundary.json")], timeout_sec=60)


def step_build_warnaserror(out_dir: Path) -> StepResult:
    return run_and_capture(
        out_dir,
        name="dotnet-build-warnaserror",
        cmd=["py", "-3", "scripts/sc/build.py", "GodotGame.csproj", "--type", "dev"],
        timeout_sec=1_800,
    )


def step_security_soft(out_dir: Path) -> StepResult:
    # Soft checks: do not block, but record output.
    steps = []
    steps.append(run_and_capture(out_dir, "check-sentry-secrets", ["py", "-3", "scripts/python/check_sentry_secrets.py"], 60))
    steps.append(run_and_capture(out_dir, "check-sanguo-gameloop-contracts", ["py", "-3", "scripts/python/check_sanguo_gameloop_contracts.py"], 60))
    steps.append(run_and_capture(out_dir, "security-soft-scan", ["py", "-3", "scripts/python/security_soft_scan.py", "--out", str(out_dir / "security-soft-scan.json")], 120))
    # Optional: encoding scan (soft)
    steps.append(run_and_capture(out_dir, "check-encoding-since-today", ["py", "-3", "scripts/python/check_encoding.py", "--since-today"], 300))

    # Soft gate: always ok, but include failures in details.
    details = {"steps": [s.__dict__ for s in steps]}
    write_json(out_dir / "security-soft.json", details)
    return StepResult(name="security-soft", status="ok", details=details)

def step_tests_all(out_dir: Path, godot_bin: str | None) -> StepResult:
    cmd = ["py", "-3", "scripts/sc/test.py", "--type", "all"]
    if godot_bin:
        cmd += ["--godot-bin", godot_bin]
    return run_and_capture(out_dir, name="tests-all", cmd=cmd, timeout_sec=1_200)

def find_latest_headless_log() -> Path | None:
    ci_root = repo_root() / "logs" / "ci"
    if not ci_root.exists():
        return None
    candidates = list(ci_root.rglob("headless.log"))
    if not candidates:
        return None
    return max(candidates, key=lambda p: p.stat().st_mtime)

def step_perf_budget(out_dir: Path, *, max_p95_ms: int) -> StepResult:
    if max_p95_ms <= 0:
        details = {"status": "disabled", "max_p95_ms": max_p95_ms}
        write_json(out_dir / "perf-budget.json", details)
        return StepResult(name="perf-budget", status="skipped", details=details)

    root = repo_root()
    headless_log = find_latest_headless_log()
    if not headless_log:
        details = {"error": "no recent headless.log found under logs/ci (run smoke first)", "max_p95_ms": max_p95_ms}
        write_json(out_dir / "perf-budget.json", details)
        return StepResult(name="perf-budget", status="fail", details=details)

    content = headless_log.read_text(encoding="utf-8", errors="ignore")
    matches = list(PERF_METRICS_RE.finditer(content))
    if not matches:
        details = {"error": "no [PERF] metrics found in headless.log", "headless_log": str(headless_log), "max_p95_ms": max_p95_ms}
        write_json(out_dir / "perf-budget.json", details)
        return StepResult(name="perf-budget", status="fail", details=details)

    last = matches[-1]
    frames = int(last.group(1))
    p95_ms = float(last.group(4))
    details = {
        "headless_log": str(headless_log.relative_to(root)).replace("\\", "/"),
        "frames": frames,
        "p95_ms": p95_ms,
        "max_p95_ms": max_p95_ms,
        "budget_status": "pass" if p95_ms <= max_p95_ms else "fail",
        "note": "Hard gate when enabled. Threshold defaults per ADR-0015; override via --perf-p95-ms or env PERF_P95_THRESHOLD_MS.",
    }
    write_json(out_dir / "perf-budget.json", details)
    return StepResult(name="perf-budget", status="ok" if p95_ms <= max_p95_ms else "fail", details=details)

def write_markdown_report(out_dir: Path, task: TaskmasterTriplet, steps: list[StepResult]) -> None:
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
    lines.append("## Steps")
    for s in steps:
        lines.append(f"- {s.name}: {s.status}" + (f" (rc={s.rc})" if s.rc is not None else ""))
        if s.log:
            rel_log = str(Path(s.log).relative_to(repo_root())).replace("\\", "/")
            lines.append(f"  - log: `{rel_log}`")
    lines.append("")
    write_text(out_dir / "report.md", "\n".join(lines) + "\n")

def main() -> int:
    ap = argparse.ArgumentParser(description="sc-acceptance-check (reproducible acceptance gate)")
    ap.add_argument("--task-id", default=None, help="Taskmaster id (e.g. 10 or 10.3). Default: first status=in-progress task.")
    ap.add_argument("--godot-bin", default=None, help="Godot mono console path (or set env GODOT_BIN)")
    ap.add_argument("--perf-p95-ms", type=int, default=None, help="Enable perf hard gate by parsing [PERF] p95_ms from latest logs/ci/**/headless.log. 0 disables.")
    ap.add_argument("--require-perf", action="store_true", help="(legacy) enable perf hard gate using env PERF_P95_THRESHOLD_MS (or default 20ms)")
    ap.add_argument("--strict-adr-status", action="store_true", help="fail if any referenced ADR is not Accepted")
    ap.add_argument(
        "--only",
        default=None,
        help="Comma-separated step filter (adr,links,overlay,contracts,arch,build,security,tests,perf). Default: all.",
    )
    args = ap.parse_args()

    task_id = parse_task_id(args.task_id)
    try:
        triplet = resolve_triplet(task_id=task_id)
    except Exception as exc:  # noqa: BLE001
        print(f"[sc-acceptance-check] ERROR: failed to resolve task: {exc}")
        return 2

    out_dir = ci_dir("sc-acceptance-check")
    only = set((args.only or "").split(",")) if args.only else None

    def enabled(key: str) -> bool:
        return True if only is None else (key in only)

    steps: list[StepResult] = []

    # 1) ADR compliance (hard)
    if enabled("adr"):
        steps.append(step_adr_compliance(out_dir, triplet, strict_status=bool(args.strict_adr_status)))

    # 2) Task links (hard)
    if enabled("links"):
        steps.append(step_task_links_validate(out_dir))

    # 3) Overlay schema (hard)
    if enabled("overlay"):
        steps.append(step_overlay_validate(out_dir, triplet))

    # 4) Contracts <-> overlay refs (hard)
    if enabled("contracts"):
        steps.append(step_contracts_validate(out_dir))

    # 5) Architecture boundary (hard)
    if enabled("arch"):
        steps.append(step_architecture_boundary(out_dir))

    # 6) Build (hard)
    if enabled("build"):
        steps.append(step_build_warnaserror(out_dir))

    # Security (soft)
    if enabled("security"):
        steps.append(step_security_soft(out_dir))

    # Tests (hard)
    godot_bin = args.godot_bin or os.environ.get("GODOT_BIN")
    if enabled("tests"):
        steps.append(step_tests_all(out_dir, godot_bin))

    env_v = os.environ.get("PERF_P95_THRESHOLD_MS")
    env_p95 = int(env_v) if (env_v and env_v.isdigit()) else None
    perf_p95_ms = max(0, int(args.perf_p95_ms)) if args.perf_p95_ms is not None else (env_p95 if env_p95 is not None else (20 if args.require_perf else 0))

    # Perf (hard gate when enabled)
    if enabled("perf"):
        steps.append(step_perf_budget(out_dir, max_p95_ms=perf_p95_ms))

    hard_failed = False
    for s in steps:
        if s.name == "security-soft":
            continue
        if s.status == "fail":
            hard_failed = True

    summary = {
        "cmd": "sc-acceptance-check",
        "task_id": triplet.task_id,
        "title": triplet.master.get("title"),
        "status": "fail" if hard_failed else "ok",
        "steps": [s.__dict__ for s in steps],
        "out_dir": str(out_dir),
    }
    write_json(out_dir / "summary.json", summary)
    write_markdown_report(out_dir, triplet, steps)

    print(f"SC_ACCEPTANCE status={summary['status']} out={out_dir}")
    return 0 if not hard_failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
