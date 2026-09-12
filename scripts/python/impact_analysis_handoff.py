#!/usr/bin/env python3
"""Shared fail-closed validator for KCP impact-analysis handoffs."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

EXIT_CODES = {
    "target_not_found": 2, "ambiguous_target": 3, "path_outside_repository": 4,
    "missing_index": 5, "stale_index": 6, "revision_mismatch": 7,
    "source_read_failure": 8, "unsupported_relation": 9,
    "index_identity_collision": 10, "invalid_kcp_binding": 11,
    "internal_error": 12, "dirty_state": 13, "unsupported_target": 14,
    "invalid_manifest": 15, "lock_unavailable": 16, "underqualified_target": 17,
}


@dataclass(frozen=True)
class HandoffValidationResult:
    ok: bool
    code: str = ""
    exit_code: int = 0
    reason: str = ""
    identity: dict[str, Any] | None = None


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _resolve_repo_path(value: str | os.PathLike[str], repo_root: Path) -> Path | None:
    raw = str(value or "").strip()
    if not raw:
        return None
    p = Path(raw)
    try:
        if p.is_absolute() or (len(raw) >= 2 and raw[1] == ":") or raw.startswith("\\\\"):
            return None
        candidate = (repo_root / p).resolve()
        candidate.relative_to(repo_root.resolve())
    except (ValueError, OSError):
        return None
    return candidate


def _fail(code: str, reason: str) -> HandoffValidationResult:
    return HandoffValidationResult(False, code, EXIT_CODES.get(code, 12), reason)


def validate_handoff(
    frozen_context: str | os.PathLike[str] | None,
    impact_report: str | os.PathLike[str] | None,
    revision: str | None,
    *,
    repo_root: str | os.PathLike[str] | None = None,
    consumer: str | None = None,
    task_id: str | None = None,
    binding_evidence: str | os.PathLike[str] | None = None,
) -> HandoffValidationResult:
    values = (frozen_context, impact_report, revision)
    if not any(str(v or "").strip() for v in values):
        return HandoffValidationResult(True)
    if not all(str(v or "").strip() for v in values):
        return _fail("invalid_kcp_binding", "handoff parameters must be supplied as an atomic group")
    root = Path(repo_root).resolve() if repo_root else Path.cwd().resolve()
    frozen_path = _resolve_repo_path(str(frozen_context), root)
    report_path = _resolve_repo_path(str(impact_report), root)
    if frozen_path is None or report_path is None:
        return _fail("path_outside_repository", "handoff paths must remain inside the repository")
    if not frozen_path.exists() or not report_path.exists():
        return _fail("invalid_kcp_binding", "frozen context or impact report is missing")
    try:
        frozen_bytes = frozen_path.read_bytes()
        report_bytes = report_path.read_bytes()
        frozen = json.loads(frozen_bytes.decode("utf-8"))
        report = json.loads(report_bytes.decode("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        return _fail("invalid_kcp_binding", f"unable to read handoff artifacts: {exc}")
    if not isinstance(frozen, dict) or not isinstance(report, dict):
        return _fail("invalid_kcp_binding", "handoff artifacts must be JSON objects")
    requested_revision = str(revision).strip()
    if not re.fullmatch(r"[0-9a-fA-F]{40}", requested_revision):
        return _fail("revision_mismatch", "revision must be a full 40-character Git SHA")
    if str(frozen.get("schema_version") or "") != "newrouge.knowledge-frozen-context.v1":
        return _fail("invalid_kcp_binding", "unsupported frozen context schema")
    report_revision = str(report.get("repository_revision") or "").strip()
    snapshot = frozen.get("snapshot") if isinstance(frozen.get("snapshot"), dict) else {}
    frozen_revision = str(snapshot.get("commit") or frozen.get("repository_revision") or "").strip()
    if report_revision != requested_revision or frozen_revision != requested_revision:
        return _fail("revision_mismatch", "revision does not match report and frozen context")
    if str(frozen.get("freeze_state") or "").strip().lower() != "frozen":
        return _fail("invalid_kcp_binding", "frozen context is not frozen")
    binding = report.get("knowledge_binding")
    if not isinstance(binding, dict):
        return _fail("invalid_kcp_binding", "impact report knowledge_binding is missing")
    actual_frozen_hash = hashlib.sha256(frozen_bytes).hexdigest()
    bound_hash = str(binding.get("frozen_context_sha256") or "").strip().lower()
    if bound_hash != actual_frozen_hash:
        return _fail("invalid_kcp_binding", "frozen context hash mismatch")
    try:
        bound_frozen_path = Path(str(binding.get("frozen_context_path") or ""))
        if bound_frozen_path.is_absolute() or any(part in {"", ".", ".."} for part in bound_frozen_path.parts):
            return _fail("invalid_kcp_binding", "invalid frozen_context_path binding")
        bound_relative = bound_frozen_path.as_posix()
        actual_relative = frozen_path.relative_to(root).as_posix()
    except ValueError:
        return _fail("invalid_kcp_binding", "invalid frozen_context_path binding")
    if bound_relative != actual_relative:
        return _fail("invalid_kcp_binding", "frozen context path binding mismatch")
    expected_consumer = str(consumer or binding.get("consumer") or frozen.get("consumer") or "").strip()
    if expected_consumer not in {"chapter4", "chapter5", "chapter6", "review"}:
        return _fail("invalid_kcp_binding", "unsupported consumer binding")
    if str(frozen.get("consumer") or "").strip() != expected_consumer:
        return _fail("invalid_kcp_binding", "frozen context consumer mismatch")
    if expected_consumer and str(binding.get("consumer") or "").strip() != expected_consumer:
        return _fail("invalid_kcp_binding", "consumer binding mismatch")
    if expected_consumer in {"chapter4", "chapter5", "chapter6"}:
        expected_task = str(task_id or "").strip()
        if expected_task and str(binding.get("task_id") or "").strip() != expected_task:
            return _fail("invalid_kcp_binding", "task binding mismatch")
    elif expected_consumer == "review":
        if "task_id" not in binding or binding.get("task_id") is not None:
            return _fail("invalid_kcp_binding", "review task_id must be explicit null")
    for key in ("decision_set_sha256", "freeze_point", "publication_generation", "publication_sha256"):
        if key not in binding or (key != "task_id" and not str(binding.get(key) or "").strip()):
            return _fail("invalid_kcp_binding", f"knowledge binding field missing: {key}")
    if str(report.get("schema_version") or "") != "newrouge.impact-analysis.v1":
        return _fail("invalid_kcp_binding", "unsupported impact report schema")
    manifest_path = report_path.with_name("run-manifest.v1.json")
    if binding_evidence and manifest_path.exists():
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            expected_path = str(manifest.get("binding_evidence_path") or "")
            expected_sha = str(manifest.get("binding_evidence_sha256") or "")
            sidecar = _resolve_repo_path(str(binding_evidence), root)
            actual_path = sidecar.relative_to(root).as_posix() if sidecar else ""
            actual_sha = hashlib.sha256(sidecar.read_bytes()).hexdigest() if sidecar and sidecar.exists() else ""
            if expected_path != actual_path or expected_sha != actual_sha:
                return _fail("invalid_kcp_binding", "binding evidence manifest mismatch")
        except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError):
            return _fail("invalid_kcp_binding", "binding evidence manifest is invalid")
    if not isinstance(report.get("target"), dict):
        return _fail("invalid_kcp_binding", "impact report target is missing")
    if binding_evidence:
        evidence_path = _resolve_repo_path(str(binding_evidence), root)
        if evidence_path is None or not evidence_path.exists():
            return _fail("invalid_kcp_binding", "binding evidence is missing")
        try:
            from .knowledge_binding_producer import validate_binding_evidence
        except ImportError:
            from knowledge_binding_producer import validate_binding_evidence
        try:
            evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
            if evidence.get("schema_version") != "newrouge.knowledge-binding-evidence.v1" or evidence.get("repository_revision") != requested_revision:
                raise ValueError("binding_evidence_lineage_mismatch")
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            return _fail("invalid_kcp_binding", str(exc))
    if str(report.get("risk_level") or "").strip().lower() not in {"high", "medium", "low", "unknown"}:
        return _fail("invalid_kcp_binding", "impact report risk_level is invalid")
    if str(report.get("status") or "").strip().lower() != "ok":
        return _fail("invalid_kcp_binding", "impact report status is not ok")
    identity = {
        "revision": requested_revision,
        "frozen_context_sha256": actual_frozen_hash,
        "impact_report_sha256": hashlib.sha256(report_bytes).hexdigest(),
        "index_id": str(report.get("index_id") or ""),
        "index_sha256": str(report.get("index_sha256") or ""),
        "knowledge_binding": dict(binding),
    }
    if not identity["index_id"] or not identity["index_sha256"]:
        return _fail("invalid_kcp_binding", "impact report index identity is missing")
    index_ref = report.get("index_path") or report.get("index_artifact_path")
    if index_ref:
        index_path = _resolve_repo_path(str(index_ref), root)
        if index_path is None or not index_path.exists():
            return _fail("missing_index", "referenced impact index is missing")
        if _sha256(index_path).lower() != identity["index_sha256"].lower().removeprefix("sha256:"):
            return _fail("stale_index", "impact index hash mismatch")
    return HandoffValidationResult(True, identity=identity)


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate a KCP impact-analysis handoff.")
    parser.add_argument("--frozen-context")
    parser.add_argument("--impact-report")
    parser.add_argument("--revision")
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--consumer", default=None)
    parser.add_argument("--task-id", default=None)
    parser.add_argument("--binding-evidence", default=None)
    args = parser.parse_args()
    result = validate_handoff(args.frozen_context, args.impact_report, args.revision, repo_root=args.repo_root, consumer=args.consumer, task_id=args.task_id, binding_evidence=args.binding_evidence)
    print(json.dumps({"status": "ok" if result.ok else "fail", "code": result.code, "reason": result.reason, "identity": result.identity}, sort_keys=True))
    return result.exit_code


if __name__ == "__main__":
    raise SystemExit(main())
