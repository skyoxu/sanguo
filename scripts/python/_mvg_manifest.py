"""MVG integration ownership and test inventory. Taskmaster owns task status."""
from __future__ import annotations

import json
import re
from pathlib import Path, PurePosixPath

SCHEMA = 'newrouge.mvg-integration.v1'
LEVELS = {'dotnet': {'domain-integration'},
          'gdunit': {'scene-method', 'engine-input'}}
COVERAGE_MODES = {'pilot', 'critical', 'full'}


def safe_path(root: Path, value: str) -> Path:
    if not isinstance(value, str) or not value or '\\' in value or ':' in value:
        raise ValueError('Expected a repository-relative POSIX path')
    path = PurePosixPath(value)
    if path.is_absolute() or '..' in path.parts:
        raise ValueError('Path escapes repository')
    target = root.joinpath(*path.parts)
    if not target.resolve().is_relative_to(root.resolve()):
        raise ValueError('Path resolves outside repository')
    return target


def read_manifest(root: Path, path: str) -> dict:
    return json.loads(safe_path(root, path).read_text(encoding='utf-8-sig'))


def validate_manifest(root: Path, doc: dict, executable: bool = False) -> list[str]:
    errors = []
    try:
        if doc.get('schema_version') != SCHEMA:
            errors.append('Unsupported schema_version')
        if not re.fullmatch(r'[a-z0-9][a-z0-9-]*', doc.get('mvg_id', '')):
            errors.append('Invalid mvg_id')
        tasks_doc = read_manifest(root, '.taskmaster/tasks/tasks.json')
        task_rows = {int(row['id']): row for row in tasks_doc['master']['tasks']}
        tasks = set(task_rows)
        flows, tests = doc['flows'], doc['tests']
        if not flows or not tests:
            errors.append('At least one flow and test are required')
        coverage = doc.get('coverage')
        if not isinstance(coverage, dict):
            errors.append('coverage contract is required')
        else:
            mode = coverage.get('mode')
            if mode not in COVERAGE_MODES:
                errors.append('coverage: invalid mode')
            scope_id = coverage.get('scope_id', '')
            if not isinstance(scope_id, str) or not re.fullmatch(r'[a-z0-9][a-z0-9-]*', scope_id):
                errors.append('coverage: invalid scope_id')
            required_flow_ids = coverage.get('required_flow_ids')
            flow_ids = [flow['id'] for flow in flows]
            if (not isinstance(required_flow_ids, list)
                    or required_flow_ids != flow_ids):
                errors.append('coverage: required_flow_ids must exactly match manifest flow order')
            excluded_claims = coverage.get('excluded_claims')
            if (not isinstance(excluded_claims, list) or not excluded_claims
                    or any(not isinstance(item, str) or not item.strip() for item in excluded_claims)):
                errors.append('coverage: excluded_claims must be a non-empty string array')

            referenced_tasks = sorted({task_id for flow in flows for task_id in flow.get('task_ids', [])
                                       if isinstance(task_id, int) and task_id in task_rows})
            non_done = sorted(task_id for task_id in referenced_tasks
                              if str(task_rows[task_id].get('status', '')).lower() != 'done')
            declared_blockers = coverage.get('blocking_task_ids', [])
            if (not isinstance(declared_blockers, list)
                    or any(type(task_id) is not int for task_id in declared_blockers)
                    or sorted(declared_blockers) != non_done):
                errors.append(f'coverage: blocking_task_ids must match non-done scoped tasks {non_done}')
            if mode == 'critical' and len(flows) < 2:
                errors.append('coverage: critical mode requires at least two flows')
            if mode == 'full' and len(flows) < 3:
                errors.append('coverage: full mode requires at least three flows')
            if executable and mode in {'critical', 'full'} and non_done:
                errors.append(f'coverage: executable {mode} scope blocked by non-done tasks {non_done}')
        for rows, label in [(flows, 'flow'), (tests, 'test')]:
            ids = [row['id'] for row in rows]
            if len(ids) != len(set(ids)) or any(not re.fullmatch(r'[a-z0-9][a-z0-9-]*', i) for i in ids):
                errors.append(f'Duplicate or invalid {label} id')
        test_ids = {row['id'] for row in tests}
        for test in tests:
            label = test['id']
            if test['state'] not in {'planned', 'implemented'}:
                errors.append(f'{label}: invalid state')
            if executable and test['state'] != 'implemented':
                errors.append(f'{label}: planned test cannot be executed')
            if test['evidence_level'] not in LEVELS.get(test['kind'], set()):
                errors.append(f'{label}: invalid evidence level')
            target = safe_path(root, test['path'])
            prefix = 'Game.Core.Tests/' if test['kind'] == 'dotnet' else 'Tests.Godot/tests/'
            suffix = '.cs' if test['kind'] == 'dotnet' else '.gd'
            if not test['path'].startswith(prefix) or not test['path'].endswith(suffix):
                errors.append(f'{label}: invalid test path')
            if test['state'] == 'implemented' and not target.is_file():
                errors.append(f'{label}: missing implemented test')
            if type(test['min_tests']) is not int or test['min_tests'] < 1:
                errors.append(f'{label}: min_tests must be positive')
            if test['kind'] == 'dotnet' and not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_.]+', test['selector']):
                errors.append(f'{label}: selector must be a class name')
        used_tests = set()
        for flow in flows:
            label = flow['id']
            ids = flow['task_ids']
            if not ids or any(type(i) is not int or i not in tasks for i in ids):
                errors.append(f'{label}: unknown or empty task_ids')
            if not flow['outcome'].strip() or not flow['source_paths'] or not flow['handoffs']:
                errors.append(f'{label}: outcome, sources and handoffs are required')
            for path in flow['source_paths']:
                if not safe_path(root, path).is_file():
                    errors.append(f'{label}: missing source {path}')
            coverage = set(flow['test_ids'])
            if not coverage or not coverage <= test_ids:
                errors.append(f'{label}: unknown or empty test coverage')
            used_tests.update(coverage)
            for edge in flow['handoffs']:
                if any(type(edge[key]) is not int or edge[key] not in ids
                       for key in ('producer_task', 'consumer_task', 'owner_task')):
                    errors.append(f'{label}: each handoff needs known producer, consumer and owner tasks')
                if not safe_path(root, edge['contract_ref']).is_file() or not edge['behavior'].strip():
                    errors.append(f'{label}: handoff contract and behavior are required')
                if not edge['test_ids'] or not set(edge['test_ids']) <= coverage:
                    errors.append(f'{label}: uncovered handoff')
        if used_tests != test_ids:
            errors.append('Test inventory contains tests not assigned to a flow')
    except (KeyError, TypeError, ValueError, AttributeError, OSError) as exc:
        errors.append(f'Malformed manifest: {exc}')
    return errors


def recommend(doc: dict, changed_paths: list[str], *, unknown_reason: str = '') -> dict:
    """Explicit mappings are positive evidence, never proof of no impact."""
    mapped, matched, evidence = set(), [], []
    tests = {test['id']: test for test in doc['tests']}
    for flow in doc['flows']:
        paths = set(flow['source_paths']) | {edge['contract_ref'] for edge in flow['handoffs']}
        paths.update(tests[i]['path'] for i in flow['test_ids'])
        hits = sorted(paths.intersection(changed_paths))
        if hits:
            matched.append(flow['id'])
            mapped.update(hits)
            evidence.append({'flow_id': flow['id'], 'changed_paths': hits, 'test_ids': flow['test_ids']})
    unmapped = sorted(set(changed_paths) - mapped)
    coverage = doc.get('coverage') if isinstance(doc.get('coverage'), dict) else {}
    return {'recommendation': 'full-mvg' if unmapped or not matched or unknown_reason else 'related-first',
            'matched_flows': matched, 'evidence_paths': evidence, 'unmapped_changes': unmapped,
            'unknown_reason': unknown_reason,
            'required_tests': [test['id'] for test in doc['tests']],
            'manifest_coverage_mode': coverage.get('mode', 'unknown'),
            'manifest_scope_id': coverage.get('scope_id', ''),
            'manifest_blocking_task_ids': coverage.get('blocking_task_ids', []),
            'authorizes_test_exclusion': False,
            'analysis_scope': 'Explicit manifest source/contract/test mappings; full-mvg means all tests in this manifest, not automatic product-wide coverage'}
