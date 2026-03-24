#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Hard gate for repository text integrity on critical paths.

Checks:
1) UTF-8 strict decode (no decode errors)
2) No UTF-8 BOM
3) No semantic-level garbled/mojibake indicators

Default scan roots:
  - docs
  - .github
  - .taskmaster

Also scans key root files when present:
  - AGENTS.md
  - README.md
  - project.godot
  - .gitignore
  - .gitattributes

Output:
  logs/ci/<YYYY-MM-DD>/docs-utf8-gate/summary.json
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
from pathlib import Path
from typing import Any


# Suspicious signals with low false-positive risk for this repo.
FFFD_RE = re.compile("\uFFFD")
CN_BREAK_Q_RE = re.compile(r"[\u4e00-\u9fff]\?[\u4e00-\u9fff]")
MULTI_Q_RE = re.compile(r"\?{3,}")
CP1252_MOJIBAKE_RE = re.compile(r"â[€™œž“”–—]")

MOJIBAKE_TOKENS = (
    "锟斤拷",
    "茂禄驴",
    "闂侀柣閻熼崡閳",
    "芒鈧",
    "Ã",
    "Â",
    "Ð",
    "Ñ",
)

# Potentially-garbled CJK glyph cluster used only by ratio gate (high threshold).
MIXED_MOJIBAKE_GLYPHS = "鈥銆鍙鍔鎴浠绗鏂寮缁瀛闂閿璇锛鍚璁鍙"

DEFAULT_ROOTS = ["docs", ".github", ".taskmaster"]
DEFAULT_ROOT_FILES = ["AGENTS.md", "README.md", "project.godot", ".gitignore", ".gitattributes"]

# Known fixture intentionally contains bad encoding signal for gate verification.
DEFAULT_ALLOWLIST = [
    "docs/architecture/base/ZZZ-encoding-fixture-bad.md",
]

SKIP_DIR_NAMES = {
    ".git",
    ".godot",
    "node_modules",
    "bin",
    "obj",
    "logs",
    "TestResults",
    "__pycache__",
}

TEXT_EXTENSIONS = {
    ".md",
    ".txt",
    ".json",
    ".yml",
    ".yaml",
    ".xml",
    ".toml",
    ".ini",
    ".cfg",
    ".index",
    ".feature",
    ".py",
    ".ps1",
    ".cs",
    ".csproj",
    ".sln",
    ".gd",
    ".tscn",
    ".tres",
    ".editorconfig",
}

TEXT_FILE_NAMES = {
    ".gitignore",
    ".gitattributes",
    "Dockerfile",
    "Makefile",
    "AGENTS.md",
    "README.md",
}


def _today_str() -> str:
    return dt.date.today().strftime("%Y-%m-%d")


def _to_posix(path: Path) -> str:
    return str(path).replace("\\", "/")


def _safe_sample(text: str, *, max_chars: int = 180) -> str:
    line = text.replace("\n", " ").strip()
    if len(line) <= max_chars:
        return line
    return line[: max_chars - 3] + "..."


def _count_cjk(text: str) -> int:
    return sum(1 for ch in text if "\u4e00" <= ch <= "\u9fff")


def _semantic_garbled_reasons(text: str) -> list[str]:
    reasons: list[str] = []

    if FFFD_RE.search(text):
        reasons.append("replacement_char_fffd")
    if CN_BREAK_Q_RE.search(text):
        reasons.append("cjk_broken_by_question_mark")
    if MULTI_Q_RE.search(text):
        reasons.append("multi_question_marks")
    if CP1252_MOJIBAKE_RE.search(text):
        reasons.append("cp1252_mojibake_punctuation")

    token_hits = [token for token in MOJIBAKE_TOKENS if token in text]
    if token_hits:
        reasons.append("mojibake_tokens:" + ",".join(token_hits[:4]))

    cjk_total = _count_cjk(text)
    if cjk_total > 0:
        mixed_count = sum(text.count(ch) for ch in set(MIXED_MOJIBAKE_GLYPHS))
        mixed_ratio = mixed_count / cjk_total
        if mixed_count >= 24 and mixed_ratio >= 0.18:
            reasons.append(f"mojibake_glyph_ratio:{mixed_count}/{cjk_total}")

    return reasons


def _scan_file(path: Path) -> dict[str, Any]:
    result: dict[str, Any] = {
        "path": _to_posix(path),
        "utf8_ok": False,
        "has_bom": False,
        "semantic_garbled": False,
        "reasons": [],
        "error": None,
        "sample": "",
    }

    try:
        raw = path.read_bytes()
        result["has_bom"] = raw.startswith(b"\xef\xbb\xbf")
        text = raw.decode("utf-8", errors="strict")
        result["utf8_ok"] = True
        reasons = _semantic_garbled_reasons(text)
        result["reasons"] = reasons
        result["semantic_garbled"] = len(reasons) > 0
        if reasons:
            result["sample"] = _safe_sample(text)
    except UnicodeDecodeError as exc:
        result["error"] = f"UnicodeDecodeError: {exc}"
    except Exception as exc:  # noqa: BLE001
        result["error"] = str(exc)

    return result


def _collect_targets(repo_root: Path, roots: list[str]) -> list[Path]:
    files: set[Path] = set()

    for rel_root in roots:
        rel_root = rel_root.strip()
        if not rel_root:
            continue
        target = (repo_root / rel_root).resolve()
        if not target.exists():
            continue
        if target.is_file():
            files.add(target)
            continue
        for item in target.rglob("*"):
            if not item.is_file():
                continue
            if any(part in SKIP_DIR_NAMES for part in item.parts):
                continue
            suffix = item.suffix.lower()
            if suffix not in TEXT_EXTENSIONS and item.name not in TEXT_FILE_NAMES:
                continue
            files.add(item.resolve())

    for rel_file in DEFAULT_ROOT_FILES:
        candidate = (repo_root / rel_file).resolve()
        if candidate.exists() and candidate.is_file():
            files.add(candidate)

    return sorted(files, key=lambda p: _to_posix(p).lower())


def _normalize_allowlist(repo_root: Path, allowlist_items: list[str]) -> set[str]:
    out: set[str] = set()
    for item in allowlist_items:
        text = str(item or "").strip()
        if not text:
            continue
        abs_path = (repo_root / text).resolve()
        out.add(_to_posix(abs_path))
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description="Hard gate: UTF-8/no-BOM/no-garbled on critical text paths.")
    parser.add_argument(
        "--roots",
        nargs="*",
        default=DEFAULT_ROOTS,
        help="Relative roots/files to scan. Default includes docs/.github/.taskmaster/scripts.",
    )
    parser.add_argument("--out", default="", help="Optional output summary path")
    parser.add_argument("--max-print", type=int, default=12, help="Max failing entries to print")
    parser.add_argument(
        "--allow",
        nargs="*",
        default=DEFAULT_ALLOWLIST,
        help="Relative files to allowlist from failure set",
    )
    args = parser.parse_args()

    repo_root = Path.cwd().resolve()
    targets = _collect_targets(repo_root, list(args.roots or []))
    allowlist = _normalize_allowlist(repo_root, list(args.allow or []))

    scanned: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []

    for file_path in targets:
        item = _scan_file(file_path)
        scanned.append(item)

        failed = (not item.get("utf8_ok")) or bool(item.get("has_bom")) or bool(item.get("semantic_garbled"))
        if not failed:
            continue

        if item["path"] in allowlist:
            item["allowlisted"] = True
            continue

        failures.append(item)

    date = _today_str()
    default_out = Path("logs") / "ci" / date / "docs-utf8-gate" / "summary.json"
    out_path = Path(args.out) if args.out else default_out
    out_path.parent.mkdir(parents=True, exist_ok=True)

    summary: dict[str, Any] = {
        "ts": dt.datetime.now(dt.timezone.utc).isoformat(),
        "action": "utf8-bom-garbled-gate",
        "reason": "enforce utf8-without-bom and semantic-garbled free critical text paths",
        "roots": list(args.roots or []),
        "allowlist": sorted(allowlist),
        "caller": "python-check_docs_utf8_integrity",
        "scanned": len(scanned),
        "failed": len(failures),
        "failed_paths": [x["path"] for x in failures],
        "results": scanned,
    }

    out_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    status = "ok" if len(failures) == 0 else "fail"
    print(
        f"DOCS_UTF8_GATE status={status} scanned={len(scanned)} failed={len(failures)} "
        f"out={_to_posix(out_path)}"
    )

    if failures:
        for item in failures[: max(1, int(args.max_print))]:
            print(
                " - "
                f"path={item.get('path')} utf8_ok={item.get('utf8_ok')} bom={item.get('has_bom')} "
                f"reasons={';'.join(item.get('reasons') or []) or '-'} error={item.get('error') or '-'}"
            )

    return 0 if len(failures) == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
