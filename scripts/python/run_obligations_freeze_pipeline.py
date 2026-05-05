#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import subprocess
from pathlib import Path
from typing import Any

from _obligations_freeze_pipeline_steps import (
    build_jitter_batch_command,
    parse_eval_aggregate,
    run_step,
    write_pipeline_summary,
)
from _obligations_freeze_runtime import (
    known_delivery_profile_choices,
    resolve_delivery_and_security,
    resolve_repo_path,
)


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def today_str() -> str:
    return dt.date.today().strftime('%Y-%m-%d')


def parse_args() -> argparse.Namespace:
    today = today_str()
    parser = argparse.ArgumentParser(description='Run obligations freeze orchestration pipeline.')
    parser.add_argument('--out-dir', default=f'logs/ci/{today}/sc-obligations-freeze-pipeline', help='Pipeline artifact directory.')
    parser.add_argument('--skip-jitter', action='store_true', help='Skip jitter batch step and reuse an existing --raw file.')
    parser.add_argument('--raw', default='', help='Raw jitter JSON. Required when --skip-jitter is used.')
    parser.add_argument('--task-ids', default='')
    parser.add_argument('--tasks-file', default='', help='Tasks JSON path. Empty means resolve default taskmaster/tasks or examples/taskmaster/tasks at runtime.')
    parser.add_argument('--batch-size', type=int, default=5)
    parser.add_argument('--rounds', type=int, default=3)
    parser.add_argument('--start-group', type=int, default=1)
    parser.add_argument('--end-group', type=int, default=0)
    parser.add_argument('--timeout-sec', type=int, default=420)
    parser.add_argument('--round-id-prefix', default='jitter')
    parser.add_argument('--delivery-profile', default=None, choices=known_delivery_profile_choices(), help='Delivery profile forwarded to jitter/extract steps.')
    parser.add_argument('--security-profile', default='', choices=('', 'strict', 'host-safe'))
    parser.add_argument('--consensus-runs', type=int, default=1)
    parser.add_argument('--min-obligations', type=int, default=0)
    parser.add_argument('--garbled-gate', default='on', choices=('on', 'off'))
    parser.add_argument('--auto-escalate', default='on', choices=('on', 'off'))
    parser.add_argument('--escalate-max-runs', type=int, default=3)
    parser.add_argument('--max-schema-errors', type=int, default=5)
    parser.add_argument('--reuse-last-ok', action='store_true')
    parser.add_argument('--explain-reuse-miss', action='store_true')
    parser.add_argument('--override-rerun', default='', help='Optional rerun rows JSON for refresh step.')
    parser.add_argument('--draft-json', default='', help='Whitelist draft output path. Default: <out-dir>/obligations-freeze-whitelist.draft.json')
    parser.add_argument('--draft-md', default='', help='Whitelist draft report path. Default: <out-dir>/obligations-freeze-whitelist-draft.md')
    parser.add_argument('--eval-dir', default='', help='Evaluation output directory. Default: <out-dir>/freeze-eval')
    parser.add_argument('--allow-draft-eval', dest='allow_draft_eval', action='store_true', default=True, help='Allow evaluating draft whitelist in evaluate step (default: enabled).')
    parser.add_argument('--no-allow-draft-eval', dest='allow_draft_eval', action='store_false', help='Disable --allow-draft and require non-draft whitelist for evaluate step.')
    parser.add_argument('--require-judgable', action='store_true', help='Fail pipeline if evaluation aggregate.judgable is false.')
    parser.add_argument('--require-freeze-pass', action='store_true', help='Fail pipeline if evaluation aggregate.freeze_gate_pass is false.')
    parser.add_argument('--approve-promote', action='store_true', help='Allow promotion step. Disabled by default as stop-loss.')
    parser.add_argument('--baseline-dir', default='.taskmaster/config/obligations-freeze-baselines')
    parser.add_argument('--baseline-date', default=today)
    parser.add_argument('--baseline-tag', default='')
    parser.add_argument('--current-baseline', default='.taskmaster/config/obligations-freeze-whitelist.baseline.current.json')
    parser.add_argument('--promote-report', default='', help='Promote report path. Default: <out-dir>/obligations-freeze-promote.md')
    parser.add_argument('--jitter-timeout-sec', type=int, default=21600, help='External timeout for jitter batch step.')
    parser.add_argument('--step-timeout-sec', type=int, default=1800, help='External timeout for non-jitter steps.')
    return parser.parse_args()


def _init_pipeline_payload(
    out_dir: Path,
    raw_path: Path,
    summary_path: Path,
    summary_report: Path,
    refreshed_summary: Path,
    refreshed_report: Path,
    draft_json: Path,
    draft_md: Path,
    eval_dir: Path,
    promote_report: Path,
    *,
    delivery_profile: str,
    security_profile: str,
    security_override: bool,
) -> dict[str, Any]:
    return {
        'schema_version': '1.0.0',
        'cmd': 'run_obligations_freeze_pipeline.py',
        'date': today_str(),
        'status': 'ok',
        'delivery_profile': delivery_profile,
        'security_profile': security_profile,
        'security_override': bool(security_override),
        'out_dir': str(out_dir),
        'steps': [],
        'paths': {
            'raw': str(raw_path),
            'summary': str(summary_path),
            'summary_report': str(summary_report),
            'refreshed_summary': str(refreshed_summary),
            'refreshed_report': str(refreshed_report),
            'draft_json': str(draft_json),
            'draft_md': str(draft_md),
            'eval_dir': str(eval_dir),
            'promote_report': str(promote_report),
        },
    }


def _append_and_fail(pipeline: dict[str, Any], out_dir: Path, step: dict[str, Any]) -> int:
    pipeline['steps'].append(step)
    pipeline['status'] = 'fail'
    write_pipeline_summary(out_dir, pipeline)
    return int(step['rc'])


def main() -> int:
    args = parse_args()
    root = repo_root()
    out_dir = resolve_repo_path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    delivery_profile, security_profile = resolve_delivery_and_security(args.delivery_profile, args.security_profile)
    security_override = bool(str(args.security_profile).strip())
    args.delivery_profile = delivery_profile

    raw_path = resolve_repo_path(args.raw) if str(args.raw).strip() else out_dir / 'sc-llm-obligations-jitter-batch5x3-raw.json'
    summary_path = out_dir / 'sc-llm-obligations-jitter-batch5x3-summary.json'
    summary_report = out_dir / 'sc-llm-obligations-jitter-batch5x3-report.md'
    refreshed_summary = out_dir / 'sc-llm-obligations-jitter-batch5x3-summary-refreshed.json'
    refreshed_report = out_dir / 'sc-llm-obligations-jitter-batch5x3-refreshed-report.md'
    draft_json = resolve_repo_path(args.draft_json) if str(args.draft_json).strip() else out_dir / 'obligations-freeze-whitelist.draft.json'
    draft_md = resolve_repo_path(args.draft_md) if str(args.draft_md).strip() else out_dir / 'obligations-freeze-whitelist-draft.md'
    eval_dir = resolve_repo_path(args.eval_dir) if str(args.eval_dir).strip() else out_dir / 'freeze-eval'
    promote_report = resolve_repo_path(args.promote_report) if str(args.promote_report).strip() else out_dir / 'obligations-freeze-promote.md'

    pipeline = _init_pipeline_payload(
        out_dir,
        raw_path,
        summary_path,
        summary_report,
        refreshed_summary,
        refreshed_report,
        draft_json,
        draft_md,
        eval_dir,
        promote_report,
        delivery_profile=delivery_profile,
        security_profile=security_profile,
        security_override=security_override,
    )

    try:
        if not args.skip_jitter:
            step = run_step('jitter-batch', build_jitter_batch_command(args, raw_path=raw_path, root=root), out_dir, root=root, timeout_sec=max(60, args.jitter_timeout_sec))
            if step['rc'] != 0:
                return _append_and_fail(pipeline, out_dir, step)
            pipeline['steps'].append(step)
        elif not raw_path.exists():
            pipeline['status'] = 'fail'
            pipeline['error'] = f'missing raw file for --skip-jitter: {raw_path.as_posix()}'
            write_pipeline_summary(out_dir, pipeline)
            print(f"ERROR: {pipeline['error']}")
            return 2

        step = run_step('build-summary', ['py', '-3', 'scripts/python/build_obligations_jitter_summary.py', '--raw', str(raw_path), '--out-summary', str(summary_path), '--out-report', str(summary_report)], out_dir, root=root, timeout_sec=max(60, args.step_timeout_sec))
        if step['rc'] != 0:
            return _append_and_fail(pipeline, out_dir, step)
        pipeline['steps'].append(step)

        summary_for_following = summary_path
        if str(args.override_rerun).strip():
            override_rerun = resolve_repo_path(args.override_rerun)
            step = run_step('refresh-summary', ['py', '-3', 'scripts/python/refresh_obligations_jitter_summary_with_overrides.py', '--base-summary', str(summary_path), '--override-rerun', str(override_rerun), '--out-summary', str(refreshed_summary), '--out-report', str(refreshed_report)], out_dir, root=root, timeout_sec=max(60, args.step_timeout_sec))
            if step['rc'] != 0:
                return _append_and_fail(pipeline, out_dir, step)
            pipeline['steps'].append(step)
            summary_for_following = refreshed_summary

        step = run_step('generate-draft', ['py', '-3', 'scripts/python/generate_obligations_freeze_whitelist_draft.py', '--summary', str(summary_for_following), '--out-json', str(draft_json), '--out-md', str(draft_md)], out_dir, root=root, timeout_sec=max(60, args.step_timeout_sec))
        if step['rc'] != 0:
            return _append_and_fail(pipeline, out_dir, step)
        pipeline['steps'].append(step)

        eval_cmd = ['py', '-3', 'scripts/python/evaluate_obligations_freeze_whitelist.py', '--whitelist', str(draft_json), '--summary', str(summary_for_following), '--out-dir', str(eval_dir)]
        if bool(args.allow_draft_eval):
            eval_cmd.append('--allow-draft')
        step = run_step('evaluate', eval_cmd, out_dir, root=root, timeout_sec=max(60, args.step_timeout_sec))
        if step['rc'] != 0:
            return _append_and_fail(pipeline, out_dir, step)
        pipeline['steps'].append(step)

        eval_aggregate = parse_eval_aggregate(eval_dir)
        pipeline['evaluation'] = eval_aggregate
        if bool(args.require_judgable) and (not eval_aggregate or not bool(eval_aggregate.get('judgable'))):
            pipeline['status'] = 'fail'
            pipeline['error'] = 'evaluation aggregate.judgable is false'
            write_pipeline_summary(out_dir, pipeline)
            print('ERROR: evaluation aggregate.judgable is false')
            return 2
        if bool(args.require_freeze_pass) and (not eval_aggregate or not bool(eval_aggregate.get('freeze_gate_pass'))):
            pipeline['status'] = 'fail'
            pipeline['error'] = 'evaluation aggregate.freeze_gate_pass is false'
            write_pipeline_summary(out_dir, pipeline)
            print('ERROR: evaluation aggregate.freeze_gate_pass is false')
            return 2

        if bool(args.approve_promote):
            if not str(args.baseline_tag).strip():
                pipeline['status'] = 'fail'
                pipeline['error'] = 'baseline-tag is required when --approve-promote is used'
                write_pipeline_summary(out_dir, pipeline)
                print('ERROR: baseline-tag is required when --approve-promote is used')
                return 2
            step = run_step('promote', ['py', '-3', 'scripts/python/promote_obligations_freeze_baseline.py', '--draft', str(draft_json), '--baseline-dir', args.baseline_dir, '--baseline-date', args.baseline_date, '--baseline-tag', args.baseline_tag, '--current', args.current_baseline, '--report', str(promote_report)], out_dir, root=root, timeout_sec=max(60, args.step_timeout_sec))
            if step['rc'] != 0:
                return _append_and_fail(pipeline, out_dir, step)
            pipeline['steps'].append(step)
        else:
            pipeline['steps'].append({'name': 'promote', 'status': 'skipped', 'rc': 0, 'reason': 'approve_promote_disabled'})

        pipeline['active_summary'] = str(summary_for_following)
        write_pipeline_summary(out_dir, pipeline)
        print(f"OBLIGATIONS_FREEZE_PIPELINE status={pipeline['status']} out={out_dir.as_posix()}")
        return 0
    except subprocess.TimeoutExpired as exc:
        pipeline['status'] = 'fail'
        pipeline['error'] = f'step timeout: {exc}'
        write_pipeline_summary(out_dir, pipeline)
        print(f"ERROR: {pipeline['error']}")
        return 124


if __name__ == '__main__':
    raise SystemExit(main())
