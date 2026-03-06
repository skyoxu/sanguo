#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Validate run_gate_bundle.py configuration, referenced scripts, and workflow allowlist.
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


BUNDLE_SCRIPT = Path('scripts/python/run_gate_bundle.py')
ALLOWLIST_PATH = Path('scripts/python/config/workflow-gate-allowlist.json')
DEFAULT_TASK_FILES = ['.taskmaster/tasks/tasks_back.json', '.taskmaster/tasks/tasks_gameplay.json']
REQUIRED_GATE_SCRIPTS = {
    'scripts/python/check_task_contract_refs.py',
    'scripts/python/check_tasks_all_refs.py',
    'scripts/python/check_gate_bundle_consistency.py',
    'scripts/python/check_workflow_gate_enforcement.py',
    'scripts/sc/check_acceptance_garbled.py',
}
SCRIPT_RE = re.compile(r'^scripts/[A-Za-z0-9_./-]+\.py$')


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


def _extract_scripts(commands: list[dict[str, Any]]) -> list[str]:
    scripts: list[str] = []
    for spec in commands:
        cmd = spec.get('cmd') or []
        for item in cmd:
            text = str(item).replace('\\', '/')
            if SCRIPT_RE.match(text):
                scripts.append(text)
    return scripts


def _load_allowlist(repo_root: Path, allowlist_path: Path) -> dict[str, Any]:
    full_path = allowlist_path if allowlist_path.is_absolute() else (repo_root / allowlist_path)
    if not full_path.exists():
        raise FileNotFoundError(f'Allowlist file not found: {allowlist_path.as_posix()}')
    payload = json.loads(full_path.read_text(encoding='utf-8-sig'))
    if not isinstance(payload, dict):
        raise ValueError(f'Allowlist must be a JSON object: {allowlist_path.as_posix()}')
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


def main() -> int:
    parser = argparse.ArgumentParser(description='Validate gate bundle configuration and allowlist consistency.')
    parser.add_argument('--allowlist', default=ALLOWLIST_PATH.as_posix())
    parser.add_argument('--out', default='')
    args = parser.parse_args()

    repo_root = _repo_root()
    violations: list[dict[str, Any]] = []

    script_path = repo_root / BUNDLE_SCRIPT
    if not script_path.exists():
        print(f'GATE_BUNDLE_CONSISTENCY status=fail reason=missing_bundle_script path={BUNDLE_SCRIPT.as_posix()}')
        return 1

    try:
        module = _load_bundle_module(repo_root)
        hard_commands = module._hard_gate_commands_with_options(list(DEFAULT_TASK_FILES), -1)
        soft_commands = module._soft_gate_commands(list(DEFAULT_TASK_FILES))
        allowlist = _load_allowlist(repo_root, Path(args.allowlist))
    except Exception as exc:
        print(f'GATE_BUNDLE_CONSISTENCY status=fail reason=load_error msg={exc}')
        return 1

    hard_names = [str(item.get('name') or '') for item in hard_commands]
    soft_names = [str(item.get('name') or '') for item in soft_commands]
    all_names = hard_names + soft_names
    if not hard_names:
        violations.append({'rule': 'missing_hard_gates', 'message': 'Hard gate bundle must contain at least one gate.'})
    if len(all_names) != len(set(all_names)):
        violations.append({'rule': 'duplicate_gate_names', 'message': 'Gate names must be unique across hard and soft bundles.', 'names': all_names})

    gate_scripts = sorted(set(_extract_scripts(hard_commands) + _extract_scripts(soft_commands)))
    missing_required = sorted(REQUIRED_GATE_SCRIPTS - set(gate_scripts))
    if missing_required:
        violations.append({'rule': 'required_gate_scripts_missing', 'message': 'Bundle is missing required governance gates.', 'scripts': missing_required})

    missing_gate_scripts = [script for script in gate_scripts if not (repo_root / script).exists()]
    if missing_gate_scripts:
        violations.append({'rule': 'bundle_script_missing_on_disk', 'message': 'Referenced gate scripts must exist on disk.', 'scripts': missing_gate_scripts})

    allowed_direct_scripts = allowlist['allowed_direct_scripts']
    required_workflows = allowlist['required_bundle_workflows']
    if BUNDLE_SCRIPT.as_posix() not in allowed_direct_scripts:
        violations.append({'rule': 'bundle_not_allowlisted', 'message': 'Allowlist must include scripts/python/run_gate_bundle.py.'})

    missing_allowlisted_scripts = [script for script in allowed_direct_scripts if script.startswith('scripts/') and not (repo_root / script).exists()]
    if missing_allowlisted_scripts:
        violations.append({'rule': 'allowlisted_script_missing_on_disk', 'message': 'Allowlisted direct scripts must exist on disk.', 'scripts': missing_allowlisted_scripts})

    missing_workflows = [path for path in required_workflows if not (repo_root / path).exists()]
    if missing_workflows:
        violations.append({'rule': 'required_workflow_missing', 'message': 'Required bundle workflows must exist on disk.', 'workflows': missing_workflows})

    summary = {
        'ts': dt.datetime.now(dt.timezone.utc).isoformat(),
        'action': 'gate-bundle-consistency',
        'status': 'ok' if not violations else 'fail',
        'bundle_script': BUNDLE_SCRIPT.as_posix(),
        'allowlist': allowlist['path'],
        'hard_gate_names': hard_names,
        'soft_gate_names': soft_names,
        'gate_scripts': gate_scripts,
        'allowed_direct_scripts': allowed_direct_scripts,
        'required_bundle_workflows': required_workflows,
        'violations_count': len(violations),
        'violations': violations,
    }

    out_path = Path(args.out) if args.out else (Path('logs') / 'ci' / _today() / 'gate-bundle-consistency' / 'summary.json')
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

    print(f"GATE_BUNDLE_CONSISTENCY status={summary['status']} violations={len(violations)} out={out_path.as_posix()}")
    if violations:
        for item in violations[:20]:
            print(f" - rule={item['rule']} msg={item['message']}")
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
