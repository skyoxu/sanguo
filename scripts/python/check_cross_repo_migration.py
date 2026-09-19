#!/usr/bin/env python3
"""Validate repository-neutral source-to-target migration reconciliation manifests."""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import subprocess
import urllib.error
import urllib.request
from pathlib import Path, PurePosixPath
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DIR = Path("docs/migration/reconciliation")
SCHEMA_VERSION = "repo.cross-repo-migration-reconciliation.v1"
SUMMARY_SCHEMA_VERSION = "repo.cross-repo-migration-reconciliation-check.v1"
CLASSIFICATIONS = {
    "copy_exact",
    "adapt_target_native",
    "already_present",
    "derived_regenerate",
    "business_only_drop",
    "protocol_name_retain",
}
HEX40_RE = re.compile(r"^[0-9a-f]{40}$")
REPO_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
MIGRATION_MARKER_RE = re.compile(r"(?mi)^Migration-Key:\s*(\S+)\s*$")


def _safe_repo_name(value: Any) -> bool:
    text = str(value or "")
    if not REPO_RE.fullmatch(text):
        return False
    owner, repo = text.split("/", 1)
    return owner not in {".", ".."} and repo not in {".", ".."}


def _strict_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in pairs:
        if key in out:
            raise ValueError(f"duplicate JSON key: {key}")
        out[key] = value
    return out


def _read_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=_strict_object)
    if not isinstance(data, dict):
        raise ValueError("manifest root must be an object")
    return data


def _safe_repo_path(root: Path, value: str) -> tuple[Path | None, str | None]:
    text = str(value or "").replace("\\", "/").strip()
    pure = PurePosixPath(text)
    if (not text or pure.is_absolute() or re.match(r"^[A-Za-z]:/", text)
            or any(part in {"", ".", ".."} for part in pure.parts)):
        return None, f"unsafe repository path: {value!r}"
    return root.joinpath(*pure.parts), None


def _git_blob_sha(path: Path, repo_root: Path | None = None) -> str:
    if repo_root is not None:
        try:
            rel = path.resolve().relative_to(repo_root.resolve()).as_posix()
            proc = subprocess.run(
                ["git", "-C", str(repo_root), "hash-object", f"--path={rel}", rel],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace",
                check=False,
            )
            value = (proc.stdout or "").strip()
            if proc.returncode == 0 and HEX40_RE.fullmatch(value):
                return value
        except (OSError, ValueError):
            pass
    data = path.read_bytes()
    header = f"blob {len(data)}\0".encode("ascii")
    return hashlib.sha1(header + data).hexdigest()


def _changed_files_sha256(values: list[str]) -> str:
    payload = json.dumps(sorted(values), ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _require_existing_paths(root: Path, values: Any, field: str, source_path: str) -> list[str]:
    errors: list[str] = []
    if not isinstance(values, list):
        return [f"{source_path}: {field} must be an array"]
    for raw in values:
        if not isinstance(raw, str):
            errors.append(f"{source_path}: {field} entries must be strings")
            continue
        candidate, err = _safe_repo_path(root, raw)
        if err:
            errors.append(f"{source_path}: {field}: {err}")
        elif candidate is None or not candidate.exists():
            errors.append(f"{source_path}: {field} path does not exist: {raw}")
    return errors


def validate_manifest(doc: dict[str, Any], repo_root: Path) -> list[str]:
    errors: list[str] = []
    if doc.get("schema_version") != SCHEMA_VERSION:
        errors.append(f"schema_version must equal {SCHEMA_VERSION}")

    source = doc.get("source")
    target = doc.get("target")
    entries = doc.get("entries")
    if not isinstance(source, dict):
        errors.append("source must be an object")
        source = {}
    if not isinstance(target, dict):
        errors.append("target must be an object")
        target = {}
    if not isinstance(entries, list):
        errors.append("entries must be an array")
        entries = []

    if not isinstance(source.get("repo"), str) or not _safe_repo_name(source.get("repo")):
        errors.append("source.repo must be a safe owner/name")
    if not isinstance(source.get("pr"), int) or int(source.get("pr") or 0) <= 0:
        errors.append("source.pr must be a positive integer")
    if not HEX40_RE.fullmatch(str(source.get("merge_commit") or "")):
        errors.append("source.merge_commit must be a full 40-character lowercase git hash")
    if not isinstance(target.get("repo"), str) or not _safe_repo_name(target.get("repo")):
        errors.append("target.repo must be a safe owner/name")

    identity_declared = "migration_key" in target
    if identity_declared:
        target_pr = target.get("pr")
        target_branch = str(target.get("branch") or "")
        migration_key = str(target.get("migration_key") or "")
        if type(target_pr) is not int or target_pr < 1:
            errors.append("target.pr must be a positive integer when canonical identity is declared")
        if not target_branch or target_branch.startswith("/") or ".." in target_branch or any(ch.isspace() for ch in target_branch):
            errors.append("target.branch must be a safe non-empty branch name when canonical identity is declared")
        expected_key = f"{source.get('repo')}@{source.get('merge_commit')}->{target.get('repo')}"
        if migration_key != expected_key:
            errors.append("target.migration_key must bind source repo + merge commit + target repo")

    changed_files = source.get("changed_files")
    if not isinstance(changed_files, list) or not changed_files or not all(isinstance(item, str) and item for item in changed_files):
        errors.append("source.changed_files must be a non-empty string array")
        changed_files = []
    if len(changed_files) != len(set(changed_files)):
        errors.append("source.changed_files contains duplicates")
    for source_item in changed_files:
        pure = PurePosixPath(str(source_item).replace("\\", "/"))
        normalized_source = str(source_item).replace("\\", "/")
        if (pure.is_absolute() or re.match(r"^[A-Za-z]:/", normalized_source)
                or any(part in {"", ".", ".."} for part in pure.parts)):
            errors.append(f"unsafe source changed-file path: {source_item!r}")
    declared_count = source.get("changed_file_count")
    if declared_count != len(changed_files):
        errors.append(f"source.changed_file_count={declared_count!r} does not match changed_files={len(changed_files)}")
    expected_inventory_sha = _changed_files_sha256(changed_files)
    declared_inventory_sha = str(source.get("changed_files_sha256") or "").lower()
    if declared_inventory_sha and declared_inventory_sha != expected_inventory_sha:
        errors.append("source.changed_files_sha256 does not match canonical changed_files inventory")

    seen: set[str] = set()
    for index, raw_entry in enumerate(entries):
        label = f"entries[{index}]"
        if not isinstance(raw_entry, dict):
            errors.append(f"{label} must be an object")
            continue
        source_path = raw_entry.get("source_path")
        if not isinstance(source_path, str) or not source_path:
            errors.append(f"{label}.source_path must be a non-empty string")
            continue
        if source_path in seen:
            errors.append(f"duplicate entry for source path: {source_path}")
        seen.add(source_path)

        classification = raw_entry.get("classification")
        if classification not in CLASSIFICATIONS:
            errors.append(f"{source_path}: unsupported classification {classification!r}")
            continue
        if not str(raw_entry.get("rationale") or "").strip():
            errors.append(f"{source_path}: rationale must not be blank")

        target_paths = raw_entry.get("target_paths", [])
        validation_paths = raw_entry.get("validation_paths", [])
        if classification == "copy_exact":
            if not isinstance(target_paths, list) or len(target_paths) != 1:
                errors.append(f"{source_path}: copy_exact requires exactly one target path")
                continue
            errors.extend(_require_existing_paths(repo_root, target_paths, "target_paths", source_path))
            source_blob_sha = str(raw_entry.get("source_blob_sha") or "")
            if not HEX40_RE.fullmatch(source_blob_sha):
                errors.append(f"{source_path}: copy_exact requires source_blob_sha")
            else:
                candidate, err = _safe_repo_path(repo_root, target_paths[0])
                if err:
                    errors.append(f"{source_path}: {err}")
                elif candidate is not None and not candidate.is_file():
                    errors.append(f"{source_path}: copy_exact target must be a file: {target_paths[0]}")
                elif candidate is not None:
                    target_blob_sha = _git_blob_sha(candidate, repo_root)
                    if target_blob_sha != source_blob_sha:
                        errors.append(f"{source_path}: copy_exact drift target={target_blob_sha} source={source_blob_sha}")
        elif classification in {"adapt_target_native", "already_present", "protocol_name_retain"}:
            if not isinstance(target_paths, list) or not target_paths:
                errors.append(f"{source_path}: {classification} requires target_paths")
            else:
                errors.extend(_require_existing_paths(repo_root, target_paths, "target_paths", source_path))
            if not isinstance(validation_paths, list) or not validation_paths:
                errors.append(f"{source_path}: {classification} requires validation_paths")
            else:
                errors.extend(_require_existing_paths(repo_root, validation_paths, "validation_paths", source_path))
            if classification == "protocol_name_retain" and not raw_entry.get("retained_identifiers"):
                errors.append(f"{source_path}: protocol_name_retain requires retained_identifiers")
        elif classification == "derived_regenerate":
            if target_paths:
                errors.extend(_require_existing_paths(repo_root, target_paths, "target_paths", source_path))
            if not str(raw_entry.get("regeneration_command") or "").strip():
                errors.append(f"{source_path}: derived_regenerate requires regeneration_command")
        elif classification == "business_only_drop" and target_paths:
            errors.append(f"{source_path}: business_only_drop must not declare target_paths")

    changed_set = set(changed_files)
    missing = sorted(changed_set - seen)
    extra = sorted(seen - changed_set)
    if missing:
        errors.append("unclassified source files: " + ", ".join(missing))
    if extra:
        errors.append("entries not present in source.changed_files: " + ", ".join(extra))
    if len(entries) != len(changed_files):
        errors.append(f"entry count {len(entries)} does not match changed file count {len(changed_files)}")
    return errors


def _github_json(url: str, token: str) -> Any:
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "cross-repo-migration-reconciliation",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    except (OSError, urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError) as exc:
        raise ValueError(f"GitHub source verification failed: {exc}") from exc


def fetch_github_source_inventory(source: dict[str, Any], token: str = "") -> dict[str, Any]:
    repo = str(source.get("repo") or "")
    pr = int(source.get("pr") or 0)
    if not _safe_repo_name(repo) or pr <= 0:
        raise ValueError("source.repo/source.pr are invalid")
    base = f"https://api.github.com/repos/{repo}"
    pr_doc = _github_json(f"{base}/pulls/{pr}", token)
    if not isinstance(pr_doc, dict) or not pr_doc.get("merged_at"):
        raise ValueError("source PR is not merged")
    changed: list[str] = []
    page = 1
    while True:
        page_doc = _github_json(f"{base}/pulls/{pr}/files?per_page=100&page={page}", token)
        if not isinstance(page_doc, list):
            raise ValueError("source PR files response is invalid")
        changed.extend(str(item.get("filename") or "") for item in page_doc if isinstance(item, dict))
        if len(page_doc) < 100:
            break
        page += 1
        if page > 100:
            raise ValueError("source PR files pagination exceeded safety limit")
    if any(not item for item in changed):
        raise ValueError("source PR files response contains blank filename")
    return {
        "merge_commit": str(pr_doc.get("merge_commit_sha") or ""),
        "changed_files": changed,
    }


def extract_migration_key(body: str) -> str:
    match = MIGRATION_MARKER_RE.search(body or "")
    return match.group(1) if match else ""


def current_pr_from_event(event_path: str) -> dict[str, Any]:
    if not event_path:
        return {}
    path = Path(event_path)
    if not path.is_file():
        return {}
    payload = _read_json(path)
    pr = payload.get("pull_request")
    return pr if isinstance(pr, dict) else {}


def fetch_open_pull_requests(repository: str, token: str = "") -> list[dict[str, Any]]:
    if not _safe_repo_name(repository):
        raise ValueError("target repository is invalid")
    output: list[dict[str, Any]] = []
    page = 1
    while True:
        rows = _github_json(
            f"https://api.github.com/repos/{repository}/pulls?state=open&per_page=100&page={page}",
            token,
        )
        if not isinstance(rows, list):
            raise ValueError("target open pull request response is invalid")
        output.extend(row for row in rows if isinstance(row, dict))
        if len(rows) < 100:
            break
        page += 1
        if page > 100:
            raise ValueError("target pull request pagination exceeded safety limit")
    return output


def verify_target_open_pr(doc: dict[str, Any], *, event_path: str, repository: str,
                          token: str = "") -> list[str]:
    source = doc.get("source")
    target = doc.get("target")
    if not isinstance(source, dict) or not isinstance(target, dict):
        return ["source/target must be objects before canonical PR verification"]
    required = ("pr", "branch", "migration_key")
    if any(key not in target for key in required):
        return ["target canonical identity requires pr, branch and migration_key"]
    target_repo = str(target.get("repo") or "")
    if repository != target_repo:
        return [f"GITHUB_REPOSITORY mismatch expected={target_repo} actual={repository}"]
    current = current_pr_from_event(event_path)
    if not current:
        return ["pull_request event payload is required for canonical PR verification"]

    errors: list[str] = []
    expected_pr = target.get("pr")
    expected_branch = str(target.get("branch") or "")
    expected_key = str(target.get("migration_key") or "")
    head = current.get("head") if isinstance(current.get("head"), dict) else {}
    if current.get("number") != expected_pr:
        errors.append(f"current PR number does not match target.pr expected={expected_pr} actual={current.get('number')}")
    if str(head.get("ref") or "") != expected_branch:
        errors.append("current PR branch does not match target.branch")
    if extract_migration_key(str(current.get("body") or "")) != expected_key:
        errors.append("current PR Migration-Key marker does not match target.migration_key")

    try:
        open_prs = fetch_open_pull_requests(repository, token)
    except ValueError as exc:
        return errors + [str(exc)]
    matching = [
        row for row in open_prs
        if extract_migration_key(str(row.get("body") or "")) == expected_key
    ]
    if len(matching) != 1:
        errors.append(
            "expected exactly one open PR for target.migration_key; "
            f"found {[row.get('number') for row in matching]}"
        )
    elif matching[0].get("number") != expected_pr:
        errors.append("canonical open PR does not match target.pr")
    return errors


def verify_source_github(doc: dict[str, Any], token: str = "") -> list[str]:
    source = doc.get("source")
    if not isinstance(source, dict):
        return ["source must be an object before GitHub verification"]
    try:
        remote = fetch_github_source_inventory(source, token)
    except ValueError as exc:
        return [str(exc)]
    errors: list[str] = []
    if remote["merge_commit"] != source.get("merge_commit"):
        errors.append(f"source merge commit mismatch remote={remote['merge_commit']} manifest={source.get('merge_commit')}")
    remote_files = remote["changed_files"]
    manifest_files = source.get("changed_files") if isinstance(source.get("changed_files"), list) else []
    if set(remote_files) != set(manifest_files) or len(remote_files) != len(manifest_files):
        missing = sorted(set(remote_files) - set(manifest_files))
        extra = sorted(set(manifest_files) - set(remote_files))
        errors.append(f"source changed-file inventory mismatch missing={missing} extra={extra}")
    return errors


def validate_file(path: Path, repo_root: Path, *, verify_github: bool = False,
                  check_open_prs: bool = False, event_path: str = "",
                  repository: str = "", token: str = "") -> list[str]:
    try:
        doc = _read_json(path)
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        return [f"{path}: invalid JSON: {exc}"]
    errors = validate_manifest(doc, repo_root)
    if verify_github and not errors:
        errors.extend(verify_source_github(doc, token))
    if check_open_prs and not errors:
        errors.extend(verify_target_open_pr(
            doc, event_path=event_path, repository=repository, token=token
        ))
    return [f"{path}: {item}" for item in errors]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=str(REPO_ROOT))
    parser.add_argument("--dir", default=str(DEFAULT_DIR))
    parser.add_argument("--manifest", action="append", default=[])
    parser.add_argument("--require-manifests", action="store_true")
    parser.add_argument("--verify-source-github", action="store_true")
    parser.add_argument("--check-open-prs", action="store_true")
    parser.add_argument("--github-token-env", default="GITHUB_TOKEN")
    parser.add_argument("--out", default="")
    args = parser.parse_args(argv)

    root = Path(args.root).resolve()
    manifests = [root / item for item in args.manifest] if args.manifest else (
        sorted((root / args.dir).glob("*.json")) if (root / args.dir).exists() else []
    )
    errors: list[str] = []
    if not manifests and args.require_manifests:
        errors.append(f"no reconciliation manifests found under {args.dir}")
    if args.check_open_prs and len(manifests) != 1:
        errors.append("--check-open-prs requires exactly one reconciliation manifest")
    token = os.getenv(args.github_token_env, "") if (args.verify_source_github or args.check_open_prs) else ""
    event_path = os.getenv("GITHUB_EVENT_PATH", "") if args.check_open_prs else ""
    repository = os.getenv("GITHUB_REPOSITORY", "") if args.check_open_prs else ""
    for path in manifests:
        errors.extend(validate_file(
            path,
            root,
            verify_github=args.verify_source_github,
            check_open_prs=args.check_open_prs and len(manifests) == 1,
            event_path=event_path,
            repository=repository,
            token=token,
        ))

    status = "failed" if errors else ("skipped" if not manifests else "passed")
    summary = {
        "schema_version": SUMMARY_SCHEMA_VERSION,
        "status": status,
        "github_source_verified": bool(args.verify_source_github and manifests and not errors),
        "canonical_pr_verified": bool(args.check_open_prs and len(manifests) == 1 and not errors),
        "manifests": [str(path.relative_to(root)).replace("\\", "/") for path in manifests if path.is_relative_to(root)],
        "errors": errors,
    }
    out = Path(args.out) if args.out else (
        root / "logs" / "ci" / dt.date.today().isoformat() / "cross-repo-migration-reconciliation" / "summary.json"
    )
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    shown_out = out.relative_to(root).as_posix() if out.is_relative_to(root) else str(out)
    print(f"CROSS_REPO_MIGRATION_RECONCILIATION status={status} manifests={len(manifests)} errors={len(errors)} out={shown_out}")
    for item in errors:
        print(f"ERROR: {item}")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
