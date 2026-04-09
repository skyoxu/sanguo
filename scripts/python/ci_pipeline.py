#!/usr/bin/env python3
"""
CI pipeline driver (Python): dotnet tests+coverage (soft gate), Godot self-check, encoding scan.

Usage (Windows):
  py -3 scripts/python/ci_pipeline.py all \
    --solution auto --configuration Debug \
    --godot-bin "C:\\Godot\\Godot_v4.5.1-stable_mono_win64_console.exe" \
    --build-solutions

Exit codes:
  0  success (or only soft gates failed)
  1  hard failure (dotnet tests failed or self-check failed)
"""
import argparse
import datetime as dt
import io
import json
import os
import re
import subprocess
import sys

from solution_target import resolve_test_solution_arg


def run_cmd(args, cwd=None, timeout=900_000):
    p = subprocess.Popen(args, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                         text=True, encoding='utf-8', errors='ignore')
    try:
        out, _ = p.communicate(timeout=timeout/1000.0)
    except subprocess.TimeoutExpired:
        p.kill()
        out, _ = p.communicate()
        return 124, out
    return p.returncode, out


def read_json(path):
    try:
        with io.open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return None


def copy_if_exists(src_path: str, dst_path: str) -> bool:
    if not src_path or not os.path.exists(src_path):
        return False
    try:
        with io.open(src_path, 'r', encoding='utf-8', errors='ignore') as rf:
            content = rf.read()
        with io.open(dst_path, 'w', encoding='utf-8') as wf:
            wf.write(content)
        return True
    except Exception:
        return False


def extract_failed_tests(dotnet_test_output: str):
    """
    Parse failed test names from dotnet test console output.
    Compatible with common VSTest/xUnit output lines, for example:
      Failed Namespace.Class.TestName [123 ms]
      [FAIL] Namespace.Class.TestName
    """
    if not dotnet_test_output:
        return []

    failed = []
    for raw in dotnet_test_output.splitlines():
        line = raw.strip()
        if not line:
            continue

        # Pattern: "Failed Namespace.Class.Test [123 ms]"
        m = re.match(r'^Failed\s+(.+?)\s+\[[0-9]+(?:\.[0-9]+)?\s*ms\]$', line)
        if m:
            failed.append(m.group(1).strip())
            continue

        # Pattern: "[FAIL] Namespace.Class.Test"
        m = re.match(r'^\[FAIL\]\s+(.+)$', line)
        if m:
            failed.append(m.group(1).strip())
            continue

        # Pattern: "X Namespace.Class.Test [123ms]"
        m = re.match(r'^[xX]\s+(.+?)\s+\[[0-9]+(?:\.[0-9]+)?\s*ms\]$', line)
        if m:
            failed.append(m.group(1).strip())

    # Stable de-duplication, keep first occurrence.
    seen = set()
    deduped = []
    for item in failed:
        if item in seen:
            continue
        seen.add(item)
        deduped.append(item)
    return deduped


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest='cmd', required=True)
    ap_all = sub.add_parser('all')
    ap_all.add_argument('--solution', default='')
    ap_all.add_argument('--configuration', default='Debug')
    ap_all.add_argument('--godot-bin', required=True)
    ap_all.add_argument('--project', default='project.godot')
    ap_all.add_argument('--build-solutions', action='store_true')

    args = ap.parse_args()
    if args.cmd != 'all':
        print('Unsupported command')
        return 1

    root = os.getcwd()
    resolved_solution = resolve_test_solution_arg(args.solution)
    date = dt.date.today().strftime('%Y-%m-%d')
    ci_dir = os.path.join('logs', 'ci', date)
    os.makedirs(ci_dir, exist_ok=True)

    summary = {
        'solution': resolved_solution,
        'solution_input': args.solution,
        'manual_triplet_examples': {},
        'whitelist_expiry_warning': {},
        'dotnet': {},
        'selfcheck': {},
        'encoding': {},
        'status': 'ok'
    }
    hard_fail = False

    # 0) Enforce unified task-level entrypoint command policy (hard gate)
    rc0, out0 = run_cmd([
        'py', '-3', 'scripts/python/forbid_manual_sc_triplet_examples.py',
        '--root', '.',
        '--mode', 'all',
        '--whitelist', 'docs/workflows/unified-pipeline-command-whitelist.txt',
        '--whitelist-metadata', 'require',
    ], cwd=root)
    with io.open(os.path.join(ci_dir, 'forbid-manual-sc-triplet-examples.log'), 'w', encoding='utf-8') as f:
        f.write(out0)
    manual_sum = read_json(os.path.join('logs', 'ci', date, 'forbid-manual-sc-triplet-examples.json')) or {}
    summary['manual_triplet_examples'] = {
        'rc': rc0,
        'status': 'ok' if rc0 == 0 else 'fail',
        'hits_count': manual_sum.get('hits_count'),
        'scanned_files': manual_sum.get('scanned_files'),
        'mode': manual_sum.get('mode'),
    }
    if rc0 != 0:
        hard_fail = True

    # 0.5) Soft warning: whitelist expiry horizon.
    rcw, outw = run_cmd([
        'py', '-3', 'scripts/python/warn_whitelist_expiry.py',
        '--root', '.',
        '--whitelist', 'docs/workflows/unified-pipeline-command-whitelist.txt',
    ], cwd=root)
    with io.open(os.path.join(ci_dir, 'whitelist-expiry-warning.log'), 'w', encoding='utf-8') as f:
        f.write(outw)
    warn_sum = read_json(os.path.join('logs', 'ci', date, 'whitelist-expiry-warning.json')) or {}
    summary['whitelist_expiry_warning'] = {
        'rc': rcw,
        'status': warn_sum.get('status') or ('ok' if rcw == 0 else 'warn'),
        'expiring_soon_count': warn_sum.get('expiring_soon_count'),
        'expired_count': warn_sum.get('expired_count'),
        'warn_days': warn_sum.get('warn_days'),
    }

    # 1) Dotnet tests + coverage (soft gate on coverage)
    rc, out = run_cmd(['py', '-3', 'scripts/python/run_dotnet.py',
                       '--solution', resolved_solution,
                       '--configuration', args.configuration], cwd=root)
    with io.open(os.path.join(ci_dir, 'run-dotnet-console.txt'), 'w', encoding='utf-8') as f:
        f.write(out)
    dotnet_sum = read_json(os.path.join('logs', 'unit', date, 'summary.json')) or {}
    dotnet_out_dir = dotnet_sum.get('out_dir') if isinstance(dotnet_sum, dict) else None
    dotnet_test_output_src = os.path.join(dotnet_out_dir, 'dotnet-test-output.txt') if dotnet_out_dir else ''
    dotnet_test_output_ci = os.path.join(ci_dir, 'dotnet-test-output.txt')
    copied_test_output = copy_if_exists(dotnet_test_output_src, dotnet_test_output_ci)
    dotnet_test_output_text = ''
    if copied_test_output:
        try:
            with io.open(dotnet_test_output_ci, 'r', encoding='utf-8', errors='ignore') as f:
                dotnet_test_output_text = f.read()
        except Exception:
            dotnet_test_output_text = ''
    failed_tests = extract_failed_tests(dotnet_test_output_text)
    summary['dotnet'] = {
        'rc': rc,
        'line_pct': (dotnet_sum.get('coverage') or {}).get('line_pct'),
        'branch_pct': (dotnet_sum.get('coverage') or {}).get('branch_pct'),
        'status': dotnet_sum.get('status'),
        'run_dotnet_console_log': os.path.join(ci_dir, 'run-dotnet-console.txt'),
        'dotnet_test_output_log': dotnet_test_output_ci if copied_test_output else None,
        'failed_tests_count': len(failed_tests),
        'failed_tests': failed_tests[:50],
    }
    if rc not in (0, 2) or summary['dotnet']['status'] == 'tests_failed':
        hard_fail = True

    # 2) Godot self-check (hard gate)
    # ensure autoload fixed (explicit project path)
    _ = run_cmd(['py', '-3', 'scripts/python/godot_selfcheck.py', 'fix-autoload', '--project', args.project], cwd=root)
    sc_args = ['py', '-3', 'scripts/python/godot_selfcheck.py', 'run', '--godot-bin', args.godot_bin, '--project', args.project]
    if args.build_solutions:
        sc_args.append('--build-solutions')
    rc2, out2 = run_cmd(sc_args, cwd=root, timeout=600_000)
    # persist raw stdout for diagnosis
    os.makedirs(os.path.join('logs', 'ci', date), exist_ok=True)
    with io.open(os.path.join('logs', 'ci', date, 'selfcheck-stdout.txt'), 'w', encoding='utf-8') as f:
        f.write(out2)
    sc_sum = read_json(os.path.join('logs', 'e2e', date, 'selfcheck-summary.json')) or {}
    # fallback: parse status from stdout if summary missing
    if not sc_sum:
        import re
        m = re.search(r"SELF_CHECK status=([a-z]+).*? out=([^\r\n]+)", out2)
        if m:
            sc_status = m.group(1)
            sc_out = m.group(2)
            sc_sum = {'status': sc_status, 'out': sc_out, 'note': 'parsed-from-stdout'}
    # as ultimate fallback, trust process rc (0==ok)
    # Copy Godot selfcheck raw console/stderr into ci logs if present
    try:
        e2e_dir = os.path.join('logs', 'e2e', date)
        ci_dir = os.path.join('logs', 'ci', date)
        cons = [p for p in os.listdir(e2e_dir) if p.startswith('godot-selfcheck-console-')]
        if cons:
            cons.sort()
            src = os.path.join(e2e_dir, cons[-1])
            with io.open(src, 'r', encoding='utf-8', errors='ignore') as rf, io.open(os.path.join(ci_dir, 'selfcheck-console.txt'), 'w', encoding='utf-8') as wf:
                wf.write(rf.read())
        errs = [p for p in os.listdir(e2e_dir) if p.startswith('godot-selfcheck-stderr-')]
        if errs:
            errs.sort()
            src = os.path.join(e2e_dir, errs[-1])
            with io.open(src, 'r', encoding='utf-8', errors='ignore') as rf, io.open(os.path.join(ci_dir, 'selfcheck-stderr.txt'), 'w', encoding='utf-8') as wf:
                wf.write(rf.read())
    except Exception:
        pass

    sc_ok = (sc_sum.get('status') == 'ok') or (rc2 == 0)
    summary['selfcheck'] = sc_sum or {'status': 'fail', 'note': 'no-summary'}
    if not sc_ok:
        hard_fail = True

    # 3) Encoding scan (soft gate)
    rc3, out3 = run_cmd(['py', '-3', 'scripts/python/check_encoding.py', '--since-today'], cwd=root)
    enc_sum = read_json(os.path.join('logs', 'ci', date, 'encoding', 'session-summary.json')) or {}
    summary['encoding'] = enc_sum

    summary['status'] = 'ok' if not hard_fail else 'fail'
    with io.open(os.path.join(ci_dir, 'ci-pipeline-summary.json'), 'w', encoding='utf-8') as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    print(
        f"CI_PIPELINE status={summary['status']} manual_examples={summary['manual_triplet_examples'].get('status')} "
        f"whitelist_expiry={summary['whitelist_expiry_warning'].get('status')} "
        f"dotnet={summary['dotnet'].get('status')} selfcheck={summary['selfcheck'].get('status')} "
        f"encoding_bad={summary['encoding'].get('bad', 'n/a')}"
    )
    return 0 if not hard_fail else 1


if __name__ == '__main__':
    sys.exit(main())
