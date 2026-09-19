#!/usr/bin/env python3
"""Plan, recommend, or execute MVG integration tests against an isolated snapshot."""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

from _mvg_manifest import read_manifest, recommend, validate_manifest
from _mvg_execution import execute_test
from _project_health_runtime_snapshot import prepare_snapshot

DEFAULT_MANIFEST = 'docs/testing/mvg/boot-pilot.json'


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def git(root: Path, *args: str) -> str:
    return subprocess.run(['git', '-C', str(root), *args], check=True, capture_output=True,
                          timeout=30).stdout.decode('utf-8').strip()


def changed_paths(root: Path, base: str, revision: str = 'HEAD', *, workspace: bool = True) -> tuple[list[str], str]:
    try:
        paths = set()
        if base:
            resolved = git(root, 'rev-parse', '--verify', base + '^{commit}')
            paths.update(git(root, 'diff', '--name-only', '--no-renames', '-z', resolved, revision).split('\0'))
        if workspace:
            paths.update(git(root, 'diff', '--name-only', '--no-renames', '-z', revision).split('\0'))
            paths.update(git(root, 'ls-files', '--others', '--exclude-standard', '-z').split('\0'))
        return sorted(paths - {''}), '' if paths - {''} else 'No changed paths; absence is not proof of no impact'
    except (subprocess.SubprocessError, OSError) as exc:
        return [], 'Git change range unavailable: ' + str(exc)


def register_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument('--manifest', default=DEFAULT_MANIFEST)
    parser.add_argument('--mode', choices=['plan', 'recommend', 'run'], default='plan')
    parser.add_argument('--snapshot', choices=['workspace', 'commit'], default='workspace')
    parser.add_argument('--revision', default='HEAD')
    parser.add_argument('--base', default='', help='Optional comparison base; recommendations never exclude tests')
    parser.add_argument('--godot-bin', default=os.environ.get('GODOT_BIN', ''))
    parser.add_argument('--timeout-sec', type=int, default=900, help='Global runtime budget')
    parser.add_argument('--challenge-input', action='store_true', help='After baseline passes, prove the manifest-declared disconnected UI input is detected')


def run(args: argparse.Namespace, root: Path | None = None) -> int:
    root = (root or Path(__file__).resolve().parents[2]).resolve()
    run_id = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ') + '-' + uuid.uuid4().hex[:8]
    out = root / 'logs/ci/mvg-acceptance' / run_id
    out.mkdir(parents=True)
    summary = {'schema_version': 'newrouge.mvg-acceptance.v1', 'run_id': run_id,
               'mode': args.mode, 'status': 'blocked', 'runtime_verified': False, 'steps': [],
               'authorizes_task_status_write': False}
    exit_code = 1
    try:
        if args.timeout_sec < 1:
            raise ValueError('timeout-sec must be positive')
        revision = git(root, 'rev-parse', '--verify', args.revision + '^{commit}')
        summary.update(base_commit=revision, workspace_dirty=bool(git(root, 'status', '--porcelain')))
        deadline = time.monotonic() + args.timeout_sec
        execution_root = root
        if args.mode == 'run' or args.snapshot == 'commit':
            execution_root = out / 'snapshot'
            snapshot = prepare_snapshot(root, execution_root, revision,
                                        'main' if args.snapshot == 'commit' else 'workspace', deadline)
            summary['source_revision'] = snapshot['source_revision']
            summary['snapshot_digest'] = snapshot['snapshot_digest']
            summary['input_manifest'] = str(out / 'input-manifest.json')
        doc = read_manifest(execution_root, args.manifest)
        errors = validate_manifest(execution_root, doc, executable=args.mode == 'run')
        summary.update(mvg_id=doc.get('mvg_id'), manifest=args.manifest,
                       coverage=doc.get('coverage', {}), validation_errors=errors)
        if errors:
            raise ValueError('; '.join(errors))
        comparison_revision = revision if args.snapshot == 'commit' else git(root, 'rev-parse', 'HEAD')
        paths, unknown = changed_paths(root, args.base, comparison_revision,
                                       workspace=args.snapshot == 'workspace')
        summary['recommendation'] = recommend(doc, paths, unknown_reason=unknown)
        summary['recommendation']['comparison_target'] = (summary.get('source_revision', 'workspace')
                                                          if args.snapshot == 'workspace' else revision)
        summary['recommendation']['includes_working_changes'] = args.snapshot == 'workspace'
        summary['required_tests'] = [test['id'] for test in doc['tests']]
        if args.mode != 'run':
            summary['status'] = 'planned' if args.mode == 'plan' else 'recommended'
            exit_code = 0
        else:
            env = dict(os.environ)
            # Isolate user:// without changing production scene/script bytes.
            env['APPDATA'] = str(out / 'user-data')
            env['XDG_DATA_HOME'] = str(out / 'user-data')
            env['GDUNIT_STRICT_EXIT_CODE'] = '1'
            env.pop('MVG_INPUT_CHALLENGE', None)
            godot_ready = False
            for test in doc['tests']:
                if time.monotonic() >= deadline:
                    raise TimeoutError('Global runtime budget exhausted')
                result = execute_test(execution_root, test, out / test['id'], args.godot_bin,
                                      deadline, env, prewarm=not godot_ready)
                summary['steps'].append(result)
                if result['status'] != 'passed':
                    raise RuntimeError('Required test failed or is unverified: ' + test['id'])
                if test['kind'] == 'gdunit':
                    godot_ready = True
            if args.challenge_input:
                targets = [test for test in doc['tests'] if test.get('challenge')]
                if not targets:
                    raise ValueError('Manifest has no input challenge target')
                summary['challenges'] = []
                for test in targets:
                    challenge = str(test.get('challenge') or '')
                    marker = str(test.get('challenge_failure_marker') or '')
                    if not challenge or not marker:
                        raise ValueError('Input challenge requires challenge and challenge_failure_marker')
                    env['MVG_INPUT_CHALLENGE'] = challenge
                    result = execute_test(execution_root, test, out / ('challenge-' + test['id']),
                                          args.godot_bin, deadline, env, prewarm=not godot_ready)
                    # A crash, missing runtime or compilation error is NOT a detected defect.
                    detected = (result['exit_code'] not in {0, 124, 127}
                                and result['evidence']['failed'] > 0
                                and result['evidence']['skipped'] == 0
                                and any(marker in message for message in result['evidence']['failure_messages'])
                                and result['evidence']['reason'] == 'failed-skipped-or-empty-tests')
                    result['challenge'] = challenge
                    result['failure_marker'] = marker
                    result['defect_detected'] = detected
                    summary['challenges'].append(result)
                    if not detected:
                        raise RuntimeError('Disconnected input was not demonstrated by a test assertion')
                env.pop('MVG_INPUT_CHALLENGE', None)
            summary.update(status='passed', runtime_verified=True)
            exit_code = 0
    except (ValueError, KeyError, TypeError, OSError, RuntimeError, subprocess.SubprocessError, TimeoutError) as exc:
        summary['reason'] = str(exc)
    finally:
        summary['finished_at'] = datetime.now(timezone.utc).isoformat()
        write_json(out / 'summary.json', summary)
        print(json.dumps({'status': summary['status'], 'runtime_verified': summary['runtime_verified'],
                          'summary': str(out / 'summary.json'), 'reason': summary.get('reason', '')}))
    return exit_code


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    register_arguments(parser)
    return run(parser.parse_args(argv))


if __name__ == '__main__':
    raise SystemExit(main())
