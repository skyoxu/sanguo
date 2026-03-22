from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from _util import ensure_dir, repo_root, today_str, write_json


_BEGIN = "<!-- BEGIN AUTO:RUN_REVIEW_PIPELINE_TECHNICAL_DEBT -->"
_END = "<!-- END AUTO:RUN_REVIEW_PIPELINE_TECHNICAL_DEBT -->"
_TASK_SECTION_RE = re.compile(r"(?ms)^## Task (?P<task_id>\d+)\n.*?(?=^## Task \d+\n|\Z)")
_HEADING_RE = re.compile(r"^\s*#{1,6}\s*(P[0-4])\b.*$", flags=re.IGNORECASE)
_INLINE_RE = re.compile(r"^\s*(?:[-*]|\d+\.)?\s*(P[0-4])\b(?:\s*[:\-]\s*|\s+)(.+?)\s*$", flags=re.IGNORECASE)
_BULLET_PREFIX_RE = re.compile(r"^\s*(?:[-*]|\d+\.)\s*")
_VERDICT_RE = re.compile(r"^\s*Verdict\s*:", flags=re.IGNORECASE)
_LOW_PRIORITY = {"P2", "P3", "P4"}


def _normalize_relpath(path: Path, *, root: Path) -> str:
    try:
        return str(path.resolve().relative_to(root.resolve())).replace("\\", "/")
    except Exception:
        return str(path).replace("\\", "/")


def _parse_review_markdown(text: str) -> list[dict[str, str]]:
    findings: list[dict[str, str]] = []
    current_severity: str | None = None
    for raw_line in str(text or "").splitlines():
        line = raw_line.rstrip()
        if not line.strip():
            continue
        if _VERDICT_RE.match(line):
            current_severity = None
            continue
        heading_match = _HEADING_RE.match(line)
        if heading_match:
            current_severity = str(heading_match.group(1)).upper()
            continue
        inline_match = _INLINE_RE.match(line)
        if inline_match:
            severity = str(inline_match.group(1)).upper()
            message = str(inline_match.group(2)).strip()
            if severity in _LOW_PRIORITY and message:
                findings.append({"severity": severity, "message": message})
            continue
        if current_severity not in _LOW_PRIORITY:
            continue
        message = _BULLET_PREFIX_RE.sub("", line).strip()
        if message:
            findings.append({"severity": current_severity, "message": message})
    return findings


def collect_low_priority_review_findings(*, summary: dict[str, Any], root: Path | None = None) -> list[dict[str, str]]:
    root_dir = root or repo_root()
    results = summary.get("results") or []
    findings: list[dict[str, str]] = []
    seen: set[tuple[str, str, str, str]] = set()
    if not isinstance(results, list):
        return findings
    for result in results:
        if not isinstance(result, dict):
            continue
        output_path = Path(str(result.get("output_path") or "").strip())
        if not str(output_path):
            continue
        if not output_path.is_absolute():
            output_path = root_dir / output_path
        if not output_path.exists():
            continue
        agent = str(result.get("agent") or "").strip() or "unknown-agent"
        text = output_path.read_text(encoding="utf-8", errors="ignore")
        for item in _parse_review_markdown(text):
            key = (agent, item["severity"], item["message"], str(output_path))
            if key in seen:
                continue
            seen.add(key)
            findings.append(
                {
                    "severity": item["severity"],
                    "agent": agent,
                    "message": item["message"],
                    "source_path": _normalize_relpath(output_path, root=root_dir),
                }
            )
    return findings


def _base_document() -> str:
    return "\n".join(
        [
            "# Technical Debt Register",
            "",
            "This file is updated by `scripts/sc/run_review_pipeline.py`.",
            "",
            "- P0/P1 findings stay in the must-fix path and should not be parked here.",
            "- Only `P2/P3/P4` items from `sc-llm-review` are recorded here, grouped by task.",
            "",
            _BEGIN,
            _END,
            "",
        ]
    )


def _ensure_markers(text: str) -> str:
    if _BEGIN in text and _END in text:
        return text
    stripped = text.rstrip()
    if stripped:
        return stripped + "\n\n" + _BEGIN + "\n" + _END + "\n"
    return _base_document()


def _split_document(text: str) -> tuple[str, str, str]:
    prepared = _ensure_markers(text)
    start = prepared.index(_BEGIN)
    end = prepared.index(_END)
    prefix = prepared[:start]
    body = prepared[start + len(_BEGIN) : end]
    suffix = prepared[end + len(_END) :]
    return prefix, body, suffix


def _parse_sections(body: str) -> dict[str, str]:
    sections: dict[str, str] = {}
    for match in _TASK_SECTION_RE.finditer(body.strip()):
        sections[str(match.group("task_id"))] = str(match.group(0)).strip()
    return sections


def _render_task_section(*, task_id: str, run_id: str, findings: list[dict[str, str]], delivery_profile: str) -> str:
    grouped: dict[str, list[dict[str, str]]] = {"P2": [], "P3": [], "P4": []}
    for item in findings:
        sev = str(item.get("severity") or "").upper()
        if sev in grouped:
            grouped[sev].append(item)
    lines = [
        f"## Task {task_id}",
        f"- last_updated: {today_str()}",
        f"- latest_run_id: {run_id}",
        f"- delivery_profile: {delivery_profile}",
        "",
    ]
    for severity in ("P2", "P3", "P4"):
        items = grouped[severity]
        if not items:
            continue
        lines.append(f"### {severity}")
        for item in items:
            agent = str(item.get("agent") or "").strip()
            message = str(item.get("message") or "").strip()
            source_path = str(item.get("source_path") or "").strip()
            if source_path:
                lines.append(f"- [{agent}] {message} (`{source_path}`)")
            else:
                lines.append(f"- [{agent}] {message}")
        lines.append("")
    return "\n".join(lines).rstrip()


def update_technical_debt_register(
    *,
    doc_path: Path,
    task_id: str,
    run_id: str,
    findings: list[dict[str, str]],
    delivery_profile: str,
) -> dict[str, Any]:
    ensure_dir(doc_path.parent)
    original = doc_path.read_text(encoding="utf-8") if doc_path.exists() else _base_document()
    prefix, body, suffix = _split_document(original)
    sections = _parse_sections(body)
    if findings:
        sections[str(task_id)] = _render_task_section(
            task_id=str(task_id),
            run_id=str(run_id),
            findings=findings,
            delivery_profile=delivery_profile,
        )
        status = "updated"
    else:
        status = "removed" if sections.pop(str(task_id), None) else "noop"
    ordered = "\n\n".join(section for _, section in sorted(sections.items(), key=lambda item: int(item[0])))
    new_text = prefix + _BEGIN + "\n"
    if ordered:
        new_text += ordered + "\n"
    new_text += _END + suffix
    doc_path.write_text(new_text, encoding="utf-8")
    return {
        "status": status,
        "task_id": str(task_id),
        "run_id": str(run_id),
        "item_count": len(findings),
        "path": str(doc_path),
    }


def write_low_priority_debt_artifacts(
    *,
    out_dir: Path,
    summary: dict[str, Any],
    task_id: str,
    run_id: str,
    delivery_profile: str,
    root: Path | None = None,
) -> dict[str, Any]:
    root_dir = root or repo_root()
    findings_path = out_dir / "llm-review-low-priority-findings.json"
    llm_step = next((step for step in (summary.get("steps") or []) if isinstance(step, dict) and str(step.get("name") or "") == "sc-llm-review"), None)
    llm_step_status = str((llm_step or {}).get("status") or "").strip().lower()
    if llm_step_status != "ok" or not isinstance(summary.get("results"), list):
        payload = {
            "cmd": "sc-review-pipeline",
            "task_id": str(task_id),
            "run_id": str(run_id),
            "delivery_profile": str(delivery_profile),
            "item_count": 0,
            "findings": [],
            "register": {
                "status": "skipped",
                "reason": "llm_review_not_executed_or_no_results",
                "path": str(root_dir / "docs" / "technical-debt.md"),
            },
        }
        write_json(findings_path, payload)
        return {
            "findings_path": str(findings_path),
            "register_path": str(root_dir / "docs" / "technical-debt.md"),
            "item_count": 0,
            "register_status": "skipped",
        }
    findings = collect_low_priority_review_findings(summary=summary, root=root_dir)
    payload = {
        "cmd": "sc-review-pipeline",
        "task_id": str(task_id),
        "run_id": str(run_id),
        "delivery_profile": str(delivery_profile),
        "item_count": len(findings),
        "findings": findings,
    }
    write_json(findings_path, payload)
    register_result = update_technical_debt_register(
        doc_path=root_dir / "docs" / "technical-debt.md",
        task_id=str(task_id),
        run_id=str(run_id),
        findings=findings,
        delivery_profile=str(delivery_profile),
    )
    payload["register"] = register_result
    write_json(findings_path, payload)
    return {
        "findings_path": str(findings_path),
        "register_path": str(root_dir / "docs" / "technical-debt.md"),
        "item_count": len(findings),
        "register_status": register_result["status"],
    }
