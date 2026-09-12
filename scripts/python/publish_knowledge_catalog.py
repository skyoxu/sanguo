from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from _knowledge_catalog_builder import GitSnapshot, build_layers
from _knowledge_locator_core import locate


POLICY_PATH = Path("knowledge/policies/consumer-policies.v1.json")
EXCLUSIONS_PATH = Path("knowledge/policies/source-exclusions.v1.json")
SUITE_PATH = Path("knowledge/evaluation/queries.v1.json")
CANONICAL_PATHS = {
    "snapshot": Path("knowledge/snapshots/repository-source-snapshot.v1.json"),
    "catalog": Path("knowledge/catalogs/repository-knowledge-catalog.v1.json"),
    "projections": Path("knowledge/projections/consumer-projections.v1.json"),
}
INDEX_ROOT = Path("knowledge/indexes")
CONTROL_PLANE_PATHS = (
    "knowledge/policies",
    "knowledge/evaluation",
    "scripts/python/_knowledge_catalog_builder.py",
    "scripts/python/_knowledge_locator_core.py",
    "scripts/python/publish_knowledge_catalog.py",
)
GENERATION_ARTIFACTS = (
    "snapshot",
    "catalog",
    "projections",
    "policies",
    "exclusions",
    "query_suite",
    "evaluation",
)


class PublicationBlocked(ValueError):
    def __init__(self, reason: str, *, details: dict[str, Any] | None = None) -> None:
        super().__init__(reason)
        self.reason = reason
        self.details = details


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _prefixed_sha(value: Any) -> str:
    return "sha256:" + hashlib.sha256(_canonical_bytes(value)).hexdigest()


def _atomic_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", newline="\n", delete=False, dir=path.parent, suffix=".tmp") as handle:
        handle.write(text)
        temporary = Path(handle.name)
    os.replace(temporary, path)


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _git(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", "-C", str(root), *args], text=True, encoding="utf-8", capture_output=True, check=False)


def _control_plane_clean(root: Path) -> bool:
    completed = _git(root, "status", "--porcelain", "--", *CONTROL_PLANE_PATHS)
    return completed.returncode == 0 and not completed.stdout.strip()


def _matches(candidate: dict[str, Any], expectation: dict[str, Any]) -> bool:
    path = str(candidate.get("path", ""))
    any_paths = expectation.get("any_paths", [])
    prefixes = expectation.get("any_path_prefixes", [])
    domains = expectation.get("domains", [])
    statuses = expectation.get("statuses", [])
    if any_paths and path not in any_paths:
        return False
    if prefixes and not any(path.startswith(prefix) for prefix in prefixes):
        return False
    if domains and candidate.get("primary_domain") not in domains:
        return False
    if statuses and candidate.get("status") not in statuses:
        return False
    return True


def _evaluate(catalog: dict[str, Any], projections: dict[str, Any], policies: dict[str, Any], suite: dict[str, Any]) -> dict[str, Any]:
    by_consumer = {
        item.get("consumer"): item
        for item in policies.get("policies", [])
        if isinstance(item, dict) and isinstance(item.get("consumer"), str)
    }
    projection_by_consumer = {
        item.get("consumer"): item
        for item in projections.get("projections", [])
        if isinstance(item, dict) and isinstance(item.get("consumer"), str)
    }
    failures: list[dict[str, Any]] = []
    cases = list(suite.get("cases", []))
    snapshot = catalog.get("source_snapshot", {})
    for case in cases:
        consumer = case.get("consumer")
        policy = by_consumer.get(consumer)
        projection = projection_by_consumer.get(consumer)
        if policy is None or projection is None:
            failures.append({
                "id": case.get("id"),
                "consumer": consumer,
                "query": case.get("query"),
                "reason": "consumer_policy_or_projection_missing",
                "expected": case.get("must_include", []),
                "candidate_paths": [],
            })
            continue
        request = {
            "schema_version": "newrouge.knowledge-locator-request.v1",
            "request_id": str(case.get("id")),
            "consumer": consumer,
            "query": case.get("query"),
            "snapshot": {"ref": snapshot.get("ref"), "commit": snapshot.get("commit")},
            "policy_revision": policies.get("policy_revision"),
        }
        maximum = int(policy.get("max_candidates", 12))
        result = locate(request, catalog, policy, set(projection.get("eligible_module_ids", [])), maximum)
        candidates = list(result.get("candidates", []))
        ok = result.get("status") == case.get("expected_status", "matched")
        forbidden_hits: list[str] = []
        for prefix in case.get("forbidden_path_prefixes", []):
            hits = [str(candidate.get("path", "")) for candidate in candidates if str(candidate.get("path", "")).startswith(prefix)]
            forbidden_hits.extend(hits)
            if hits:
                ok = False
        missing_expectations: list[dict[str, Any]] = []
        for expectation in case.get("must_include", []):
            if not any(_matches(candidate, expectation) for candidate in candidates):
                missing_expectations.append(expectation)
                ok = False
        if not ok:
            failures.append({
                "id": case.get("id"),
                "consumer": consumer,
                "query": case.get("query"),
                "reason": "query_expectation_failed",
                "status": result.get("status"),
                "expected_status": case.get("expected_status", "matched"),
                "missing_expectations": missing_expectations,
                "forbidden_hits": sorted(set(forbidden_hits)),
                "candidate_paths": [candidate.get("path") for candidate in candidates],
            })
    return {
        "schema_version": "newrouge.knowledge-evaluation-report.v1",
        "status": "passed" if not failures else "failed",
        "passed": len(cases) - len(failures),
        "total": len(cases),
        "failures": failures,
    }


def _artifact_hashes(artifacts: dict[str, dict[str, Any]]) -> dict[str, str]:
    return {name: _prefixed_sha(value) for name, value in sorted(artifacts.items())}


def _manifest(artifacts: dict[str, dict[str, Any]], authority_ref: str, commit: str) -> dict[str, Any]:
    hashes = _artifact_hashes(artifacts)
    basis = {
        "authority_ref": authority_ref,
        "main_commit": commit,
        "source_snapshot_id": artifacts["snapshot"]["snapshot_id"],
        "artifacts": hashes,
    }
    generation_id = hashlib.sha256(_canonical_bytes(basis)).hexdigest()
    return {
        "schema_version": "newrouge.knowledge-publication-generation.v1",
        "generation_id": generation_id,
        **basis,
    }


def _pointer(manifest: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": "newrouge.knowledge-index-pointer.v1",
        "generation_id": manifest["generation_id"],
        "generation_sha256": _prefixed_sha(manifest),
        "source_snapshot_id": manifest["source_snapshot_id"],
        "authority_ref": manifest["authority_ref"],
        "main_commit": manifest["main_commit"],
    }


def _generation_dir(root: Path, generation_id: str) -> Path:
    return root / INDEX_ROOT / "generations" / generation_id


def _validate_generation(root: Path, pointer: dict[str, Any], *, require_current_ref: bool) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    generation_id = pointer.get("generation_id")
    if not isinstance(generation_id, str) or not re.fullmatch(r"[0-9a-f]{64}", generation_id):
        raise PublicationBlocked("generation_id_invalid")
    generation = _generation_dir(root, generation_id)
    manifest = _load(generation / "manifest.json")
    if manifest.get("generation_id") != generation_id or pointer.get("generation_sha256") != _prefixed_sha(manifest):
        raise PublicationBlocked("generation_manifest_binding_invalid")
    artifacts: dict[str, dict[str, Any]] = {}
    for name in GENERATION_ARTIFACTS:
        artifact = _load(generation / f"{name}.json")
        if manifest.get("artifacts", {}).get(name) != _prefixed_sha(artifact):
            raise PublicationBlocked(f"generation_artifact_hash_invalid:{name}")
        artifacts[name] = artifact
    if require_current_ref:
        current = _git(root, "rev-parse", str(manifest.get("authority_ref")))
        if current.returncode or current.stdout.strip() != manifest.get("main_commit"):
            raise PublicationBlocked("authority_ref_moved")
    return manifest, artifacts


def publish(root: Path, authority_ref: str) -> dict[str, Any]:
    if not _control_plane_clean(root):
        raise PublicationBlocked("dirty_control_plane")
    policies = _load(root / POLICY_PATH)
    exclusions = _load(root / EXCLUSIONS_PATH)
    suite = _load(root / SUITE_PATH)
    snapshot, catalog, projections = build_layers(GitSnapshot(root, authority_ref), exclusions, policies)
    evaluation = _evaluate(catalog, projections, policies, suite)
    if evaluation.get("status") != "passed":
        raise PublicationBlocked("repository_query_evaluation_failed", details={"evaluation": evaluation})
    artifacts = {
        "snapshot": snapshot,
        "catalog": catalog,
        "projections": projections,
        "policies": policies,
        "exclusions": exclusions,
        "query_suite": suite,
        "evaluation": evaluation,
    }
    manifest = _manifest(artifacts, authority_ref, snapshot["commit"])
    generation = _generation_dir(root, manifest["generation_id"])
    for name, value in artifacts.items():
        _atomic_json(generation / f"{name}.json", value)
    _atomic_json(generation / "manifest.json", manifest)
    pointer = _pointer(manifest)
    _validate_generation(root, pointer, require_current_ref=True)

    _atomic_json(root / CANONICAL_PATHS["snapshot"], snapshot)
    _atomic_json(root / CANONICAL_PATHS["catalog"], catalog)
    _atomic_json(root / CANONICAL_PATHS["projections"], projections)
    _atomic_json(root / INDEX_ROOT / "current.json", pointer)
    _atomic_json(root / INDEX_ROOT / "last-known-good.json", pointer)
    return {"status": "published", "pointer": pointer, "evaluation": evaluation}


def check_current(root: Path) -> dict[str, Any]:
    pointer_path = root / INDEX_ROOT / "current.json"
    if not pointer_path.is_file():
        raise PublicationBlocked("current_pointer_missing")
    pointer = _load(pointer_path)
    manifest, artifacts = _validate_generation(root, pointer, require_current_ref=True)
    for name in ("snapshot", "catalog", "projections"):
        canonical = _load(root / CANONICAL_PATHS[name])
        if canonical != artifacts[name]:
            raise PublicationBlocked(f"canonical_artifact_mismatch:{name}")
    if _load(root / POLICY_PATH) != artifacts["policies"]:
        raise PublicationBlocked("current_policy_mismatch")
    if _load(root / EXCLUSIONS_PATH) != artifacts["exclusions"]:
        raise PublicationBlocked("current_exclusions_mismatch")
    if _load(root / SUITE_PATH) != artifacts["query_suite"]:
        raise PublicationBlocked("current_query_suite_mismatch")
    if artifacts["evaluation"].get("status") != "passed":
        raise PublicationBlocked("published_evaluation_not_passed")
    return {"status": "current", "pointer": pointer, "manifest": manifest}


def restore_lkg(root: Path) -> dict[str, Any]:
    pointer_path = root / INDEX_ROOT / "last-known-good.json"
    if not pointer_path.is_file():
        raise PublicationBlocked("lkg_pointer_missing")
    pointer = _load(pointer_path)
    _, artifacts = _validate_generation(root, pointer, require_current_ref=False)
    for name in ("snapshot", "catalog", "projections"):
        _atomic_json(root / CANONICAL_PATHS[name], artifacts[name])
    _atomic_json(root / INDEX_ROOT / "current.json", pointer)
    return {"status": "restored", "pointer": pointer}


def main() -> int:
    parser = argparse.ArgumentParser(description="Publish or recover validated newrouge repository knowledge generations.")
    parser.add_argument("--repository-root", type=Path, default=Path.cwd())
    parser.add_argument("--authority-ref", default="refs/heads/main")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--publish", action="store_true")
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--restore-lkg", action="store_true")
    args = parser.parse_args()
    root = args.repository_root.resolve()
    try:
        if args.publish:
            result = publish(root, args.authority_ref)
        elif args.check:
            result = check_current(root)
        else:
            result = restore_lkg(root)
    except PublicationBlocked as exc:
        payload: dict[str, Any] = {
            "schema_version": "newrouge.knowledge-publication-result.v1",
            "status": "blocked",
            "reason": exc.reason,
        }
        if exc.details:
            payload["details"] = exc.details
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
        return 2
    except (OSError, json.JSONDecodeError, subprocess.SubprocessError) as exc:
        print(json.dumps({"schema_version": "newrouge.knowledge-publication-result.v1", "status": "blocked", "reason": str(exc)}, ensure_ascii=False, sort_keys=True))
        return 2
    print(json.dumps({"schema_version": "newrouge.knowledge-publication-result.v1", **result}, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
