#!/usr/bin/env python3
"""Lightweight TDD runner for prototype-lane work."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import subprocess
import sys
from pathlib import Path


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def today_str() -> str:
    return dt.date.today().isoformat()


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def write_text(path: Path, content: str) -> None:
    ensure_dir(path.parent)
    path.write_text(content, encoding="utf-8")


def write_json(path: Path, payload: object) -> None:
    ensure_dir(path.parent)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def run_cmd(args: list[str], *, cwd: Path, timeout_sec: int) -> tuple[int, str]:
    proc = subprocess.Popen(
        args,
        cwd=str(cwd),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="ignore",
    )
    try:
        out, _ = proc.communicate(timeout=timeout_sec)
    except subprocess.TimeoutExpired:
        proc.kill()
        out, _ = proc.communicate()
        return 124, out
    return proc.returncode or 0, out


def _sanitize_slug(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_-]+", "-", str(value or "").strip())
    cleaned = re.sub(r"-{2,}", "-", cleaned).strip("-_")
    return cleaned or "prototype"


def _prototype_record_path(*, root: Path, prototype_dir: str, record_path: str, slug: str) -> Path:
    if str(record_path or "").strip():
        return (root / record_path).resolve()
    return root / prototype_dir / f"{today_str()}-{slug}.md"


def _render_record(
    *,
    slug: str,
    owner: str,
    related_task_ids: list[str],
    hypothesis: str,
    scope_in: list[str],
    scope_out: list[str],
    success_criteria: list[str],
    evidence: list[str],
    next_step: str,
) -> str:
    related = ", ".join(related_task_ids) if related_task_ids else "none yet"
    scope_in_lines = "\n".join(f"  - {item}" for item in (scope_in or ["TBD"]))
    scope_out_lines = "\n".join(f"  - {item}" for item in (scope_out or ["TBD"]))
    criteria_lines = "\n".join(f"- {item}" for item in (success_criteria or ["TBD"]))
    evidence_lines = "\n".join(f"  - {item}" for item in (evidence or ["TBD"]))
    lines = [
        f"# Prototype: {slug}",
        "",
        "- Status: active",
        f"- Owner: {owner}",
        f"- Date: {today_str()}",
        f"- Related formal task ids: {related}",
        "",
        "## Hypothesis",
        f"- {hypothesis}",
        "",
        "## Scope",
        "- In:",
        scope_in_lines,
        "- Out:",
        scope_out_lines,
        "",
        "## Success Criteria",
        criteria_lines,
        "",
        "## Evidence",
        "- Code paths:",
        evidence_lines,
        "- Logs / media / notes:",
        "  - TBD",
        "",
        "## Decision",
        "- pending (choose discard | archive | promote)",
        "",
        "## Next Step",
        f"- {next_step}",
        "",
    ]
    return "\n".join(lines)


def _ensure_record(
    *,
    root: Path,
    slug: str,
    prototype_dir: str,
    record_path: str,
    skip_record: bool,
    owner: str,
    related_task_ids: list[str],
    hypothesis: str,
    scope_in: list[str],
    scope_out: list[str],
    success_criteria: list[str],
    evidence: list[str],
    next_step: str,
) -> str:
    if skip_record:
        return ""
    record = _prototype_record_path(root=root, prototype_dir=prototype_dir, record_path=record_path, slug=slug)
    if not record.exists():
        write_text(
            record,
            _render_record(
                slug=slug,
                owner=owner,
                related_task_ids=related_task_ids,
                hypothesis=hypothesis,
                scope_in=scope_in,
                scope_out=scope_out,
                success_criteria=success_criteria,
                evidence=evidence,
                next_step=next_step,
            ),
        )
    try:
        return str(record.relative_to(root)).replace("\\", "/")
    except ValueError:
        return str(record).replace("\\", "/")


def _build_dotnet_steps(*, targets: list[str], configuration: str, filter_expr: str) -> list[dict[str, object]]:
    steps: list[dict[str, object]] = []
    for idx, target in enumerate(targets, start=1):
        cmd = ["dotnet", "test", target, "-c", configuration]
        if filter_expr:
            cmd += ["--filter", filter_expr]
        steps.append(
            {
                "name": f"dotnet-{idx}",
                "kind": "dotnet-test",
                "cmd": cmd,
            }
        )
    return steps


def _build_gdunit_step(*, godot_bin: str, gdunit_paths: list[str], timeout_sec: int, report_dir: str) -> dict[str, object]:
    cmd = [
        "py",
        "-3",
        "scripts/python/run_gdunit.py",
        "--prewarm",
        "--godot-bin",
        godot_bin,
        "--project",
        "Tests.Godot",
    ]
    for path in gdunit_paths:
        cmd += ["--add", path]
    cmd += ["--timeout-sec", str(timeout_sec), "--rd", report_dir]
    return {
        "name": "gdunit",
        "kind": "gdunit",
        "cmd": cmd,
    }


def _expected_outcome(stage: str, expect: str) -> str:
    if expect in {"fail", "pass"}:
        return expect
    return "fail" if stage == "red" else "pass"


def _evaluate_steps(*, expected: str, steps: list[dict[str, object]]) -> tuple[str, str]:
    failed = [step for step in steps if int(step.get("rc", 0)) != 0]
    if expected == "fail":
        if failed:
            return "ok", "Prototype red evidence captured at least one failing verification step."
        return "unexpected_green", "Prototype red stage expected a failing verification step, but all checks passed."
    if failed:
        return "unexpected_red", "Prototype green/refactor stage expected all verification steps to pass."
    return "ok", "Prototype verification steps passed."


def _build_report(*, payload: dict[str, object]) -> str:
    lines = [
        f"# Prototype TDD Summary ({payload.get('slug', '')})",
        "",
        f"- Stage: {payload.get('stage', '')}",
        f"- Expected: {payload.get('expected', '')}",
        f"- Status: {payload.get('status', '')}",
        f"- Message: {payload.get('message', '')}",
        f"- Prototype record: {payload.get('prototype_record', '') or 'skipped'}",
        "",
        "## Verification Steps",
        "",
    ]
    steps = payload.get("steps", [])
    if isinstance(steps, list) and steps:
        for step in steps:
            if not isinstance(step, dict):
                continue
            lines.append(
                f"- {step.get('name', '')}: rc={step.get('rc', '')} kind={step.get('kind', '')} log={step.get('log', '')}"
            )
    else:
        lines.append("- none")
    lines.append("")
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description="Run a lightweight prototype-lane TDD loop without entering the formal task pipeline.")
    ap.add_argument("--slug", required=True, help="Prototype slug used for docs/prototypes and log artifacts.")
    ap.add_argument("--stage", choices=["red", "green", "refactor"], default="red")
    ap.add_argument("--expect", choices=["auto", "fail", "pass"], default="auto")
    ap.add_argument("--prototype-dir", default="docs/prototypes")
    ap.add_argument("--record-path", default="")
    ap.add_argument("--skip-record", action="store_true", help="Do not create or update a prototype record.")
    ap.add_argument("--owner", default="operator")
    ap.add_argument("--related-task-id", action="append", default=[])
    ap.add_argument("--hypothesis", default="TODO: describe the prototype hypothesis.")
    ap.add_argument("--scope-in", action="append", default=[])
    ap.add_argument("--scope-out", action="append", default=[])
    ap.add_argument("--success-criteria", action="append", default=[])
    ap.add_argument("--evidence", action="append", default=[])
    ap.add_argument("--next-step", default="Decide discard | archive | promote after the prototype result is clear.")
    ap.add_argument("--create-record-only", action="store_true", help="Create the prototype record and exit without running verification.")
    ap.add_argument("--dotnet-target", action="append", default=[], help="Repeatable dotnet test project or solution target.")
    ap.add_argument("--filter", default="", help="Optional dotnet test filter applied to every --dotnet-target.")
    ap.add_argument("--configuration", default="Debug")
    ap.add_argument("--godot-bin", default="")
    ap.add_argument("--gdunit-path", action="append", default=[], help="Repeatable Tests.Godot relative path for prototype GdUnit checks.")
    ap.add_argument("--timeout-sec", type=int, default=300)
    ap.add_argument("--out-dir", default="")
    return ap


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    root = repo_root()
    slug = _sanitize_slug(args.slug)
    out_dir = Path(args.out_dir) if str(args.out_dir or "").strip() else (root / "logs" / "ci" / today_str() / f"prototype-tdd-{slug}-{args.stage}")
    ensure_dir(out_dir)

    prototype_record = _ensure_record(
        root=root,
        slug=slug,
        prototype_dir=str(args.prototype_dir),
        record_path=str(args.record_path),
        skip_record=bool(args.skip_record),
        owner=str(args.owner),
        related_task_ids=[str(item) for item in args.related_task_id],
        hypothesis=str(args.hypothesis),
        scope_in=[str(item) for item in args.scope_in],
        scope_out=[str(item) for item in args.scope_out],
        success_criteria=[str(item) for item in args.success_criteria],
        evidence=[str(item) for item in args.evidence],
        next_step=str(args.next_step),
    )

    steps: list[dict[str, object]] = []
    if args.dotnet_target:
        steps.extend(_build_dotnet_steps(targets=[str(item) for item in args.dotnet_target], configuration=str(args.configuration), filter_expr=str(args.filter)))
    if args.gdunit_path:
        if not str(args.godot_bin or "").strip():
            print("PROTOTYPE_TDD ERROR: --godot-bin is required when --gdunit-path is used.", file=sys.stderr)
            return 2
        steps.append(
            _build_gdunit_step(
                godot_bin=str(args.godot_bin),
                gdunit_paths=[str(item) for item in args.gdunit_path],
                timeout_sec=int(args.timeout_sec),
                report_dir=str((out_dir / "gdunit-report").as_posix()),
            )
        )

    if not steps and not args.create_record_only:
        print("PROTOTYPE_TDD ERROR: provide at least one --dotnet-target or --gdunit-path, or use --create-record-only.", file=sys.stderr)
        return 2

    if not args.create_record_only:
        for index, step in enumerate(steps, start=1):
            log_path = out_dir / f"step-{index:02d}-{step['name']}.log"
            rc, out = run_cmd([str(item) for item in step["cmd"]], cwd=root, timeout_sec=int(args.timeout_sec))
            write_text(log_path, out)
            step["rc"] = rc
            step["log"] = str(log_path.relative_to(root)).replace("\\", "/")

    expected = _expected_outcome(stage=str(args.stage), expect=str(args.expect))
    if args.create_record_only:
        status = "ok"
        message = "Prototype record scaffold created; no verification steps were requested."
    else:
        status, message = _evaluate_steps(expected=expected, steps=steps)

    payload: dict[str, object] = {
        "cmd": "prototype-tdd",
        "slug": slug,
        "stage": str(args.stage),
        "expected": expected,
        "status": status,
        "message": message,
        "prototype_record": prototype_record,
        "steps": steps,
        "create_record_only": bool(args.create_record_only),
    }
    write_json(out_dir / "summary.json", payload)
    write_text(out_dir / "report.md", _build_report(payload=payload))
    print(f"PROTOTYPE_TDD status={status} stage={args.stage} expected={expected} out={out_dir}")
    return 0 if status == "ok" else 1


if __name__ == "__main__":
    sys.exit(main())
