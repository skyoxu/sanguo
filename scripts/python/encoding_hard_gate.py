#!/usr/bin/env python3
"""Hard CI gate for UTF-8/BOM/mojibake checks.

Scope (default):
  - docs/**
  - .github/**
  - .taskmaster/** (optional when folder is missing)
  - AGENTS.md

The gate fails when any scanned file has:
  - non-UTF-8 bytes
  - UTF-8 BOM
  - semantic garble indicators (mojibake heuristics)
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable


UTF8_BOM = b"\xef\xbb\xbf"
DEFAULT_TARGETS = ("docs", ".github", ".taskmaster", "AGENTS.md")
OPTIONAL_MISSING_TARGETS = {".taskmaster"}
ALLOWLIST_REL_PATHS = {
    "docs/architecture/base/ZZZ-encoding-fixture-bad.md",
}

CONTROL_CHARS_RE = re.compile(r"[\x00-\x08\x0B\x0C\x0E-\x1F]")

MOJIBAKE_RULES: list[tuple[str, re.Pattern[str]]] = [
    ("replacement_char", re.compile("\uFFFD")),
    ("latin1_utf8_mix", re.compile(r"(?:Ã.|Â.|â€™|â€œ|â€|ï»¿)")),
    ("gbk_token", re.compile(r"锟斤拷")),
    (
        "cjk_mojibake_cluster",
        re.compile(r"[闂侀柣閻熼崡閳х紓婵為柛閹槐閿涚粭闁块崐閹紒濠礭]{2,}"),
    ),
]


@dataclass(frozen=True)
class Violation:
    path: str
    kind: str
    message: str
    sample: str | None = None


def to_posix(path: Path) -> str:
    return str(path).replace("\\", "/")


def read_text_strict(path: Path) -> tuple[str | None, str | None, bool]:
    raw = path.read_bytes()
    has_bom = raw.startswith(UTF8_BOM)
    try:
        text = raw.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        return None, f"UnicodeDecodeError: {exc}", has_bom
    return text, None, has_bom


def summarize_line_hits(text: str, rx: re.Pattern[str], *, max_lines: int = 3) -> str | None:
    samples: list[str] = []
    for idx, line in enumerate(text.splitlines(), start=1):
        if rx.search(line):
            preview = line.strip()
            if len(preview) > 160:
                preview = preview[:160] + "..."
            samples.append(f"L{idx}:{preview}")
            if len(samples) >= max_lines:
                break
    return " | ".join(samples) if samples else None


def iter_target_files(repo_root: Path, targets: Iterable[str]) -> tuple[list[Path], list[Violation]]:
    files: list[Path] = []
    violations: list[Violation] = []

    for raw_target in targets:
        target = raw_target.strip()
        if not target:
            continue

        path = (repo_root / target).resolve()
        rel = to_posix(Path(target))

        if not path.exists():
            if target in OPTIONAL_MISSING_TARGETS:
                continue
            violations.append(
                Violation(
                    path=rel,
                    kind="missing_required_path",
                    message=f"Required path does not exist: {rel}",
                )
            )
            continue

        if path.is_file():
            files.append(path)
            continue

        for child in path.rglob("*"):
            if child.is_file():
                files.append(child)

    uniq = sorted(set(files), key=lambda p: to_posix(p.relative_to(repo_root)))
    return uniq, violations


def is_allowlisted(repo_root: Path, path: Path) -> bool:
    rel = to_posix(path.relative_to(repo_root))
    return rel in ALLOWLIST_REL_PATHS


def validate_file(repo_root: Path, path: Path) -> list[Violation]:
    rel = to_posix(path.relative_to(repo_root))
    violations: list[Violation] = []

    text, decode_error, has_bom = read_text_strict(path)
    if decode_error is not None:
        violations.append(Violation(path=rel, kind="not_utf8", message=decode_error))
        return violations

    assert text is not None

    if has_bom:
        violations.append(
            Violation(
                path=rel,
                kind="utf8_bom",
                message="UTF-8 BOM is forbidden",
            )
        )

    ctrl_matches = CONTROL_CHARS_RE.findall(text)
    if ctrl_matches:
        violations.append(
            Violation(
                path=rel,
                kind="control_chars",
                message=f"Found {len(ctrl_matches)} control chars",
            )
        )

    for kind, rx in MOJIBAKE_RULES:
        if not rx.search(text):
            continue
        sample = summarize_line_hits(text, rx)
        violations.append(
            Violation(
                path=rel,
                kind=f"mojibake_{kind}",
                message=f"Matched mojibake rule: {kind}",
                sample=sample,
            )
        )

    return violations


def build_out_dir(repo_root: Path, custom: str | None) -> Path:
    if custom:
        out = (repo_root / custom).resolve()
    else:
        today = dt.date.today().strftime("%Y-%m-%d")
        out = (repo_root / "logs" / "ci" / today / "encoding-hard-gate").resolve()
    out.mkdir(parents=True, exist_ok=True)
    return out


def write_reports(out_dir: Path, *, scanned: int, targets: list[str], violations: list[Violation]) -> None:
    summary = {
        "generated_at": dt.datetime.now(dt.UTC).isoformat(),
        "scanned_files": scanned,
        "targets": targets,
        "allowlist_paths": sorted(ALLOWLIST_REL_PATHS),
        "violations": len(violations),
        "status": "fail" if violations else "ok",
    }
    details = [asdict(v) for v in violations]

    (out_dir / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (out_dir / "violations.json").write_text(json.dumps(details, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    lines: list[str] = []
    lines.append(f"ENCODING_HARD_GATE status={summary['status']} scanned={scanned} violations={len(violations)}")
    lines.append(f"OUT={to_posix(out_dir)}")
    for v in violations[:120]:
        line = f"{v.path} | {v.kind} | {v.message}"
        if v.sample:
            line += f" | {v.sample}"
        lines.append(line)
    if len(violations) > 120:
        lines.append(f"... truncated, total violations={len(violations)}")

    (out_dir / "summary.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Hard CI gate for UTF-8/BOM/mojibake checks.")
    parser.add_argument(
        "--target",
        action="append",
        default=None,
        help="Path to scan (file or dir). Can be repeated. Default: docs,.github,.taskmaster,AGENTS.md",
    )
    parser.add_argument("--out-dir", default=None, help="Output directory for reports.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    repo_root = Path(__file__).resolve().parents[2]
    targets = args.target if args.target else list(DEFAULT_TARGETS)

    files, violations = iter_target_files(repo_root, targets)
    for path in files:
        if is_allowlisted(repo_root, path):
            continue
        violations.extend(validate_file(repo_root, path))

    out_dir = build_out_dir(repo_root, args.out_dir)
    write_reports(out_dir, scanned=len(files), targets=targets, violations=violations)

    status = "fail" if violations else "ok"
    print(f"ENCODING_HARD_GATE status={status} scanned={len(files)} violations={len(violations)} out={to_posix(out_dir)}")
    return 1 if violations else 0


if __name__ == "__main__":
    raise SystemExit(main())
