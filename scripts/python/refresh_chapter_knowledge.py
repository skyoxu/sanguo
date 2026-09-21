#!/usr/bin/env python3
"""Refresh registered Chapter closure topology without weakening KCP authority."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

from _semantic_topology import TOPOLOGY_ARTIFACTS, build_topology_view, unavailable_topology
from audit_task_candidate_coverage import DEFAULT_TASK_VIEWS, audit as audit_task_coverage
from validate_semantic_conservation import validate as validate_semantic_conservation
from chapter5_semantic_reconciliation import (
    DEFAULT_READINESS_DIR as CH5_READINESS_DIR,
    DEFAULT_RECONCILIATION_DIR as CH5_RECONCILIATION_DIR,
    READINESS_SCHEMA as CH5_READINESS_SCHEMA,
    RECONCILIATION_SCHEMA as CH5_RECONCILIATION_SCHEMA,
    validate_chapter5_evidence_freshness,
)

TOPOLOGY_RUNTIME_DIR = Path("logs/ci/project-health-knowledge/topology")
ATTEMPT_PATH = TOPOLOGY_RUNTIME_DIR / "workspace-last-attempt.json"
LEGACY_ATTEMPT_PATH = TOPOLOGY_RUNTIME_DIR / "workspace-latest.json"
STABLE_PATH = TOPOLOGY_RUNTIME_DIR / "workspace-latest-successful.json"
CHAPTER5_STABLE_PATH = TOPOLOGY_RUNTIME_DIR / "workspace-latest-stabilized.json"
REGISTERED_SOURCES = {"chapter3", "chapter5"}
DEFAULT_COVERAGE_PATH = Path("logs/ci/task-generation/coverage-report.json")
DEFAULT_LEGACY_REQUIREMENTS_PATH = Path("logs/ci/task-generation/requirements.index.json")
DEFAULT_TRIPLET_ATTESTATION_PATH = Path(
    "logs/ci/task-generation/triplet-baseline-attestation.json"
)
DEFAULT_CH5_RECONCILIATION_PATH = CH5_RECONCILIATION_DIR / "latest.json"
DEFAULT_CH5_READINESS_PATH = CH5_READINESS_DIR / "latest.json"
TRIPLET_TASK_FILES = [
    ".taskmaster/tasks/tasks.json",
    ".taskmaster/tasks/tasks_back.json",
    ".taskmaster/tasks/tasks_gameplay.json",
]
TRIPLET_REQUIRED_CHECKS = {
    "task_links_validate",
    "check_tasks_all_refs",
    "validate_task_master_triplet",
    "validate_semantic_review_tier",
}


def load_json(path: Path, default: Any = None) -> Any:
    if not path.is_file():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    """Atomically replace JSON so a failed refresh cannot corrupt prior stable state."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    try:
        tmp.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
            newline="\n",
        )
        tmp.replace(path)
    finally:
        if tmp.exists():
            try:
                tmp.unlink()
            except OSError:
                pass


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _snapshot_file(path: Path) -> bytes | None:
    return path.read_bytes() if path.is_file() else None


def _restore_file(path: Path, snapshot: bytes | None) -> None:
    if snapshot is None:
        if path.exists():
            path.unlink()
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".restore.tmp")
    try:
        tmp.write_bytes(snapshot)
        tmp.replace(path)
    finally:
        if tmp.exists():
            try:
                tmp.unlink()
            except OSError:
                pass


def _canonical_payload_sha(payload: Any) -> str:
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def chapter5_closure_evidence(
    root: Path,
    source_manifest: dict[str, Any],
    ledger: dict[str, Any],
    reconciliation: dict[str, Any],
    readiness: dict[str, Any],
    *,
    source_manifest_path: Path,
    ledger_path: Path,
    semantics_path: Path,
) -> tuple[dict[str, Any], bool, str]:
    errors: list[str] = []
    if reconciliation.get("schema_version") != CH5_RECONCILIATION_SCHEMA:
        errors.append("invalid_chapter5_reconciliation_schema")
    if readiness.get("schema_version") != CH5_READINESS_SCHEMA:
        errors.append("invalid_chapter5_readiness_schema")
    source_revision = str(ledger.get("source_revision") or source_manifest.get("source_revision") or "")
    if str(reconciliation.get("source_revision") or "") != source_revision:
        errors.append("chapter5_reconciliation_source_revision_mismatch")
    if str(readiness.get("source_revision") or "") != source_revision:
        errors.append("chapter5_readiness_source_revision_mismatch")
    if readiness.get("extraction_b_snapshot_id") != reconciliation.get("extraction_b_snapshot_id"):
        errors.append("chapter5_snapshot_identity_mismatch")
    if readiness.get("cache_key") != reconciliation.get("cache_key"):
        errors.append("chapter5_cache_key_mismatch")
    expected_reconciliation_sha = "sha256:" + _canonical_payload_sha(reconciliation)
    if str(readiness.get("reconciliation_sha256") or "") != expected_reconciliation_sha:
        errors.append("chapter5_readiness_reconciliation_hash_mismatch")
    readiness_status = str(readiness.get("readiness") or "")
    if readiness_status not in {"READY", "CONCERNS"}:
        errors.append("chapter5_readiness_not_closable")
    if readiness_status == "CONCERNS" and readiness.get("allow_concerns") is not True:
        errors.append("chapter5_concerns_not_policy_allowed")
    if readiness.get("closure_allowed") is not True:
        errors.append("chapter5_closure_not_allowed")
    if reconciliation.get("global_audit_completed") is not True:
        errors.append("chapter5_global_audit_incomplete")
    summary = reconciliation.get("summary") if isinstance(reconciliation.get("summary"), dict) else {}
    if int(summary.get("blocking_count") or 0) != 0:
        errors.append("chapter5_reconciliation_blocking_findings")
    task_id = str(readiness.get("task_id") or reconciliation.get("task_id") or "")
    freshness_ok, freshness_reason = validate_chapter5_evidence_freshness(
        root,
        task_id=task_id,
        reconciliation=reconciliation,
        readiness=readiness,
        manifest_path=source_manifest_path,
        ledger_path=ledger_path,
        semantics_path=semantics_path,
    )
    if not freshness_ok:
        errors.append(freshness_reason)

    report = {
        "schema_version": "chapter5.semantic-reconciliation-closure.v1",
        "stage": "closure",
        "source_revision": source_revision,
        "status": "passed" if not errors else "blocked",
        "blocking_counts": {
            "chapter5_readiness": len(errors),
            "missing": int(summary.get("missing") or 0),
            "partial": int(summary.get("partial") or 0),
            "invented": int(summary.get("invented") or 0),
            "conflicts": int(summary.get("conflicts") or 0),
            "orphan_delivery_semantic": int(summary.get("orphan_delivery_semantic") or 0),
            "orphan_acceptance": int(summary.get("orphan_acceptance") or 0),
        },
        "details": {
            "readiness": readiness_status,
            "closure_allowed": bool(readiness.get("closure_allowed")),
            "errors": errors,
            "extraction_b_snapshot_id": reconciliation.get("extraction_b_snapshot_id"),
        },
    }
    return report, not errors, "verified_chapter5_readiness" if not errors else ",".join(errors)


def closure_evidence(
    root: Path,
    source: str,
    source_manifest: dict[str, Any],
    ledger: dict[str, Any],
    semantics: dict[str, Any],
    candidates: dict[str, Any],
    coverage: dict[str, Any],
    persisted_report: dict[str, Any],
) -> tuple[dict[str, Any], bool, str]:
    """Re-validate Chapter 3 closure and bind refresh to the exact current artifacts."""
    if source != "chapter3":
        raise ValueError("Chapter 5 closure must use reconciliation/readiness evidence")

    recomputed, _edges = validate_semantic_conservation(
        root, ledger, semantics, "closure", candidates
    )
    existing_tasks: list[dict[str, Any]] = []
    for value in DEFAULT_TASK_VIEWS:
        payload = load_json(root / value, [])
        if isinstance(payload, list):
            existing_tasks.extend(row for row in payload if isinstance(row, dict))
    legacy_requirements = load_json(
        root / DEFAULT_LEGACY_REQUIREMENTS_PATH, {"anchors": []}
    )
    recomputed_coverage = audit_task_coverage(
        semantics, candidates, legacy_requirements, existing_tasks
    )
    errors: list[str] = []
    if str(source_manifest.get("source_revision") or "") != str(ledger.get("source_revision") or ""):
        errors.append("source_manifest_revision_mismatch")
    if str(source_manifest.get("manifest_sha256") or "") != str(ledger.get("source_manifest_sha256") or ""):
        errors.append("source_manifest_hash_mismatch")
    if coverage.get("schema") != "task-generation.coverage-report.v2":
        errors.append("invalid_coverage_schema")
    if coverage.get("coverage_model") != "semantic-sink":
        errors.append("semantic_sink_coverage_required")
    if coverage.get("status") != recomputed_coverage.get("status"):
        errors.append("coverage_status_mismatch")
    if recomputed_coverage.get("status") != "ok":
        errors.append("task_coverage_not_passed")
    if coverage.get("missing_blocking_count") != recomputed_coverage.get("missing_blocking_count"):
        errors.append("coverage_blocking_count_mismatch")
    if coverage.get("invalid_task_semantic_refs", []) != recomputed_coverage.get("invalid_task_semantic_refs", []):
        errors.append("coverage_invalid_refs_mismatch")
    if coverage.get("stale_existing_task_mappings", []) != recomputed_coverage.get("stale_existing_task_mappings", []):
        errors.append("coverage_stale_mapping_mismatch")
    if coverage.get("legacy_p0_p1_packaging", {}) != recomputed_coverage.get("legacy_p0_p1_packaging", {}):
        errors.append("coverage_legacy_packaging_mismatch")
    if str(coverage.get("source_revision") or "") != str(ledger.get("source_revision") or ""):
        errors.append("coverage_source_revision_mismatch")
    if str(coverage.get("source_manifest_sha256") or "") != str(ledger.get("source_manifest_sha256") or ""):
        errors.append("coverage_source_manifest_mismatch")
    if persisted_report.get("schema_version") != "chapter3.semantic-conservation-report.v1":
        errors.append("invalid_report_schema")
    if persisted_report.get("stage") != "closure":
        errors.append("closure_stage_required")
    if str(persisted_report.get("source_revision") or "") != str(ledger.get("source_revision") or ""):
        errors.append("report_source_revision_mismatch")
    if str(persisted_report.get("source_manifest_sha256") or "") != str(ledger.get("source_manifest_sha256") or ""):
        errors.append("report_source_manifest_mismatch")
    if persisted_report.get("status") != recomputed.get("status"):
        errors.append("report_status_mismatch")
    if persisted_report.get("blocking_counts", {}) != recomputed.get("blocking_counts", {}):
        errors.append("report_blocking_counts_mismatch")

    passed = not errors and recomputed.get("status") == "passed"
    if passed:
        return recomputed, True, "verified_closure"

    effective = dict(recomputed)
    blocking = dict(effective.get("blocking_counts", {}))
    blocking["closure_evidence_invalid"] = 1
    effective["blocking_counts"] = blocking
    effective["status"] = "blocked"
    details = dict(effective.get("details", {}))
    details["closure_evidence_errors"] = errors or ["recomputed_closure_blocked"]
    effective["details"] = details
    return effective, False, ",".join(errors or ["recomputed_closure_blocked"])


def verify_triplet_attestation(
    root: Path,
    payload: dict[str, Any],
) -> tuple[bool, str]:
    errors: list[str] = []
    if payload.get("schema_version") != "chapter3.triplet-baseline-attestation.v1":
        errors.append("invalid_triplet_attestation_schema")
    if payload.get("status") != "passed":
        errors.append("triplet_attestation_not_passed")

    task_files = payload.get("task_files")
    if not isinstance(task_files, dict):
        task_files = {}
        errors.append("invalid_triplet_task_file_manifest")
    for value in TRIPLET_TASK_FILES:
        path = root / value
        row = task_files.get(value)
        if not path.is_file():
            errors.append(f"triplet_file_missing:{value}")
            continue
        if not isinstance(row, dict):
            errors.append(f"triplet_file_not_attested:{value}")
            continue
        actual = "sha256:" + sha256_bytes(path.read_bytes())
        if str(row.get("sha256") or "") != actual:
            errors.append(f"triplet_file_hash_mismatch:{value}")

    checks = payload.get("checks")
    by_name = {
        str(row.get("name")): row
        for row in checks
        if isinstance(row, dict) and row.get("name")
    } if isinstance(checks, list) else {}
    if not isinstance(checks, list):
        errors.append("invalid_triplet_checks")
    missing_checks = sorted(TRIPLET_REQUIRED_CHECKS - set(by_name))
    if missing_checks:
        errors.append("missing_triplet_checks:" + ",".join(missing_checks))
    for name in sorted(TRIPLET_REQUIRED_CHECKS & set(by_name)):
        row = by_name[name]
        try:
            returncode = int(row.get("returncode", 1))
        except (TypeError, ValueError):
            returncode = 1
            errors.append(f"invalid_triplet_check_returncode:{name}")
        if row.get("status") != "passed" or returncode != 0:
            errors.append(f"triplet_check_failed:{name}")

    return not errors, ",".join(errors) if errors else "verified_triplet_baseline"


def workspace_revision(
    source: str,
    trigger_run_id: str,
    source_revision: str,
    conservation_report: dict[str, Any],
) -> str:
    binding = {
        "source": source,
        "trigger_run_id": trigger_run_id,
        "source_revision": source_revision,
        "report_status": conservation_report.get("status"),
        "blocking_counts": conservation_report.get("blocking_counts", {}),
    }
    raw = json.dumps(binding, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return "workspace:" + hashlib.sha256(raw.encode("utf-8")).hexdigest()[:24]


def task_details_from_candidates(candidates: dict[str, Any]) -> list[dict[str, Any]]:
    details = []
    for row in candidates.get("candidates", []):
        if not isinstance(row, dict) or row.get("id") is None:
            continue
        task = dict(row)
        task["id"] = str(row["id"])
        details.append({"task": task, "mappings": {}, "godot": {"status": "unmapped", "scenes": []}})
    return details


def task_details_from_task_views(root: Path, candidates: dict[str, Any]) -> list[dict[str, Any]]:
    candidate_by_id = {
        str(row.get("id")): dict(row)
        for row in candidates.get("candidates", [])
        if isinstance(row, dict) and row.get("id") is not None
    }
    details: dict[str, dict[str, Any]] = {}
    for view_path_value in DEFAULT_TASK_VIEWS:
        view_path = Path(view_path_value)
        payload = load_json(root / view_path, [])
        if not isinstance(payload, list):
            continue
        view_name = view_path.stem
        for row in payload:
            if not isinstance(row, dict):
                continue
            raw_id = row.get("taskmaster_id") if row.get("taskmaster_id") is not None else row.get("id")
            if raw_id is None:
                continue
            task_id = str(raw_id)
            if task_id.endswith(".0"):
                task_id = task_id[:-2]
            detail = details.setdefault(task_id, {
                "task": {"id": task_id},
                "mappings": {"tasks_back": [], "tasks_gameplay": []},
                "godot": {"status": "unmapped", "scenes": []},
            })
            merged = detail["task"]
            merged.update(candidate_by_id.get(task_id, {}))
            for field in (
                "title", "status", "semantic_refs", "requirement_ids", "capability_refs",
                "overlay_refs", "contractRefs", "overlay_requirement_refs",
                "contract_requirement_refs", "acceptance", "test_refs",
            ):
                if field in row and row.get(field) not in (None, [], {}, ""):
                    merged[field] = row.get(field)
            detail["mappings"].setdefault(view_name, []).append(row)
    for task_id, candidate in candidate_by_id.items():
        if task_id not in details:
            task = dict(candidate)
            task["id"] = task_id
            details[task_id] = {"task": task, "mappings": {}, "godot": {"status": "unmapped", "scenes": []}}
    return list(details.values())


def view_problems(report: dict[str, Any], triplet_status: str, source: str) -> list[dict[str, Any]]:
    problems = []
    for family, count in report.get("blocking_counts", {}).items():
        if isinstance(count, int) and count > 0:
            problems.append({"kind": family, "count": count})
    if source == "chapter3" and triplet_status != "passed":
        problems.append({"kind": "triplet_baseline_not_passed", "status": triplet_status})
    return problems


def build_workspace_view(
    source: str,
    trigger_run_id: str,
    source_manifest: dict[str, Any],
    ledger: dict[str, Any],
    semantics: dict[str, Any],
    capabilities: dict[str, Any],
    edges: dict[str, Any],
    candidates: dict[str, Any],
    report: dict[str, Any],
    triplet_status: str,
    view_kind: str,
    closure_passed_override: bool | None = None,
    task_details_override: list[dict[str, Any]] | None = None,
    reconciliation: dict[str, Any] | None = None,
    readiness: dict[str, Any] | None = None,
) -> dict[str, Any]:
    source_revision = str(
        ledger.get("source_revision")
        or source_manifest.get("source_revision")
        or semantics.get("source_revision")
        or "unknown"
    )
    revision = workspace_revision(source, trigger_run_id, source_revision, report)
    identity = {
        "kind": "workspace",
        "revision": revision,
        "trigger_run_id": trigger_run_id,
        "chapter_source": source,
        "source_revision": source_revision,
    }
    manifest = {
        "schema_version": "newrouge.semantic-topology-manifest.v1",
        "source_revision": source_revision,
        "source_manifest_sha256": source_manifest.get("manifest_sha256")
        or ledger.get("source_manifest_sha256"),
        "schema_revision": "v1",
        "generator_revision": "chapter-closure-refresh-v1",
        "artifacts": {},
    }
    view = build_topology_view(
        identity,
        manifest,
        ledger,
        semantics,
        capabilities,
        edges,
        task_details_override if task_details_override is not None else task_details_from_candidates(candidates),
        view_problems(report, triplet_status, source),
    )
    report_passed = report.get("status") == "passed"
    closure_passed = (
        bool(closure_passed_override)
        if closure_passed_override is not None
        else report_passed and triplet_status == "passed"
    )
    view["workspace_view"] = view_kind
    view["chapter_run"] = {
        "source": source,
        "trigger_run_id": trigger_run_id,
        "conservation_status": report.get("status", "unknown"),
        "triplet_status": triplet_status,
        "closure_passed": closure_passed,
    }
    if source == "chapter5":
        reconciliation_summary = (
            reconciliation.get("summary", {})
            if isinstance(reconciliation, dict)
            and isinstance(reconciliation.get("summary"), dict)
            else {}
        )
        readiness_value = (
            str(readiness.get("readiness") or "UNKNOWN")
            if isinstance(readiness, dict)
            else "UNKNOWN"
        )
        if not isinstance(reconciliation, dict):
            reconciliation_status = "missing"
        elif int(reconciliation_summary.get("conflicts") or 0) > 0:
            reconciliation_status = "conflict"
        elif int(reconciliation_summary.get("invented") or 0) > 0:
            reconciliation_status = "invented"
        elif any(
            int(reconciliation_summary.get(key) or 0) > 0
            for key in ("missing", "partial", "orphan_delivery_semantic", "orphan_acceptance")
        ):
            reconciliation_status = "partial"
        elif readiness_value in {"READY", "CONCERNS"} and bool(
            readiness.get("closure_allowed") if isinstance(readiness, dict) else False
        ):
            reconciliation_status = "stabilized"
        else:
            reconciliation_status = "partial"
        view["chapter_run"]["reconciliation_status"] = reconciliation_status
        view["chapter_run"]["readiness"] = readiness_value
        view["chapter_run"]["extraction_b_snapshot_id"] = (
            reconciliation.get("extraction_b_snapshot_id") if isinstance(reconciliation, dict) else None
        )
        view.setdefault("summary", {})["chapter5_reconciliation_status"] = reconciliation_status
        view["summary"]["chapter5_readiness"] = readiness_value
        view["reconciliation"] = {
            "summary": reconciliation_summary,
            "findings": reconciliation.get("findings", []) if isinstance(reconciliation, dict) else [],
            "dependency_corrections": reconciliation.get("dependency_corrections", []) if isinstance(reconciliation, dict) else [],
            "overlap_reviews": reconciliation.get("overlap_reviews", []) if isinstance(reconciliation, dict) else [],
            "readiness": readiness_value,
            "closure_allowed": readiness.get("closure_allowed", False) if isinstance(readiness, dict) else False,
        }
    view["status"] = "passed" if closure_passed else "concern"
    if not closure_passed:
        view["fresh"] = False
    return view


def copy_planning_artifacts(
    root: Path,
    source_manifest: dict[str, Any],
    ledger_path: Path,
    semantics_path: Path,
    capabilities_path: Path,
    edges_path: Path,
) -> dict[str, Any]:
    destinations = {
        "source_blocks": root / TOPOLOGY_ARTIFACTS["source_blocks"],
        "requirements": root / TOPOLOGY_ARTIFACTS["requirements"],
        "capabilities": root / TOPOLOGY_ARTIFACTS["capabilities"],
        "edges": root / TOPOLOGY_ARTIFACTS["edges"],
    }
    sources = {
        "source_blocks": ledger_path,
        "requirements": semantics_path,
        "capabilities": capabilities_path,
        "edges": edges_path,
    }
    manifest_path = root / TOPOLOGY_ARTIFACTS["manifest"]
    snapshots = {
        path: _snapshot_file(path)
        for path in [*destinations.values(), manifest_path]
    }
    try:
        artifact_hashes = {}
        for key, destination in destinations.items():
            source_path = sources[key]
            if not source_path.is_file():
                raise ValueError(f"missing topology source artifact: {source_path}")
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source_path, destination)
            artifact_hashes[destination.relative_to(root).as_posix()] = "sha256:" + sha256_bytes(destination.read_bytes())
        manifest = {
            "schema_version": "newrouge.semantic-topology-manifest.v1",
            "source_revision": source_manifest.get("source_revision"),
            "source_manifest_sha256": source_manifest.get("manifest_sha256"),
            "schema_revision": "v1",
            "generator_revision": "chapter3-semantic-conservation-v1",
            "artifacts": artifact_hashes,
        }
        # Do not write repository_revision here: the generated topology is
        # committed after this step, so binding it to the pre-commit HEAD would make
        # the just-committed topology immediately stale. Keep the observed source
        # checkout only as audit metadata; canonical freshness is bound later by KCP
        # publication plus per-source hashes.
        source_repository_revision = source_manifest.get("repository_revision")
        if isinstance(source_repository_revision, str) and source_repository_revision:
            manifest["source_repository_revision"] = source_repository_revision
        write_json(manifest_path, manifest)
        return manifest
    except Exception:
        for path, snapshot in snapshots.items():
            try:
                _restore_file(path, snapshot)
            except OSError:
                pass
        raise


def git_result(root: Path, args: list[str]) -> str:
    result = subprocess.run(
        ["git", "-C", str(root), *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=15,
        check=True,
    )
    return result.stdout.strip()


def publication_eligibility(root: Path) -> tuple[bool, str]:
    try:
        branch = git_result(root, ["branch", "--show-current"])
        dirty = git_result(root, ["status", "--porcelain"])
        head = git_result(root, ["rev-parse", "HEAD"])
        main = git_result(root, ["rev-parse", "refs/heads/main"])
    except (OSError, subprocess.SubprocessError) as exc:
        return False, f"git_state_unavailable:{exc}"
    if branch != "main":
        return False, f"trusted_ref_required:branch={branch or 'detached'}"
    if dirty:
        return False, "dirty_worktree"
    if head != main:
        return False, "head_not_local_main"
    return True, "eligible"


def current_generation(root: Path) -> str | None:
    payload = load_json(root / "knowledge/indexes/current.json", {})
    value = payload.get("generation_id") if isinstance(payload, dict) else None
    return str(value) if value else None


def maybe_publish(root: Path, requested: bool) -> tuple[str, str]:
    if not requested:
        return "deferred", "not_requested"
    eligible, reason = publication_eligibility(root)
    if not eligible:
        return "deferred", reason
    result = subprocess.run(
        ["py", "-3", "scripts/python/publish_knowledge_catalog.py", "--publish"],
        cwd=root,
        text=True,
        capture_output=True,
        encoding="utf-8",
        timeout=300,
        check=False,
    )
    if result.returncode != 0:
        return "failed", (result.stderr or result.stdout)[-1200:]
    return "published", "trusted_ref_publication_complete"


def partial_attempt(
    source: str,
    trigger_run_id: str,
    reason: str,
    missing: list[str],
) -> dict[str, Any]:
    raw = source + chr(0) + trigger_run_id + chr(0) + reason
    revision = "workspace:" + hashlib.sha256(raw.encode("utf-8")).hexdigest()[:24]
    payload = unavailable_topology("workspace", revision, reason)
    payload["identity"].update({
        "trigger_run_id": trigger_run_id,
        "chapter_source": source,
        "source_revision": "unknown",
    })
    payload["workspace_view"] = "last_attempt"
    payload["status"] = "concern"
    payload["problems"] = [{"kind": "missing_refresh_input", "path": path} for path in missing]
    payload["chapter_run"] = {
        "source": source,
        "trigger_run_id": trigger_run_id,
        "conservation_status": "unavailable",
        "triplet_status": "unknown",
        "closure_passed": False,
    }
    return payload


def record_run_failure_attempt(
    root: Path,
    *,
    source: str,
    trigger_run_id: str,
    reason: str,
) -> dict[str, Any]:
    """Record a failed producer run without evaluating or promoting stale closure artifacts."""
    if source not in REGISTERED_SOURCES:
        raise ValueError(f"unregistered closure producer: {source}")
    attempt = partial_attempt(source, trigger_run_id, reason, [])
    attempt.setdefault("chapter_run", {})["lifecycle_status"] = "failed"
    attempt["chapter_run"]["knowledge_refresh_status"] = "attempt_failed"
    try:
        write_json(root / ATTEMPT_PATH, attempt)
        write_json(root / LEGACY_ATTEMPT_PATH, attempt)
    except OSError as exc:
        return _refresh_failure_summary(
            root,
            source=source,
            trigger_run_id=trigger_run_id,
            topology_revision=attempt.get("identity", {}).get("revision"),
            semantic_triplet_closure_passed=False,
            family="attempt_refresh_failed",
            reason=str(exc),
            attempt_written=False,
        )
    return {
        "schema_version": "chapter-knowledge-refresh-summary.v1",
        "source": source,
        "trigger_run_id": trigger_run_id,
        "topology_revision": attempt.get("identity", {}).get("revision"),
        "closure_passed": False,
        "chapter_closure_status": "concern",
        "local_refresh_status": "attempt_refreshed",
        "local_refresh_failure_family": None,
        "publication_status": "deferred",
        "publication_reason": "producer_run_failed",
        "attempt_path": ATTEMPT_PATH.as_posix(),
        "stable_path": None,
    }


def begin_run_attempt(
    root: Path,
    *,
    source: str,
    trigger_run_id: str,
) -> dict[str, Any]:
    """Record a run-start attempt so an interrupted Chapter run still leaves evidence."""
    if source not in REGISTERED_SOURCES:
        raise ValueError(f"unregistered closure producer: {source}")
    attempt = partial_attempt(
        source,
        trigger_run_id,
        "chapter run started; closure evidence not available yet",
        [],
    )
    attempt.setdefault("chapter_run", {})["lifecycle_status"] = "started"
    attempt["chapter_run"]["knowledge_refresh_status"] = "attempt_started"
    attempt_written = False
    try:
        write_json(root / ATTEMPT_PATH, attempt)
        attempt_written = True
        write_json(root / LEGACY_ATTEMPT_PATH, attempt)
    except OSError as exc:
        return _refresh_failure_summary(
            root,
            source=source,
            trigger_run_id=trigger_run_id,
            topology_revision=attempt.get("identity", {}).get("revision"),
            semantic_triplet_closure_passed=False,
            family="attempt_refresh_failed",
            reason=str(exc),
            attempt_written=attempt_written,
        )
    return {
        "schema_version": "chapter-knowledge-refresh-summary.v1",
        "source": source,
        "trigger_run_id": trigger_run_id,
        "topology_revision": attempt.get("identity", {}).get("revision"),
        "semantic_triplet_closure_passed": False,
        "closure_passed": False,
        "chapter_closure_status": "concern",
        "local_refresh_status": "attempt_refreshed_started",
        "local_refresh_failure_family": None,
        "planning_artifact_status": "not_requested",
        "publication_status": "deferred",
        "publication_reason": "chapter_run_in_progress",
        "current_generation_id": current_generation(root),
        "attempt_path": ATTEMPT_PATH.as_posix(),
        "stable_path": None,
    }


def _mark_attempt_refresh_failure(
    root: Path,
    attempt: dict[str, Any],
    family: str,
    reason: str,
) -> bool:
    """Best-effort: make Project Health Last Attempt show the refresh failure."""
    attempt["status"] = "concern"
    attempt["fresh"] = False
    problems = attempt.setdefault("problems", [])
    if isinstance(problems, list):
        problems.append({
            "kind": "knowledge_refresh_failed",
            "failure_family": family,
            "reason": reason,
        })
    chapter_run = attempt.setdefault("chapter_run", {})
    if isinstance(chapter_run, dict):
        chapter_run["closure_passed"] = False
        chapter_run["knowledge_refresh_status"] = "failed"
        chapter_run["knowledge_refresh_failure_family"] = family
    try:
        write_json(root / ATTEMPT_PATH, attempt)
        write_json(root / LEGACY_ATTEMPT_PATH, attempt)
    except OSError:
        return False
    return True


def _refresh_failure_summary(
    root: Path,
    *,
    source: str,
    trigger_run_id: str,
    topology_revision: str | None,
    semantic_triplet_closure_passed: bool,
    family: str,
    reason: str,
    attempt_written: bool,
) -> dict[str, Any]:
    return {
        "schema_version": "chapter-knowledge-refresh-summary.v1",
        "source": source,
        "trigger_run_id": trigger_run_id,
        "topology_revision": topology_revision,
        "semantic_triplet_closure_passed": semantic_triplet_closure_passed,
        "closure_passed": False,
        "chapter_closure_status": "knowledge_refresh_failed",
        "local_refresh_status": "failed",
        "local_refresh_failure_family": family,
        "local_refresh_reason": reason,
        "planning_artifact_status": "blocked_by_knowledge_refresh",
        "publication_status": "deferred",
        "publication_reason": "knowledge_refresh_failed",
        "current_generation_id": current_generation(root),
        "attempt_path": ATTEMPT_PATH.as_posix() if attempt_written else None,
        "stable_path": None,
    }


def run(
    root: Path,
    *,
    source: str,
    trigger_run_id: str,
    refresh_local: bool,
    write_planning: bool,
    publish_if_eligible: bool,
    triplet_status: str,
    source_manifest_path: Path,
    ledger_path: Path,
    semantics_path: Path,
    capabilities_path: Path,
    edges_path: Path,
    candidates_path: Path,
    report_path: Path,
    coverage_path: Path | None = None,
    triplet_attestation_path: Path | None = None,
    reconciliation_path: Path | None = None,
    readiness_path: Path | None = None,
) -> dict[str, Any]:
    if source not in REGISTERED_SOURCES:
        raise ValueError(f"unregistered closure producer: {source}")
    coverage_path = coverage_path or (root / DEFAULT_COVERAGE_PATH)
    triplet_attestation_path = (
        triplet_attestation_path or (root / DEFAULT_TRIPLET_ATTESTATION_PATH)
    )
    reconciliation_path = reconciliation_path or (root / DEFAULT_CH5_RECONCILIATION_PATH)
    readiness_path = readiness_path or (root / DEFAULT_CH5_READINESS_PATH)
    required = [
        source_manifest_path, ledger_path, semantics_path, capabilities_path,
        edges_path, candidates_path,
    ]
    if source == "chapter3":
        required.append(report_path)
        required.append(coverage_path)
        if triplet_status == "passed":
            required.append(triplet_attestation_path)
    else:
        required.extend([reconciliation_path, readiness_path])
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        reason = "partial Chapter closure: required refresh inputs are missing"
        if refresh_local:
            attempt = partial_attempt(source, trigger_run_id, reason, missing)
            try:
                write_json(root / ATTEMPT_PATH, attempt)
                write_json(root / LEGACY_ATTEMPT_PATH, attempt)
            except OSError as exc:
                return _refresh_failure_summary(
                    root,
                    source=source,
                    trigger_run_id=trigger_run_id,
                    topology_revision=attempt.get("identity", {}).get("revision"),
                    semantic_triplet_closure_passed=False,
                    family="attempt_refresh_failed",
                    reason=str(exc),
                    attempt_written=False,
                )
        return {
            "schema_version": "chapter-knowledge-refresh-summary.v1",
            "source": source,
            "trigger_run_id": trigger_run_id,
            "topology_revision": None,
            "closure_passed": False,
            "local_refresh_status": "attempt_refreshed_partial" if refresh_local else "skipped",
            "planning_artifact_status": "blocked_by_closure",
            "publication_status": "deferred",
            "publication_reason": "missing_refresh_inputs",
            "current_generation_id": current_generation(root),
            "attempt_path": ATTEMPT_PATH.as_posix() if refresh_local else None,
            "stable_path": None,
            "missing_inputs": missing,
        }

    source_manifest = load_json(source_manifest_path, {})
    ledger = load_json(ledger_path, {})
    semantics = load_json(semantics_path, {})
    capabilities = load_json(capabilities_path, {})
    edges = load_json(edges_path, {})
    candidates = load_json(candidates_path, {})
    coverage = load_json(coverage_path, {}) if source == "chapter3" else {}
    persisted_report = load_json(report_path, {}) if source == "chapter3" else {}
    reconciliation = load_json(reconciliation_path, {}) if source == "chapter5" else {}
    readiness = load_json(readiness_path, {}) if source == "chapter5" else {}
    triplet_attestation = (
        load_json(triplet_attestation_path, {})
        if source == "chapter3" and triplet_status == "passed"
        else {}
    )
    triplet_evidence_passed, triplet_evidence_reason = (
        verify_triplet_attestation(root, triplet_attestation)
        if source == "chapter3" and triplet_status == "passed"
        else (False, f"triplet_status_{triplet_status}")
    )
    if source == "chapter3":
        report, closure_evidence_passed, closure_evidence_reason = closure_evidence(
            root, source, source_manifest, ledger, semantics, candidates, coverage, persisted_report
        )
        semantic_triplet_closure_passed = (
            closure_evidence_passed
            and triplet_status == "passed"
            and triplet_evidence_passed
        )
        task_details_override = None
        effective_edges = edges
    else:
        report, closure_evidence_passed, closure_evidence_reason = chapter5_closure_evidence(
            root,
            source_manifest,
            ledger,
            reconciliation,
            readiness,
            source_manifest_path=source_manifest_path,
            ledger_path=ledger_path,
            semantics_path=semantics_path,
        )
        triplet_evidence_passed = True
        triplet_evidence_reason = "not_applicable_chapter5"
        semantic_triplet_closure_passed = closure_evidence_passed
        task_details_override = task_details_from_task_views(root, candidates)
        effective_edges = dict(edges)
        merged_edges = list(edges.get("edges", [])) if isinstance(edges, dict) else []
        merged_edges.extend(
            row for row in reconciliation.get("topology_edges", [])
            if isinstance(row, dict)
        )
        effective_edges["edges"] = merged_edges

    attempt = build_workspace_view(
        source, trigger_run_id, source_manifest, ledger, semantics, capabilities,
        effective_edges, candidates, report, triplet_status, "last_attempt",
        closure_passed_override=semantic_triplet_closure_passed,
        task_details_override=task_details_override,
        reconciliation=reconciliation if source == "chapter5" else None,
        readiness=readiness if source == "chapter5" else None,
    )
    attempt.setdefault("chapter_run", {})["closure_evidence_status"] = (
        "verified" if closure_evidence_passed else "blocked"
    )
    attempt["chapter_run"]["closure_evidence_reason"] = closure_evidence_reason
    attempt["chapter_run"]["task_coverage_status"] = coverage.get("status", "unknown")
    attempt["chapter_run"]["triplet_evidence_status"] = (
        "verified" if triplet_evidence_passed else "blocked"
    )
    attempt["chapter_run"]["triplet_evidence_reason"] = triplet_evidence_reason
    if triplet_status == "passed" and not triplet_evidence_passed:
        attempt.setdefault("problems", []).append({
            "kind": "triplet_baseline_evidence_invalid",
            "reason": triplet_evidence_reason,
        })
        attempt["status"] = "concern"
        attempt["fresh"] = False
        attempt["chapter_run"]["closure_passed"] = False
    stable_input_hash = None
    if source == "chapter5":
        input_fingerprint = reconciliation.get("input_fingerprint")
        stable_input_hash = (
            str(input_fingerprint.get("sha256") or "")
            if isinstance(input_fingerprint, dict)
            else ""
        )
        if not stable_input_hash:
            stable_input_hash = "sha256:" + _canonical_payload_sha({
                "source_revision": reconciliation.get("source_revision"),
                "extraction_b_snapshot_id": reconciliation.get("extraction_b_snapshot_id"),
                "chapter3_topology_sha256": reconciliation.get("chapter3_topology_sha256"),
                "readiness": readiness.get("readiness"),
                "closure_allowed": readiness.get("closure_allowed"),
            })
        attempt.setdefault("chapter_run", {})["stable_input_hash"] = stable_input_hash
    local_status = "skipped"
    attempt_written = False
    stable_snapshot = _snapshot_file(root / STABLE_PATH)
    chapter5_stable_snapshot = _snapshot_file(root / CHAPTER5_STABLE_PATH)
    if refresh_local:
        try:
            write_json(root / ATTEMPT_PATH, attempt)
            attempt_written = True
            write_json(root / LEGACY_ATTEMPT_PATH, attempt)
        except OSError as exc:
            return _refresh_failure_summary(
                root,
                source=source,
                trigger_run_id=trigger_run_id,
                topology_revision=attempt.get("identity", {}).get("revision"),
                semantic_triplet_closure_passed=semantic_triplet_closure_passed,
                family="attempt_refresh_failed",
                reason=str(exc),
                attempt_written=attempt_written,
            )
        local_status = "attempt_refreshed"
        if semantic_triplet_closure_passed:
            previous_chapter5_stable = (
                load_json(root / CHAPTER5_STABLE_PATH, {})
                if source == "chapter5"
                else {}
            )
            previous_stable_input_hash = (
                ((previous_chapter5_stable.get("chapter_run") or {}).get("stable_input_hash"))
                if isinstance(previous_chapter5_stable, dict)
                else None
            )
            if (
                source == "chapter5"
                and stable_input_hash
                and previous_stable_input_hash == stable_input_hash
            ):
                local_status = "stable_reused"
            else:
                stable = build_workspace_view(
                    source, trigger_run_id, source_manifest, ledger, semantics, capabilities,
                    effective_edges, candidates, report, triplet_status, "latest_successful",
                    closure_passed_override=True,
                    task_details_override=task_details_override,
                    reconciliation=reconciliation if source == "chapter5" else None,
                    readiness=readiness if source == "chapter5" else None,
                )
                if source == "chapter5" and stable_input_hash:
                    stable.setdefault("chapter_run", {})["stable_input_hash"] = stable_input_hash
                try:
                    write_json(root / STABLE_PATH, stable)
                    if source == "chapter5":
                        write_json(root / CHAPTER5_STABLE_PATH, stable)
                except OSError as exc:
                    try:
                        _restore_file(root / STABLE_PATH, stable_snapshot)
                        if source == "chapter5":
                            _restore_file(root / CHAPTER5_STABLE_PATH, chapter5_stable_snapshot)
                    except OSError:
                        pass
                    _mark_attempt_refresh_failure(
                        root, attempt, "stable_refresh_failed", str(exc)
                    )
                    return _refresh_failure_summary(
                        root,
                        source=source,
                        trigger_run_id=trigger_run_id,
                        topology_revision=attempt.get("identity", {}).get("revision"),
                        semantic_triplet_closure_passed=True,
                        family="stable_refresh_failed",
                        reason=str(exc),
                        attempt_written=True,
                    )
                local_status = "stable_refreshed"

    stable_required = source in {"chapter3", "chapter5"} or write_planning or publish_if_eligible
    closure_passed = semantic_triplet_closure_passed and (
        local_status in {"stable_refreshed", "stable_reused"}
        if refresh_local
        else not stable_required
    )

    planning_status = "not_requested"
    if write_planning:
        if not closure_passed:
            planning_status = "blocked_by_closure"
        else:
            try:
                copy_planning_artifacts(
                    root, source_manifest, ledger_path, semantics_path, capabilities_path, edges_path
                )
            except (OSError, ValueError) as exc:
                try:
                    _restore_file(root / STABLE_PATH, stable_snapshot)
                    if source == "chapter5":
                        _restore_file(root / CHAPTER5_STABLE_PATH, chapter5_stable_snapshot)
                except OSError:
                    pass
                _mark_attempt_refresh_failure(
                    root, attempt, "planning_topology_refresh_failed", str(exc)
                )
                return _refresh_failure_summary(
                    root,
                    source=source,
                    trigger_run_id=trigger_run_id,
                    topology_revision=attempt.get("identity", {}).get("revision"),
                    semantic_triplet_closure_passed=True,
                    family="planning_topology_refresh_failed",
                    reason=str(exc),
                    attempt_written=attempt_written,
                )
            planning_status = "written"

    if closure_passed:
        publication_status, publication_reason = maybe_publish(root, publish_if_eligible)
    else:
        publication_status, publication_reason = "deferred", "closure_not_passed"
    summary = {
        "schema_version": "chapter-knowledge-refresh-summary.v1",
        "source": source,
        "trigger_run_id": trigger_run_id,
        "topology_revision": attempt.get("identity", {}).get("revision"),
        "semantic_triplet_closure_passed": semantic_triplet_closure_passed,
        "closure_evidence_status": "verified" if closure_evidence_passed else "blocked",
        "closure_evidence_reason": closure_evidence_reason,
        "task_coverage_status": coverage.get("status", "unknown"),
        "triplet_evidence_status": (
            "verified" if triplet_evidence_passed else "blocked"
        ),
        "triplet_evidence_reason": triplet_evidence_reason,
        "closure_passed": closure_passed,
        "chapter_closure_status": "passed" if closure_passed else "concern",
        "local_refresh_status": local_status,
        "local_refresh_failure_family": None,
        "planning_artifact_status": planning_status,
        "publication_status": publication_status,
        "publication_reason": publication_reason,
        "current_generation_id": current_generation(root),
        "attempt_path": ATTEMPT_PATH.as_posix() if refresh_local else None,
        "stable_path": STABLE_PATH.as_posix() if refresh_local and closure_passed else None,
        "stabilized_path": (
            CHAPTER5_STABLE_PATH.as_posix()
            if source == "chapter5" and refresh_local and closure_passed
            else None
        ),
    }
    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--source", choices=sorted(REGISTERED_SOURCES), required=True)
    parser.add_argument("--trigger-run-id", required=True)
    parser.add_argument("--refresh-local", action="store_true")
    parser.add_argument("--write-planning-artifacts", action="store_true")
    parser.add_argument("--publish-if-eligible", action="store_true")
    parser.add_argument("--triplet-status", choices=["passed", "blocked", "unknown"], default="unknown")
    parser.add_argument("--source-manifest", default="logs/ci/task-generation/source-manifest.v1.json")
    parser.add_argument("--ledger", default="logs/ci/task-generation/source-blocks.v1.json")
    parser.add_argument("--semantics", default="logs/ci/task-generation/semantic-requirements.v1.json")
    parser.add_argument("--capabilities", default="logs/ci/task-generation/capabilities.v1.json")
    parser.add_argument("--edges", default="logs/ci/task-generation/topology-edges.v1.json")
    parser.add_argument("--candidates", default="logs/ci/task-generation/task-candidates.enriched.json")
    parser.add_argument("--report", default="logs/ci/task-generation/semantic-conservation-report.json")
    parser.add_argument("--coverage", default=DEFAULT_COVERAGE_PATH.as_posix())
    parser.add_argument(
        "--triplet-attestation",
        default=DEFAULT_TRIPLET_ATTESTATION_PATH.as_posix(),
    )
    parser.add_argument("--reconciliation", default=DEFAULT_CH5_RECONCILIATION_PATH.as_posix())
    parser.add_argument("--readiness", default=DEFAULT_CH5_READINESS_PATH.as_posix())
    args = parser.parse_args(argv)
    root = Path(args.repo_root).resolve()
    try:
        summary = run(
            root,
            source=args.source,
            trigger_run_id=args.trigger_run_id,
            refresh_local=args.refresh_local,
            write_planning=args.write_planning_artifacts,
            publish_if_eligible=args.publish_if_eligible,
            triplet_status=args.triplet_status,
            source_manifest_path=root / args.source_manifest,
            ledger_path=root / args.ledger,
            semantics_path=root / args.semantics,
            capabilities_path=root / args.capabilities,
            edges_path=root / args.edges,
            candidates_path=root / args.candidates,
            report_path=root / args.report,
            coverage_path=root / args.coverage,
            triplet_attestation_path=root / args.triplet_attestation,
            reconciliation_path=root / args.reconciliation,
            readiness_path=root / args.readiness,
        )
    except ValueError as exc:
        print(json.dumps({
            "schema_version": "chapter-knowledge-refresh-summary.v1",
            "source": args.source,
            "trigger_run_id": args.trigger_run_id,
            "local_refresh_status": "failed",
            "publication_status": "deferred",
            "publication_reason": str(exc),
        }, ensure_ascii=False))
        return 2
    print(json.dumps(summary, ensure_ascii=False))
    if summary["local_refresh_status"] == "failed" or summary["publication_status"] == "failed":
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
