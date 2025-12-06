#!/usr/bin/env python3
"""
Run GdUnit4 tests headless and archive reports to logs/e2e/<date>/.

Usage:
  py -3 scripts/python/run_gdunit.py \
    --godot-bin "C:\\Godot\\Godot_v4.5.1-stable_mono_win64_console.exe" \
    --project Tests.Godot \
    --add tests/Adapters --add tests/OtherSuite \
    --timeout-sec 300
"""
import argparse
import datetime as dt
import os
import shutil
import subprocess
import json
import time


def run_cmd(args, cwd=None, timeout=600_000):
    p = subprocess.Popen(args, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                         text=True, encoding='utf-8', errors='ignore')
    try:
        out, _ = p.communicate(timeout=timeout/1000.0)
    except subprocess.TimeoutExpired:
        p.kill()
        out, _ = p.communicate()
        return 124, out
    return p.returncode, out


def run_cmd_failfast(args, cwd=None, timeout=600_000, break_markers=None):
    """Run a process and stream stdout; if any line contains a break marker, kill early and return rc=1.
    This avoids long timeouts when Godot enters Debugger Break state.
    """
    break_markers = break_markers or [
        'Debugger Break',
        'Parser Error',
        'SCRIPT ERROR',
    ]
    p = subprocess.Popen(args, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                         text=True, encoding='utf-8', errors='ignore')
    buf_lines = []
    hit_break = False
    try:
        # Poll line-by-line up to timeout
        end_ts = dt.datetime.now().timestamp() + (timeout/1000.0)
        while True:
            line = p.stdout.readline()
            if line:
                buf_lines.append(line)
                low = line.lower()
                if any(m.lower() in low for m in break_markers):
                    hit_break = True
                    p.kill()
                    break
            else:
                if p.poll() is not None:
                    break
            if dt.datetime.now().timestamp() > end_ts:
                p.kill()
                return 124, ''.join(buf_lines)
        out = ''.join(buf_lines)
        if hit_break:
            return 1, out
        return (p.returncode or 0), out
    except Exception:
        try:
            p.kill()
        except Exception:
            pass
        return 1, ''.join(buf_lines)


def write_text(path: str, content: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--godot-bin', required=True)
    ap.add_argument('--project', default='Tests.Godot')
    ap.add_argument('--add', action='append', default=[], help='Add directory or suite path(s). E.g., tests/Adapters or res://tests/Adapters')
    ap.add_argument('--timeout-sec', type=int, default=600, help='Timeout seconds for test run (default 600)')
    ap.add_argument('--prewarm', action='store_true', help='Prewarm: build solutions before running tests')
    ap.add_argument('--rd', dest='report_dir', default=None, help='Custom destination to copy reports into (defaults to logs/e2e/<date>/gdunit-reports)')
    args = ap.parse_args()

    root = os.getcwd()
    proj = os.path.abspath(args.project)
    date = dt.date.today().strftime('%Y-%m-%d')
    out_dir = os.path.join(root, 'logs', 'e2e', date)
    os.makedirs(out_dir, exist_ok=True)

    # Optional prewarm with fallback
    prewarm_rc = None
    prewarm_note = None
    if args.prewarm:
        pre_cmd = [args.godot_bin, '--headless', '--path', proj, '--build-solutions', '--quit']
        _rcp, _outp = run_cmd(pre_cmd, cwd=proj, timeout=300_000)
        prewarm_attempts = 1
        prewarm_rc = _rcp
        # Write first attempt
        write_text(os.path.join(out_dir, 'prewarm-godot.txt'), _outp)
        if _rcp != 0:
            # Wait and retry once to mitigate transient C# load issues
            time.sleep(3)
            _rcp2, _outp2 = run_cmd(pre_cmd, cwd=proj, timeout=360_000)
            prewarm_attempts = 2
            prewarm_rc = _rcp2
            # Append retry log to same file
            try:
                with open(os.path.join(out_dir, 'prewarm-godot.txt'), 'a', encoding='utf-8') as f:
                    f.write("\n=== retry rc=%d ===\n" % _rcp2)
                    f.write(_outp2)
            except Exception:
                pass
            if _rcp2 == 0:
                prewarm_note = 'retry-ok'
            else:
                # Fallback to dotnet build to avoid editor plugin failures
                dotnet_projects = []
                tests_csproj = os.path.join(proj, 'Tests.Godot.csproj')
                if os.path.isfile(tests_csproj):
                    dotnet_projects.append(tests_csproj)
                # Also try solution at repo root if present
                sln = os.path.join(root, 'GodotGame.sln')
                # Prefer project build; if solution exists, add as secondary
                build_logs = []
                for item in (dotnet_projects or [sln] if os.path.isfile(sln) else []):
                    rc_b, out_b = run_cmd(['dotnet', 'build', item, '-c', 'Debug', '-v', 'minimal'], cwd=root, timeout=600_000)
                    build_logs.append((item, rc_b, out_b))
                # Persist build logs
                agg = []
                for item, rc_b, out_b in build_logs:
                    agg.append(f'=== {item} rc={rc_b} ===\n{out_b}\n')
                write_text(os.path.join(out_dir, 'prewarm-dotnet.txt'), '\n'.join(agg) if agg else 'NO_DOTNET_BUILD_TARGETS')
                prewarm_note = 'fallback-dotnet'

    # Run tests（带 Debugger Break fail-fast）
    # Build command with optional -a filters
    cmd = [args.godot_bin, '--headless', '--path', proj, '-s', '-d', 'res://addons/gdUnit4/bin/GdUnitCmdTool.gd', '--ignoreHeadlessMode']
    for a in args.add:
        apath = a
        if not apath.startswith('res://'):
            # normalize relative tests path to res://
            apath = 'res://' + apath.replace('\\', '/').lstrip('/')
        cmd += ['-a', apath]
    rc, out = run_cmd_failfast(cmd, cwd=proj, timeout=args.timeout_sec*1000)
    console_path = os.path.join(out_dir, 'gdunit-console.txt')
    with open(console_path, 'w', encoding='utf-8') as f:
        f.write(out)

    # Generate HTML log frame (optional)
    _rc2, _out2 = run_cmd([args.godot_bin, '--headless', '--path', proj, '--quiet', '-s', 'res://addons/gdUnit4/bin/GdUnitCopyLog.gd'], cwd=proj)

    # Archive reports
    reports_dir = os.path.join(proj, 'reports')
    dest = args.report_dir if args.report_dir else os.path.join(out_dir, 'gdunit-reports')
    # Always create a destination folder with at least the console log and a summary
    if os.path.isdir(dest):
        shutil.rmtree(dest, ignore_errors=True)
    os.makedirs(dest, exist_ok=True)
    # Copy console log for diagnosis
    try:
        shutil.copy2(console_path, os.path.join(dest, 'gdunit-console.txt'))
    except Exception:
        pass
    # Copy reports if they exist
    if os.path.isdir(reports_dir):
        for name in os.listdir(reports_dir):
            src = os.path.join(reports_dir, name)
            dst = os.path.join(dest, name)
            if os.path.isdir(src):
                shutil.copytree(src, dst, dirs_exist_ok=True)
            else:
                shutil.copy2(src, dst)
    # Write a small summary json for CI
    summary = {'rc': rc, 'project': proj, 'added': args.add, 'timeout_sec': args.timeout_sec}
    if prewarm_rc is not None:
        summary['prewarm_rc'] = prewarm_rc
        if prewarm_note:
            summary['prewarm_note'] = prewarm_note
        try:
            summary['prewarm_attempts'] = prewarm_attempts
        except NameError:
            pass
    try:
        with open(os.path.join(dest, 'run-summary.json'), 'w', encoding='utf-8') as f:
            json.dump(summary, f, ensure_ascii=False)
    except Exception:
        pass
    print(f'GDUNIT_DONE rc={rc} out={out_dir}')
    return 0 if rc == 0 else rc


if __name__ == '__main__':
    raise SystemExit(main())
