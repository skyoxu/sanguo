#!/usr/bin/env python3
"""Capture repeatable browser evidence for the local Project Health pages."""
from __future__ import annotations

import argparse
import subprocess
from datetime import date
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--url', required=True)
    parser.add_argument('--output', default='')
    args = parser.parse_args()
    output = Path(args.output or f'logs/ci/{date.today().isoformat()}/knowledge-browser')
    output.mkdir(parents=True, exist_ok=True)
    checks = [
        ('desktop', args.url + '/knowledge/', 'Desktop Chrome', output / 'desktop.png'),
        ('scene-composition', args.url + '/knowledge/scenes', 'Desktop Chrome', output / 'scene-composition.png'),
        ('mobile-unreachable', args.url + '/knowledge/scenes/unreachable', None, output / 'mobile-unreachable.png'),
    ]
    for name, url, device, target in checks:
        command = ['npx.cmd', '--yes', 'playwright', 'screenshot']
        command += [f'--device={device}'] if device else ['--viewport-size=390,844']
        command += [url, str(target)]
        result = subprocess.run(command, capture_output=True, text=True, encoding='utf-8')
        if result.returncode:
            print(f'{name}: failed: {result.stderr.strip()[-1000:]}')
            return result.returncode
        print(f'{name}: {target}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
