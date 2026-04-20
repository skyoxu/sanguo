#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import datetime as dt
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


def orchestrate(*, repo_root: Path, delivery_profile: str, write_doc: bool) -> tuple[int, dict[str, Any]]:
    out_dir = repo_root / 'logs' / 'ci' / _today() / 'chapter7-ui-wiring'
    steps: list[dict[str, Any]] = []
    commands = [
        ('collect', ['py', '-3', 'scripts/python/collect_ui_wiring_inputs.py', '--repo-root', str(repo_root)]),
        ('validate', ['py', '-3', 'scripts/python/validate_chapter7_ui_wiring.py', '--repo-root', str(repo_root)]),
    ]
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
        payload = {
            'ts': dt.datetime.now(dt.timezone.utc).isoformat(),
            'action': 'run-chapter7-ui-wiring',
            'status': 'ok',
            'delivery_profile': args.delivery_profile,
            'write_doc': bool(args.write_doc),
            'planned_steps': ['collect', 'validate'],
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0

    rc, payload = orchestrate(repo_root=repo_root, delivery_profile=args.delivery_profile, write_doc=bool(args.write_doc))
    out = Path(args.out_json) if args.out_json else (repo_root / 'logs' / 'ci' / _today() / 'chapter7-ui-wiring' / 'summary.json')
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(f"CHAPTER7_UI_WIRING status={payload['status']} steps={len(payload['steps'])} out={str(out).replace('\\', '/')}")
    return rc


if __name__ == '__main__':
    raise SystemExit(main())
