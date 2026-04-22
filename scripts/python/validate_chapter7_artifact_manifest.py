#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


REQUIRED_ARTIFACT_TYPES = ["input-snapshot", "ui-gdd", "candidate-sidecar", "summary"]


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def validate(*, repo_root: Path, manifest_path: Path) -> tuple[int, dict[str, Any]]:
    manifest_path = manifest_path.resolve()
    payload = _load_json(manifest_path)
    artifacts = payload.get("artifacts", [])
    missing_top_level = [
        key
        for key in ["schema_version", "run_profile", "action", "status", "out_dir", "artifacts"]
        if key not in payload
    ]
    missing_artifact_types = [
        artifact_type
        for artifact_type in REQUIRED_ARTIFACT_TYPES
        if artifact_type not in [str(item.get("artifact_type") or "") for item in artifacts if isinstance(item, dict)]
    ]
    missing_files: list[str] = []
    hash_mismatch_artifact_types: list[str] = []
    malformed_entries: list[int] = []

    for index, item in enumerate(artifacts):
        if not isinstance(item, dict):
            malformed_entries.append(index)
            continue
        required_entry_fields = ["artifact_type", "producer_step", "path", "relative_path", "sha256"]
        if any(field not in item for field in required_entry_fields):
            malformed_entries.append(index)
            continue
        artifact_type = str(item["artifact_type"])
        path = Path(str(item["path"]))
        if not path.is_absolute():
            path = repo_root / path
        if not path.exists():
            missing_files.append(str(item["path"]).replace("\\", "/"))
            continue
        expected_hash = str(item["sha256"])
        if expected_hash == "non-idempotent-summary":
            continue
        actual_hash = _sha256_file(path)
        if actual_hash != expected_hash:
            hash_mismatch_artifact_types.append(artifact_type)

    status = "ok"
    if missing_top_level or missing_artifact_types or missing_files or hash_mismatch_artifact_types or malformed_entries:
        status = "fail"
    result = {
        "action": "validate-chapter7-artifact-manifest",
        "status": status,
        "manifest": str(manifest_path).replace("\\", "/"),
        "schema_version": payload.get("schema_version"),
        "run_profile": payload.get("run_profile"),
        "artifact_count": len(artifacts) if isinstance(artifacts, list) else 0,
        "missing_top_level": missing_top_level,
        "missing_artifact_types": missing_artifact_types,
        "missing_files": missing_files,
        "hash_mismatch_artifact_types": hash_mismatch_artifact_types,
        "malformed_entries": malformed_entries,
    }
    return (0 if status == "ok" else 1), result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate Chapter 7 artifact manifest contract and hashes.")
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--out", default="")
    args = parser.parse_args(argv)

    repo_root = Path(args.repo_root).resolve()
    rc, payload = validate(repo_root=repo_root, manifest_path=Path(args.manifest))
    out = Path(args.out) if args.out else Path(args.manifest).with_name("artifact-manifest-validation.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(
        "CHAPTER7_ARTIFACT_MANIFEST "
        f"status={payload['status']} artifacts={payload['artifact_count']} out={str(out).replace('\\', '/')}"
    )
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
