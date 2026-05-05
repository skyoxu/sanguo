#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Enforce workflow usage rule for Python gate scripts.

Rule:
- New gate scripts must be wired into scripts/python/run_gate_bundle.py first.
- Workflow files should call run_gate_bundle.py for gate execution, rather than
  directly invoking gate scripts.

This checker scans .github/workflows/*.yml and reports:
1) direct calls to gate scripts that are already inside run_gate_bundle
2) direct calls to unknown scripts not explicitly allowlisted
3) workflow files that do not invoke run_gate_bundle.py at all

Output:
  logs/ci/<YYYY-MM-DD>/workflow-gate-enforcement/summary.json
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


WORKFLOW_GLOB = ".github/workflows/*.yml"
BUNDLE_SCRIPT = Path("scripts/python/run_gate_bundle.py")
DEFAULT_ALLOWLIST_PATH = Path("scripts/python/config/workflow-gate-allowlist.json")


def _today() -> str:
    return dt.date.today().strftime("%Y-%m-%d")


def _load_bundle_module(repo_root: Path):
    path = repo_root / BUNDLE_SCRIPT
    spec = importlib.util.spec_from_file_location("run_gate_bundle_module", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load module from {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # type: ignore[assignment]
    return module


def _extract_gate_scripts(commands: list[dict[str, Any]]) -> set[str]:
    out: set[str] = set()
    for item in commands:
        cmd = [str(x) for x in item.get("cmd", [])]
        for token in cmd:
            normalized = token.replace("\\", "/")
            if normalized.startswith("scripts/python/") and normalized.endswith(".py"):
                out.add(normalized)
                break
    return out


def _extract_workflow_scripts(text: str) -> set[str]:
    pattern = re.compile(r"scripts/python/[A-Za-z0-9_.-]+\.py")
    return {match.group(0).replace("\\", "/") for match in pattern.finditer(text)}


def _load_allowlist(repo_root: Path, allowlist_path: Path) -> dict[str, Any]:
    full_path = allowlist_path if allowlist_path.is_absolute() else (repo_root / allowlist_path)
    if not full_path.exists():
        raise FileNotFoundError(f"allowlist file not found: {allowlist_path.as_posix()}")

    payload = json.loads(full_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"allowlist must be a JSON object: {allowlist_path.as_posix()}")

    allowed_direct = payload.get("allowed_direct_scripts")
    required_workflows = payload.get("required_bundle_workflows")

    if not isinstance(allowed_direct, list) or not all(isinstance(x, str) for x in allowed_direct):
        raise ValueError(
            f"allowlist.allowed_direct_scripts must be an array of strings: {allowlist_path.as_posix()}"
        )
    if not isinstance(required_workflows, list) or not all(isinstance(x, str) for x in required_workflows):
        raise ValueError(
            f"allowlist.required_bundle_workflows must be an array of strings: {allowlist_path.as_posix()}"
        )

    return {
        "path": allowlist_path.as_posix(),
        "allowed_direct_scripts": sorted({x.replace("\\", "/") for x in allowed_direct}),
        "required_bundle_workflows": sorted({x.replace("\\", "/") for x in required_workflows}),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Enforce gate-bundle usage in workflow files")
    parser.add_argument(
        "--allowlist",
        default=DEFAULT_ALLOWLIST_PATH.as_posix(),
        help="Path to workflow gate allowlist json",
    )
    parser.add_argument("--out", default="", help="Optional output summary path")
    args = parser.parse_args()

    repo_root = Path.cwd().resolve()
    workflows = sorted(repo_root.glob(WORKFLOW_GLOB))

    if not workflows:
        print(f"WORKFLOW_GATE_ENFORCEMENT status=fail reason=no-workflows pattern={WORKFLOW_GLOB}")
        return 1

    try:
        allowlist = _load_allowlist(repo_root, Path(args.allowlist))
    except Exception as exc:
        print(f"WORKFLOW_GATE_ENFORCEMENT status=fail reason=allowlist_error msg={exc}")
        return 1

    allowed_direct_scripts = set(allowlist["allowed_direct_scripts"])
    required_bundle_workflows = set(allowlist["required_bundle_workflows"])

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

    bundle_gate_scripts = _extract_gate_scripts(hard_commands) | _extract_gate_scripts(soft_commands)

    violations: list[dict[str, Any]] = []
    per_file: list[dict[str, Any]] = []

    for wf in workflows:
        rel = wf.relative_to(repo_root).as_posix()
        text = wf.read_text(encoding="utf-8")
        scripts = sorted(_extract_workflow_scripts(text))

        run_gate_bundle_present = "scripts/python/run_gate_bundle.py" in scripts
        direct_gate_calls = sorted([s for s in scripts if s in bundle_gate_scripts and s != "scripts/python/run_gate_bundle.py"])
        unknown_direct = sorted([s for s in scripts if s not in allowed_direct_scripts and s not in bundle_gate_scripts])

        file_violations: list[dict[str, Any]] = []

        if direct_gate_calls:
            file_violations.append(
                {
                    "rule": "direct_gate_call_not_allowed",
                    "message": "gate scripts in bundle must not be called directly in workflow",
                    "scripts": direct_gate_calls,
                }
            )

        if unknown_direct:
            file_violations.append(
                {
                    "rule": "unknown_direct_python_script",
                    "message": "workflow references python scripts not covered by bundle/allowlist",
                    "scripts": unknown_direct,
                }
            )

        # enforce for primary windows gate workflows
        if rel in required_bundle_workflows and not run_gate_bundle_present:
            file_violations.append(
                {
                    "rule": "missing_run_gate_bundle",
                    "message": "workflow must invoke scripts/python/run_gate_bundle.py",
                    "scripts": [],
                }
            )

        for v in file_violations:
            violations.append({"workflow": rel, **v})

        per_file.append(
            {
                "workflow": rel,
                "scripts": scripts,
                "run_gate_bundle_present": run_gate_bundle_present,
                "direct_gate_calls": direct_gate_calls,
                "unknown_direct": unknown_direct,
                "violations": file_violations,
            }
        )

    ok = len(violations) == 0
    summary = {
        "ts": dt.datetime.now(dt.timezone.utc).isoformat(),
        "action": "workflow-gate-enforcement",
        "status": "ok" if ok else "fail",
        "workflow_glob": WORKFLOW_GLOB,
        "bundle_script": BUNDLE_SCRIPT.as_posix(),
        "allowlist": allowlist["path"],
        "bundle_gate_scripts": sorted(bundle_gate_scripts),
        "allowed_direct_scripts": sorted(allowed_direct_scripts),
        "required_bundle_workflows": sorted(required_bundle_workflows),
        "violations_count": len(violations),
        "violations": violations,
        "files": per_file,
    }

    if args.out:
        out_path = Path(args.out)
    else:
        out_path = Path("logs") / "ci" / _today() / "workflow-gate-enforcement" / "summary.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(
        f"WORKFLOW_GATE_ENFORCEMENT status={'ok' if ok else 'fail'} violations={len(violations)} "
        f"workflows={len(per_file)} out={out_path.as_posix()}"
    )
    if not ok:
        for v in violations[:30]:
            print(f" - workflow={v['workflow']} rule={v['rule']} scripts={v.get('scripts', [])}")

    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
