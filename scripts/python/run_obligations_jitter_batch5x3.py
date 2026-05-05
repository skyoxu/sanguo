#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import subprocess
from pathlib import Path
from typing import Any

from _obligations_freeze_runtime import (
    default_tasks_file_path,
    known_delivery_profile_choices,
    resolve_delivery_and_security,
    resolve_repo_path,
)


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def today_str() -> str:
    return dt.date.today().strftime('%Y-%m-%d')


def parse_task_ids_csv(text: str) -> list[int]:
    ids: list[int] = []
    seen: set[int] = set()
    for raw in (text or '').split(','):
        value = str(raw).strip()
        if not value:
            continue
        if value.lower().startswith('t') and value[1:].isdigit():
            value = value[1:]
        if not value.isdigit():
            raise ValueError(f'invalid task id token: {raw!r}')
        task_id = int(value)
        if task_id in seen:
            continue
        seen.add(task_id)
        ids.append(task_id)
    return ids


def load_numeric_task_ids(tasks_file: Path) -> list[int]:
    if not tasks_file.exists():
        raise FileNotFoundError(f'tasks file not found: {tasks_file.as_posix()}')
    data = json.loads(tasks_file.read_text(encoding='utf-8'))
    tasks: list[Any] = []
    if isinstance(data, dict):
        if isinstance(data.get('master'), dict) and isinstance(data['master'].get('tasks'), list):
            tasks = data['master']['tasks']
        elif isinstance(data.get('tasks'), list):
            tasks = data['tasks']
    elif isinstance(data, list):
        tasks = data

    result: list[int] = []
    seen: set[int] = set()
    for item in tasks:
        if not isinstance(item, dict):
            continue
        raw_id = item.get('id')
        task_id: int | None = None
        if isinstance(raw_id, int):
            task_id = raw_id
        elif isinstance(raw_id, str):
            raw_id = raw_id.strip()
            if raw_id.isdigit():
                task_id = int(raw_id)
        if task_id is None or task_id <= 0 or task_id in seen:
            continue
        seen.add(task_id)
        result.append(task_id)
    result.sort()
    return result


def chunk_task_ids(task_ids: list[int], batch_size: int) -> list[list[int]]:
    if batch_size <= 0:
        raise ValueError('batch_size must be > 0')
    return [task_ids[index:index + batch_size] for index in range(0, len(task_ids), batch_size)]


def default_out_path() -> Path:
    return resolve_repo_path(f'logs/ci/{today_str()}/sc-llm-obligations-jitter-batch5x3-raw.json')


def parse_out_dir(stdout_text: str, stderr_text: str) -> Path | None:
    combined = '\n'.join(x for x in ((stdout_text or '').strip(), (stderr_text or '').strip()) if x)
    if not combined:
        return None
    matches = re.findall(r'\bout=([^\r\n]+)', combined)
    if not matches:
        return None
    candidate = matches[-1].strip()
    if not candidate:
        return None
    path = Path(candidate)
    if path.is_absolute():
        return path
    return (repo_root() / path).resolve()


def find_latest_task_out_dir(task_id: int) -> Path | None:
    root = repo_root() / 'logs' / 'ci'
    pattern = f'**/sc-llm-obligations-task-{task_id}*'
    candidates = [path for path in root.glob(pattern) if path.is_dir()]
    if not candidates:
        return None
    candidates.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return candidates[0]


def read_json_safe(path: Path) -> dict[str, Any] | None:
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except Exception:
        return None


def read_task_outputs(
    task_id: int,
    *,
    parsed_out_dir: Path | None,
    fallback_rc: int,
) -> tuple[Path | None, dict[str, Any], dict[str, Any]]:
    task_dir = parsed_out_dir if parsed_out_dir and parsed_out_dir.is_dir() else find_latest_task_out_dir(task_id)
    if task_dir is None:
        return None, {'status': 'fail', 'rc': fallback_rc if fallback_rc != 0 else 1, 'error': 'missing_task_outputs'}, {'status': 'fail', 'uncovered_obligation_ids': []}

    summary_obj = read_json_safe(task_dir / 'summary.json')
    verdict_obj = read_json_safe(task_dir / 'verdict.json')
    if not isinstance(summary_obj, dict) or not isinstance(verdict_obj, dict):
        return task_dir, {'status': 'fail', 'rc': fallback_rc if fallback_rc != 0 else 1, 'error': 'missing_or_invalid_outputs'}, {'status': 'fail', 'uncovered_obligation_ids': []}
    return task_dir, summary_obj, verdict_obj


def load_or_init_payload(
    path: Path,
    *,
    task_ids: list[int],
    groups: list[list[int]],
    rounds: int,
    batch_size: int,
    args: argparse.Namespace,
) -> dict[str, Any]:
    if path.exists():
        payload = json.loads(path.read_text(encoding='utf-8'))
        if isinstance(payload, dict):
            payload.setdefault('meta', {})
            payload.setdefault('rows', [])
            return payload
    delivery_profile, security_profile = resolve_delivery_and_security(getattr(args, 'delivery_profile', None), getattr(args, 'security_profile', None))
    return {
        'meta': {
            'date': today_str(),
            'batch_size': batch_size,
            'rounds': rounds,
            'task_ids': task_ids,
            'groups': groups,
            'source_tasks_file': str(Path(args.tasks_file)).replace('\\', '/'),
            'delivery_profile': delivery_profile,
            'security_profile': security_profile,
            'security_override': bool(str(getattr(args, 'security_profile', '') or '').strip()),
            'consensus_runs': args.consensus_runs,
            'min_obligations': args.min_obligations,
            'garbled_gate': args.garbled_gate,
            'auto_escalate': args.auto_escalate,
            'escalate_max_runs': args.escalate_max_runs,
            'max_schema_errors': args.max_schema_errors,
            'reuse_last_ok': bool(args.reuse_last_ok),
        },
        'rows': [],
    }


def build_extract_command(*, task_id: int, timeout_sec: int = 420, round_id: str, args: argparse.Namespace) -> list[str]:
    delivery_profile, security_profile = resolve_delivery_and_security(getattr(args, 'delivery_profile', None), getattr(args, 'security_profile', None))
    has_security_override = bool(str(getattr(args, 'security_profile', '') or '').strip())
    cmd = [
        'py',
        '-3',
        'scripts/sc/llm_extract_task_obligations.py',
        '--task-id',
        str(task_id),
        '--timeout-sec',
        str(timeout_sec),
        '--round-id',
        round_id,
        '--delivery-profile',
        delivery_profile,
        '--garbled-gate',
        getattr(args, 'garbled_gate', 'on'),
        '--auto-escalate',
        getattr(args, 'auto_escalate', 'on'),
        '--escalate-max-runs',
        str(getattr(args, 'escalate_max_runs', 3)),
        '--max-schema-errors',
        str(getattr(args, 'max_schema_errors', 5)),
    ]
    if has_security_override:
        cmd += ['--security-profile', security_profile]
    if args.consensus_runs is not None:
        cmd += ['--consensus-runs', str(args.consensus_runs)]
    if args.min_obligations is not None:
        cmd += ['--min-obligations', str(args.min_obligations)]
    if bool(args.reuse_last_ok):
        cmd.append('--reuse-last-ok')
    if bool(args.explain_reuse_miss):
        cmd.append('--explain-reuse-miss')
    return cmd


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Run obligations jitter batch rounds.')
    parser.add_argument('--task-ids', default='', help='CSV task ids (e.g. 1,2,3 or T1,T2). Default: auto load numeric ids from --tasks-file.')
    parser.add_argument('--tasks-file', default=str(default_tasks_file_path().relative_to(repo_root())).replace('\\', '/'), help='Task source file used when --task-ids is empty.')
    parser.add_argument('--batch-size', type=int, default=5, help='Tasks per group (default: 5).')
    parser.add_argument('--rounds', type=int, default=3, help='Rounds per group (default: 3).')
    parser.add_argument('--start-group', type=int, default=1, help='1-based start group.')
    parser.add_argument('--end-group', type=int, default=0, help='1-based end group. 0 means all groups.')
    parser.add_argument('--timeout-sec', type=int, default=420, help='Timeout passed to llm_extract_task_obligations.py.')
    parser.add_argument('--round-id-prefix', default='jitter', help='round-id prefix for each run.')
    parser.add_argument('--out-raw', default='', help='Raw output JSON path. Default: logs/ci/<today>/sc-llm-obligations-jitter-batch5x3-raw.json')
    parser.add_argument('--delivery-profile', default=None, choices=known_delivery_profile_choices(), help='Delivery profile forwarded to llm_extract_task_obligations.py.')
    parser.add_argument('--security-profile', default='', choices=['', 'strict', 'host-safe'])
    parser.add_argument('--consensus-runs', type=int, default=1)
    parser.add_argument('--min-obligations', type=int, default=0)
    parser.add_argument('--garbled-gate', default='on', choices=['on', 'off'])
    parser.add_argument('--auto-escalate', default='on', choices=['on', 'off'])
    parser.add_argument('--escalate-max-runs', type=int, default=3)
    parser.add_argument('--max-schema-errors', type=int, default=5)
    parser.add_argument('--reuse-last-ok', action='store_true')
    parser.add_argument('--explain-reuse-miss', action='store_true')
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = repo_root()
    tasks_file = resolve_repo_path(args.tasks_file)
    args.tasks_file = str(tasks_file.relative_to(root)).replace('\\', '/') if tasks_file.is_relative_to(root) else str(tasks_file)

    if str(args.task_ids).strip():
        task_ids = parse_task_ids_csv(args.task_ids)
    else:
        task_ids = load_numeric_task_ids(tasks_file)
    if not task_ids:
        print('ERROR: no task ids resolved')
        return 2

    groups = chunk_task_ids(task_ids, args.batch_size)
    total_groups = len(groups)
    end_group = args.end_group if args.end_group > 0 else total_groups
    if args.start_group < 1 or end_group > total_groups or args.start_group > end_group:
        print(f'ERROR: invalid group range start={args.start_group} end={end_group} total={total_groups}')
        return 2

    out_raw = resolve_repo_path(args.out_raw) if str(args.out_raw).strip() else default_out_path()
    out_raw.parent.mkdir(parents=True, exist_ok=True)
    payload = load_or_init_payload(out_raw, task_ids=task_ids, groups=groups, rounds=args.rounds, batch_size=args.batch_size, args=args)
    rows: list[dict[str, Any]] = list(payload.get('rows') or [])

    for group_index in range(args.start_group, end_group + 1):
        task_group = groups[group_index - 1]
        print(f'[group {group_index}/{total_groups}] task_ids={task_group}')
        for round_index in range(1, args.rounds + 1):
            print(f'  [round {round_index}/{args.rounds}]')
            for task_id in task_group:
                round_id = f'{args.round_id_prefix}-g{group_index:02d}-r{round_index:02d}-t{task_id}'
                cmd = build_extract_command(task_id=task_id, timeout_sec=args.timeout_sec, round_id=round_id, args=args)
                process = subprocess.run(cmd, cwd=str(root), capture_output=True, text=True, encoding='utf-8', errors='replace')
                stdout = (process.stdout or '').strip()
                stderr = (process.stderr or '').strip()
                parsed_out_dir = parse_out_dir(stdout, stderr)
                task_dir, summary, verdict = read_task_outputs(task_id, parsed_out_dir=parsed_out_dir, fallback_rc=process.returncode)
                uncovered_ids = verdict.get('uncovered_obligation_ids', [])
                if not isinstance(uncovered_ids, list):
                    uncovered_ids = []
                row = {
                    'ts': dt.datetime.now().isoformat(timespec='seconds'),
                    'group': group_index,
                    'round': round_index,
                    'task_id': task_id,
                    'round_id': round_id,
                    'cp_returncode': process.returncode,
                    'stdout_tail': stdout.splitlines()[-1] if stdout else '',
                    'stderr_tail': stderr.splitlines()[-1] if stderr else '',
                    'out_dir': str(task_dir).replace('\\', '/') if task_dir else None,
                    'summary_status': summary.get('status'),
                    'summary_rc': summary.get('rc'),
                    'summary_error': summary.get('error'),
                    'verdict_status': verdict.get('status'),
                    'uncovered_count': len(uncovered_ids),
                    'uncovered_ids': uncovered_ids,
                }
                rows.append(row)
                payload['rows'] = rows
                out_raw.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
                print(f"    T{task_id}: verdict={row['verdict_status']} summary_rc={row['summary_rc']} uncovered={row['uncovered_count']}")

    print(f'wrote {out_raw.as_posix()}')
    print(f'rows_now={len(rows)}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
