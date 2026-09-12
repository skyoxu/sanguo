#!/usr/bin/env python3
"""Deterministic impact-index core for the Windows-only newrouge repository.

The publication and path rules implement ADR-0011's Windows-only constraint.
"""
from __future__ import annotations

import json
import math
import os
import platform
import re
import socket
import subprocess
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from hashlib import sha256
from pathlib import Path, PurePosixPath
from typing import Any, Callable, Iterable

try:
    from impact_analysis_handoff import EXIT_CODES
except ModuleNotFoundError:  # pragma: no cover - package import path
    from scripts.python.impact_analysis_handoff import EXIT_CODES


INDEX_SCHEMA = "newrouge.impact-index.v1"
INDEX_MANIFEST_SCHEMA = "newrouge.impact-index-manifest.v1"
LOCK_SCHEMA = "newrouge.impact-index-lock.v1"
IMPLEMENTATION_REVISION = "newrouge.impact-index-builder.v1"
FULL_SHA = re.compile(r"[0-9a-f]{40}")
SHA256_HEX = re.compile(r"[0-9a-f]{64}")
SHARING_RETRY_DELAYS = (0.1, 0.2, 0.4, 0.8, 1.6)
GIT_TIMEOUT_SECONDS = 30
JCS_MAX_SAFE_INTEGER = 9_007_199_254_740_991
INDEX_FIELDS = {
    "schema_version",
    "index_schema",
    "index_id",
    "repository_revision",
    "analyzer_implementation_revision",
    "analysis_config_revision",
    "analysis_config_sha256",
    "alias_table_revision",
    "alias_table_sha256",
    "discovery_policy_sha256",
    "source_manifest_sha256",
    "source_manifest",
}
SOURCE_ENTRY_FIELDS = {
    "path",
    "sha256",
    "size_bytes",
    "git_mode",
    "source_kind",
    "parser_family",
    "parser_version",
    "included",
    "exclusion_reason",
}
MANIFEST_FIELDS = {
    "schema_version",
    "index_schema",
    "index_id",
    "artifact_path",
    "artifact_sha256",
    "repository_revision",
    "trusted_ref",
    "analyzer_implementation_revision",
    "analysis_config_revision",
    "analysis_config_sha256",
    "alias_table_revision",
    "alias_table_sha256",
    "discovery_policy_sha256",
    "source_manifest_sha256",
    "generated_at",
    "toolchain",
}
LOCK_FIELDS = {
    "schema_version",
    "index_id",
    "host",
    "pid",
    "process_start",
    "created_at",
    "owner_token",
}


class ImpactIndexError(RuntimeError):
    def __init__(self, code: str, reason: str) -> None:
        super().__init__(reason)
        self.code = code
        self.reason = reason
        self.exit_code = EXIT_CODES.get(code, EXIT_CODES["internal_error"])


def fail(code: str, reason: str) -> ImpactIndexError:
    return ImpactIndexError(code, reason)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def utc_text(value: datetime | None = None) -> str:
    current = value or utc_now()
    return current.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def sha256_bytes(value: bytes) -> str:
    return sha256(value).hexdigest()


def _jcs_key(value: str) -> bytes:
    return value.encode("utf-16-be", errors="surrogatepass")


def _jcs_text(value: Any) -> str:
    if value is None:
        return "null"
    if value is True:
        return "true"
    if value is False:
        return "false"
    if isinstance(value, str):
        return json.dumps(value, ensure_ascii=False, allow_nan=False)
    if isinstance(value, int):
        if value < -JCS_MAX_SAFE_INTEGER or value > JCS_MAX_SAFE_INTEGER:
            raise fail("invalid_manifest", "JCS integer exceeds the interoperable safe range")
        return str(value)
    if isinstance(value, float):
        if not math.isfinite(value):
            raise fail("invalid_manifest", "JCS does not permit NaN or Infinity")
        raise fail("invalid_manifest", "floating-point JCS members are not supported by this identity schema")
    if isinstance(value, list):
        return "[" + ",".join(_jcs_text(item) for item in value) + "]"
    if isinstance(value, dict):
        if any(not isinstance(key, str) for key in value):
            raise fail("invalid_manifest", "JCS object keys must be strings")
        members = []
        for key in sorted(value, key=_jcs_key):
            members.append(_jcs_text(key) + ":" + _jcs_text(value[key]))
        return "{" + ",".join(members) + "}"
    raise fail("invalid_manifest", f"unsupported JCS value type: {type(value).__name__}")


def jcs_bytes(value: Any) -> bytes:
    try:
        return _jcs_text(value).encode("utf-8")
    except UnicodeEncodeError as exc:
        raise fail("invalid_manifest", f"invalid Unicode in JCS input: {exc}") from exc


def derive_index_id(identity: dict[str, Any]) -> str:
    required = {
        "repository_revision",
        "source_manifest_sha256",
        "index_schema",
        "analyzer_implementation_revision",
        "analysis_config_revision",
    }
    if set(identity) != required or any(not isinstance(identity[key], str) or not identity[key] for key in required):
        raise fail("invalid_manifest", "index identity must contain exactly the five versioned string members")
    return "idx-" + sha256_bytes(jcs_bytes(identity))


def normalize_repository_path(value: str) -> str:
    if not isinstance(value, str):
        raise fail("path_outside_repository", "repository path must be a string")
    raw = value.strip().replace("\\", "/")
    if (
        not raw
        or "\x00" in raw
        or raw.startswith("/")
        or raw.startswith("//")
        or re.match(r"^[A-Za-z]:", raw)
    ):
        raise fail("path_outside_repository", f"invalid repository-relative path: {value!r}")
    path = PurePosixPath(raw)
    if not path.parts or any(part in {"", ".", ".."} for part in path.parts):
        raise fail("path_outside_repository", f"invalid repository-relative path: {value!r}")
    normalized = path.as_posix()
    if normalized == ".":
        raise fail("path_outside_repository", f"invalid repository-relative path: {value!r}")
    return normalized


def resolve_repository_path(root: Path, value: str, *, must_exist: bool = False) -> Path:
    normalized = normalize_repository_path(value)
    repository_root = root.resolve()
    candidate = repository_root.joinpath(*PurePosixPath(normalized).parts)
    try:
        resolved = candidate.resolve(strict=must_exist)
        _relative_to_repository(resolved, repository_root)
    except (OSError, ValueError) as exc:
        raise fail("path_outside_repository", f"path escapes repository: {normalized}") from exc
    return candidate


def _is_reparse_point(path: Path) -> bool:
    try:
        # Inspect the directory entry itself, including junction attributes.
        if path.is_symlink() or os.path.islink(os.fspath(path)):
            return True
        if os.name == "nt":
            attributes = os.lstat(os.fspath(path)).st_file_attributes
            return bool(attributes & 0x400)
    except OSError:
        return False
    return False


def _lexical_absolute_path(path: Path) -> Path:
    """Expand Windows 8.3 aliases without following junctions or symlinks."""
    absolute = Path(os.path.abspath(path))
    if os.name != "nt":
        return absolute
    import ctypes

    get_long = ctypes.windll.kernel32.GetLongPathNameW
    get_long.argtypes = [ctypes.c_wchar_p, ctypes.c_wchar_p, ctypes.c_uint32]
    get_long.restype = ctypes.c_uint32
    suffix: list[str] = []
    current = absolute
    while True:
        buffer = ctypes.create_unicode_buffer(32768)
        result = get_long(str(current), buffer, len(buffer))
        if 0 < result < len(buffer):
            return Path(buffer.value).joinpath(*reversed(suffix))
        if current == current.parent:
            return absolute
        suffix.append(current.name)
        current = current.parent


def _canonical_windows_path(path: Path) -> Path:
    """Normalize long/short Windows aliases before containment checks."""
    absolute = os.path.realpath(os.path.abspath(str(path)))
    if os.name == "nt":
        try:
            import ctypes

            get_long = ctypes.windll.kernel32.GetLongPathNameW
            get_long.argtypes = [ctypes.c_wchar_p, ctypes.c_wchar_p, ctypes.c_uint32]
            get_long.restype = ctypes.c_uint32
            size = 260
            while size <= 32768:
                buffer = ctypes.create_unicode_buffer(size)
                result = get_long(absolute, buffer, size)
                if result == 0:
                    break
                if result < size:
                    absolute = buffer.value
                    break
                size = result + 1
        except (AttributeError, OSError):
            pass
    return Path(os.path.normcase(absolute))


def _relative_to_repository(path: Path, root: Path) -> Path:
    canonical_path = _canonical_windows_path(path)
    canonical_root = _canonical_windows_path(root)
    try:
        return canonical_path.relative_to(canonical_root)
    except ValueError as exc:
        raise fail("path_outside_repository", f"path escapes repository: {path}") from exc


def _ensure_no_reparse_ancestors(path: Path, root: Path) -> None:
    """Reject symlink/junction/reparse ancestors without resolving through them."""
    root_abs = _lexical_absolute_path(root)
    path_abs = _lexical_absolute_path(path)
    try:
        # Preserve lexical path segments so reparse-point ancestors are still
        # inspected instead of being hidden by realpath canonicalization.
        relative = path_abs.relative_to(root_abs)
    except ValueError as exc:
        # Windows paths are case-insensitive, while Path.relative_to is not.
        # Compare the lexical components case-insensitively and retain the
        # original spelling for reparse-point inspection.
        root_parts = root_abs.parts
        path_parts = path_abs.parts
        if len(path_parts) < len(root_parts) or any(
            left.casefold() != right.casefold()
            for left, right in zip(path_parts[: len(root_parts)], root_parts)
        ):
            raise fail("path_outside_repository", f"path escapes repository: {path}") from exc
        relative = Path(*path_parts[len(root_parts) :])
    current = root_abs
    if _is_reparse_point(current):
        raise fail("path_outside_repository", f"reparse-point repository root: {current}")
    # Walk lexical ancestors from the repository root so a mocked or native
    # junction marker is observed before any content/hash checks run.
    for part in relative.parts:
        current = current / part
        if _is_reparse_point(current):
            raise fail("path_outside_repository", f"reparse-point path boundary: {current}")


def artifact_json_bytes(value: dict[str, Any]) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False) + "\n").encode("utf-8")


def _strict_json_object(data: bytes, *, code: str, label: str) -> dict[str, Any]:
    if data.startswith(b"\xef\xbb\xbf"):
        raise fail(code, f"UTF-8 BOM is forbidden: {label}")

    def reject_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise fail(code, f"duplicate JSON key in {label}: {key}")
            result[key] = value
        return result

    def reject_constant(value: str) -> Any:
        raise fail(code, f"non-finite JSON constant in {label}: {value}")

    try:
        value = json.loads(
            data.decode("utf-8"),
            object_pairs_hook=reject_duplicates,
            parse_constant=reject_constant,
        )
    except ImpactIndexError:
        raise
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise fail(code, f"invalid UTF-8 JSON in {label}: {exc}") from exc
    if not isinstance(value, dict):
        raise fail(code, f"JSON document must be an object: {label}")
    return value


def load_json_bytes(path: Path, *, code: str = "invalid_manifest") -> tuple[bytes, dict[str, Any]]:
    try:
        data = path.read_bytes()
    except OSError as exc:
        raise fail(code, f"unable to read {path}: {exc}") from exc
    return data, _strict_json_object(data, code=code, label=str(path))


def _git(
    root: Path,
    *args: str,
    text: bool = False,
    input_data: bytes | str | None = None,
) -> subprocess.CompletedProcess[Any]:
    try:
        return subprocess.run(
            ["git", "-C", str(root), *args],
            capture_output=True,
            text=text,
            encoding="utf-8" if text else None,
            input=input_data,
            check=False,
            timeout=GIT_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired as exc:
        raise fail("source_read_failure", f"Git command timed out after {GIT_TIMEOUT_SECONDS} seconds") from exc


@dataclass(frozen=True)
class GitTreeEntry:
    mode: str
    object_type: str
    object_id: str
    path: str
    size_bytes: int | None


class GitTreeSnapshot:
    def __init__(self, root: Path, revision: str, trusted_ref: str | None) -> None:
        self.root = root.resolve()
        normalized_revision = str(revision or "").strip().lower()
        if not FULL_SHA.fullmatch(normalized_revision):
            raise fail("revision_mismatch", "revision must be a full 40-character lowercase Git SHA")
        verified = _git(self.root, "rev-parse", "--verify", f"{normalized_revision}^{{commit}}", text=True)
        if verified.returncode or verified.stdout.strip().lower() != normalized_revision:
            raise fail("revision_mismatch", "revision is not an available Git commit")
        head = _git(self.root, "rev-parse", "HEAD", text=True)
        if head.returncode or head.stdout.strip().lower() != normalized_revision:
            raise fail("revision_mismatch", "checked-out HEAD does not match requested revision")
        if trusted_ref:
            ref_result = _git(self.root, "rev-parse", "--verify", f"{trusted_ref}^{{commit}}", text=True)
            if ref_result.returncode or ref_result.stdout.strip().lower() != normalized_revision:
                raise fail("revision_mismatch", "trusted ref does not resolve to requested revision")
            self.trusted_ref = trusted_ref
        else:
            self.trusted_ref = f"detached:{normalized_revision}"
        self.revision = normalized_revision
        result = _git(self.root, "ls-tree", "-lrz", "--full-tree", normalized_revision)
        if result.returncode:
            raise fail("source_read_failure", "unable to enumerate trusted Git tree")
        entries: list[GitTreeEntry] = []
        seen_case: dict[str, str] = {}
        for record in result.stdout.split(b"\0"):
            if not record:
                continue
            try:
                metadata, raw_path = record.split(b"\t", 1)
                parts = metadata.decode("ascii").split()
                if len(parts) != 4:
                    raise ValueError("unexpected ls-tree metadata")
                mode, object_type, object_id, raw_size = parts
                size_bytes = None if raw_size == "-" else int(raw_size)
                path = normalize_repository_path(raw_path.decode("utf-8"))
            except (ValueError, UnicodeDecodeError, ImpactIndexError) as exc:
                raise fail("invalid_manifest", f"invalid Git tree entry: {exc}") from exc
            folded = path.casefold()
            previous = seen_case.get(folded)
            if previous is not None and previous != path:
                raise fail("invalid_manifest", f"case-ambiguous Git paths: {previous}, {path}")
            seen_case[folded] = path
            entries.append(GitTreeEntry(mode, object_type, object_id, path, size_bytes))
        self.entries = tuple(entries)
        self._blob_cache: dict[str, bytes] = {}
        blob_entries = [entry for entry in self.entries if entry.object_type == "blob"]
        if blob_entries:
            request = b"".join((entry.object_id.encode("ascii") + b"\n") for entry in blob_entries)
            batch = _git(self.root, "cat-file", "--batch", input_data=request)
            if batch.returncode:
                raise fail("source_read_failure", "unable to read trusted Git blobs in batch")
            cursor = 0
            for entry in blob_entries:
                header_end = batch.stdout.find(b"\n", cursor)
                if header_end < 0:
                    raise fail("source_read_failure", f"malformed Git batch response: {entry.path}")
                header = batch.stdout[cursor:header_end].split()
                cursor = header_end + 1
                if len(header) != 3 or header[1] != b"blob":
                    raise fail("source_read_failure", f"missing tracked blob: {entry.path}")
                size = int(header[2])
                data = batch.stdout[cursor : cursor + size]
                if len(data) != size or batch.stdout[cursor + size : cursor + size + 1] != b"\n":
                    raise fail("source_read_failure", f"truncated Git batch response: {entry.path}")
                self._blob_cache[entry.object_id] = bytes(data)
                cursor += size + 1

    def read_blob(self, entry: GitTreeEntry) -> bytes:
        if entry.object_type != "blob":
            raise fail("source_read_failure", f"unsupported non-blob source: {entry.path}")
        try:
            return self._blob_cache[entry.object_id]
        except KeyError as exc:
            raise fail("source_read_failure", f"missing tracked blob: {entry.path}") from exc

    def verify_worktree(self, entries: Iterable[dict[str, Any]]) -> None:
        tree_by_path = {entry.path: entry for entry in self.entries}
        included_paths: list[str] = []
        normalized_paths: set[str] = set()
        for manifest_entry in entries:
            if manifest_entry.get("included") is not True:
                continue
            path = str(manifest_entry["path"])
            lexical_candidate = self.root.joinpath(*PurePosixPath(normalize_repository_path(path)).parts)
            try:
                _ensure_no_reparse_ancestors(lexical_candidate, self.root)
            except ImpactIndexError as exc:
                if exc.code == "path_outside_repository":
                    raise fail("source_read_failure", exc.reason) from exc
                raise
            candidate = resolve_repository_path(self.root, path)
            try:
                _ensure_no_reparse_ancestors(candidate, self.root)
            except ImpactIndexError as exc:
                if exc.code == "path_outside_repository":
                    raise fail("source_read_failure", exc.reason) from exc
                raise
            if candidate.is_symlink():
                raise fail("source_read_failure", f"symlink-ambiguous source: {path}")
            if not candidate.is_file():
                raise fail("source_read_failure", f"tracked source is missing from worktree: {path}")
            try:
                resolved = candidate.resolve(strict=True)
                resolved.relative_to(self.root)
            except (OSError, ValueError) as exc:
                raise fail("source_read_failure", f"unable to reread source {path}: {exc}") from exc
            tree_entry = tree_by_path.get(path)
            if tree_entry is None:
                raise fail("source_read_failure", f"tracked source is absent from trusted tree: {path}")
            try:
                current_bytes = candidate.read_bytes()
            except OSError as exc:
                raise fail("source_read_failure", f"unable to reread source {path}: {exc}") from exc
            if path in tree_by_path and path in {
                "scripts/python/impact_analysis_config.v1.json",
                "scripts/python/impact_target_aliases.v1.json",
            } and current_bytes.startswith(b"\xef\xbb\xbf"):
                raise fail("invalid_manifest", f"UTF-8 BOM is forbidden in identity source: {path}")
            if sha256_bytes(current_bytes) == manifest_entry.get("sha256"):
                included_paths.append(path)
                continue
            # Policy files are tracked with LF normalization.  A Windows
            # checkout may materialize CRLF even when the trusted blob is LF;
            # accept that representation only when it is byte-equivalent
            # after the declared text normalization.
            if path in {
                "scripts/python/impact_analysis_config.v1.json",
                "scripts/python/impact_target_aliases.v1.json",
            }:
                trusted_bytes = self.read_blob(tree_entry)
                normalized_policy = re.sub(rb"\r+\n", b"\n", current_bytes).replace(b"\r", b"\n")
                if normalized_policy == trusted_bytes:
                    included_paths.append(path)
                    normalized_paths.add(path)
                    continue
            clean_hash = _git(
                self.root,
                f"hash-object",
                f"--path={path}",
                "--stdin",
                text=False,
                input_data=current_bytes,
            )
            clean_hash_text = bytes(clean_hash.stdout or b"").decode("ascii", errors="ignore").strip().lower()
            if clean_hash.returncode or clean_hash_text != tree_entry.object_id:
                raise fail("dirty_state", f"included source differs from trusted Git tree: {path}")
            included_paths.append(path)
        if included_paths:
            current = _git(self.root, "diff", "--name-only", "-z", self.revision, text=False)
            if current.returncode:
                raise fail("source_read_failure", "unable to verify included worktree sources")
            changed = {
                item.decode("utf-8")
                for item in bytes(current.stdout).split(b"\0")
                if item
            }
            if changed.intersection(set(included_paths) - normalized_paths):
                raise fail("dirty_state", "included source differs from trusted Git tree")

    def verify_revision(self) -> None:
        head = _git(self.root, "rev-parse", "HEAD", text=True)
        if head.returncode or head.stdout.strip().lower() != self.revision:
            raise fail("revision_mismatch", "checked-out HEAD changed during index build")
        if self.trusted_ref.startswith("detached:"):
            return
        trusted = _git(self.root, "rev-parse", "--verify", f"{self.trusted_ref}^{{commit}}", text=True)
        if trusted.returncode or trusted.stdout.strip().lower() != self.revision:
            raise fail("revision_mismatch", "trusted ref changed during index build")


def _validate_string_list(value: Any, field: str, *, allow_empty: bool = False) -> list[str]:
    if not isinstance(value, list) or (not value and not allow_empty) or any(not isinstance(item, str) or not item for item in value):
        qualifier = "possibly empty " if allow_empty else ""
        raise fail("invalid_manifest", f"{field} must be a {qualifier}string array")
    return list(value)


def validate_config(config: dict[str, Any]) -> dict[str, Any]:
    required_fields = {
        "schema_version",
        "analysis_config_revision",
        "index_schema",
        "text_encoding",
        "maximum_file_size_bytes",
        "allow_identity_only",
        "scan_roots",
        "identity_files",
        "source_rules",
        "exclusions",
    }
    if set(config) != required_fields:
        raise fail("invalid_manifest", "impact analysis config fields are incomplete or unsupported")
    if config.get("schema_version") != "newrouge.impact-analysis-config.v1":
        raise fail("invalid_manifest", "unsupported impact analysis config schema")
    for field in ("analysis_config_revision", "index_schema", "text_encoding"):
        if not isinstance(config.get(field), str) or not config[field]:
            raise fail("invalid_manifest", f"config field is required: {field}")
    if config["index_schema"] != INDEX_SCHEMA or config["text_encoding"] != "utf-8-no-bom":
        raise fail("invalid_manifest", "unsupported index schema or text encoding")
    maximum = config.get("maximum_file_size_bytes")
    if not isinstance(maximum, int) or isinstance(maximum, bool) or maximum <= 0:
        raise fail("invalid_manifest", "maximum_file_size_bytes must be a positive integer")
    if not isinstance(config.get("allow_identity_only"), bool):
        raise fail("invalid_manifest", "allow_identity_only must be boolean")
    config["scan_roots"] = [
        normalize_repository_path(item).rstrip("/")
        for item in _validate_string_list(config.get("scan_roots"), "scan_roots")
    ]
    config["identity_files"] = [
        normalize_repository_path(item)
        for item in _validate_string_list(config.get("identity_files"), "identity_files")
    ]
    for field in ("scan_roots", "identity_files"):
        values = config[field]
        folded = [item.casefold() for item in values]
        if len(folded) != len(set(folded)):
            raise fail("invalid_manifest", f"{field} contains duplicate paths")
    rules = config.get("source_rules")
    if not isinstance(rules, list) or not rules:
        raise fail("invalid_manifest", "source_rules must be a non-empty ordered array")
    for rule in rules:
        if not isinstance(rule, dict):
            raise fail("invalid_manifest", "source rule must be an object")
        if set(rule) != {"suffixes", "path_prefixes", "source_kind", "parser_family", "parser_version", "binary"}:
            raise fail("invalid_manifest", "source rule fields are incomplete or unsupported")
        suffixes = _validate_string_list(rule.get("suffixes"), "source_rules.suffixes")
        folded_suffixes = [item.casefold() for item in suffixes]
        if len(folded_suffixes) != len(set(folded_suffixes)):
            raise fail("invalid_manifest", "source_rules.suffixes contains duplicate suffixes")
        prefixes = rule.get("path_prefixes", [])
        rule["path_prefixes"] = [
            normalize_repository_path(item).rstrip("/")
            for item in _validate_string_list(
                prefixes,
                "source_rules.path_prefixes",
                allow_empty=True,
            )
        ]
        for field in ("source_kind", "parser_family", "parser_version"):
            if not isinstance(rule.get(field), str) or not rule[field]:
                raise fail("invalid_manifest", f"source rule field is required: {field}")
        if not isinstance(rule.get("binary"), bool):
            raise fail("invalid_manifest", "source rule binary must be boolean")
    exclusions = config.get("exclusions")
    if not isinstance(exclusions, list):
        raise fail("invalid_manifest", "exclusions must be an ordered array")
    for exclusion in exclusions:
        if not isinstance(exclusion, dict) or set(exclusion) - {"reason", "path_prefix", "path_pattern"} or not isinstance(exclusion.get("reason"), str) or not exclusion["reason"]:
            raise fail("invalid_manifest", "each exclusion requires a reason")
        prefix = exclusion.get("path_prefix")
        pattern = exclusion.get("path_pattern")
        if bool(prefix) == bool(pattern):
            raise fail("invalid_manifest", "each exclusion requires exactly one path_prefix or path_pattern")
        if prefix:
            exclusion["path_prefix"] = normalize_repository_path(prefix).rstrip("/")
        else:
            raw_pattern = str(pattern).replace("\\", "/")
            if raw_pattern.startswith("/") or re.match(r"^[A-Za-z]:", raw_pattern) or ".." in PurePosixPath(raw_pattern).parts:
                raise fail("path_outside_repository", f"invalid exclusion pattern: {pattern}")
            exclusion["path_pattern"] = raw_pattern
    required_identities = {
        "scripts/python/impact_analysis_index.py",
        "scripts/python/build_impact_index.py",
        "scripts/python/impact_analysis_config.v1.json",
        "scripts/python/impact_target_aliases.v1.json",
        "scripts/python/impact_runtime.py",
    }
    if not config.get("allow_identity_only") and not required_identities.issubset(set(config["identity_files"])):
        raise fail("invalid_manifest", "config identity_files must include all Index Core identity files")
    return config


def validate_aliases(aliases: dict[str, Any]) -> dict[str, Any]:
    if set(aliases) != {"schema_version", "alias_table_revision", "aliases"}:
        raise fail("invalid_manifest", "target alias fields are incomplete or unsupported")
    if aliases.get("schema_version") != "newrouge.impact-target-aliases.v1":
        raise fail("invalid_manifest", "unsupported target alias schema")
    if not isinstance(aliases.get("alias_table_revision"), str) or not aliases["alias_table_revision"]:
        raise fail("invalid_manifest", "alias_table_revision is required")
    table = aliases.get("aliases")
    if not isinstance(table, dict):
        raise fail("invalid_manifest", "aliases must be a kind-scoped object")
    if set(table) != {"event", "contract"}:
        raise fail("invalid_manifest", "aliases must contain exactly event and contract tables")
    for kind, mappings in table.items():
        if not isinstance(kind, str) or not kind or not isinstance(mappings, dict):
            raise fail("invalid_manifest", "alias kinds and mapping tables must be objects")
        aliases_folded = [alias.casefold() for alias in mappings]
        if len(aliases_folded) != len(set(aliases_folded)):
            raise fail("invalid_manifest", "alias mappings contain case-insensitive collisions")
        if any(
            not isinstance(alias, str)
            or not isinstance(target, str)
            or not alias
            or not target
            for alias, target in mappings.items()
        ):
            raise fail("invalid_manifest", "alias mappings must contain non-empty strings")
    return aliases


def _path_selected(path: str, roots: list[str], exact: set[str]) -> bool:
    if path in exact:
        return True
    return any(path == root or path.startswith(root + "/") for root in roots)


def _exclusion_reason(path: str, exclusions: list[dict[str, Any]]) -> str | None:
    from fnmatch import fnmatchcase

    for rule in exclusions:
        prefix = rule.get("path_prefix")
        pattern = rule.get("path_pattern")
        if prefix and (path == prefix or path.startswith(prefix + "/")):
            return str(rule["reason"])
        if pattern and fnmatchcase(path, str(pattern)):
            return str(rule["reason"])
    return None


def _source_rule(path: str, rules: list[dict[str, Any]]) -> dict[str, Any] | None:
    lowered = path.casefold()
    for rule in rules:
        prefixes = rule.get("path_prefixes", [])
        prefix_matches = not prefixes or any(
            path == prefix or path.startswith(prefix + "/")
            for prefix in prefixes
        )
        if prefix_matches and any(lowered.endswith(suffix.casefold()) for suffix in rule["suffixes"]):
            return rule
    return None


def _trusted_blob_for_path(snapshot: GitTreeSnapshot, path: str) -> bytes:
    normalized = normalize_repository_path(path)
    for entry in snapshot.entries:
        if entry.path == normalized:
            if entry.object_type != "blob" or entry.mode not in {"100644", "100755"}:
                raise fail("invalid_manifest", f"identity source is not a regular blob: {normalized}")
            return snapshot.read_blob(entry)
    raise fail("invalid_manifest", f"identity source missing from trusted Git tree: {normalized}")


def _validate_identity_worktree_file(root: Path, relative: str, validator, label: str) -> None:
    """Validate mutable identity inputs before source verification.

    Syntax/encoding defects in policy files are manifest defects, while valid
    content that differs from the trusted blob remains a dirty worktree.
    """
    path = resolve_repository_path(root, relative)
    try:
        _ensure_no_reparse_ancestors(path, root)
        data = path.read_bytes()
    except ImpactIndexError as exc:
        if exc.code == "path_outside_repository":
            raise fail("invalid_manifest", f"identity path is not repository-local: {relative}") from exc
        raise
    except OSError as exc:
        raise fail("invalid_manifest", f"unable to read identity source {relative}: {exc}") from exc
    if data.startswith(b"\xef\xbb\xbf"):
        raise fail("invalid_manifest", f"UTF-8 BOM is forbidden in identity source: {relative}")
    value = _strict_json_object(data, code="invalid_manifest", label=label)
    validator(value)


def build_source_manifest(
    snapshot: GitTreeSnapshot,
    config: dict[str, Any],
    *,
    config_path: str,
    aliases_path: str,
) -> tuple[list[dict[str, Any]], str]:
    exact = set(config["identity_files"])
    exact.update({normalize_repository_path(config_path), normalize_repository_path(aliases_path)})
    roots = list(config["scan_roots"])
    tree_paths = {entry.path for entry in snapshot.entries}
    missing_roots = [
        root
        for root in roots
        if not any(path == root or path.startswith(root + "/") for path in tree_paths)
    ]
    if missing_roots:
        raise fail("invalid_manifest", "scan root missing from Git tree: " + ", ".join(missing_roots))
    entries: list[dict[str, Any]] = []
    discovered: set[str] = set()
    for tree_entry in snapshot.entries:
        path = tree_entry.path
        if not _path_selected(path, roots, exact):
            continue
        discovered.add(path)
        if tree_entry.mode == "160000" or tree_entry.object_type != "blob":
            raise fail("source_read_failure", f"submodules and non-blob sources are unsupported: {path}")
        if tree_entry.mode == "120000":
            raise fail("source_read_failure", f"symlink-ambiguous source is unsupported: {path}")
        if tree_entry.size_bytes is None:
            raise fail("source_read_failure", f"Git blob size is unavailable: {path}")
        if tree_entry.size_bytes > config["maximum_file_size_bytes"]:
            code = "invalid_manifest" if path in exact else "source_read_failure"
            raise fail(code, f"selected source exceeds maximum file size before capture: {path}")
        data = snapshot.read_blob(tree_entry)
        digest = sha256_bytes(data)
        reason = _exclusion_reason(path, config["exclusions"])
        rule = _source_rule(path, config["source_rules"])
        included = reason is None and rule is not None
        if reason is None and rule is None:
            reason = "unsupported_file_class"
        if included and not rule.get("binary", False):
            if data.startswith(b"\xef\xbb\xbf"):
                code = "invalid_manifest" if path in exact else "source_read_failure"
                raise fail(code, f"UTF-8 BOM is forbidden in indexed source: {path}")
            try:
                data.decode("utf-8")
            except UnicodeDecodeError as exc:
                raise fail("source_read_failure", f"indexed text is not UTF-8: {path}") from exc
        if path in exact and not included:
            raise fail("invalid_manifest", f"required identity source is excluded or unsupported: {path}")
        entries.append(
            {
                "path": path,
                "sha256": digest,
                "size_bytes": len(data),
                "git_mode": tree_entry.mode,
                "source_kind": rule["source_kind"] if rule else "unsupported",
                "parser_family": rule["parser_family"] if rule else "none",
                "parser_version": rule["parser_version"] if rule else "none",
                "included": included,
                "exclusion_reason": None if included else reason,
            }
        )
    missing = sorted(exact - discovered, key=lambda value: value.encode("utf-8"))
    if missing:
        raise fail("invalid_manifest", "required identity source missing from Git tree: " + ", ".join(missing))
    if not config["allow_identity_only"] and not any(
        entry["included"] and entry["path"] not in exact for entry in entries
    ):
        raise fail("invalid_manifest", "scan roots contain no supported non-identity sources")
    entries.sort(key=lambda item: (item["path"].encode("utf-8"), item["source_kind"]))
    manifest_sha = sha256_bytes(jcs_bytes(entries))
    return entries, manifest_sha


def _validate_sha(value: Any, field: str) -> str:
    text = str(value or "")
    if not SHA256_HEX.fullmatch(text):
        raise fail("invalid_manifest", f"invalid SHA-256 field: {field}")
    return text


def validate_index_document(value: dict[str, Any]) -> None:
    if set(value) != INDEX_FIELDS:
        raise fail("invalid_manifest", "impact index fields are incomplete or unsupported")
    if value.get("schema_version") != INDEX_SCHEMA or value.get("index_schema") != INDEX_SCHEMA:
        raise fail("invalid_manifest", "unsupported impact index schema")
    revision = str(value.get("repository_revision") or "")
    if not FULL_SHA.fullmatch(revision):
        raise fail("invalid_manifest", "index repository revision is invalid")
    manifest = value.get("source_manifest")
    if not isinstance(manifest, list) or not manifest:
        raise fail("invalid_manifest", "index source manifest is empty")
    paths = []
    for entry in manifest:
        if not isinstance(entry, dict):
            raise fail("invalid_manifest", "source manifest entry must be an object")
        if set(entry) != SOURCE_ENTRY_FIELDS:
            raise fail("invalid_manifest", "source manifest entry fields are incomplete or unsupported")
        if not isinstance(entry.get("path"), str):
            raise fail("invalid_manifest", "source manifest path must be a string")
        path = normalize_repository_path(entry["path"])
        if path != entry["path"]:
            raise fail("invalid_manifest", "source manifest path must be normalized")
        paths.append(path)
        _validate_sha(entry.get("sha256"), "source_manifest.sha256")
        size_bytes = entry.get("size_bytes")
        if not isinstance(size_bytes, int) or isinstance(size_bytes, bool) or size_bytes < 0:
            raise fail("invalid_manifest", "source manifest size_bytes must be a non-negative integer")
        if entry.get("git_mode") not in {"100644", "100755"}:
            raise fail("invalid_manifest", "source manifest git_mode is invalid")
        for field in ("source_kind", "parser_family", "parser_version"):
            if not isinstance(entry.get(field), str) or not entry[field]:
                raise fail("invalid_manifest", f"source manifest {field} must be a non-empty string")
        if not isinstance(entry.get("included"), bool):
            raise fail("invalid_manifest", "source manifest included must be boolean")
        exclusion_reason = entry.get("exclusion_reason")
        if entry["included"]:
            if exclusion_reason is not None:
                raise fail("invalid_manifest", "included source must not have an exclusion reason")
            if entry["source_kind"] == "unsupported" or entry["parser_family"] == "none" or entry["parser_version"] == "none":
                raise fail("invalid_manifest", "included source must declare a supported parser")
        else:
            if not isinstance(exclusion_reason, str) or not exclusion_reason:
                raise fail("invalid_manifest", "excluded source must have an exclusion reason")
            if exclusion_reason == "unsupported_file_class" and (
                entry["source_kind"] != "unsupported"
                or entry["parser_family"] != "none"
                or entry["parser_version"] != "none"
            ):
                raise fail("invalid_manifest", "unsupported source classification is inconsistent")
    if paths != sorted(paths, key=lambda item: item.encode("utf-8")) or len(paths) != len(set(paths)):
        raise fail("invalid_manifest", "source manifest paths must be unique and UTF-8 sorted")
    expected_manifest_sha = sha256_bytes(jcs_bytes(manifest))
    if value.get("source_manifest_sha256") != expected_manifest_sha:
        raise fail("invalid_manifest", "source manifest hash mismatch")
    identity = {
        "repository_revision": revision,
        "source_manifest_sha256": expected_manifest_sha,
        "index_schema": INDEX_SCHEMA,
        "analyzer_implementation_revision": value.get("analyzer_implementation_revision"),
        "analysis_config_revision": value.get("analysis_config_revision"),
    }
    if value.get("index_id") != derive_index_id(identity):
        raise fail("invalid_manifest", "index identity mismatch")
    _validate_sha(value.get("analysis_config_sha256"), "analysis_config_sha256")
    _validate_sha(value.get("alias_table_sha256"), "alias_table_sha256")
    _validate_sha(value.get("discovery_policy_sha256"), "discovery_policy_sha256")
    for field in ("analyzer_implementation_revision", "analysis_config_revision", "alias_table_revision"):
        if not isinstance(value.get(field), str) or not value[field]:
            raise fail("invalid_manifest", f"index field is required: {field}")


def validate_index_bytes(data: bytes) -> dict[str, Any]:
    value = _strict_json_object(data, code="invalid_manifest", label="impact index")
    validate_index_document(value)
    return value


def _validate_utc_z(value: Any, field: str, *, code: str = "invalid_manifest") -> datetime:
    if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z", value):
        raise fail(code, f"{field} must be a UTC Z timestamp")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise fail(code, f"{field} is invalid") from exc
    if parsed.tzinfo != timezone.utc:
        raise fail(code, f"{field} must be UTC")
    return parsed


def validate_manifest_bytes(
    data: bytes,
    *,
    index_bytes: bytes | None = None,
    expected_index: dict[str, Any] | None = None,
    expected_trusted_ref: str | None = None,
) -> dict[str, Any]:
    value = _strict_json_object(data, code="invalid_manifest", label="index manifest")
    if set(value) != MANIFEST_FIELDS or value.get("schema_version") != INDEX_MANIFEST_SCHEMA:
        raise fail("invalid_manifest", "unsupported index manifest schema")
    if value.get("index_schema") != INDEX_SCHEMA:
        raise fail("invalid_manifest", "index manifest index schema is invalid")
    if not isinstance(value.get("index_id"), str) or not re.fullmatch(r"idx-[0-9a-f]{64}", value["index_id"]):
        raise fail("invalid_manifest", "index manifest identity is invalid")
    if value.get("artifact_path") != "impact-index.v1.json":
        raise fail("invalid_manifest", "index manifest artifact path is invalid")
    _validate_sha(value.get("artifact_sha256"), "artifact_sha256")
    if index_bytes is not None and value["artifact_sha256"] != sha256_bytes(index_bytes):
        raise fail("invalid_manifest", "index artifact hash differs from manifest")
    if not FULL_SHA.fullmatch(str(value.get("repository_revision") or "")):
        raise fail("invalid_manifest", "index manifest repository revision is invalid")
    if not isinstance(value.get("trusted_ref"), str) or not value["trusted_ref"]:
        raise fail("invalid_manifest", "index manifest trusted ref is invalid")
    for field in ("analyzer_implementation_revision", "analysis_config_revision", "alias_table_revision"):
        if not isinstance(value.get(field), str) or not value[field]:
            raise fail("invalid_manifest", f"index manifest field is required: {field}")
    for field in (
        "analysis_config_sha256",
        "alias_table_sha256",
        "discovery_policy_sha256",
        "source_manifest_sha256",
    ):
        _validate_sha(value.get(field), field)
    _validate_utc_z(value.get("generated_at"), "generated_at")
    toolchain = value.get("toolchain")
    if not isinstance(toolchain, dict) or set(toolchain) != {"python"}:
        raise fail("invalid_manifest", "index manifest toolchain is invalid")
    if not isinstance(toolchain["python"], str) or not re.fullmatch(r"\d+\.\d+\.\d+", toolchain["python"]):
        raise fail("invalid_manifest", "index manifest Python version is invalid")
    if expected_index is not None:
        validate_index_document(expected_index)
        comparisons = {
            "index_schema": expected_index["index_schema"],
            "index_id": expected_index["index_id"],
            "repository_revision": expected_index["repository_revision"],
            "analyzer_implementation_revision": expected_index["analyzer_implementation_revision"],
            "analysis_config_revision": expected_index["analysis_config_revision"],
            "analysis_config_sha256": expected_index["analysis_config_sha256"],
            "alias_table_revision": expected_index["alias_table_revision"],
            "alias_table_sha256": expected_index["alias_table_sha256"],
            "discovery_policy_sha256": expected_index["discovery_policy_sha256"],
            "source_manifest_sha256": expected_index["source_manifest_sha256"],
        }
        if any(value[field] != expected for field, expected in comparisons.items()):
            raise fail("invalid_manifest", "index manifest lineage differs from expected index")
    if expected_trusted_ref is not None and value["trusted_ref"] != expected_trusted_ref:
        raise fail("invalid_manifest", "index manifest trusted ref differs from requested provenance")
    return value


def _sharing_violation(exc: OSError) -> bool:
    return isinstance(exc, PermissionError) or getattr(exc, "winerror", None) in {32, 33}


def atomic_publish_bytes(
    destination: Path,
    data: bytes,
    *,
    validator: Callable[[bytes], Any],
    sleep: Callable[[float], None] = time.sleep,
) -> os.stat_result:
    """Publish without overwrite and return identity captured before publication."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        raise fail("index_identity_collision", f"destination already exists: {destination}")
    temporary = destination.parent / f".{destination.name}.{uuid.uuid4()}.tmp"
    try:
        with temporary.open("xb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        reread = temporary.read_bytes()
        if reread != data:
            raise fail("internal_error", f"temporary artifact reread mismatch: {temporary}")
        validator(reread)
        identity = temporary.stat()
        if identity.st_size != len(data):
            raise fail("internal_error", f"temporary artifact size changed: {temporary}")
        for attempt in range(len(SHARING_RETRY_DELAYS) + 1):
            try:
                os.rename(temporary, destination)
                break
            except FileExistsError as exc:
                raise fail("index_identity_collision", f"destination appeared during publication: {destination}") from exc
            except OSError as exc:
                if not _sharing_violation(exc) or attempt >= len(SHARING_RETRY_DELAYS):
                    raise fail("internal_error", f"atomic replace failed for {destination}: {exc}") from exc
                sleep(SHARING_RETRY_DELAYS[attempt])
        return identity
    finally:
        for transient in (temporary,):
            try:
                transient.unlink(missing_ok=True)
            except OSError as exc:
                marker = transient.parent / f"publication-cleanup-failure.{uuid.uuid4()}.v1.json"
                try:
                    with marker.open("xb") as handle:
                        handle.write(artifact_json_bytes({"schema_version":"newrouge.impact-index-publication-cleanup-failure.v1","status":"failed","path":str(transient),"reason":str(exc)}))
                        handle.flush()
                        os.fsync(handle.fileno())
                except OSError:
                    pass


def _windows_process_info(pid: int, *, kernel32: Any | None = None, get_last_error: Callable[[], int] | None = None) -> tuple[bool, str | None]:
    """Return (alive, process-start-token) using a bounded Win32 query."""
    try:
        import ctypes
        from ctypes import wintypes
        if kernel32 is None:
            kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        if get_last_error is None:
            get_last_error = ctypes.get_last_error
        process = kernel32.OpenProcess(0x1000, False, int(pid))
        if not process:
            error = int(get_last_error())
            return (True, None) if error == 5 else (False, None)
        creation = wintypes.FILETIME(); exit_time = wintypes.FILETIME(); kernel = wintypes.FILETIME(); user = wintypes.FILETIME()
        try:
            if not kernel32.GetProcessTimes(process, ctypes.byref(creation), ctypes.byref(exit_time), ctypes.byref(kernel), ctypes.byref(user)):
                return True, None
            return True, str((creation.dwHighDateTime << 32) | creation.dwLowDateTime)
        finally:
            kernel32.CloseHandle(process)
    except (AttributeError, OSError, ImportError):
        return False, None


def _process_start_token(pid: int) -> str | None:
    if os.name == "nt":
        alive, token = _windows_process_info(pid)
        return token if alive else None
    try:
        fields = Path(f"/proc/{pid}/stat").read_text(encoding="ascii").split()
        return fields[21]
    except (OSError, IndexError, UnicodeDecodeError):
        try:
            os.kill(pid, 0)
        except OSError:
            return None
        return "alive-unverifiable"


def _pid_exists(pid: int) -> bool:
    if pid <= 0:
        return False
    if pid == os.getpid():
        return True
    if os.name == "nt":
        alive, _ = _windows_process_info(pid)
        return alive
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError:
        return False
    return True


class IndexLock:
    def __init__(
        self,
        path: Path,
        index_id: str,
        *,
        host: str | None = None,
        pid: int | None = None,
        process_start: str | None = None,
        sleep: Callable[[float], None] = time.sleep,
        now: Callable[[], datetime] = utc_now,
        process_start_lookup: Callable[[int], str | None] = _process_start_token,
    ) -> None:
        self.path = path
        self.index_id = index_id
        self.host = host or socket.gethostname()
        self.pid = pid or os.getpid()
        self.process_start = process_start or process_start_lookup(self.pid)
        if not self.process_start:
            raise fail("lock_unavailable", "current process start time cannot be verified")
        self.sleep = sleep
        self.now = now
        self.process_start_lookup = process_start_lookup
        self.owner_token = str(uuid.uuid4())
        self.held = False
        self.owned_bytes: bytes | None = None

    def _payload(self) -> dict[str, Any]:
        return {
            "schema_version": LOCK_SCHEMA,
            "index_id": self.index_id,
            "host": self.host,
            "pid": self.pid,
            "process_start": self.process_start,
            "created_at": utc_text(self.now()),
            "owner_token": self.owner_token,
        }

    def _create(self) -> bool:
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            raise fail("lock_unavailable", f"lock directory is unavailable: {exc}") from exc
        data = artifact_json_bytes(self._payload())
        try:
            descriptor = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        except FileExistsError:
            return False
        except OSError as exc:
            raise fail("lock_unavailable", f"lock path is unavailable: {exc}") from exc
        handle = None
        try:
            handle = os.fdopen(descriptor, "wb")
            with handle:
                handle.write(data)
                handle.flush()
                os.fsync(handle.fileno())
        except BaseException as exc:
            if handle is None:
                try:
                    os.close(descriptor)
                except OSError:
                    pass
            try:
                if self.path.read_bytes() == data:
                    self.path.unlink(missing_ok=True)
            except OSError:
                pass
            if isinstance(exc, OSError):
                raise fail("lock_unavailable", f"lock write failed: {exc}") from exc
            raise
        self.held = True
        self.owned_bytes = data
        return True

    def _stale_same_host(self) -> bytes | None:
        try:
            data = self.path.read_bytes()
            payload = validate_lock_bytes(data, expected_index_id=self.index_id)
            created_at = _validate_utc_z(payload["created_at"], "created_at", code="lock_unavailable")
            owner_host = payload["host"]
            owner_pid = payload["pid"]
            owner_start = payload["process_start"]
        except (OSError, ImpactIndexError) as exc:
            raise fail("lock_unavailable", f"existing lock cannot be verified: {exc}") from exc
        if owner_host != self.host:
            return None
        if self.now() - created_at.astimezone(timezone.utc) <= timedelta(minutes=5):
            return None
        actual_start = self.process_start_lookup(owner_pid)
        if actual_start is None:
            return data if not _pid_exists(owner_pid) else None
        return data if actual_start != owner_start else None

    def acquire(self) -> None:
        for attempt in range(6):
            if self._create():
                return
            stale_observation = self._stale_same_host()
            if isinstance(stale_observation, bytes):
                try:
                    quarantine = self.path.with_name(self.path.name + f".{uuid.uuid4()}.reclaim")
                    os.rename(self.path, quarantine)
                    moved = quarantine.read_bytes()
                    if moved != stale_observation:
                        if not self.path.exists():
                            self.path.write_bytes(moved)
                        quarantine.unlink(missing_ok=True)
                        raise fail("lock_unavailable", "stale lock changed during reclaim")
                    quarantine.unlink(missing_ok=True)
                except FileNotFoundError:
                    pass
                except OSError as exc:
                    raise fail("lock_unavailable", f"stale lock could not be removed: {exc}") from exc
                continue
            if attempt < 5:
                self.sleep(1.0)
        raise fail("lock_unavailable", f"index lock is unavailable: {self.index_id}")

    def release(self) -> None:
        if not self.held:
            return
        try:
            if self.owned_bytes is not None and self.path.read_bytes() == self.owned_bytes:
                tombstone = self.path.with_name(self.path.name + f".{self.owner_token}.release")
                try:
                    os.rename(self.path, tombstone)
                except OSError:
                    return
                try:
                    if tombstone.read_bytes() == self.owned_bytes:
                        tombstone.unlink(missing_ok=True)
                    else:
                        os.rename(tombstone, self.path)
                except OSError:
                    pass
        except OSError:
            pass
        finally:
            self.held = False
            self.owned_bytes = None

    def __enter__(self) -> "IndexLock":
        self.acquire()
        return self

    def __exit__(self, exc_type, exc, traceback) -> None:
        try:
            self.release()
        except BaseException:
            if exc_type is None:
                raise


def validate_lock_bytes(data: bytes, *, expected_index_id: str) -> dict[str, Any]:
    value = _strict_json_object(data, code="lock_unavailable", label="index lock")
    if set(value) != LOCK_FIELDS or value.get("schema_version") != LOCK_SCHEMA:
        raise fail("lock_unavailable", "index lock fields or schema are invalid")
    if value.get("index_id") != expected_index_id:
        raise fail("lock_unavailable", "index lock identity does not match")
    for field in ("host", "process_start", "owner_token"):
        if not isinstance(value.get(field), str) or not value[field]:
            raise fail("lock_unavailable", f"index lock field is invalid: {field}")
    pid = value.get("pid")
    if not isinstance(pid, int) or isinstance(pid, bool) or pid <= 0:
        raise fail("lock_unavailable", "index lock PID is invalid")
    _validate_utc_z(value.get("created_at"), "created_at", code="lock_unavailable")
    return value


def _relative_to_root(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return str(path.resolve())


def _expected_identity(index_document: dict[str, Any]) -> dict[str, Any]:
    return {
        "repository_revision": index_document["repository_revision"],
        "source_manifest_sha256": index_document["source_manifest_sha256"],
        "index_schema": index_document["index_schema"],
        "analyzer_implementation_revision": index_document["analyzer_implementation_revision"],
        "analysis_config_revision": index_document["analysis_config_revision"],
    }


def validate_existing_directory(
    directory: Path,
    expected: dict[str, Any],
    *,
    expected_trusted_ref: str,
    expected_toolchain: dict[str, str],
) -> dict[str, Any]:
    index_path = directory / "impact-index.v1.json"
    manifest_path = directory / "index-manifest.v1.json"
    if not index_path.is_file() or not manifest_path.is_file():
        raise fail("index_identity_collision", f"existing index directory is incomplete: {directory}")
    try:
        index_bytes = index_path.read_bytes()
        manifest_bytes = manifest_path.read_bytes()
        index_document = validate_index_bytes(index_bytes)
        manifest_document = validate_manifest_bytes(
            manifest_bytes,
            index_bytes=index_bytes,
            expected_index=expected,
            expected_trusted_ref=expected_trusted_ref,
        )
    except ImpactIndexError as exc:
        if exc.code == "index_identity_collision":
            raise
        raise fail(
            "index_identity_collision",
            f"existing index directory failed validation: {directory}: {exc.reason}",
        ) from exc
    except OSError as exc:
        raise fail("index_identity_collision", f"existing index directory cannot be read: {exc}") from exc
    if index_document != expected:
        raise fail("index_identity_collision", f"existing immutable index differs: {directory}")
    existing_python = manifest_document["toolchain"].get("python", "")
    expected_python = expected_toolchain.get("python", "")
    if not (re.fullmatch(r"\d+\.\d+\.\d+", existing_python) and re.fullmatch(r"\d+\.\d+\.\d+", expected_python)
            and existing_python.split(".")[:2] == expected_python.split(".")[:2]):
        raise fail("index_identity_collision", f"existing manifest toolchain differs: {directory}")
    return {
        "index_path": index_path,
        "manifest_path": manifest_path,
        "index_sha256": sha256_bytes(index_bytes),
        "manifest_sha256": sha256_bytes(manifest_bytes),
    }


def discover_existing(
    output_root: Path,
    expected: dict[str, Any],
    *,
    expected_trusted_ref: str,
    expected_toolchain: dict[str, str],
) -> dict[str, Any] | None:
    _ensure_no_reparse_ancestors(output_root, output_root.parent)
    candidates = sorted(
        output_root.glob(f"*/impact-analysis/indexes/{expected['index_id']}"),
        key=lambda path: path.as_posix(),
    )
    if not candidates:
        return None
    for candidate in candidates:
        _ensure_no_reparse_ancestors(candidate, output_root)
    validated = [
        validate_existing_directory(
            candidate,
            expected,
            expected_trusted_ref=expected_trusted_ref,
            expected_toolchain=expected_toolchain,
        )
        for candidate in candidates
    ]
    first_hash = validated[0]["index_sha256"]
    if any(item["index_sha256"] != first_hash for item in validated[1:]):
        raise fail("index_identity_collision", "multiple index directories have different artifact bytes")
    first_manifest_hash = validated[0]["manifest_sha256"]
    if any(item["manifest_sha256"] != first_manifest_hash for item in validated[1:]):
        raise fail("index_identity_collision", "multiple index directories have different manifest bytes")
    return validated[0]


def build_and_publish_index(
    repository_root: Path,
    *,
    revision: str,
    trusted_ref: str | None,
    config_relative: str,
    aliases_relative: str,
    output_root: Path,
    implementation_revision: str = IMPLEMENTATION_REVISION,
    reuse_only: bool = False,
) -> dict[str, Any]:
    root = repository_root.resolve()
    logs_ci_root = (root / "logs/ci").resolve()
    try:
        logs_ci_root.relative_to(root)
    except ValueError as exc:
        raise fail("path_outside_repository", "repository logs/ci path escapes the repository") from exc
    _ensure_no_reparse_ancestors(output_root, root)
    resolved_output = output_root.resolve()
    try:
        resolved_output.relative_to(logs_ci_root)
    except ValueError as exc:
        raise fail("path_outside_repository", "impact index output must remain under logs/ci") from exc
    output_root = resolved_output
    snapshot = GitTreeSnapshot(root, revision, trusted_ref)
    config_path = resolve_repository_path(root, config_relative)
    aliases_path = resolve_repository_path(root, aliases_relative)
    _validate_identity_worktree_file(root, config_relative, validate_config, config_relative)
    _validate_identity_worktree_file(root, aliases_relative, validate_aliases, aliases_relative)
    config_bytes = _trusted_blob_for_path(snapshot, config_relative)
    aliases_bytes = _trusted_blob_for_path(snapshot, aliases_relative)
    config = _strict_json_object(config_bytes, code="invalid_manifest", label=config_relative)
    aliases = _strict_json_object(aliases_bytes, code="invalid_manifest", label=aliases_relative)
    config = validate_config(config)
    validate_aliases(aliases)
    source_manifest, source_manifest_sha = build_source_manifest(
        snapshot,
        config,
        config_path=config_path.relative_to(root).as_posix(),
        aliases_path=aliases_path.relative_to(root).as_posix(),
    )
    snapshot.verify_worktree(source_manifest)
    identity = {
        "repository_revision": snapshot.revision,
        "source_manifest_sha256": source_manifest_sha,
        "index_schema": INDEX_SCHEMA,
        "analyzer_implementation_revision": implementation_revision,
        "analysis_config_revision": config["analysis_config_revision"],
    }
    index_id = derive_index_id(identity)
    build_time = utc_now()
    generated_at = utc_text(build_time)
    toolchain = {"python": platform.python_version()}
    index_document = {
        "schema_version": INDEX_SCHEMA,
        "index_schema": INDEX_SCHEMA,
        "index_id": index_id,
        "repository_revision": snapshot.revision,
        "analyzer_implementation_revision": implementation_revision,
        "analysis_config_revision": config["analysis_config_revision"],
        "analysis_config_sha256": sha256_bytes(config_bytes),
        "alias_table_revision": aliases["alias_table_revision"],
        "alias_table_sha256": sha256_bytes(aliases_bytes),
        "discovery_policy_sha256": sha256_bytes(jcs_bytes(config)),
        "source_manifest_sha256": source_manifest_sha,
        "source_manifest": source_manifest,
    }
    validate_index_document(index_document)
    index_bytes = artifact_json_bytes(index_document)
    index_sha = sha256_bytes(index_bytes)
    existing = discover_existing(
        output_root,
        index_document,
        expected_trusted_ref=snapshot.trusted_ref,
        expected_toolchain=toolchain,
    )
    if existing is not None:
        snapshot.verify_revision()
        snapshot.verify_worktree(source_manifest)
        return {
            "status": "ok",
            "code": None,
            "reused": True,
            "index_id": index_id,
            "repository_revision": snapshot.revision,
            "source_manifest_sha256": source_manifest_sha,
            "index_sha256": existing["index_sha256"],
            "manifest_sha256": existing["manifest_sha256"],
            "index_path": _relative_to_root(existing["index_path"], root),
            "manifest_path": _relative_to_root(existing["manifest_path"], root),
        }
    if reuse_only:
        raise fail("stale_index", "no exact immutable index is available for reuse")
    date_path = build_time.date().isoformat()
    directory = output_root / date_path / "impact-analysis" / "indexes" / index_id
    lock_path = output_root / ".impact-analysis-locks" / f"{index_id}.lock.json"
    _ensure_no_reparse_ancestors(directory, root)
    _ensure_no_reparse_ancestors(lock_path.parent, root)
    with IndexLock(lock_path, index_id):
        snapshot.verify_revision()
        snapshot.verify_worktree(source_manifest)
        existing = discover_existing(
            output_root,
            index_document,
            expected_trusted_ref=snapshot.trusted_ref,
            expected_toolchain=toolchain,
        )
        if existing is not None:
            snapshot.verify_revision()
            snapshot.verify_worktree(source_manifest)
            return {
                "status": "ok",
                "code": None,
                "reused": True,
                "index_id": index_id,
                "repository_revision": snapshot.revision,
                "source_manifest_sha256": source_manifest_sha,
                "index_sha256": existing["index_sha256"],
                "manifest_sha256": existing["manifest_sha256"],
                "index_path": _relative_to_root(existing["index_path"], root),
                "manifest_path": _relative_to_root(existing["manifest_path"], root),
            }
        if directory.exists():
            if not directory.is_dir():
                raise fail("index_identity_collision", f"target index directory path is not a directory: {directory}")
            if any(directory.iterdir()):
                raise fail("index_identity_collision", f"target index directory already contains data: {directory}")
        directory.mkdir(parents=True, exist_ok=True)
        index_path = directory / "impact-index.v1.json"
        manifest_path = directory / "index-manifest.v1.json"
        manifest_document = {
            "schema_version": INDEX_MANIFEST_SCHEMA,
            "index_schema": INDEX_SCHEMA,
            "index_id": index_id,
            "artifact_path": "impact-index.v1.json",
            "artifact_sha256": index_sha,
            "repository_revision": snapshot.revision,
            "trusted_ref": snapshot.trusted_ref,
            "analyzer_implementation_revision": implementation_revision,
            "analysis_config_revision": config["analysis_config_revision"],
            "analysis_config_sha256": sha256_bytes(config_bytes),
            "alias_table_revision": aliases["alias_table_revision"],
            "alias_table_sha256": sha256_bytes(aliases_bytes),
            "discovery_policy_sha256": sha256_bytes(jcs_bytes(config)),
            "source_manifest_sha256": source_manifest_sha,
            "generated_at": generated_at,
            "toolchain": toolchain,
        }
        manifest_bytes = artifact_json_bytes(manifest_document)
        published_index = False
        try:
            atomic_publish_bytes(index_path, index_bytes, validator=validate_index_bytes)
            published_index = True
            atomic_publish_bytes(
                manifest_path,
                manifest_bytes,
                validator=lambda data: validate_manifest_bytes(
                    data,
                    index_bytes=index_bytes,
                    expected_index=index_document,
                    expected_trusted_ref=snapshot.trusted_ref,
                ),
            )
        except BaseException:
            if published_index and not manifest_path.exists():
                try:
                    if index_path.read_bytes() == index_bytes:
                        index_path.unlink(missing_ok=True)
                        try:
                            if not any(directory.iterdir()):
                                directory.rmdir()
                                parent = directory.parent
                                while parent != output_root and parent.exists() and not any(parent.iterdir()):
                                    parent.rmdir()
                                    parent = parent.parent
                        except OSError:
                            pass
                    else:
                        marker = {
                            "schema_version": "newrouge.impact-index-publication-failure.v1",
                            "code": "index_identity_collision",
                            "reason": "published index was replaced before manifest failure cleanup",
                            "index_id": index_id,
                            "expected_artifact_sha256": index_sha,
                        }
                        marker_path = directory / "publication-failure.v1.json"
                        try:
                            with marker_path.open("xb") as handle:
                                handle.write(artifact_json_bytes(marker))
                                handle.flush()
                                os.fsync(handle.fileno())
                        except OSError:
                            pass
                except OSError:
                    pass
            try:
                if directory.exists() and directory.is_dir() and not any(directory.iterdir()):
                    directory.rmdir()
                    parent = directory.parent
                    while parent != output_root and parent.exists() and parent.is_dir() and not any(parent.iterdir()):
                        parent.rmdir(); parent = parent.parent
            except OSError:
                pass
            raise
        return {
            "status": "ok",
            "code": None,
            "reused": False,
            "index_id": index_id,
            "repository_revision": snapshot.revision,
            "source_manifest_sha256": source_manifest_sha,
            "index_sha256": index_sha,
            "manifest_sha256": sha256_bytes(manifest_bytes),
            "index_path": _relative_to_root(index_path, root),
            "manifest_path": _relative_to_root(manifest_path, root),
        }
