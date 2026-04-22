#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from pathlib import Path
from typing import Any

from collect_ui_wiring_inputs import UI_GDD_FLOW, build_summary


REQUIRED_SECTIONS = [
    '## 5. UI Wiring Matrix',
    '## 10. Unwired UI Feature List',
    '## 11. Next UI Wiring Task Candidates',
]


def _today() -> str:
    return dt.date.today().strftime('%Y-%m-%d')


def _extract_task_refs(text: str) -> set[int]:
    hits = set()
    for match in re.finditer(r'\bT0*(\d{1,4})\b', text):
        hits.add(int(match.group(1)))
    return hits


def validate(*, repo_root: Path) -> tuple[int, dict[str, Any]]:
    summary = build_summary(repo_root=repo_root)
    gdd_path = repo_root / UI_GDD_FLOW
    missing_sections: list[str] = []
    missing_done_task_refs: list[int] = []
    if not gdd_path.exists():
        payload = {
            'ts': dt.datetime.now(dt.timezone.utc).isoformat(),
            'action': 'validate-chapter7-ui-wiring',
            'status': 'fail',
            'reason': 'missing_ui_gdd_flow',
            'target': str(UI_GDD_FLOW).replace('\\', '/'),
            'missing_sections': REQUIRED_SECTIONS,
            'missing_done_task_refs': [item['task_id'] for item in summary['needed_wiring_features']],
        }
        return 1, payload

    text = gdd_path.read_text(encoding='utf-8')
    for section in REQUIRED_SECTIONS:
        if section not in text:
            missing_sections.append(section)
    task_refs = _extract_task_refs(text)
    for item in summary['needed_wiring_features']:
        task_id = int(item['task_id'])
        if task_id not in task_refs:
            missing_done_task_refs.append(task_id)
    payload = {
        'ts': dt.datetime.now(dt.timezone.utc).isoformat(),
        'action': 'validate-chapter7-ui-wiring',
        'status': 'ok' if not missing_sections and not missing_done_task_refs else 'fail',
        'target': str(UI_GDD_FLOW).replace('\\', '/'),
        'required_sections': REQUIRED_SECTIONS,
        'missing_sections': missing_sections,
        'completed_master_tasks_count': summary['completed_master_tasks_count'],
        'missing_done_task_refs': missing_done_task_refs,
    }
    return (0 if payload['status'] == 'ok' else 1), payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description='Hard gate for Chapter 7 UI wiring workflow artifacts.')
    parser.add_argument('--repo-root', default='.')
    parser.add_argument('--out', default='')
    args = parser.parse_args(argv)

    repo_root = Path(args.repo_root).resolve()
    rc, payload = validate(repo_root=repo_root)
    out = Path(args.out) if args.out else (repo_root / 'logs' / 'ci' / _today() / 'chapter7-ui-wiring-gate' / 'summary.json')
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(f"CHAPTER7_UI_WIRING_GATE status={payload['status']} missing_sections={len(payload['missing_sections'])} missing_done_tasks={len(payload['missing_done_task_refs'])} out={str(out).replace('\\', '/')}")
    if rc != 0:
        if payload['missing_sections']:
            print(f" - missing_sections={payload['missing_sections']}")
        if payload['missing_done_task_refs']:
            print(f" - missing_done_task_refs={payload['missing_done_task_refs']}")
    return rc


if __name__ == '__main__':
    raise SystemExit(main())
