import argparse
import json
import os
import re
from datetime import datetime


MOJIBAKE_RE = re.compile(
    r"[\u95c1\u95bb\u941f\u9357\u9227\u7f02\u6fde\u95b8\u93ae\u7ef1\u951b\u7ed7\u95bf\u934a\u93af\u7f01\u5a75]"
)
ALLOWED_EXTS = {'.md', '.txt', '.yml', '.yaml', '.json', '.xml', '.ini', '.cfg', '.index', '.adoc'}


def scan_file(path: str):
    try:
        with open(path, 'rb') as f:
            raw = f.read()
        # strict UTF-8 decode to surface decode errors
        text = raw.decode('utf-8', errors='strict')
    except Exception as e:
        return {
            'file': path,
            'error': f'decode_error: {type(e).__name__}: {e}',
            'suspected': True,
            'has_fffd': False,
            'mojibake_hits': 0,
            'lines': []
        }

    has_fffd = '\uFFFD' in text
    hits = 0
    lines = []
    for i, line in enumerate(text.splitlines(), start=1):
        if MOJIBAKE_RE.search(line):
            hits += 1
            if len(lines) < 8:
                # keep a short preview line
                lines.append({'line': i, 'text': line[:400]})

    suspected = has_fffd or hits > 0
    return {
        'file': path,
        'error': None,
        'suspected': bool(suspected),
        'has_fffd': bool(has_fffd),
        'mojibake_hits': int(hits),
        'lines': lines,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--root', default='docs', help='Root directory to scan (default: docs)')
    ap.add_argument('--out', default=None, help='Output directory for logs (default: logs/ci/<ts>/garble-scan)')
    args = ap.parse_args()

    root = os.path.abspath(args.root)
    results = []
    for dirpath, _, filenames in os.walk(root):
        for name in filenames:
            ext = os.path.splitext(name)[1].lower()
            if ext not in ALLOWED_EXTS:
                continue
            path = os.path.join(dirpath, name)
            results.append(scan_file(path))

    ts = datetime.now().strftime('%Y%m%d-%H%M%S')
    out = args.out or os.path.join('logs', 'ci', ts, 'garble-scan')
    os.makedirs(out, exist_ok=True)
    with open(os.path.join(out, 'summary.json'), 'w', encoding='utf-8') as f:
        json.dump({'ts': ts, 'root': root, 'files': results}, f, ensure_ascii=False, indent=2)

    # also provide a compact list for quick read
    suspected = [r for r in results if r['suspected']]
    suspected.sort(key=lambda r: (r['mojibake_hits'], r['file']), reverse=True)
    with open(os.path.join(out, 'suspected.txt'), 'w', encoding='utf-8') as f:
        for r in suspected:
            f.write(f"{r['file']} | hits={r['mojibake_hits']} | fffd={r['has_fffd']}\n")
            for ln in r['lines'][:3]:
                f.write(f"  [{ln['line']}] {ln['text']}\n")
            f.write('\n')

    print(f"Scanned {len(results)} files under {root}. Suspected: {len(suspected)}. Logs: {out}")


if __name__ == '__main__':
    main()
