#!/usr/bin/env python3
"""Optional seeded MVG mutation experiment for Sanguo startup validation; not a default gate."""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import time
import uuid
from pathlib import Path

from _mvg_execution import execute_test
from _project_health_runtime_snapshot import prepare_snapshot
from run_mvg_acceptance import git, write_json

SOURCE = 'Game.Core/Contracts/Sanguo/GameStartConfigValidator.cs'
MUTANTS = [
    ('allow-one-player',
     'private static readonly int[] AllowedPlayersCounts = { 2, 3, 4 };',
     'private static readonly int[] AllowedPlayersCounts = { 1, 2, 3, 4 };'),
    ('allow-zero-starting-money',
     'private static readonly int[] AllowedStartingMoneyPresets = { 5000, 10000, 20000 };',
     'private static readonly int[] AllowedStartingMoneyPresets = { 0, 5000, 10000, 20000 };'),
]
TEST = {
    'id': 'boot-mutation-probes',
    'kind': 'dotnet',
    'evidence_level': 'domain-integration',
    'selector': 'Game.Core.Tests.Tasks.Task50GameStartConfigTests',
    'min_tests': 15,
}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--timeout-sec', type=int, default=900)
    parser.add_argument('--snapshot', choices=['workspace', 'commit'], default='workspace')
    parser.add_argument('--revision', default='HEAD')
    args = parser.parse_args(argv)
    root = Path(__file__).resolve().parents[2]
    out = root / 'logs/ci/mvg-mutation' / uuid.uuid4().hex
    out.mkdir(parents=True)
    summary = {
        'schema_version': 'newrouge.mvg-mutation-probe.v1',
        'status': 'blocked',
        'scope': SOURCE,
        'mutants': [],
        'default_gate': False,
    }
    rc = 1
    try:
        if args.timeout_sec < 1:
            raise ValueError('timeout-sec must be positive')
        revision = git(root, 'rev-parse', '--verify', args.revision + '^{commit}')
        summary['base_commit'] = revision
        deadline = time.monotonic() + args.timeout_sec
        work = out / 'snapshot'
        summary['inputs'] = prepare_snapshot(
            root, work, revision, 'main' if args.snapshot == 'commit' else 'workspace', deadline
        )
        baseline = execute_test(work, TEST, out / 'baseline', '', deadline)
        summary['baseline'] = baseline
        if baseline['status'] != 'passed':
            raise RuntimeError('Baseline did not pass; mutation results would be uninterpretable')
        source = work / SOURCE
        original = source.read_bytes()
        summary['source_sha256'] = hashlib.sha256(original).hexdigest()
        try:
            for name, before, after in MUTANTS:
                if original.count(before.encode()) != 1:
                    raise ValueError('Mutation target drift: ' + name)
                source.write_bytes(original.replace(before.encode(), after.encode()))
                result = execute_test(work, TEST, out / name, '', deadline)
                evidence = result['evidence']
                killed = (
                    result['exit_code'] not in {0, 124, 127}
                    and evidence['failed'] > 0
                    and evidence['tests'] >= TEST['min_tests']
                    and evidence['skipped'] == 0
                    and evidence['reason'] == 'failed-skipped-or-empty-tests'
                )
                status = 'killed' if killed else ('survived' if result['status'] == 'passed' else 'unverified')
                summary['mutants'].append({
                    'id': name,
                    'before': before,
                    'after': after,
                    'status': status,
                    'execution': result,
                })
                source.write_bytes(original)
                if time.monotonic() >= deadline:
                    raise TimeoutError('Global mutation budget exhausted')
        finally:
            source.write_bytes(original)
        summary['status'] = (
            'passed' if all(row['status'] == 'killed' for row in summary['mutants'])
            else 'needs-investigation'
        )
        rc = 0 if summary['status'] == 'passed' else 1
    except (OSError, ValueError, RuntimeError, TimeoutError, subprocess.SubprocessError) as exc:
        summary['reason'] = str(exc)
    finally:
        write_json(out / 'summary.json', summary)
        print(json.dumps({'status': summary['status'], 'summary': str(out / 'summary.json')}))
    return rc


if __name__ == '__main__':
    raise SystemExit(main())
