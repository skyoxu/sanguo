#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Hard gate for task view contractRefs consistency.

Rules:
1) contractRefs must be an array when present.
2) contractRefs values must resolve to known event constants from contracts.
3) Event-driven UI or core runtime tasks must not omit contractRefs.
4) Shared taskmaster_id entries across task view files must use identical contractRefs,
   unless an explicit per-file override is configured.

Default target files:
  - .taskmaster/tasks/tasks_back.json
  - .taskmaster/tasks/tasks_gameplay.json

Default output:
  logs/ci/<YYYY-MM-DD>/task-contract-refs-gate/summary.json
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
from pathlib import Path
from typing import Any


DEFAULT_TASK_FILES = [
    Path('.taskmaster/tasks/tasks_back.json'),
    Path('.taskmaster/tasks/tasks_gameplay.json'),
]
DEFAULT_CONSISTENCY_WHITELIST = Path('.taskmaster/docs/contractrefs-consistency-whitelist.json')
EVENT_PATTERNS = [
    re.compile(r'public\s+const\s+string\s+EventType\s*=\s*"([a-z0-9._-]+)"\s*;'),
    re.compile(r'public\s+const\s+string\s+\w+\s*=\s*"([a-z0-9._-]+)"\s*;'),
]
EVENT_PREFIXES = ('core.', 'ui.', 'screen.')
RUNTIME_CONTRACT_ROOTS = [Path('Game.Core/Contracts'), Path('Scripts')]
PRESENTATION_LAYERS = {'adapter', 'ui', 'presentation'}
CORE_LAYERS = {'core'}
UI_REQUIRED_TITLE_KEYWORDS = (
    'event',
    'log',
    'display',
    'hint',
    'explain',
    'tooltip',
    'money',
    'date',
    'dice',
    'state',
    'status',
    '提示',
    '日志',
    '显示',
    '解释',
    '资金',
    '日期',
    '骰子',
    '状态',
)
UI_REQUIRED_LABELS = {'events', 'hud-log', 'explain'}
CORE_REQUIRED_TITLE_KEYWORDS = (
    'manager',
    'turn',
    'settlement',
    'combat',
    'battle',
    'random event',
    'global event',
    'relic',
    'loot',
    'inventory',
    'toll',
    'synergy',
    'ownership',
    '回合',
    '结算',
    '管理器',
    '战斗',
    '随机事件',
    '全局事件',
    '宝物',
    '州郡',
    '收费',
    '协同',
    '卡牌',
)
CORE_REQUIRED_LABELS = {'turn', 'economy', 'combat', 'region', 'relic', 'loot', 'card', 'inventory', 'ai'}
CORE_SKIP_TITLE_KEYWORDS = ('命名', '迁移', 'rename', 'migration')


def _today() -> str:
    return dt.date.today().strftime('%Y-%m-%d')


def _posix(path: Path | str) -> str:
    return str(path).replace('\\', '/')


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding='utf-8-sig'))


def _load_allowed_events(repo_root: Path) -> tuple[set[str], dict[str, list[str]]]:
    allowed: set[str] = set()
    per_file: dict[str, list[str]] = {}

    for root in RUNTIME_CONTRACT_ROOTS:
        full_root = repo_root / root
        if not full_root.exists():
            continue
        for file_path in full_root.rglob('*.cs'):
            try:
                text = file_path.read_text(encoding='utf-8')
            except Exception:
                continue
            hits: set[str] = set()
            for pattern in EVENT_PATTERNS:
                hits.update(pattern.findall(text))
            filtered = sorted(x for x in hits if x.startswith(EVENT_PREFIXES))
            if filtered:
                allowed.update(filtered)
                per_file[_posix(file_path.relative_to(repo_root))] = filtered

    if not allowed:
        roots = ', '.join(_posix(item) for item in RUNTIME_CONTRACT_ROOTS)
        raise ValueError(f'No event constants discovered under: {roots}')
    return allowed, per_file


def _normalize_refs(refs: list[Any] | None) -> list[str]:
    if refs is None:
        return []
    return sorted({str(item).strip() for item in refs if str(item).strip()})


def _labels(task: dict[str, Any]) -> set[str]:
    raw = task.get('labels')
    if not isinstance(raw, list):
        return set()
    return {str(item).strip().lower() for item in raw if str(item).strip()}


def _test_refs(task: dict[str, Any]) -> list[str]:
    raw = task.get('test_refs')
    if not isinstance(raw, list):
        return []
    return [str(item).replace('\\', '/').strip() for item in raw if str(item).strip()]


def _title(task: dict[str, Any]) -> str:
    return str(task.get('title') or '').strip()


def _task_ref(task: dict[str, Any]) -> str:
    taskmaster_id = task.get('taskmaster_id')
    if taskmaster_id is not None:
        return f"taskmaster_id={taskmaster_id}"
    task_id = task.get('id')
    return f"id={task_id}" if task_id is not None else '<unknown-task>'


def _contains_any(text: str, keywords: tuple[str, ...]) -> bool:
    lowered = text.lower()
    return any(keyword in lowered for keyword in keywords)


def _requires_contract_refs(task: dict[str, Any]) -> tuple[bool, str]:
    layer = str(task.get('layer') or '').strip().lower()
    title = _title(task)
    labels = _labels(task)
    test_refs = _test_refs(task)

    if layer in PRESENTATION_LAYERS:
        has_ui_tests = any('/tests/ui/' in ref.lower() for ref in test_refs)
        if (_contains_any(title, UI_REQUIRED_TITLE_KEYWORDS) and (has_ui_tests or 'ui' in labels or 'hud' in labels)):
            return True, 'ui-consumer-task'
        if labels & UI_REQUIRED_LABELS:
            return True, 'ui-consumer-task'

    if layer in CORE_LAYERS:
        lowered = title.lower()
        if any(keyword in lowered for keyword in CORE_SKIP_TITLE_KEYWORDS):
            return False, ''
        if _contains_any(title, CORE_REQUIRED_TITLE_KEYWORDS):
            return True, 'core-runtime-task'

    return False, ''


def _normalize_task_file_key(path: Path, repo_root: Path) -> str:
    try:
        return _posix(path.resolve().relative_to(repo_root))
    except Exception:
        return _posix(path)


def _load_consistency_config(repo_root: Path, whitelist_path: Path) -> tuple[dict[int, dict[str, list[str]]], set[int]]:
    full_path = whitelist_path if whitelist_path.is_absolute() else (repo_root / whitelist_path)
    if not full_path.exists():
        return {}, set()

    payload = _read_json(full_path)
    if not isinstance(payload, dict):
        raise ValueError(f'Whitelist must be a JSON object: {_posix(whitelist_path)}')

    overrides_raw = payload.get('overrides', [])
    if not isinstance(overrides_raw, list):
        raise ValueError(f'Whitelist field overrides must be an array: {_posix(whitelist_path)}')

    required_exemptions_raw = payload.get('required_exemptions', [])
    if not isinstance(required_exemptions_raw, list):
        raise ValueError(f'Whitelist field required_exemptions must be an array: {_posix(whitelist_path)}')

    overrides: dict[int, dict[str, list[str]]] = {}
    for idx, item in enumerate(overrides_raw):
        if not isinstance(item, dict):
            raise ValueError(f'Whitelist override item must be an object at index {idx}: {_posix(whitelist_path)}')
        try:
            taskmaster_id = int(item.get('taskmaster_id'))
        except Exception as exc:
            raise ValueError(f'Whitelist override taskmaster_id must be an integer at index {idx}: {_posix(whitelist_path)}') from exc
        files = item.get('files')
        if not isinstance(files, dict):
            raise ValueError(f'Whitelist override files must be an object at index {idx}: {_posix(whitelist_path)}')
        overrides[taskmaster_id] = {
            _posix(Path(file_key)): _normalize_refs(refs if isinstance(refs, list) else [])
            for file_key, refs in files.items()
        }

    required_exemptions: set[int] = set()
    for item in required_exemptions_raw:
        try:
            required_exemptions.add(int(item))
        except Exception as exc:
            raise ValueError(f'Whitelist required_exemptions values must be integers: {_posix(whitelist_path)}') from exc

    return overrides, required_exemptions


def _iter_task_files(repo_root: Path, task_files: list[Path]) -> list[tuple[Path, list[dict[str, Any]]]]:
    loaded: list[tuple[Path, list[dict[str, Any]]]] = []
    for task_file in task_files:
        full_path = task_file if task_file.is_absolute() else (repo_root / task_file)
        if not full_path.exists():
            raise FileNotFoundError(f'Missing task file: {_posix(task_file)}')
        payload = _read_json(full_path)
        if not isinstance(payload, list):
            raise ValueError(f'Task file must be a JSON array: {_posix(task_file)}')
        loaded.append((full_path, payload))
    return loaded


def run_gate(repo_root: Path, task_files: list[Path], whitelist_path: Path) -> dict[str, Any]:
    allowed_events, event_sources = _load_allowed_events(repo_root)
    overrides, required_exemptions = _load_consistency_config(repo_root, whitelist_path)
    loaded_task_files = _iter_task_files(repo_root, task_files)

    errors: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []
    per_file: list[dict[str, Any]] = []
    shared_refs: dict[int, dict[str, list[str]]] = {}

    for full_path, tasks in loaded_task_files:
        file_key = _normalize_task_file_key(full_path, repo_root)
        file_errors = 0
        file_required = 0
        file_present = 0
        file_missing = 0
        file_invalid = 0

        for task in tasks:
            if not isinstance(task, dict):
                errors.append({'file': file_key, 'rule': 'task_not_object', 'message': 'Task entry must be an object.'})
                file_errors += 1
                continue

            ref_id = _task_ref(task)
            taskmaster_id_raw = task.get('taskmaster_id')
            taskmaster_id = None
            if taskmaster_id_raw is not None:
                try:
                    taskmaster_id = int(taskmaster_id_raw)
                except Exception:
                    errors.append({'file': file_key, 'task': ref_id, 'rule': 'taskmaster_id_invalid', 'message': 'taskmaster_id must be an integer when present.'})
                    file_errors += 1

            refs_raw = task.get('contractRefs')
            if refs_raw is not None and not isinstance(refs_raw, list):
                errors.append({'file': file_key, 'task': ref_id, 'rule': 'contractRefs_not_array', 'message': 'contractRefs must be an array when present.'})
                file_errors += 1
                continue

            refs_list = refs_raw if isinstance(refs_raw, list) else []
            normalized_refs = _normalize_refs(refs_list)
            duplicates = len(refs_list) != len({str(item).strip() for item in refs_list if str(item).strip()})
            if duplicates:
                errors.append({'file': file_key, 'task': ref_id, 'rule': 'contractRefs_duplicate_values', 'message': 'contractRefs must not contain duplicate values.'})
                file_errors += 1

            invalid_refs = [ref for ref in normalized_refs if ref not in allowed_events]
            for ref in invalid_refs:
                errors.append({'file': file_key, 'task': ref_id, 'rule': 'contractRef_unknown_event', 'message': f'Unknown contractRefs event: {ref}'})
                file_errors += 1
                file_invalid += 1

            requires_refs, reason = _requires_contract_refs(task)
            if requires_refs:
                file_required += 1
                if not normalized_refs and (taskmaster_id is None or taskmaster_id not in required_exemptions):
                    errors.append({'file': file_key, 'task': ref_id, 'rule': 'contractRefs_required_missing', 'message': f'contractRefs is required for {reason}.'})
                    file_errors += 1
                    file_missing += 1

            if normalized_refs:
                file_present += 1

            if taskmaster_id is not None:
                shared_refs.setdefault(taskmaster_id, {})[file_key] = normalized_refs

        per_file.append(
            {
                'file': file_key,
                'tasks': len(tasks),
                'required_tasks': file_required,
                'with_contractRefs': file_present,
                'missing_required_contractRefs': file_missing,
                'invalid_contractRefs': file_invalid,
                'errors': file_errors,
            }
        )

    normalized_task_files = {_normalize_task_file_key((repo_root / path) if not path.is_absolute() else path, repo_root) for path in task_files}
    for taskmaster_id, refs_by_file in sorted(shared_refs.items()):
        if len(refs_by_file) < 2:
            continue
        values = {tuple(refs) for refs in refs_by_file.values()}
        if len(values) <= 1:
            continue
        override = overrides.get(taskmaster_id)
        if override:
            normalized_override = {key: tuple(value) for key, value in override.items() if key in normalized_task_files}
            normalized_actual = {key: tuple(value) for key, value in refs_by_file.items() if key in normalized_task_files}
            if normalized_override == normalized_actual:
                warnings.append(
                    {
                        'taskmaster_id': taskmaster_id,
                        'rule': 'consistency_override_applied',
                        'message': 'contractRefs mismatch accepted by explicit whitelist override.',
                    }
                )
                continue
        errors.append(
            {
                'taskmaster_id': taskmaster_id,
                'rule': 'contractRefs_mismatch_between_task_views',
                'message': 'Shared taskmaster_id must use identical contractRefs across task view files.',
                'files': refs_by_file,
            }
        )

    return {
        'ts': dt.datetime.now(dt.timezone.utc).isoformat(),
        'action': 'task-contract-refs-gate',
        'status': 'ok' if not errors else 'fail',
        'task_files': [_posix(path) for path in task_files],
        'allowed_events_count': len(allowed_events),
        'allowed_event_sources_count': len(event_sources),
        'required_exemptions': sorted(required_exemptions),
        'files': per_file,
        'warnings_count': len(warnings),
        'warnings': warnings,
        'errors_count': len(errors),
        'errors': errors,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description='Validate task view contractRefs against local contract events.')
    parser.add_argument('--task-files', nargs='*', default=[_posix(path) for path in DEFAULT_TASK_FILES])
    parser.add_argument('--whitelist', default=_posix(DEFAULT_CONSISTENCY_WHITELIST))
    parser.add_argument('--out', default='')
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[2]
    task_files = [Path(item) for item in args.task_files]
    whitelist_path = Path(args.whitelist)

    try:
        summary = run_gate(repo_root, task_files, whitelist_path)
    except Exception as exc:
        print(f'TASK_CONTRACT_REFS status=fail reason=exception msg={exc}')
        return 1

    out_path = Path(args.out) if args.out else (Path('logs') / 'ci' / _today() / 'task-contract-refs-gate' / 'summary.json')
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

    print(
        f"TASK_CONTRACT_REFS status={summary['status']} errors={summary['errors_count']} "
        f"warnings={summary['warnings_count']} allowed_events={summary['allowed_events_count']} out={out_path.as_posix()}"
    )
    if summary['status'] != 'ok':
        for item in summary['errors'][:30]:
            task_part = f" task={item.get('task')}" if item.get('task') else ''
            print(f" - file={item.get('file', '')}{task_part} rule={item['rule']} msg={item['message']}")
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
