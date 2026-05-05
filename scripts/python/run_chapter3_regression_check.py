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


def build_summary(repo_root: Path, out_dir: Path) -> dict[str, Any]:
    candidates = load_tasks(out_dir / "task-candidates.enriched.json")
    filtered = filtered_tasks_json(repo_root)
    coverage = json.loads((out_dir / "coverage-report.json").read_text(encoding="utf-8"))
    quality = json.loads((out_dir / "task-intents.quality.json").read_text(encoding="utf-8"))
    return {
        "schema": "chapter3.regression-check.v1",
        "generated_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "repo_root": str(repo_root),
        "simulation_dir": str(out_dir),
        "candidate_count": len(candidates),
        "filtered_tasks_json_count": len(filtered),
        "candidate_to_filtered_ratio": round(len(candidates) / len(filtered), 3) if filtered else None,
        "candidate_delta_vs_filtered": len(candidates) - len(filtered),
        "coverage_status": coverage.get("status"),
        "missing_blocking_count": coverage.get("missing_blocking_count"),
        "intent_quality_status": quality.get("status"),
        "intent_quality_issue_count": quality.get("issue_count"),
        "intent_quality_issue_counts": quality.get("issue_counts", {}),
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
            "scripts/python/extract_requirement_anchors.py",
            "--repo-root",
            str(repo_root),
            "--mode",
            args.mode,
            *add_typed_sources(args),
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
    run(template_root, ["py", "-3", "scripts/python/audit_task_candidate_coverage.py", "--repo-root", str(repo_root), "--requirements", str(requirements), "--candidates", str(enriched), "--out", str(coverage)])
    run(template_root, ["py", "-3", "scripts/python/compile_task_triplet.py", "--repo-root", str(repo_root), "--mode", args.mode, "--candidates", str(enriched), "--coverage", str(coverage), "--out", str(patch)])

    summary = build_summary(repo_root, out_dir)
    write_json(out_dir / "regression-summary.json", summary)
    print(
        "CHAPTER3_REGRESSION "
        f"repo={repo_root.name} candidates={summary['candidate_count']} "
        f"filtered_tasks={summary['filtered_tasks_json_count']} "
        f"coverage={summary['coverage_status']} quality={summary['intent_quality_status']} "
        f"out={out_dir / 'regression-summary.json'}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
