from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

from _knowledge_locator_core import locate


def _canonical_hash(value: Any) -> str:
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


def _git_blob_hash(root: Path, commit: str, path: str) -> str | None:
    completed = subprocess.run(["git", "-C", str(root), "show", f"{commit}:{path}"], capture_output=True, check=False)
    return hashlib.sha256(completed.stdout).hexdigest() if completed.returncode == 0 else None


def _fresh(root: Path, catalog: dict[str, Any]) -> bool:
    snapshot = catalog.get("source_snapshot", {})
    ref = snapshot.get("ref")
    commit = snapshot.get("commit")
    if not isinstance(ref, str) or not isinstance(commit, str):
        return False
    current = subprocess.run(["git", "-C", str(root), "rev-parse", ref], capture_output=True, text=True, encoding="utf-8", check=False)
    if current.returncode or current.stdout.strip() != commit:
        return False
    for source in snapshot.get("sources", []):
        if not isinstance(source, dict):
            return False
        if _git_blob_hash(root, commit, str(source.get("path", ""))) != source.get("sha256"):
            return False
    return True


def _publication_valid(root: Path, catalog: dict[str, Any], policies: dict[str, Any], projections: dict[str, Any]) -> bool:
    pointer_path = root / "knowledge/indexes/current.json"
    try:
        pointer = json.loads(pointer_path.read_text(encoding="utf-8"))
        generation_id = pointer.get("generation_id")
        if pointer.get("schema_version") != "newrouge.knowledge-index-pointer.v1" or not isinstance(generation_id, str) or not re.fullmatch(r"[0-9a-f]{64}", generation_id):
            return False
        generation = root / "knowledge/indexes/generations" / generation_id
        manifest = json.loads((generation / "manifest.json").read_text(encoding="utf-8"))
        if (
            manifest.get("schema_version") != "newrouge.knowledge-publication-generation.v1"
            or manifest.get("generation_id") != generation_id
            or pointer.get("generation_sha256") != _canonical_hash(manifest)
            or pointer.get("source_snapshot_id") != manifest.get("source_snapshot_id")
            or pointer.get("authority_ref") != manifest.get("authority_ref")
            or pointer.get("main_commit") != manifest.get("main_commit")
        ):
            return False
        snapshot = catalog.get("source_snapshot", {})
        exclusions = json.loads((root / "knowledge/policies/source-exclusions.v1.json").read_text(encoding="utf-8"))
        query_suite = json.loads((root / "knowledge/evaluation/queries.v1.json").read_text(encoding="utf-8"))
        expected = {
            "snapshot": snapshot,
            "catalog": catalog,
            "policies": policies,
            "projections": projections,
            "exclusions": exclusions,
            "query_suite": query_suite,
        }
        for name, value in expected.items():
            if manifest.get("artifacts", {}).get(name) != _canonical_hash(value):
                return False
            if json.loads((generation / f"{name}.json").read_text(encoding="utf-8")) != value:
                return False
        evaluation = json.loads((generation / "evaluation.json").read_text(encoding="utf-8"))
        if manifest.get("artifacts", {}).get("evaluation") != _canonical_hash(evaluation) or evaluation.get("status") != "passed":
            return False
    except (OSError, json.JSONDecodeError):
        return False
    return True


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="Locate authoritative newrouge repository knowledge without synthesizing answers.")
    parser.add_argument("--repository-root", type=Path, default=Path.cwd())
    parser.add_argument("--catalog", type=Path, default=Path("knowledge/catalogs/repository-knowledge-catalog.v1.json"))
    parser.add_argument("--policies", type=Path, default=Path("knowledge/policies/consumer-policies.v1.json"))
    parser.add_argument("--projections", type=Path, default=Path("knowledge/projections/consumer-projections.v1.json"))
    parser.add_argument("--max-candidates", type=int, default=12)
    parser.add_argument("--allow-unpublished-inputs", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    root = args.repository_root.resolve()
    rooted = lambda path: path if path.is_absolute() else root / path
    request = json.load(sys.stdin)
    catalog_path = rooted(args.catalog)
    policy_path = rooted(args.policies)
    projection_path = rooted(args.projections)
    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    policies = json.loads(policy_path.read_text(encoding="utf-8"))
    projections = json.loads(projection_path.read_text(encoding="utf-8"))
    snapshot = catalog.get("source_snapshot", {})
    policy = next((item for item in policies.get("policies", []) if item.get("consumer") == request.get("consumer")), None)
    projection = next((item for item in projections.get("projections", []) if item.get("consumer") == request.get("consumer")), None)
    bindings_ok = (
        projections.get("source_snapshot_id") == snapshot.get("snapshot_id")
        and projections.get("catalog_sha256") == _canonical_hash(catalog)
        and projections.get("policy_revision") == policies.get("policy_revision") == request.get("policy_revision")
        and projections.get("policy_sha256") == _canonical_hash(policies)
        and request.get("snapshot") == {"ref": snapshot.get("ref"), "commit": snapshot.get("commit")}
    )
    canonical_paths = (
        catalog_path == root / "knowledge/catalogs/repository-knowledge-catalog.v1.json"
        and policy_path == root / "knowledge/policies/consumer-policies.v1.json"
        and projection_path == root / "knowledge/projections/consumer-projections.v1.json"
    )
    publication_ok = args.allow_unpublished_inputs or not canonical_paths or _publication_valid(root, catalog, policies, projections)
    if policy is None or projection is None or not bindings_ok or not publication_ok or not _fresh(root, catalog):
        status, candidates = "blocked", []
    else:
        maximum = min(args.max_candidates, int(policy.get("max_candidates", args.max_candidates)))
        core = locate(request, catalog, policy, set(projection.get("eligible_module_ids", [])), maximum)
        status, candidates = core["status"], core["candidates"]
    print(json.dumps({
        "schema_version": "newrouge.knowledge-locator-result.v1",
        "request_id": request.get("request_id"),
        "status": status,
        "snapshot": request.get("snapshot"),
        "policy_revision": request.get("policy_revision"),
        "candidates": candidates,
    }, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
