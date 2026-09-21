#!/usr/bin/env python3
"""Guard a scripted Chapter 3 run so Attempt Preview is recorded at start and end."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Callable

from refresh_chapter_knowledge import (
    DEFAULT_COVERAGE_PATH,
    DEFAULT_TRIPLET_ATTESTATION_PATH,
    begin_run_attempt,
    run as refresh_knowledge,
)

DEFAULT_PATHS = {
    "source_manifest": "logs/ci/task-generation/source-manifest.v1.json",
    "ledger": "logs/ci/task-generation/source-blocks.v1.json",
    "semantics": "logs/ci/task-generation/semantic-requirements.v1.json",
    "capabilities": "logs/ci/task-generation/capabilities.v1.json",
    "edges": "logs/ci/task-generation/topology-edges.v1.json",
    "candidates": "logs/ci/task-generation/task-candidates.enriched.json",
    "report": "logs/ci/task-generation/semantic-conservation-report.json",
    "coverage": DEFAULT_COVERAGE_PATH.as_posix(),
    "triplet_attestation": DEFAULT_TRIPLET_ATTESTATION_PATH.as_posix(),
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
    triplet_status_on_success: str = "unknown",
    write_planning: bool = False,
    publish_if_eligible: bool = False,
    runner: Callable[..., subprocess.CompletedProcess[Any]] = subprocess.run,
) -> tuple[int, dict[str, Any]]:
    """Run one scripted Chapter 3 workflow command inside a refresh lifecycle guard."""
    if triplet_status_on_success not in {"passed", "blocked", "unknown"}:
        raise ValueError("invalid triplet_status_on_success")
    if not command:
        raise ValueError("guarded Chapter 3 run requires a child command")

    start_summary = begin_run_attempt(
        root,
        source="chapter3",
        trigger_run_id=trigger_run_id,
    )
    if _refresh_failed(start_summary):
        return 2, {
            "schema_version": "chapter3.guarded-run-summary.v1",
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

    triplet_status = triplet_status_on_success if child_rc == 0 else "blocked"
    try:
        final_summary = refresh_knowledge(
            root,
            source="chapter3",
            trigger_run_id=trigger_run_id,
            refresh_local=True,
            write_planning=write_planning,
            publish_if_eligible=publish_if_eligible,
            triplet_status=triplet_status,
            source_manifest_path=root / DEFAULT_PATHS["source_manifest"],
            ledger_path=root / DEFAULT_PATHS["ledger"],
            semantics_path=root / DEFAULT_PATHS["semantics"],
            capabilities_path=root / DEFAULT_PATHS["capabilities"],
            edges_path=root / DEFAULT_PATHS["edges"],
            candidates_path=root / DEFAULT_PATHS["candidates"],
            report_path=root / DEFAULT_PATHS["report"],
            coverage_path=root / DEFAULT_PATHS["coverage"],
            triplet_attestation_path=root / DEFAULT_PATHS["triplet_attestation"],
        )
    except Exception as exc:  # fail closed; the start attempt remains available
        final_summary = {
            "schema_version": "chapter-knowledge-refresh-summary.v1",
            "source": "chapter3",
            "trigger_run_id": trigger_run_id,
            "closure_passed": False,
            "chapter_closure_status": "knowledge_refresh_failed",
            "local_refresh_status": "failed",
            "local_refresh_failure_family": "guarded_final_refresh_failed",
            "local_refresh_reason": str(exc),
            "publication_status": "deferred",
            "publication_reason": "knowledge_refresh_failed",
        }

    closure_blocked = (
        child_rc == 0
        and triplet_status_on_success in {"passed", "blocked"}
        and not bool(final_summary.get("closure_passed"))
    )
    status = (
        "failed"
        if child_rc != 0 or _refresh_failed(final_summary) or closure_blocked
        else "ok"
    )
    summary = {
        "schema_version": "chapter3.guarded-run-summary.v1",
        "status": status,
        "trigger_run_id": trigger_run_id,
        "child_command": command,
        "child_returncode": child_rc,
        "child_error": child_error,
        "triplet_status": triplet_status,
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
    parser.add_argument(
        "--triplet-status-on-success",
        choices=["passed", "blocked", "unknown"],
        default="unknown",
    )
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
            triplet_status_on_success=args.triplet_status_on_success,
            write_planning=bool(args.write_planning_artifacts),
            publish_if_eligible=bool(args.publish_if_eligible),
        )
    except ValueError as exc:
        print(json.dumps({
            "schema_version": "chapter3.guarded-run-summary.v1",
            "status": "failed",
            "trigger_run_id": args.trigger_run_id,
            "reason": str(exc),
        }, ensure_ascii=False))
        return 2
    print(json.dumps(summary, ensure_ascii=False))
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
