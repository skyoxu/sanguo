#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import datetime as dt
import hashlib
import json
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class FileFinding:
    path: str
    kind: str
    detail: str | None = None


def _today_ci_dir() -> Path:
    date = dt.date.today().strftime("%Y-%m-%d")
    return Path("logs") / "ci" / date / "text-integrity"


def _run_git(args: list[str]) -> str:
    p = subprocess.run(
        ["git", *args],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if p.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed (rc={p.returncode}): {p.stderr.strip()}")
    return p.stdout


def _list_staged_files() -> list[str]:
    out = _run_git(["diff", "--cached", "--name-only", "--diff-filter=ACMR"])
    return [ln.strip().replace("\\", "/") for ln in out.splitlines() if ln.strip()]


def _is_text_path(path: str) -> bool:
    # Keep conservative: only scan likely text files.
    p = Path(path)
    ext = p.suffix.lower()
    if ext in {
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
    }:
        return True
    # Also include extensionless git hook files.
    if p.name in {"pre-commit", "commit-msg"} and ext == "":
        return True
    return False


def _is_probably_semantic_garbled(text: str) -> bool:
    # Minimal, explainable heuristics:
    # - U+FFFD replacement char
    # - three-plus question mark runs (common substitution symptom)
    if "\ufffd" in text:
        return True
    if re.search(r"\?{3,}", text):
        return True
    # Common CJK mojibake punctuation when UTF-8 bytes were mis-decoded as GBK and re-saved.
    # These characters are valid Unicode, so we treat them as suspicious only when there are many.
    mojibake_cjk = ["锛", "銆", "鈥", "鈥", "鍙", "鎴", "绯"]
    if sum(text.count(ch) for ch in mojibake_cjk) >= 8:
        return True
    return False


def _scan_file(path: Path) -> list[FileFinding]:
    findings: list[FileFinding] = []
    data = path.read_bytes()
    try:
        text = data.decode("utf-8", errors="strict")
    except UnicodeDecodeError as e:
        findings.append(
            FileFinding(
                path=str(path).replace("\\", "/"),
                kind="utf8_decode_error",
                detail=str(e),
            )
        )
        return findings

    if "\ufeff" in text:
        findings.append(
            FileFinding(
                path=str(path).replace("\\", "/"),
                kind="bom_char_in_text",
                detail="contains U+FEFF",
            )
        )

    if "\ufffd" in text:
        findings.append(
            FileFinding(
                path=str(path).replace("\\", "/"),
                kind="replacement_char",
                detail=f"count={text.count('\ufffd')}",
            )
        )

    q_runs = len(re.findall(r"\?{3,}", text))
    if q_runs > 0:
        findings.append(
            FileFinding(
                path=str(path).replace("\\", "/"),
                kind="question_mark_run",
                detail=f"runs={q_runs}",
            )
        )

    # Extra: catch obvious mojibake tokens (still UTF-8-valid but semantically wrong)
    # NOTE: This is heuristic; do not hard-fail on it unless requested.
    mojibake_tokens = ["锟斤拷", "Ã", "Â", "â€™", "â€œ", "â€"]
    hit = [t for t in mojibake_tokens if t in text]
    if hit:
        findings.append(
            FileFinding(
                path=str(path).replace("\\", "/"),
                kind="mojibake_token",
                detail=",".join(hit),
            )
        )

    mojibake_cjk = ["锛", "銆", "鈥", "鍙", "鎴", "绯"]
    cjk_hits = {ch: text.count(ch) for ch in mojibake_cjk}
    cjk_total = sum(cjk_hits.values())
    if cjk_total >= 8:
        findings.append(
            FileFinding(
                path=str(path).replace("\\", "/"),
                kind="mojibake_cjk_punct",
                detail=json.dumps(cjk_hits, ensure_ascii=False),
            )
        )

    # Optional semantic check: header should not contain three-plus question mark runs
    head = "\n".join(text.splitlines()[:20])
    if _is_probably_semantic_garbled(head):
        findings.append(
            FileFinding(
                path=str(path).replace("\\", "/"),
                kind="header_suspicious",
                detail="first_20_lines",
            )
        )

    return findings


def main() -> int:
    import argparse

    ap = argparse.ArgumentParser(description="Check files for decode/BOM/garbled text patterns.")
    ap.add_argument("--out-dir", default=None, help="override output dir under logs/ci/<date>/...")
    ap.add_argument("--files", nargs="*", default=None, help="explicit repo-relative file list")
    ap.add_argument("--staged", action="store_true", help="scan staged files (git diff --cached)")
    ap.add_argument(
        "--hard-bom",
        action="store_true",
        help="treat BOM (U+FEFF) as hard failure for .json/.cs/.py/.gd/.txt/.yml/.yaml/.xml/.toml/.ini/.cfg/.tscn/.tres/.sln/.csproj/.gitignore/.gitattributes",
    )
    args = ap.parse_args()

    out_dir = Path(args.out_dir) if args.out_dir else _today_ci_dir()
    out_dir.mkdir(parents=True, exist_ok=True)

    targets: list[Path] = []
    if args.files:
        for f in args.files:
            f = str(f).strip().replace("\\", "/")
            if not f or not _is_text_path(f):
                continue
            targets.append(Path(f))
    elif args.staged:
        for f in _list_staged_files():
            if not _is_text_path(f):
                continue
            targets.append(Path(f))
    else:
        targets.append(Path(".taskmaster/docs/prd.txt"))
        targets.extend(Path(".taskmaster/tasks").glob("tasks*.json"))
        targets.extend(Path("docs/architecture/overlays/PRD-SANGUO-T2").rglob("*.md"))

    all_findings: list[FileFinding] = []
    hashed: dict[str, str] = {}
    for p in targets:
        if not p.exists() or not p.is_file():
            continue
        all_findings.extend(_scan_file(p))
        hashed[str(p).replace("\\", "/")] = hashlib.sha256(p.read_bytes()).hexdigest()

    report = {
        "ts": dt.datetime.now(dt.timezone.utc).isoformat(),
        "operation": "check_text_integrity",
        "targets_count": len(targets),
        "findings_count": len(all_findings),
        "findings": [f.__dict__ for f in all_findings],
        "sha256": hashed,
    }
    (out_dir / "summary.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    hard_kinds = {"utf8_decode_error", "replacement_char", "question_mark_run"}
    if args.hard_bom:
        hard_bom_exts = {
            ".json",
            ".cs",
            ".py",
            ".gd",
            ".txt",
            ".yml",
            ".yaml",
            ".xml",
            ".toml",
            ".ini",
            ".cfg",
            ".tscn",
            ".tres",
            ".sln",
            ".csproj",
            ".gitignore",
            ".gitattributes",
        }
        for f in all_findings:
            if f.kind != "bom_char_in_text":
                continue
            ext = Path(f.path).suffix.lower()
            if ext in hard_bom_exts:
                hard_kinds.add("bom_char_in_text")
                break
    hard = [f for f in all_findings if f.kind in hard_kinds]
    if hard:
        print(f"TEXT_INTEGRITY status=fail hard={len(hard)} out={out_dir}")
        return 2
    print(f"TEXT_INTEGRITY status=ok findings={len(all_findings)} out={out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
