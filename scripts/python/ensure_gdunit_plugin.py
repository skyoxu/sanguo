#!/usr/bin/env python3
"""
Ensure GdUnit4 plugin exists under a Godot test project (Tests.Godot).
If missing, download the specified release tag zip from GitHub and extract
the 'addons/gdUnit4' folder into the project.

Windows friendly; uses only stdlib.

Usage:
  py -3 scripts/python/ensure_gdunit_plugin.py --project Tests.Godot --version v6.0.0
"""
import argparse
import io
import os
import shutil
import sys
import tempfile
import urllib.request
import zipfile


def ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def download(url: str, dest: str) -> None:
    with urllib.request.urlopen(url) as r, open(dest, 'wb') as f:
        shutil.copyfileobj(r, f)


def find_addons_root(unzip_dir: str) -> str | None:
    # Search for a directory ending with 'addons/gdUnit4'
    for root, dirs, files in os.walk(unzip_dir):
        if root.replace('\\', '/').endswith('addons/gdUnit4'):
            return root
    return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--project', default='Tests.Godot')
    ap.add_argument('--version', default='v6.0.0', help='GdUnit4 release tag (e.g., v6.0.0)')
    args = ap.parse_args()

    proj = os.path.abspath(args.project)
    target_tool = os.path.join(proj, 'addons', 'gdUnit4', 'bin', 'GdUnitCmdTool.gd')
    if os.path.isfile(target_tool):
        print('GDUNIT_PLUGIN_PRESENT=1')
        return 0

    print('GDUNIT_PLUGIN_PRESENT=0 (trying to fetch)')
    work = tempfile.mkdtemp(prefix='gdunit4_')
    try:
        # Try common URLs
        urls = [
            f'https://github.com/MikeSchulze/gdUnit4/archive/refs/tags/{args.version}.zip',
            f'https://github.com/MikeSchulze/gdUnit4/releases/download/{args.version}/gdUnit4-{args.version}.zip',
            f'https://github.com/MikeSchulze/gdUnit4/releases/download/{args.version}/gdUnit4-{args.version}.zip'.replace('v',''),
        ]
        zip_path = os.path.join(work, 'gdunit4.zip')
        ok = False
        last_err = None
        for u in urls:
            try:
                download(u, zip_path)
                ok = True
                break
            except Exception as e:
                last_err = e
                continue
        if not ok:
            print(f'ERROR: Failed to download GdUnit4 zip: {last_err}')
            return 1
        # Unzip
        unzip_dir = os.path.join(work, 'unzipped')
        ensure_dir(unzip_dir)
        with zipfile.ZipFile(zip_path, 'r') as z:
            z.extractall(unzip_dir)
        addons_root = find_addons_root(unzip_dir)
        if not addons_root:
            print('ERROR: addons/gdUnit4 folder not found in the downloaded archive')
            return 1
        # Copy into project
        dest_root = os.path.join(proj, 'addons', 'gdUnit4')
        if os.path.isdir(dest_root):
            shutil.rmtree(dest_root, ignore_errors=True)
        shutil.copytree(addons_root, dest_root)
        # Verify
        if os.path.isfile(target_tool):
            print('GDUNIT_PLUGIN_FETCHED=1')
            return 0
        print('ERROR: GdUnitCmdTool.gd still missing after fetch')
        return 1
    finally:
        shutil.rmtree(work, ignore_errors=True)


if __name__ == '__main__':
    sys.exit(main())

