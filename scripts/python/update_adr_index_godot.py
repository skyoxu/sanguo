#!/usr/bin/env python3
"""
Update docs/architecture/ADR_INDEX_GODOT.md from docs/adr/ as the single source of truth.

Rules:
- Read/write using UTF-8 (no BOM).
- Keep output deterministic: sort by ADR id.
- Surface missing/unknown statuses explicitly to avoid silent drift.

Usage (Windows):
  py -3 scripts/python/update_adr_index_godot.py
"""

from __future__ import annotations

import datetime as dt
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


RE_STATUS = re.compile(r"(?:^|[-*]\s*)Status\s*:\s*([A-Za-z]+)\b", flags=re.IGNORECASE)
RE_TITLE = re.compile(r"^#\s+(.*\S)\s*$")
RE_ADR_ID = re.compile(r"ADR-(\d{4})", flags=re.IGNORECASE)
RE_TITLE_PREFIX = re.compile(r"^ADR-(\d{4})\s*[:：]\s*", flags=re.IGNORECASE)


@dataclass(frozen=True)
class AdrEntry:
    adr_id: str  # e.g. ADR-0004
    adr_num: int
    title: str
    status: str  # Accepted|Superseded|Proposed|...
    rel_path: str


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def _write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8", newline="\n")


def _parse_adr_id_from_name(name: str) -> tuple[str, int] | None:
    m = RE_ADR_ID.search(name)
    if not m:
        return None
    n = int(m.group(1))
    return f"ADR-{n:04d}", n


def _parse_title_and_status(text: str) -> tuple[str, str]:
    title = ""
    status = ""
    for line in text.splitlines():
        if not title:
            mt = RE_TITLE.match(line)
            if mt:
                title = mt.group(1).strip()
        if not status:
            ms = RE_STATUS.search(line)
            if ms:
                status = (ms.group(1) or "").strip()
        if title and status:
            break
    return title, status


def _normalize_title(adr_id: str, raw_title: str) -> str:
    t = (raw_title or "").strip()
    if not t:
        return ""
    # Remove duplicated "ADR-XXXX:" prefix in the visible part.
    t = RE_TITLE_PREFIX.sub("", t)
    return t.strip()


def _collect_entries(repo_root: Path) -> tuple[list[AdrEntry], list[AdrEntry], list[AdrEntry], list[AdrEntry]]:
    adr_dir = repo_root / "docs" / "adr"
    addenda_dir = adr_dir / "addenda"
    if not adr_dir.exists():
        raise FileNotFoundError(f"ADR directory not found: {adr_dir}")

    entries: list[AdrEntry] = []
    for p in sorted(adr_dir.glob("ADR-*.md")):
        parsed = _parse_adr_id_from_name(p.name)
        if parsed is None:
            continue
        adr_id, adr_num = parsed
        raw = _read_text(p)
        raw_title, status = _parse_title_and_status(raw)
        title = _normalize_title(adr_id, raw_title) or _normalize_title(adr_id, p.stem)
        rel = p.relative_to(repo_root).as_posix()
        entries.append(
            AdrEntry(
                adr_id=adr_id,
                adr_num=adr_num,
                title=title,
                status=status,
                rel_path=rel,
            )
        )

    addenda: list[AdrEntry] = []
    if addenda_dir.exists():
        for p in sorted(addenda_dir.glob("ADR-*.md")):
            parsed = _parse_adr_id_from_name(p.name)
            if parsed is None:
                continue
            adr_id, adr_num = parsed
            raw = _read_text(p)
            raw_title, status = _parse_title_and_status(raw)
            title = _normalize_title(adr_id, raw_title) or _normalize_title(adr_id, p.stem)
            rel = p.relative_to(repo_root).as_posix()
            addenda.append(
                AdrEntry(
                    adr_id=adr_id,
                    adr_num=adr_num,
                    title=title,
                    status=status,
                    rel_path=rel,
                )
            )

    accepted = sorted([e for e in entries if e.status.lower() == "accepted"], key=lambda x: x.adr_num)
    superseded = sorted([e for e in entries if e.status.lower() == "superseded"], key=lambda x: x.adr_num)
    proposed = sorted([e for e in entries if e.status.lower() == "proposed"], key=lambda x: x.adr_num)
    missing_status = sorted([e for e in entries if not e.status.strip()], key=lambda x: x.adr_num)

    # Keep addenda stable (by number then path).
    addenda = sorted(addenda, key=lambda x: (x.adr_num, x.rel_path))
    return accepted, addenda, superseded, proposed + missing_status


def _render_list(items: Iterable[AdrEntry], *, suffix: str = "") -> str:
    lines: list[str] = []
    for e in items:
        if suffix:
            lines.append(f"- {e.adr_id}: {e.title}{suffix} — `{e.rel_path}`")
        else:
            lines.append(f"- {e.adr_id}: {e.title} — `{e.rel_path}`")
    return "\n".join(lines)


def main() -> int:
    repo_root = Path(__file__).resolve().parents[2]
    out_path = repo_root / "docs" / "architecture" / "ADR_INDEX_GODOT.md"

    accepted, addenda, superseded, needs_attention = _collect_entries(repo_root)

    parts: list[str] = []
    parts.append("# ADR 索引 — Godot 迁移（Accepted + Addenda）")
    parts.append("")
    parts.append("本文件用于快速定位与 Godot + C# 模板相关的 ADR（以 `docs/adr/` 为唯一口径）。")
    parts.append("")
    parts.append("## 已采纳（Accepted）")
    parts.append(_render_list(accepted) if accepted else "- (none)")
    parts.append("")
    parts.append("## 附录（Addenda）")
    if addenda:
        # Addenda shows status because it is not necessarily Accepted.
        parts.append(
            "\n".join([f"- {e.adr_id} Addendum ({e.status or 'Unknown'}): {e.title} — `{e.rel_path}`" for e in addenda])
        )
    else:
        parts.append("- (none)")
    parts.append("")
    parts.append("## 已替代（Superseded）")
    parts.append(_render_list(superseded) if superseded else "- (none)")
    parts.append("")
    parts.append("## 需要处理（Status 缺失/非 Accepted）")
    if needs_attention:
        parts.append(
            "\n".join(
                [
                    f"- {e.adr_id}: {e.title} (Status={e.status or 'Missing'}) — `{e.rel_path}`"
                    for e in needs_attention
                ]
            )
        )
    else:
        parts.append("- (none)")
    parts.append("")

    content = "\n".join(parts)
    _write_text(out_path, content)

    date = dt.datetime.now().strftime("%Y-%m-%d")
    log_dir = repo_root / "logs" / "ci" / date
    log_dir.mkdir(parents=True, exist_ok=True)
    summary = {
        "out_path": out_path.as_posix(),
        "accepted": [e.rel_path for e in accepted],
        "addenda": [e.rel_path for e in addenda],
        "superseded": [e.rel_path for e in superseded],
        "needs_attention": [{"path": e.rel_path, "status": e.status} for e in needs_attention],
    }
    (log_dir / "update-adr-index-godot.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"OK updated {out_path.as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
