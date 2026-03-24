#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Enforce workflow usage of run_gate_bundle.py and forbid direct invocation of bundled gates.
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


WORKFLOW_GLOB = '.github/workflows/*.y*ml'
BUNDLE_SCRIPT = Path('scripts/python/run_gate_bundle.py')
ALLOWLIST_PATH = Path('scripts/python/config/workflow-gate-allowlist.json')
DEFAULT_TASK_FILES = ['.taskmaster/tasks/tasks_back.json', '.taskmaster/tasks/tasks_gameplay.json']
SCRIPT_RE = re.compile(r'scripts/[A-Za-z0-9_./-]+\.py')


def _today() -> str:
    return dt.date.today().strftime('%Y-%m-%d')


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _load_bundle_module(repo_root: Path):
    script_path = repo_root / BUNDLE_SCRIPT
    spec = importlib.util.spec_from_file_location('run_gate_bundle_module', script_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f'Unable to load bundle module: {BUNDLE_SCRIPT.as_posix()}')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_allowlist(repo_root: Path, allowlist_path: Path) -> dict[str, Any]:
    full_path = allowlist_path if allowlist_path.is_absolute() else (repo_root / allowlist_path)
    if not full_path.exists():
        raise FileNotFoundError(f'Allowlist file not found: {allowlist_path.as_posix()}')
    payload = json.loads(full_path.read_text(encoding='utf-8-sig'))
    if not isinstance(payload, dict):
        raise ValueError('Allowlist must be a JSON object.')
    allowed_direct = payload.get('allowed_direct_scripts')
    required_workflows = payload.get('required_bundle_workflows')
    if not isinstance(allowed_direct, list) or not all(isinstance(item, str) for item in allowed_direct):
        raise ValueError('allowed_direct_scripts must be an array of strings.')
    if not isinstance(required_workflows, list) or not all(isinstance(item, str) for item in required_workflows):
        raise ValueError('required_bundle_workflows must be an array of strings.')
    return {
        'path': allowlist_path.as_posix(),
        'allowed_direct_scripts': sorted({item.replace('\\', '/') for item in allowed_direct}),
        'required_bundle_workflows': sorted({item.replace('\\', '/') for item in required_workflows}),
    }


def _extract_gate_scripts(commands: list[dict[str, Any]]) -> set[str]:
    scripts: set[str] = set()
    for spec in commands:
        for item in spec.get('cmd') or []:
            text = str(item).replace('\\', '/')
            if text.startswith('scripts/') and text.endswith('.py'):
                scripts.add(text)
    return scripts


def _extract_workflow_scripts(text: str) -> set[str]:
    return {item.replace('\\', '/') for item in SCRIPT_RE.findall(text)}


def main() -> int:
    parser = argparse.ArgumentParser(description='Enforce workflow use of run_gate_bundle.py.')
    parser.add_argument('--allowlist', default=ALLOWLIST_PATH.as_posix())
    parser.add_argument('--out', default='')
    args = parser.parse_args()

    repo_root = _repo_root()
    workflows = sorted(repo_root.glob('.github/workflows/*.yml')) + sorted(repo_root.glob('.github/workflows/*.yaml'))
    if not workflows:
        print(f'WORKFLOW_GATE_ENFORCEMENT status=fail reason=no-workflows pattern={WORKFLOW_GLOB}')
        return 1

    try:
        allowlist = _load_allowlist(repo_root, Path(args.allowlist))
        module = _load_bundle_module(repo_root)
        runtime = module.resolve_gate_bundle_runtime(delivery_profile=None)
        hard_commands = module._hard_gate_commands_with_options(
            list(DEFAULT_TASK_FILES),
            bool(runtime['stability_template_hard']),
            int(runtime['task_links_max_warnings']),
        )
        soft_commands = module._soft_gate_commands(list(DEFAULT_TASK_FILES), bool(runtime['stability_template_hard']))
    except Exception as exc:
        print(f'WORKFLOW_GATE_ENFORCEMENT status=fail reason=load_error msg={exc}')
        return 1

    bundle_gate_scripts = _extract_gate_scripts(hard_commands) | _extract_gate_scripts(soft_commands)
    allowed_direct_scripts = set(allowlist['allowed_direct_scripts'])
    required_bundle_workflows = set(allowlist['required_bundle_workflows'])

    violations: list[dict[str, Any]] = []
    files_summary: list[dict[str, Any]] = []

    for workflow_path in workflows:
        rel = workflow_path.relative_to(repo_root).as_posix()
        text = workflow_path.read_text(encoding='utf-8')
        scripts = sorted(_extract_workflow_scripts(text))

        run_gate_bundle_present = BUNDLE_SCRIPT.as_posix() in scripts
        direct_gate_calls = sorted(script for script in scripts if script in bundle_gate_scripts and script != BUNDLE_SCRIPT.as_posix())
        unknown_direct = sorted(script for script in scripts if script not in allowed_direct_scripts and script not in bundle_gate_scripts)

        file_violations: list[dict[str, Any]] = []
        if direct_gate_calls:
            file_violations.append({'rule': 'direct_gate_call_not_allowed', 'message': 'Bundled governance gates must not be called directly from workflow files.', 'scripts': direct_gate_calls})
        if unknown_direct:
            file_violations.append({'rule': 'unknown_direct_python_script', 'message': 'Workflow references Python scripts that are neither bundled nor allowlisted.', 'scripts': unknown_direct})
        if rel in required_bundle_workflows and not run_gate_bundle_present:
            file_violations.append({'rule': 'missing_run_gate_bundle', 'message': 'Workflow must invoke scripts/python/run_gate_bundle.py.', 'scripts': []})

        for item in file_violations:
            violations.append({'workflow': rel, **item})

        files_summary.append(
            {
                'workflow': rel,
                'scripts': scripts,
                'run_gate_bundle_present': run_gate_bundle_present,
                'direct_gate_calls': direct_gate_calls,
                'unknown_direct': unknown_direct,
                'violations': file_violations,
            }
        )

    summary = {
        'ts': dt.datetime.now(dt.timezone.utc).isoformat(),
        'action': 'workflow-gate-enforcement',
        'status': 'ok' if not violations else 'fail',
        'allowlist': allowlist['path'],
        'bundle_script': BUNDLE_SCRIPT.as_posix(),
        'bundle_gate_scripts': sorted(bundle_gate_scripts),
        'allowed_direct_scripts': sorted(allowed_direct_scripts),
        'required_bundle_workflows': sorted(required_bundle_workflows),
        'violations_count': len(violations),
        'violations': violations,
        'files': files_summary,
    }

    out_path = Path(args.out) if args.out else (Path('logs') / 'ci' / _today() / 'workflow-gate-enforcement' / 'summary.json')
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

    print(f"WORKFLOW_GATE_ENFORCEMENT status={summary['status']} violations={len(violations)} workflows={len(files_summary)} out={out_path.as_posix()}")
    if violations:
        for item in violations[:30]:
            print(f" - workflow={item['workflow']} rule={item['rule']} scripts={item.get('scripts', [])}")
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
