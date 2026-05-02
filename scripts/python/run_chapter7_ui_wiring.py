#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

from _chapter7_profile import bucket_names, bucket_profile, load_chapter7_profile, surface_aliases


def _today() -> str:
    return dt.date.today().strftime('%Y-%m-%d')


def _run(cmd: list[str], *, cwd: Path) -> tuple[int, str]:
    proc = subprocess.run(cmd, cwd=str(cwd), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding='utf-8', errors='ignore', check=False)
    return proc.returncode, proc.stdout or ''


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding='utf-8', newline='\n')


def _script_path(name: str) -> str:
    return str((Path(__file__).resolve().parent / name))


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load_json_if_exists(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding='utf-8'))


def _optional_resolved_path(repo_root: Path, value: Path | None) -> Path | None:
    if value is None:
        return None
    return value if value.is_absolute() else (repo_root / value)


def _contract_path(repo_root: Path, value: Path | None) -> str:
    if value is None:
        return ''
    resolved = _optional_resolved_path(repo_root, value)
    if resolved is None:
        return ''
    return str(resolved.resolve()).replace('\\', '/')


def _canonical_input_snapshot(source_payload: dict[str, Any]) -> dict[str, Any]:
    if not source_payload:
        return {}
    return {
        'action': source_payload.get('action'),
        'repo_root': source_payload.get('repo_root'),
        'source_files': source_payload.get('source_files', []),
        'completed_master_tasks_count': source_payload.get('completed_master_tasks_count'),
        'needed_wiring_features_count': source_payload.get('needed_wiring_features_count'),
        'feature_family_counts': source_payload.get('feature_family_counts', {}),
        'needed_wiring_features': source_payload.get('needed_wiring_features', []),
    }


def _read_text_if_exists(path: Path) -> str:
    try:
        return path.read_text(encoding='utf-8')
    except FileNotFoundError:
        return ''


def _scene_has_surface_nodes(repo_root: Path, scene_rel_path: str, surfaces: list[str], *, profile: dict[str, Any]) -> list[str]:
    scene_path = (repo_root / scene_rel_path).resolve()
    scene_text = _read_text_if_exists(scene_path)
    if not scene_text:
        return []

    present: list[str] = []
    for surface in surfaces:
        aliases = surface_aliases(profile, surface)
        if any(f'[node name="{alias}"' in scene_text for alias in aliases):
            present.append(surface)
    return present


def _extract_section(text: str, heading: str | list[str]) -> str:
    headings = {heading} if isinstance(heading, str) else set(heading)
    lines = text.splitlines()
    capture = False
    out: list[str] = []
    for line in lines:
        stripped = line.strip()
        if stripped in headings:
            capture = True
            continue
        if capture and (stripped.startswith('## ') or stripped.startswith('### ')):
            break
        if capture:
            out.append(line)
    return '\n'.join(out)


def _normalize_table_cell(value: str) -> str:
    normalized = value.strip()
    if normalized.startswith('`') and normalized.endswith('`') and len(normalized) >= 2:
        normalized = normalized[1:-1].strip()
    return normalized


def _split_path_list(value: str) -> list[str]:
    normalized = _normalize_table_cell(value).replace('`', '')
    if not normalized:
        return []
    return [item.strip() for item in normalized.split(',') if item.strip()]


def _dedupe_keep_order(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value in seen or not value:
            continue
        seen.add(value)
        result.append(value)
    return result


def _pick_evidence_status(evidence_statuses: list[str]) -> str:
    if any(status == 'docs-only' for status in evidence_statuses):
        return 'docs-only'
    if any(status == 'partial' for status in evidence_statuses):
        return 'partial'
    if any(status == 'test-only' for status in evidence_statuses):
        return 'test-only'
    if evidence_statuses and all(status == 'runtime' for status in evidence_statuses):
        return 'runtime'
    return 'unknown'


def _surface_closure_status(surface: str, implemented_surfaces: list[str], *, profile: dict[str, Any]) -> str:
    aliases = set(surface_aliases(profile, surface))
    return 'implemented' if any(alias in implemented_surfaces for alias in aliases) else 'pending'


def _surface_present_in_paths(surface: str, paths: list[str], *, profile: dict[str, Any]) -> bool:
    aliases = set(surface_aliases(profile, surface))
    normalized_paths = [path.strip() for path in paths if path.strip()]
    return any(path in aliases or any(alias in path for alias in aliases) for path in normalized_paths)


def _load_task_status_views(
    *,
    repo_root: Path,
    tasks_json_path: Path,
    tasks_back_path: Path,
    tasks_gameplay_path: Path,
) -> dict[str, dict[int, dict[str, Any]]]:
    tasks_json = _load_json_if_exists(tasks_json_path if tasks_json_path.is_absolute() else (repo_root / tasks_json_path))
    tasks_back = _load_json_if_exists(tasks_back_path if tasks_back_path.is_absolute() else (repo_root / tasks_back_path))
    tasks_gameplay = _load_json_if_exists(tasks_gameplay_path if tasks_gameplay_path.is_absolute() else (repo_root / tasks_gameplay_path))
    master_index: dict[int, dict[str, Any]] = {}
    for item in tasks_json.get('master', {}).get('tasks', []):
        if isinstance(item, dict) and isinstance(item.get('id'), int):
            master_index[item['id']] = item
    back_index: dict[int, dict[str, Any]] = {}
    if isinstance(tasks_back, list):
        for item in tasks_back:
            if isinstance(item, dict) and isinstance(item.get('taskmaster_id'), int):
                back_index[item['taskmaster_id']] = item
    gameplay_index: dict[int, dict[str, Any]] = {}
    if isinstance(tasks_gameplay, list):
        for item in tasks_gameplay:
            if isinstance(item, dict) and isinstance(item.get('taskmaster_id'), int):
                gameplay_index[item['taskmaster_id']] = item
    return {
        'tasks_json': master_index,
        'tasks_back': back_index,
        'tasks_gameplay': gameplay_index,
    }


def _build_status_patch_preview(
    *,
    repo_root: Path,
    closure_summary: dict[str, Any],
    tasks_json_path: Path,
    tasks_back_path: Path,
    tasks_gameplay_path: Path,
) -> dict[str, Any]:
    view_indexes = _load_task_status_views(
        repo_root=repo_root,
        tasks_json_path=tasks_json_path,
        tasks_back_path=tasks_back_path,
        tasks_gameplay_path=tasks_gameplay_path,
    )
    recommended_status_by_recommendation = {
        'done-ready': 'done',
        'partial-closure': 'review',
        'keep-open': 'pending',
    }
    view_path_map = {
        'tasks_json': tasks_json_path,
        'tasks_back': tasks_back_path,
        'tasks_gameplay': tasks_gameplay_path,
    }
    mismatches: list[dict[str, Any]] = []
    for slice_item in closure_summary.get('slices', []):
        contract = slice_item.get('write_back_contract', {})
        task_id = contract.get('task_id')
        if not isinstance(task_id, int):
            continue
        recommendation = str(contract.get('current_recommendation') or '')
        recommended_status = recommended_status_by_recommendation.get(recommendation, 'review')
        for view_name, index in view_indexes.items():
            task_row = index.get(task_id)
            if not task_row:
                continue
            current_status = str(task_row.get('status') or '')
            if current_status == recommended_status:
                continue
            path_obj = view_path_map[view_name]
            resolved_path = path_obj if path_obj.is_absolute() else (repo_root / path_obj)
            mismatches.append(
                {
                    'view': view_name,
                    'path': str(resolved_path.resolve()).replace('\\', '/'),
                    'task_id': task_id,
                    'task_ref': contract.get('task_ref'),
                    'title': task_row.get('title', ''),
                    'bucket': slice_item.get('bucket', ''),
                    'current_status': current_status,
                    'recommended_status': recommended_status,
                    'write_back_recommendation': recommendation,
                    'ready_for_done': bool(contract.get('ready_for_done')),
                    'blocker_class': contract.get('blocker_class', ''),
                    'must_keep_open_reasons': list(contract.get('must_keep_open_reasons') or []),
                }
            )
    return {
        'schema_version': 1,
        'status': 'ok',
        'mismatch_count': len(mismatches),
        'views_checked': ['tasks_json', 'tasks_back', 'tasks_gameplay'],
        'status_mapping_policy': recommended_status_by_recommendation,
        'mismatches': mismatches,
    }


def _render_status_patch_preview_markdown(preview: dict[str, Any]) -> str:
    lines: list[str] = []
    lines.append('# Chapter 7 Task Status Patch Preview')
    lines.append('')
    lines.append(f"- mismatch_count: `{preview.get('mismatch_count', 0)}`")
    lines.append(f"- views_checked: `{', '.join(preview.get('views_checked', []))}`")
    policy = preview.get('status_mapping_policy', {})
    if policy:
        lines.append(
            "- status_mapping_policy: "
            + ", ".join(f"`{key} -> {value}`" for key, value in policy.items())
        )
    lines.append('')
    mismatches = preview.get('mismatches', [])
    if not mismatches:
        lines.append('No status mismatches detected.')
        lines.append('')
        return '\n'.join(lines)
    grouped: dict[str, list[dict[str, Any]]] = {}
    for item in mismatches:
        grouped.setdefault(str(item.get('path') or ''), []).append(item)
    for path, items in grouped.items():
        lines.append(f'## {path}')
        lines.append('')
        lines.append('| Task | Bucket | Current | Recommended | Closure | Blocker |')
        lines.append('| --- | --- | --- | --- | --- | --- |')
        for item in items:
            lines.append(
                f"| {item.get('task_ref', '')} | {item.get('bucket', '')} | "
                f"`{item.get('current_status', '')}` | `{item.get('recommended_status', '')}` | "
                f"`{item.get('write_back_recommendation', '')}` | `{item.get('blocker_class', '')}` |"
            )
        lines.append('')
        for item in items:
            lines.append(f"### {item.get('task_ref', '')} {item.get('title', '')}")
            lines.append('')
            lines.append(f"- current_status: `{item.get('current_status', '')}`")
            lines.append(f"- recommended_status: `{item.get('recommended_status', '')}`")
            lines.append(f"- write_back_recommendation: `{item.get('write_back_recommendation', '')}`")
            lines.append(f"- ready_for_done: `{str(bool(item.get('ready_for_done'))).lower()}`")
            lines.append(f"- blocker_class: `{item.get('blocker_class', '')}`")
            reasons = list(item.get('must_keep_open_reasons') or [])
            if reasons:
                lines.append('- reasons_to_keep_open:')
                for reason in reasons:
                    lines.append(f"  - {reason}")
            lines.append('')
    return '\n'.join(lines).rstrip() + '\n'


def _build_status_patch_contract(preview: dict[str, Any]) -> dict[str, Any]:
    operations: list[dict[str, Any]] = []
    for item in preview.get('mismatches', []):
        operations.append(
            {
                'op': 'replace-task-status',
                'path': item.get('path', ''),
                'view': item.get('view', ''),
                'task_id': item.get('task_id'),
                'task_ref': item.get('task_ref', ''),
                'title': item.get('title', ''),
                'from_status': item.get('current_status', ''),
                'to_status': item.get('recommended_status', ''),
                'bucket': item.get('bucket', ''),
                'closure_recommendation': item.get('write_back_recommendation', ''),
                'ready_for_done': bool(item.get('ready_for_done')),
                'blocker_class': item.get('blocker_class', ''),
                'reasons': list(item.get('must_keep_open_reasons') or []),
            }
        )
    return {
        'schema_version': 1,
        'contract_type': 'chapter7-task-status-patch',
        'status': 'ok',
        'operation_count': len(operations),
        'operations': operations,
    }


def _extract_table_row(section_text: str, task_id: int) -> dict[str, str]:
    marker = f'| T{task_id:02d} |'
    for line in section_text.splitlines():
        if not line.strip().startswith(marker):
            continue
        cells = [_normalize_table_cell(cell) for cell in line.strip().strip('|').split('|')]
        if len(cells) < 7:
            continue
        return {
            'task': cells[0],
            'title': cells[1],
            'primary_surface_code': cells[2],
            'primary_test_evidence': cells[3],
            'governance_path': cells[4],
            'evidence_status': cells[5],
            'gap_to_close': cells[6],
        }
    return {}


def _extract_all_table_rows(section_text: str) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for line in section_text.splitlines():
        stripped = line.strip()
        if not stripped.startswith('| T'):
            continue
        cells = [_normalize_table_cell(cell) for cell in stripped.strip('|').split('|')]
        if len(cells) < 7:
            continue
        rows.append(
            {
                'task': cells[0],
                'title': cells[1],
                'primary_surface_code': cells[2],
                'primary_test_evidence': cells[3],
                'governance_path': cells[4],
                'evidence_status': cells[5],
                'gap_to_close': cells[6],
            }
        )
    return rows


def _candidate_by_bucket(candidate_payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for item in candidate_payload.get('candidates', []) if isinstance(candidate_payload, dict) else []:
        if not isinstance(item, dict):
            continue
        bucket = str(item.get('bucket') or '').strip()
        if bucket:
            result[bucket] = item
    return result


def _bucket_to_section_heading(profile: dict[str, Any], bucket: str) -> list[str]:
    values = list(bucket_profile(profile, bucket).get('section_headings') or [])
    return [str(item) for item in values if str(item).strip()]


def _build_closure_summary(
    *,
    repo_root: Path,
    source_payload: dict[str, Any],
    ui_candidates_path: Path,
    wiring_audit_path: Path | None,
    profile: dict[str, Any],
) -> dict[str, Any]:
    candidate_payload = _load_json_if_exists(ui_candidates_path)
    candidates_by_bucket = _candidate_by_bucket(candidate_payload)
    audit_text = _read_text_if_exists(wiring_audit_path) if wiring_audit_path and wiring_audit_path.exists() else ''
    bucket_order = bucket_names(profile)
    slices: list[dict[str, Any]] = []
    for bucket in bucket_order:
        config = bucket_profile(profile, bucket)
        candidate = candidates_by_bucket.get(bucket, {})
        section_text = _extract_section(audit_text, _bucket_to_section_heading(profile, bucket)) if audit_text else ''
        section_rows = _extract_all_table_rows(section_text) if section_text else []
        closure_task_ids = [int(item) for item in config.get('closure_task_ids', []) if isinstance(item, int)]
        task_rows = [_extract_table_row(section_text, task_id) for task_id in closure_task_ids]
        task_rows = [row for row in task_rows if row]
        evidence_statuses = [row['evidence_status'] for row in section_rows if row.get('evidence_status')]
        evidence_status = _pick_evidence_status(evidence_statuses)
        suggested_surfaces = list(candidate.get('suggested_standalone_surfaces') or [])
        implemented_surfaces: list[str] = []
        pending_surfaces = list(suggested_surfaces)
        primary_surface_paths = _dedupe_keep_order(
            [path for row in section_rows for path in _split_path_list(row.get('primary_surface_code', ''))]
        )
        scene_rel = str(config.get('scene_rel_path') or '').strip()
        if scene_rel:
            implemented_surfaces = _scene_has_surface_nodes(
                repo_root=repo_root,
                scene_rel_path=scene_rel,
                surfaces=suggested_surfaces,
                profile=profile,
            )
        implemented_surfaces = _dedupe_keep_order(
            implemented_surfaces
            + [surface for surface in suggested_surfaces if _surface_present_in_paths(surface, primary_surface_paths, profile=profile)]
        )
        if suggested_surfaces:
            pending_surfaces = [item for item in suggested_surfaces if item not in implemented_surfaces]
        gap_to_close = [row['gap_to_close'] for row in task_rows if row.get('gap_to_close') and row.get('gap_to_close') != 'None']
        epic_usable = evidence_status == 'runtime' and len(pending_surfaces) == 0 and not gap_to_close
        if evidence_status in {'docs-only', 'test-only'}:
            write_back_recommendation = 'keep-open'
        elif evidence_status == 'partial' or pending_surfaces or gap_to_close:
            write_back_recommendation = 'partial-closure'
        else:
            write_back_recommendation = 'done-ready'
        standalone_surface_status = [
            {
                'surface': surface,
                'status': _surface_closure_status(surface, implemented_surfaces, profile=profile),
            }
            for surface in suggested_surfaces
        ]
        primary_test_paths = _dedupe_keep_order(
            [path for row in section_rows for path in _split_path_list(row.get('primary_test_evidence', ''))]
        )
        governance_paths = _dedupe_keep_order(
            [path for row in section_rows for path in _split_path_list(row.get('governance_path', ''))]
        )
        scope_task_ids = list(candidate.get('scope_task_ids') or [])
        wiring_task_id = int(config.get('wiring_task_id') or 0)
        related_wiring_row = next((row for row in task_rows if row.get('task') == f'T{wiring_task_id:02d}'), {})
        blocker_class = 'surface-missing' if pending_surfaces else ('evidence-missing' if evidence_status != 'runtime' else 'none')
        ready_for_done = evidence_status == 'runtime' and len(pending_surfaces) == 0 and not gap_to_close
        write_back_contract = {
            'task_id': wiring_task_id,
            'task_ref': f'T{wiring_task_id:02d}',
            'current_recommendation': write_back_recommendation,
            'ready_for_done': ready_for_done,
            'blocker_class': blocker_class,
            'must_keep_open_reasons': _dedupe_keep_order(
                pending_surfaces + gap_to_close + ([] if evidence_status == 'runtime' else [f'evidence_status={evidence_status}'])
            ),
            'done_when': {
                'required_evidence_status': 'runtime',
                'required_pending_surfaces_count': 0,
                'required_gap_count': 0,
            },
            'missing_surface_owners': pending_surfaces,
            'related_scope_task_ids': scope_task_ids,
            'wiring_task_gap': related_wiring_row.get('gap_to_close', ''),
        }
        slices.append(
            {
                'bucket': bucket,
                'screen_group': candidate.get('screen_group') or '',
                'ui_entry': candidate.get('ui_entry') or '',
                'surface_status': {
                    'suggested_surfaces': suggested_surfaces,
                    'implemented_surfaces': implemented_surfaces,
                    'pending_surfaces': pending_surfaces,
                },
                'evidence_status': evidence_status,
                'gap_to_close': gap_to_close,
                'epic_usable': epic_usable,
                'write_back_recommendation': write_back_recommendation,
                'standalone_surface_status': standalone_surface_status,
                'evidence_paths': {
                    'primary_surface_code': primary_surface_paths,
                    'primary_test_evidence': primary_test_paths,
                    'governance_path': governance_paths,
                    'candidate_test_refs': list(candidate.get('test_refs') or []),
                    'candidate_validation_artifact_targets': list(candidate.get('validation_artifact_targets') or []),
                },
                'write_back_contract': write_back_contract,
                'task_rows': task_rows,
            }
        )
    return {
        'slice_count': len(slices),
        'epic_usable_count': sum(1 for item in slices if item['epic_usable']),
        'done_ready_count': sum(1 for item in slices if item['write_back_contract']['ready_for_done']),
        'partial_closure_count': sum(1 for item in slices if item['write_back_recommendation'] == 'partial-closure'),
        'keep_open_count': sum(1 for item in slices if item['write_back_recommendation'] == 'keep-open'),
        'slices': slices,
    }


def _artifact_entry(*, repo_root: Path, path: Path, artifact_type: str, producer_step: str) -> dict[str, str]:
    return {
        'artifact_type': artifact_type,
        'producer_step': producer_step,
        'path': str(path.resolve()).replace('\\', '/'),
        'relative_path': str(path.resolve().relative_to(repo_root.resolve())).replace('\\', '/'),
        'sha256': _sha256_file(path),
    }


def _is_skipped_input_summary(source_payload: dict[str, Any]) -> bool:
    return str(source_payload.get('status') or '').lower() == 'skipped' and str(source_payload.get('reason') or '') == 'missing_task_triplet'


def orchestrate(
    *,
    repo_root: Path,
    delivery_profile: str,
    write_doc: bool,
    create_tasks: bool,
    tasks_json_path: Path,
    tasks_back_path: Path,
    tasks_gameplay_path: Path,
    overlay_root_path: Path,
    ui_gdd_flow_path: Path,
    alignment_audit_path: Path | None,
    wiring_audit_path: Path | None,
    chapter7_profile_path: Path | None,
    repo_label: str,
    back_story_id: str,
    gameplay_story_id: str,
) -> tuple[int, dict[str, Any]]:
    out_dir = repo_root / 'logs' / 'ci' / _today() / 'chapter7-ui-wiring'
    steps: list[dict[str, Any]] = []
    artifact_entries: list[dict[str, str]] = []
    ui_candidates_path = ui_gdd_flow_path.with_suffix('.candidates.json')
    resolved_alignment_audit_path = _optional_resolved_path(repo_root, alignment_audit_path)
    resolved_wiring_audit_path = _optional_resolved_path(repo_root, wiring_audit_path)
    profile = load_chapter7_profile(repo_root=repo_root, profile_path=chapter7_profile_path)
    commands = [
        (
            'collect',
            [
                'py',
                '-3',
                _script_path('collect_ui_wiring_inputs.py'),
                '--repo-root',
                str(repo_root),
                '--tasks-json-path',
                str(tasks_json_path),
                '--tasks-back-path',
                str(tasks_back_path),
                '--tasks-gameplay-path',
                str(tasks_gameplay_path),
                '--overlay-root-path',
                str(overlay_root_path),
            ],
        ),
    ]
    if write_doc:
        commands.append(
            (
                'write-doc',
                [
                    'py',
                    '-3',
                    _script_path('chapter7_ui_gdd_writer.py'),
                    '--repo-root',
                    str(repo_root),
                    '--ui-gdd-flow-path',
                    str(ui_gdd_flow_path),
                    '--tasks-json-path',
                    str(tasks_json_path),
                    '--tasks-back-path',
                    str(tasks_back_path),
                    '--tasks-gameplay-path',
                    str(tasks_gameplay_path),
                    '--overlay-root-path',
                    str(overlay_root_path),
                ],
            )
        )
        if chapter7_profile_path:
            commands[-1][1].extend(['--chapter7-profile-path', str(chapter7_profile_path)])
    commands.append(
        (
            'validate',
            [
                'py',
                '-3',
                _script_path('validate_chapter7_ui_wiring.py'),
                '--repo-root',
                str(repo_root),
                '--ui-gdd-flow-path',
                str(ui_gdd_flow_path),
                '--tasks-json-path',
                str(tasks_json_path),
                '--tasks-back-path',
                str(tasks_back_path),
                '--tasks-gameplay-path',
                str(tasks_gameplay_path),
                '--overlay-root-path',
                str(overlay_root_path),
            ],
        )
    )
    if chapter7_profile_path:
        commands[-1][1].extend(['--chapter7-profile-path', str(chapter7_profile_path)])
    if create_tasks:
        commands.append(
            (
                'create-tasks',
                [
                    'py',
                    '-3',
                    _script_path('create_chapter7_tasks_from_ui_candidates.py'),
                    '--repo-root',
                    str(repo_root),
                    '--tasks-json-path',
                    str(tasks_json_path),
                    '--tasks-back-path',
                    str(tasks_back_path),
                    '--tasks-gameplay-path',
                    str(tasks_gameplay_path),
                    '--ui-candidates-path',
                    str(ui_candidates_path),
                    '--overlay-root-path',
                    str(overlay_root_path),
                ],
            )
        )
        if chapter7_profile_path:
            commands[-1][1].extend(['--chapter7-profile-path', str(chapter7_profile_path)])
        if repo_label:
            commands[-1][1].extend(['--repo-label', repo_label])
        if back_story_id:
            commands[-1][1].extend(['--back-story-id', back_story_id])
        if gameplay_story_id:
            commands[-1][1].extend(['--gameplay-story-id', gameplay_story_id])
    overall_rc = 0
    for name, cmd in commands:
        rc, output = _run(cmd, cwd=repo_root)
        _write(out_dir / f'{name}.log', output)
        steps.append({'name': name, 'rc': rc, 'cmd': cmd, 'log': str((out_dir / f'{name}.log')).replace('\\', '/')})
        if rc != 0 and overall_rc == 0:
            overall_rc = rc
            break
    payload = {
        'ts': dt.datetime.now(dt.timezone.utc).isoformat(),
        'action': 'run-chapter7-ui-wiring',
        'status': 'ok' if overall_rc == 0 else 'fail',
        'delivery_profile': delivery_profile,
        'write_doc': write_doc,
        'create_tasks': create_tasks,
        'out_dir': str(out_dir).replace('\\', '/'),
        'steps': steps,
        'input_contract': {
            'repo_root': str(repo_root.resolve()).replace('\\', '/'),
            'tasks_json_path': _contract_path(repo_root, tasks_json_path),
            'tasks_back_path': _contract_path(repo_root, tasks_back_path),
            'tasks_gameplay_path': _contract_path(repo_root, tasks_gameplay_path),
            'overlay_root_path': _contract_path(repo_root, overlay_root_path),
            'ui_gdd_flow_path': _contract_path(repo_root, ui_gdd_flow_path),
            'ui_candidates_path': _contract_path(repo_root, ui_candidates_path),
            'alignment_audit_path': _contract_path(repo_root, alignment_audit_path),
            'wiring_audit_path': _contract_path(repo_root, wiring_audit_path),
            'chapter7_profile_path': profile.get('_loaded_profile_path') or '',
            'repo_label': repo_label,
            'back_story_id': back_story_id,
            'gameplay_story_id': gameplay_story_id,
        },
    }
    audit_references: list[dict[str, str]] = []
    if resolved_alignment_audit_path and resolved_alignment_audit_path.exists():
        payload['alignment_audit'] = str(resolved_alignment_audit_path.resolve()).replace('\\', '/')
        audit_references.append(
            {
                'kind': 'alignment-audit',
                'path': str(resolved_alignment_audit_path.resolve()).replace('\\', '/'),
                'relative_path': str(resolved_alignment_audit_path.resolve().relative_to(repo_root.resolve())).replace('\\', '/'),
            }
        )
        artifact_entries.append(
            _artifact_entry(
                repo_root=repo_root,
                path=resolved_alignment_audit_path,
                artifact_type='alignment-audit-reference',
                producer_step='reference',
            )
        )
    if resolved_wiring_audit_path and resolved_wiring_audit_path.exists():
        payload['wiring_audit'] = str(resolved_wiring_audit_path.resolve()).replace('\\', '/')
        audit_references.append(
            {
                'kind': 'wiring-audit',
                'path': str(resolved_wiring_audit_path.resolve()).replace('\\', '/'),
                'relative_path': str(resolved_wiring_audit_path.resolve().relative_to(repo_root.resolve())).replace('\\', '/'),
            }
        )
        artifact_entries.append(
            _artifact_entry(
                repo_root=repo_root,
                path=resolved_wiring_audit_path,
                artifact_type='wiring-audit-reference',
                producer_step='reference',
            )
        )
    if audit_references:
        payload['audit_references'] = audit_references
    if overall_rc == 0:
        input_source = repo_root / 'logs' / 'ci' / _today() / 'chapter7-ui-wiring-inputs' / 'summary.json'
        input_snapshot = out_dir / 'inputs.snapshot.json'
        if input_source.exists():
            source_payload = _load_json_if_exists(input_source)
            canonical_snapshot = _canonical_input_snapshot(source_payload)
            if audit_references:
                canonical_snapshot['audit_references'] = audit_references
            input_snapshot.write_text(json.dumps(canonical_snapshot, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\n')
            input_snapshot_str = str(input_snapshot.resolve()).replace('\\', '/')
            payload['input_snapshot'] = input_snapshot_str
            artifact_entries.append(
                _artifact_entry(repo_root=repo_root, path=input_snapshot, artifact_type='input-snapshot', producer_step='collect')
            )
            payload['input_snapshot_meta'] = {
                'completed_master_tasks_count': source_payload.get('completed_master_tasks_count'),
                'needed_wiring_features_count': source_payload.get('needed_wiring_features_count'),
                'feature_family_counts': source_payload.get('feature_family_counts', {}),
            }
            if _is_skipped_input_summary(source_payload):
                payload['status'] = 'skipped'
                payload['skip_reason'] = 'missing_task_triplet'
                payload['missing_source_files'] = list(source_payload.get('missing_source_files') or [])
            else:
                closure_summary_path = out_dir / 'closure-summary.json'
                closure_summary = _build_closure_summary(
                    repo_root=repo_root,
                    source_payload=source_payload,
                    ui_candidates_path=ui_candidates_path if ui_candidates_path.is_absolute() else (repo_root / ui_candidates_path),
                    wiring_audit_path=resolved_wiring_audit_path,
                    profile=profile,
                )
                closure_summary_path.write_text(
                    json.dumps(closure_summary, ensure_ascii=False, indent=2) + '\n',
                    encoding='utf-8',
                    newline='\n',
                )
                payload['closure_summary'] = str(closure_summary_path.resolve()).replace('\\', '/')
                payload['closure_summary_meta'] = {
                    'slice_count': closure_summary.get('slice_count', 0),
                    'epic_usable_count': closure_summary.get('epic_usable_count', 0),
                }
                artifact_entries.append(
                    _artifact_entry(
                        repo_root=repo_root,
                        path=closure_summary_path,
                        artifact_type='closure-summary',
                        producer_step='collect',
                    )
                )
                status_patch_preview_path = out_dir / 'task-status-patch-preview.json'
                status_patch_preview = _build_status_patch_preview(
                    repo_root=repo_root,
                    closure_summary=closure_summary,
                    tasks_json_path=tasks_json_path,
                    tasks_back_path=tasks_back_path,
                    tasks_gameplay_path=tasks_gameplay_path,
                )
                status_patch_preview_path.write_text(
                    json.dumps(status_patch_preview, ensure_ascii=False, indent=2) + '\n',
                    encoding='utf-8',
                    newline='\n',
                )
                payload['task_status_patch_preview'] = str(status_patch_preview_path.resolve()).replace('\\', '/')
                payload['task_status_patch_preview_meta'] = {
                    'mismatch_count': status_patch_preview.get('mismatch_count', 0),
                }
                artifact_entries.append(
                    _artifact_entry(
                        repo_root=repo_root,
                        path=status_patch_preview_path,
                        artifact_type='task-status-patch-preview',
                        producer_step='collect',
                    )
                )
                status_patch_preview_md_path = out_dir / 'task-status-patch-preview.md'
                status_patch_preview_md_path.write_text(
                    _render_status_patch_preview_markdown(status_patch_preview),
                    encoding='utf-8',
                    newline='\n',
                )
                payload['task_status_patch_preview_md'] = str(status_patch_preview_md_path.resolve()).replace('\\', '/')
                artifact_entries.append(
                    _artifact_entry(
                        repo_root=repo_root,
                        path=status_patch_preview_md_path,
                        artifact_type='task-status-patch-preview-md',
                        producer_step='collect',
                    )
                )
                status_patch_contract_path = out_dir / 'task-status-patch.json'
                status_patch_contract = _build_status_patch_contract(status_patch_preview)
                status_patch_contract_path.write_text(
                    json.dumps(status_patch_contract, ensure_ascii=False, indent=2) + '\n',
                    encoding='utf-8',
                    newline='\n',
                )
                payload['task_status_patch'] = str(status_patch_contract_path.resolve()).replace('\\', '/')
                payload['task_status_patch_meta'] = {
                    'operation_count': status_patch_contract.get('operation_count', 0),
                }
                artifact_entries.append(
                    _artifact_entry(
                        repo_root=repo_root,
                        path=status_patch_contract_path,
                        artifact_type='task-status-patch',
                        producer_step='collect',
                    )
                )
    if overall_rc == 0 and payload.get('status') == 'ok':
        candidate_sidecar_path = ui_candidates_path if ui_candidates_path.is_absolute() else (repo_root / ui_candidates_path)
        ui_gdd_path = ui_gdd_flow_path if ui_gdd_flow_path.is_absolute() else (repo_root / ui_gdd_flow_path)
        payload['ui_gdd'] = str(ui_gdd_path.resolve()).replace('\\', '/')
        payload['candidate_sidecar'] = str(candidate_sidecar_path.resolve()).replace('\\', '/')
        artifact_entries.extend(
            [
                _artifact_entry(repo_root=repo_root, path=ui_gdd_path, artifact_type='ui-gdd', producer_step='collect'),
                _artifact_entry(repo_root=repo_root, path=candidate_sidecar_path, artifact_type='candidate-sidecar', producer_step='collect'),
            ]
        )
    summary_path = out_dir / 'summary.json'
    manifest_path = out_dir / 'artifact-manifest.json'
    artifact_entries.append(
        {
            'artifact_type': 'summary',
            'producer_step': 'summary',
            'path': str(summary_path.resolve()).replace('\\', '/'),
            'relative_path': str(summary_path.resolve().relative_to(repo_root.resolve())).replace('\\', '/'),
            'sha256': 'non-idempotent-summary',
        }
    )
    payload['artifact_manifest'] = str(manifest_path.resolve()).replace('\\', '/')
    payload['_artifact_manifest_entries'] = artifact_entries
    return overall_rc, payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description='Top-level Chapter 7 UI wiring orchestrator.')
    parser.add_argument('--repo-root', default='.')
    parser.add_argument('--delivery-profile', default='fast-ship')
    parser.add_argument('--tasks-json-path', default='.taskmaster/tasks/tasks.json')
    parser.add_argument('--tasks-back-path', default='.taskmaster/tasks/tasks_back.json')
    parser.add_argument('--tasks-gameplay-path', default='.taskmaster/tasks/tasks_gameplay.json')
    parser.add_argument('--overlay-root-path', default='docs/architecture/overlays')
    parser.add_argument('--ui-gdd-flow-path', default='docs/gdd/ui-gdd-flow.md')
    parser.add_argument('--alignment-audit-path', default='')
    parser.add_argument('--wiring-audit-path', default='')
    parser.add_argument('--chapter7-profile-path', default='')
    parser.add_argument('--repo-label', default='')
    parser.add_argument('--back-story-id', default='')
    parser.add_argument('--gameplay-story-id', default='')
    parser.add_argument('--write-doc', action='store_true')
    parser.add_argument('--create-tasks', action='store_true')
    parser.add_argument('--out-json', default='')
    parser.add_argument('--self-check', action='store_true')
    args = parser.parse_args(argv)

    repo_root = Path(args.repo_root).resolve()
    if args.self_check:
        planned_steps = ['collect']
        if args.write_doc:
            planned_steps.append('write-doc')
        planned_steps.append('validate')
        if args.create_tasks:
            planned_steps.append('create-tasks')
        payload = {
            'ts': dt.datetime.now(dt.timezone.utc).isoformat(),
            'action': 'run-chapter7-ui-wiring',
            'status': 'ok',
            'delivery_profile': args.delivery_profile,
            'write_doc': bool(args.write_doc),
            'create_tasks': bool(args.create_tasks),
            'chapter7_profile_path': args.chapter7_profile_path,
            'repo_label': args.repo_label,
            'back_story_id': args.back_story_id,
            'gameplay_story_id': args.gameplay_story_id,
            'planned_steps': planned_steps,
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0

    effective_wiring_audit = Path(args.wiring_audit_path) if args.wiring_audit_path else None
    if effective_wiring_audit is not None and not (repo_root / effective_wiring_audit).exists() and not effective_wiring_audit.is_absolute():
        effective_wiring_audit = None

    rc, payload = orchestrate(
        repo_root=repo_root,
        delivery_profile=args.delivery_profile,
        write_doc=bool(args.write_doc),
        create_tasks=bool(args.create_tasks),
        tasks_json_path=Path(args.tasks_json_path),
        tasks_back_path=Path(args.tasks_back_path),
        tasks_gameplay_path=Path(args.tasks_gameplay_path),
        overlay_root_path=Path(args.overlay_root_path),
        ui_gdd_flow_path=Path(args.ui_gdd_flow_path),
        alignment_audit_path=Path(args.alignment_audit_path) if args.alignment_audit_path else None,
        wiring_audit_path=effective_wiring_audit,
        chapter7_profile_path=Path(args.chapter7_profile_path) if args.chapter7_profile_path else None,
        repo_label=args.repo_label,
        back_story_id=args.back_story_id,
        gameplay_story_id=args.gameplay_story_id,
    )
    out = Path(args.out_json) if args.out_json else (repo_root / 'logs' / 'ci' / _today() / 'chapter7-ui-wiring' / 'summary.json')
    out.parent.mkdir(parents=True, exist_ok=True)
    manifest_path = Path(payload['artifact_manifest'])
    artifact_entries = list(payload.pop('_artifact_manifest_entries', []))
    for item in artifact_entries:
        if item.get('artifact_type') == 'summary':
            summary_path = out.resolve()
            item['path'] = str(summary_path).replace('\\', '/')
            item['relative_path'] = str(summary_path.relative_to(repo_root.resolve())).replace('\\', '/')
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    manifest_payload = {
        'schema_version': 1,
        'run_profile': payload['delivery_profile'],
        'action': payload['action'],
        'status': payload['status'],
        'out_dir': payload['out_dir'],
        'artifacts': artifact_entries,
    }
    if payload.get('skip_reason'):
        manifest_payload['skip_reason'] = payload['skip_reason']
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest_payload, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\n')
    validation_out = manifest_path.with_name('artifact-manifest-validation.json')
    manifest_rc, manifest_output = _run(
        [
            'py',
            '-3',
            _script_path('validate_chapter7_artifact_manifest.py'),
            '--repo-root',
            str(repo_root),
            '--manifest',
            str(manifest_path),
            '--out',
            str(validation_out),
        ],
        cwd=repo_root,
    )
    manifest_log = manifest_path.with_name('artifact-manifest.log')
    _write(manifest_log, manifest_output)
    payload['steps'].append(
        {
            'name': 'artifact-manifest',
            'rc': manifest_rc,
            'cmd': [
                'py',
                '-3',
                _script_path('validate_chapter7_artifact_manifest.py'),
                '--repo-root',
                str(repo_root),
                '--manifest',
                str(manifest_path),
                '--out',
                str(validation_out),
            ],
            'log': str(manifest_log).replace('\\', '/'),
        }
    )
    payload['artifact_manifest_validation'] = str(validation_out.resolve()).replace('\\', '/')
    payload['status'] = 'ok' if rc == 0 and manifest_rc == 0 else 'fail'
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(f"CHAPTER7_UI_WIRING status={payload['status']} steps={len(payload['steps'])} out={str(out).replace('\\', '/')}")
    return rc if rc != 0 else manifest_rc


if __name__ == '__main__':
    raise SystemExit(main())
