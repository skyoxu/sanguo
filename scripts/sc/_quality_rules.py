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
  - P0: fire-and-forget PublishAsync in core runtime code (publishing without awaiting/returning)
  - P1: UI publishes core.* events (UI must publish ui.* intent events; core publishes core.* fact events)
  - P1: Core publishes ui.* events (core must not emit UI intent events)
  - P1: Threading primitives used inside Game.Core (Task.Run / new Thread / Parallel.*)
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
_PUBLISHASYNC_FIRE_FORGET_RE = re.compile(r"(^|[^\w])_\s*=\s*[^;\n]*\.PublishAsync\s*\(", flags=re.MULTILINE)
_UI_PUBLISH_CORE_EVENT_RE = re.compile(r'\bPublishSimple\s*\(\s*"core\.', flags=re.IGNORECASE)
_CORE_PUBLISH_UI_EVENT_RE = re.compile(r'"ui\.[a-z0-9_.-]+"', flags=re.IGNORECASE)
_THREADING_PRIMITIVES_RE = re.compile(r"\b(Task\.Run\s*\(|new\s+Thread\s*\(|Parallel\.)")


def _to_posix(path: Path) -> str:
    return str(path).replace("\\", "/")


def _iter_cs_files(root: Path) -> Iterable[Path]:
    for p in root.rglob("*.cs"):
        if not p.is_file():
            continue
        if any(seg in {".git", ".godot", "bin", "obj", "logs", "TestResults"} for seg in p.parts):
            continue
        # Avoid scanning a junctioned mirror under Tests.Godot (single source of truth is Game.Godot at repo root).
        r = _to_posix(p)
        if r.startswith("Tests.Godot/Game.Godot/"):
            continue
        yield p


def _iter_gd_files(root: Path) -> Iterable[Path]:
    for p in root.rglob("*.gd"):
        if not p.is_file():
            continue
        if any(seg in {".git", ".godot", "bin", "obj", "logs", "TestResults"} for seg in p.parts):
            continue
        # Avoid scanning a junctioned mirror under Tests.Godot (single source of truth is Game.Godot at repo root).
        r = _to_posix(p)
        if r.startswith("Tests.Godot/Game.Godot/"):
            continue
        # Skip third-party addons/tests; only our own scripts matter here.
        if "addons" in p.parts:
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
    return False


def _is_core_publish_hard_scope(rel: str) -> bool:
    r = rel.replace("\\", "/")
    if not r.startswith("Game.Core/"):
        return False
    if "/Services/" in r or "/Engine/" in r:
        return True
    return False


def _is_ui_publish_hard_scope(rel: str) -> bool:
    r = rel.replace("\\", "/")
    if r.startswith("Game.Godot/") and "/Scripts/" in r and "/Examples/" not in r and "/Demo/" not in r:
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

        if _is_core_publish_hard_scope(rel) and _PUBLISHASYNC_FIRE_FORGET_RE.search(text):
            for m in _PUBLISHASYNC_FIRE_FORGET_RE.finditer(text):
                line = _line_number(text, m.start())
                sample = text.splitlines()[line - 1].strip() if line - 1 < len(text.splitlines()) else None
                findings.append(
                    Finding(
                        rule="cs.eventbus_publishasync_fire_and_forget",
                        severity="p0",
                        file=rel,
                        line=line,
                        message="Fire-and-forget PublishAsync detected in Game.Core (must be awaited/returned for core domain events).",
                        sample=sample,
                    )
                )

        if _is_core_publish_hard_scope(rel) and _CORE_PUBLISH_UI_EVENT_RE.search(text):
            # Static string-literal check: core layer must not emit ui.* events.
            for m in _CORE_PUBLISH_UI_EVENT_RE.finditer(text):
                line = _line_number(text, m.start())
                sample = text.splitlines()[line - 1].strip() if line - 1 < len(text.splitlines()) else None
                findings.append(
                    Finding(
                        rule="cs.core_emits_ui_events",
                        severity="p1",
                        file=rel,
                        line=line,
                        message="String literal with ui.* found inside Game.Core; core must not emit UI intent events (ADR-0028).",
                        sample=sample,
                    )
                )

        if rel.replace("\\", "/").startswith("Game.Core/") and _THREADING_PRIMITIVES_RE.search(text):
            for m in _THREADING_PRIMITIVES_RE.finditer(text):
                line = _line_number(text, m.start())
                sample = text.splitlines()[line - 1].strip() if line - 1 < len(text.splitlines()) else None
                findings.append(
                    Finding(
                        rule="cs.core_threading_primitives",
                        severity="p1",
                        file=rel,
                        line=line,
                        message="Threading primitive detected inside Game.Core (prefer single-thread core + adapters boundaries; ADR-0030).",
                        sample=sample,
                    )
                )

        # UI-specific rules: apply to runtime UI scripts (both main project and Tests.Godot runtime mirror).
        if _is_ui_publish_hard_scope(rel) and rel.endswith(".cs"):
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

            if _UI_PUBLISH_CORE_EVENT_RE.search(text):
                for m in _UI_PUBLISH_CORE_EVENT_RE.finditer(text):
                    line = _line_number(text, m.start())
                    sample = text.splitlines()[line - 1].strip() if line - 1 < len(text.splitlines()) else None
                    findings.append(
                        Finding(
                            rule="cs.ui_publishes_core_events",
                            severity="p1",
                            file=rel,
                            line=line,
                            message="UI PublishSimple(\"core.*\") detected; UI must publish ui.* intent events and never fabricate core.* facts (ADR-0028).",
                            sample=sample,
                        )
                    )

    # GDScript UI publish rule: detect UI publishing core.* (legacy/demo scripts are still risky drift sources).
    for p in _iter_gd_files(repo_root / "Game.Godot"):
        rel = _to_posix(p.relative_to(repo_root))
        r = rel.replace("\\", "/")
        if "/Scripts/" not in r or "/Examples/" in r or "/Demo/" in r:
            continue
        text = p.read_text(encoding="utf-8", errors="ignore")
        if _UI_PUBLISH_CORE_EVENT_RE.search(text):
            for m in _UI_PUBLISH_CORE_EVENT_RE.finditer(text):
                line = _line_number(text, m.start())
                sample = text.splitlines()[line - 1].strip() if line - 1 < len(text.splitlines()) else None
                findings.append(
                    Finding(
                        rule="gd.ui_publishes_core_events",
                        severity="p1",
                        file=rel,
                        line=line,
                        message="GDScript PublishSimple(\"core.*\") detected; UI must publish ui.* intent events (ADR-0028).",
                        sample=sample,
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
            "cs.eventbus_publishasync_fire_and_forget",
            "cs.core_emits_ui_events",
            "cs.core_threading_primitives",
            "cs.eventbus_repeated_lookup",
            "cs.domain_event_connect_without_exit_cleanup",
            "cs.jsondocument_parse_single_arg",
            "cs.ui_publishes_core_events",
            "gd.ui_publishes_core_events",
        ],
        "findings": by_sev,
        "counts": {
            "total": len(findings),
            "p0": len(p0),
            "p1": len(p1),
            "p2": len(by_sev.get("p2") or []),
        },
    }
