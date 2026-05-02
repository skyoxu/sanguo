#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from pathlib import Path
from typing import Any

from collect_ui_wiring_inputs import OVERLAY_ROOT, TASKS_BACK, TASKS_GAMEPLAY, TASKS_JSON, UI_GDD_FLOW, build_summary


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


def validate(
    *,
    repo_root: Path,
    ui_gdd_flow_path: Path = UI_GDD_FLOW,
    tasks_json_path: Path = TASKS_JSON,
    tasks_back_path: Path = TASKS_BACK,
    tasks_gameplay_path: Path = TASKS_GAMEPLAY,
    overlay_root_path: Path = OVERLAY_ROOT,
    chapter7_profile_path: Path | None = None,
) -> tuple[int, dict[str, Any]]:
    summary = build_summary(
        repo_root=repo_root,
        tasks_json_path=tasks_json_path,
        tasks_back_path=tasks_back_path,
        tasks_gameplay_path=tasks_gameplay_path,
        overlay_root_path=overlay_root_path,
    )
    if summary.get('status') == 'skipped':
        payload = {
            'ts': dt.datetime.now(dt.timezone.utc).isoformat(),
            'action': 'validate-chapter7-ui-wiring',
            'status': 'skipped',
            'reason': summary.get('reason') or 'missing_task_triplet',
            'target': str(ui_gdd_flow_path).replace('\\', '/'),
            'required_sections': REQUIRED_SECTIONS,
            'missing_sections': [],
            'completed_master_tasks_count': 0,
            'missing_done_task_refs': [],
            'missing_source_files': summary.get('missing_source_files', []),
        }
        return 0, payload

    gdd_path = ui_gdd_flow_path if ui_gdd_flow_path.is_absolute() else (repo_root / ui_gdd_flow_path)
    missing_sections: list[str] = []
    missing_done_task_refs: list[int] = []
    if not gdd_path.exists():
        payload = {
            'ts': dt.datetime.now(dt.timezone.utc).isoformat(),
            'action': 'validate-chapter7-ui-wiring',
            'status': 'fail',
            'reason': 'missing_ui_gdd_flow',
            'target': str(ui_gdd_flow_path).replace('\\', '/'),
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
        'target': str(ui_gdd_flow_path).replace('\\', '/'),
        'required_sections': REQUIRED_SECTIONS,
        'missing_sections': missing_sections,
        'completed_master_tasks_count': summary['completed_master_tasks_count'],
        'missing_done_task_refs': missing_done_task_refs,
    }
    return (0 if payload['status'] == 'ok' else 1), payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description='Hard gate for Chapter 7 UI wiring workflow artifacts.')
    parser.add_argument('--repo-root', default='.')
    parser.add_argument('--ui-gdd-flow-path', default=str(UI_GDD_FLOW))
    parser.add_argument('--tasks-json-path', default=str(TASKS_JSON))
    parser.add_argument('--tasks-back-path', default=str(TASKS_BACK))
    parser.add_argument('--tasks-gameplay-path', default=str(TASKS_GAMEPLAY))
    parser.add_argument('--overlay-root-path', default=str(OVERLAY_ROOT))
    parser.add_argument('--chapter7-profile-path', default='')
    parser.add_argument('--out', default='')
    args = parser.parse_args(argv)

    repo_root = Path(args.repo_root).resolve()
    rc, payload = validate(
        repo_root=repo_root,
        ui_gdd_flow_path=Path(args.ui_gdd_flow_path),
        tasks_json_path=Path(args.tasks_json_path),
        tasks_back_path=Path(args.tasks_back_path),
        tasks_gameplay_path=Path(args.tasks_gameplay_path),
        overlay_root_path=Path(args.overlay_root_path),
        chapter7_profile_path=Path(args.chapter7_profile_path) if args.chapter7_profile_path else None,
    )
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
