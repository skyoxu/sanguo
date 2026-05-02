#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path
from typing import Any


def _today() -> str:
    return dt.date.today().strftime('%Y-%m-%d')


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding='utf-8'))


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\n')


def _apply_master_status(data: dict[str, Any], *, task_id: int, to_status: str) -> bool:
    for item in data.get('master', {}).get('tasks', []):
        if isinstance(item, dict) and item.get('id') == task_id:
            item['status'] = to_status
            return True
    return False


def _apply_view_status(data: list[dict[str, Any]], *, task_id: int, to_status: str) -> bool:
    for item in data:
        if isinstance(item, dict) and item.get('taskmaster_id') == task_id:
            item['status'] = to_status
            return True
    return False


def _apply_operation(op: dict[str, Any], *, dry_run: bool) -> dict[str, Any]:
    path = Path(str(op.get('path') or ''))
    view = str(op.get('view') or '')
    task_id = int(op.get('task_id'))
    to_status = str(op.get('to_status') or '')
    payload = _load_json(path)
    if view == 'tasks_json':
        updated = _apply_master_status(payload, task_id=task_id, to_status=to_status)
    else:
        updated = _apply_view_status(payload, task_id=task_id, to_status=to_status)
    if updated and not dry_run:
        _write_json(path, payload)
    return {
        'path': str(path.resolve()).replace('\\', '/'),
        'view': view,
        'task_id': task_id,
        'task_ref': op.get('task_ref', ''),
        'from_status': op.get('from_status', ''),
        'to_status': to_status,
        'applied': bool(updated),
        'dry_run': dry_run,
    }


def apply_patch_contract(*, patch_path: Path, dry_run: bool) -> tuple[int, dict[str, Any]]:
    contract = _load_json(patch_path)
    operations = list(contract.get('operations') or [])
    results = [_apply_operation(item, dry_run=dry_run) for item in operations]
    failed = [item for item in results if not item['applied']]
    return (
        0 if not failed else 1,
        {
            'ts': dt.datetime.now(dt.timezone.utc).isoformat(),
            'action': 'apply-chapter7-status-patch',
            'status': 'ok' if not failed else 'fail',
            'dry_run': dry_run,
            'patch_path': str(patch_path.resolve()).replace('\\', '/'),
            'operation_count': len(operations),
            'applied_count': sum(1 for item in results if item['applied']),
            'failed_count': len(failed),
            'results': results,
        },
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description='Apply or preview a Chapter 7 task status patch contract.')
    parser.add_argument('--patch', required=True)
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--out-json', default='')
    parser.add_argument('--self-check', action='store_true')
    args = parser.parse_args(argv)

    patch_path = Path(args.patch).resolve()
    if args.self_check:
        payload = {
            'ts': dt.datetime.now(dt.timezone.utc).isoformat(),
            'action': 'apply-chapter7-status-patch',
            'status': 'ok',
            'dry_run': bool(args.dry_run),
            'patch': str(patch_path).replace('\\', '/'),
            'planned_steps': ['load-patch', 'apply-operations', 'emit-summary'],
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0

    rc, payload = apply_patch_contract(patch_path=patch_path, dry_run=bool(args.dry_run))
    out = Path(args.out_json) if args.out_json else (patch_path.parent / ('apply-dry-run-summary.json' if args.dry_run else 'apply-summary.json'))
    _write_json(out, payload)
    print(f"CHAPTER7_STATUS_PATCH status={payload['status']} dry_run={str(bool(args.dry_run)).lower()} out={str(out).replace('\\', '/')}")
    return rc


if __name__ == '__main__':
    raise SystemExit(main())
