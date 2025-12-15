#!/usr/bin/env python3
"""
sc-analyze: Repo-specific static analysis shim (Godot+C# template).

This script is intended to provide an equivalent workflow to SuperClaude
`/sc:analyze` for this repository by orchestrating existing Python checks and
lightweight pattern scans. It does not compile code or run the game engine.

Usage (Windows):
  py -3 scripts/sc/analyze.py
  py -3 scripts/sc/analyze.py --focus security --depth deep --format report
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path
from typing import Any

from _taskmaster import resolve_triplet
from _util import ci_dir, iter_files, repo_root, run_cmd, write_json, write_text


TEXT_EXTS = {
    ".cs",
    ".csproj",
    ".sln",
    ".gd",
    ".tscn",
    ".tres",
    ".res",
    ".json",
    ".md",
    ".toml",
    ".yml",
    ".yaml",
}

SKIP_DIRS = {
    ".git",
    ".godot",
    ".serena",
    ".taskmaster",
    "addons",
    "bin",
    "build",
    "logs",
    "obj",
    "tmp",
}


def scan_patterns(target: Path, patterns: dict[str, str], max_hits: int) -> dict[str, Any]:
    findings: dict[str, Any] = {"target": str(target), "patterns": {}, "total_hits": 0}

    compiled = {k: re.compile(v) for k, v in patterns.items()}
    for p in compiled:
        findings["patterns"][p] = {"hits": [], "count": 0}

    for path in iter_files(target, include_exts=TEXT_EXTS, skip_dirs=SKIP_DIRS):
        try:
            text = path.read_text(encoding="utf-8")
        except Exception:
            continue

        for name, rx in compiled.items():
            for m in rx.finditer(text):
                findings["patterns"][name]["count"] += 1
                findings["total_hits"] += 1
                if len(findings["patterns"][name]["hits"]) < max_hits:
                    # Keep a short snippet to avoid huge logs.
                    start = max(m.start() - 40, 0)
                    end = min(m.end() + 40, len(text))
                    snippet = text[start:end].replace("\r", "").replace("\n", "\\n")
                    findings["patterns"][name]["hits"].append(
                        {
                            "path": str(path.relative_to(repo_root())),
                            "snippet": snippet,
                        }
                    )
    return findings


def run_checks(out_dir: Path, focus: str) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []

    def run_check(
        name: str,
        cmd: list[str],
        *,
        requires_relpaths: list[str] | None = None,
        timeout_sec: int = 900,
    ) -> None:
        log_path = out_dir / f"{name}.log"
        if requires_relpaths:
            missing = [p for p in requires_relpaths if not (repo_root() / p).exists()]
            if missing:
                joined = ", ".join(missing)
                write_text(log_path, f"SKIP missing: {joined}\n")
                checks.append(
                    {
                        "name": name,
                        "cmd": cmd,
                        "rc": 0,
                        "log": str(log_path),
                        "status": "skipped",
                        "reason": "missing:" + joined,
                    }
                )
                return
        rc, out = run_cmd(cmd, cwd=repo_root(), timeout_sec=timeout_sec)
        write_text(log_path, out)
        checks.append({"name": name, "cmd": cmd, "rc": rc, "log": str(log_path), "status": "ok" if rc == 0 else "fail"})

    # Architecture/traceability checks.
    if focus in ("all", "architecture", "quality"):
        run_check(
            "check_tasks_all_refs",
            ["py", "-3", "scripts/python/check_tasks_all_refs.py"],
            requires_relpaths=["scripts/python/check_tasks_all_refs.py", ".taskmaster/tasks/tasks.json"],
        )
        run_check(
            "check_tasks_back_references",
            ["py", "-3", "scripts/python/check_tasks_back_references.py"],
            requires_relpaths=["scripts/python/check_tasks_back_references.py", ".taskmaster/tasks/tasks_back.json"],
        )
        run_check(
            "validate_task_master_triplet",
            ["py", "-3", "scripts/python/validate_task_master_triplet.py"],
            requires_relpaths=[
                "scripts/python/validate_task_master_triplet.py",
                ".taskmaster/tasks/tasks.json",
                ".taskmaster/tasks/tasks_back.json",
                ".taskmaster/tasks/tasks_gameplay.json",
            ],
        )
        run_check(
            "validate_task_overlays",
            ["py", "-3", "scripts/python/validate_task_overlays.py"],
            requires_relpaths=["scripts/python/validate_task_overlays.py", ".taskmaster/tasks/tasks.json"],
        )

    # Contracts consistency (Overlay <-> Contracts).
    if focus in ("all", "architecture", "quality"):
        run_check(
            "validate_contracts",
            ["py", "-3", "scripts/python/validate_contracts.py"],
            requires_relpaths=["scripts/python/validate_contracts.py"],
        )
        run_check(
            "check_sanguo_gameloop_contracts",
            ["py", "-3", "scripts/python/check_sanguo_gameloop_contracts.py"],
            requires_relpaths=["scripts/python/check_sanguo_gameloop_contracts.py"],
        )

    # Quality checks.
    if focus in ("all", "quality"):
        run_check(
            "check_test_naming",
            ["py", "-3", "scripts/python/check_test_naming.py"],
            requires_relpaths=["scripts/python/check_test_naming.py"],
        )
        run_check(
            "check_encoding_since_today",
            ["py", "-3", "scripts/python/check_encoding.py", "--since-today"],
            requires_relpaths=["scripts/python/check_encoding.py"],
        )

    # Security checks.
    if focus in ("all", "security"):
        run_check(
            "check_sentry_secrets",
            ["py", "-3", "scripts/python/check_sentry_secrets.py"],
            requires_relpaths=["scripts/python/check_sentry_secrets.py"],
        )

    return checks


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description="sc-analyze (static analysis shim)")
    ap.add_argument("target", nargs="?", default=".", help="analysis target directory (default: repo root)")
    ap.add_argument("--task-id", default=None, help="task id; defaults to first status=in-progress in tasks.json")
    ap.add_argument("--tasks-json-path", default=None, help="override .taskmaster/tasks/tasks.json path")
    ap.add_argument("--tasks-back-path", default=None, help="override .taskmaster/tasks/tasks_back.json path")
    ap.add_argument("--tasks-gameplay-path", default=None, help="override .taskmaster/tasks/tasks_gameplay.json path")
    ap.add_argument("--taskdoc-dir", default="taskdoc", help="directory containing Serena task docs (default: taskdoc)")
    ap.add_argument("--focus", choices=["all", "quality", "security", "performance", "architecture"], default="all")
    ap.add_argument("--depth", choices=["quick", "deep"], default="quick")
    ap.add_argument("--format", choices=["text", "json", "report"], default="text")
    ap.add_argument("--max-pattern-hits", type=int, default=10)
    ap.add_argument("--strict", action="store_true", help="exit non-zero on any pattern hits")
    return ap


def main() -> int:
    args = build_parser().parse_args()

    out_dir = ci_dir("sc-analyze")
    target = (repo_root() / args.target).resolve()

    # Resolve current Taskmaster triplet (tasks.json + tasks_back + tasks_gameplay).
    try:
        triplet = resolve_triplet(
            task_id=args.task_id,
            tasks_json_path=args.tasks_json_path,
            tasks_back_path=args.tasks_back_path,
            tasks_gameplay_path=args.tasks_gameplay_path,
            taskdoc_dir=args.taskdoc_dir,
        )
        write_json(out_dir / "task_context.json", triplet.__dict__)
        task_md_lines = [
            "# sc-analyze task context",
            "",
            f"- task_id: {triplet.task_id}",
            f"- title: {triplet.master.get('title')}",
            f"- status: {triplet.master.get('status')}",
            f"- priority: {triplet.master.get('priority')}",
            f"- adrRefs: {', '.join(triplet.adr_refs()) if triplet.adr_refs() else '(missing)'}",
            f"- archRefs: {', '.join(triplet.arch_refs()) if triplet.arch_refs() else '(missing)'}",
            f"- overlay: {triplet.overlay() or '(none)'}",
            f"- taskdoc: {triplet.taskdoc_path or '(missing)'}",
            f"- tasks_back mapped: {'yes' if triplet.back else 'no'}",
            f"- tasks_gameplay mapped: {'yes' if triplet.gameplay else 'no'}",
            "",
        ]
        if triplet.taskdoc_path:
            try:
                taskdoc_text = Path(triplet.taskdoc_path).read_text(encoding="utf-8")
                task_md_lines += ["## taskdoc", "", taskdoc_text.rstrip(), ""]
            except Exception:
                pass
        write_text(out_dir / "task_context.md", "\n".join(task_md_lines))
    except Exception as e:
        # Keep analyze usable for general audits even when task mapping is broken.
        write_text(out_dir / "task_context.error.txt", f"{type(e).__name__}: {e}\n")

    report: dict[str, Any] = {
        "cmd": "sc-analyze",
        "focus": args.focus,
        "depth": args.depth,
        "target": str(target),
        "status": "fail",
        "checks": [],
        "pattern_findings": None,
    }

    checks = run_checks(out_dir, args.focus)
    report["checks"] = checks

    any_check_failed = any(c.get("rc", 0) != 0 for c in checks)

    pattern_findings = None
    if args.depth == "deep":
        # Keep patterns repo-specific and intentionally conservative to reduce noise.
        patterns: dict[str, str] = {}
        if args.focus in ("all", "security"):
            patterns.update(
                {
                    "godot_os_execute": r"\bOS\.Execute\s*\(",
                    "non_https_url": r"http://[^\s)\"']+",
                    "absolute_windows_path": r"\b[A-Za-z]:\\\\",
                }
            )
        if args.focus in ("all", "performance"):
            patterns.update(
                {
                    "thread_sleep": r"\bThread\.Sleep\s*\(",
                    "gc_collect": r"\bGC\.Collect\s*\(",
                }
            )
        if patterns:
            pattern_findings = scan_patterns(target, patterns, max_hits=args.max_pattern_hits)
    report["pattern_findings"] = pattern_findings

    pattern_failed = bool(pattern_findings and pattern_findings.get("total_hits", 0) > 0 and args.strict)

    report["status"] = "ok" if (not any_check_failed and not pattern_failed) else "fail"

    json_path = out_dir / "summary.json"
    write_json(json_path, report)

    if args.format == "report":
        md_lines = [
            "# sc-analyze report",
            "",
            f"- status: {report['status']}",
            f"- focus: {args.focus}",
            f"- depth: {args.depth}",
            f"- target: {target}",
            "",
            "## Checks",
        ]
        for c in checks:
            md_lines.append(f"- {c['name']}: rc={c['rc']} log={c['log']}")
        if pattern_findings:
            md_lines += ["", "## Pattern Findings", f"- total_hits: {pattern_findings.get('total_hits')}"]
            for k, v in (pattern_findings.get("patterns") or {}).items():
                md_lines.append(f"- {k}: count={v.get('count')}")
        write_text(out_dir / "report.md", "\n".join(md_lines) + "\n")

    print(f"SC_ANALYZE status={report['status']} out={out_dir}")
    return 0 if report["status"] == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
