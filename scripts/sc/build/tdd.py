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
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any


def _bootstrap_imports() -> None:
    # scripts/sc/build/tdd.py -> scripts/sc/build -> scripts/sc
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


_bootstrap_imports()

from _taskmaster import resolve_triplet  # noqa: E402
from _util import ci_dir, repo_root, run_cmd, today_str, write_json, write_text  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description="sc-build tdd gatekeeper")
    ap.add_argument("--stage", choices=["red", "green", "refactor"], default="green")
    ap.add_argument("--task-id", default=None, help="task id; defaults to first status=in-progress in tasks.json")
    ap.add_argument("--solution", default="Game.sln")
    ap.add_argument("--configuration", default="Debug")
    ap.add_argument("--generate-red-test", action="store_true", help="create a failing test skeleton if missing")
    ap.add_argument("--no-coverage-gate", action="store_true", help="do not enforce default coverage thresholds")
    return ap


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


def assert_no_new_contract_files(before: set[str]) -> None:
    after = snapshot_contract_files()
    new_files = sorted(after - before)
    if new_files:
        joined = "\n".join(f"- {p}" for p in new_files)
        raise RuntimeError(f"New contract files were created, which is not allowed:\n{joined}")


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


def run_green_gate(*, solution: str, configuration: str, out_dir: Path, no_coverage_gate: bool) -> dict[str, Any]:
    if not no_coverage_gate:
        os.environ.setdefault("COVERAGE_LINES_MIN", "90")
        os.environ.setdefault("COVERAGE_BRANCHES_MIN", "85")

    cmd = ["py", "-3", "scripts/python/run_dotnet.py", "--solution", solution, "--configuration", configuration]
    rc, out = run_cmd(cmd, cwd=repo_root(), timeout_sec=1_800)
    log_path = out_dir / "run_dotnet.log"
    write_text(log_path, out)
    return {"name": "run_dotnet", "cmd": cmd, "rc": rc, "log": str(log_path), "stdout": out}


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
        ("check_test_naming", ["py", "-3", "scripts/python/check_test_naming.py", "--task-id", str(task_id), "--style", "strict"], "scripts/python/check_test_naming.py"),
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


def main() -> int:
    args = build_parser().parse_args()
    out_dir = ci_dir("sc-build-tdd")

    before_contracts = snapshot_contract_files()

    summary: dict[str, Any] = {
        "cmd": "sc-build-tdd",
        "stage": args.stage,
        "status": "fail",
        "steps": [],
    }

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
        summary["steps"].append(run_sc_analyze_task_context(task_id=triplet.task_id, out_dir=out_dir))
        ctx_step = validate_task_context_required_fields(task_id=triplet.task_id, stage="red", out_dir=out_dir)
        summary["steps"].append(ctx_step)
        if ctx_step["rc"] != 0:
            write_json(out_dir / "summary.json", summary)
            print(f"SC_BUILD_TDD status=fail out={out_dir}")
            assert_no_new_contract_files(before_contracts)
            return 1

        test_path = ensure_red_test_exists(
            triplet.task_id,
            str(triplet.master.get("title") or ""),
            allow_create=args.generate_red_test,
            out_dir=out_dir,
        )
        if not test_path:
            write_json(out_dir / "summary.json", summary)
            print("[sc-build-tdd] ERROR: no task-scoped test found. Use --generate-red-test to create one.")
            return 2

        step = run_dotnet_test_filtered(
            triplet.task_id,
            solution=args.solution,
            configuration=args.configuration,
            out_dir=out_dir,
        )
        summary["steps"].append(step)

        # In red stage, we EXPECT a failure.
        summary["status"] = "ok" if step["rc"] != 0 else "unexpected_green"
        write_json(out_dir / "summary.json", summary)
        print(f"SC_BUILD_TDD status={summary['status']} out={out_dir}")
        assert_no_new_contract_files(before_contracts)
        return 0 if summary["status"] == "ok" else 1

    if args.stage == "green":
        summary["steps"].append(run_sc_analyze_task_context(task_id=triplet.task_id, out_dir=out_dir))
        ctx_step = validate_task_context_required_fields(task_id=triplet.task_id, stage="green", out_dir=out_dir)
        summary["steps"].append(ctx_step)
        if ctx_step["rc"] != 0:
            write_json(out_dir / "summary.json", summary)
            print(f"SC_BUILD_TDD status=fail out={out_dir}")
            assert_no_new_contract_files(before_contracts)
            return 1

        step = run_green_gate(
            solution=args.solution,
            configuration=args.configuration,
            out_dir=out_dir,
            no_coverage_gate=args.no_coverage_gate,
        )
        summary["steps"].append(step)
        if step["rc"] == 2:
            summary["steps"].append(write_coverage_hotspots(ci_out_dir=out_dir, run_dotnet_output=step.get("stdout") or ""))
        summary["status"] = "ok" if step["rc"] == 0 else "fail"
        write_json(out_dir / "summary.json", summary)
        print(f"SC_BUILD_TDD status={summary['status']} out={out_dir}")
        assert_no_new_contract_files(before_contracts)
        return 0 if step["rc"] == 0 else 1

    if args.stage == "refactor":
        summary["steps"].append(run_sc_analyze_task_context(task_id=triplet.task_id, out_dir=out_dir))
        ctx_step = validate_task_context_required_fields(task_id=triplet.task_id, stage="refactor", out_dir=out_dir)
        summary["steps"].append(ctx_step)
        if ctx_step["rc"] != 0:
            write_json(out_dir / "summary.json", summary)
            print(f"SC_BUILD_TDD status=fail out={out_dir}")
            assert_no_new_contract_files(before_contracts)
            return 1

        steps = run_refactor_checks(out_dir, task_id=triplet.task_id)
        summary["steps"].extend(steps)
        summary["status"] = "ok" if all(s["rc"] == 0 for s in steps) else "fail"
        write_json(out_dir / "summary.json", summary)

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

        assert_no_new_contract_files(before_contracts)
        return 0 if summary["status"] == "ok" else 1

    write_json(out_dir / "summary.json", summary)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
