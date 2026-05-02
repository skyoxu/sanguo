#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from pathlib import Path
from typing import Any

TASKS_JSON = Path('.taskmaster/tasks/tasks.json')
TASKS_BACK = Path('.taskmaster/tasks/tasks_back.json')
TASKS_GAMEPLAY = Path('.taskmaster/tasks/tasks_gameplay.json')
UI_GDD_FLOW = Path('docs/gdd/ui-gdd-flow.md')
OVERLAY_ROOT = Path('docs/architecture/overlays')


def _today() -> str:
    return dt.date.today().strftime('%Y-%m-%d')


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding='utf-8'))


def _resolve_path(value: str | Path) -> Path:
    return value if isinstance(value, Path) else Path(value)


def _missing_task_files(repo_root: Path, tasks_json_path: Path, tasks_back_path: Path, tasks_gameplay_path: Path) -> list[str]:
    missing: list[str] = []
    for item in (tasks_json_path, tasks_back_path, tasks_gameplay_path):
        candidate = item if item.is_absolute() else (repo_root / item)
        if not candidate.is_file():
            missing.append(str(item).replace('\\', '/'))
    return missing


def _load_master_tasks(repo_root: Path, tasks_json_path: Path) -> list[dict[str, Any]]:
    path = tasks_json_path if tasks_json_path.is_absolute() else (repo_root / tasks_json_path)
    payload = _read_json(path)
    tasks = payload.get('master', {}).get('tasks', []) if isinstance(payload, dict) else []
    return [item for item in tasks if isinstance(item, dict)]


def _load_view_tasks(repo_root: Path, rel: Path) -> list[dict[str, Any]]:
    path = rel if rel.is_absolute() else (repo_root / rel)
    payload = _read_json(path)
    return [item for item in payload if isinstance(item, dict)] if isinstance(payload, list) else []


def _feature_family(task: dict[str, Any], gameplay_view: dict[str, Any] | None, back_view: dict[str, Any] | None) -> str:
    title = str(task.get('title') or '') + ' ' + str((gameplay_view or {}).get('title') or '') + ' ' + str((back_view or {}).get('title') or '')
    labels = {str(x).lower() for x in ((gameplay_view or {}).get('labels') or [])}
    text = title.lower()
    if 'reward' in labels or 'reward' in text:
        return 'reward'
    if 'rest' in labels or 'rest' in text:
        return 'rest'
    if 'shop' in labels or 'shop' in text:
        return 'shop'
    if 'event' in labels or 'event' in text:
        return 'event'
    if 'combat' in labels or 'combat' in text:
        return 'combat'
    if 'map' in labels or 'map' in text:
        return 'map'
    if 'menu' in text or 'difficulty' in text or 'character' in text or 'run' in text:
        return 'run-entry'
    if 'translation' in text or 'text' in text or 'i18n' in labels:
        return 'text-localization'
    return 'system-support'


def _merge_refs(*refs_lists: list[str]) -> list[str]:
    seen: set[str] = set()
    merged: list[str] = []
    for refs in refs_lists:
        for item in refs:
            value = str(item).strip()
            if not value or value in seen:
                continue
            seen.add(value)
            merged.append(value)
    return merged


def _read_text_if_exists(path: Path) -> str:
    try:
        return path.read_text(encoding='utf-8')
    except FileNotFoundError:
        return ''


def _overlay_manifest_path(repo_root: Path, overlay_root: Path) -> Path | None:
    if overlay_root.name == '08':
        direct_manifest = (repo_root / overlay_root / 'overlay-manifest.json').resolve()
        return direct_manifest if direct_manifest.exists() else None
    overlay_base = (repo_root / overlay_root).resolve()
    manifests = sorted(overlay_base.glob('*/08/overlay-manifest.json'))
    if not manifests:
        return None

    repo_slug = re.sub(r'[^a-z0-9]+', '', repo_root.name.lower())
    preferred: list[Path] = []
    for manifest in manifests:
        try:
            payload = _read_json(manifest)
        except Exception:
            continue
        prd_id = str(payload.get('prd_id') or manifest.parent.parent.name).lower() if isinstance(payload, dict) else manifest.parent.parent.name.lower()
        if repo_slug and repo_slug in re.sub(r'[^a-z0-9]+', '', prd_id):
            preferred.append(manifest)
    return (preferred or manifests)[0]


def _overlay_file_map(repo_root: Path, overlay_root: Path) -> dict[str, Path]:
    manifest_path = _overlay_manifest_path(repo_root, overlay_root)
    if manifest_path is None:
        return {}
    payload = _read_json(manifest_path)
    files = payload.get('files', {}) if isinstance(payload, dict) else {}
    result: dict[str, Path] = {}
    for key, value in files.items():
        if isinstance(value, str) and value.strip():
            result[key] = manifest_path.parent / value
    return result


def _task_ids_from_scope(scope_text: str) -> set[int]:
    hits: set[int] = set()
    for match in re.finditer(r'\bT0*(\d{1,4})\b', scope_text):
        hits.add(int(match.group(1)))
    for match in re.finditer(r'\b(\d+)\s*-\s*(\d+)\b', scope_text):
        start = int(match.group(1))
        end = int(match.group(2))
        if 0 < start <= end <= 9999:
            hits.update(range(start, end + 1))
    if not hits:
        for match in re.finditer(r'\b(\d{1,4})\b', scope_text):
            value = int(match.group(1))
            if 0 < value <= 9999:
                hits.add(value)
    return hits


def _collect_overlay_requirement_mapping(repo_root: Path, overlay_root: Path) -> dict[int, list[dict[str, Any]]]:
    files = _overlay_file_map(repo_root, overlay_root)
    text = _read_text_if_exists(files.get('testing', Path('__missing__')))
    mapping: dict[int, list[dict[str, Any]]] = {}
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped.startswith('| RQ-'):
            continue
        cells = [cell.strip() for cell in stripped.strip('|').split('|')]
        if len(cells) < 4:
            continue
        requirement_id, task_scope, tests, expected_logs = cells[:4]
        task_ids = _task_ids_from_scope(task_scope)
        tests_list = [item.strip('` ') for item in tests.split(',') if item.strip()]
        logs_list = [item.strip('` ') for item in expected_logs.split(',') if item.strip()]
        row = {
            'requirement_id': requirement_id,
            'task_scope': task_scope,
            'tests': tests_list,
            'expected_logs': logs_list,
        }
        for task_id in task_ids:
            mapping.setdefault(task_id, []).append(row)
    return mapping


def _collect_overlay_evidence_mapping(repo_root: Path, overlay_root: Path) -> dict[int, list[dict[str, Any]]]:
    files = _overlay_file_map(repo_root, overlay_root)
    text = _read_text_if_exists(files.get('observability', Path('__missing__')))
    mapping: dict[int, list[dict[str, Any]]] = {}
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped.startswith('| `T'):
            continue
        cells = [cell.strip() for cell in stripped.strip('|').split('|')]
        if len(cells) < 3:
            continue
        task_scope, required_artifact, minimum_fields = cells[:3]
        task_ids = _task_ids_from_scope(task_scope)
        row = {
            'task_scope': task_scope,
            'required_artifact': required_artifact.strip('` '),
            'minimum_fields': [item.strip('` ') for item in minimum_fields.split(',') if item.strip()],
        }
        for task_id in task_ids:
            mapping.setdefault(task_id, []).append(row)
    return mapping


def _collect_overlay_acceptance_notes(repo_root: Path, overlay_root: Path) -> dict[int, list[str]]:
    files = _overlay_file_map(repo_root, overlay_root)
    text = _read_text_if_exists(files.get('feature', Path('__missing__')))
    mapping: dict[int, list[str]] = {}
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped.startswith('-'):
            continue
        task_ids = _task_ids_from_scope(stripped)
        if not task_ids:
            continue
        note = stripped.lstrip('-').strip().replace('`', '')
        lowered = note.lower()
        if (
            lowered.startswith('adr-')
            or lowered.startswith('docs/')
            or lowered.startswith('taskmaster ids ')
            or lowered.startswith('key tasks:')
            or lowered.startswith('scope:')
            or lowered.startswith('contract anchor:')
        ):
            continue
        for task_id in task_ids:
            mapping.setdefault(task_id, []).append(note)
    return mapping


def build_summary(
    *,
    repo_root: Path,
    tasks_json_path: Path = TASKS_JSON,
    tasks_back_path: Path = TASKS_BACK,
    tasks_gameplay_path: Path = TASKS_GAMEPLAY,
    overlay_root_path: Path = OVERLAY_ROOT,
) -> dict[str, Any]:
    tasks_json_path = _resolve_path(tasks_json_path)
    tasks_back_path = _resolve_path(tasks_back_path)
    tasks_gameplay_path = _resolve_path(tasks_gameplay_path)
    overlay_root_path = _resolve_path(overlay_root_path)
    missing = _missing_task_files(repo_root, tasks_json_path, tasks_back_path, tasks_gameplay_path)
    if missing:
        return {
            'ts': dt.datetime.now(dt.timezone.utc).isoformat(),
            'action': 'collect-ui-wiring-inputs',
            'status': 'skipped',
            'reason': 'missing_task_triplet',
            'repo_root': str(repo_root).replace('\\', '/'),
            'source_files': [str(tasks_json_path).replace('\\', '/'), str(tasks_back_path).replace('\\', '/'), str(tasks_gameplay_path).replace('\\', '/')],
            'overlay_root': str(overlay_root_path).replace('\\', '/'),
            'missing_source_files': missing,
            'completed_master_tasks_count': 0,
            'needed_wiring_features_count': 0,
            'feature_family_counts': {},
            'needed_wiring_features': [],
        }

    master_tasks = _load_master_tasks(repo_root, tasks_json_path)
    done_master = [task for task in master_tasks if str(task.get('status') or '').lower() == 'done']
    back_tasks = _load_view_tasks(repo_root, tasks_back_path)
    gameplay_tasks = _load_view_tasks(repo_root, tasks_gameplay_path)
    back_by_tm: dict[int, list[dict[str, Any]]] = {}
    gameplay_by_tm: dict[int, list[dict[str, Any]]] = {}
    for item in back_tasks:
        tm = item.get('taskmaster_id')
        if isinstance(tm, int):
            back_by_tm.setdefault(tm, []).append(item)
    for item in gameplay_tasks:
        tm = item.get('taskmaster_id')
        if isinstance(tm, int):
            gameplay_by_tm.setdefault(tm, []).append(item)
    overlay_requirement_map = _collect_overlay_requirement_mapping(repo_root, overlay_root_path)
    overlay_evidence_map = _collect_overlay_evidence_mapping(repo_root, overlay_root_path)
    overlay_acceptance_map = _collect_overlay_acceptance_notes(repo_root, overlay_root_path)

    needed: list[dict[str, Any]] = []
    for task in done_master:
        task_id = int(task.get('id'))
        gameplay_views = gameplay_by_tm.get(task_id, [])
        back_views = back_by_tm.get(task_id, [])
        gameplay_view = gameplay_views[0] if gameplay_views else None
        back_view = back_views[0] if back_views else None
        overlay_requirements = overlay_requirement_map.get(task_id, [])
        overlay_evidence = overlay_evidence_map.get(task_id, [])
        overlay_acceptance_notes = overlay_acceptance_map.get(task_id, [])
        needed.append({
            'task_id': task_id,
            'task_title': str(task.get('title') or ''),
            'feature_family': _feature_family(task, gameplay_view, back_view),
            'gameplay_view_ids': [str(item.get('id') or '') for item in gameplay_views if str(item.get('id') or '').strip()],
            'back_view_ids': [str(item.get('id') or '') for item in back_views if str(item.get('id') or '').strip()],
            'status_master': str(task.get('status') or ''),
            'status_views': sorted({str(item.get('status') or '') for item in [*gameplay_views, *back_views] if str(item.get('status') or '').strip()}),
            'labels': sorted({str(x).lower() for item in gameplay_views for x in (item.get('labels') or [])}),
            'test_refs': _merge_refs(*[item.get('test_refs') or [] for item in [*gameplay_views, *back_views]]),
            'acceptance': _merge_refs(*[item.get('acceptance') or [] for item in [*gameplay_views, *back_views]]),
            'contract_refs': _merge_refs(*[item.get('contractRefs') or [] for item in [*gameplay_views, *back_views]]),
            'overlay_requirement_ids': _merge_refs(*[[item['requirement_id']] for item in overlay_requirements]),
            'overlay_expected_logs': _merge_refs(
                *[[value for value in item.get('expected_logs', [])] for item in overlay_requirements],
                *[[item.get('required_artifact', '')] for item in overlay_evidence],
            ),
            'overlay_minimum_fields': _merge_refs(*[[value for value in item.get('minimum_fields', [])] for item in overlay_evidence]),
            'overlay_acceptance_notes': _merge_refs(overlay_acceptance_notes),
        })

    families: dict[str, int] = {}
    for item in needed:
        families[item['feature_family']] = families.get(item['feature_family'], 0) + 1

    return {
        'ts': dt.datetime.now(dt.timezone.utc).isoformat(),
        'action': 'collect-ui-wiring-inputs',
        'status': 'ok',
        'repo_root': str(repo_root).replace('\\', '/'),
        'source_files': [str(tasks_json_path).replace('\\', '/'), str(tasks_back_path).replace('\\', '/'), str(tasks_gameplay_path).replace('\\', '/')],
        'overlay_root': str(overlay_root_path).replace('\\', '/'),
        'completed_master_tasks_count': len(done_master),
        'needed_wiring_features_count': len(needed),
        'feature_family_counts': families,
        'needed_wiring_features': needed,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description='Collect completed task triplet inputs for Chapter 7 UI wiring flow.')
    parser.add_argument('--repo-root', default='.')
    parser.add_argument('--tasks-json-path', default=str(TASKS_JSON))
    parser.add_argument('--tasks-back-path', default=str(TASKS_BACK))
    parser.add_argument('--tasks-gameplay-path', default=str(TASKS_GAMEPLAY))
    parser.add_argument('--overlay-root-path', default=str(OVERLAY_ROOT))
    parser.add_argument('--out', default='')
    args = parser.parse_args(argv)

    repo_root = Path(args.repo_root).resolve()
    payload = build_summary(
        repo_root=repo_root,
        tasks_json_path=Path(args.tasks_json_path),
        tasks_back_path=Path(args.tasks_back_path),
        tasks_gameplay_path=Path(args.tasks_gameplay_path),
        overlay_root_path=Path(args.overlay_root_path),
    )
    out = Path(args.out) if args.out else (repo_root / 'logs' / 'ci' / _today() / 'chapter7-ui-wiring-inputs' / 'summary.json')
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(f"CHAPTER7_UI_WIRING_INPUTS status={payload['status']} tasks={payload['needed_wiring_features_count']} out={str(out).replace('\\', '/')}")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
