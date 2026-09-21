#!/usr/bin/env python3
"""Audit semantic Requirement to Task sink coverage.

Legacy P0/P1 anchor coverage remains available as a downstream packaging gate.
When validated semantic requirements are present, active delivery requirements
must have a Task or explicit non-Task sink.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path
from typing import Any

BLOCKING_PRIORITIES = {"P0", "P1"}
NON_TASK_SINK_TYPES = {"global_constraint", "quality_gate", "adr", "adr_owned", "deferred", "exclusion"}
DEFAULT_TASK_VIEWS = [
    ".taskmaster/tasks/tasks_back.json",
    ".taskmaster/tasks/tasks_gameplay.json",
]


def load_json(path: Path, default: Any = None) -> Any:
    if not path.is_file():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def candidate_coverage(candidates: dict[str, Any]) -> tuple[dict[str, list[str]], list[dict[str, Any]]]:
    by_req: dict[str, list[str]] = {}
    rows = [row for row in candidates.get("candidates", []) if isinstance(row, dict)]
    for task in rows:
        tid = str(task.get("id", ""))
        refs = task.get("semantic_refs", task.get("requirement_ids", []))
        if not isinstance(refs, list):
            continue
        for rid in refs:
            by_req.setdefault(str(rid), []).append(tid)
    return by_req, rows


def audit_legacy(requirements: dict[str, Any], candidates: dict[str, Any]) -> dict[str, Any]:
    by_req, _tasks = candidate_coverage(candidates)
    rows = []
    missing_blocking = []
    for anchor in requirements.get("anchors", []):
        rid = str(anchor.get("requirement_id"))
        covered = sorted(set(by_req.get(rid, [])))
        priority = str(anchor.get("priority", "P2")).upper()
        status = "covered" if covered else "missing"
        row = {
            "requirement_id": rid,
            "priority": priority,
            "kind": anchor.get("kind"),
            "source": f"{anchor.get('source_path')}:{anchor.get('line')}",
            "coverage_status": status,
            "covered_by_tasks": covered,
        }
        rows.append(row)
        if status == "missing" and priority in BLOCKING_PRIORITIES:
            missing_blocking.append(row)
    return {
        "schema": "task-generation.coverage-report.v1",
        "coverage_model": "legacy-p0-p1-packaging",
        "generated_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "requirement_count": len(rows),
        "candidate_count": len(candidates.get("candidates", [])),
        "missing_count": sum(1 for row in rows if row["coverage_status"] == "missing"),
        "missing_blocking_count": len(missing_blocking),
        "status": "ok" if not missing_blocking else "blocked",
        "coverage": rows,
        "missing_blocking": missing_blocking,
        "invalid_task_semantic_refs": [],
    }


def audit_semantic(
    semantics: dict[str, Any],
    candidates: dict[str, Any],
    legacy_requirements: dict[str, Any] | None = None,
    existing_tasks: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    by_req, tasks = candidate_coverage(candidates)
    requirements = {
        str(row.get("requirement_id")): row
        for row in semantics.get("requirements", [])
        if isinstance(row, dict) and row.get("requirement_id")
    }
    invalid_refs = []
    for task in tasks:
        task_id = str(task.get("id", ""))
        refs = task.get("semantic_refs", task.get("requirement_ids", []))
        if not isinstance(refs, list):
            invalid_refs.append({"task_id": task_id, "reason": "invalid_ref_shape"})
            continue
        for rid in refs:
            rid_text = str(rid)
            requirement = requirements.get(rid_text)
            if requirement is None:
                invalid_refs.append({
                    "task_id": task_id,
                    "requirement_id": rid_text,
                    "reason": "unknown_requirement",
                })
                continue
            if str(requirement.get("status", "active")).casefold() in {"removed", "superseded"}:
                invalid_refs.append({
                    "task_id": task_id,
                    "requirement_id": rid_text,
                    "reason": "stale_requirement",
                })
    candidate_by_id = {
        str(task.get("id")): task
        for task in tasks
        if task.get("id") is not None
    }
    stale_existing = []
    for task in existing_tasks or []:
        if not isinstance(task, dict) or task.get("id") is None:
            continue
        task_id = str(task.get("id"))
        refs = task.get("semantic_refs")
        if not isinstance(refs, list) or not refs:
            continue
        stale = sorted({
            str(rid)
            for rid in refs
            if (
                str(rid) not in requirements
                or str(requirements[str(rid)].get("status", "active")).casefold()
                in {"removed", "superseded"}
            )
        })
        if not stale:
            continue
        replacement = candidate_by_id.get(task_id)
        replacement_refs = (
            replacement.get("semantic_refs", replacement.get("requirement_ids", []))
            if isinstance(replacement, dict) else []
        )
        reconciled = (
            isinstance(replacement_refs, list)
            and bool(replacement_refs)
            and all(
                str(rid) in requirements
                and str(requirements[str(rid)].get("status", "active")).casefold() == "active"
                for rid in replacement_refs
            )
        )
        if not reconciled:
            stale_existing.append({
                "task_id": task_id,
                "stale_requirement_ids": stale,
                "reason": "existing_task_semantic_mapping_stale",
                "reconcile": "update or remove the stale semantic mapping before triplet write",
            })

    rows = []
    missing = []
    for rid, requirement in sorted(requirements.items()):
        if str(requirement.get("status", "active")).casefold() != "active":
            continue
        if requirement.get("delivery_relevant") is not True:
            continue
        tasks_for_requirement = sorted(set(by_req.get(rid, [])))
        non_task_sinks = [
            sink for sink in requirement.get("non_task_sinks", [])
            if isinstance(sink, dict)
            and str(sink.get("type") or "") in NON_TASK_SINK_TYPES
            and str(sink.get("id") or "").strip()
        ]
        covered = bool(tasks_for_requirement or non_task_sinks)
        row = {
            "requirement_id": rid,
            "priority": str(requirement.get("priority") or "P2").upper(),
            "kind": requirement.get("kind"),
            "source_block_ids": list(requirement.get("source_block_ids", [])),
            "coverage_status": "covered" if covered else "missing",
            "covered_by_tasks": tasks_for_requirement,
            "non_task_sinks": non_task_sinks,
        }
        rows.append(row)
        if not covered:
            missing.append(row)
    semantic_blocks = {
        rid: {str(value) for value in row.get("source_block_ids", [])}
        for rid, row in requirements.items()
    }
    covered_blocks: set[str] = set()
    for rid, task_ids in by_req.items():
        if task_ids:
            covered_blocks.update(semantic_blocks.get(rid, set()))
    for rid, requirement in requirements.items():
        non_task_sinks = [
            sink for sink in requirement.get("non_task_sinks", [])
            if isinstance(sink, dict)
            and str(sink.get("type") or "") in NON_TASK_SINK_TYPES
            and str(sink.get("id") or "").strip()
        ]
        if non_task_sinks:
            covered_blocks.update(semantic_blocks.get(rid, set()))

    packaging_rows = []
    packaging_missing = []
    for anchor in (legacy_requirements or {}).get("anchors", []):
        if not isinstance(anchor, dict):
            continue
        priority = str(anchor.get("priority", "P2")).upper()
        if priority not in BLOCKING_PRIORITIES:
            continue
        block_id = str(anchor.get("source_block_id") or "")
        covered = bool(block_id and block_id in covered_blocks)
        row = {
            "requirement_id": str(anchor.get("requirement_id") or ""),
            "source_block_id": block_id,
            "priority": priority,
            "coverage_status": "covered" if covered else "missing",
        }
        packaging_rows.append(row)
        if not covered:
            packaging_missing.append(row)

    blocked = bool(missing or invalid_refs or stale_existing or packaging_missing)
    return {
        "schema": "task-generation.coverage-report.v2",
        "coverage_model": "semantic-sink",
        "generated_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "source_revision": semantics.get("source_revision"),
        "source_manifest_sha256": semantics.get("source_manifest_sha256"),
        "requirement_count": len(rows),
        "candidate_count": len(tasks),
        "missing_count": len(missing),
        "missing_blocking_count": len(missing),
        "status": "blocked" if blocked else "ok",
        "coverage": rows,
        "missing_blocking": missing,
        "invalid_task_semantic_refs": invalid_refs,
        "stale_existing_task_mappings": stale_existing,
        "source_coverage": semantics.get("source_accounting", []),
        "legacy_p0_p1_packaging": {
            "checked_count": len(packaging_rows),
            "missing_count": len(packaging_missing),
            "status": "ok" if not packaging_missing else "blocked",
            "coverage": packaging_rows,
            "missing": packaging_missing,
        },
    }


def audit(
    requirements: dict[str, Any],
    candidates: dict[str, Any],
    legacy_requirements: dict[str, Any] | None = None,
    existing_tasks: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    if requirements.get("schema_version") == "newrouge.semantic-requirements.v1":
        return audit_semantic(requirements, candidates, legacy_requirements, existing_tasks)
    return audit_legacy(requirements, candidates)


def blocking_after_p1_waiver(result: dict[str, Any]) -> list[dict[str, Any]]:
    """Return blockers that --allow-missing-p1 is never allowed to waive."""
    blockers: list[dict[str, Any]] = []
    if result.get("coverage_model") == "semantic-sink":
        blockers.extend(
            {"kind": "semantic_sink", **row}
            for row in result.get("missing_blocking", [])
            if isinstance(row, dict)
        )
        blockers.extend(
            {"kind": "invalid_task_semantic_ref", **row}
            for row in result.get("invalid_task_semantic_refs", [])
            if isinstance(row, dict)
        )
        blockers.extend(
            {"kind": "stale_existing_task_mapping", **row}
            for row in result.get("stale_existing_task_mappings", [])
            if isinstance(row, dict)
        )
        packaging = result.get("legacy_p0_p1_packaging", {})
        blockers.extend(
            {"kind": "legacy_packaging", **row}
            for row in packaging.get("missing", [])
            if isinstance(row, dict) and str(row.get("priority", "")).upper() != "P1"
        )
        return blockers

    blockers.extend(
        {"kind": "legacy_packaging", **row}
        for row in result.get("missing_blocking", [])
        if isinstance(row, dict) and str(row.get("priority", "")).upper() != "P1"
    )
    return blockers


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--requirements", default="logs/ci/task-generation/requirements.index.json")
    parser.add_argument("--semantics", default="logs/ci/task-generation/semantic-requirements.v1.json")
    parser.add_argument("--candidates", default="logs/ci/task-generation/task-candidates.enriched.json")
    parser.add_argument("--out", default="logs/ci/task-generation/coverage-report.json")
    parser.add_argument("--allow-missing-p1", action="store_true")
    parser.add_argument(
        "--task-view",
        action="append",
        default=[],
        help="Existing task view to inspect for stale semantic mappings; defaults to tasks_back/tasks_gameplay.",
    )
    args = parser.parse_args(argv)
    root = Path(args.repo_root).resolve()
    semantics_path = root / args.semantics
    source = load_json(semantics_path) if semantics_path.is_file() else load_json(root / args.requirements, {})
    legacy = load_json(root / args.requirements, {"anchors": []}) if semantics_path.is_file() else None
    task_view_paths = args.task_view or DEFAULT_TASK_VIEWS
    existing_tasks: list[dict[str, Any]] = []
    for value in task_view_paths:
        payload = load_json(root / value, [])
        if isinstance(payload, list):
            existing_tasks.extend(row for row in payload if isinstance(row, dict))
    result = audit(
        source,
        load_json(root / args.candidates, {"candidates": []}),
        legacy,
        existing_tasks,
    )
    out = root / args.out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        f"coverage_report={out} model={result['coverage_model']} "
        f"status={result['status']} missing_blocking={result['missing_blocking_count']}"
    )
    if result["status"] == "ok":
        return 0
    if not args.allow_missing_p1:
        return 2
    remaining = blocking_after_p1_waiver(result)
    if remaining:
        print(
            "coverage_waiver_rejected="
            + json.dumps(remaining[:20], ensure_ascii=False, separators=(",", ":"))
        )
        return 2
    print("coverage_waiver=legacy_p1_packaging_only")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
