#!/usr/bin/env python3
"""
Deterministic code-quality stop-loss rules.

Why:
  Claude-style LLM reviews often spot recurring "foot-gun" patterns in Godot+C# projects.
  This module turns a small subset of those into deterministic rules so we can gate them
  as hard/soft checks inside sc-acceptance-check.

Scope (4 rules):
  - P0: blocking async wait via GetAwaiter().GetResult() in production code
  - P1: repeated /root/EventBus lookups in a single UI script
  - P1: EventBus DomainEventEmitted connect without _ExitTree cleanup
  - P1: JsonDocument.Parse(...) single-argument calls (no JsonDocumentOptions)
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable


@dataclass(frozen=True)
class Finding:
    rule: str
    severity: str  # p0|p1|p2
    file: str
    line: int | None
    message: str
    sample: str | None = None


_BLOCKING_WAIT_RE = re.compile(r"\.GetAwaiter\s*\(\s*\)\s*\.GetResult\s*\(\s*\)")
_EVENTBUS_LOOKUP_RE = re.compile(r'GetNodeOrNull\s*<\s*EventBusAdapter\s*>\s*\(\s*"/root/EventBus"\s*\)')
_DOMAIN_EVENT_CONNECT_RE = re.compile(r"Connect\s*\(\s*EventBusAdapter\.SignalName\.DomainEventEmitted\b")


def _to_posix(path: Path) -> str:
    return str(path).replace("\\", "/")


def _iter_cs_files(root: Path) -> Iterable[Path]:
    for p in root.rglob("*.cs"):
        if not p.is_file():
            continue
        if any(seg in {".git", ".godot", "bin", "obj", "logs", "TestResults"} for seg in p.parts):
            continue
        yield p


def _is_blocking_wait_hard_scope(rel: str) -> bool:
    """
    Only gate blocking waits where they are known to cause real stop-the-world issues:
      - Game.Core service layer
      - Godot runtime scripts (not Examples/DB bridges)
    """
    r = rel.replace("\\", "/")
    if r.startswith("Game.Core/") and "/Services/" in r:
        return True
    if r.startswith("Game.Godot/") and "/Scripts/" in r and "/Examples/" not in r:
        return True
    if r.startswith("Tests.Godot/Game.Godot/") and "/Scripts/" in r and "/Examples/" not in r:
        return True
    return False


def _line_number(text: str, pos: int) -> int:
    return text.count("\n", 0, pos) + 1


def _find_jsondocument_parse_single_arg(text: str) -> list[int]:
    """
    Finds `JsonDocument.Parse(<single-arg>)` calls by parsing parentheses and
    checking whether a top-level comma exists inside the argument list.
    Returns list of 0-based positions in `text` where the call starts.
    """
    needle = "JsonDocument.Parse"
    hits: list[int] = []
    i = 0
    while True:
        pos = text.find(needle, i)
        if pos < 0:
            break
        open_pos = text.find("(", pos + len(needle))
        if open_pos < 0:
            i = pos + len(needle)
            continue

        depth = 0
        in_str: str | None = None
        esc = False
        has_top_level_comma = False
        end = -1

        for j in range(open_pos, len(text)):
            ch = text[j]
            if in_str:
                if esc:
                    esc = False
                    continue
                if ch == "\\":
                    esc = True
                    continue
                if ch == in_str:
                    in_str = None
                continue

            if ch in ("\"", "'"):
                in_str = ch
                continue

            if ch == "(":
                depth += 1
                continue
            if ch == ")":
                depth -= 1
                if depth == 0:
                    end = j
                    break
                continue
            if ch == "," and depth == 1:
                has_top_level_comma = True

        if end > 0 and not has_top_level_comma:
            hits.append(pos)

        i = (end + 1) if end > 0 else (pos + len(needle))
    return hits


def scan_quality_rules(*, repo_root: Path) -> dict[str, Any]:
    findings: list[Finding] = []

    for p in _iter_cs_files(repo_root):
        rel = _to_posix(p.relative_to(repo_root))
        text = p.read_text(encoding="utf-8", errors="ignore")

        if _is_blocking_wait_hard_scope(rel) and _BLOCKING_WAIT_RE.search(text):
            for m in _BLOCKING_WAIT_RE.finditer(text):
                line = _line_number(text, m.start())
                sample = text.splitlines()[line - 1].strip() if line - 1 < len(text.splitlines()) else None
                findings.append(
                    Finding(
                        rule="cs.blocking_async_wait",
                        severity="p0",
                        file=rel,
                        line=line,
                        message="Blocking async wait via GetAwaiter().GetResult() in Game.Core services or Godot runtime scripts.",
                        sample=sample,
                    )
                )

        # UI-specific rules: apply to runtime UI scripts (both main project and Tests.Godot runtime mirror).
        if "/Scripts/" in rel and rel.endswith(".cs"):
            lookups = list(_EVENTBUS_LOOKUP_RE.finditer(text))
            if len(lookups) > 1:
                findings.append(
                    Finding(
                        rule="cs.eventbus_repeated_lookup",
                        severity="p1",
                        file=rel,
                        line=_line_number(text, lookups[1].start()),
                        message=f"Repeated GetNodeOrNull<EventBusAdapter>(\"/root/EventBus\") lookups in one file (count={len(lookups)}). Prefer caching/injection.",
                        sample=lookups[1].group(0),
                    )
                )

            if _DOMAIN_EVENT_CONNECT_RE.search(text) and "override void _ExitTree" not in text:
                findings.append(
                    Finding(
                        rule="cs.domain_event_connect_without_exit_cleanup",
                        severity="p1",
                        file=rel,
                        line=None,
                        message="Connect(DomainEventEmitted) detected but no _ExitTree override found; risk of leaked signal connection.",
                    )
                )

            for pos in _find_jsondocument_parse_single_arg(text):
                findings.append(
                    Finding(
                        rule="cs.jsondocument_parse_single_arg",
                        severity="p1",
                        file=rel,
                        line=_line_number(text, pos),
                        message="JsonDocument.Parse(...) called without JsonDocumentOptions (no MaxDepth bound). Prefer JsonDocument.Parse(json, options).",
                    )
                )

    by_sev: dict[str, list[dict[str, Any]]] = {"p0": [], "p1": [], "p2": []}
    for f in findings:
        by_sev.setdefault(f.severity, []).append(
            {
                "rule": f.rule,
                "severity": f.severity,
                "file": f.file,
                "line": f.line,
                "message": f.message,
                "sample": f.sample,
            }
        )

    p0 = by_sev.get("p0") or []
    p1 = by_sev.get("p1") or []

    verdict = "OK"
    if p0 or p1:
        verdict = "Needs Fix"

    return {
        "status": "ok",
        "verdict": verdict,
        "rules": [
            "cs.blocking_async_wait",
            "cs.eventbus_repeated_lookup",
            "cs.domain_event_connect_without_exit_cleanup",
            "cs.jsondocument_parse_single_arg",
        ],
        "findings": by_sev,
        "counts": {
            "total": len(findings),
            "p0": len(p0),
            "p1": len(p1),
            "p2": len(by_sev.get("p2") or []),
        },
    }
