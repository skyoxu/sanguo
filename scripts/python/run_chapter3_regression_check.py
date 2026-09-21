#!/usr/bin/env python3
"""Run a read-only Chapter 3 regression simulation for a business repository."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import subprocess
from pathlib import Path
from typing import Any


def load_tasks(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, list):
        return [x for x in data if isinstance(x, dict)]
    if isinstance(data, dict):
        if isinstance(data.get("candidates"), list):
            return [x for x in data["candidates"] if isinstance(x, dict)]
        if isinstance(data.get("tasks"), list):
            return [x for x in data["tasks"] if isinstance(x, dict)]
        master = data.get("master")
        if isinstance(master, dict) and isinstance(master.get("tasks"), list):
            return [x for x in master["tasks"] if isinstance(x, dict)]
    return []


def norm_id(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    return text[:-2] if text.endswith(".0") else text


def labels(task: dict[str, Any]) -> set[str]:
    return {str(x).lower() for x in task.get("labels", [])}


def is_obvious_post_ch3(task: dict[str, Any]) -> bool:
    task_labels = labels(task)
    title = str(task.get("title", "")).lower()
    if "chapter7-ui" in task_labels or title.startswith("wire ui:") or task.get("ui_wiring_candidate"):
        return True
    if "split" in task_labels or "complexity" in task_labels or "split from" in title:
        return True
    post_terms = [
        "closure",
        "hard-gate",
        "gate closure",
        "promote",
        "runtime effects",
        "shared run trigger",
        "resume evidence",
        "invalid-definition fallback",
    ]
    return any(term in title for term in post_terms)


def taskmaster_ids(tasks: list[dict[str, Any]]) -> set[str]:
    return {norm_id(task.get("taskmaster_id")) for task in tasks if norm_id(task.get("taskmaster_id"))}


def filtered_tasks_json(repo_root: Path) -> list[dict[str, Any]]:
    tasks = load_tasks(repo_root / ".taskmaster" / "tasks" / "tasks.json")
    back_ids = taskmaster_ids(load_tasks(repo_root / ".taskmaster" / "tasks" / "tasks_back.json"))
    gameplay_ids = taskmaster_ids(load_tasks(repo_root / ".taskmaster" / "tasks" / "tasks_gameplay.json"))
    out: list[dict[str, Any]] = []
    for task in tasks:
        if is_obvious_post_ch3(task):
            continue
        task_id = norm_id(task.get("id"))
        if task_id and task_id in back_ids and task_id not in gameplay_ids:
            continue
        out.append(task)
    return out


def add_typed_sources(args: argparse.Namespace) -> list[str]:
    out: list[str] = []
    for flag, values in [
        ("--prd-path", args.prd_path),
        ("--gdd-path", args.gdd_path),
        ("--epics-path", args.epics_path),
        ("--stories-path", args.stories_path),
        ("--source-glob", args.source_glob),
    ]:
        for value in values:
            out.extend([flag, value])
    return out


def run(template_root: Path, command: list[str]) -> None:
    subprocess.run(command, cwd=template_root, check=True)


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")


def repo_slug(repo_root: Path) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "-", repo_root.name).strip("-") or "repo"


def build_summary(
    repo_root: Path,
    out_dir: Path,
    semantic_requirements: Path | None = None,
) -> dict[str, Any]:
    candidates = load_tasks(out_dir / "task-candidates.enriched.json")
    filtered = filtered_tasks_json(repo_root)
    coverage = json.loads((out_dir / "coverage-report.json").read_text(encoding="utf-8"))
    quality = json.loads((out_dir / "task-intents.quality.json").read_text(encoding="utf-8"))
    ledger = json.loads((out_dir / "source-blocks.v1.json").read_text(encoding="utf-8"))
    legacy_index = json.loads((out_dir / "requirements.index.json").read_text(encoding="utf-8"))

    blocks = [row for row in ledger.get("blocks", []) if isinstance(row, dict)]
    semantic_doc: dict[str, Any] | None = None
    if semantic_requirements is not None and semantic_requirements.is_file():
        payload = json.loads(semantic_requirements.read_text(encoding="utf-8"))
        if payload.get("schema_version") == "newrouge.semantic-requirements.v1":
            semantic_doc = payload

    source_layer = {
        "status": "complete" if blocks else "empty",
        "source_block_count": len(blocks),
        "source_count": len({
            str(row.get("source_path")) for row in blocks if row.get("source_path")
        }),
        "parser_inventory": ledger.get("parser_inventory", {}),
        "delta": ledger.get("delta", {}),
    }

    if semantic_doc is None:
        semantic_layer = {
            "status": "not_run",
            "reason": "no reviewed semantic-requirements input supplied",
            "requirement_count": None,
            "delivery_requirement_count": None,
            "accounted_block_count": None,
            "source_accounting_coverage": None,
        }
    else:
        requirements = [
            row for row in semantic_doc.get("requirements", [])
            if isinstance(row, dict)
        ]
        accounting = [
            row for row in semantic_doc.get("source_accounting", [])
            if isinstance(row, dict) and row.get("block_id")
        ]
        accounted_ids = {str(row["block_id"]) for row in accounting}
        delivery = [
            row for row in requirements
            if row.get("delivery_relevant") is True
            and str(row.get("status", "active")).casefold() == "active"
        ]
        semantic_layer = {
            "status": "available",
            "source_revision": semantic_doc.get("source_revision"),
            "requirement_count": len(requirements),
            "delivery_requirement_count": len(delivery),
            "accounted_block_count": len(accounted_ids),
            "source_accounting_coverage": (
                round(len(accounted_ids) / len(blocks), 6) if blocks else 1.0
            ),
            "unresolved_delivery_potential_count": sum(
                1 for row in accounting
                if str(row.get("disposition") or "").casefold() == "unresolved"
                and row.get("delivery_potential") is True
            ),
        }

    task_layer = {
        "status": coverage.get("status"),
        "candidate_count": len(candidates),
        "mature_filtered_task_count": len(filtered),
        "candidate_to_filtered_ratio": (
            round(len(candidates) / len(filtered), 3) if filtered else None
        ),
        "candidate_delta_vs_filtered": len(candidates) - len(filtered),
        "coverage_model": coverage.get("coverage_model"),
        "missing_blocking_count": coverage.get("missing_blocking_count"),
        "intent_quality_status": quality.get("status"),
        "intent_quality_issue_count": quality.get("issue_count"),
    }

    legacy_anchor_count = len(legacy_index.get("anchors", []))
    return {
        "schema": "chapter3.regression-check.v2",
        "generated_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "repo_root": str(repo_root),
        "simulation_dir": str(out_dir),
        "layers": {
            "source": source_layer,
            "semantic": semantic_layer,
            "task": task_layer,
        },
        "shadow_compare": {
            "legacy_requirement_anchor_count": legacy_anchor_count,
            "source_block_count": len(blocks),
            "legacy_anchor_to_source_block_ratio": (
                round(legacy_anchor_count / len(blocks), 4) if blocks else None
            ),
            "mature_filtered_task_count": len(filtered),
            "candidate_count": len(candidates),
            "candidate_delta_vs_filtered": len(candidates) - len(filtered),
            "semantic_requirement_count": (
                semantic_layer.get("requirement_count")
                if semantic_layer.get("status") == "available" else None
            ),
        },
        # Compatibility keys retained for existing report consumers.
        "candidate_count": len(candidates),
        "filtered_tasks_json_count": len(filtered),
        "candidate_to_filtered_ratio": task_layer["candidate_to_filtered_ratio"],
        "candidate_delta_vs_filtered": task_layer["candidate_delta_vs_filtered"],
        "coverage_status": coverage.get("status"),
        "missing_blocking_count": coverage.get("missing_blocking_count"),
        "intent_quality_status": quality.get("status"),
        "intent_quality_issue_count": quality.get("issue_count"),
        "intent_quality_issue_counts": quality.get("issue_counts", {}),
        "source_block_count": len(blocks),
        "legacy_requirement_anchor_count": legacy_anchor_count,
        "legacy_anchor_to_source_block_ratio": (
            round(legacy_anchor_count / len(blocks), 4) if blocks else None
        ),
        "source_parser_inventory": ledger.get("parser_inventory", {}),
    }

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run a read-only Chapter 3 regression simulation.")
    parser.add_argument("business_repo", help="Business repository path.")
    parser.add_argument("--template-root", default=".")
    parser.add_argument("--out-dir", default="")
    parser.add_argument("--id-prefix", default="INT")
    parser.add_argument("--mode", choices=["init", "add"], default="init")
    parser.add_argument("--split-profile", choices=["compact", "balanced", "expanded"], default="balanced")
    parser.add_argument("--prd-path", action="append", default=[])
    parser.add_argument("--gdd-path", action="append", default=[])
    parser.add_argument("--epics-path", action="append", default=[])
    parser.add_argument("--stories-path", action="append", default=[])
    parser.add_argument("--source-glob", action="append", default=[])
    parser.add_argument(
        "--semantic-requirements",
        default="",
        help="Optional reviewed semantic-requirements.v1.json used only for semantic-layer shadow metrics.",
    )
    args = parser.parse_args(argv)

    template_root = Path(args.template_root).resolve()
    repo_root = Path(args.business_repo).resolve()
    if not (template_root / "workflow.md").exists():
        raise SystemExit(f"workflow.md not found under {template_root}")
    if not repo_root.exists():
        raise SystemExit(f"business repo not found: {repo_root}")

    out_dir = Path(args.out_dir) if args.out_dir else template_root / "logs" / "analysis" / "chapter3-regression" / repo_slug(repo_root)
    if not out_dir.is_absolute():
        out_dir = template_root / out_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    source_manifest = out_dir / "source-manifest.v1.json"
    source_blocks = out_dir / "source-blocks.v1.json"
    requirements = out_dir / "requirements.index.json"
    intents = out_dir / "task-intents.normalized.json"
    quality = out_dir / "task-intents.quality.json"
    candidates = out_dir / "task-candidates.normalized.json"
    enriched = out_dir / "task-candidates.enriched.json"
    coverage = out_dir / "coverage-report.json"
    patch = out_dir / "task-triplet.patch.json"

    run(
        template_root,
        [
            "py",
            "-3",
            "scripts/python/build_source_ledger.py",
            "--repo-root",
            str(repo_root),
            "--mode",
            args.mode,
            *add_typed_sources(args),
            "--manifest-out",
            str(source_manifest),
            "--out",
            str(source_blocks),
        ],
    )
    run(
        template_root,
        [
            "py",
            "-3",
            "scripts/python/extract_requirement_anchors.py",
            "--repo-root",
            str(repo_root),
            "--mode",
            args.mode,
            "--ledger-input",
            str(source_blocks),
            "--out",
            str(requirements),
        ],
    )
    run(
        template_root,
        [
            "py",
            "-3",
            "scripts/python/normalize_task_intents.py",
            "--repo-root",
            str(repo_root),
            "--mode",
            args.mode,
            "--id-prefix",
            args.id_prefix,
            "--requirements",
            str(requirements),
            "--semantics",
            str(out_dir / "legacy-shadow-no-semantics.json"),
            "--split-profile",
            args.split_profile,
            "--out",
            str(intents),
        ],
    )
    run(template_root, ["py", "-3", "scripts/python/audit_task_intents_quality.py", "--intents", str(intents), "--out", str(quality)])
    run(
        template_root,
        [
            "py",
            "-3",
            "scripts/python/generate_task_candidates_from_sources.py",
            "--repo-root",
            str(repo_root),
            "--mode",
            args.mode,
            "--id-prefix",
            args.id_prefix,
            "--requirements",
            str(requirements),
            "--intents",
            str(intents),
            "--out",
            str(candidates),
        ],
    )
    run(template_root, ["py", "-3", "scripts/python/enrich_task_candidates.py", "--repo-root", str(repo_root), "--candidates", str(candidates), "--out", str(enriched)])
    run(template_root, [
        "py", "-3", "scripts/python/audit_task_candidate_coverage.py",
        "--repo-root", str(repo_root),
        "--requirements", str(requirements),
        "--semantics", str(out_dir / "legacy-shadow-no-semantics.json"),
        "--candidates", str(enriched),
        "--out", str(coverage),
    ])
    run(template_root, ["py", "-3", "scripts/python/compile_task_triplet.py", "--repo-root", str(repo_root), "--mode", args.mode, "--candidates", str(enriched), "--coverage", str(coverage), "--out", str(patch)])

    semantic_path = None
    if args.semantic_requirements:
        semantic_path = Path(args.semantic_requirements)
        if not semantic_path.is_absolute():
            semantic_path = repo_root / semantic_path
    summary = build_summary(repo_root, out_dir, semantic_path)
    write_json(out_dir / "regression-summary.json", summary)
    print(
        "CHAPTER3_REGRESSION "
        f"repo={repo_root.name} candidates={summary['candidate_count']} "
        f"filtered_tasks={summary['filtered_tasks_json_count']} "
        f"coverage={summary['coverage_status']} quality={summary['intent_quality_status']} "
        f"source_blocks={summary['source_block_count']} legacy_anchors={summary['legacy_requirement_anchor_count']} "
        f"semantic={summary['layers']['semantic']['status']} "
        f"out={out_dir / 'regression-summary.json'}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
