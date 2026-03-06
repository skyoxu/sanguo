#!/usr/bin/env python3
"""
Hard gate: forbid newly-added manual command examples that chain legacy sc scripts.

Policy:
- Task-level workflow must use:
  py -3 scripts/sc/run_review_pipeline.py --task-id <id>
- Do not add new doc command examples that directly call:
  scripts/sc/test.py
  scripts/sc/acceptance_check.py
  scripts/sc/llm_review.py

Default behavior scans only *newly added lines* in current git changes.
Whitelist can be used to allow specific legacy docs.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable

from _whitelist_metadata import normalize_rel, parse_whitelist


DOC_EXTS = {".md", ".txt", ".rst", ".adoc"}
EXCLUDE_DIR_NAMES = {
    ".git",
    ".godot",
    "bin",
    "obj",
    "logs",
    "node_modules",
    ".taskmaster",
}

FORBIDDEN_PATTERNS: dict[str, re.Pattern[str]] = {
    "sc-test": re.compile(r"\b(?:py(?:thon)?(?:\s+-3)?|python)\s+scripts/sc/test\.py\b", re.IGNORECASE),
    "sc-acceptance-check": re.compile(r"\b(?:py(?:thon)?(?:\s+-3)?|python)\s+scripts/sc/acceptance_check\.py\b", re.IGNORECASE),
    "sc-llm-review": re.compile(r"\b(?:py(?:thon)?(?:\s+-3)?|python)\s+scripts/sc/llm_review\.py\b", re.IGNORECASE),
}


@dataclass(frozen=True)
class Hit:
    file: str
    line: int
    rule: str
    excerpt: str


HUNK_RE = re.compile(r"^@@\s*-[0-9]+(?:,[0-9]+)?\s+\+([0-9]+)(?:,([0-9]+))?\s*@@")


def _today() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def _write_utf8(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def _run_git(root: Path, args: list[str]) -> tuple[int, str]:
    cmd = ["git", "-C", str(root), *args]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="ignore", check=False)
    except Exception:
        return 2, ""
    return int(proc.returncode), (proc.stdout or "")


def _inside_git_repo(root: Path) -> bool:
    rc, out = _run_git(root, ["rev-parse", "--is-inside-work-tree"])
    return rc == 0 and out.strip().lower() == "true"


def _candidate_doc(path: Path) -> bool:
    return path.is_file() and path.suffix.lower() in DOC_EXTS


def _is_excluded_rel(rel: str) -> bool:
    parts = [part for part in rel.replace("\\", "/").split("/") if part]
    return any(part in EXCLUDE_DIR_NAMES for part in parts)


def _parse_changed_paths_from_status(root: Path) -> list[str]:
    rc, out = _run_git(root, ["status", "--porcelain"])
    if rc != 0:
        return []
    paths: list[str] = []
    for raw in out.splitlines():
        line = raw.rstrip("\r\n")
        if len(line) < 4:
            continue
        body = line[3:].strip()
        if " -> " in body:
            body = body.split(" -> ", 1)[1].strip()
        rel = normalize_rel(body)
        if rel:
            paths.append(rel)
    seen: set[str] = set()
    unique: list[str] = []
    for rel in paths:
        if rel in seen:
            continue
        seen.add(rel)
        unique.append(rel)
    return unique


def _added_lines_from_diff_text(diff_text: str) -> list[tuple[int, str]]:
    out: list[tuple[int, str]] = []
    new_line_no = 0
    for raw in diff_text.splitlines():
        line = raw.rstrip("\n")
        m = HUNK_RE.match(line)
        if m:
            new_line_no = int(m.group(1))
            continue
        if line.startswith("+++ ") or line.startswith("--- "):
            continue
        if line.startswith("+"):
            out.append((new_line_no, line[1:]))
            new_line_no += 1
            continue
        if line.startswith("-"):
            continue
        if line.startswith(" "):
            new_line_no += 1
    return out


def _added_lines_for_path(root: Path, rel_path: str) -> list[tuple[int, str]]:
    added: list[tuple[int, str]] = []
    for extra in ([], ["--cached"]):
        rc, out = _run_git(root, [*extra, "diff", "--unified=0", "--", rel_path])
        if rc != 0:
            continue
        added.extend(_added_lines_from_diff_text(out))
    seen: set[tuple[int, str]] = set()
    uniq: list[tuple[int, str]] = []
    for item in added:
        if item in seen:
            continue
        seen.add(item)
        uniq.append(item)
    return uniq


def _all_lines(path: Path) -> list[tuple[int, str]]:
    rows: list[tuple[int, str]] = []
    for idx, line in enumerate(path.read_text(encoding="utf-8", errors="ignore").splitlines(), 1):
        rows.append((idx, line))
    return rows


def _scan_lines(rel_path: str, lines: Iterable[tuple[int, str]]) -> list[Hit]:
    hits: list[Hit] = []
    for line_no, text in lines:
        excerpt = text.strip()
        if not excerpt:
            continue
        for rule, pattern in FORBIDDEN_PATTERNS.items():
            if pattern.search(text):
                clipped = excerpt if len(excerpt) <= 240 else (excerpt[:240] + "...")
                hits.append(Hit(file=rel_path, line=int(line_no), rule=rule, excerpt=clipped))
    return hits


def _scan_diff_mode(root: Path, whitelist: set[str]) -> tuple[int, int, list[Hit]]:
    scanned = 0
    hits: list[Hit] = []
    for rel in _parse_changed_paths_from_status(root):
        path = root / rel
        if rel in whitelist or _is_excluded_rel(rel):
            continue
        if not _candidate_doc(path):
            continue
        scanned += 1
        if not path.exists():
            continue
        added = _added_lines_for_path(root, rel)
        if added:
            hits.extend(_scan_lines(rel, added))
        else:
            hits.extend(_scan_lines(rel, _all_lines(path)))
    return scanned, len(hits), hits


def _scan_all_mode(root: Path, whitelist: set[str]) -> tuple[int, int, list[Hit]]:
    scanned = 0
    hits: list[Hit] = []
    for path in root.rglob("*"):
        if not _candidate_doc(path):
            continue
        rel = normalize_rel(str(path.relative_to(root)))
        if rel in whitelist or _is_excluded_rel(rel):
            continue
        scanned += 1
        hits.extend(_scan_lines(rel, _all_lines(path)))
    return scanned, len(hits), hits


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Hard gate: forbid newly-added manual sc triplet command examples.")
    parser.add_argument("--root", default=".", help="Repo root path.")
    parser.add_argument("--mode", default="diff", choices=["diff", "all"], help="Scan mode: diff (default) or all.")
    parser.add_argument(
        "--whitelist",
        default="docs/workflows/unified-pipeline-command-whitelist.txt",
        help="Whitelist file (repo-relative).",
    )
    parser.add_argument(
        "--whitelist-metadata",
        default="off",
        choices=["off", "warn", "require"],
        help="Whitelist metadata policy: off|warn|require.",
    )
    args = parser.parse_args(argv)

    root = Path(args.root).resolve()
    whitelist_path = (root / str(args.whitelist)).resolve()
    whitelist_mode = str(args.whitelist_metadata).strip().lower()
    whitelist, whitelist_entries, whitelist_issues = parse_whitelist(whitelist_path, metadata_mode=whitelist_mode)

    out_dir = root / "logs" / "ci" / _today()
    out_dir.mkdir(parents=True, exist_ok=True)
    out_json = out_dir / "forbid-manual-sc-triplet-examples.json"
    out_txt = out_dir / "forbid-manual-sc-triplet-examples.txt"

    mode = str(args.mode).strip().lower()
    if mode == "diff" and not _inside_git_repo(root):
        mode = "all"

    if mode == "diff":
        scanned_files, hits_count, hits = _scan_diff_mode(root, whitelist)
    else:
        scanned_files, hits_count, hits = _scan_all_mode(root, whitelist)

    metadata_error_count = sum(1 for issue in whitelist_issues if issue.severity == "error")
    metadata_warn_count = sum(1 for issue in whitelist_issues if issue.severity == "warn")
    ok = hits_count == 0 and metadata_error_count == 0

    report: dict[str, object] = {
        "ok": ok,
        "mode": mode,
        "root": normalize_rel(str(root)),
        "scanned_files": scanned_files,
        "hits_count": hits_count,
        "hits": [h.__dict__ for h in hits],
        "whitelist_file": normalize_rel(str(whitelist_path.relative_to(root))) if whitelist_path.exists() else None,
        "whitelist_count": len(whitelist),
        "whitelist_metadata_mode": whitelist_mode,
        "whitelist_entries": whitelist_entries,
        "whitelist_issues_count": len(whitelist_issues),
        "whitelist_issue_error_count": metadata_error_count,
        "whitelist_issue_warn_count": metadata_warn_count,
        "whitelist_issues": [issue.__dict__ for issue in whitelist_issues],
        "forbidden_rules": list(FORBIDDEN_PATTERNS.keys()),
        "policy": "Use scripts/sc/run_review_pipeline.py as the single task-level entrypoint.",
        "repair": [
            "Replace manual examples with: py -3 scripts/sc/run_review_pipeline.py --task-id <id>",
            "If a legacy guide must keep old commands, whitelist with path|owner|expire_date|reason.",
        ],
    }

    _write_utf8(out_json, json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    if ok:
        _write_utf8(
            out_txt,
            f"OK: no forbidden manual sc triplet command examples detected (mode={mode}); "
            f"whitelist_issues={len(whitelist_issues)} metadata_mode={whitelist_mode}.\n",
        )
    else:
        lines: list[str] = [f"FAIL: forbidden manual sc triplet command examples detected (mode={mode}).", ""]
        for h in hits:
            lines.append(f"{h.file}:{h.line} [{h.rule}] {h.excerpt}")
        if whitelist_issues:
            lines.extend(["", "Whitelist issues:"])
            for issue in whitelist_issues:
                lines.append(
                    f"line={issue.line} severity={issue.severity} code={issue.code} "
                    f"message={issue.message} raw={issue.raw}"
                )
        lines.extend(
            [
                "",
                "Repair:",
                "- Replace manual examples with: py -3 scripts/sc/run_review_pipeline.py --task-id <id>",
                "- Keep only temporary whitelist entries with owner + expire_date + reason.",
                "",
            ]
        )
        _write_utf8(out_txt, "\n".join(lines))

    status = "OK" if ok else "FAIL"
    print(
        f"forbid_manual_sc_triplet_examples: {status} hits={hits_count} scanned={scanned_files} mode={mode} "
        f"metadata_mode={whitelist_mode} metadata_errors={metadata_error_count} metadata_warns={metadata_warn_count}"
    )
    print(f"report={out_json.as_posix()}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())

