#!/usr/bin/env python3
"""CLI for deterministic repository-local impact analysis."""
from __future__ import annotations

import argparse
import json
import hashlib
import os
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    from impact_analysis_handoff import EXIT_CODES
    from impact_analysis_index import ImpactIndexError, validate_index_bytes, atomic_publish_bytes, artifact_json_bytes, _ensure_no_reparse_ancestors, _lexical_absolute_path
    from impact_analyzer import (
        ANALYZER_IMPLEMENTATION_REVISION,
        ImpactAnalyzer,
        validate_report_document,
        failure_report,
        load_frozen_binding,
    )
except ModuleNotFoundError:  # pragma: no cover
    from scripts.python.impact_analysis_handoff import EXIT_CODES
    from scripts.python.impact_analysis_index import ImpactIndexError, validate_index_bytes, atomic_publish_bytes, artifact_json_bytes, _ensure_no_reparse_ancestors, _lexical_absolute_path
    from scripts.python.impact_analyzer import (
        ANALYZER_IMPLEMENTATION_REVISION,
        ImpactAnalyzer,
        validate_report_document,
        failure_report,
        load_frozen_binding,
    )


def _utc_date() -> str:
    return datetime.now(timezone.utc).date().isoformat()


def _resolve_inside(root: Path, value: str) -> Path:
    p = Path(value)
    if p.is_absolute() or (len(value) > 1 and value[1] == ":") or value.startswith("\\\\"):
        candidate = Path(os.path.abspath(str(p)))
    else:
        candidate = Path(os.path.abspath(str(root / p)))
    try:
        canonical_candidate = Path(os.path.normcase(os.path.realpath(str(candidate))))
        canonical_root = Path(os.path.normcase(os.path.realpath(str(root))))
        canonical_candidate.relative_to(canonical_root)
    except ValueError as exc:
        raise ImpactIndexError("path_outside_repository", f"path outside repository: {value}") from exc
    # Return the repository spelling for 8.3 aliases so later relative paths
    # and manifest bindings remain stable, while preserving ordinary paths.
    lexical = _lexical_absolute_path(candidate)
    if lexical != candidate:
        return lexical
    return candidate


def _discover_index(root: Path, revision: str) -> Path:
    base = root / "logs" / "ci"
    candidates: list[tuple[Path, str, str]] = []
    for path in base.glob("*/impact-analysis/indexes/*/impact-index.v1.json"):
        try:
            value = validate_index_bytes(path.read_bytes())
            if value.get("repository_revision") == revision.lower():
                manifest = path.with_name("index-manifest.v1.json")
                m = json.loads(manifest.read_text(encoding="utf-8"))
                candidates.append((path, str(value.get("index_id")), str(m.get("trusted_ref"))))
        except Exception:
            continue
    if not candidates:
        raise ImpactIndexError("missing_index", "no validated impact index found for revision")
    identities = {(idx, ref) for _, idx, ref in candidates}
    if len(identities) != 1:
        raise ImpactIndexError("index_identity_collision", "multiple index identities/provenance match revision")
    return sorted((p for p, _, _ in candidates), key=lambda p: p.as_posix())[0]


def _validated_output(root: Path, value: str) -> Path:
    # Check Windows aliases before resolve() can normalize them away.
    for part in Path(value).parts:
        if part == Path(value).anchor:
            continue
        if (part.rstrip(" .") != part or re.search(r'[<>:"|?*\x00-\x1f]', part)
                or re.fullmatch(r"(?i)(CON|PRN|AUX|NUL|COM[1-9¹²³]|LPT[1-9¹²³])(?:\..*)?", part)):
            raise ImpactIndexError("index_identity_collision", "reserved output path component")
    path = _resolve_inside(root, value)
    try:
        _ensure_no_reparse_ancestors(path, root / "logs" / "ci")
    except ImpactIndexError as exc:
        raise ImpactIndexError("path_outside_repository", "output must remain under logs/ci") from exc
    try:
        # The policy boundary is the literal repository logs/ci root, not its redirect target.
        try:
            relative = path.relative_to(root / "logs" / "ci")
        except ValueError:
            canonical_path = _lexical_absolute_path(path)
            relative = canonical_path.relative_to(
                _lexical_absolute_path(root / "logs" / "ci")
            )
            path = root / "logs" / "ci" / relative
        if not relative.parts:
            raise ValueError("output must name a file beneath logs/ci")
    except ValueError as exc:
        raise ImpactIndexError("path_outside_repository", "output must remain under logs/ci") from exc
    if path.name.casefold() in {"run-manifest.v1.json", ".impact-report-publish.lock", "publication-cleanup-failure.v1.json"}:
        raise ImpactIndexError("index_identity_collision", "reserved output filename")
    return path


def _publish_pair(root: Path, output: Path, report: dict[str, Any], manifest: dict[str, Any]) -> dict[str, Any]:
    output = _validated_output(root, str(output))
    report_data = artifact_json_bytes(report)
    report_sha = hashlib.sha256(report_data).hexdigest()
    manifest_data = artifact_json_bytes(manifest)

    def validate_report(data: bytes) -> None:
        value = json.loads(data)
        if value["status"] == "ok":
            validate_report_document(value)
        elif value.get("failure_reason", {}).get("code") != value["status"]:
            raise ImpactIndexError("invalid_manifest", "failure report status mismatch")
        if data != report_data:
            raise ImpactIndexError("internal_error", "report bytes mismatch")

    def validate_manifest(data: bytes) -> None:
        value = json.loads(data)
        if (data != manifest_data or value["status"] != report["status"]
                or value["report_path"] != output.relative_to(root).as_posix()
                or value["report_sha256"] != report_sha):
            raise ImpactIndexError("invalid_manifest", "run manifest does not bind this report")

    validate_report(report_data)
    validate_manifest(manifest_data)
    output.parent.mkdir(parents=True, exist_ok=True)
    _validated_output(root, str(output))
    lock = output.parent / ".impact-report-publish.lock"
    try:
        lock.mkdir()
    except FileExistsError as exc:
        raise ImpactIndexError("index_identity_collision", "another writer owns the output directory") from exc
    owned_identity = None
    cleanup_warning = None
    publication_error = None
    diagnostics: list[str] = []
    manifest_path = output.with_name("run-manifest.v1.json")
    try:
        if output.exists() or manifest_path.exists():
            raise ImpactIndexError("index_identity_collision", "output report or run manifest already exists")
        owned_identity = atomic_publish_bytes(output, report_data, validator=validate_report)
        atomic_publish_bytes(manifest_path, manifest_data, validator=validate_manifest)
    except Exception as exc:
        publication_error = exc
        if owned_identity is not None:
            try:
                diagnostics.extend(_rollback_report(output, owned_identity, report_data))
            except Exception as rollback_error:
                diagnostics.append(f"rollback could not complete; possible residual report: {output}; reason: {rollback_error}")
    finally:
        try:
            lock.rmdir()
        except Exception as exc:
            cleanup_warning = f"writer lock cleanup failed; residual lock: {lock}; reason: {exc}"
    if publication_error is not None:
        if cleanup_warning:
            diagnostics.append(cleanup_warning)
        code = publication_error.code if isinstance(publication_error, ImpactIndexError) else "internal_error"
        reason = str(publication_error)
        if diagnostics:
            reason += "; " + "; ".join(diagnostics)
        raise ImpactIndexError(code, reason) from publication_error
    return {"cleanup_warning": cleanup_warning} if cleanup_warning else {}


def _rollback_report(output: Path, owned_identity: Any, report_data: bytes) -> list[str]:
    """Compensate only a verified owned report; never hide the publication error."""
    try:
        current = output.stat()
    except FileNotFoundError:
        return []
    except Exception as exc:
        return [f"rollback identity unavailable; possible residual report: {output}; reason: {exc}"]
    identity_fields = ("st_dev", "st_ino", "st_ctime_ns", "st_mtime_ns")
    if any(getattr(current, field) != getattr(owned_identity, field) for field in identity_fields):
        return [f"rollback ownership changed; residual report retained at: {output}"]
    try:
        unchanged = output.read_bytes() == report_data
    except Exception as exc:
        return [f"rollback content unavailable; possible residual report: {output}; reason: {exc}"]
    if not unchanged:
        return [f"rollback content changed; residual report retained at: {output}"]
    try:
        output.unlink()
        return []
    except Exception as cleanup_error:
        quarantine = output.with_name(f".unpublished-{uuid.uuid4()}.tmp")
        try:
            output.rename(quarantine)
        except Exception as quarantine_error:
            return [f"publication rollback failed; residual report: {output}; delete: {cleanup_error}; quarantine: {quarantine_error}"]
        return [f"unpublished report quarantined at {quarantine}; delete: {cleanup_error}"]


def _failure_evidence(root: Path, output: Path | None, run_id: str, target: Any,
                      revision: str | None, reason: ImpactIndexError) -> dict[str, Any]:
    isolated = root / "logs" / "ci" / _utc_date() / "impact-analysis" / ("failed-" + run_id) / "impact-report.v1.json"
    candidates = [output, isolated] if output is not None and output != isolated else [isolated]
    errors = []
    for candidate in candidates:
        try:
            candidate = _validated_output(root, str(candidate))
            diagnostic_reason = reason
            if errors:
                diagnostic_reason = ImpactIndexError(reason.code, reason.reason + "; prior evidence publication failed: " + "; ".join(errors))
            report = failure_report(target, revision, diagnostic_reason)
            manifest = {
                "schema_version": "newrouge.impact-analysis-run-manifest.v1", "run_id": run_id,
                "report_path": candidate.relative_to(root).as_posix(), "status": reason.code,
                "report_sha256": hashlib.sha256(artifact_json_bytes(report)).hexdigest(),
                "failure_reason": report["failure_reason"], "generated_at": report["generated_at"],
            }
            cleanup = _publish_pair(root, candidate, report, manifest)
            if errors:
                cleanup["evidence_warning"] = "; ".join(errors)
            return {"evidence_saved": True, "report_path": manifest["report_path"], "report_sha256": manifest["report_sha256"], **cleanup}
        except Exception as exc:
            errors.append(str(exc))
    return {"evidence_saved": False, "evidence_error": "; ".join(errors)}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Analyze a target against an immutable Impact Index. Stable failure codes: "
        + ", ".join(f"{k}={v}" for k, v in sorted(EXIT_CODES.items()))
    )
    parser.add_argument("--target", required=True, help='JSON target, e.g. {"type":"event","id":"RewardOfferPresentedEvent"}')
    parser.add_argument("--revision", required=True, help="Full 40-character Git commit SHA.")
    parser.add_argument("--trusted-ref", default=None)
    parser.add_argument("--index", default=None, help="Repository-relative impact-index.v1.json (or containing directory).")
    parser.add_argument("--frozen-context", "--frozen-context-path", dest="frozen_context", required=False)
    parser.add_argument("--consumer", default=None, choices=["chapter4", "chapter5", "chapter6", "review"])
    parser.add_argument("--task-id", default=None)
    parser.add_argument("--binding-evidence", default=None)
    parser.add_argument("--output", default=None, help="Report path; defaults to an isolated UTC run directory.")
    parser.add_argument("--repository-root", default=".")
    args = parser.parse_args(argv)
    root = Path(args.repository_root).resolve()
    run_id = str(uuid.uuid4())
    output_path: Path | None = None
    target_input: Any = {}
    revision: str | None = None
    publication_started = False
    try:
        requested_output = args.output or str(root / "logs" / "ci" / _utc_date() / "impact-analysis" / run_id / "impact-report.v1.json")
        output_path = _validated_output(root, requested_output)
        if len(args.revision.strip()) != 40 or any(c not in "0123456789abcdefABCDEF" for c in args.revision.strip()):
            raise ImpactIndexError("revision_mismatch", "revision must be a full 40-character Git SHA")
        revision = args.revision.strip().lower()
        if isinstance(args.target, str):
            try:
                parsed_target = json.loads(args.target)
                artifact_json_bytes(parsed_target)
                target_input = parsed_target
            except (ValueError, UnicodeError):
                raise ImpactIndexError("unsupported_target", f"invalid target JSON: {ascii(args.target)}")
        else:
            target_input = args.target
        index_path = _resolve_inside(root, args.index) if args.index else _discover_index(root, revision)
        try:
            index_path.relative_to((root / "logs" / "ci").resolve())
        except ValueError as exc:
            raise ImpactIndexError("path_outside_repository", "index must remain under logs/ci immutable roots") from exc
        if output_path.exists() or output_path.with_name("run-manifest.v1.json").exists():
            raise ImpactIndexError("index_identity_collision", "output report or run manifest already exists")
        if index_path.is_dir(): index_path = index_path / "impact-index.v1.json"
        analyzer = ImpactAnalyzer(root, index_path, revision, args.trusted_ref)
        if not args.frozen_context:
            raise ImpactIndexError("invalid_kcp_binding", "--frozen-context is required for successful reports")
        binding = load_frozen_binding(root, args.frozen_context, revision, args.consumer, args.task_id)
        report = analyzer.analyze(target_input, binding)
        report_sha = hashlib.sha256(artifact_json_bytes(report)).hexdigest()
        manifest = {
            "schema_version": "newrouge.impact-analysis-run-manifest.v1", "run_id": run_id,
            "report_path": output_path.relative_to(root).as_posix(), "report_sha256": report_sha,
            "index_id": report["index_id"], "index_path": index_path.relative_to(root).as_posix(), "index_sha256": report["index_sha256"],
            "repository_revision": revision, "knowledge_binding_sha256": binding["frozen_context_sha256"],
            "status": "ok", "generated_at": report["generated_at"],
        }
        if args.binding_evidence:
            sidecar = _resolve_inside(root, args.binding_evidence)
            if not sidecar.exists():
                raise ImpactIndexError("invalid_kcp_binding", "binding evidence is missing")
            sidecar_bytes = sidecar.read_bytes()
            sidecar_doc = json.loads(sidecar_bytes.decode("utf-8"))
            if sidecar_doc.get("repository_revision") != revision:
                raise ImpactIndexError("revision_mismatch", "binding evidence revision mismatch")
            manifest["binding_evidence_path"] = sidecar.relative_to(root).as_posix()
            manifest["binding_evidence_sha256"] = hashlib.sha256(sidecar_bytes).hexdigest()
        publication_started = True
        cleanup = _publish_pair(root, output_path, report, manifest)
        print(json.dumps({"status": "ok", "run_id": run_id, "report_path": manifest["report_path"], "report_sha256": report_sha, **cleanup}, ensure_ascii=False, sort_keys=True))
        return 0
    except Exception as exc:
        reason = exc if isinstance(exc, ImpactIndexError) else ImpactIndexError("internal_error", str(exc))
        evidence = _failure_evidence(root, None if publication_started else output_path,
                                     run_id, target_input, revision, reason)
        print(json.dumps({"status": "failed", "code": reason.code, "exit_code": reason.exit_code,
                          "reason": reason.reason, "run_id": run_id, **evidence}, ensure_ascii=False, sort_keys=True))
        return reason.exit_code


if __name__ == "__main__":
    raise SystemExit(main())
