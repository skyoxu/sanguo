"""Immutable runtime input preparation for local validation (ADR-0035)."""
from __future__ import annotations

import hashlib
import json
import stat
import subprocess
import time
import zipfile
from pathlib import Path, PurePosixPath

from project_health_knowledge import safe_file, write_json


def prepare_snapshot(root: Path, destination: Path, revision: str, mode: str, deadline: float) -> dict:
    destination.mkdir(parents=True, exist_ok=False)

    def remaining():
        seconds = int(deadline - time.monotonic())
        if seconds <= 0:
            raise TimeoutError('Snapshot preparation exceeded the global timeout')
        return seconds

    hashes = {}
    if mode == 'main':
        archive = destination.parent / 'main.zip'
        subprocess.run(['git', '-C', str(root), 'archive', '--format=zip', '-o', str(archive), revision],
                       capture_output=True, check=True, timeout=remaining())
        with zipfile.ZipFile(archive) as bundle:
            for item in bundle.infolist():
                remaining()
                if item.is_dir():
                    continue
                if stat.S_ISLNK(item.external_attr >> 16):
                    raise ValueError('Runtime snapshot does not support tracked symlinks: ' + item.filename)
                target = safe_file(destination, item.filename)
                data = bundle.read(item)
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(data)
                hashes[item.filename] = hashlib.sha256(data).hexdigest()
    elif mode == 'workspace':
        names = subprocess.run(['git', '-C', str(root), 'ls-files', '-z', '--cached', '--others', '--exclude-standard'],
                               capture_output=True, check=True, timeout=remaining()).stdout.decode('utf-8').split('\0')
        for name in sorted(set(names) - {''}):
            remaining()
            if any(p in {'.git', 'logs', '.godot', 'bin', 'obj', 'reports', '__pycache__'} for p in PurePosixPath(name).parts):
                continue
            source = safe_file(root, name)
            if not source.is_file():
                continue
            data = source.read_bytes()
            target = safe_file(destination, name)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
            hashes[name] = hashlib.sha256(data).hexdigest()
    else:
        raise ValueError('Unknown runtime mode')
    digest = hashlib.sha256(json.dumps(hashes, sort_keys=True).encode()).hexdigest()
    manifest = {'mode': mode, 'source_revision': revision if mode == 'main' else 'workspace:' + digest,
                'files': hashes, 'snapshot_digest': digest}
    write_json(destination.parent / 'input-manifest.json', manifest)
    return manifest
