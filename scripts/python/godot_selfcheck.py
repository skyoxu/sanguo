#!/usr/bin/env python3
"""
Godot self-check utilities (Python, Windows friendly).

Subcommands:
  - fix-autoload: ensure CompositionRoot autoload uses script singleton (*)
  - run: invoke headless self-check GDScript and archive result under logs/e2e/<date>/

Usage examples (Windows / py launcher):
  py -3 scripts/python/godot_selfcheck.py fix-autoload --project project.godot
  py -3 scripts/python/godot_selfcheck.py run --godot-bin "C:\\Godot\\Godot_v4.5.1-stable_mono_win64_console.exe" --build-solutions
"""

import argparse
import datetime as dt
import io
import json
import os
import re
import shutil
import sys
import subprocess

AUT_LOAD_NAME = 'CompositionRoot'
AUT_LOAD_VALUE = '"*res://Game.Godot/Autoloads/CompositionRoot.cs"'


def read_text(path: str) -> str:
    with io.open(path, 'r', encoding='utf-8', errors='ignore') as f:
        return f.read()


def write_text(path: str, content: str) -> None:
    with io.open(path, 'w', encoding='utf-8') as f:
        f.write(content)


def ensure_autoload(project_path: str) -> bool:
    text = read_text(project_path)
    changed = False
    if '[autoload]' not in text:
        # append new section
        text = text.rstrip() + '\n\n[autoload]\n' + f'{AUT_LOAD_NAME}={AUT_LOAD_VALUE}\n'
        changed = True
    else:
        # replace or insert within [autoload]
        pattern = re.compile(r'(\[autoload\][\s\S]*?)(\n\[|\Z)', re.M)
        m = pattern.search(text)
        if not m:
            # defensive: append section again
            text = text.rstrip() + '\n\n[autoload]\n' + f'{AUT_LOAD_NAME}={AUT_LOAD_VALUE}\n'
            changed = True
        else:
            section = m.group(1)
            if re.search(rf'^{AUT_LOAD_NAME}=.*$', section, re.M):
                # replace line with star-prefixed singleton value
                new_section = re.sub(rf'^{AUT_LOAD_NAME}=.*$', f'{AUT_LOAD_NAME}={AUT_LOAD_VALUE}', section, flags=re.M)
            else:
                # add missing line at end of section
                new_section = section.rstrip() + '\n' + f'{AUT_LOAD_NAME}={AUT_LOAD_VALUE}' + '\n'
            if new_section != section:
                text = text[:m.start(1)] + new_section + text[m.end(1):]
                changed = True
    if changed:
        write_text(project_path, text)
    return changed


def run_cmd(args: list[str], cwd: str | None = None, timeout: int = 120000) -> tuple[int, str, str]:
    """Run a command and capture stdout/stderr separately (UTF-8 text)."""
    p = subprocess.Popen(
        args,
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding='utf-8',
        errors='ignore',
    )
    try:
        out, err = p.communicate(timeout=timeout / 1000.0)
    except subprocess.TimeoutExpired:
        p.kill()
        out, err = p.communicate()
        return 124, out, err
    return p.returncode, out, err


def run_selfcheck(godot_bin: str, project_godot: str, build_solutions: bool) -> dict:
    root = os.path.dirname(os.path.abspath(project_godot))
    date = dt.date.today().strftime('%Y-%m-%d')
    out_dir = os.path.join(root, 'logs', 'e2e', date)
    os.makedirs(out_dir, exist_ok=True)

    summary = {
        'godot': godot_bin,
        'project': project_godot,
        'out_dir': out_dir,
        'status': 'fail',
    }

    ts = dt.datetime.now().strftime('%H%M%S%f')
    if build_solutions:
        # Be explicit with --path to avoid project resolution flakiness on CI
        rc, out, err = run_cmd([godot_bin, '--headless', '--no-window', '--path', root, '--build-solutions', '--quit'], cwd=root, timeout=600000)
        with open(os.path.join(out_dir, f'godot-buildsolutions-{ts}.txt'), 'w', encoding='utf-8') as f:
            f.write(out or '')
            if err:
                f.write("\n--- STDERR ---\n")
                f.write(err)
        summary['build_rc'] = rc

    # Run the selfcheck script with explicit --path and verbose output
    args = [godot_bin, '--headless', '--no-window', '--path', root, '-s', 'res://Game.Godot/Scripts/Diagnostics/CompositionRootSelfCheck.gd', '--verbose']
    console_path = os.path.join(out_dir, f'godot-selfcheck-console-{ts}.txt')
    stderr_path = os.path.join(out_dir, f'godot-selfcheck-stderr-{ts}.txt')
    # Write call header for traceability
    with open(console_path, 'w', encoding='utf-8') as f:
        f.write('SELF_CHECK_CALL: ' + ' '.join(args) + '\n')
    rc, out, err = run_cmd(args, cwd=root, timeout=300000)
    with open(console_path, 'a', encoding='utf-8') as f:
        f.write(out or '')
    with open(stderr_path, 'w', encoding='utf-8') as f:
        f.write(err or '')
    summary['selfcheck_rc'] = rc
    m = re.search(r'SELF_CHECK_OUT:(.*)$', out or '', flags=re.M)
    if not m:
        # Retry once after a lightweight prewarm
        _rcpw, _outpw, _errpw = run_cmd([godot_bin, '--headless', '--no-window', '--path', root, '--quit'], cwd=root, timeout=120000)
        rc2, out2, err2 = run_cmd(args, cwd=root, timeout=300000)
        with open(console_path, 'a', encoding='utf-8') as f:
            f.write('\n--- RETRY ---\n')
            f.write(out2 or '')
        with open(stderr_path, 'a', encoding='utf-8') as f:
            f.write('\n--- RETRY ---\n')
            f.write(err2 or '')
        summary['selfcheck_rc'] = rc2
        out = out2
        m = re.search(r'SELF_CHECK_OUT:(.*)$', out or '', flags=re.M)
        if not m:
            summary['reason'] = 'SELF_CHECK_OUT not found in console output'
            return summary
    user_json = m.group(1).strip()
    if not os.path.exists(user_json):
        summary['reason'] = f'output not found at {user_json}'
        return summary

    dest = os.path.join(out_dir, 'composition_root_selfcheck.json')
    if os.path.normcase(os.path.abspath(user_json)) != os.path.normcase(os.path.abspath(dest)):
        shutil.copyfile(user_json, dest)
    summary['json'] = dest

    try:
        with open(dest, 'r', encoding='utf-8') as f:
            data = json.load(f)
        ports = data.get('ports', {})
        ok_count = sum(1 for k, v in ports.items() if v is True)
        summary['ports_ok'] = ok_count
        summary['ports_total'] = len(ports)
        summary['status'] = 'ok'
    except Exception as e:
        summary['reason'] = f'parse json failed: {e}'
    return summary


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest='cmd', required=True)
    ap_fix = sub.add_parser('fix-autoload')
    ap_fix.add_argument('--project', default='project.godot')

    ap_run = sub.add_parser('run')
    ap_run.add_argument('--godot-bin', required=True)
    ap_run.add_argument('--project', default='project.godot')
    ap_run.add_argument('--build-solutions', action='store_true')

    args = ap.parse_args()

    if args.cmd == 'fix-autoload':
        changed = ensure_autoload(args.project)
        print(f'AUTOLOAD_CHANGED={changed}')
        return 0
    if args.cmd == 'run':
        summary = run_selfcheck(args.godot_bin, args.project, args.build_solutions)
        out_dir = summary.get('out_dir', '.')
        # write summary next to logs for traceability
        with open(os.path.join(out_dir, 'selfcheck-summary.json'), 'w', encoding='utf-8') as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)
        status = summary.get('status')
        ok = status == 'ok'
        print(f"SELF_CHECK status={status} ports={summary.get('ports_ok','?')}/{summary.get('ports_total','?')} out={out_dir}")
        return 0 if ok else 2

    return 0


if __name__ == '__main__':
    sys.exit(main())
