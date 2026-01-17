#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import datetime as dt
import hashlib
import json
import re
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


def _is_probably_semantic_garbled(text: str) -> bool:
    # Minimal, explainable heuristics:
    # - U+FFFD replacement char
    # - "???" runs (common substitution symptom)
    # - suspicious "�" marker already covered by U+FFFD
    if "\ufffd" in text:
        return True
    if re.search(r"\?{3,}", text):
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

    # Optional semantic check: header should not contain "???" runs
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
    out_dir = _today_ci_dir()
    out_dir.mkdir(parents=True, exist_ok=True)

    targets: list[Path] = []
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
    hard = [f for f in all_findings if f.kind in hard_kinds]
    if hard:
        print(f"TEXT_INTEGRITY status=fail hard={len(hard)} out={out_dir}")
        return 2
    print(f"TEXT_INTEGRITY status=ok findings={len(all_findings)} out={out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

