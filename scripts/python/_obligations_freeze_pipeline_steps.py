from __future__ import annotations

import json
import shlex
import subprocess
from pathlib import Path
from typing import Any

from _obligations_freeze_runtime import default_tasks_file_path, resolve_delivery_and_security, resolve_repo_path


def build_jitter_batch_command(args: Any, *, raw_path: Path, root: Path) -> list[str]:
    tasks_file = resolve_repo_path(str(getattr(args, 'tasks_file', '') or ''), root=root) if str(getattr(args, 'tasks_file', '') or '').strip() else default_tasks_file_path(root)
    delivery_profile, security_profile = resolve_delivery_and_security(getattr(args, 'delivery_profile', None), getattr(args, 'security_profile', None))
    has_security_override = bool(str(getattr(args, 'security_profile', '') or '').strip())
    cmd = [
        'py',
        '-3',
        'scripts/python/run_obligations_jitter_batch5x3.py',
        '--tasks-file',
        str(tasks_file.relative_to(root)).replace('\\', '/') if tasks_file.is_relative_to(root) else str(tasks_file),
        '--batch-size',
        str(args.batch_size),
        '--rounds',
        str(args.rounds),
        '--start-group',
        str(args.start_group),
        '--end-group',
        str(args.end_group),
        '--timeout-sec',
        str(args.timeout_sec),
        '--round-id-prefix',
        args.round_id_prefix,
        '--delivery-profile',
        delivery_profile,
        '--consensus-runs',
        str(args.consensus_runs),
        '--min-obligations',
        str(args.min_obligations),
        '--garbled-gate',
        args.garbled_gate,
        '--auto-escalate',
        args.auto_escalate,
        '--escalate-max-runs',
        str(args.escalate_max_runs),
        '--max-schema-errors',
        str(args.max_schema_errors),
        '--out-raw',
        str(raw_path),
    ]
    if str(getattr(args, 'task_ids', '') or '').strip():
        cmd += ['--task-ids', args.task_ids]
    if has_security_override:
        cmd += ['--security-profile', security_profile]
    if bool(args.reuse_last_ok):
        cmd.append('--reuse-last-ok')
    if bool(args.explain_reuse_miss):
        cmd.append('--explain-reuse-miss')
    return cmd


def run_step(step_name: str, cmd: list[str], out_dir: Path, *, root: Path, timeout_sec: int) -> dict[str, Any]:
    log_path = out_dir / f'{step_name}.log'
    process = subprocess.run(cmd, cwd=str(root), capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=timeout_sec)
    cmd_text = ' '.join(shlex.quote(token) for token in cmd)
    log_path.write_text('\n'.join([f'$ {cmd_text}', '', '### stdout', process.stdout or '', '', '### stderr', process.stderr or '']), encoding='utf-8')
    return {'name': step_name, 'status': 'ok' if process.returncode == 0 else 'fail', 'rc': process.returncode, 'cmd': cmd, 'log': str(log_path)}


def write_pipeline_summary(out_dir: Path, payload: dict[str, Any]) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / 'summary.json').write_text(json.dumps(payload, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def parse_eval_aggregate(eval_dir: Path) -> dict[str, Any] | None:
    summary_file = eval_dir / 'summary.json'
    if not summary_file.exists():
        return None
    try:
        parsed = json.loads(summary_file.read_text(encoding='utf-8'))
    except Exception:
        return None
    aggregate = parsed.get('aggregate')
    return aggregate if isinstance(aggregate, dict) else None
