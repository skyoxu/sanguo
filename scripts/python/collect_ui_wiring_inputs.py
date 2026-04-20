#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path
from typing import Any

TASKS_JSON = Path('.taskmaster/tasks/tasks.json')
TASKS_BACK = Path('.taskmaster/tasks/tasks_back.json')
TASKS_GAMEPLAY = Path('.taskmaster/tasks/tasks_gameplay.json')
UI_GDD_FLOW = Path('docs/gdd/ui-gdd-flow.md')


def _today() -> str:
    return dt.date.today().strftime('%Y-%m-%d')


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding='utf-8'))


def _load_master_tasks(repo_root: Path) -> list[dict[str, Any]]:
    payload = _read_json(repo_root / TASKS_JSON)
    tasks = payload.get('master', {}).get('tasks', []) if isinstance(payload, dict) else []
    return [item for item in tasks if isinstance(item, dict)]


def _load_view_tasks(repo_root: Path, rel: Path) -> list[dict[str, Any]]:
    payload = _read_json(repo_root / rel)
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


def build_summary(*, repo_root: Path) -> dict[str, Any]:
    master_tasks = _load_master_tasks(repo_root)
    done_master = [task for task in master_tasks if str(task.get('status') or '').lower() == 'done']
    back_tasks = _load_view_tasks(repo_root, TASKS_BACK)
    gameplay_tasks = _load_view_tasks(repo_root, TASKS_GAMEPLAY)
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

    needed: list[dict[str, Any]] = []
    for task in done_master:
        task_id = int(task.get('id'))
        gameplay_views = gameplay_by_tm.get(task_id, [])
        back_views = back_by_tm.get(task_id, [])
        gameplay_view = gameplay_views[0] if gameplay_views else None
        back_view = back_views[0] if back_views else None
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
        })

    families: dict[str, int] = {}
    for item in needed:
        families[item['feature_family']] = families.get(item['feature_family'], 0) + 1

    return {
        'ts': dt.datetime.now(dt.timezone.utc).isoformat(),
        'action': 'collect-ui-wiring-inputs',
        'repo_root': str(repo_root).replace('\\', '/'),
        'source_files': [str(TASKS_JSON).replace('\\', '/'), str(TASKS_BACK).replace('\\', '/'), str(TASKS_GAMEPLAY).replace('\\', '/')],
        'completed_master_tasks_count': len(done_master),
        'needed_wiring_features_count': len(needed),
        'feature_family_counts': families,
        'needed_wiring_features': needed,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description='Collect completed task triplet inputs for Chapter 7 UI wiring flow.')
    parser.add_argument('--repo-root', default='.')
    parser.add_argument('--out', default='')
    args = parser.parse_args(argv)

    repo_root = Path(args.repo_root).resolve()
    payload = build_summary(repo_root=repo_root)
    out = Path(args.out) if args.out else (repo_root / 'logs' / 'ci' / _today() / 'chapter7-ui-wiring-inputs' / 'summary.json')
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(f"CHAPTER7_UI_WIRING_INPUTS status=ok tasks={payload['needed_wiring_features_count']} out={str(out).replace('\\', '/')}")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
