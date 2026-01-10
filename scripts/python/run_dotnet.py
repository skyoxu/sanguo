#!/usr/bin/env python3
"""
Run dotnet restore/test with coverage and archive artifacts under logs/unit/<date>/.
Exits non-zero on test failure or when coverage thresholds (if provided) are not met.

Env thresholds (optional):
  COVERAGE_LINES_MIN   e.g., "90" (percent)
  COVERAGE_BRANCHES_MIN e.g., "85" (percent)

Usage (Windows):
  py -3 scripts/python/run_dotnet.py --solution Game.sln --configuration Debug
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
import time
import xml.etree.ElementTree as ET


def resolve_dotnet_exe(repo_root: str) -> str:
    """
    Prefer the repo-local toolchain when available.

    CI and local workflows may provision a pinned .NET SDK under `.dotnet/`.
    Relying on the system-wide `dotnet` can be brittle if the host SDK is
    missing workload-related SDK components.
    """
    local = os.path.join(repo_root, ".dotnet", "dotnet.exe")
    if os.path.isfile(local):
        return local
    return "dotnet"


def ensure_local_workload_locator_sdks(*, repo_root: str, dotnet_exe: str, out_dir: str) -> dict:
    """
    Some pinned/local SDK installs can miss workload locator SDK folders/files.

    In that case, MSBuild fails very early with errors like:
      - MSB4019: missing AutoImport.props
      - MSB4276: failed to resolve Workload*Locator SDKs

    This function creates minimal no-op stubs for:
      - Microsoft.NET.SDK.WorkloadAutoImportPropsLocator/Sdk/{Sdk.props,Sdk.targets,AutoImport.props}
      - Microsoft.NET.SDK.WorkloadManifestTargetsLocator/Sdk/{Sdk.props,Sdk.targets,WorkloadManifest.targets}

    The directory `.dotnet/` is gitignored; creating these files is an environment repair,
    not a source change.
    """
    report = {"dotnet_exe": dotnet_exe, "attempted": False, "created": [], "sdk_version": None, "error": None}

    local_root = os.path.join(repo_root, ".dotnet")
    if os.path.abspath(dotnet_exe).startswith(os.path.abspath(local_root) + os.sep):
        report["attempted"] = True
    else:
        return report

    def _write_if_missing(path: str) -> None:
        if os.path.exists(path):
            return
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with io.open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write("<Project />\n")
        report["created"].append(path.replace("\\", "/"))

    try:
        rc, ver_out = run_cmd([dotnet_exe, "--version"], cwd=repo_root, timeout=30_000)
        sdk_ver = (ver_out or "").strip().splitlines()[-1].strip() if rc == 0 and ver_out else ""
        report["sdk_version"] = sdk_ver or None
        if not sdk_ver:
            return report

        sdks_root = os.path.join(local_root, "sdk", sdk_ver, "Sdks")
        auto_dir = os.path.join(sdks_root, "Microsoft.NET.SDK.WorkloadAutoImportPropsLocator", "Sdk")
        man_dir = os.path.join(sdks_root, "Microsoft.NET.SDK.WorkloadManifestTargetsLocator", "Sdk")

        _write_if_missing(os.path.join(auto_dir, "Sdk.props"))
        _write_if_missing(os.path.join(auto_dir, "Sdk.targets"))
        _write_if_missing(os.path.join(auto_dir, "AutoImport.props"))

        _write_if_missing(os.path.join(man_dir, "Sdk.props"))
        _write_if_missing(os.path.join(man_dir, "Sdk.targets"))
        _write_if_missing(os.path.join(man_dir, "WorkloadManifest.targets"))

        with io.open(os.path.join(out_dir, "dotnet-sdk-repair.json"), "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
    except Exception as e:
        report["error"] = str(e)
        try:
            with io.open(os.path.join(out_dir, "dotnet-sdk-repair.json"), "w", encoding="utf-8") as f:
                json.dump(report, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    return report


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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--solution', default='Game.sln')
    ap.add_argument('--configuration', default='Debug')
    ap.add_argument('--out-dir', default=None)
    args = ap.parse_args()

    root = os.getcwd()
    dotnet = resolve_dotnet_exe(root)
    date = dt.date.today().strftime('%Y-%m-%d')
    out_dir = args.out_dir or os.path.join(root, 'logs', 'unit', date)
    ensure_dir(out_dir)

    summary = {
        'solution': args.solution,
        'configuration': args.configuration,
        'out_dir': out_dir,
        'dotnet': dotnet,
        'status': 'fail',
    }

    summary['dotnet_sdk_repair'] = ensure_local_workload_locator_sdks(repo_root=root, dotnet_exe=dotnet, out_dir=out_dir)

    # Restore (with retry for transient CI/network issues)
    restore_retries = max(1, int(os.getenv("DOTNET_RESTORE_RETRIES", "3") or "3"))
    restore_delay_s = float(os.getenv("DOTNET_RESTORE_RETRY_DELAY_SECS", "2") or "2")
    restore_attempts: list[dict] = []
    rc = 1
    out = ""
    for attempt in range(1, restore_retries + 1):
        rc, out = run_cmd([dotnet, "restore", args.solution], cwd=root)
        restore_attempts.append({"attempt": attempt, "rc": rc})
        with io.open(os.path.join(out_dir, f"dotnet-restore-attempt{attempt}.log"), "w", encoding="utf-8") as f:
            f.write(out)
        if rc == 0:
            break
        if attempt < restore_retries:
            time.sleep(restore_delay_s)
            restore_delay_s = min(30.0, restore_delay_s * 2)

    # Keep a stable filename for CI artifact copy.
    try:
        shutil.copyfile(
            os.path.join(out_dir, f"dotnet-restore-attempt{len(restore_attempts)}.log"),
            os.path.join(out_dir, "dotnet-restore.log"),
        )
    except Exception:
        with io.open(os.path.join(out_dir, "dotnet-restore.log"), "w", encoding="utf-8") as f:
            f.write(out)

    summary["restore_rc"] = rc
    summary["restore_attempts"] = restore_attempts
    if rc != 0:
        with io.open(os.path.join(out_dir, "summary.json"), "w", encoding="utf-8") as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)
        print(f"RUN_DOTNET status=fail stage=restore out={out_dir}")
        return 1

    # Test with coverage
    rc, out = run_cmd([dotnet, 'test', args.solution,
                       f'-c', args.configuration,
                       '--collect:XPlat Code Coverage',
                       '--logger', 'trx;LogFileName=tests.trx'], cwd=root)
    with io.open(os.path.join(out_dir, 'dotnet-test-output.txt'), 'w', encoding='utf-8') as f:
        f.write(out)
    summary['test_rc'] = rc

    # Copy artifacts using paths emitted by dotnet test output (preferred).
    artifacts = parse_paths_from_test_output(out)
    summary['artifacts_detected'] = artifacts

    trx_src = pick_latest_existing(artifacts.get('trx_paths') or [])
    cov_src = pick_latest_existing(artifacts.get('coverage_paths') or [])

    # Fallback: search inside Game.Core.Tests/TestResults only (avoid logs/**).
    if not trx_src:
        fallback_trx_root = os.path.join(root, 'Game.Core.Tests', 'TestResults')
        if os.path.isdir(fallback_trx_root):
            candidates = []
            for cur_root, _, files in os.walk(fallback_trx_root):
                for name in files:
                    if name.lower().endswith('.trx'):
                        candidates.append(os.path.join(cur_root, name))
            trx_src = pick_latest_existing(candidates)

    if not cov_src:
        fallback_cov_root = os.path.join(root, 'Game.Core.Tests', 'TestResults')
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

    # Thresholds (default hard gate; override via env)
    #
    # NOTE: These defaults are the project baseline. See docs/testing-framework.md.
    default_lines_min = 90.0
    default_branches_min = 85.0

    raw_lines_min = (os.environ.get('COVERAGE_LINES_MIN') or '').strip()
    raw_branches_min = (os.environ.get('COVERAGE_BRANCHES_MIN') or '').strip()

    lines_min = default_lines_min
    branches_min = default_branches_min
    threshold_source = {
        'lines_min': 'default',
        'branches_min': 'default',
    }

    try:
        if raw_lines_min:
            lines_min = float(raw_lines_min)
            threshold_source['lines_min'] = 'env'
    except Exception:
        pass

    try:
        if raw_branches_min:
            branches_min = float(raw_branches_min)
            threshold_source['branches_min'] = 'env'
    except Exception:
        pass

    if coverage and isinstance(coverage, dict):
        # Provide stable keys for downstream tools/tests.
        if 'line_pct' in coverage and 'lines_pct' not in coverage:
            coverage['lines_pct'] = coverage.get('line_pct')
        if 'branch_pct' in coverage and 'branches_pct' not in coverage:
            coverage['branches_pct'] = coverage.get('branch_pct')
        coverage['lines_min'] = lines_min
        coverage['branches_min'] = branches_min
        coverage['threshold_source'] = threshold_source

    threshold_ok = False
    if coverage and isinstance(coverage, dict):
        try:
            threshold_ok = (float(coverage.get('line_pct', 0) or 0) >= float(lines_min)) and (
                float(coverage.get('branch_pct', 0) or 0) >= float(branches_min)
            )
        except Exception:
            threshold_ok = False

    summary['threshold_ok'] = bool(threshold_ok)

    summary['status'] = 'ok' if (rc == 0 and threshold_ok) else ('tests_failed' if rc != 0 else 'coverage_failed')
    with io.open(os.path.join(out_dir, 'summary.json'), 'w', encoding='utf-8') as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    print(f"RUN_DOTNET status={summary['status']} line={coverage.get('line_pct', 'n/a') if coverage else 'n/a'}% branch={coverage.get('branch_pct','n/a') if coverage else 'n/a'} out={out_dir}")
    if summary['status'] == 'ok':
        return 0
    return 2 if summary['status'] == 'coverage_failed' else 1


if __name__ == '__main__':
    sys.exit(main())
