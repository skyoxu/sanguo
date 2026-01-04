#!/usr/bin/env python3
"""
Deterministic review helpers for sc-llm-review.

Why:
  Some "subagent" prompts overlap with sc-acceptance-check hard gates
  (ADR compliance + performance budget). Running those via LLM is both
  redundant and can fail due to transient network/model issues.

What:
  This module maps two agents to acceptance_check artifacts:
    - adr-compliance-checker -> logs/ci/**/sc-acceptance-check*/adr-compliance.json
    - performance-slo-validator -> logs/ci/**/sc-acceptance-check*/perf-budget.json
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from _util import repo_root, today_str, write_text


DETERMINISTIC_AGENTS = {"adr-compliance-checker", "performance-slo-validator"}


def _to_posix(path: Path) -> str:
    return str(path).replace("\\", "/")


def _find_latest_acceptance_dir(*, task_id: str | None) -> Path | None:
    ci_root = repo_root() / "logs" / "ci"
    if not ci_root.exists():
        return None

    candidates: list[Path] = []
    today_dir = ci_root / today_str()
    if today_dir.exists():
        for p in [today_dir / "sc-acceptance-check", *today_dir.glob("sc-acceptance-check-task-*")]:
            if (p / "summary.json").is_file():
                candidates.append(p)

    if not candidates:
        for summary in ci_root.rglob("summary.json"):
            parent = summary.parent
            if parent.name.startswith("sc-acceptance-check"):
                candidates.append(parent)

    best: Path | None = None
    best_mtime = -1.0
    for p in candidates:
        summary = p / "summary.json"
        try:
            data = json.loads(summary.read_text(encoding="utf-8"))
        except Exception:
            continue
        if task_id and str(data.get("task_id") or "") != str(task_id):
            continue
        try:
            mtime = summary.stat().st_mtime
        except OSError:
            mtime = 0.0
        if mtime > best_mtime:
            best_mtime = mtime
            best = p
    return best


def _render_adr_report(*, task_id: str | None, acceptance_dir: Path) -> tuple[str, str, dict[str, Any]]:
    path = acceptance_dir / "adr-compliance.json"
    meta = {"source": _to_posix(path.relative_to(repo_root()))}
    if not path.is_file():
        md = "\n".join(
            [
                "# ADR Compliance (deterministic)",
                "",
                f"- task_id: {task_id or '(unknown)'}",
                f"- source: `{meta['source']}` (missing)",
                "",
                "## P2",
                "- missing deterministic ADR compliance artifact; run acceptance_check first",
                "",
                "Verdict: Needs Fix",
                "",
            ]
        )
        return md, "Needs Fix", meta

    data = json.loads(path.read_text(encoding="utf-8"))
    errors = list(data.get("errors") or [])
    warnings = list(data.get("warnings") or [])
    verdict = "OK" if not errors else "Needs Fix"

    lines: list[str] = []
    lines.append("# ADR Compliance (deterministic)")
    lines.append("")
    lines.append(f"- task_id: {data.get('task_id') or task_id or '(unknown)'}")
    lines.append(f"- title: {data.get('title') or '(unknown)'}")
    lines.append(f"- source: `{meta['source']}`")
    lines.append("")

    lines.append("## P0")
    lines.extend([f"- {e}" for e in errors] if errors else ["- none"])
    lines.append("")

    lines.append("## P2")
    lines.extend([f"- {w}" for w in warnings] if warnings else ["- none"])
    lines.append("")

    lines.append("## Evidence")
    adr_status = data.get("adrStatus") or {}
    for adr_id in sorted(adr_status.keys()):
        st = adr_status.get(adr_id) or {}
        lines.append(f"- {adr_id}: status={st.get('status')} path={st.get('path')}")
    overlay = data.get("overlay")
    if overlay:
        lines.append(f"- overlay: `{overlay}`")
    lines.append("")

    lines.append(f"Verdict: {verdict}")
    lines.append("")
    return "\n".join(lines), verdict, meta


def _render_perf_report(*, task_id: str | None, acceptance_dir: Path) -> tuple[str, str, dict[str, Any]]:
    path = acceptance_dir / "perf-budget.json"
    meta = {"source": _to_posix(path.relative_to(repo_root()))}
    if not path.is_file():
        md = "\n".join(
            [
                "# Performance SLO (deterministic)",
                "",
                f"- task_id: {task_id or '(unknown)'}",
                f"- source: `{meta['source']}` (missing)",
                "",
                "## P2",
                "- missing deterministic perf-budget artifact; run acceptance_check with --perf-p95-ms (or --require-perf) first",
                "",
                "Verdict: Needs Fix",
                "",
            ]
        )
        return md, "Needs Fix", meta

    data = json.loads(path.read_text(encoding="utf-8"))
    disabled = data.get("status") == "disabled" or (data.get("max_p95_ms") == 0)
    budget_status = str(data.get("budget_status") or "")
    ok = (budget_status == "pass") or disabled
    verdict = "OK" if ok else "Needs Fix"

    p95_ms = data.get("p95_ms")
    frames = data.get("frames")

    lines: list[str] = []
    lines.append("# Performance SLO (deterministic)")
    lines.append("")
    lines.append(f"- task_id: {task_id or '(unknown)'}")
    lines.append(f"- source: `{meta['source']}`")
    lines.append("")

    if disabled:
        lines.append("## P2")
        if p95_ms is not None and frames is not None:
            lines.append(f"- perf budget gate is disabled (max_p95_ms=0); latest headless [PERF] observed: p95_ms={p95_ms} frames={frames}")
        else:
            lines.append("- perf budget gate is disabled (max_p95_ms=0); no headless [PERF] evidence found in the artifact (run smoke to collect)")
        lines.append("")
    elif verdict != "OK":
        lines.append("## P0")
        lines.append(f"- perf p95_ms exceeded threshold (p95_ms={data.get('p95_ms')} max_p95_ms={data.get('max_p95_ms')})")
        lines.append("")
    else:
        lines.append("## P0")
        lines.append("- none")
        lines.append("")

    lines.append("## Evidence")
    for k in ["headless_log", "frames", "p95_ms", "max_p95_ms", "budget_status"]:
        if k in data:
            lines.append(f"- {k}: {data.get(k)}")
    lines.append("")

    lines.append(f"Verdict: {verdict}")
    lines.append("")
    return "\n".join(lines), verdict, meta


def build_deterministic_review(*, agent: str, out_dir: Path, task_id: str | None) -> dict[str, Any]:
    acceptance_dir = _find_latest_acceptance_dir(task_id=task_id)
    prompt_path = out_dir / f"prompt-{agent}.md"
    output_path = out_dir / f"review-{agent}.md"
    trace_path = out_dir / f"trace-{agent}.log"

    if not acceptance_dir:
        write_text(prompt_path, "Deterministic mode: acceptance_check artifacts not found.\n")
        write_text(output_path, "Deterministic mode: missing acceptance_check artifacts.\nVerdict: Needs Fix\n")
        write_text(trace_path, "acceptance_check artifacts not found under logs/ci.\n")
        return {
            "status": "skipped",
            "rc": 2,
            "cmd": [],
            "prompt_path": _to_posix(prompt_path.relative_to(repo_root())),
            "output_path": _to_posix(output_path.relative_to(repo_root())),
            "details": {
                "trace": _to_posix(trace_path.relative_to(repo_root())),
                "verdict": "Needs Fix",
                "note": "run acceptance_check first",
            },
        }

    acc_rel = _to_posix(acceptance_dir.relative_to(repo_root()))
    write_text(prompt_path, f"Deterministic mode: generated from `{acc_rel}`.\n")

    if agent == "adr-compliance-checker":
        md, verdict, meta = _render_adr_report(task_id=task_id, acceptance_dir=acceptance_dir)
    elif agent == "performance-slo-validator":
        md, verdict, meta = _render_perf_report(task_id=task_id, acceptance_dir=acceptance_dir)
    else:
        md = "Deterministic mode: unsupported agent.\nVerdict: Needs Fix\n"
        verdict = "Needs Fix"
        meta = {}

    write_text(output_path, md)
    write_text(trace_path, f"deterministic source_dir={str(acceptance_dir)} source_file={meta.get('source')}\n")
    return {
        "status": "ok",
        "rc": 0,
        "cmd": [],
        "prompt_path": _to_posix(prompt_path.relative_to(repo_root())),
        "output_path": _to_posix(output_path.relative_to(repo_root())),
        "details": {
            "trace": _to_posix(trace_path.relative_to(repo_root())),
            "verdict": verdict,
            "acceptance_dir": acc_rel,
            **meta,
        },
    }
