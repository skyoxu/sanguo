#!/usr/bin/env python3
"""
Deterministic test-quality heuristics (soft gate).

Scope:
  - Detect whether a task is UI-related (heuristic).
  - Check for presence of at least one GdUnit4 runtime behavior test (vs only static string assertions).
  - Flag likely flaky patterns in GdUnit4 tests (timer-based waits, tight tolerances, etc).

This is a stop-loss helper, not a proof of correctness.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any


EVENT_RE = re.compile(r"\b(?:core|ui)\.[a-z0-9_]+(?:\.[a-z0-9_]+){1,}\b", re.IGNORECASE)
PUBLISH_RE = re.compile(r"\bPublishSimple\s*\(\s*\"(core|ui)\.", re.IGNORECASE)
ASSERT_RE = re.compile(r"\bassert_\w+\b", re.IGNORECASE)


FLAKY_RULES: list[tuple[str, re.Pattern[str]]] = [
    ("gd.timer_wait", re.compile(r"\bcreate_timer\s*\(", re.IGNORECASE)),
    ("gd.await_until", re.compile(r"\b_await_until\s*\(", re.IGNORECASE)),
    ("gd.distance_tolerance", re.compile(r"\bdistance_to\s*\(.*\)\s*<=?\s*0\.\d+", re.IGNORECASE)),
]


def _to_posix(path: Path) -> str:
    return str(path).replace("\\", "/")


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def _is_ui_task(*, title: str, details_blob: str) -> bool:
    s = (title + "\n" + details_blob).lower()
    if "ui" in s or "hud" in s:
        return True
    if "界面" in s or "按钮" in s or "面板" in s:
        return True
    return False


def _extract_events_from_taskdoc(taskdoc_path: Path | None) -> dict[str, list[str]]:
    if not taskdoc_path or not taskdoc_path.is_file():
        return {"core": [], "ui": []}
    text = _read_text(taskdoc_path)
    events = sorted({m.group(0).lower() for m in EVENT_RE.finditer(text)})
    core = [e for e in events if e.startswith("core.")]
    ui = [e for e in events if e.startswith("ui.")]
    return {"core": core, "ui": ui}


def _iter_gdunit_tests(tests_root: Path) -> list[Path]:
    if not tests_root.exists():
        return []
    files = sorted({*tests_root.rglob("*.gd")})
    filtered: list[Path] = []
    for p in files:
        if not p.is_file():
            continue
        if any(seg in {".git", ".godot", "bin", "obj", "logs"} for seg in p.parts):
            continue
        filtered.append(p)
    return filtered


def assess_test_quality(
    *,
    repo_root: Path,
    task_id: str,
    title: str,
    details_blob: str,
    taskdoc_path: Path | None,
) -> dict[str, Any]:
    ui_task = _is_ui_task(title=title, details_blob=details_blob)
    taskdoc_events = _extract_events_from_taskdoc(taskdoc_path)

    tests_root = repo_root / "Tests.Godot" / "tests"
    gd_tests = _iter_gdunit_tests(tests_root)

    behavior_tests: list[str] = []
    flaky_findings: list[dict[str, Any]] = []
    referenced_events: dict[str, set[str]] = {"core": set(), "ui": set()}

    for p in gd_tests:
        text = _read_text(p)
        has_publish = bool(PUBLISH_RE.search(text))
        has_assert = bool(ASSERT_RE.search(text))
        if has_publish and has_assert:
            behavior_tests.append(_to_posix(p.relative_to(repo_root)))

        # Track event strings referenced in tests (best-effort).
        for m in EVENT_RE.finditer(text):
            ev = m.group(0).lower()
            if ev.startswith("core."):
                referenced_events["core"].add(ev)
            elif ev.startswith("ui."):
                referenced_events["ui"].add(ev)

        # Flaky heuristics (line level).
        for i, line in enumerate(text.splitlines(), start=1):
            for rule_name, rx in FLAKY_RULES:
                if rx.search(line):
                    flaky_findings.append(
                        {
                            "file": _to_posix(p.relative_to(repo_root)),
                            "line": i,
                            "rule": rule_name,
                            "text": line.strip(),
                        }
                    )

    # Coverage vs taskdoc events (helps avoid false confidence).
    missing_core_events = [e for e in taskdoc_events["core"] if e not in referenced_events["core"]]
    missing_ui_events = [e for e in taskdoc_events["ui"] if e not in referenced_events["ui"]]

    findings_p1: list[str] = []
    findings_p2: list[str] = []

    if ui_task and not behavior_tests:
        findings_p1.append("UI task but no GdUnit4 runtime behavior test detected (PublishSimple + assert_*).")
    if ui_task and taskdoc_events["core"] and missing_core_events:
        findings_p1.append(
            "Taskdoc core events not referenced by any GdUnit4 test: "
            + ", ".join(missing_core_events[:10])
            + (" ..." if len(missing_core_events) > 10 else "")
        )
    if ui_task and taskdoc_events["ui"] and missing_ui_events:
        findings_p2.append(
            "Taskdoc UI events not referenced by any GdUnit4 test: "
            + ", ".join(missing_ui_events[:10])
            + (" ..." if len(missing_ui_events) > 10 else "")
        )

    if flaky_findings:
        findings_p2.append(f"Potential flaky patterns detected in GdUnit tests: {len(flaky_findings)} findings.")

    verdict = "OK"
    if findings_p1:
        verdict = "Needs Fix"
    elif findings_p2:
        verdict = "Warn"

    return {
        "task_id": str(task_id),
        "title": title,
        "ui_task": ui_task,
        "taskdoc_path": _to_posix(taskdoc_path) if taskdoc_path else None,
        "taskdoc_events": taskdoc_events,
        "gdunit": {
            "tests_root": _to_posix(tests_root.relative_to(repo_root)) if tests_root.exists() else _to_posix(tests_root),
            "tests_scanned": len(gd_tests),
            "behavior_tests_found": behavior_tests[:50],
            "behavior_tests_total": len(behavior_tests),
            "referenced_events": {
                "core": sorted(referenced_events["core"]),
                "ui": sorted(referenced_events["ui"]),
            },
        },
        "findings": {
            "p1": findings_p1,
            "p2": findings_p2,
            "flaky_samples": flaky_findings[:50],
        },
        "verdict": verdict,
    }
