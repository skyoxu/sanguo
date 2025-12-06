#!/usr/bin/env python3
"""
Prepare Tests.Godot to reference runtime directory (e.g., Game.Godot) as res://Game.Godot.
Tries to create a directory junction; falls back to copy excluding heavy folders.

Usage:
  py -3 scripts/python/prepare_gd_tests.py --project Tests.Godot --runtime Game.Godot
"""
import argparse
import os
import shutil
import subprocess
import sys

EXCLUDE = {'bin','obj','.import','.godot','logs'}

def is_windows():
    return os.name == 'nt'

def make_junction(link, target):
    if not is_windows():
        return False
    try:
        # Use cmd mklink /J link target
        cmd = ['cmd','/c','mklink','/J',link,target]
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        out,_ = p.communicate(timeout=10)
        return p.returncode == 0 and os.path.isdir(link)
    except Exception:
        return False

def copy_runtime(link, target):
    os.makedirs(link, exist_ok=True)
    for name in os.listdir(target):
        if name in EXCLUDE:
            continue
        src = os.path.join(target, name)
        dst = os.path.join(link, name)
        if os.path.isdir(src):
            shutil.copytree(src, dst, dirs_exist_ok=True)
        else:
            shutil.copy2(src, dst)
    # mark copied
    open(os.path.join(link, '._copied'), 'w', encoding='utf-8').close()

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--project', default='Tests.Godot')
    ap.add_argument('--runtime', default='Game.Godot')
    args = ap.parse_args()

    root = os.getcwd()
    proj = os.path.abspath(args.project)
    runtime = os.path.abspath(args.runtime)
    if not os.path.isdir(proj):
        print(f'PROJECT_NOT_FOUND: {proj}')
        return 1
    if not os.path.isdir(runtime):
        print(f'RUNTIME_NOT_FOUND: {runtime}')
        return 1

    link = os.path.join(proj, os.path.basename(runtime))
    if os.path.exists(link):
        print(f'TEST_RUNTIME_LINK_EXISTS: {link}')
        return 0
    # try junction then copy fallback
    if make_junction(link, runtime):
        print(f'JUNCTION_CREATED: {link} -> {runtime}')
        return 0
    copy_runtime(link, runtime)
    if not os.path.exists(link):
        print(f'PREPARE_FAILED: {link}')
        return 1
    print(f'RUNTIME_COPIED: {link}')
    return 0

if __name__ == '__main__':
    raise SystemExit(main())

