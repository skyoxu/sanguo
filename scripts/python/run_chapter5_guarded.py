#!/usr/bin/env python3
"""Guard a scripted Chapter 5 run so Attempt Preview is recorded at start and end."""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
from typing import Any, Callable

from refresh_chapter_knowledge import begin_run_attempt, record_run_failure_attempt, run as refresh_knowledge

DEFAULT_PATHS = {
    "source_manifest": "logs/ci/task-generation/source-manifest.v1.json",
    "ledger": "logs/ci/task-generation/source-blocks.v1.json",
    "semantics": "logs/ci/task-generation/semantic-requirements.v1.json",
    "capabilities": "logs/ci/task-generation/capabilities.v1.json",
    "edges": "logs/ci/task-generation/topology-edges.v1.json",
    "candidates": "logs/ci/task-generation/task-candidates.enriched.json",
    "report": "logs/ci/task-generation/semantic-conservation-report.json",
    "coverage": "logs/ci/task-generation/coverage-report.json",
    "triplet_attestation": "logs/ci/task-generation/triplet-baseline-attestation.json",
    "reconciliation": "logs/ci/chapter5/reconciliation/latest.json",
    "readiness": "logs/ci/chapter5/readiness/latest.json",
}


def _refresh_failed(summary: dict[str, Any]) -> bool:
    return (
        summary.get("local_refresh_status") == "failed"
        or summary.get("chapter_closure_status") == "knowledge_refresh_failed"
        or summary.get("publication_status") == "failed"
    )


def run_guarded(
    root: Path,
    *,
    trigger_run_id: str,
    command: list[str],
    write_planning: bool = False,
    publish_if_eligible: bool = False,
    runner: Callable[..., subprocess.CompletedProcess[Any]] = subprocess.run,
) -> tuple[int, dict[str, Any]]:
    if not command:
        raise ValueError("guarded Chapter 5 run requires a child command")

    start_summary = begin_run_attempt(root, source="chapter5", trigger_run_id=trigger_run_id)
    if _refresh_failed(start_summary):
        return 2, {
            "schema_version": "chapter5.guarded-run-summary.v1",
            "status": "failed",
            "trigger_run_id": trigger_run_id,
            "child_returncode": None,
            "start_refresh": start_summary,
            "final_refresh": None,
        }

    child_rc = 127
    child_error: str | None = None
    try:
        completed = runner(command, cwd=root, text=True, check=False)
        child_rc = int(completed.returncode)
    except OSError as exc:
        child_error = str(exc)

    try:
        if child_rc != 0:
            final_summary = record_run_failure_attempt(
                root,
                source="chapter5",
                trigger_run_id=trigger_run_id,
                reason=child_error or f"guarded Chapter 5 child failed with rc={child_rc}",
            )
        else:
            final_summary = refresh_knowledge(
                root,
                source="chapter5",
                trigger_run_id=trigger_run_id,
                refresh_local=True,
                write_planning=write_planning,
                publish_if_eligible=publish_if_eligible,
                triplet_status="unknown",
                source_manifest_path=root / DEFAULT_PATHS["source_manifest"],
                ledger_path=root / DEFAULT_PATHS["ledger"],
                semantics_path=root / DEFAULT_PATHS["semantics"],
                capabilities_path=root / DEFAULT_PATHS["capabilities"],
                edges_path=root / DEFAULT_PATHS["edges"],
                candidates_path=root / DEFAULT_PATHS["candidates"],
                report_path=root / DEFAULT_PATHS["report"],
                coverage_path=root / DEFAULT_PATHS["coverage"],
                triplet_attestation_path=root / DEFAULT_PATHS["triplet_attestation"],
                reconciliation_path=root / DEFAULT_PATHS["reconciliation"],
                readiness_path=root / DEFAULT_PATHS["readiness"],
            )
    except Exception as exc:
        final_summary = {
            "schema_version": "chapter-knowledge-refresh-summary.v1",
            "source": "chapter5",
            "trigger_run_id": trigger_run_id,
            "closure_passed": False,
            "chapter_closure_status": "knowledge_refresh_failed",
            "local_refresh_status": "failed",
            "local_refresh_failure_family": "guarded_final_refresh_failed",
            "local_refresh_reason": str(exc),
            "publication_status": "deferred",
            "publication_reason": "knowledge_refresh_failed",
        }

    closure_blocked = child_rc == 0 and not bool(final_summary.get("closure_passed"))
    status = "failed" if child_rc != 0 or _refresh_failed(final_summary) or closure_blocked else "ok"
    summary = {
        "schema_version": "chapter5.guarded-run-summary.v1",
        "status": status,
        "trigger_run_id": trigger_run_id,
        "child_command": command,
        "child_returncode": child_rc,
        "child_error": child_error,
        "start_refresh": start_summary,
        "final_refresh": final_summary,
    }
    if child_rc != 0:
        return child_rc, summary
    return (2 if _refresh_failed(final_summary) or closure_blocked else 0), summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--trigger-run-id", required=True)
    parser.add_argument("--write-planning-artifacts", action="store_true")
    parser.add_argument("--publish-if-eligible", action="store_true")
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args(argv)
    command = list(args.command)
    if command and command[0] == "--":
        command = command[1:]
    try:
        rc, summary = run_guarded(
            Path(args.repo_root).resolve(),
            trigger_run_id=args.trigger_run_id,
            command=command,
            write_planning=bool(args.write_planning_artifacts),
            publish_if_eligible=bool(args.publish_if_eligible),
        )
    except ValueError as exc:
        print(json.dumps({
            "schema_version": "chapter5.guarded-run-summary.v1",
            "status": "failed",
            "trigger_run_id": args.trigger_run_id,
            "reason": str(exc),
        }, ensure_ascii=False))
        return 2
    print(json.dumps(summary, ensure_ascii=False))
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
