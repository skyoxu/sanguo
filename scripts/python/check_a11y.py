#!/usr/bin/env python3
"""
Simple accessibility static checks for Godot UI scenes.
Scans .tscn under Game.Godot/Scenes and reports:
 - buttons_without_text: number of Button/OptionButton with empty text
 - labels_empty_text: number of Label with empty text
 - focusable_controls: count of controls setting focus_mode (approx via 'focus_mode =')

Usage:
  py -3 scripts/python/check_a11y.py --out logs/ci/<run_id>/a11y/summary.json
"""
import argparse
import json
import os
import re


def read_text(path: str) -> str:
    with open(path, 'r', encoding='utf-8', errors='ignore') as f:
        return f.read()


def scan_tscn(root: str):
    stats = {
        'scenes_scanned': 0,
        'buttons_without_text': 0,
        'labels_empty_text': 0,
        'focusable_controls': 0,
        'files': {}
    }
    btn_re = re.compile(r"\[node\s+name=\"[^\"]*\"\s+type=\"(Button|OptionButton)\".*?\n(?:[^\n]*\n)*?(?:text\s*=\s*\"(?P<txt>[^\"]*)\"|$)", re.DOTALL)
    lbl_re = re.compile(r"\[node\s+name=\"[^\"]*\"\s+type=\"Label\".*?\n(?:[^\n]*\n)*?(?:text\s*=\s*\"(?P<txt>[^\"]*)\"|$)", re.DOTALL)
    focus_re = re.compile(r"^focus_mode\s*=\s*", re.MULTILINE)

    for dirpath, _, filenames in os.walk(root):
        for fn in filenames:
            if not fn.endswith('.tscn'):
                continue
            path = os.path.join(dirpath, fn)
            txt = read_text(path)
            stats['scenes_scanned'] += 1
            fstats = {'buttons_without_text': 0, 'labels_empty_text': 0, 'focusable_controls': 0}

            for m in btn_re.finditer(txt):
                t = (m.group('txt') or '').strip()
                if t == '':
                    fstats['buttons_without_text'] += 1

            for m in lbl_re.finditer(txt):
                t = (m.group('txt') or '').strip()
                if t == '':
                    fstats['labels_empty_text'] += 1

            fstats['focusable_controls'] += len(focus_re.findall(txt))

            for k, v in fstats.items():
                stats[k] += v
            stats['files'][os.path.relpath(path)] = fstats
    return stats


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', required=True, help='Output JSON path for summary')
    args = ap.parse_args()

    project_scenes = os.path.join(os.getcwd(), 'Game.Godot', 'Scenes')
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    if not os.path.isdir(project_scenes):
        summary = {'error': 'Scenes directory not found', 'path': project_scenes}
        with open(args.out, 'w', encoding='utf-8') as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)
        print('A11Y_SUMMARY_OUT=' + args.out)
        return 0

    stats = scan_tscn(project_scenes)
    with open(args.out, 'w', encoding='utf-8') as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)
    print('A11Y_SUMMARY_OUT=' + args.out)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

