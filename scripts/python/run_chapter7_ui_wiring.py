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


def _artifact_entry(*, repo_root: Path, path: Path, artifact_type: str, producer_step: str) -> dict[str, str]:
    return {
        'artifact_type': artifact_type,
        'producer_step': producer_step,
        'path': str(path.resolve()).replace('\\', '/'),
        'relative_path': str(path.resolve().relative_to(repo_root.resolve())).replace('\\', '/'),
        'sha256': _sha256_file(path),
    }


def orchestrate(*, repo_root: Path, delivery_profile: str, write_doc: bool) -> tuple[int, dict[str, Any]]:
    out_dir = repo_root / 'logs' / 'ci' / _today() / 'chapter7-ui-wiring'
    steps: list[dict[str, Any]] = []
    artifact_entries: list[dict[str, str]] = []
    commands = [
        ('collect', ['py', '-3', _script_path('collect_ui_wiring_inputs.py'), '--repo-root', str(repo_root)]),
    ]
    if write_doc:
        commands.append(('write-doc', ['py', '-3', _script_path('chapter7_ui_gdd_writer.py'), '--repo-root', str(repo_root)]))
    commands.append(('validate', ['py', '-3', _script_path('validate_chapter7_ui_wiring.py'), '--repo-root', str(repo_root)]))
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
        'out_dir': str(out_dir).replace('\\', '/'),
        'steps': steps,
    }
    if overall_rc == 0:
        input_source = repo_root / 'logs' / 'ci' / _today() / 'chapter7-ui-wiring-inputs' / 'summary.json'
        input_snapshot = out_dir / 'inputs.snapshot.json'
        if input_source.exists():
            source_payload = _load_json_if_exists(input_source)
            canonical_snapshot = _canonical_input_snapshot(source_payload)
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
    if write_doc and overall_rc == 0:
        candidate_sidecar_path = repo_root / 'docs' / 'gdd' / 'ui-gdd-flow.candidates.json'
        ui_gdd_path = repo_root / 'docs' / 'gdd' / 'ui-gdd-flow.md'
        candidate_sidecar = str(candidate_sidecar_path.resolve()).replace('\\', '/')
        ui_gdd = str(ui_gdd_path.resolve()).replace('\\', '/')
        payload['candidate_sidecar'] = candidate_sidecar
        artifact_entries.extend(
            [
                _artifact_entry(repo_root=repo_root, path=ui_gdd_path, artifact_type='ui-gdd', producer_step='write-doc'),
                _artifact_entry(repo_root=repo_root, path=candidate_sidecar_path, artifact_type='candidate-sidecar', producer_step='write-doc'),
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
    parser.add_argument('--write-doc', action='store_true')
    parser.add_argument('--out-json', default='')
    parser.add_argument('--self-check', action='store_true')
    args = parser.parse_args(argv)

    repo_root = Path(args.repo_root).resolve()
    if args.self_check:
        planned_steps = ['collect']
        if args.write_doc:
            planned_steps.append('write-doc')
        planned_steps.append('validate')
        payload = {
            'ts': dt.datetime.now(dt.timezone.utc).isoformat(),
            'action': 'run-chapter7-ui-wiring',
            'status': 'ok',
            'delivery_profile': args.delivery_profile,
            'write_doc': bool(args.write_doc),
            'planned_steps': planned_steps,
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0

    rc, payload = orchestrate(repo_root=repo_root, delivery_profile=args.delivery_profile, write_doc=bool(args.write_doc))
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
