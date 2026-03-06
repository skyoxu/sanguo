#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Run grouped governance gates for local and CI usage.

Modes:
- hard: fail on any hard gate failure
- soft: run advisory gates only
- all : run hard then soft and emit a combined summary

Outputs:
- logs/ci/<YYYY-MM-DD>/gate-bundle/runs/<run-id>/<mode>/summary.json
- logs/ci/<YYYY-MM-DD>/gate-bundle/runs/<run-id>/<mode>/<gate>.log
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any


DEFAULT_TASK_FILES = [
    '.taskmaster/tasks/tasks_back.json',
    '.taskmaster/tasks/tasks_gameplay.json',
]


def _today() -> str:
    return dt.date.today().strftime('%Y-%m-%d')


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _safe_int(raw: str | int | None, default: int) -> int:
    try:
        return int(str(raw).strip())
    except Exception:
        return int(default)


def _default_task_links_max_warnings() -> int:
    return _safe_int(os.getenv('TASK_LINKS_MAX_WARNINGS', '-1'), -1)


def _default_run_id() -> str:
    gh_run = os.getenv('GITHUB_RUN_ID', '').strip()
    gh_attempt = os.getenv('GITHUB_RUN_ATTEMPT', '').strip()
    if gh_run:
        return f"gh-{gh_run}" + (f"-a{gh_attempt}" if gh_attempt else '')
    ts = dt.datetime.now(dt.timezone.utc).strftime('%H%M%S-%f')
    return f"local-{ts}-{os.getpid()}"


def _default_out_root(run_id: str) -> Path:
    return Path('logs') / 'ci' / _today() / 'gate-bundle' / 'runs' / run_id


def _hard_gate_commands(task_files: list[str]) -> list[dict[str, Any]]:
    return _hard_gate_commands_with_options(task_files, _default_task_links_max_warnings())


def _hard_gate_commands_with_options(task_files: list[str], task_links_max_warnings: int = -1) -> list[dict[str, Any]]:
    resolved_task_files = task_files or list(DEFAULT_TASK_FILES)
    commands: list[dict[str, Any]] = [
        {
            'name': 'gate_bundle_consistency',
            'cmd': ['py', '-3', 'scripts/python/check_gate_bundle_consistency.py'],
        },
        {
            'name': 'workflow_gate_enforcement',
            'cmd': ['py', '-3', 'scripts/python/check_workflow_gate_enforcement.py'],
        },
        {
            'name': 'task_contract_refs',
            'cmd': ['py', '-3', 'scripts/python/check_task_contract_refs.py', '--task-files', *resolved_task_files],
        },
        {
            'name': 'check_tasks_all_refs',
            'cmd': ['py', '-3', 'scripts/python/check_tasks_all_refs.py'],
        },
        {
            'name': 'acceptance_garbled',
            'cmd': ['py', '-3', 'scripts/sc/check_acceptance_garbled.py'],
        },
    ]
    if task_links_max_warnings >= 0:
        for spec in commands:
            if spec['name'] == 'check_tasks_all_refs':
                spec['cmd'].extend(['--max-warnings', str(task_links_max_warnings)])
                break
    return commands


def _soft_gate_commands(task_files: list[str]) -> list[dict[str, Any]]:
    return []


def _resolve_gate_command(name: str, cmd: list[str], out_dir: Path) -> list[str]:
    resolved = [str(item) for item in cmd]
    if name == 'check_tasks_all_refs' and '--summary-out' not in resolved:
        resolved.extend(['--summary-out', (out_dir / 'check-tasks-all-refs-summary.json').as_posix()])
    elif name == 'task_contract_refs' and '--out' not in resolved:
        resolved.extend(['--out', (out_dir / 'task-contract-refs-summary.json').as_posix()])
    elif name == 'gate_bundle_consistency' and '--out' not in resolved:
        resolved.extend(['--out', (out_dir / 'gate-bundle-consistency-summary.json').as_posix()])
    elif name == 'workflow_gate_enforcement' and '--out' not in resolved:
        resolved.extend(['--out', (out_dir / 'workflow-gate-enforcement-summary.json').as_posix()])
    return resolved


def _run_command(cmd: list[str], log_path: Path) -> tuple[int, str]:
    env = os.environ.copy()
    env.setdefault('PYTHONIOENCODING', 'utf-8')
    proc = subprocess.run(
        cmd,
        cwd=_repo_root(),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding='utf-8',
        errors='ignore',
        check=False,
        env=env,
    )
    output = proc.stdout or ''
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.write_text(output, encoding='utf-8')
    return proc.returncode, output


def _run_stage(stage: str, commands: list[dict[str, Any]], out_dir: Path) -> dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=True)
    gate_results: list[dict[str, Any]] = []
    failures = 0
    start = time.perf_counter()

    for spec in commands:
        name = str(spec['name'])
        cmd = _resolve_gate_command(name, list(spec['cmd']), out_dir)
        log_path = out_dir / f'{name}.log'
        gate_start = time.perf_counter()
        rc, _ = _run_command(cmd, log_path)
        duration_sec = round(time.perf_counter() - gate_start, 3)
        gate_results.append(
            {
                'name': name,
                'status': 'ok' if rc == 0 else 'fail',
                'rc': rc,
                'duration_sec': duration_sec,
                'cmd': cmd,
                'log': log_path.as_posix(),
            }
        )
        if rc != 0:
            failures += 1

    summary = {
        'ts': dt.datetime.now(dt.timezone.utc).isoformat(),
        'action': 'run-gate-bundle',
        'mode': stage,
        'status': 'ok' if failures == 0 else 'fail',
        'duration_sec': round(time.perf_counter() - start, 3),
        'gates_count': len(gate_results),
        'failures_count': failures,
        'gates': gate_results,
    }
    (out_dir / 'summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return summary


def _combined_summary(run_id: str, out_root: Path, hard_summary: dict[str, Any], soft_summary: dict[str, Any], strict_soft: bool) -> tuple[dict[str, Any], int]:
    hard_failures = int(hard_summary.get('failures_count') or 0)
    soft_failures = int(soft_summary.get('failures_count') or 0)
    rc = 1 if hard_failures > 0 or (strict_soft and soft_failures > 0) else 0
    summary = {
        'ts': dt.datetime.now(dt.timezone.utc).isoformat(),
        'action': 'run-gate-bundle',
        'mode': 'all',
        'run_id': run_id,
        'status': 'ok' if rc == 0 else 'fail',
        'strict_soft': bool(strict_soft),
        'out_root': out_root.as_posix(),
        'hard': hard_summary,
        'soft': soft_summary,
        'hard_failures_count': hard_failures,
        'soft_failures_count': soft_failures,
    }
    all_dir = out_root / 'all'
    all_dir.mkdir(parents=True, exist_ok=True)
    (all_dir / 'summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return summary, rc


def main() -> int:
    parser = argparse.ArgumentParser(description='Run bundled governance gates for local or CI usage.')
    parser.add_argument('--mode', choices=('hard', 'soft', 'all'), default='all')
    parser.add_argument('--task-files', nargs='*', default=list(DEFAULT_TASK_FILES))
    parser.add_argument('--task-links-max-warnings', type=int, default=_default_task_links_max_warnings())
    parser.add_argument('--strict-soft', action='store_true')
    parser.add_argument('--run-id', default='')
    parser.add_argument('--out-root', default='')
    parser.add_argument('--summary-out', default='')
    args = parser.parse_args()

    run_id = str(args.run_id).strip() or _default_run_id()
    out_root = Path(args.out_root) if args.out_root else _default_out_root(run_id)

    if args.mode == 'hard':
        summary = _run_stage('hard', _hard_gate_commands_with_options(args.task_files, args.task_links_max_warnings), out_root / 'hard')
        rc = 0 if summary['status'] == 'ok' else 1
    elif args.mode == 'soft':
        summary = _run_stage('soft', _soft_gate_commands(args.task_files), out_root / 'soft')
        rc = 0 if summary['status'] == 'ok' or not args.strict_soft else 1
    else:
        hard_summary = _run_stage('hard', _hard_gate_commands_with_options(args.task_files, args.task_links_max_warnings), out_root / 'hard')
        soft_summary = _run_stage('soft', _soft_gate_commands(args.task_files), out_root / 'soft')
        summary, rc = _combined_summary(run_id, out_root, hard_summary, soft_summary, args.strict_soft)

    if args.summary_out:
        summary_out = Path(args.summary_out)
        summary_out.parent.mkdir(parents=True, exist_ok=True)
        summary_out.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

    hard_failures = summary.get('hard_failures_count', summary.get('failures_count', 0))
    soft_failures = summary.get('soft_failures_count', 0)
    print(
        f"GATE_BUNDLE status={summary['status']} mode={summary['mode']} hard_failures={hard_failures} "
        f"soft_failures={soft_failures} out={out_root.as_posix()}"
    )
    return rc


if __name__ == '__main__':
    sys.exit(main())
