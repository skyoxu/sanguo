#!/usr/bin/env python3
"""
CI pipeline driver (Python): dotnet tests+coverage (soft gate), Godot self-check, encoding scan.

Usage (Windows):
  py -3 scripts/python/ci_pipeline.py all \
    --solution Game.sln --configuration Debug \
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
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET

from _ci_pipeline_entrypoint_guard import resolve_dotnet_stage_timeout_ms, run_unified_entrypoint_gates


def _safe_int(raw, default):
    try:
        return int(str(raw).strip())
    except Exception:
        return default


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


def run_env_evidence_preflight(root: str, godot_bin: str):
    """
    Generate deterministic environment evidence artifacts before unit tests.
    This keeps cold CI workspaces aligned with acceptance test expectations.
    """
    sc_dir = os.path.join(root, 'scripts', 'sc')
    if not os.path.isdir(sc_dir):
        return 1, {'status': 'fail', 'reason': f'missing scripts/sc: {sc_dir}'}

    added_path = False
    if sc_dir not in sys.path:
        sys.path.insert(0, sc_dir)
        added_path = True

    try:
        from _env_evidence_preflight import step_env_evidence_preflight
        from _util import ci_dir

        step = step_env_evidence_preflight(ci_dir('ci-pipeline-env-preflight'), godot_bin=godot_bin, task_id='1')
        details = dict(getattr(step, 'details', {}) or {})
        details.update(
            {
                'name': getattr(step, 'name', 'env-evidence-preflight'),
                'status': getattr(step, 'status', 'fail'),
                'rc': getattr(step, 'rc', 1),
                'log': getattr(step, 'log', None),
            }
        )
        return int(getattr(step, 'rc', 1)), details
    except Exception as exc:
        return 1, {'status': 'fail', 'reason': f'env preflight import/exec error: {exc}'}
    finally:
        if added_path:
            try:
                sys.path.remove(sc_dir)
            except ValueError:
                pass


def _copy_if_exists(src: str, dst: str) -> bool:
    try:
        if not os.path.isfile(src):
            return False
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copyfile(src, dst)
        return True
    except Exception:
        return False


def _extract_failed_tests_from_trx(trx_path: str, max_items: int = 30) -> list[dict]:
    try:
        if not os.path.isfile(trx_path):
            return []
        tree = ET.parse(trx_path)
        root = tree.getroot()
        ns = ""
        if root.tag.startswith("{"):
            ns = root.tag.split("}")[0] + "}"

        failures = []
        for r in root.findall(f".//{ns}UnitTestResult"):
            outcome = (r.attrib.get("outcome") or "").lower()
            if outcome != "failed":
                continue
            test_name = r.attrib.get("testName") or r.attrib.get("testId") or "unknown"
            msg = ""
            stack = ""
            out = r.find(f"{ns}Output")
            if out is not None:
                err = out.find(f"{ns}ErrorInfo")
                if err is not None:
                    m = err.find(f"{ns}Message")
                    if m is not None and m.text:
                        msg = m.text.strip()
                    s = err.find(f"{ns}StackTrace")
                    if s is not None and s.text:
                        stack = s.text.strip()
            failures.append({"test": test_name, "message": msg, "stack": stack})
            if len(failures) >= max_items:
                break
        return failures
    except Exception:
        return []


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest='cmd', required=True)
    ap_all = sub.add_parser('all')
    ap_all.add_argument('--solution', default='Game.sln')
    ap_all.add_argument('--configuration', default='Debug')
    ap_all.add_argument('--godot-bin', required=True)
    ap_all.add_argument('--project', default='project.godot')
    ap_all.add_argument('--build-solutions', action='store_true')
    ap_all.add_argument(
        '--dotnet-stage-timeout-ms',
        type=int,
        default=None,
        help='Outer timeout for run_dotnet stage in milliseconds. Default derives from DOTNET_TEST_TIMEOUT_MS and is at least 3600000.',
    )

    args = ap.parse_args()
    if args.cmd != 'all':
        print('Unsupported command')
        return 1

    root = os.getcwd()
    date = dt.date.today().strftime('%Y-%m-%d')
    ci_dir = os.path.join('logs', 'ci', date)
    os.makedirs(ci_dir, exist_ok=True)

    summary = {
        'manual_triplet_examples': {},
        'whitelist_expiry_warning': {},
        'gate_bundle': {},
        'line_endings': {},
        'preflight_env_evidence': {},
        'preflight_task1': {},
        'dotnet': {},
        'selfcheck': {},
        'encoding': {},
        'i18n_keys': {},
        'content_packs': {},
        'prd_v3_rules': {},
        'workflows_index': {},
        'gd_tests': {},
        'status': 'ok'
    }
    hard_fail = False

    # 0) Unified task-level entrypoint policy gates:
    #    - hard gate: forbid manual sc triplet examples
    #    - soft warning: whitelist expiry horizon
    gate_details, gate_hard_fail = run_unified_entrypoint_gates(
        root=root,
        ci_dir=ci_dir,
        date=date,
        run_cmd=run_cmd,
        read_json=read_json,
    )
    summary.update(gate_details)
    if gate_hard_fail:
        hard_fail = True

    # 0.4) Governance gate bundle (hard gate)
    gate_bundle_summary_path = os.path.join('logs', 'ci', date, 'gate-bundle', 'ci-pipeline-summary.json')
    task_links_max_warnings = _safe_int(os.environ.get('TASK_LINKS_MAX_WARNINGS', '-1'), -1)
    rc_bundle, out_bundle = run_cmd(
        [
            'py',
            '-3',
            'scripts/python/run_gate_bundle.py',
            '--mode',
            'all',
            '--task-links-max-warnings',
            str(task_links_max_warnings),
            '--summary-out',
            gate_bundle_summary_path,
        ],
        root,
        900_000,
    )
    with io.open(os.path.join(ci_dir, 'gate-bundle-stdout.txt'), 'w', encoding='utf-8') as f:
        f.write(out_bundle)
    gate_bundle_sum = read_json(gate_bundle_summary_path) or {}
    summary['gate_bundle'] = {
        'rc': rc_bundle,
        'status': gate_bundle_sum.get('status') or ('ok' if rc_bundle == 0 else 'fail'),
        'out': gate_bundle_summary_path,
        'hard_failures_count': gate_bundle_sum.get('hard_failures_count', gate_bundle_sum.get('failures_count')),
        'soft_failures_count': gate_bundle_sum.get('soft_failures_count', 0),
    }
    if rc_bundle != 0:
        hard_fail = True

    # 0.45) Line endings policy gate (hard gate)
    line_endings_summary_path = os.path.join('logs', 'ci', date, 'line-endings-summary.json')
    rc_eol, out_eol = run_cmd(
        [
            'py',
            '-3',
            'scripts/python/check_line_endings.py',
            '--summary-out',
            line_endings_summary_path,
        ],
        root,
        180_000,
    )
    with io.open(os.path.join(ci_dir, 'line-endings-stdout.txt'), 'w', encoding='utf-8') as f:
        f.write(out_eol)
    line_endings_sum = read_json(line_endings_summary_path) or {}
    summary['line_endings'] = {
        'rc': rc_eol,
        'status': line_endings_sum.get('status') or ('ok' if rc_eol == 0 else 'fail'),
        'out': line_endings_summary_path,
        'checked': line_endings_sum.get('checked'),
        'violations_count': line_endings_sum.get('violations_count'),
    }
    if rc_eol != 0:
        hard_fail = True

    # 0.5) Deterministic Task1 environment evidence preflight (hard gate)
    rc_preflight, preflight_details = run_env_evidence_preflight(root, args.godot_bin)
    summary['preflight_env_evidence'] = preflight_details
    summary['preflight_task1'] = {
        'rc': rc_preflight,
        'status': preflight_details.get('status'),
        'log': preflight_details.get('log'),
    }
    if rc_preflight != 0:
        hard_fail = True

    # 1) Dotnet tests + coverage (soft gate on coverage)
    dotnet_stage_timeout_ms = resolve_dotnet_stage_timeout_ms(args.dotnet_stage_timeout_ms)
    rc, out = run_cmd(['py', '-3', 'scripts/python/run_dotnet.py',
                       '--solution', args.solution,
                       '--configuration', args.configuration], cwd=root, timeout=dotnet_stage_timeout_ms)
    dotnet_sum = read_json(os.path.join('logs', 'unit', date, 'summary.json')) or {}
    summary['dotnet'] = {
        'rc': rc,
        'line_pct': (dotnet_sum.get('coverage') or {}).get('line_pct'),
        'branch_pct': (dotnet_sum.get('coverage') or {}).get('branch_pct'),
        'status': dotnet_sum.get('status')
    }
    if rc not in (0, 2) or summary['dotnet']['status'] == 'tests_failed':
        hard_fail = True

    # Persist dotnet runner stdout for CI forensics (so we can debug without unit artifacts).
    _copy_if_exists(
        os.path.join('logs', 'unit', date, 'dotnet-restore.log'),
        os.path.join('logs', 'ci', date, 'dotnet-restore.log'),
    )
    _copy_if_exists(
        os.path.join('logs', 'unit', date, 'dotnet-sdk-repair.json'),
        os.path.join('logs', 'ci', date, 'dotnet-sdk-repair.json'),
    )
    _copy_if_exists(
        os.path.join('logs', 'unit', date, 'dotnet-test-output.txt'),
        os.path.join('logs', 'ci', date, 'dotnet-test-output.txt'),
    )
    _copy_if_exists(
        os.path.join('logs', 'unit', date, 'tests.trx'),
        os.path.join('logs', 'ci', date, 'tests.trx'),
    )
    with io.open(os.path.join('logs', 'ci', date, 'dotnet-stdout.txt'), 'w', encoding='utf-8') as f:
        f.write(out)
    failures = _extract_failed_tests_from_trx(os.path.join('logs', 'ci', date, 'tests.trx'))
    if failures:
        with io.open(os.path.join('logs', 'ci', date, 'dotnet-failures.json'), 'w', encoding='utf-8') as f:
            json.dump({"failed": failures}, f, ensure_ascii=False, indent=2)
        summary['dotnet']['failed_tests'] = [x.get("test") for x in failures]

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

    # 3) Text integrity + encoding scan (hard gate)
    # Prefer PR-friendly compare against origin/main...HEAD instead of time-based scans.
    changed_files = []
    try:
        rc_cf, out_cf = run_cmd(['git', 'diff', '--name-only', 'origin/main...HEAD'], cwd=root)
        if rc_cf == 0:
            changed_files = [ln.strip() for ln in out_cf.splitlines() if ln.strip()]
    except Exception:
        changed_files = []

    if changed_files:
        rc3, out3 = run_cmd(['py', '-3', 'scripts/python/check_encoding.py', '--files', *changed_files], cwd=root)
    else:
        # fallback: still better than nothing in shallow/offline envs
        rc3, out3 = run_cmd(['py', '-3', 'scripts/python/check_encoding.py', '--since-today'], cwd=root)

    enc_sum = read_json(os.path.join('logs', 'ci', date, 'encoding', 'session-summary.json')) or {}
    summary['encoding'] = enc_sum
    if rc3 != 0 or int(enc_sum.get('bad') or 0) > 0:
        hard_fail = True

    # Complement: semantic garble patterns + BOM (config/code) hard gate
    try:
        if changed_files:
            rc4, out4 = run_cmd(
                ['py', '-3', 'scripts/python/check_text_integrity.py', '--files', *changed_files, '--hard-bom', '--out-dir', os.path.join('logs', 'ci', date, 'text-integrity-changed')],
                cwd=root,
            )
        else:
            rc4, out4 = run_cmd(
                ['py', '-3', 'scripts/python/check_text_integrity.py', '--hard-bom', '--out-dir', os.path.join('logs', 'ci', date, 'text-integrity-changed')],
                cwd=root,
            )
        summary['text_integrity'] = {'rc': rc4, 'note': 'see logs/ci/<date>/text-integrity-changed/summary.json'}
        if rc4 != 0:
            hard_fail = True
    except Exception as exc:
        summary['text_integrity'] = {'rc': 1, 'error': str(exc)}
        hard_fail = True

    # 4) i18n keys alignment (hard gate)
    try:
        rc_i18n, out_i18n = run_cmd(
            ['py', '-3', 'scripts/python/validate_i18n_keys.py'],
            cwd=root,
        )
        summary['i18n_keys'] = {
            'rc': rc_i18n,
            'note': 'see logs/ci/<date>/i18n-keys-validate.json',
        }
        with io.open(os.path.join('logs', 'ci', date, 'i18n-keys-stdout.txt'), 'w', encoding='utf-8') as f:
            f.write(out_i18n)
        if rc_i18n != 0:
            hard_fail = True
    except Exception as exc:
        summary['i18n_keys'] = {'rc': 1, 'error': str(exc)}
        hard_fail = True

    # 5) Data catalog validation (hard gate)
    try:
        rc_data, out_data = run_cmd(
            ['py', '-3', 'scripts/python/validate_data_catalog.py', '--strict'],
            cwd=root,
        )
        summary['data_catalog'] = {
            'rc': rc_data,
            'note': 'see logs/ci/<date>/data-catalog-validate.json',
        }
        with io.open(os.path.join('logs', 'ci', date, 'data-catalog-stdout.txt'), 'w', encoding='utf-8') as f:
            f.write(out_data)
        if rc_data != 0:
            hard_fail = True
    except Exception as exc:
        summary['data_catalog'] = {'rc': 1, 'error': str(exc)}
        hard_fail = True

    # 6) Data version bump gate (hard gate)
    try:
        rc_versions, out_versions = run_cmd(
            ['py', '-3', 'scripts/python/check_data_versions_bumped.py', '--base', 'origin/main', '--head', 'HEAD'],
            cwd=root,
        )
        summary['data_version_gate'] = {
            'rc': rc_versions,
            'note': 'see logs/ci/<date>/data-version-gate.json',
        }
        with io.open(os.path.join('logs', 'ci', date, 'data-version-gate-stdout.txt'), 'w', encoding='utf-8') as f:
            f.write(out_versions)
        if rc_versions != 0:
            hard_fail = True
    except Exception as exc:
        summary['data_version_gate'] = {'rc': 1, 'error': str(exc)}
        hard_fail = True

    # 7) GdUnit test naming/encoding (hard gate, changed files only)
    try:
        gd_changed = [
            p for p in changed_files
            if p.lower().endswith(".gd")
            and p.replace("\\", "/").startswith("Tests.Godot/tests/")
            and os.path.isfile(os.path.join(root, p))
        ]
        if gd_changed:
            gd_out = os.path.join('logs', 'ci', date, 'gd-tests-changed.json')
            rc5, out5 = run_cmd(
                ['py', '-3', 'scripts/python/check_gd_test_naming_and_encoding.py', '--files', *gd_changed, '--style', 'strict', '--out', gd_out],
                cwd=root,
            )
            summary['gd_tests'] = {'rc': rc5, 'checked': len(gd_changed), 'out': gd_out}
            if rc5 != 0:
                hard_fail = True
        else:
            summary['gd_tests'] = {'rc': 0, 'checked': 0, 'note': 'no changed Tests.Godot/tests/*.gd files'}
    except Exception as exc:
        summary['gd_tests'] = {'rc': 1, 'error': str(exc)}
        hard_fail = True

    # 8) Workflows index validation (hard gate)
    try:
        rc_wf, out_wf = run_cmd(
            ['py', '-3', 'scripts/python/validate_workflows_index.py'],
            cwd=root,
        )
        summary['workflows_index'] = {
            'rc': rc_wf,
            'note': 'see logs/ci/<date>/workflows-index-validate.json',
        }
        with io.open(os.path.join('logs', 'ci', date, 'workflows-index-stdout.txt'), 'w', encoding='utf-8') as f:
            f.write(out_wf)
        if rc_wf != 0:
            hard_fail = True
    except Exception as exc:
        summary['workflows_index'] = {'rc': 1, 'error': str(exc)}
        hard_fail = True

    # 9) Content pack validation (hard gate)
    try:
        rc_pack, out_pack = run_cmd(
            ['py', '-3', 'scripts/python/validate_content_packs.py', '--strict'],
            cwd=root,
        )
        summary['content_packs'] = {
            'rc': rc_pack,
            'note': 'see logs/ci/<date>/content-pack-validate.json',
        }
        with io.open(os.path.join('logs', 'ci', date, 'content-pack-stdout.txt'), 'w', encoding='utf-8') as f:
            f.write(out_pack)
        if rc_pack != 0:
            hard_fail = True
    except Exception as exc:
        summary['content_packs'] = {'rc': 1, 'error': str(exc)}
        hard_fail = True

    # 10) PRD v3 frozen rules validation (hard gate on schema + semantic invariants)
    try:
        rules_out = os.path.join('logs', 'ci', date, 'prd-v3-rules-validate.json')
        rc_rules, out_rules = run_cmd(
            ['py', '-3', 'scripts/python/validate_prd_v3_rules.py', '--hash-mode', 'warn', '--out', rules_out],
            cwd=root,
        )
        summary['prd_v3_rules'] = {
            'rc': rc_rules,
            'out': rules_out,
            'hash_mode': 'warn',
        }
        with io.open(os.path.join('logs', 'ci', date, 'prd-v3-rules-stdout.txt'), 'w', encoding='utf-8') as f:
            f.write(out_rules)
        if rc_rules != 0:
            hard_fail = True
    except Exception as exc:
        summary['prd_v3_rules'] = {'rc': 1, 'error': str(exc)}
        hard_fail = True

    summary['status'] = 'ok' if not hard_fail else 'fail'
    with io.open(os.path.join(ci_dir, 'ci-pipeline-summary.json'), 'w', encoding='utf-8') as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    print(f"CI_PIPELINE status={summary['status']} dotnet={summary['dotnet'].get('status')} selfcheck={summary['selfcheck'].get('status')} encoding_bad={summary['encoding'].get('bad', 'n/a')}")
    return 0 if not hard_fail else 1


if __name__ == '__main__':
    sys.exit(main())
