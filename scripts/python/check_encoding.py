#!/usr/bin/env python3
"""
Check text files for UTF-8 decode errors and common mojibake/garbled patterns.

Results are written under:
  logs/ci/<YYYY-MM-DD>/encoding/session-details.json
  logs/ci/<YYYY-MM-DD>/encoding/session-summary.json

Usage (Windows):
  py -3 scripts/python/check_encoding.py --since-today
  py -3 scripts/python/check_encoding.py --since "2025-11-13 00:00:00"
  py -3 scripts/python/check_encoding.py --files path1 path2 ...
  py -3 scripts/python/check_encoding.py --root docs
"""

from __future__ import annotations

import argparse
import datetime as dt
import io
import json
import os
import re
import subprocess
import sys
from typing import Iterable, List


TEXT_EXT = {
    ".md",
    ".txt",
    ".json",
    ".yml",
    ".yaml",
    ".xml",
    ".cs",
    ".csproj",
    ".sln",
    ".gd",
    ".tscn",
    ".tres",
    ".gitattributes",
    ".gitignore",
    ".ps1",
    ".py",
    ".ini",
    ".cfg",
    ".toml",
}

# Explicit binary extensions to skip from UTF-8 validation
BINARY_EXT = {
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".bmp",
    ".ico",
    ".webp",
    ".ogg",
    ".wav",
    ".mp3",
    ".mp4",
    ".avi",
    ".mov",
    ".zip",
    ".7z",
    ".rar",
    ".gz",
    ".tar",
    ".tgz",
    ".dll",
    ".exe",
    ".pdb",
    ".pck",
    ".import",
    ".ttf",
    ".otf",
    ".db",
    ".sqlite",
    ".sav",
    ".bak",
}

# Exclude vendor/test asset folders and known binaries
EXCLUDE_SUBSTRINGS = [
    "Tests.Godot/addons/gdUnit4/src/core/assets/",
    "Tests.Godot/addons/gdUnit4/src/update/assets/",
    "Tests.Godot/addons/gdUnit4/src/reporters/html/template/css/",
    "Tests.Godot/addons/gdUnit4/src/ui/settings/",
    "gitlog/export-logs.zip",
]

# Mojibake/garble indicators (heuristic, not a proof).
MOJIBAKE_REGEXES = [
    ("FFFD_REPLACEMENT", re.compile("\uFFFD")),
    ("CJK_MOJIBAKE", re.compile(r"[闁閻鐟鍗鈧缂濞閸鎮绱锛绗閿鍊鎯缁婵锟斤拷]")),
    ("CP1252_PUNCT", re.compile(r"(?:â€™|â€œ|â€�|â€”|â€˜|â€¢|â€¦|â„¢)")),
    ("BOM_AS_TEXT", re.compile(r"ï»¿")),
]

CONTROL_CHARS_RE = re.compile(r"[\x00-\x08\x0B\x0C\x0E-\x1F]")


def run_cmd(args: List[str]) -> str:
    p = subprocess.Popen(
        args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="ignore"
    )
    out, _ = p.communicate()
    return out


def git_changed_since(since: str) -> List[str]:
    out = run_cmd(["git", "log", f"--since={since}", "--name-only", "--pretty=format:"])
    files = [ln.strip() for ln in out.splitlines() if ln.strip() and not ln.startswith(" ")]
    return sorted(set(files))


def git_changed_today() -> List[str]:
    today = dt.date.today().strftime("%Y-%m-%d")
    return git_changed_since(today + " 00:00:00")


def is_text_file(path: str) -> bool:
    _, ext = os.path.splitext(path)
    ext = ext.lower()
    norm = path.replace("\\", "/")
    if any(s in norm for s in EXCLUDE_SUBSTRINGS):
        return False
    if ext in BINARY_EXT:
        return False
    if ext in TEXT_EXT:
        return True
    # Heuristic: treat small unknown files as text, larger files as likely binary.
    try:
        sz = os.path.getsize(path)
        return sz < 128 * 1024
    except Exception:
        return False


def iter_files_under(root_dir: str) -> List[str]:
    root_dir = os.path.abspath(root_dir)
    out: List[str] = []
    for dirpath, _, filenames in os.walk(root_dir):
        for name in filenames:
            path = os.path.join(dirpath, name)
            if os.path.isfile(path) and is_text_file(path):
                out.append(path)
    return sorted(set(out))


def _summarize_hits(matches: Iterable[str], limit: int = 5) -> str:
    uniq: List[str] = []
    for m in matches:
        if m not in uniq:
            uniq.append(m)
        if len(uniq) >= limit:
            break
    return ",".join(uniq)


def check_utf8(path: str) -> dict:
    result = {
        "path": path,
        "utf8_ok": False,
        "has_bom": False,
        "mojibake_hits": [],
        "error": None,
    }
    try:
        raw = io.open(path, "rb").read()
        result["has_bom"] = raw.startswith(b"\xef\xbb\xbf")
        text = raw.decode("utf-8", errors="strict")
        result["utf8_ok"] = True

        hits_summary: List[str] = []
        for name, rx in MOJIBAKE_REGEXES:
            matches = rx.findall(text)
            if not matches:
                continue
            samples = _summarize_hits(matches)
            hits_summary.append(f"{name}:{len(matches)}:{samples}" if samples else f"{name}:{len(matches)}")

        ctrl = CONTROL_CHARS_RE.findall(text)
        if ctrl:
            hits_summary.append(f"CONTROL_CHARS:{len(ctrl)}")

        if hits_summary:
            result["mojibake_hits"] = hits_summary
    except UnicodeDecodeError as e:
        result["error"] = f"UnicodeDecodeError: {e}"
    except Exception as e:
        result["error"] = str(e)
    return result


def _filter_existing_files(paths: Iterable[str]) -> List[str]:
    out = []
    for p in paths:
        if os.path.isfile(p) and is_text_file(p):
            out.append(p)
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--since-today", action="store_true")
    ap.add_argument("--since", default=None)
    ap.add_argument("--files", nargs="*")
    ap.add_argument("--root", default=None, help="Scan all text files under a directory (overrides --since/--files)")
    args = ap.parse_args()

    if args.root:
        files = iter_files_under(args.root)
    elif args.files:
        files = _filter_existing_files(args.files)
    elif args.since:
        files = _filter_existing_files(git_changed_since(args.since))
    else:
        files = _filter_existing_files(git_changed_today())

    date = dt.date.today().strftime("%Y-%m-%d")
    out_dir = os.path.join("logs", "ci", date, "encoding")
    os.makedirs(out_dir, exist_ok=True)

    results = []
    bad = []
    for fpath in files:
        r = check_utf8(fpath)
        results.append(r)
        if not r["utf8_ok"]:
            bad.append(r)

    summary = {
        "scanned": len(results),
        "bad": len(bad),
        "bad_paths": [b["path"] for b in bad],
        "mojibake_paths": [r["path"] for r in results if r.get("mojibake_hits")],
        "generated": dt.datetime.now().isoformat(),
    }

    with io.open(os.path.join(out_dir, "session-details.json"), "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    with io.open(os.path.join(out_dir, "session-summary.json"), "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    print(f"ENCODING_CHECK scanned={summary['scanned']} bad={summary['bad']} out={out_dir}")
    return 0 if summary["bad"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())

