#!/usr/bin/env python
"""
Sync ADR-0028/0029/0030 from a sibling repo into this template repo (UTF-8).

Responsibilities:
- Copy files from <sibling>/docs/adr/ into this repo's docs/adr/.
- Template-ize / decouple obvious sibling semantics (repo names, absolute paths).
- Update docs/architecture/ADR_INDEX_GODOT.md to include the new ADR entries.
- Write an audit report to logs/ci/<YYYY-MM-DD>/sync-adrs-0028-0030.json

This script is standard-library-only and prints ASCII-only summaries to avoid
Windows console codepage issues.
"""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime
from pathlib import Path


ADR_FILES = [
    "ADR-0028-event-usage-tiering.md",
    "ADR-0029-error-handling-policy.md",
    "ADR-0030-core-threading-model.md",
]

ADR_INDEX_PATH = Path("docs/architecture/ADR_INDEX_GODOT.md")
ADR_DIR = Path("docs/adr")


def _date_dir(root: Path) -> Path:
    return root / "logs" / "ci" / datetime.now().strftime("%Y-%m-%d")


def _read_utf8(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _write_utf8(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def _templateize_markdown(text: str) -> tuple[str, list[str]]:
    notes: list[str] = []
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    # Decouple obvious sibling repo identifiers.
    before = text
    text = re.sub(r"(?i)\\bnewguild\\b", "本模板仓库", text)
    text = re.sub(r"(?i)\\bsanguo\\b", "本模板仓库", text)
    if text != before:
        notes.append("replaced_sibling_repo_names")

    # Strip absolute build paths if present.
    before = text
    text = re.sub(r"(?i)C:\\\\buildgame\\\\(newguild|sanguo)\\\\", "", text)
    if text != before:
        notes.append("removed_absolute_build_paths")

    return text, notes


def _forbidden_hits(text: str) -> list[str]:
    forbidden = [
        r"(?i)\\bnewguild\\b",
        r"(?i)\\bsanguo\\b",
        r"\\bC:\\\\buildgame\\\\newguild\\b",
        r"\\bC:\\\\buildgame\\\\sanguo\\b",
        "????",
    ]
    hits: list[str] = []
    for token in forbidden:
        if token.startswith("(?i)") or token.startswith("\\b") or token.startswith("C:\\\\"):
            if re.search(token, text):
                hits.append(token)
        else:
            if token in text:
                hits.append(token)
    return hits


def _extract_title(md_text: str) -> str:
    # Expect first line: "# ADR-00XX: <title>"
    for line in md_text.splitlines():
        line = line.strip()
        if line.startswith("# ADR-"):
            return line.lstrip("#").strip()
    return ""


def _update_adr_index(root: Path, entries: list[tuple[str, str, str]]) -> tuple[bool, str]:
    """
    entries: [(adr_id, title_line, rel_path)]
    Example title_line: "ADR-0028: 事件用途分级（...）"
    """
    index_path = root / ADR_INDEX_PATH
    if not index_path.exists():
        raise FileNotFoundError(str(index_path))

    text = _read_utf8(index_path)
    lines = text.replace("\r\n", "\n").replace("\r", "\n").splitlines()

    accepted_header = "## 已采纳（Accepted）"
    try:
        accepted_idx = lines.index(accepted_header)
    except ValueError as e:
        raise RuntimeError(f"ADR index missing header: {accepted_header}") from e

    # Find the block of bullets under Accepted.
    insert_at = None
    for i in range(accepted_idx + 1, len(lines)):
        if lines[i].startswith("## "):  # next section
            insert_at = i
            break
    if insert_at is None:
        insert_at = len(lines)

    accepted_block = lines[accepted_idx + 1 : insert_at]

    def has_adr(adr_id: str) -> bool:
        return any(re.search(rf"\b{re.escape(adr_id)}\b", l) for l in accepted_block)

    added_any = False
    for adr_id, title_line, rel_path in entries:
        if has_adr(adr_id):
            continue
        # Format: "- ADR-0028: <desc> — `docs/adr/<file>.md`"
        # title_line already contains "ADR-0028: <desc>"
        bullet = f"- {title_line} — `{rel_path}`"

        # Insert in numeric order: place after the last ADR with smaller number.
        target_num = int(adr_id.split("-")[1])
        pos = accepted_idx + 1
        for j in range(accepted_idx + 1, insert_at):
            m = re.search(r"\bADR-(\d{4})\b", lines[j])
            if not m:
                continue
            num = int(m.group(1))
            if num <= target_num:
                pos = j + 1
        lines.insert(pos, bullet)
        insert_at += 1
        added_any = True

    # Normalize Accepted bullets ordering by ADR number to prevent drift.
    accepted_block = lines[accepted_idx + 1 : insert_at]
    bullet_lines: list[str] = []
    other_lines: list[str] = []
    for l in accepted_block:
        if l.startswith("- ADR-"):
            bullet_lines.append(l)
        else:
            other_lines.append(l)

    def _adr_num(line: str) -> int:
        m = re.search(r"\bADR-(\d{4})\b", line)
        return int(m.group(1)) if m else 999999

    bullet_lines.sort(key=_adr_num)
    normalized_block = bullet_lines + other_lines
    lines = lines[: accepted_idx + 1] + normalized_block + lines[insert_at:]

    new_text = "\n".join(lines) + "\n"
    if added_any or new_text != text.replace("\r\n", "\n").replace("\r", "\n") + "\n":
        _write_utf8(index_path, new_text)
        return True, str(index_path)
    return False, str(index_path)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Sync ADR-0028/0029/0030 from sibling repo and update ADR index."
    )
    parser.add_argument("--root", default=".", help="Current repo root (default: .)")
    parser.add_argument(
        "--sibling",
        default=r"C:\buildgame\sanguo",
        help=r"Sibling repo root (default: C:\buildgame\sanguo)",
    )
    args = parser.parse_args(argv)

    root = Path(args.root).resolve()
    sibling = Path(args.sibling).resolve()

    copied: list[dict[str, object]] = []
    entries_for_index: list[tuple[str, str, str]] = []
    ok = True

    for name in ADR_FILES:
        src = sibling / "docs" / "adr" / name
        dst = root / ADR_DIR / name
        if not src.exists():
            copied.append({"file": name, "status": "missing_source", "source": str(src)})
            ok = False
            continue

        raw = _read_utf8(src)
        out, notes = _templateize_markdown(raw)
        hits = _forbidden_hits(out)
        if hits:
            ok = False
        _write_utf8(dst, out)

        title_line = _extract_title(out)
        adr_id = name.split("-", 2)[0] + "-" + name.split("-", 2)[1]  # ADR-0028
        rel_path = f"docs/adr/{name}"
        entries_for_index.append((adr_id, title_line, rel_path))

        copied.append(
            {
                "file": name,
                "status": "copied",
                "source": str(src),
                "dest": str(dst),
                "notes": notes,
                "forbidden_hits": hits,
                "title": title_line,
            }
        )

    index_updated, index_path = _update_adr_index(root, entries_for_index)

    report = {
        "ok": ok and all(c.get("status") == "copied" for c in copied),
        "sibling": str(sibling),
        "files": copied,
        "adr_index_updated": index_updated,
        "adr_index_path": index_path,
    }

    out_dir = _date_dir(root)
    out_dir.mkdir(parents=True, exist_ok=True)
    report_path = out_dir / "sync-adrs-0028-0030.json"
    _write_utf8(report_path, json.dumps(report, ensure_ascii=False, indent=2) + "\n")

    status = "OK" if report["ok"] else "FAIL"
    print(f"sync_adrs_0028_0030: {status}")
    print(f"report: {report_path.as_posix()}")
    return 0 if report["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
