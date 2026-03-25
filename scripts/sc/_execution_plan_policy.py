from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


SC_DIR = Path(__file__).resolve().parent
PYTHON_DIR = SC_DIR.parent / "python"
for candidate in (SC_DIR, PYTHON_DIR):
    text = str(candidate)
    if text not in sys.path:
        sys.path.insert(0, text)

from _acceptance_testgen_refs import extract_acceptance_refs_with_anchors, is_allowed_test_path
from _recovery_doc_scaffold import (
    build_execution_plan_markdown,
    ensure_output_path,
    format_repo_path,
    infer_recovery_links,
    resolve_git_branch,
    resolve_git_head,
    write_markdown,
)


ACTIVE_PLAN_STATUSES = {"active", "paused", "blocked"}
FIELD_LINE_RE = re.compile(r"^- ([^:]+):\s*(.*)$")
TASK_ID_RE = re.compile(r"\b\d+\b")
TEST_ROOT_PREFIXES = ("Game.Core.Tests/", "Tests.Godot/tests/", "Tests/")


@dataclass(frozen=True)
class ExecutionPlanAssessment:
    task_id: str
    title: str
    refs_total: int
    allowed_refs: list[str]
    missing_refs: list[str]
    missing_refs_count: int
    anchor_count: int
    test_roots: list[str]
    signals: list[dict[str, Any]]
    threshold_hit: bool


def _parse_fields(path: Path) -> dict[str, str]:
    fields: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        match = FIELD_LINE_RE.match(raw_line.strip())
        if not match:
            continue
        fields[match.group(1).strip()] = match.group(2).strip()
    return fields


def _extract_task_ids(value: str) -> set[str]:
    return {match.group(0) for match in TASK_ID_RE.finditer(str(value or ""))}


def _iter_allowed_refs(*, triplet: Any, task_id: str) -> dict[str, list[dict[str, str]]]:
    by_ref: dict[str, list[dict[str, str]]] = {}
    for acceptance in ((triplet.back or {}).get("acceptance"), (triplet.gameplay or {}).get("acceptance")):
        mapping = extract_acceptance_refs_with_anchors(acceptance=acceptance, task_id=task_id)
        for ref, entries in mapping.items():
            normalized = str(ref or "").strip().replace("\\", "/")
            if not normalized or not is_allowed_test_path(normalized):
                continue
            existing = by_ref.setdefault(normalized, [])
            seen = {(item.get("anchor", ""), item.get("text", "")) for item in existing}
            for entry in entries:
                if not isinstance(entry, dict):
                    continue
                anchor = str(entry.get("anchor") or "").strip()
                text = str(entry.get("text") or "").strip()
                key = (anchor, text)
                if key in seen:
                    continue
                seen.add(key)
                existing.append({"anchor": anchor, "text": text})
    return by_ref


def _test_root_for_ref(ref: str) -> str:
    normalized = str(ref or "").strip().replace("\\", "/")
    for prefix in TEST_ROOT_PREFIXES:
        if normalized.startswith(prefix):
            return prefix.rstrip("/")
    return normalized.split("/", 1)[0] if normalized else ""


def assess_execution_plan_need(
    *,
    repo_root: Path,
    triplet: Any,
    task_id: str,
    tdd_stage: str,
    verify: str,
) -> ExecutionPlanAssessment:
    by_ref = _iter_allowed_refs(triplet=triplet, task_id=task_id)
    allowed_refs = sorted(by_ref.keys())
    missing_refs = [ref for ref in allowed_refs if not (repo_root / ref).exists()]
    anchor_count = sum(len(by_ref.get(ref, [])) for ref in allowed_refs)
    test_roots = sorted({_test_root_for_ref(ref) for ref in missing_refs if _test_root_for_ref(ref)})
    missing_suffixes = {Path(ref).suffix.lower() for ref in missing_refs}
    signal_specs = [
        ("missing_refs_ge_3", len(missing_refs) >= 3, f"missing_refs_count={len(missing_refs)} threshold=3"),
        ("mixed_cs_and_gd", ".cs" in missing_suffixes and ".gd" in missing_suffixes, f"suffixes={','.join(sorted(missing_suffixes)) or 'none'}"),
        ("red_first_stage", str(tdd_stage) == "red-first", f"tdd_stage={tdd_stage}"),
        ("verify_auto_or_all", str(verify) in {"auto", "all"}, f"verify={verify}"),
        ("anchors_ge_4", anchor_count >= 4, f"anchor_count={anchor_count} threshold=4"),
        ("multiple_test_roots", len(test_roots) >= 2, f"test_roots={','.join(test_roots) or 'none'}"),
    ]
    signals = [{"id": signal_id, "active": active, "detail": detail} for signal_id, active, detail in signal_specs]
    threshold_hit = sum(1 for item in signals if item["active"]) >= 2
    return ExecutionPlanAssessment(
        task_id=str(task_id),
        title=str((triplet.master or {}).get("title") or "").strip(),
        refs_total=len(allowed_refs),
        allowed_refs=allowed_refs,
        missing_refs=missing_refs,
        missing_refs_count=len(missing_refs),
        anchor_count=anchor_count,
        test_roots=test_roots,
        signals=signals,
        threshold_hit=threshold_hit,
    )


def find_active_execution_plans(root: Path, *, task_id: str) -> list[str]:
    plan_dir = root / "execution-plans"
    if not plan_dir.is_dir():
        return []
    matches: list[str] = []
    for path in sorted(plan_dir.glob("*.md")):
        upper = path.name.upper()
        if upper in {"README.MD", "TEMPLATE.MD"}:
            continue
        fields = _parse_fields(path)
        status = str(fields.get("Status") or "").strip().lower()
        if status not in ACTIVE_PLAN_STATUSES:
            continue
        task_ids = _extract_task_ids(fields.get("Related task id(s)", ""))
        if str(task_id) not in task_ids:
            continue
        matches.append(format_repo_path(root, path))
    return matches


def create_execution_plan_draft(
    *,
    repo_root: Path,
    task_id: str,
    title: str,
    assessment: ExecutionPlanAssessment,
    latest_json: str = "",
) -> str:
    title_text = f"Task {task_id} acceptance-test generation plan"
    if title:
        title_text = f"Task {task_id} {title} acceptance-test generation plan"
    scope_refs = ", ".join(assessment.missing_refs[:3]) if assessment.missing_refs else "no missing refs detected"
    if len(assessment.missing_refs) > 3:
        scope_refs += ", ..."
    content = build_execution_plan_markdown(
        root=repo_root,
        title=title_text,
        status="active",
        goal=f"Control acceptance-driven test generation complexity for task {task_id}.",
        scope=(
            f"{assessment.missing_refs_count} missing refs across {len(assessment.test_roots)} test roots; "
            f"seed refs: {scope_refs}"
        ),
        current_step="Review missing acceptance refs and choose the first safe red step.",
        stop_loss="Do not start Codex test generation until the ref mix and verify mode are explicit.",
        next_action="Run llm_generate_tests_from_acceptance_refs.py after confirming the sequence for missing refs.",
        exit_criteria="The next acceptance-driven test generation step is explicit and low-ambiguity.",
        related_adrs=[],
        related_decision_logs=[],
        links=infer_recovery_links(root=repo_root, task_id=task_id, latest_json=latest_json),
        branch=resolve_git_branch(repo_root),
        git_head=resolve_git_head(repo_root),
    )
    out_path = ensure_output_path(repo_root, "", "execution-plans", title_text)
    write_markdown(out_path, content)
    return format_repo_path(repo_root, out_path)
