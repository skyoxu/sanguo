#!/usr/bin/env python3
"""
sc-build tdd: TDD gatekeeper (non-generative).

This script does NOT synthesize business logic. It enforces a repeatable
red/green/refactor loop with logs under logs/ci/<date>/.

Usage (Windows):
  py -3 scripts/sc/build/tdd.py --stage green
  py -3 scripts/sc/build/tdd.py --stage red --generate-red-test
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _bootstrap_imports() -> None:
    # scripts/sc/build/tdd.py -> scripts/sc/build -> scripts/sc and scripts/python
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "python"))


_bootstrap_imports()

from _delivery_profile import (  # noqa: E402
    default_security_profile_for_delivery,
    known_delivery_profiles,
    profile_test_defaults,
    resolve_delivery_profile,
)
from _security_profile import resolve_security_profile  # noqa: E402
from solution_target import resolve_test_solution_arg  # noqa: E402
from _taskmaster import resolve_triplet  # noqa: E402
from _util import ci_dir, repo_root, run_cmd, today_str, write_json, write_text  # noqa: E402
from _tdd_shared import (  # noqa: E402
    assert_no_new_contract_files,
    check_no_task_red_test_skeletons,
    snapshot_contract_files,
    write_coverage_hotspots,
)

DELIVERY_PROFILE_CHOICES = tuple(sorted(known_delivery_profiles()))


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _finalize_summary(summary: dict[str, Any], *, start_monotonic: float) -> dict[str, Any]:
    summary["finished_at"] = _utc_now_iso()
    summary["elapsed_sec"] = round(max(0.0, time.monotonic() - start_monotonic), 3)
    return summary


def resolve_tdd_runtime(*, delivery_profile: str | None, security_profile: str | None, no_coverage_gate: bool) -> dict[str, Any]:
    resolved_delivery_profile = resolve_delivery_profile(delivery_profile)
    resolved_security_profile = resolve_security_profile(
        security_profile or default_security_profile_for_delivery(resolved_delivery_profile)
    )
    test_defaults = profile_test_defaults(resolved_delivery_profile)
    return {
        "delivery_profile": resolved_delivery_profile,
        "security_profile": resolved_security_profile,
        "coverage_gate": bool(test_defaults.get("coverage_gate", True)) and not bool(no_coverage_gate),
        "coverage_lines_min": max(0, int(test_defaults.get("coverage_lines_min", 90) or 0)),
        "coverage_branches_min": max(0, int(test_defaults.get("coverage_branches_min", 85) or 0)),
    }


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description="sc-build tdd gatekeeper")
    ap.add_argument("--stage", choices=["red", "green", "refactor"], default="green")
    ap.add_argument("--task-id", default=None, help="task id; defaults to first status=in-progress in tasks.json")
    ap.add_argument(
        "--solution",
        default="auto",
        help="test solution target; default auto prefers a solution that contains test projects",
    )
    ap.add_argument("--configuration", default="Debug")
    ap.add_argument(
        "--delivery-profile",
        default=None,
        choices=DELIVERY_PROFILE_CHOICES,
        help="Delivery profile (default: env DELIVERY_PROFILE or fast-ship).",
    )
    ap.add_argument(
        "--security-profile",
        default=None,
        choices=["strict", "host-safe"],
        help="Security profile override (default derives from delivery profile).",
    )
    ap.add_argument(
        "--green-scope",
        choices=["task", "all"],
        default="task",
        help="green stage test scope: task-scoped (default) or all tests",
    )
    ap.add_argument("--generate-red-test", action="store_true", help="create a failing test skeleton if missing")
    ap.add_argument("--no-coverage-gate", action="store_true", help="do not enforce default coverage thresholds")
    ap.add_argument(
        "--allow-contract-changes",
        action="store_true",
        help="allow creating new files under Game.Core/Contracts during this TDD stage",
    )
    return ap


def default_task_test_path(task_id: str) -> Path:
    return repo_root() / "Game.Core.Tests" / "Tasks" / f"Task{task_id}RedTests.cs"


def ensure_red_test_exists(task_id: str, title: str, *, allow_create: bool, out_dir: Path) -> Path | None:
    target = default_task_test_path(task_id)
    if target.exists():
        return target
    if not allow_create:
        return None

    target.parent.mkdir(parents=True, exist_ok=True)
    class_name = f"Task{task_id}RedTests"
    safe_title = " ".join(str(title).split())
    content = f"""using FluentAssertions;
using Xunit;

namespace Game.Core.Tests.Tasks;

public class {class_name}
{{
    [Fact]
    public void Red_IsFailingUntilTaskIsImplemented()
    {{
        // This test is intentionally failing to start a TDD cycle.
        true.Should().BeFalse(\"Task {task_id} not implemented yet: {safe_title}\");
    }}
}}
"""
    target.write_text(content, encoding="utf-8")
    write_text(out_dir / "generated-red-test.txt", str(target))
    return target


def run_dotnet_test_filtered(task_id: str, *, solution: str, configuration: str, out_dir: Path) -> dict[str, Any]:
    # Best-effort filter to keep the red stage scoped.
    filter_expr = f"FullyQualifiedName~Game.Core.Tests.Tasks.Task{task_id}"
    cmd = ["dotnet", "test", solution, "-c", configuration, "--filter", filter_expr]
    rc, out = run_cmd(cmd, cwd=repo_root(), timeout_sec=900)
    log_path = out_dir / "dotnet-test-filtered.log"
    write_text(log_path, out)
    return {"name": "dotnet-test-filtered", "cmd": cmd, "rc": rc, "log": str(log_path), "filter": filter_expr}


def _collect_task_test_refs(triplet: Any) -> list[str]:
    refs: list[str] = []
    for view in (triplet.back, triplet.gameplay):
        if not isinstance(view, dict):
            continue
        test_refs = view.get("test_refs")
        if not isinstance(test_refs, list):
            continue
        for ref in test_refs:
            ref_s = str(ref or "").strip()
            if not ref_s:
                continue
            if not ref_s.lower().endswith(".cs"):
                continue
            refs.append(ref_s.replace("\\", "/"))
    # preserve order but unique
    seen: set[str] = set()
    uniq: list[str] = []
    for r in refs:
        key = r.lower()
        if key in seen:
            continue
        seen.add(key)
        uniq.append(r)
    return uniq


def _class_token_from_test_ref(test_ref: str) -> str | None:
    name = Path(test_ref).stem.strip()
    if not name:
        return None
    if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name) is None:
        return None
    return name


def _build_green_filter_expr(*, task_id: str, triplet: Any) -> tuple[str, list[str]]:
    refs = _collect_task_test_refs(triplet)
    tokens: list[str] = []
    for ref in refs:
        token = _class_token_from_test_ref(ref)
        if token:
            tokens.append(token)

    # Fallback to task-scoped namespace/class naming.
    if not tokens:
        tokens = [f"Task{task_id}"]

    # `dotnet test --filter` uses `|` as OR.
    terms = [f"FullyQualifiedName~{token}" for token in tokens]
    return "|".join(terms), refs


def run_sc_analyze_task_context(*, task_id: str, out_dir: Path) -> dict[str, Any]:
    # Ensure logs/ci/<date>/sc-analyze/task_context.json exists and is fresh enough for this TDD stage.
    # We intentionally use the repo's deterministic analyzer (no LLM).
    cmd = [
        "py",
        "-3",
        "scripts/sc/analyze.py",
        "--task-id",
        str(task_id),
        "--focus",
        "all",
        "--depth",
        "quick",
        "--format",
        "json",
    ]
    rc, out = run_cmd(cmd, cwd=repo_root(), timeout_sec=900)
    log_path = out_dir / "sc-analyze.log"
    write_text(log_path, out)
    return {"name": "sc-analyze", "cmd": cmd, "rc": rc, "log": str(log_path), "status": "ok" if rc == 0 else "fail"}


def _read_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def _normalize_task_id(value: Any) -> str:
    return str(value or "").split(".", 1)[0].strip()


def _find_latest_red_first_summary(task_id: str) -> tuple[Path | None, dict[str, Any]]:
    logs_root = repo_root() / "logs" / "ci"
    if not logs_root.exists():
        return None, {}
    candidates = sorted(
        [item for item in logs_root.glob(f"*/sc-llm-acceptance-tests/summary-{task_id}.json") if item.is_file()],
        key=lambda item: item.stat().st_mtime,
        reverse=True,
    )
    for candidate in candidates:
        payload = _read_json(candidate)
        if _normalize_task_id(payload.get("task_id")) != task_id:
            continue
        return candidate, payload
    return None, {}


def _find_latest_green_summary(task_id: str) -> tuple[Path | None, dict[str, Any]]:
    logs_root = repo_root() / "logs" / "ci"
    if not logs_root.exists():
        return None, {}
    candidates = sorted(
        [item for item in logs_root.glob("*/sc-build-tdd/summary.json") if item.is_file()],
        key=lambda item: item.stat().st_mtime,
        reverse=True,
    )
    for candidate in candidates:
        payload = _read_json(candidate)
        if str(payload.get("stage") or "").strip().lower() != "green":
            continue
        task_info = payload.get("task")
        summary_task_id = _normalize_task_id(task_info.get("task_id")) if isinstance(task_info, dict) else ""
        if summary_task_id != task_id:
            continue
        return candidate, payload
    return None, {}


def validate_green_red_prerequisite(*, task_id: str, out_dir: Path) -> dict[str, Any]:
    summary_path, payload = _find_latest_red_first_summary(task_id)
    errors: list[str] = []
    failed_refs: list[str] = []
    if summary_path is None:
        errors.append("missing red-first summary: run workflow chapter 6.4 first")
    else:
        if str(payload.get("tdd_stage") or "").strip().lower() != "red-first":
            errors.append("latest acceptance test summary is not red-first")
        results = payload.get("results")
        if isinstance(results, list):
            for item in results:
                if not isinstance(item, dict):
                    continue
                if str(item.get("status") or "").strip().lower() == "fail":
                    failed_refs.append(str(item.get("ref") or "").strip())
        if failed_refs:
            errors.append(f"red-first summary contains failed refs: {len(failed_refs)}")
        created = int(payload.get("created") or 0)
        if created > 0:
            red_verify = payload.get("red_verify")
            red_status = str(red_verify.get("status") or "").strip().lower() if isinstance(red_verify, dict) else ""
            if red_status != "ok":
                errors.append("red-first created new tests but red_verify.status is not ok")

    log_path = out_dir / "validate_green_red_prerequisite.log"
    lines = [
        f"task_id={task_id}",
        f"summary_path={summary_path if summary_path is not None else ''}",
        f"errors={len(errors)}",
    ]
    for ref in failed_refs[:30]:
        lines.append(f"FAILED_REF: {ref}")
    for err in errors:
        lines.append(f"ERROR: {err}")
    write_text(log_path, "\n".join(lines) + "\n")
    return {
        "name": "validate_green_red_prerequisite",
        "cmd": ["internal:validate_green_red_prerequisite"],
        "rc": 0 if not errors else 1,
        "log": str(log_path),
        "status": "ok" if not errors else "fail",
        "summary_path": str(summary_path) if summary_path is not None else "",
        "errors": errors,
    }


def validate_refactor_green_prerequisite(*, task_id: str, out_dir: Path) -> dict[str, Any]:
    summary_path, payload = _find_latest_green_summary(task_id)
    errors: list[str] = []
    if summary_path is None:
        errors.append("missing green summary: run workflow chapter 6.5 first")
    else:
        if str(payload.get("status") or "").strip().lower() != "ok":
            errors.append(f"latest green summary status is not ok: {payload.get('status')}")

    log_path = out_dir / "validate_refactor_green_prerequisite.log"
    lines = [
        f"task_id={task_id}",
        f"summary_path={summary_path if summary_path is not None else ''}",
        f"errors={len(errors)}",
    ]
    for err in errors:
        lines.append(f"ERROR: {err}")
    write_text(log_path, "\n".join(lines) + "\n")
    return {
        "name": "validate_refactor_green_prerequisite",
        "cmd": ["internal:validate_refactor_green_prerequisite"],
        "rc": 0 if not errors else 1,
        "log": str(log_path),
        "status": "ok" if not errors else "fail",
        "summary_path": str(summary_path) if summary_path is not None else "",
        "errors": errors,
    }


def validate_task_context_required_fields(*, task_id: str, stage: str, out_dir: Path) -> dict[str, Any]:
    # Hard gate: TDD stages MUST use the full triplet semantics (master/back/gameplay) captured by sc-analyze.
    ctx_path = repo_root() / "logs" / "ci" / today_str() / "sc-analyze" / f"task_context.{task_id}.json"

    cmd = [
        "py",
        "-3",
        "scripts/python/validate_task_context_required_fields.py",
        "--task-id",
        str(task_id),
        "--stage",
        str(stage),
        "--context",
        str(ctx_path),
        "--out",
        str(out_dir / "task-context-required.json"),
    ]
    rc, out = run_cmd(cmd, cwd=repo_root(), timeout_sec=60)
    log_path = out_dir / "validate-task-context-required.log"
    write_text(log_path, out)
    return {"name": "validate_task_context_required_fields", "cmd": cmd, "rc": rc, "log": str(log_path), "status": "ok" if rc == 0 else "fail"}


def run_task_preflight(*, triplet: Any, out_dir: Path) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []

    task_id = str(getattr(triplet, "task_id", "") or "").strip()
    master = dict(getattr(triplet, "master", {}) or {})
    back = dict(getattr(triplet, "back", {}) or {})
    gameplay = dict(getattr(triplet, "gameplay", {}) or {})

    if not task_id:
        errors.append("missing task_id in triplet")
    if not str(master.get("title") or "").strip():
        errors.append("missing master.title")
    if not isinstance(back.get("acceptance"), list):
        warnings.append("missing back.acceptance list")
    if not isinstance(gameplay.get("acceptance"), list):
        warnings.append("missing gameplay.acceptance list")

    payload = {
        "task_id": task_id,
        "errors": errors,
        "warnings": warnings,
        "status": "ok" if not errors else "fail",
    }
    out_json = out_dir / "task-preflight.json"
    write_json(out_json, payload)
    log_path = out_dir / "task-preflight.log"
    if errors:
        write_text(log_path, "\n".join([f"ERROR: {item}" for item in errors]) + "\n")
        return {
            "name": "task_preflight",
            "cmd": ["internal:task_preflight"],
            "rc": 1,
            "log": str(log_path),
            "status": "fail",
            "errors": errors,
            "warnings": warnings,
            "out": str(out_json),
        }

    lines = [f"OK: task_id={task_id}", f"warnings={len(warnings)}"]
    lines.extend([f"WARN: {item}" for item in warnings])
    write_text(log_path, "\n".join(lines) + "\n")
    return {
        "name": "task_preflight",
        "cmd": ["internal:task_preflight"],
        "rc": 0,
        "log": str(log_path),
        "status": "ok",
        "warnings": warnings,
        "out": str(out_json),
    }


def run_green_gate(
    *,
    task_id: str,
    triplet: Any,
    solution: str,
    configuration: str,
    out_dir: Path,
    coverage_gate: bool,
    coverage_lines_min: int,
    coverage_branches_min: int,
    green_scope: str,
) -> dict[str, Any]:
    prev_lines_min = os.environ.get("COVERAGE_LINES_MIN")
    prev_branches_min = os.environ.get("COVERAGE_BRANCHES_MIN")
    prev_gate_mode = os.environ.get("COVERAGE_GATE_MODE")

    coverage_gate_enabled = (green_scope == "all") and bool(coverage_gate)
    if coverage_gate_enabled:
        os.environ["COVERAGE_LINES_MIN"] = str(max(0, int(coverage_lines_min)))
        os.environ["COVERAGE_BRANCHES_MIN"] = str(max(0, int(coverage_branches_min)))
        os.environ["COVERAGE_GATE_MODE"] = "hard"
    else:
        # Task-scoped green should validate correctness quickly without global denominator drift.
        os.environ.pop("COVERAGE_LINES_MIN", None)
        os.environ.pop("COVERAGE_BRANCHES_MIN", None)
        os.environ["COVERAGE_GATE_MODE"] = "soft"

    cmd = ["py", "-3", "scripts/python/run_dotnet.py", "--solution", solution, "--configuration", configuration]
    filter_expr = ""
    filter_refs: list[str] = []
    if green_scope == "task":
        filter_expr, filter_refs = _build_green_filter_expr(task_id=task_id, triplet=triplet)
        cmd.extend(["--filter", filter_expr])

    try:
        inner_timeout_ms = int(os.environ.get("DOTNET_TEST_TIMEOUT_MS", "1800000") or "1800000")
    except ValueError:
        inner_timeout_ms = 1_800_000
    inner_timeout_ms = max(60_000, inner_timeout_ms)
    outer_timeout_sec = max(1_800, int(inner_timeout_ms / 1000) + 120)

    try:
        rc, out = run_cmd(cmd, cwd=repo_root(), timeout_sec=outer_timeout_sec)
    finally:
        if prev_lines_min is None:
            os.environ.pop("COVERAGE_LINES_MIN", None)
        else:
            os.environ["COVERAGE_LINES_MIN"] = prev_lines_min
        if prev_branches_min is None:
            os.environ.pop("COVERAGE_BRANCHES_MIN", None)
        else:
            os.environ["COVERAGE_BRANCHES_MIN"] = prev_branches_min
        if prev_gate_mode is None:
            os.environ.pop("COVERAGE_GATE_MODE", None)
        else:
            os.environ["COVERAGE_GATE_MODE"] = prev_gate_mode
    log_path = out_dir / "run_dotnet.log"
    write_text(log_path, out)
    return {
        "name": "run_dotnet",
        "cmd": cmd,
        "rc": rc,
        "log": str(log_path),
        "stdout": out,
        "inner_timeout_ms": inner_timeout_ms,
        "outer_timeout_sec": outer_timeout_sec,
        "scope": green_scope,
        "coverage_gate_enabled": coverage_gate_enabled,
        "filter": filter_expr,
        "test_refs": filter_refs,
    }


def run_refactor_checks(out_dir: Path, *, task_id: str) -> list[dict[str, Any]]:
    steps: list[dict[str, Any]] = []
    steps.append(check_no_task_red_test_skeletons(out_dir))
    # Hard gate: every task must have non-empty test_refs evidence in both task views.
    # This is enforced at refactor stage, when test files are expected to be stable.
    test_refs_script = repo_root() / "scripts" / "python" / "validate_task_test_refs.py"
    test_refs_log = out_dir / "validate_task_test_refs.log"
    if not test_refs_script.exists():
        write_text(
            test_refs_log,
            "FAIL: missing scripts/python/validate_task_test_refs.py\n"
            "Fix:\n"
            "  - git pull (or restore the file)\n",
        )
        steps.append(
            {
                "name": "validate_task_test_refs",
                "cmd": ["py", "-3", "scripts/python/validate_task_test_refs.py"],
                "rc": 1,
                "log": str(test_refs_log),
                "status": "fail",
                "reason": "missing:validate_task_test_refs.py",
            }
        )
    else:
        cmd = [
            "py",
            "-3",
            "scripts/python/validate_task_test_refs.py",
            "--task-id",
            str(task_id),
            "--out",
            str(out_dir / "task-test-refs.json"),
            "--require-non-empty",
        ]
        rc, out = run_cmd(cmd, cwd=repo_root(), timeout_sec=60)
        write_text(test_refs_log, out)
        steps.append(
            {
                "name": "validate_task_test_refs",
                "cmd": cmd,
                "rc": rc,
                "log": str(test_refs_log),
                "status": "ok" if rc == 0 else "fail",
            }
        )

    # Hard gate: acceptance items must map to deterministic evidence via "Refs:" and be included in test_refs.
    acceptance_cmd = [
        "py",
        "-3",
        "scripts/python/validate_acceptance_refs.py",
        "--task-id",
        str(task_id),
        "--stage",
        "refactor",
        "--out",
        str(out_dir / "acceptance-refs.json"),
    ]
    acceptance_rc, acceptance_out = run_cmd(acceptance_cmd, cwd=repo_root(), timeout_sec=60)
    acceptance_log = out_dir / "validate_acceptance_refs.log"
    write_text(acceptance_log, acceptance_out)
    steps.append(
        {
            "name": "validate_acceptance_refs",
            "cmd": acceptance_cmd,
            "rc": acceptance_rc,
            "log": str(acceptance_log),
            "status": "ok" if acceptance_rc == 0 else "fail",
        }
    )

    # Hard gate: referenced tests must contain ACC:T<id>.<n> anchors for each acceptance item.
    anchors_cmd = [
        "py",
        "-3",
        "scripts/python/validate_acceptance_anchors.py",
        "--task-id",
        str(task_id),
        "--stage",
        "refactor",
        "--out",
        str(out_dir / "acceptance-anchors.json"),
    ]
    anchors_rc, anchors_out = run_cmd(anchors_cmd, cwd=repo_root(), timeout_sec=60)
    anchors_log = out_dir / "validate_acceptance_anchors.log"
    write_text(anchors_log, anchors_out)
    steps.append(
        {
            "name": "validate_acceptance_anchors",
            "cmd": anchors_cmd,
            "rc": anchors_rc,
            "log": str(anchors_log),
            "status": "ok" if anchors_rc == 0 else "fail",
        }
    )
    candidates = [
        ("check_test_naming", ["py", "-3", "scripts/python/check_test_naming.py", "--task-id", str(task_id), "--style", "should_when"], "scripts/python/check_test_naming.py"),
        ("check_tasks_all_refs", ["py", "-3", "scripts/python/check_tasks_all_refs.py"], "scripts/python/check_tasks_all_refs.py"),
        ("validate_contracts", ["py", "-3", "scripts/python/validate_contracts.py"], "scripts/python/validate_contracts.py"),
    ]
    for name, cmd, requires in candidates:
        log_path = out_dir / f"{name}.log"
        if not (repo_root() / requires).exists():
            write_text(log_path, f"SKIP missing: {requires}\n")
            steps.append({"name": name, "cmd": cmd, "rc": 0, "log": str(log_path), "status": "skipped", "reason": f"missing:{requires}"})
            continue

        rc, out = run_cmd(cmd, cwd=repo_root(), timeout_sec=900)
        write_text(log_path, out)
        steps.append({"name": name, "cmd": cmd, "rc": rc, "log": str(log_path), "status": "ok" if rc == 0 else "fail"})
    return steps


def main() -> int:
    start_monotonic = time.monotonic()
    args = build_parser().parse_args()
    runtime = resolve_tdd_runtime(
        delivery_profile=args.delivery_profile,
        security_profile=args.security_profile,
        no_coverage_gate=bool(args.no_coverage_gate),
    )
    os.environ["DELIVERY_PROFILE"] = str(runtime["delivery_profile"])
    os.environ["SECURITY_PROFILE"] = str(runtime["security_profile"])
    out_dir = ci_dir("sc-build-tdd")

    before_contracts = snapshot_contract_files()

    summary: dict[str, Any] = {
        "cmd": "sc-build-tdd",
        "stage": args.stage,
        "delivery_profile": str(runtime["delivery_profile"]),
        "security_profile": str(runtime["security_profile"]),
        "allow_contract_changes": bool(args.allow_contract_changes),
        "status": "fail",
        "started_at": _utc_now_iso(),
        "steps": [],
    }
    resolved_solution = resolve_test_solution_arg(args.solution, root=repo_root())
    summary["solution"] = resolved_solution

    triplet = resolve_triplet(task_id=args.task_id)
    summary["task"] = {
        "task_id": triplet.task_id,
        "title": triplet.master.get("title"),
        "status": triplet.master.get("status"),
        "adrRefs": triplet.adr_refs(),
        "archRefs": triplet.arch_refs(),
        "overlay": triplet.overlay(),
        "taskdoc": triplet.taskdoc_path,
    }

    if args.stage == "red":
        preflight_step = run_task_preflight(triplet=triplet, out_dir=out_dir)
        summary["steps"].append(preflight_step)
        if preflight_step["rc"] != 0:
            write_json(out_dir / "summary.json", _finalize_summary(summary, start_monotonic=start_monotonic))
            print(f"SC_BUILD_TDD status=fail out={out_dir}")
            assert_no_new_contract_files(before_contracts, allow_changes=bool(args.allow_contract_changes))
            return 1
        summary["steps"].append(run_sc_analyze_task_context(task_id=triplet.task_id, out_dir=out_dir))
        ctx_step = validate_task_context_required_fields(task_id=triplet.task_id, stage="red", out_dir=out_dir)
        summary["steps"].append(ctx_step)
        if ctx_step["rc"] != 0:
            write_json(out_dir / "summary.json", _finalize_summary(summary, start_monotonic=start_monotonic))
            print(f"SC_BUILD_TDD status=fail out={out_dir}")
            assert_no_new_contract_files(before_contracts, allow_changes=bool(args.allow_contract_changes))
            return 1

        test_path = ensure_red_test_exists(
            triplet.task_id,
            str(triplet.master.get("title") or ""),
            allow_create=args.generate_red_test,
            out_dir=out_dir,
        )
        if not test_path:
            write_json(out_dir / "summary.json", _finalize_summary(summary, start_monotonic=start_monotonic))
            print("[sc-build-tdd] ERROR: no task-scoped test found. Use --generate-red-test to create one.")
            return 2

        step = run_dotnet_test_filtered(
            triplet.task_id,
            solution=resolved_solution,
            configuration=args.configuration,
            out_dir=out_dir,
        )
        summary["steps"].append(step)

        # In red stage, we EXPECT a failure.
        summary["status"] = "ok" if step["rc"] != 0 else "unexpected_green"
        write_json(out_dir / "summary.json", _finalize_summary(summary, start_monotonic=start_monotonic))
        print(f"SC_BUILD_TDD status={summary['status']} out={out_dir}")
        assert_no_new_contract_files(before_contracts, allow_changes=bool(args.allow_contract_changes))
        return 0 if summary["status"] == "ok" else 1

    if args.stage == "green":
        prereq_step = validate_green_red_prerequisite(task_id=triplet.task_id, out_dir=out_dir)
        summary["steps"].append(prereq_step)
        if prereq_step["rc"] != 0:
            write_json(out_dir / "summary.json", _finalize_summary(summary, start_monotonic=start_monotonic))
            print(f"SC_BUILD_TDD status=fail out={out_dir}")
            assert_no_new_contract_files(before_contracts, allow_changes=bool(args.allow_contract_changes))
            return 1

        preflight_step = run_task_preflight(triplet=triplet, out_dir=out_dir)
        summary["steps"].append(preflight_step)
        if preflight_step["rc"] != 0:
            write_json(out_dir / "summary.json", _finalize_summary(summary, start_monotonic=start_monotonic))
            print(f"SC_BUILD_TDD status=fail out={out_dir}")
            assert_no_new_contract_files(before_contracts, allow_changes=bool(args.allow_contract_changes))
            return 1
        summary["steps"].append(run_sc_analyze_task_context(task_id=triplet.task_id, out_dir=out_dir))
        ctx_step = validate_task_context_required_fields(task_id=triplet.task_id, stage="green", out_dir=out_dir)
        summary["steps"].append(ctx_step)
        if ctx_step["rc"] != 0:
            write_json(out_dir / "summary.json", _finalize_summary(summary, start_monotonic=start_monotonic))
            print(f"SC_BUILD_TDD status=fail out={out_dir}")
            assert_no_new_contract_files(before_contracts, allow_changes=bool(args.allow_contract_changes))
            return 1
        step = run_green_gate(
            task_id=triplet.task_id,
            triplet=triplet,
            solution=resolved_solution,
            configuration=args.configuration,
            out_dir=out_dir,
            coverage_gate=bool(runtime["coverage_gate"]),
            coverage_lines_min=int(runtime["coverage_lines_min"]),
            coverage_branches_min=int(runtime["coverage_branches_min"]),
            green_scope=args.green_scope,
        )
        summary["steps"].append(step)
        if step["rc"] == 2:
            summary["steps"].append(write_coverage_hotspots(ci_out_dir=out_dir, run_dotnet_output=step.get("stdout") or ""))
        summary["status"] = "ok" if step["rc"] == 0 else "fail"
        write_json(out_dir / "summary.json", _finalize_summary(summary, start_monotonic=start_monotonic))
        print(f"SC_BUILD_TDD status={summary['status']} out={out_dir}")
        assert_no_new_contract_files(before_contracts, allow_changes=bool(args.allow_contract_changes))
        return 0 if step["rc"] == 0 else 1

    if args.stage == "refactor":
        prereq_step = validate_refactor_green_prerequisite(task_id=triplet.task_id, out_dir=out_dir)
        summary["steps"].append(prereq_step)
        if prereq_step["rc"] != 0:
            write_json(out_dir / "summary.json", _finalize_summary(summary, start_monotonic=start_monotonic))
            print(f"SC_BUILD_TDD status=fail out={out_dir}")
            assert_no_new_contract_files(before_contracts, allow_changes=bool(args.allow_contract_changes))
            return 1

        preflight_step = run_task_preflight(triplet=triplet, out_dir=out_dir)
        summary["steps"].append(preflight_step)
        if preflight_step["rc"] != 0:
            write_json(out_dir / "summary.json", _finalize_summary(summary, start_monotonic=start_monotonic))
            print(f"SC_BUILD_TDD status=fail out={out_dir}")
            assert_no_new_contract_files(before_contracts, allow_changes=bool(args.allow_contract_changes))
            return 1
        summary["steps"].append(run_sc_analyze_task_context(task_id=triplet.task_id, out_dir=out_dir))
        ctx_step = validate_task_context_required_fields(task_id=triplet.task_id, stage="refactor", out_dir=out_dir)
        summary["steps"].append(ctx_step)
        if ctx_step["rc"] != 0:
            write_json(out_dir / "summary.json", _finalize_summary(summary, start_monotonic=start_monotonic))
            print(f"SC_BUILD_TDD status=fail out={out_dir}")
            assert_no_new_contract_files(before_contracts, allow_changes=bool(args.allow_contract_changes))
            return 1

        steps = run_refactor_checks(out_dir, task_id=triplet.task_id)
        summary["steps"].extend(steps)
        summary["status"] = "ok" if all(s["rc"] == 0 for s in steps) else "fail"
        write_json(out_dir / "summary.json", _finalize_summary(summary, start_monotonic=start_monotonic))

        if summary["status"] != "ok":
            failed = [s for s in steps if s.get("rc") != 0]
            print(f"SC_BUILD_TDD status=fail out={out_dir} failed_steps={len(failed)}")

            def _print_top_errors(json_path: Path, *, label: str, max_items: int = 12) -> None:
                if not json_path.exists():
                    return
                try:
                    payload = json.loads(json_path.read_text(encoding="utf-8"))
                except Exception:
                    return
                errs = payload.get("errors")
                if not isinstance(errs, list) or not errs:
                    return
                print(f"{label}:")
                for e in [str(x) for x in errs[:max_items]]:
                    print(f"  - {e}")
                if len(errs) > max_items:
                    print(f"  ... ({len(errs) - max_items} more)")

            _print_top_errors(out_dir / "acceptance-refs.json", label="ACCEPTANCE_REFS_TOP_ERRORS")
            _print_top_errors(out_dir / "task-test-refs.json", label="TASK_TEST_REFS_TOP_ERRORS")
            print("Fix hints:")
            print(f"  - Check logs: {out_dir}")
            print(f"  - Ensure every acceptance item has 'Refs:' and referenced files exist")
            print(f"  - Ensure refs are included in test_refs (or run update_task_test_refs_from_acceptance_refs.py)")
        else:
            print(f"SC_BUILD_TDD status=ok out={out_dir}")

        assert_no_new_contract_files(before_contracts, allow_changes=bool(args.allow_contract_changes))
        return 0 if summary["status"] == "ok" else 1

    write_json(out_dir / "summary.json", _finalize_summary(summary, start_monotonic=start_monotonic))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
