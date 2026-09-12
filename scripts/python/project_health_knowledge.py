#!/usr/bin/env python3
"""Main-only investigation CLI used by the project-health HTTP service."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath

from _knowledge_catalog_builder import DirectorySnapshot, LocalMainSnapshot, build_layers
from _knowledge_locator_core import locate, tokens
from _project_health_tasks import attach_task_scenes, task_details, task_page, task_summary
from _project_health_navigation import ASSET_SUFFIXES, CONFIG_SUFFIXES, build_navigation
from impact_analysis_index import build_and_publish_index
from impact_analysis_index import ImpactIndexError
from impact_analyzer import ImpactAnalyzer

CONFIG = 'scripts/python/project_health_knowledge_config.json'
REF = 'refs/heads/main'
SOURCE_PATHS = ['.taskmaster/tasks', 'docs/prd', 'docs/adr', 'docs/architecture',
                'docs/agents', 'docs/workflows', 'Game.Core', 'Game.Godot',
                'Game.Core.Tests', 'Tests.Godot', 'README.md', 'AGENTS.md',
                'DELIVERY_PROFILE.md', 'workflow.md', 'docs/testing-framework.md']
SOURCE_PATH_BINDINGS = dict(zip(
    ('tasks', 'product_requirements', 'architecture_decisions', 'architecture', 'agent_rules',
     'workflows', 'domain_code', 'engine_code', 'domain_tests', 'engine_tests', 'project_entry',
     'repository_rules', 'delivery_profile', 'root_workflow', 'testing_rules'),
    SOURCE_PATHS,
))
DEFAULT_CONFIG = {
    'source_paths': SOURCE_PATHS,
    'source_path_bindings': SOURCE_PATH_BINDINGS,
    'gdd_paths': ['docs/gdd/ui-gdd-flow.md'],
    'task_scene_bindings': [{
        'task_id': 115, 'scene': 'Game.Godot/Scenes/Reward.tscn', 'node': '.',
        'script': 'Game.Godot/Scripts/RewardScene.gd',
        'witness': 'func _claim_reward(reward_type: String, selected_card_id: String, selected_index: int) -> void:'
    }],
    'query_aliases': {'奖励': ['Reward'], '存档': ['Save'], '战斗': ['Combat']},
}


def base_dir(root: Path) -> Path:
    return root / 'logs/ci/project-health-knowledge'


def write_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + '.' + uuid.uuid4().hex + '.tmp')
    temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
    os.replace(temporary, path)


def read_json(path: Path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def git(root: Path, *args: str) -> str:
    result = subprocess.run(['git', '-C', str(root), *args], capture_output=True,
                            text=True, encoding='utf-8', errors='replace', timeout=120,
                            env={**os.environ, 'GIT_TERMINAL_PROMPT': '0'})
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or 'Git operation failed')
    return result.stdout.strip()


def safe_file(root: Path, relative: str) -> Path:
    p = PurePosixPath(relative)
    if not relative or not p.parts or relative == '.' or '\\' in relative or ':' in relative or p.is_absolute() or '..' in p.parts:
        raise ValueError('Expected a repository-relative path')
    candidate = root.joinpath(*p.parts)
    candidate.resolve().relative_to(root.resolve())
    if any(parent.is_symlink() or getattr(parent, 'is_junction', lambda: False)()
           for parent in (candidate, *candidate.parents) if parent != root.parent):
        raise ValueError('Symlinks are not supported')
    return candidate


def load_config(root: Path) -> dict:
    path = root / CONFIG
    config = read_json(path) if path.exists() else DEFAULT_CONFIG.copy()
    return validate_config(root, config)


def validate_config(root: Path, config: dict) -> dict:
    required = {'source_paths', 'gdd_paths', 'task_scene_bindings', 'query_aliases'}
    if (not isinstance(config, dict) or not required.issubset(config)
            or set(config) - required not in (set(), {'source_path_bindings'})):
        raise ValueError('Unexpected configuration keys')
    bindings = config.get('source_path_bindings')
    if bindings is not None:
        if (not isinstance(bindings, dict) or set(bindings) - set(SOURCE_PATH_BINDINGS)
                or not all(isinstance(value, str) for value in bindings.values())):
            raise ValueError('source_path_bindings must contain known string-valued categories')
        if [value for value in bindings.values() if value] != config['source_paths']:
            raise ValueError('source_paths must match non-empty source_path_bindings values')
    if not isinstance(config['source_paths'], list) or not config['source_paths'] or len(config['source_paths']) > 100:
        raise ValueError('source_paths must contain 1 to 100 repository-relative sources')
    if not isinstance(config['gdd_paths'], list):
        raise ValueError('gdd_paths must be an array')
    for value in config['source_paths'] + config['gdd_paths']:
        if not isinstance(value, str) or not value or value.split('/')[0].lower() in {'logs', '.git'}:
            raise ValueError('Invalid source path')
        if any(part in {'', '.', '..'} for part in value.split('/')):
            raise ValueError('Source paths must be canonical repository-relative paths')
        safe_file(root, value)
    if not isinstance(config['gdd_paths'], list) or len(config['gdd_paths']) > 100:
        raise ValueError('gdd_paths must be an array of at most 100 paths')
    for value in config['gdd_paths']:
        if not isinstance(value, str):
            raise ValueError('GDD paths must be strings')
        safe_file(root, value)
        if Path(value).suffix.lower() not in {'.md', '.txt', '.json'}:
            raise ValueError('GDD sources must be UTF-8 Markdown, text or JSON')
    if not isinstance(config['task_scene_bindings'], list) or not all(isinstance(x, dict) for x in config['task_scene_bindings']):
        raise ValueError('task_scene_bindings must be an array of objects')
    if not isinstance(config['query_aliases'], dict) or not all(
        isinstance(k, str) and isinstance(v, list) and all(isinstance(q, str) and len(q) <= 500 for q in v)
        for k, v in config['query_aliases'].items()
    ):
        raise ValueError('query_aliases must map text to arrays of query strings')
    return config


def scan(root: Path) -> dict:
    base = base_dir(root)
    base.mkdir(parents=True, exist_ok=True)
    lock = base / 'scan.lock'
    try:
        lock.mkdir()
    except FileExistsError as exc:
        raise RuntimeError('Scan already running; inspect scan.lock after an interrupted process') from exc
    try:
        config = load_config(root)
        if (root / '.git').exists() or (root / '.git').is_file():
            trusted = LocalMainSnapshot(root, REF)
            revision = trusted.commit
        else:
            trusted = DirectorySnapshot(root, config['source_paths'] + config['gdd_paths'] + ['knowledge/policies'])
            revision = trusted.commit
        required = ['.taskmaster/tasks/tasks.json', '.taskmaster/tasks/tasks_back.json',
                    '.taskmaster/tasks/tasks_gameplay.json', 'knowledge/policies/consumer-policies.v1.json',
                    'knowledge/policies/source-exclusions.v1.json', *config['gdd_paths']]
        allowed = config['source_paths'] + config['gdd_paths'] + ['knowledge/policies']
        for prefix in config['source_paths'] + config['gdd_paths']:
            if not any(p == prefix or p.startswith(prefix.rstrip('/') + '/') for p in trusted.paths):
                raise ValueError('Configured source does not exist: ' + prefix)
        trusted.paths = tuple(p for p in trusted.paths if any(p == prefix or p.startswith(prefix.rstrip('/') + '/') for prefix in allowed))
        for path in required:
            if path not in trusted.paths:
                raise ValueError('Required source missing from selected scope: ' + path)
        policies = json.loads(trusted.read_text('knowledge/policies/consumer-policies.v1.json'))
        exclusions = json.loads(trusted.read_text('knowledge/policies/source-exclusions.v1.json'))
        _, catalog, projections = build_layers(trusted, exclusions, policies)
        index = {'status': 'unavailable', 'reason': 'Impact index is not built by exploratory scan'}
        # Only tracked, bounded UTF-8 source files enter the investigation workspace.
        selected = {m['source_path'] for m in catalog['modules']}
        selected.update(config['gdd_paths'])
        selected.update(p for p in trusted.paths if p.startswith(('Game.Godot/', 'Game.Core/', 'Game.Core.Tests/', 'Tests.Godot/'))
                        and Path(p).suffix.lower() in ({'.tscn', '.cs', '.gd'} | CONFIG_SUFFIXES))
        sources = {}
        for path in sorted(selected & set(trusted.paths)):
            data = trusted.read_bytes(path)
            if len(data) <= 4 * 1024 * 1024:
                try:
                    sources[path] = data.decode('utf-8-sig')
                except UnicodeDecodeError:
                    pass
        details = task_details(trusted)
        attach_task_scenes(details, sources, config['task_scene_bindings'])
        gdds = [{'path': p, 'available': p in sources, 'role': 'supplementary-design-source',
                 'sha256': trusted.digest(p) if p in sources else None}
                for p in config['gdd_paths']]
        publication = {}
        result = {'schema_version': 'newrouge.project-health-knowledge.v1', 'revision': revision,
                  'scanned_at': datetime.now(timezone.utc).isoformat(), 'branch': 'main' if revision[:10] != 'directory:' else 'directory',
                  'snapshot': None, 'summary': task_summary(details), 'tasks': details,
                  'gdd_files': gdds, 'config': config, 'index': index,
                  'catalog': catalog, 'policies': policies, 'projections': projections,
                  'sources': sources,
                  'file_manifest': sorted(set(sources) | {p for p in trusted.paths
                      if p.startswith(('Game.Core/', 'Game.Godot/', 'Tests.Godot/', 'Game.Core.Tests/'))
                      and Path(p).suffix.lower() in ASSET_SUFFIXES}),
                  'publication': {'main_commit': publication.get('main_commit'),
                  'matches_scan': publication.get('main_commit') == revision,
                  'note': 'Exploratory catalogs are not published or frozen KCP authority.'}}
        # Commit only complete successful scans; failures retain the previous dated result.
        write_json(base / 'latest.json', result)
        return status(root, result)
    finally:
        try:
            lock.rmdir()
        except OSError:
            pass


def apply_runtime_eligibility(state: dict) -> None:
    source = state.get('sources', {}).get('.taskmaster/tasks/tasks_gameplay.json')
    rows = json.loads(source) if isinstance(source, str) else []
    eligible = set()
    for row in rows:
        combined = json.dumps({'test_refs': row.get('test_refs', []),
                               'acceptance': row.get('acceptance', row.get('acceptance_criteria', [])),
                               'test_strategy': row.get('testStrategy', row.get('test_strategy', []))},
                              ensure_ascii=False).replace('\\\\', '/')
        refs = re.findall(r'Tests\.Godot/[A-Za-z0-9_./-]+', combined)
        if any(ref.rstrip('.,;/') in state.get('sources', {}) or
               any(path.startswith(ref.rstrip('.,;/') + '/') for path in state.get('sources', {}))
               for ref in refs):
            eligible.add(str(row.get('taskmaster_id')))
    for detail in state.get('tasks', []):
        detail['godot']['runtime_eligible'] = str(detail['task']['id']) in eligible


def apply_runtime_results(root: Path, state: dict) -> None:
    apply_runtime_eligibility(state)
    workspace_index = base_dir(root) / 'runtime/workspace-latest.json'
    if workspace_index.exists():
        workspace = read_json(workspace_index)
        if workspace.get('verification_mode') == 'workspace':
            by_task = {str(row.get('task_id')): row for row in workspace.get('tasks', [])}
            for detail in state.get('tasks', []):
                detail['godot']['workspace_evidence'] = by_task.get(str(detail['task']['id']))
    path = base_dir(root) / 'runtime' / 'latest.json'
    if not path.exists():
        return
    runtime = read_json(path)
    if runtime.get('source_revision') != state.get('revision'):
        return
    by_id = {str(row.get('task_id')): row for row in runtime.get('tasks', [])}
    for detail in state.get('tasks', []):
        evidence = by_id.get(str(detail['task']['id']))
        if not evidence:
            detail['godot']['runtime_status'] = 'runtime_unverified'
            continue
        required = {'task_id', 'source_revision', 'test_refs', 'scenes', 'status',
                    'started_at', 'finished_at', 'evidence_path'}
        evidence_file_matches = False
        try:
            evidence_path = safe_file(root, evidence.get('evidence_path', ''))
            runtime_root = (base_dir(root) / 'runtime').resolve()
            evidence_path.resolve().relative_to(runtime_root)
            evidence_file_matches = evidence_path.is_file() and read_json(evidence_path) == evidence
        except (ValueError, OSError, TypeError, json.JSONDecodeError):
            pass
        detail['godot']['runtime_evidence'] = evidence
        verified = (evidence.get('verification_mode', 'main') == 'main'
                    and required <= evidence.keys() and evidence.get('status') == 'passed'
                    and evidence.get('source_revision') == state.get('revision')
                    and bool(evidence.get('test_refs'))
                    and all(re.fullmatch(r'Tests\.Godot/[A-Za-z0-9_./-]+', str(ref))
                            and '..' not in PurePosixPath(str(ref)).parts for ref in evidence['test_refs'])
                    and evidence_file_matches)
        detail['godot']['runtime_verified'] = verified
        detail['godot']['runtime_status'] = ('runtime_verified' if verified
                                                else evidence.get('status', 'runtime_unverified'))
        if verified:
            detail['godot']['status'] = 'runtime_verified'
        elif evidence.get('status') == 'failed' and detail['godot']['status'] == 'static_attached':
            detail['godot']['status'] = 'runtime_failed_static_attached'


def status(root: Path, state: dict) -> dict:
    if state.get('tasks'):
        state['summary'] = task_summary(state['tasks'])
    result = {key: state.get(key) for key in ('schema_version', 'revision', 'scanned_at', 'branch',
                                              'summary', 'gdd_files', 'publication', 'config')}
    runtime_path = base_dir(root) / 'runtime' / 'latest.json'
    if runtime_path.exists():
        runtime = read_json(runtime_path)
        if runtime.get('source_revision') == state.get('revision'):
            result['runtime'] = runtime.get('summary', {})
        else:
            result['runtime'] = {'total': 0, 'runtime_verified': 0, 'runtime_failed': 0,
                                 'stale': True, 'reason': 'Runtime evidence belongs to another scan revision'}
    else:
        result['runtime'] = {'total': 0, 'runtime_verified': 0, 'runtime_failed': 0}
    return result


ACTION_GROUP_LIMIT = 8
ACTION_NAVIGATION_LIMIT = 4


def _search_terms(text: str) -> set[str]:
    """Return small deterministic search terms with light English normalization."""
    result = set()
    separated = re.sub(r'(?<=[a-z0-9])(?=[A-Z])', ' ', text)
    for value in re.findall(r'[\w]+', separated.casefold(), flags=re.UNICODE):
        if len(value) <= 1:
            continue
        if value.endswith('ing') and len(value) > 5:
            value = value[:-3]
        elif value.endswith('er') and len(value) > 5:
            value = value[:-2]
        elif value.endswith('s') and len(value) > 4:
            value = value[:-1]
        result.add(value)
    return result


def _term_score(text: str, needles: set[str]) -> tuple[int, int]:
    haystack = _search_terms(text)
    matched = len(haystack & needles)
    return matched, len(needles)


def _snapshot_freshness(root: Path, revision: str | None) -> dict:
    try:
        current = git(root, 'rev-parse', 'HEAD')
    except (RuntimeError, OSError, subprocess.SubprocessError):
        current = None
    stale = bool(current and revision and current != revision)
    return {
        'stale': stale,
        'snapshot_revision': revision,
        'current_revision': current,
        'message': ('Snapshot is stale; results describe the scanned revision.' if stale
                    else 'Snapshot matches the current revision.' if current == revision
                    else 'Snapshot freshness could not be determined.'),
    }


def _action_item(kind: str, path: str | None, score: int, strength: str,
                 reason: str, task: dict | None = None) -> dict:
    item = {'kind': kind, 'score': score, 'evidence_strength': strength,
            'reason': reason}
    if path:
        item['path'] = path
    if task:
        item['task_id'] = str(task['id'])
        item['title'] = task.get('title', '')
        item['status'] = task.get('status')
    return item


def _actionable_results(root: Path, state: dict, queries: list[str]) -> dict:
    query_text = ' '.join(queries)
    query_needles = [_search_terms(query) for query in queries]
    query_needles = [needles for needles in query_needles if needles]
    needles = set().union(*query_needles) if query_needles else set()

    def best_score(text: str) -> tuple[int, int]:
        """Score against each query variant so aliases do not dilute matches."""
        scores = [_term_score(text, terms) for terms in query_needles]
        return max(scores, key=lambda score: (score[0] == score[1], score[0], -score[1]),
                   default=(0, 0))

    normalized_query = query_text.casefold().replace('\\', '/')

    def path_is_explicit(path: str) -> bool:
        candidate = path.casefold().replace('\\', '/')
        boundary = r'[a-z0-9_]'
        pattern = rf'(?<!{boundary}){re.escape(candidate)}(?!{boundary})'
        return re.search(pattern, normalized_query) is not None

    exact_paths = {path for path in state.get('file_manifest', [])
                   if path_is_explicit(path)}
    task_candidates = []
    for detail in state.get('tasks', []):
        task = detail.get('task', {})
        searchable = json.dumps({'task': task, 'mappings': detail.get('mappings', {})},
                                ensure_ascii=False)
        matched, total = best_score(searchable)
        exact_task = re.search(r'\btask\s*#?\s*' + re.escape(str(task.get('id'))) + r'\b',
                               query_text, flags=re.IGNORECASE)
        if exact_task or (matched and (matched == total or matched >= min(2, total))):
            title_matched, _ = best_score(str(task.get('title', '')))
            score = 1000 if exact_task else 500 + matched * 40 + title_matched * 15
            task_candidates.append((score, detail))
    task_candidates.sort(key=lambda row: (-row[0], int(row[1]['task']['id'])))
    task_candidates = task_candidates[:16]

    groups = {name: {} for name in ('tasks', 'configs', 'code', 'tests')}
    strength_rank = {'direct': 2, 'confirmed': 1, 'inferred': 0}

    def put(group: str, key: str, item: dict) -> None:
        current = groups[group].get(key)
        if (current is None
                or strength_rank[item['evidence_strength']] > strength_rank[current['evidence_strength']]
                or (item['evidence_strength'] == current['evidence_strength']
                    and item['score'] > current['score'])):
            groups[group][key] = item

    for score, detail in task_candidates:
        task = detail['task']
        put('tasks', str(task['id']), _action_item(
            'task', None, score, 'direct', 'Task title or definition matches the query.', task))
    for score, detail in task_candidates[:ACTION_NAVIGATION_LIMIT]:
        task = detail['task']
        navigation = build_navigation(detail, state)
        task_id = str(task['id'])
        for group, output_kind in (('configs', 'config'), ('code', 'code'), ('tests', 'test')):
            for nav_item in navigation.get(group, []):
                path = nav_item['path']
                focus = nav_item.get('focus', 'core')
                strength = ('confirmed' if focus == 'core' and
                            nav_item.get('evidence_kind') != 'static_candidate' else 'inferred')
                relation_score = score - (35 if strength == 'confirmed' else 180)
                direct, _ = best_score(path)
                if path in exact_paths:
                    relation_score = 1200
                    strength = 'direct'
                else:
                    relation_score += direct * 30
                item = _action_item(output_kind, path, relation_score, strength,
                                    f'Linked through task {task_id} navigation evidence.')
                item['related_task_ids'] = [task_id]
                put(group, path, item)

    source_groups = (('configs', 'config', CONFIG_SUFFIXES),
                     ('code', 'code', {'.cs', '.gd'}),
                     ('tests', 'test', {'.cs', '.gd'}))
    for path in state.get('file_manifest', []):
        suffix = PurePosixPath(path).suffix.lower()
        for group, kind, suffixes in source_groups:
            if suffix not in suffixes:
                continue
            if group == 'tests' and not path.startswith(('Game.Core.Tests/', 'Tests.Godot/')):
                continue
            if group == 'code' and not path.startswith(('Game.Core/', 'Game.Godot/')):
                continue
            if group == 'configs' and not path.startswith(('Game.Core/', 'Game.Godot/')):
                continue
            matched, total = best_score(path)
            if path in exact_paths:
                put(group, path, _action_item(kind, path, 1400, 'direct',
                                              'Exact scanned path matches the query.'))
            elif total and matched == total:
                put(group, path, _action_item(kind, path, 420 + matched * 20, 'direct',
                                              'Scanned path matches all query terms.'))

    ordered_groups = {}
    kind_order = {'task': 0, 'config': 1, 'code': 2, 'test': 3}
    for name in ('tasks', 'configs', 'code', 'tests'):
        items = sorted(groups[name].values(), key=lambda item: (
            -strength_rank[item['evidence_strength']], -item['score'],
            kind_order[item['kind']], item.get('path', ''), item.get('task_id', '')))
        visible = items[:ACTION_GROUP_LIMIT]
        ordered_groups[name] = {'items': visible, 'total': len(items),
                                'truncated': max(0, len(items) - len(visible))}
    top = []
    for name, limit in (('tasks', 2), ('configs', 1), ('code', 1), ('tests', 1)):
        evidenced = [item for item in ordered_groups[name]['items']
                     if item['evidence_strength'] != 'inferred']
        top.extend(evidenced[:limit])
    return {**ordered_groups, 'top': top, 'group_limit': ACTION_GROUP_LIMIT}


def query(root: Path, state: dict, request: dict) -> dict:
    query_text = request.get('query')
    if not isinstance(query_text, str) or not query_text.strip() or len(query_text) > 2000:
        raise ValueError('Query must contain 1 to 2000 characters')
    queries = [query_text]
    for key, values in state['config']['query_aliases'].items():
        if key.casefold() in query_text.casefold():
            queries.extend(values)
    queries = list(dict.fromkeys(queries))[:12]
    consumer = request.get('consumer', 'repository-session')
    policy = next((p for p in state['policies']['policies'] if p['consumer'] == consumer), None)
    projection = next((p for p in state['projections']['projections'] if p['consumer'] == consumer), None)
    if not policy or not projection:
        raise ValueError('Unknown knowledge consumer')
    candidates = {}
    for text in queries:
        found = locate({'query': text}, state['catalog'], policy, set(projection['eligible_module_ids']), 12)
        for item in found['candidates']:
            candidates.setdefault(item['module_id'], {**item, 'matched_query': text})
    supplemental = []
    for item in state['gdd_files']:
        content = state['sources'].get(item['path'], '')
        if item['available'] and any(any(t in content.casefold() for t in tokens(q)) for q in queries):
            supplemental.append(item)
    analyzer = ImpactAnalyzer.from_exploratory_sources(state.get('sources', {}), state['revision'])
    targets = []
    needles = set(t for q in queries for t in tokens(q))
    # Exploratory scans may not have a formal Impact index. Catalog/query results
    # remain useful, while formal handoff is explicitly unavailable.
    if analyzer:
        for symbol in analyzer.resolver.symbol_index.symbols:
            if symbol.kind.startswith('__'):
                continue
            if any(t in symbol.identity.casefold() for t in needles):
                targets.append({'type': symbol.kind, 'id': symbol.identity, 'path': symbol.path})
        for path in analyzer.hashes:
            if any(t in path.casefold() for t in needles):
                targets.append({'type': 'file', 'id': path, 'path': path})
    try:
        preview = analyzer.explore(request['target']) if analyzer and request.get('target') else None
    except ImpactIndexError as exc:
        preview = {'status': 'blocked', 'code': exc.code, 'reason': exc.reason, 'handoff_eligible': False}
    freshness = _snapshot_freshness(root, state['revision'])
    result = {'status': 'exploratory', 'handoff_eligible': False, 'revision': state['revision'],
              'queries': queries, 'consumer': consumer, 'knowledge': list(candidates.values()),
              'gdd_supplements': supplemental, 'impact_targets': targets[:80],
              'impact_target_total': len(targets), 'impact_preview': preview,
              'impact_skipped_methods': analyzer.resolver.symbol_index.skipped_methods if analyzer else [],
              'actionable_results': _actionable_results(root, state, queries),
              'snapshot_freshness': freshness,
              'next_step': 'Select an exact Impact target. Formal handoff requires existing KCP accept/freeze and analyze_impact CLI.'}
    evidence = base_dir(root) / 'queries' / (uuid.uuid4().hex + '.json')
    write_json(evidence, result)
    result['evidence_path'] = evidence.relative_to(root).as_posix()
    return result


def attach_semantic_navigation(navigation: dict, semantic: dict, sources: dict | None = None) -> None:
    sources = sources or {}
    by_key = {(item.get('kind'), item.get('path')): item for item in semantic.get('entries', [])
              if isinstance(item, dict)}
    for group, kind in (('configs', 'config'), ('assets', 'asset'), ('scenes', 'scene')):
        for item in navigation.get(group, []):
            item['semantic'] = by_key.get((kind, item.get('path')))
            if kind != 'config':
                continue
            confirmed = {field.get('pointer'): {**field, 'confirmation': 'static_record_identity'}
                         for field in item.get('focused_fields', []) if field.get('pointer')}
            reader_text = '\n'.join(sources.get(reader.get('reader'), '') for reader in item.get('readers', []))
            quoted_keys = set(re.findall(r'["\']([A-Za-z_][A-Za-z0-9_]*)["\']', reader_text))
            fields_by_pointer = {field.get('pointer'): field for field in item.get('fields', [])}
            for parameter in (item.get('semantic') or {}).get('parameters', []):
                pointer = parameter.get('pointer') or parameter.get('key')
                segments = [segment.replace('~1', '/').replace('~0', '~')
                            for segment in str(pointer or '').split('/') if segment and not segment.isdigit()]
                if (pointer in fields_by_pointer and segments and segments[-1] in quoted_keys
                        and any(segment in quoted_keys for segment in segments[:-1])):
                    confirmed[pointer] = {**fields_by_pointer[pointer],
                                          'confirmation': 'semantic_reconstruction+static_reader_key_chain'}
            item['confirmed_fields'] = list(confirmed.values())


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('scan', 'status', 'tasks', 'task', 'query', 'source'))
    parser.add_argument('--repo-root', type=Path, default=Path.cwd())
    parser.add_argument('--page', type=int, default=1)
    parser.add_argument('--task-id')
    parser.add_argument('--path')
    parser.add_argument('--filter-kind', choices=('task_status', 'godot_status'))
    parser.add_argument('--filter-value')
    args = parser.parse_args(argv)
    root = args.repo_root.resolve()
    try:
        if args.action == 'scan':
            result = scan(root)
        else:
            latest = base_dir(root) / 'latest.json'
            if latest.exists():
                state = read_json(latest)
            else:
                config = load_config(root)
                state = {'schema_version': 'newrouge.project-health-knowledge.v1',
                         'revision': None, 'scanned_at': None, 'branch': 'main',
                         'summary': {'total': 0, 'statuses': {}, 'godot': {}},
                         'gdd_files': [], 'publication': {'main_commit': None,
                         'matches_scan': False, 'note': 'No successful local main scan yet.'},
                         'config': config, 'tasks': [], 'sources': {}, 'policies': {},
                         'projections': {}, 'catalog': {}, 'index': {}}
            if args.action == 'status':
                apply_runtime_results(root, state)
                result = status(root, state)
            elif args.action == 'tasks':
                apply_runtime_results(root, state)
                result = task_page(state['tasks'], args.page, args.filter_kind, args.filter_value)
            elif args.action == 'task':
                apply_runtime_results(root, state)
                result = next((x for x in state['tasks'] if str(x['task']['id']) == args.task_id), None)
                if result is None:
                    raise ValueError('Task not found')
                result = {**result, 'navigation': build_navigation(result, state)}
                links_path = root / 'docs/knowledge/generated/task-resource-links.json'
                if links_path.exists():
                    links = read_json(links_path).get('generated', [])
                    result['resource_knowledge'] = [entry for entry in links if str(entry.get('task_id')) == str(args.task_id)]
                semantic_path = root / 'docs/knowledge/generated' / f'task-{args.task_id}-semantic.json'
                if semantic_path.exists():
                    semantic = read_json(semantic_path)
                    attach_semantic_navigation(result.get('navigation', {}), semantic, state.get('sources', {}))
            elif args.action == 'source':
                if args.path not in state['sources']:
                    raise ValueError('Source is not in the scanned allowlist')
                result = {'path': args.path, 'revision': state['revision'], 'content': state['sources'][args.path]}
            else:
                result = query(root, state, json.load(sys.stdin))
        print(json.dumps(result, ensure_ascii=False))
        return 0
    except Exception as exc:
        print(json.dumps({'status': 'failed', 'reason': str(exc)}, ensure_ascii=False))
        return 1


if __name__ == '__main__':
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    raise SystemExit(main())
