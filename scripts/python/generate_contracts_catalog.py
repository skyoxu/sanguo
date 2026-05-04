#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Generate a contracts catalog (template-friendly).

This tool is intentionally generic: it does NOT assume any specific project/module name.
It can be used by any project created by copying this template.

Outputs (default):
  logs/ci/<YYYY-MM-DD>/contracts-catalog/contracts-catalog[--<PRD-ID>].md
  logs/ci/<YYYY-MM-DD>/contracts-catalog/summary.json
"""

from __future__ import annotations

import argparse
import json
import os
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


EVENT_TYPE_CONST_RE = re.compile(
    r"\bpublic\s+const\s+string\s+EventType\s*=\s*\"([^\"]+)\"\s*;",
    re.MULTILINE,
)
TYPE_DEF_RE = re.compile(
    r"\bpublic\s+(?:sealed\s+)?(?:partial\s+)?(?:record|class)\s+([A-Za-z_][A-Za-z0-9_]*)\b",
    re.MULTILINE,
)
PUBLIC_INTERFACE_RE = re.compile(
    r"\bpublic\s+interface\s+([A-Za-z_][A-Za-z0-9_]*)\b",
    re.MULTILINE,
)


@dataclass(frozen=True)
class EventEntry:
    event_type: str
    symbol: str | None
    file: str


@dataclass(frozen=True)
class InterfaceEntry:
    symbol: str
    file: str


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _to_posix(path: Path) -> str:
    return str(path).replace("\\", "/")


def _today_ci_dir(root: Path) -> Path:
    day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return root / "logs" / "ci" / day


def _read_text_utf8(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def _iter_files(base: Path, pattern: str) -> Iterable[Path]:
    if not base.exists():
        return []
    files: list[Path] = []
    for p in base.rglob(pattern):
        if not p.is_file():
            continue
        if any(seg in {"bin", "obj"} for seg in p.parts):
            continue
        files.append(p)
    return sorted(files)


def _guess_symbol_near(text: str, const_start: int) -> str | None:
    # Heuristic: find the closest type definition above the constant (within 2k chars).
    window = text[max(0, const_start - 2000) : const_start]
    matches = list(TYPE_DEF_RE.finditer(window))
    return matches[-1].group(1) if matches else None


def _collect_events(root: Path, *, contracts_dir: Path, domain_prefix: str) -> list[EventEntry]:
    entries: list[EventEntry] = []
    for cs in _iter_files(contracts_dir, "*.cs"):
        text = _read_text_utf8(cs)
        for m in EVENT_TYPE_CONST_RE.finditer(text):
            event_type = m.group(1).strip()
            if not event_type.startswith(domain_prefix + "."):
                continue
            symbol = _guess_symbol_near(text, m.start())
            entries.append(
                EventEntry(
                    event_type=event_type,
                    symbol=symbol,
                    file=_to_posix(cs.relative_to(root)),
                )
            )
    entries.sort(key=lambda e: (e.file, e.event_type))
    return entries


def _collect_interfaces(root: Path, base_dir: Path) -> list[InterfaceEntry]:
    entries: list[InterfaceEntry] = []
    for cs in _iter_files(base_dir, "*.cs"):
        text = _read_text_utf8(cs)
        for m in PUBLIC_INTERFACE_RE.finditer(text):
            entries.append(
                InterfaceEntry(
                    symbol=m.group(1),
                    file=_to_posix(cs.relative_to(root)),
                )
            )
    entries.sort(key=lambda e: (e.symbol, e.file))
    return entries


def _load_tasks(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []

    if isinstance(data, list):
        return [t for t in data if isinstance(t, dict)]
    if isinstance(data, dict):
        tasks = data.get("tasks")
        if isinstance(tasks, list):
            return [t for t in tasks if isinstance(t, dict)]
    return []


def _collect_task_contract_refs(tasks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for t in tasks:
        task_id = t.get("id") or t.get("task_id") or t.get("taskId")
        title = t.get("title") or t.get("name")
        refs = t.get("contractRefs") or t.get("contract_refs") or []
        if isinstance(refs, str):
            refs = [refs]
        if not isinstance(refs, list):
            refs = []
        refs_norm = sorted({str(x).strip() for x in refs if str(x).strip()})
        if not refs_norm:
            continue
        out.append({"id": str(task_id) if task_id is not None else None, "title": title, "contractRefs": refs_norm})
    out.sort(key=lambda x: (x["id"] or "", x.get("title") or ""))
    return out


def _md_escape(s: str) -> str:
    return s.replace("\\", "\\\\").replace("`", "\\`")


def main() -> int:
    ap = argparse.ArgumentParser(description="Generate a contracts catalog (template-friendly).")
    ap.add_argument("--prd-id", default=None, help="Optional PRD id for the catalog header (e.g. PRD-Guild-Manager).")
    ap.add_argument(
        "--domain-prefix",
        default=(os.environ.get("DOMAIN_PREFIX") or "core").strip() or "core",
        help="Domain prefix for EventType filtering (default from env DOMAIN_PREFIX or 'core').",
    )
    ap.add_argument("--contracts-dir", default="Game.Core/Contracts", help="Contracts root (relative to repo root).")
    ap.add_argument("--tasks-back", default=".taskmaster/tasks/tasks_back.json", help="Optional tasks view (back).")
    ap.add_argument("--tasks-gameplay", default=".taskmaster/tasks/tasks_gameplay.json", help="Optional tasks view (gameplay).")
    ap.add_argument("--out-md", default=None, help="Output markdown path. Default: logs/ci/<date>/contracts-catalog/...")
    ap.add_argument("--out-json", default=None, help="Output json summary path. Default: logs/ci/<date>/contracts-catalog/summary.json")
    args = ap.parse_args()

    root = repo_root()
    ts_utc = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

    contracts_dir = root / str(args.contracts_dir)
    ci_dir = _today_ci_dir(root) / "contracts-catalog"
    ci_dir.mkdir(parents=True, exist_ok=True)

    suffix = f"--{args.prd_id}" if args.prd_id else ""
    out_md = Path(args.out_md) if args.out_md else (ci_dir / f"contracts-catalog{suffix}.md")
    out_json = Path(args.out_json) if args.out_json else (ci_dir / "summary.json")
    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_json.parent.mkdir(parents=True, exist_ok=True)

    events: list[EventEntry] = []
    if contracts_dir.exists():
        events = _collect_events(root, contracts_dir=contracts_dir, domain_prefix=args.domain_prefix)

    ports = _collect_interfaces(root, root / "Game.Core" / "Ports")
    services = _collect_interfaces(root, root / "Game.Core" / "Services")
    repos = _collect_interfaces(root, root / "Game.Core" / "Repositories")

    tasks_back = _collect_task_contract_refs(_load_tasks(root / str(args.tasks_back)))
    tasks_gameplay = _collect_task_contract_refs(_load_tasks(root / str(args.tasks_gameplay)))

    md_lines: list[str] = []
    header_prd = f" ({_md_escape(args.prd_id)})" if args.prd_id else ""
    md_lines.append(f"# Contracts Catalog{header_prd} (generated)")
    md_lines.append("")
    md_lines.append(f"- Generated at (UTC): `{ts_utc}`")
    md_lines.append(f"- Generator: `scripts/python/generate_contracts_catalog.py`")
    md_lines.append(f"- Domain prefix filter: `{_md_escape(args.domain_prefix)}.*`")
    md_lines.append("")
    md_lines.append("## Sources (SSoT references)")
    md_lines.append(f"- Contracts (code): `{_md_escape(_to_posix(contracts_dir.relative_to(root)))}**`")
    md_lines.append(f"- Tasks (optional): `{_md_escape(str(args.tasks_back))}`, `{_md_escape(str(args.tasks_gameplay))}`")
    md_lines.append("")
    md_lines.append("## Domain Events (EventType)")
    md_lines.append("")
    if not contracts_dir.exists():
        md_lines.append(f"> Skipped: contracts dir not found: `{_md_escape(_to_posix(contracts_dir.relative_to(root)))}'")
    elif not events:
        md_lines.append("> No EventType constants found under Contracts for the selected domain prefix.")
    else:
        by_file: dict[str, list[EventEntry]] = {}
        for e in events:
            by_file.setdefault(e.file, []).append(e)
        for file, items in sorted(by_file.items()):
            md_lines.append(f"### `{_md_escape(file)}`")
            for e in items:
                if e.symbol:
                    md_lines.append(f"- `{_md_escape(e.event_type)}` → `{_md_escape(e.symbol)}`")
                else:
                    md_lines.append(f"- `{_md_escape(e.event_type)}`")
            md_lines.append("")

    def _render_iface(title: str, entries: list[InterfaceEntry]) -> None:
        md_lines.append(f"## {title}")
        md_lines.append("")
        if not entries:
            md_lines.append("> None found.")
            md_lines.append("")
            return
        for e in entries:
            md_lines.append(f"- `{_md_escape(e.symbol)}` (`{_md_escape(e.file)}`)")
        md_lines.append("")

    _render_iface("Ports (Core → Adapters)", ports)
    _render_iface("Services (Core abstractions)", services)
    _render_iface("Repositories (persistence abstractions)", repos)

    md_lines.append("## By task (contractRefs view)")
    md_lines.append("")
    if not tasks_back and not tasks_gameplay:
        md_lines.append("> Skipped: no task views found (or no contractRefs present).")
        md_lines.append("")
    else:
        if tasks_back:
            md_lines.append("### tasks_back.json")
            for t in tasks_back:
                label = t["id"] or "(no-id)"
                title = f" — {t['title']}" if t.get("title") else ""
                md_lines.append(f"- **{_md_escape(label)}**{_md_escape(title)}")
                for r in t["contractRefs"]:
                    md_lines.append(f"  - `{_md_escape(r)}`")
            md_lines.append("")
        if tasks_gameplay:
            md_lines.append("### tasks_gameplay.json")
            for t in tasks_gameplay:
                label = t["id"] or "(no-id)"
                title = f" — {t['title']}" if t.get("title") else ""
                md_lines.append(f"- **{_md_escape(label)}**{_md_escape(title)}")
                for r in t["contractRefs"]:
                    md_lines.append(f"  - `{_md_escape(r)}`")
            md_lines.append("")

    out_md.write_text("\n".join(md_lines).rstrip() + "\n", encoding="utf-8")

    report = {
        "status": "ok",
        "generated_at_utc": ts_utc,
        "prd_id": args.prd_id,
        "domain_prefix": args.domain_prefix,
        "paths": {
            "contracts_dir": _to_posix(contracts_dir.relative_to(root)) if contracts_dir.exists() else _to_posix(contracts_dir),
            "tasks_back": str(args.tasks_back),
            "tasks_gameplay": str(args.tasks_gameplay),
            "out_md": _to_posix(out_md),
            "out_json": _to_posix(out_json),
        },
        "counts": {
            "events": len(events),
            "ports": len(ports),
            "services": len(services),
            "repositories": len(repos),
            "tasks_back_with_contractRefs": len(tasks_back),
            "tasks_gameplay_with_contractRefs": len(tasks_gameplay),
        },
    }
    out_json.write_text(json.dumps(report, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")

    print(f"CONTRACTS_CATALOG status=ok out_md={_to_posix(out_md)} out_json={_to_posix(out_json)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

