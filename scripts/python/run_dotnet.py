#!/usr/bin/env python3
"""
Run dotnet restore/test with coverage and archive artifacts under logs/unit/<date>/.
Exits non-zero on test failure or when coverage thresholds (if provided) are not met.

Env thresholds (optional):
  COVERAGE_LINES_MIN   e.g., "90" (percent)
  COVERAGE_BRANCHES_MIN e.g., "85" (percent)

Usage (Windows):
  py -3 scripts/python/run_dotnet.py --solution auto --configuration Debug
"""
import argparse
import datetime as dt
import io
import json
import os
import re
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

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


def ensure_dir(path):
    os.makedirs(path, exist_ok=True)


def parse_cobertura(path):
    try:
        tree = ET.parse(path)
        root = tree.getroot()
        # Cobertura schema with attributes lines-covered/lines-valid etc.
        lc = int(root.attrib.get('lines-covered', '0'))
        lv = int(root.attrib.get('lines-valid', '0'))
        bc = int(root.attrib.get('branches-covered', '0'))
        bv = int(root.attrib.get('branches-valid', '0'))
        line_pct = round((lc*100.0)/lv, 2) if lv > 0 else 0.0
        branch_pct = round((bc*100.0)/bv, 2) if bv > 0 else 0.0
        return {
            'lines_covered': lc,
            'lines_valid': lv,
            'branches_covered': bc,
            'branches_valid': bv,
            'line_pct': line_pct,
            'branch_pct': branch_pct,
        }
    except Exception as e:
        return {'error': str(e)}


def parse_paths_from_test_output(output: str):
    """
    Extract artifact paths from `dotnet test` output.

    This avoids accidentally copying stale artifacts from logs/ or previous TestResults runs.
    """
    # Note: output contains Windows paths with single backslashes.
    trx_paths = re.findall(r'([A-Za-z]:\\[^\r\n]*?\.trx)', output)
    cov_paths = re.findall(r'([A-Za-z]:\\[^\r\n]*?coverage\.cobertura\.xml)', output)
    return {
        'trx_paths': list(dict.fromkeys(trx_paths)),
        'coverage_paths': list(dict.fromkeys(cov_paths)),
    }


def pick_latest_existing(paths):
    existing = [p for p in paths if p and os.path.exists(p)]
    if not existing:
        return None
    return max(existing, key=lambda p: os.path.getmtime(p))


def _parse_solution_project_paths(solution_path):
    try:
        text = Path(solution_path).read_text(encoding='utf-8-sig', errors='ignore')
    except OSError:
        return []
    paths = []
    for line in text.splitlines():
        line = line.strip()
        if not line.startswith('Project('):
            continue
        parts = [part.strip().strip('"') for part in line.split('=', 1)[-1].split(',')]
        if len(parts) < 2:
            continue
        candidate = parts[1].replace('\\\\', '\\')
        if candidate.lower().endswith('.csproj'):
            paths.append(candidate)
    return paths


def _looks_like_test_project(project_path):
    normalized = str(project_path or '').replace('\\', '/').lower()
    if 'test' in normalized:
        return True
    try:
        text = Path(project_path).read_text(encoding='utf-8', errors='ignore').lower()
    except OSError:
        return False
    return '<istestproject>true</istestproject>' in text


def resolve_dotnet_test_target(resolved_solution, *, root):
    target = Path(resolved_solution)
    if target.suffix.lower() != '.sln':
        return resolved_solution
    solution_path = target if target.is_absolute() else Path(root) / target
    projects = _parse_solution_project_paths(solution_path)
    for project in projects:
        project_path = Path(project)
        disk_path = project_path if project_path.is_absolute() else Path(root) / project_path
        if _looks_like_test_project(disk_path):
            return str(project_path)
    return resolved_solution


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--solution', default='')
    ap.add_argument('--configuration', default='Debug')
    ap.add_argument('--filter', default=None, help='Optional dotnet test filter expression.')
    ap.add_argument('--out-dir', default=None)
    args = ap.parse_args()

    root = os.getcwd()
    resolved_solution = resolve_test_solution_arg(args.solution, root=Path(root))
    test_target = resolve_dotnet_test_target(resolved_solution, root=root)
    date = dt.date.today().strftime('%Y-%m-%d')
    out_dir = args.out_dir or os.path.join(root, 'logs', 'unit', date)
    ensure_dir(out_dir)

    summary = {
        'solution': resolved_solution,
        'solution_input': args.solution,
        'test_target': test_target,
        'configuration': args.configuration,
        'filter': args.filter or '',
        'out_dir': out_dir,
        'status': 'fail',
    }

    # Restore
    rc, out = run_cmd(
        ['dotnet', 'restore', resolved_solution, '--property:RestoreBuildInParallel=false'],
        cwd=root,
    )
    with io.open(os.path.join(out_dir, 'dotnet-restore.log'), 'w', encoding='utf-8') as f:
        f.write(out)
    summary['restore_rc'] = rc
    if rc != 0:
        with io.open(os.path.join(out_dir, 'summary.json'), 'w', encoding='utf-8') as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)
        print(f'RUN_DOTNET status=fail stage=restore out={out_dir}')
        return 1

    # Test with coverage
    test_cmd = ['dotnet', 'test', test_target,
                f'-c', args.configuration,
                '--no-restore',
                '--collect:XPlat Code Coverage',
                '--logger', 'trx;LogFileName=tests.trx']
    if args.filter:
        test_cmd.extend(['--filter', args.filter])
    rc, out = run_cmd(test_cmd, cwd=root)
    with io.open(os.path.join(out_dir, 'dotnet-test-output.txt'), 'w', encoding='utf-8') as f:
        f.write(out)
    summary['test_rc'] = rc

    # Copy artifacts using paths emitted by dotnet test output (preferred).
    artifacts = parse_paths_from_test_output(out)
    summary['artifacts_detected'] = artifacts

    trx_src = pick_latest_existing(artifacts.get('trx_paths') or [])
    cov_src = pick_latest_existing(artifacts.get('coverage_paths') or [])

    # Fallback: search inside Game.Core.Tests/TestResults only (avoid logs/**).
    test_target_path = Path(test_target)
    if test_target_path.suffix.lower() == '.csproj':
        test_results_root = str((test_target_path if test_target_path.is_absolute() else Path(root) / test_target_path).parent / 'TestResults')
    else:
        test_results_root = os.path.join(root, 'Game.Core.Tests', 'TestResults')

    if not trx_src:
        fallback_trx_root = test_results_root
        if os.path.isdir(fallback_trx_root):
            candidates = []
            for cur_root, _, files in os.walk(fallback_trx_root):
                for name in files:
                    if name.lower().endswith('.trx'):
                        candidates.append(os.path.join(cur_root, name))
            trx_src = pick_latest_existing(candidates)

    if not cov_src:
        fallback_cov_root = test_results_root
        if os.path.isdir(fallback_cov_root):
            candidates = []
            for cur_root, _, files in os.walk(fallback_cov_root):
                for name in files:
                    if name == 'coverage.cobertura.xml':
                        candidates.append(os.path.join(cur_root, name))
            cov_src = pick_latest_existing(candidates)

    summary['artifacts_selected'] = {'trx': trx_src, 'coverage': cov_src}

    if trx_src:
        try:
            shutil.copyfile(trx_src, os.path.join(out_dir, 'tests.trx'))
        except Exception:
            pass

    if cov_src:
        try:
            shutil.copyfile(cov_src, os.path.join(out_dir, 'coverage.cobertura.xml'))
        except Exception:
            pass

    coverage = None
    cov_path = os.path.join(out_dir, 'coverage.cobertura.xml')
    if os.path.exists(cov_path):
        coverage = parse_cobertura(cov_path)
        summary['coverage'] = coverage

    # Thresholds (optional)
    lines_min = os.environ.get('COVERAGE_LINES_MIN')
    branches_min = os.environ.get('COVERAGE_BRANCHES_MIN')
    threshold_ok = True
    if coverage and (lines_min or branches_min):
        try:
            if lines_min:
                threshold_ok = threshold_ok and (coverage.get('line_pct', 0) >= float(lines_min))
            if branches_min:
                threshold_ok = threshold_ok and (coverage.get('branch_pct', 0) >= float(branches_min))
        except Exception:
            pass
    summary['threshold_ok'] = threshold_ok

    summary['status'] = 'ok' if (rc == 0 and threshold_ok) else ('tests_failed' if rc != 0 else 'coverage_failed')
    with io.open(os.path.join(out_dir, 'summary.json'), 'w', encoding='utf-8') as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    print(f"RUN_DOTNET status={summary['status']} line={coverage.get('line_pct', 'n/a') if coverage else 'n/a'}% branch={coverage.get('branch_pct','n/a') if coverage else 'n/a'} out={out_dir}")
    if summary['status'] == 'ok':
        return 0
    return 2 if summary['status'] == 'coverage_failed' else 1


if __name__ == '__main__':
    sys.exit(main())
