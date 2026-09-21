#!/usr/bin/env python3
"""Chapter 5 independent Extraction B, bidirectional reconciliation, and readiness gate."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
from pathlib import Path
from typing import Any

DEFAULT_SOURCE_MANIFEST = Path("logs/ci/task-generation/source-manifest.v1.json")
DEFAULT_SOURCE_LEDGER = Path("logs/ci/task-generation/source-blocks.v1.json")
DEFAULT_CH3_SEMANTICS = Path("logs/ci/task-generation/semantic-requirements.v1.json")
DEFAULT_EXTRACTION_CANDIDATE = Path("logs/ci/chapter5/extraction-b.candidate.json")
DEFAULT_EXTRACTION_SNAPSHOT = Path("logs/ci/chapter5/extraction-b.snapshot.json")
DEFAULT_RECONCILIATION_DIR = Path("logs/ci/chapter5/reconciliation")
DEFAULT_READINESS_DIR = Path("logs/ci/chapter5/readiness")
DEFAULT_TASK_VIEWS = (
    Path(".taskmaster/tasks/tasks_back.json"),
    Path(".taskmaster/tasks/tasks_gameplay.json"),
)
PARSER_REVISION = "chapter3-source-ledger-v2"
EXTRACTOR_REVISION = "chapter5-independent-extraction-b-v1"
SNAPSHOT_SCHEMA = "newrouge.independent-extraction-b.v1"
RECONCILIATION_SCHEMA = "newrouge.semantic-reconciliation.v1"
READINESS_SCHEMA = "newrouge.chapter5-readiness.v1"
ALLOWED_DISPOSITIONS = {
    "context", "rationale", "duplicate", "superseded", "deferred",
    "out_of_scope", "adr_owned",
}
ALLOWED_MATCH_STATUS = {
    "equivalent", "partial", "missing_in_ch3", "invented_in_ch3",
    "superseded", "conflict_with_adr", "out_of_task_scope",
    "needs_human_decision",
}
ALLOWED_OVERLAP_DECISIONS = {
    "keep_separate", "merge_recommended", "overlap_justified",
}
ALLOWED_DEPENDENCY_RELATIONS = {
    "producer_consumer", "contract", "schema", "state", "asset_scene_availability",
}
ALLOWED_AUTHORITY_STATUS = {"compatible", "conflict", "out_of_scope"}
BLOCKING_FINDINGS = {
    "invented_in_ch3", "conflict_with_adr", "unsupported_task_claim",
    "orphan_acceptance", "partial_acceptance", "untraceable_acceptance",
    "out_of_task_scope", "invalid_dependency",
}
REFS_RE = re.compile(r"\bRefs:\s*([^\n]+)$", re.IGNORECASE)


def _load_json(path: Path, default: Any = None) -> Any:
    if not path.is_file():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: Any) -> None:
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


def _sha_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha_file(path: Path) -> str:
    return _sha_bytes(path.read_bytes())


def _sha_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _canonical_sha(payload: Any) -> str:
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return _sha_text(raw)


def _canonical_task_id(value: Any) -> str:
    if value is None or isinstance(value, bool):
        return ""
    text = str(value).strip()
    if re.fullmatch(r"\d+\.0", text):
        return text[:-2]
    return text


def _source_slice(text: str, block: dict[str, Any]) -> str:
    start = block.get("source_char_start")
    end = block.get("source_char_end_exclusive")
    if isinstance(start, int) and isinstance(end, int) and 0 <= start <= end <= len(text):
        return text[start:end].rstrip()
    line_start = int(block.get("line_start") or 1)
    line_end = int(block.get("line_end") or line_start)
    lines = text.splitlines()
    if line_start < 1 or line_end < line_start or line_end > len(lines):
        raise ValueError(f"invalid source line range for {block.get('block_id')}")
    return "\n".join(lines[line_start - 1:line_end]).rstrip()


def source_scope(
    root: Path,
    manifest: dict[str, Any],
    ledger: dict[str, Any],
) -> tuple[list[dict[str, Any]], dict[str, str], list[str]]:
    errors: list[str] = []
    if manifest.get("schema_version") != "chapter3.source-manifest.v1":
        errors.append("invalid_source_manifest_schema")
    if ledger.get("schema_version") != "newrouge.source-blocks.v1":
        errors.append("invalid_source_ledger_schema")
    if str(manifest.get("source_revision") or "") != str(ledger.get("source_revision") or ""):
        errors.append("source_revision_mismatch")
    if str(manifest.get("manifest_sha256") or "") != str(ledger.get("source_manifest_sha256") or ""):
        errors.append("source_manifest_binding_mismatch")

    manifest_sources = {
        str(row.get("path") or ""): row
        for row in manifest.get("sources", [])
        if isinstance(row, dict) and str(row.get("path") or "").strip()
    }
    texts: dict[str, str] = {}
    scope: list[dict[str, Any]] = []
    for path, row in sorted(manifest_sources.items()):
        source_path = root / path
        if not source_path.is_file():
            errors.append(f"source_missing:{path}")
            continue
        text = source_path.read_text(encoding="utf-8")
        texts[path] = text
        actual = _sha_text(text)
        expected = str(row.get("sha256") or "").removeprefix("sha256:")
        if not expected or actual != expected:
            errors.append(f"source_hash_mismatch:{path}")
        scope.append({
            "path": path,
            "source_type": row.get("source_type"),
            "sha256": "sha256:" + actual,
            "block_count": int(row.get("block_count") or 0),
        })

    blocks = [row for row in ledger.get("blocks", []) if isinstance(row, dict)]
    if int(manifest.get("block_count") or len(blocks)) != len(blocks):
        errors.append("source_block_count_mismatch")
    seen_ids: set[str] = set()
    by_path_count: dict[str, int] = {}
    for block in blocks:
        block_id = str(block.get("block_id") or "")
        path = str(block.get("source_path") or "")
        if not block_id or block_id in seen_ids:
            errors.append(f"invalid_or_duplicate_block_id:{block_id or 'missing'}")
            continue
        seen_ids.add(block_id)
        by_path_count[path] = by_path_count.get(path, 0) + 1
        text = texts.get(path)
        if text is None:
            errors.append(f"block_source_unavailable:{block_id}")
            continue
        try:
            raw = _source_slice(text, block)
        except ValueError:
            errors.append(f"block_source_range_invalid:{block_id}")
            continue
        expected_raw = str(block.get("raw_text") or "").rstrip()
        if raw != expected_raw:
            errors.append(f"block_raw_source_mismatch:{block_id}")
        expected_hash = str(block.get("content_hash") or "").removeprefix("sha256:")
        if not expected_hash or _sha_text(expected_raw) != expected_hash:
            errors.append(f"block_content_hash_mismatch:{block_id}")
        expected_source = str(block.get("source_sha256") or "").removeprefix("sha256:")
        if expected_source and _sha_text(text) != expected_source:
            errors.append(f"block_source_hash_mismatch:{block_id}")

    for row in scope:
        expected = int(row.get("block_count") or 0)
        actual = by_path_count.get(str(row["path"]), 0)
        if expected != actual:
            errors.append(f"source_scope_block_count_mismatch:{row['path']}")
    return scope, texts, sorted(set(errors))


def build_cache_key(
    manifest_path: Path,
    ledger_path: Path,
    manifest: dict[str, Any],
    *,
    parser_revision: str,
    extractor_revision: str,
) -> dict[str, str]:
    return {
        "source_manifest_sha": str(manifest.get("manifest_sha256") or ("sha256:" + _sha_file(manifest_path))),
        "source_block_ledger_sha": "sha256:" + _sha_file(ledger_path),
        "parser_revision": parser_revision,
        "extractor_revision": extractor_revision,
    }


def prepare_extraction_b(
    root: Path,
    *,
    manifest_path: Path,
    ledger_path: Path,
    candidate_path: Path,
    snapshot_path: Path,
    parser_revision: str = PARSER_REVISION,
    extractor_revision: str = EXTRACTOR_REVISION,
) -> dict[str, Any]:
    manifest = _load_json(manifest_path, {})
    ledger = _load_json(ledger_path, {})
    scope, texts, errors = source_scope(root, manifest, ledger)
    cache_key = build_cache_key(
        manifest_path, ledger_path, manifest,
        parser_revision=parser_revision,
        extractor_revision=extractor_revision,
    )
    snapshot_id = "EXB-" + _canonical_sha(cache_key)[:20].upper()
    prior = _load_json(snapshot_path, {})
    if (
        not errors
        and prior.get("schema_version") == SNAPSHOT_SCHEMA
        and prior.get("status") == "complete"
        and prior.get("cache_key") == cache_key
        and prior.get("extraction_b_snapshot_id") == snapshot_id
    ):
        return {
            "status": "cache_hit",
            "extraction_b_snapshot_id": snapshot_id,
            "cache_key": cache_key,
            "snapshot_path": snapshot_path.as_posix(),
            "candidate_path": candidate_path.as_posix(),
            "source_scope_errors": [],
        }

    block_results: list[dict[str, Any]] = []
    for block in ledger.get("blocks", []):
        if not isinstance(block, dict):
            continue
        path = str(block.get("source_path") or "")
        text = texts.get(path, "")
        raw = _source_slice(text, block) if text else str(block.get("raw_text") or "").rstrip()
        block_results.append({
            "block_id": str(block.get("block_id") or ""),
            "source_path": path,
            "heading_path": list(block.get("heading_path") or []),
            "line_start": block.get("line_start"),
            "line_end": block.get("line_end"),
            "block_content_hash": block.get("content_hash"),
            "raw_source": raw,
            "review_status": "review_required",
            "delivery_potential": None,
            "disposition": "",
            "obligations": [],
        })
    candidate = {
        "schema_version": "newrouge.independent-extraction-b.candidate.v1",
        "generated_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "source_revision": ledger.get("source_revision"),
        "extraction_b_snapshot_id": snapshot_id,
        "cache_key": cache_key,
        "source_scope": scope,
        "source_scope_errors": errors,
        "block_results": block_results,
        "instructions": {
            "independence": "Review every raw_source directly. Do not use Chapter 3 task mappings to select or omit blocks.",
            "completion": "Every block must set delivery_potential and either obligations or a valid non-delivery disposition.",
        },
    }
    _write_json(candidate_path, candidate)
    return {
        "status": "blocked" if errors else "review_required",
        "extraction_b_snapshot_id": snapshot_id,
        "cache_key": cache_key,
        "candidate_path": candidate_path.as_posix(),
        "snapshot_path": snapshot_path.as_posix(),
        "source_scope_errors": errors,
    }


def compile_extraction_b(
    root: Path,
    *,
    manifest_path: Path,
    ledger_path: Path,
    candidate_path: Path,
    snapshot_path: Path,
    parser_revision: str = PARSER_REVISION,
    extractor_revision: str = EXTRACTOR_REVISION,
) -> dict[str, Any]:
    manifest = _load_json(manifest_path, {})
    ledger = _load_json(ledger_path, {})
    candidate = _load_json(candidate_path, {})
    scope, _texts, scope_errors = source_scope(root, manifest, ledger)
    cache_key = build_cache_key(
        manifest_path, ledger_path, manifest,
        parser_revision=parser_revision,
        extractor_revision=extractor_revision,
    )
    snapshot_id = "EXB-" + _canonical_sha(cache_key)[:20].upper()
    errors = list(scope_errors)
    if candidate.get("schema_version") != "newrouge.independent-extraction-b.candidate.v1":
        errors.append("invalid_extraction_candidate_schema")
    if candidate.get("cache_key") != cache_key:
        errors.append("extraction_candidate_cache_key_mismatch")
    if candidate.get("extraction_b_snapshot_id") != snapshot_id:
        errors.append("extraction_candidate_snapshot_id_mismatch")

    blocks = {
        str(row.get("block_id") or ""): row
        for row in ledger.get("blocks", [])
        if isinstance(row, dict) and row.get("block_id")
    }
    results = [
        row for row in candidate.get("block_results", [])
        if isinstance(row, dict)
    ]
    ids = [str(row.get("block_id") or "") for row in results]
    if set(ids) != set(blocks) or len(ids) != len(set(ids)):
        errors.append("extraction_candidate_block_coverage_invalid")

    inventory: list[dict[str, Any]] = []
    accounting: list[dict[str, Any]] = []
    obligation_ids: set[str] = set()
    for row in results:
        block_id = str(row.get("block_id") or "")
        block = blocks.get(block_id)
        if block is None:
            continue
        row_errors: list[str] = []
        if str(row.get("block_content_hash") or "") != str(block.get("content_hash") or ""):
            row_errors.append("stale_block_content_hash")
        if row.get("delivery_potential") not in {True, False}:
            row_errors.append("delivery_potential_not_reviewed")
        obligations = row.get("obligations")
        if not isinstance(obligations, list):
            obligations = []
            row_errors.append("invalid_obligations_shape")
        disposition = str(row.get("disposition") or "").strip()
        if row.get("delivery_potential") is True and not obligations:
            row_errors.append("delivery_block_missing_obligation")
        if row.get("delivery_potential") is False and not obligations and disposition not in ALLOWED_DISPOSITIONS:
            row_errors.append("non_delivery_block_missing_disposition")
        emitted: list[str] = []
        for obligation in obligations:
            if not isinstance(obligation, dict):
                row_errors.append("invalid_obligation_shape")
                continue
            statement = str(obligation.get("statement") or "").strip()
            source_ids = [str(value) for value in obligation.get("source_block_ids", [block_id])]
            if not statement:
                row_errors.append("obligation_missing_statement")
                continue
            if not source_ids or any(value not in blocks for value in source_ids):
                row_errors.append("obligation_invalid_source_refs")
                continue
            oid = str(obligation.get("obligation_id") or "").strip()
            if not oid:
                oid = "OB-" + _canonical_sha({
                    "source_block_ids": sorted(set(source_ids)),
                    "statement": " ".join(statement.split()).casefold(),
                })[:16].upper()
            if oid in obligation_ids:
                row_errors.append(f"duplicate_obligation_id:{oid}")
                continue
            obligation_ids.add(oid)
            emitted.append(oid)
            inventory.append({
                "obligation_id": oid,
                "statement": statement,
                "kind": str(obligation.get("kind") or "functional"),
                "priority": str(obligation.get("priority") or "P2").upper(),
                "delivery_relevant": bool(obligation.get("delivery_relevant", True)),
                "source_block_ids": sorted(set(source_ids)),
                "authority_refs": sorted(set(str(x) for x in obligation.get("authority_refs", []) if str(x).strip())),
            })
        if row_errors:
            errors.extend(f"{block_id}:{value}" for value in row_errors)
        accounting.append({
            "block_id": block_id,
            "block_content_hash": block.get("content_hash"),
            "delivery_potential": row.get("delivery_potential"),
            "disposition": disposition,
            "obligation_ids": emitted,
        })

    snapshot = {
        "schema_version": SNAPSHOT_SCHEMA,
        "generated_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "status": "blocked" if errors else "complete",
        "source_revision": ledger.get("source_revision"),
        "extraction_b_snapshot_id": snapshot_id,
        "cache_key": cache_key,
        "source_scope": scope,
        "source_scope_errors": sorted(set(scope_errors)),
        "source_accounting": accounting,
        "semantic_inventory": inventory,
        "errors": sorted(set(errors)),
    }
    _write_json(snapshot_path, snapshot)
    return snapshot


def _semantic_tokens(text: str) -> set[str]:
    normalized = " ".join(str(text or "").casefold().split())
    latin = set(re.findall(r"[a-z0-9_]{2,}", normalized))
    cjk = "".join(re.findall(r"[\u3400-\u9fff]", normalized))
    bigrams = {cjk[i:i + 2] for i in range(max(0, len(cjk) - 1))}
    singles = set(cjk) if len(cjk) <= 3 else set()
    return latin | bigrams | singles


def semantic_similarity(left: str, right: str) -> float:
    a = _semantic_tokens(left)
    b = _semantic_tokens(right)
    if not a or not b:
        return 1.0 if " ".join(left.split()).casefold() == " ".join(right.split()).casefold() else 0.0
    return len(a & b) / len(a | b)


def _load_task_rows(root: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in DEFAULT_TASK_VIEWS:
        payload = _load_json(root / path, [])
        if not isinstance(payload, list):
            continue
        view = path.stem
        for row in payload:
            if not isinstance(row, dict):
                continue
            task_id = _canonical_task_id(row.get("taskmaster_id") if row.get("taskmaster_id") is not None else row.get("id"))
            if not task_id:
                continue
            rows.append({"task_id": task_id, "view": view, "row": row})
    return rows


def _task_bundle(rows: list[dict[str, Any]], task_id: str) -> dict[str, Any]:
    selected = [item for item in rows if item["task_id"] == str(task_id)]
    semantic_refs: set[str] = set()
    capability_refs: set[str] = set()
    dependencies: set[str] = set()
    acceptance: list[str] = []
    overlap: set[str] = set()
    overlays: set[str] = set()
    contracts: set[str] = set()
    for item in selected:
        row = item["row"]
        semantic_refs.update(str(x) for x in row.get("semantic_refs", row.get("requirement_ids", [])) if str(x).strip())
        capability_refs.update(str(x) for x in row.get("capability_refs", []) if str(x).strip())
        dependencies.update(_canonical_task_id(x) for x in row.get("depends_on", []) if _canonical_task_id(x))
        for value in row.get("acceptance", []):
            text = str(value or "").strip()
            if text and text not in acceptance:
                acceptance.append(text)
        overlap.update(str(x) for x in row.get("implementation_overlap_candidates", []) if str(x).strip())
        overlays.update(str(x) for x in row.get("overlay_refs", []) if str(x).strip())
        contracts.update(str(x) for x in row.get("contractRefs", []) if str(x).strip())
    return {
        "task_id": str(task_id),
        "semantic_refs": sorted(semantic_refs),
        "capability_refs": sorted(capability_refs),
        "depends_on": sorted(dependencies),
        "acceptance": acceptance,
        "implementation_overlap_candidates": sorted(overlap),
        "overlay_refs": sorted(overlays),
        "contract_refs": sorted(contracts),
        "views": [item["view"] for item in selected],
    }



def _line_for_token(text: str, token: str) -> int | None:
    for index, line in enumerate(text.splitlines(), 1):
        if token in line:
            return index
    return None


def build_task_authority_scope(root: Path, task: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    """Bind Chapter 5 task reconciliation to real Chapter 4/ADR/Contract authority bytes."""
    errors: list[str] = []
    overlays: list[dict[str, Any]] = []
    contracts: list[dict[str, Any]] = []
    adrs: dict[str, dict[str, Any]] = {}

    for value in task.get("overlay_refs", []):
        rel = str(value or "").replace("\\", "/").strip()
        if not rel:
            continue
        path = root / rel
        if not path.is_file():
            errors.append(f"overlay_missing:{rel}")
            continue
        text = path.read_text(encoding="utf-8")
        overlays.append({
            "ref": rel,
            "sha256": "sha256:" + _sha_text(text),
        })
        for token in sorted(set(re.findall(r"\bADR-\d{3,5}\b", text, re.IGNORECASE))):
            canonical = token.upper()
            matches = sorted((root / "docs/adr").glob(canonical + "*.md"))
            if not matches:
                errors.append(f"adr_missing:{canonical}")
                continue
            adr_path = matches[0]
            adr_text = adr_path.read_text(encoding="utf-8")
            rel_adr = adr_path.relative_to(root).as_posix()
            adrs[canonical] = {
                "ref": canonical,
                "path": rel_adr,
                "sha256": "sha256:" + _sha_text(adr_text),
            }

    contract_files = sorted((root / "Game.Core/Contracts").rglob("*.cs"))
    contract_texts: list[tuple[Path, str]] = []
    for path in contract_files:
        try:
            contract_texts.append((path, path.read_text(encoding="utf-8")))
        except UnicodeDecodeError:
            continue
    for contract_ref in task.get("contract_refs", []):
        token = str(contract_ref or "").strip()
        if not token:
            continue
        found = None
        for path, text in contract_texts:
            if token in text:
                found = (path, text)
                break
        if found is None:
            errors.append(f"contract_missing:{token}")
            continue
        path, text = found
        contracts.append({
            "ref": token,
            "path": path.relative_to(root).as_posix(),
            "line": _line_for_token(text, token),
            "sha256": "sha256:" + _sha_text(text),
        })

    return {
        "overlays": overlays,
        "contracts": contracts,
        "adrs": [adrs[key] for key in sorted(adrs)],
    }, sorted(set(errors))



def augment_authority_scope_from_acceptance_links(
    root: Path,
    authority_scope: dict[str, Any],
    decisions: dict[str, Any],
) -> dict[str, Any]:
    scope = {
        "overlays": list(authority_scope.get("overlays", [])),
        "contracts": list(authority_scope.get("contracts", [])),
        "adrs": list(authority_scope.get("adrs", [])),
    }
    existing = {
        str(item.get("ref") or "")
        for kind in ("contracts", "adrs")
        for item in scope.get(kind, [])
        if isinstance(item, dict)
    }
    refs: set[str] = set()
    for row in decisions.get("acceptance_links", []) if isinstance(decisions.get("acceptance_links"), list) else []:
        if isinstance(row, dict):
            refs.update(str(value).strip().replace("\\", "/") for value in row.get("authority_refs", []) if str(value).strip())

    contract_files = sorted((root / "Game.Core/Contracts").rglob("*.cs"))
    for value in sorted(refs - existing):
        if re.fullmatch(r"ADR-\d{3,5}", value, re.IGNORECASE):
            matches = sorted((root / "docs/adr").glob(value.upper() + "*.md"))
            if matches:
                path = matches[0]
                text = path.read_text(encoding="utf-8")
                scope["adrs"].append({
                    "ref": value.upper(),
                    "path": path.relative_to(root).as_posix(),
                    "sha256": "sha256:" + _sha_text(text),
                })
            continue
        direct = root / value
        if value.startswith("docs/adr/") and direct.is_file():
            text = direct.read_text(encoding="utf-8")
            scope["adrs"].append({
                "ref": value,
                "path": value,
                "sha256": "sha256:" + _sha_text(text),
            })
            continue
        if value.startswith("Game.Core/Contracts/") and direct.is_file():
            text = direct.read_text(encoding="utf-8")
            scope["contracts"].append({
                "ref": value,
                "path": value,
                "line": None,
                "sha256": "sha256:" + _sha_text(text),
            })
            continue
        for path in contract_files:
            try:
                text = path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue
            if value in text:
                scope["contracts"].append({
                    "ref": value,
                    "path": path.relative_to(root).as_posix(),
                    "line": _line_for_token(text, value),
                    "sha256": "sha256:" + _sha_text(text),
                })
                break
    scope["contracts"] = sorted(scope["contracts"], key=lambda row: (str(row.get("ref") or ""), str(row.get("path") or "")))
    scope["adrs"] = sorted(scope["adrs"], key=lambda row: (str(row.get("ref") or ""), str(row.get("path") or "")))
    return scope


def resolve_acceptance_authority_ref(
    root: Path,
    authority: str,
    authority_scope: dict[str, Any],
) -> tuple[str | None, str | None]:
    value = str(authority or "").strip().replace("\\", "/")
    if not value:
        return None, None
    for item in authority_scope.get("contracts", []):
        if value in {str(item.get("ref") or ""), str(item.get("path") or "")}:
            return "contract", str(item.get("ref") or value)
    for item in authority_scope.get("adrs", []):
        if value in {str(item.get("ref") or ""), str(item.get("path") or "")}:
            return "adr", str(item.get("ref") or value)

    direct = root / value
    if direct.is_file() and value.startswith("docs/adr/"):
        return "adr", value
    if direct.is_file() and value.startswith("Game.Core/Contracts/"):
        return "contract", value

    if re.fullmatch(r"ADR-\d{3,5}", value, re.IGNORECASE):
        matches = sorted((root / "docs/adr").glob(value.upper() + "*.md"))
        if matches:
            return "adr", value.upper()
    return None, None


def _all_task_sinks(rows: list[dict[str, Any]]) -> dict[str, set[str]]:
    sinks: dict[str, set[str]] = {}
    for item in rows:
        row = item["row"]
        for rid in row.get("semantic_refs", row.get("requirement_ids", [])):
            sinks.setdefault(str(rid), set()).add(item["task_id"])
    return sinks


def _decision_by_id(decisions: dict[str, Any], key: str, id_field: str) -> dict[str, dict[str, Any]]:
    values = decisions.get(key, [])
    if not isinstance(values, list):
        return {}
    return {
        str(row.get(id_field) or ""): row
        for row in values
        if isinstance(row, dict) and str(row.get(id_field) or "").strip()
    }


def _parse_acceptance_test_refs(text: str) -> list[str]:
    match = REFS_RE.search(str(text or "").strip())
    if not match:
        return []
    return sorted({
        value.strip().replace("\\", "/")
        for value in re.split(r"[,;]", match.group(1))
        if value.strip()
    })



def _task_semantic_surface(task: dict[str, Any]) -> dict[str, Any]:
    return {
        "task_id": str(task.get("task_id") or ""),
        "semantic_refs": list(task.get("semantic_refs") or []),
        "capability_refs": list(task.get("capability_refs") or []),
        "depends_on": list(task.get("depends_on") or []),
        "acceptance": list(task.get("acceptance") or []),
        "implementation_overlap_candidates": list(task.get("implementation_overlap_candidates") or []),
        "overlay_refs": list(task.get("overlay_refs") or []),
        "contract_refs": list(task.get("contract_refs") or []),
    }


def build_chapter5_input_fingerprint(
    root: Path,
    *,
    manifest_path: Path,
    ledger_path: Path,
    snapshot: dict[str, Any],
    semantics_path: Path,
    task: dict[str, Any],
    authority_scope: dict[str, Any],
    authority_reconciliation: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    payload = {
        "source_manifest_sha": "sha256:" + _sha_file(manifest_path) if manifest_path.is_file() else None,
        "source_block_ledger_sha": "sha256:" + _sha_file(ledger_path) if ledger_path.is_file() else None,
        "extraction_b_snapshot_id": snapshot.get("extraction_b_snapshot_id"),
        "extraction_b_cache_key": snapshot.get("cache_key"),
        "semantic_requirements_sha": "sha256:" + _sha_file(semantics_path) if semantics_path.is_file() else None,
        "task_semantic_surface": _task_semantic_surface(task),
        "authority_scope": authority_scope,
        "authority_reconciliation": list(authority_reconciliation or []),
    }
    return {
        "schema_version": "newrouge.chapter5-input-fingerprint.v1",
        "payload": payload,
        "sha256": "sha256:" + _canonical_sha(payload),
    }


def _authority_decisions(
    decisions: dict[str, Any],
    authority_scope: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    raw = decisions.get("authority_decisions", [])
    if not isinstance(raw, list):
        raw = []
    by_ref = {
        str(row.get("authority_ref") or ""): row
        for row in raw
        if isinstance(row, dict) and str(row.get("authority_ref") or "").strip()
    }
    reviews: list[dict[str, Any]] = []
    findings: list[dict[str, Any]] = []
    required = []
    for kind in ("contracts", "adrs"):
        for item in authority_scope.get(kind, []):
            if isinstance(item, dict) and str(item.get("ref") or "").strip():
                required.append((kind[:-1] if kind.endswith("s") else kind, item))
    for authority_type, item in required:
        ref = str(item.get("ref") or "")
        decision = by_ref.get(ref, {})
        status = str(decision.get("status") or "").strip()
        rationale = str(decision.get("rationale") or "").strip()
        if status not in ALLOWED_AUTHORITY_STATUS or not rationale:
            status = "needs_human_decision"
        review = {
            "authority_type": authority_type,
            "authority_ref": ref,
            "authority_sha256": item.get("sha256"),
            "status": status,
            "rationale": rationale,
        }
        reviews.append(review)
        if status == "conflict":
            findings.append({
                "finding_type": "authority",
                "status": "conflict_with_adr",
                "authority_type": authority_type,
                "authority_ref": ref,
                "authority_sha256": item.get("sha256"),
                "reason": rationale,
                "action": "route_to_chapter5_or_source_owner",
            })
        elif status == "needs_human_decision":
            findings.append({
                "finding_type": "authority",
                "status": "needs_human_decision",
                "authority_type": authority_type,
                "authority_ref": ref,
                "authority_sha256": item.get("sha256"),
                "reason": "authority compatibility has not been explicitly reviewed",
                "priority": "P1",
                "action": "review_authority_compatibility",
            })
    return reviews, findings


def reconcile(
    root: Path,
    *,
    task_id: str,
    snapshot_path: Path,
    semantics_path: Path,
    decisions_path: Path | None,
    out_path: Path,
    readiness_path: Path,
    manifest_path: Path | None = None,
    ledger_path: Path | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    snapshot = _load_json(snapshot_path, {})
    semantics = _load_json(semantics_path, {})
    decisions = _load_json(decisions_path, {}) if decisions_path and decisions_path.is_file() else {}
    source_errors = list(snapshot.get("source_scope_errors", []))
    if snapshot.get("schema_version") != SNAPSHOT_SCHEMA or snapshot.get("status") != "complete":
        source_errors.append("extraction_b_snapshot_not_complete")

    requirements = {
        str(row.get("requirement_id") or ""): row
        for row in semantics.get("requirements", [])
        if isinstance(row, dict) and str(row.get("requirement_id") or "").strip()
    }
    by_block: dict[str, list[str]] = {}
    for rid, row in requirements.items():
        for block_id in row.get("source_block_ids", []):
            by_block.setdefault(str(block_id), []).append(rid)

    task_rows = _load_task_rows(root)
    task = _task_bundle(task_rows, task_id)
    authority_scope, authority_errors = build_task_authority_scope(root, task)
    authority_scope = augment_authority_scope_from_acceptance_links(root, authority_scope, decisions)
    authority_reconciliation, authority_findings = _authority_decisions(decisions, authority_scope)
    task_sinks = _all_task_sinks(task_rows)
    match_decisions = _decision_by_id(decisions, "match_decisions", "obligation_id")

    findings: list[dict[str, Any]] = list(authority_findings)
    matched_requirements: set[str] = set()
    obligation_to_requirements: dict[str, list[str]] = {}
    for obligation in snapshot.get("semantic_inventory", []):
        if not isinstance(obligation, dict) or obligation.get("delivery_relevant") is not True:
            continue
        oid = str(obligation.get("obligation_id") or "")
        source_ids = [str(x) for x in obligation.get("source_block_ids", [])]
        candidates = sorted({
            rid for block_id in source_ids for rid in by_block.get(block_id, [])
            if str(requirements.get(rid, {}).get("status", "active")).casefold() == "active"
        })
        override = match_decisions.get(oid, {})
        explicit_ids = [
            str(x) for x in override.get("chapter3_requirement_ids", [])
            if str(x) in requirements
        ]
        if explicit_ids:
            candidates = sorted(set(explicit_ids))
        if not candidates:
            findings.append({
                "finding_type": "source_semantic",
                "status": "missing_in_ch3",
                "global_gate": "orphan_delivery_semantic",
                "obligation_id": oid,
                "source_block_ids": source_ids,
                "chapter5_obligation": obligation.get("statement"),
                "priority": obligation.get("priority", "P2"),
                "action": "route_to_source_owner",
            })
            obligation_to_requirements[oid] = []
            continue

        scored = sorted(
            (
                semantic_similarity(str(obligation.get("statement") or ""), str(requirements[rid].get("statement") or "")),
                rid,
            )
            for rid in candidates
        )
        score, best_rid = scored[-1]
        status = str(override.get("status") or "").strip()
        rationale = str(override.get("rationale") or "").strip()
        if status not in ALLOWED_MATCH_STATUS or (status != "needs_human_decision" and not rationale):
            # Lexical similarity is diagnostic only. A semantic verdict must be explicit
            # and carry review rationale; otherwise fail closed for independent review.
            status = "needs_human_decision"
        chosen = sorted(set(explicit_ids or [best_rid]))
        matched_requirements.update(chosen)
        obligation_to_requirements[oid] = chosen
        findings.append({
            "finding_type": "source_semantic",
            "status": status,
            "obligation_id": oid,
            "source_block_ids": source_ids,
            "chapter3_requirement_ids": chosen,
            "chapter5_obligation": obligation.get("statement"),
            "similarity": round(score, 4),
            "priority": obligation.get("priority", "P2"),
            "action": str(override.get("action") or ("keep" if status == "equivalent" else "review")),
            "rationale": rationale,
        })

    for rid, requirement in sorted(requirements.items()):
        if str(requirement.get("status", "active")).casefold() != "active":
            continue
        if requirement.get("delivery_relevant") is not True:
            continue
        if rid not in matched_requirements:
            findings.append({
                "finding_type": "source_semantic",
                "status": "invented_in_ch3",
                "chapter3_requirement_ids": [rid],
                "source_block_ids": list(requirement.get("source_block_ids", [])),
                "chapter5_obligation": None,
                "priority": requirement.get("priority", "P2"),
                "action": "review_upstream_claim",
            })
            continue
        non_task_sinks = [
            sink for sink in requirement.get("non_task_sinks", [])
            if isinstance(sink, dict) and str(sink.get("id") or "").strip()
        ]
        if not task_sinks.get(rid) and not non_task_sinks:
            findings.append({
                "finding_type": "semantic_sink",
                "status": "orphan_delivery_semantic",
                "chapter3_requirement_ids": [rid],
                "priority": requirement.get("priority", "P2"),
                "action": "assign_explainable_sink",
            })

    for rid in task["semantic_refs"]:
        if rid not in requirements or str(requirements[rid].get("status", "active")).casefold() != "active":
            findings.append({
                "finding_type": "task_claim",
                "status": "unsupported_task_claim",
                "task_id": task_id,
                "chapter3_requirement_ids": [rid],
                "action": "remove_or_reconcile_task_claim",
            })

    acceptance_links = decisions.get("acceptance_links", [])
    if not isinstance(acceptance_links, list):
        acceptance_links = []
    links_by_index = {
        int(row.get("acceptance_index")): row
        for row in acceptance_links
        if isinstance(row, dict) and str(row.get("acceptance_index") or "").isdigit()
    }
    acceptance_coverage: dict[str, list[int]] = {rid: [] for rid in task["semantic_refs"]}
    topology_edges: list[dict[str, Any]] = []
    for rid in task["semantic_refs"]:
        if rid in requirements:
            topology_edges.append({
                "source_type": "requirement", "source_id": rid,
                "target_type": "task", "target_id": str(task_id),
                "relation": "implemented_by",
                "contribution": "chapter5_stabilized",
            })
    acceptance_findings: list[dict[str, Any]] = []
    for index, text in enumerate(task["acceptance"], 1):
        link = links_by_index.get(index)
        if not isinstance(link, dict):
            acceptance_findings.append({
                "finding_type": "acceptance",
                "status": "orphan_acceptance",
                "task_id": task_id,
                "acceptance_index": index,
                "acceptance": text,
            })
            continue
        req_ids = sorted(set(str(x) for x in link.get("requirement_ids", []) if str(x).strip()))
        authority_refs = sorted(set(str(x) for x in link.get("authority_refs", []) if str(x).strip()))
        test_refs = sorted(set(
            [str(x) for x in link.get("test_refs", []) if str(x).strip()]
            + _parse_acceptance_test_refs(text)
        ))
        if not req_ids and not authority_refs:
            acceptance_findings.append({
                "finding_type": "acceptance",
                "status": "orphan_acceptance",
                "task_id": task_id,
                "acceptance_index": index,
                "acceptance": text,
            })
        if not test_refs:
            acceptance_findings.append({
                "finding_type": "acceptance",
                "status": "untraceable_acceptance",
                "task_id": task_id,
                "acceptance_index": index,
                "acceptance": text,
            })
        out_of_scope = [rid for rid in req_ids if rid not in task["semantic_refs"]]
        if out_of_scope:
            acceptance_findings.append({
                "finding_type": "acceptance",
                "status": "out_of_task_scope",
                "task_id": task_id,
                "acceptance_index": index,
                "chapter3_requirement_ids": out_of_scope,
                "acceptance": text,
            })
        acc_id = "AC-T" + str(task_id) + "-" + _sha_text(str(task_id) + "\0" + text)[:12]
        topology_edges.append({
            "source_type": "task", "source_id": str(task_id),
            "target_type": "acceptance", "target_id": acc_id,
            "relation": "verified_by",
        })
        for rid in req_ids:
            if rid in acceptance_coverage:
                acceptance_coverage[rid].append(index)
            topology_edges.append({
                "source_type": "requirement", "source_id": rid,
                "target_type": "acceptance", "target_id": acc_id,
                "relation": "accepted_by",
            })
        for authority in authority_refs:
            authority_type, authority_id = resolve_acceptance_authority_ref(
                root, authority, authority_scope
            )
            if authority_type is None or authority_id is None:
                acceptance_findings.append({
                    "finding_type": "acceptance",
                    "status": "untraceable_acceptance",
                    "task_id": task_id,
                    "acceptance_index": index,
                    "acceptance": text,
                    "authority_ref": authority,
                    "reason": "authority_ref_missing_or_unbound",
                })
                continue
            topology_edges.append({
                "source_type": "acceptance", "source_id": acc_id,
                "target_type": authority_type, "target_id": authority_id,
                "relation": "authorized_by",
            })

    for rid, covered in acceptance_coverage.items():
        if not covered:
            acceptance_findings.append({
                "finding_type": "acceptance",
                "status": "partial_acceptance",
                "task_id": task_id,
                "chapter3_requirement_ids": [rid],
                "action": "add_verifiable_acceptance",
            })

    findings.extend(acceptance_findings)

    dependency_decisions = decisions.get("dependency_decisions", [])
    if not isinstance(dependency_decisions, list):
        dependency_decisions = []
    dep_by_id = {
        _canonical_task_id(row.get("dependency_id")): row
        for row in dependency_decisions
        if isinstance(row, dict) and _canonical_task_id(row.get("dependency_id"))
    }
    dependency_corrections: list[dict[str, Any]] = []
    for dep in task["depends_on"]:
        decision = dep_by_id.get(dep)
        if not isinstance(decision, dict):
            dependency_corrections.append({
                "dependency_id": dep,
                "action": "needs_human_decision",
                "reason": "existing dependency lacks Chapter 5 semantic evidence",
                "evidence": [],
            })
            continue
        action = str(decision.get("action") or "").strip()
        reason = str(decision.get("dependency_reason") or decision.get("reason") or "").strip()
        evidence = [str(x) for x in decision.get("dependency_evidence", decision.get("evidence", [])) if str(x).strip()]
        relation = str(decision.get("relation") or "").strip()
        valid = action in {"keep", "remove"} and bool(reason)
        if action == "keep":
            valid = valid and relation in ALLOWED_DEPENDENCY_RELATIONS and bool(evidence)
        dependency_corrections.append({
            "dependency_id": dep,
            "action": action if valid else "needs_human_decision",
            "relation": relation,
            "dependency_reason": reason,
            "dependency_evidence": evidence,
        })
    for decision in dependency_decisions:
        if not isinstance(decision, dict) or str(decision.get("action") or "") != "add":
            continue
        dep = _canonical_task_id(decision.get("dependency_id"))
        relation = str(decision.get("relation") or "").strip()
        reason = str(decision.get("dependency_reason") or decision.get("reason") or "").strip()
        evidence = [str(x) for x in decision.get("dependency_evidence", decision.get("evidence", [])) if str(x).strip()]
        dependency_corrections.append({
            "dependency_id": dep,
            "action": "add" if dep and relation in ALLOWED_DEPENDENCY_RELATIONS and reason and evidence else "needs_human_decision",
            "relation": relation,
            "dependency_reason": reason,
            "dependency_evidence": evidence,
        })

    final_dependencies = set(task["depends_on"])
    for row in dependency_corrections:
        dep = _canonical_task_id(row.get("dependency_id"))
        if not dep:
            continue
        if row.get("action") == "remove":
            final_dependencies.discard(dep)
        elif row.get("action") in {"keep", "add"}:
            final_dependencies.add(dep)

    numeric_task = int(task_id) if str(task_id).isdigit() else None
    for dep in sorted(final_dependencies):
        if numeric_task is not None and dep.isdigit() and int(dep) > numeric_task:
            findings.append({
                "finding_type": "dependency",
                "status": "invalid_dependency",
                "dependency_id": dep,
                "reason": "forward dependency is not allowed after Chapter 5 stabilization",
            })

    graph: dict[str, set[str]] = {}
    for item in task_rows:
        row = item["row"]
        graph.setdefault(item["task_id"], set()).update(
            _canonical_task_id(x) for x in row.get("depends_on", [])
            if _canonical_task_id(x)
        )
    graph[str(task_id)] = set(final_dependencies)

    def reaches(start: str, target: str, visiting: set[str]) -> bool:
        if start == target:
            return True
        if start in visiting:
            return False
        visiting.add(start)
        return any(reaches(dep, target, visiting) for dep in graph.get(start, set()))

    if any(reaches(dep, str(task_id), set()) for dep in final_dependencies):
        findings.append({
            "finding_type": "dependency",
            "status": "invalid_dependency",
            "reason": "dependency cycle detected after Chapter 5 stabilization",
        })

    overlap_decisions = decisions.get("overlap_decisions", [])
    if not isinstance(overlap_decisions, list):
        overlap_decisions = []
    overlap_by_task = {
        _canonical_task_id(row.get("other_task_id")): row
        for row in overlap_decisions
        if isinstance(row, dict) and _canonical_task_id(row.get("other_task_id"))
    }
    overlap_reviews: list[dict[str, Any]] = []
    for other in task["implementation_overlap_candidates"]:
        decision = overlap_by_task.get(_canonical_task_id(other), {})
        status = str(decision.get("status") or "").strip()
        rationale = str(decision.get("rationale") or "").strip()
        if status not in ALLOWED_OVERLAP_DECISIONS or not rationale:
            status = "needs_human_decision"
        overlap_reviews.append({
            "other_task_id": _canonical_task_id(other),
            "status": status,
            "rationale": rationale,
        })

    for overlay in task["overlay_refs"]:
        for rid in task["semantic_refs"]:
            topology_edges.append({
                "source_type": "requirement", "source_id": rid,
                "target_type": "overlay", "target_id": overlay,
                "relation": "constrained_by",
            })
    for contract in task["contract_refs"]:
        for rid in task["semantic_refs"]:
            topology_edges.append({
                "source_type": "requirement", "source_id": rid,
                "target_type": "contract", "target_id": contract,
                "relation": "constrained_by",
            })

    all_findings = findings
    blocking: list[dict[str, Any]] = []
    concerns: list[dict[str, Any]] = []
    for finding in all_findings:
        status = str(finding.get("status") or "")
        priority = str(finding.get("priority") or "P2").upper()
        if status in BLOCKING_FINDINGS:
            blocking.append(finding)
        elif status in {"missing_in_ch3", "orphan_delivery_semantic"}:
            (blocking if priority in {"P0", "P1"} else concerns).append(finding)
        elif status == "needs_human_decision":
            # An unresolved semantic/authority verdict is never a closable concern.
            blocking.append(finding)
        elif status == "partial":
            if priority in {"P0", "P1"}:
                blocking.append(finding)
            else:
                concerns.append(finding)
    for row in dependency_corrections:
        if row.get("action") == "needs_human_decision":
            blocking.append({"finding_type": "dependency", "status": "dependency_unresolved", **row})
    for row in overlap_reviews:
        if row.get("status") == "needs_human_decision":
            concerns.append({"finding_type": "overlap", **row})
    if source_errors:
        blocking.extend({"finding_type": "source_scope", "status": value} for value in source_errors)
    if authority_errors:
        blocking.extend(
            {"finding_type": "authority_scope", "status": value}
            for value in authority_errors
        )

    allow_concerns = bool(decisions.get("allow_concerns", False))
    readiness = "BLOCKED" if blocking else ("CONCERNS" if concerns else "READY")
    closure_allowed = readiness == "READY" or (readiness == "CONCERNS" and allow_concerns)

    input_fingerprint = build_chapter5_input_fingerprint(
        root,
        manifest_path=manifest_path or (root / DEFAULT_SOURCE_MANIFEST),
        ledger_path=ledger_path or (root / DEFAULT_SOURCE_LEDGER),
        snapshot=snapshot,
        semantics_path=semantics_path,
        task=task,
        authority_scope=authority_scope,
        authority_reconciliation=authority_reconciliation,
    )

    reconciliation = {
        "schema_version": RECONCILIATION_SCHEMA,
        "generated_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "task_id": str(task_id),
        "source_revision": snapshot.get("source_revision"),
        "extraction_b_snapshot_id": snapshot.get("extraction_b_snapshot_id"),
        "cache_key": snapshot.get("cache_key"),
        "chapter3_topology_sha256": "sha256:" + _sha_file(semantics_path) if semantics_path.is_file() else None,
        "global_audit_completed": snapshot.get("status") == "complete",
        "source_scope": snapshot.get("source_scope", []),
        "authority_scope": authority_scope,
        "authority_scope_errors": authority_errors,
        "authority_reconciliation": authority_reconciliation,
        "input_fingerprint": input_fingerprint,
        "findings": all_findings,
        "dependency_corrections": dependency_corrections,
        "final_dependencies": sorted(final_dependencies),
        "overlap_reviews": overlap_reviews,
        "acceptance_coverage": acceptance_coverage,
        "topology_edges": topology_edges,
        "summary": {
            "missing": sum(1 for row in all_findings if row.get("status") == "missing_in_ch3"),
            "partial": sum(1 for row in all_findings if row.get("status") in {"partial", "partial_acceptance"}),
            "invented": sum(1 for row in all_findings if row.get("status") == "invented_in_ch3"),
            "conflicts": sum(1 for row in all_findings if row.get("status") == "conflict_with_adr"),
            "orphan_delivery_semantic": sum(1 for row in all_findings if row.get("status") == "orphan_delivery_semantic" or row.get("global_gate") == "orphan_delivery_semantic"),
            "orphan_acceptance": sum(1 for row in all_findings if row.get("status") == "orphan_acceptance"),
            "blocking_count": len(blocking),
            "concern_count": len(concerns),
        },
    }
    readiness_doc = {
        "schema_version": READINESS_SCHEMA,
        "generated_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "task_id": str(task_id),
        "source_revision": snapshot.get("source_revision"),
        "extraction_b_snapshot_id": snapshot.get("extraction_b_snapshot_id"),
        "cache_key": snapshot.get("cache_key"),
        "reconciliation_sha256": "sha256:" + _canonical_sha(reconciliation),
        "input_fingerprint": input_fingerprint,
        "readiness": readiness,
        "closure_allowed": closure_allowed,
        "allow_concerns": allow_concerns,
        "blocking_findings": blocking,
        "concerns": concerns,
    }
    _write_json(out_path, reconciliation)
    _write_json(readiness_path, readiness_doc)
    _write_json(root / DEFAULT_RECONCILIATION_DIR / "latest.json", reconciliation)
    _write_json(root / DEFAULT_READINESS_DIR / "latest.json", readiness_doc)
    return reconciliation, readiness_doc


def apply_task_corrections(
    root: Path,
    task_id: str,
    reconciliation: dict[str, Any],
    readiness: dict[str, Any],
    decisions: dict[str, Any],
) -> list[str]:
    if readiness.get("closure_allowed") is not True:
        raise ValueError("cannot apply Chapter 5 task corrections while readiness is blocked")
    changed: list[str] = []
    final_dependencies = [
        int(value) if str(value).isdigit() else str(value)
        for value in reconciliation.get("final_dependencies", [])
    ]
    for view_path in DEFAULT_TASK_VIEWS:
        path = root / view_path
        payload = _load_json(path, [])
        if not isinstance(payload, list):
            continue
        dirty = False
        for row in payload:
            if not isinstance(row, dict):
                continue
            row_id = _canonical_task_id(
                row.get("taskmaster_id") if row.get("taskmaster_id") is not None else row.get("id")
            )
            if row_id != str(task_id):
                continue
            row["depends_on"] = final_dependencies
            row["dependency_status"] = "chapter5_stabilized"
            row["dependency_decisions"] = reconciliation.get("dependency_corrections", [])
            row["overlap_reviews"] = reconciliation.get("overlap_reviews", [])
            row["acceptance_semantic_links"] = decisions.get("acceptance_links", [])
            row["chapter5_readiness"] = readiness.get("readiness")
            dirty = True
        if dirty:
            _write_json(path, payload)
            changed.append(view_path.as_posix())
    return changed


def readiness_path_for_task(root: Path, task_id: str) -> Path:
    return root / DEFAULT_READINESS_DIR / f"task-{_canonical_task_id(task_id)}.json"


def reconciliation_path_for_task(root: Path, task_id: str) -> Path:
    return root / DEFAULT_RECONCILIATION_DIR / f"task-{_canonical_task_id(task_id)}.json"


def validate_chapter5_evidence_freshness(
    root: Path,
    *,
    task_id: str,
    reconciliation: dict[str, Any],
    readiness: dict[str, Any],
    manifest_path: Path | None = None,
    ledger_path: Path | None = None,
    snapshot_path: Path | None = None,
    semantics_path: Path | None = None,
) -> tuple[bool, str]:
    manifest_path = manifest_path or (root / DEFAULT_SOURCE_MANIFEST)
    ledger_path = ledger_path or (root / DEFAULT_SOURCE_LEDGER)
    snapshot_path = snapshot_path or (root / DEFAULT_EXTRACTION_SNAPSHOT)
    semantics_path = semantics_path or (root / DEFAULT_CH3_SEMANTICS)
    if not manifest_path.is_file() or not ledger_path.is_file() or not snapshot_path.is_file() or not semantics_path.is_file():
        return False, "chapter5_current_source_evidence_missing"
    manifest = _load_json(manifest_path, {})
    ledger = _load_json(ledger_path, {})
    snapshot = _load_json(snapshot_path, {})
    _scope, _texts, source_errors = source_scope(root, manifest, ledger)
    if source_errors:
        return False, "chapter5_current_source_scope_invalid"
    current_cache_key = build_cache_key(
        manifest_path,
        ledger_path,
        manifest,
        parser_revision=PARSER_REVISION,
        extractor_revision=EXTRACTOR_REVISION,
    )
    current_snapshot_id = "EXB-" + _canonical_sha(current_cache_key)[:20].upper()
    if snapshot.get("schema_version") != SNAPSHOT_SCHEMA or snapshot.get("status") != "complete":
        return False, "chapter5_current_extraction_b_invalid"
    if snapshot.get("cache_key") != current_cache_key or snapshot.get("extraction_b_snapshot_id") != current_snapshot_id:
        return False, "chapter5_current_extraction_b_stale"
    if readiness.get("cache_key") != current_cache_key or reconciliation.get("cache_key") != current_cache_key:
        return False, "chapter5_readiness_source_identity_stale"
    if str(reconciliation.get("source_revision") or "") != str(ledger.get("source_revision") or ""):
        return False, "chapter5_readiness_source_revision_stale"

    task_rows = _load_task_rows(root)
    task = _task_bundle(task_rows, _canonical_task_id(task_id))
    authority_scope, authority_errors = build_task_authority_scope(root, task)
    stored_scope = reconciliation.get("authority_scope", {})
    stored_refs = []
    if isinstance(stored_scope, dict):
        for kind in ("contracts", "adrs"):
            for item in stored_scope.get(kind, []):
                if isinstance(item, dict) and str(item.get("ref") or "").strip():
                    stored_refs.append(str(item.get("ref") or "").strip())
    if stored_refs:
        authority_scope = augment_authority_scope_from_acceptance_links(
            root,
            authority_scope,
            {"acceptance_links": [{"authority_refs": sorted(set(stored_refs))}]},
        )
    if authority_errors:
        return False, "chapter5_current_authority_scope_invalid"
    authority_reconciliation = reconciliation.get("authority_reconciliation", [])
    current_fingerprint = build_chapter5_input_fingerprint(
        root,
        manifest_path=manifest_path,
        ledger_path=ledger_path,
        snapshot=snapshot,
        semantics_path=semantics_path,
        task=task,
        authority_scope=authority_scope,
        authority_reconciliation=authority_reconciliation if isinstance(authority_reconciliation, list) else [],
    )
    if reconciliation.get("input_fingerprint") != current_fingerprint:
        return False, "chapter5_reconciliation_input_fingerprint_stale"
    if readiness.get("input_fingerprint") != current_fingerprint:
        return False, "chapter5_readiness_input_fingerprint_stale"
    return True, "ready"


def load_task_readiness(root: Path, task_id: str) -> tuple[bool, dict[str, Any], str]:
    path = readiness_path_for_task(root, task_id)
    payload = _load_json(path, {})
    if not path.is_file():
        return False, {}, "chapter5_readiness_missing"
    if payload.get("schema_version") != READINESS_SCHEMA:
        return False, payload, "chapter5_readiness_schema_invalid"
    if str(payload.get("task_id") or "") != _canonical_task_id(task_id):
        return False, payload, "chapter5_readiness_task_mismatch"
    if payload.get("readiness") == "BLOCKED":
        return False, payload, "chapter5_readiness_blocked"
    if payload.get("readiness") not in {"READY", "CONCERNS"}:
        return False, payload, "chapter5_readiness_invalid"
    if payload.get("closure_allowed") is not True:
        return False, payload, "chapter5_concerns_not_allowed"

    reconciliation_path = reconciliation_path_for_task(root, task_id)
    reconciliation = _load_json(reconciliation_path, {})
    if reconciliation.get("schema_version") != RECONCILIATION_SCHEMA:
        return False, payload, "chapter5_reconciliation_missing_or_invalid"
    expected = "sha256:" + _canonical_sha(reconciliation)
    if str(payload.get("reconciliation_sha256") or "") != expected:
        return False, payload, "chapter5_readiness_reconciliation_stale"
    if payload.get("extraction_b_snapshot_id") != reconciliation.get("extraction_b_snapshot_id"):
        return False, payload, "chapter5_readiness_snapshot_mismatch"

    freshness_ok, freshness_reason = validate_chapter5_evidence_freshness(
        root,
        task_id=_canonical_task_id(task_id),
        reconciliation=reconciliation,
        readiness=payload,
    )
    if not freshness_ok:
        return False, payload, freshness_reason
    return True, payload, "ready"


def _paths(root: Path, args: argparse.Namespace) -> tuple[Path, Path, Path, Path, Path]:
    manifest = root / str(args.source_manifest)
    ledger = root / str(args.source_ledger)
    candidate = root / str(args.candidate)
    snapshot = root / str(args.snapshot)
    semantics = root / str(getattr(args, "semantics", DEFAULT_CH3_SEMANTICS.as_posix()))
    return manifest, ledger, candidate, snapshot, semantics


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", default=".")
    sub = parser.add_subparsers(dest="command", required=True)

    def add_source_args(p: argparse.ArgumentParser) -> None:
        p.add_argument("--source-manifest", default=DEFAULT_SOURCE_MANIFEST.as_posix())
        p.add_argument("--source-ledger", default=DEFAULT_SOURCE_LEDGER.as_posix())
        p.add_argument("--candidate", default=DEFAULT_EXTRACTION_CANDIDATE.as_posix())
        p.add_argument("--snapshot", default=DEFAULT_EXTRACTION_SNAPSHOT.as_posix())
        p.add_argument("--parser-revision", default=PARSER_REVISION)
        p.add_argument("--extractor-revision", default=EXTRACTOR_REVISION)

    prepare = sub.add_parser("prepare", help="prepare independent Extraction B from the complete authoritative source scope")
    add_source_args(prepare)

    compile_cmd = sub.add_parser("compile", help="validate a reviewed Extraction B candidate and write the revision-bound snapshot")
    add_source_args(compile_cmd)

    reconcile_cmd = sub.add_parser("reconcile", help="run global orphan audit and task-scoped bidirectional reconciliation")
    add_source_args(reconcile_cmd)
    reconcile_cmd.add_argument("--semantics", default=DEFAULT_CH3_SEMANTICS.as_posix())
    reconcile_cmd.add_argument("--task-id", required=True)
    reconcile_cmd.add_argument("--decisions", default="")
    reconcile_cmd.add_argument("--out", default="")
    reconcile_cmd.add_argument("--readiness-out", default="")
    reconcile_cmd.add_argument("--apply-task-corrections", action="store_true")

    check_cmd = sub.add_parser("check-readiness", help="fail closed unless Chapter 5 allows the task to enter Chapter 6")
    check_cmd.add_argument("--task-id", required=True)

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    root = Path(args.repo_root).resolve()
    if args.command in {"prepare", "compile", "reconcile"}:
        manifest, ledger, candidate, snapshot, semantics = _paths(root, args)
    if args.command == "prepare":
        result = prepare_extraction_b(
            root,
            manifest_path=manifest,
            ledger_path=ledger,
            candidate_path=candidate,
            snapshot_path=snapshot,
            parser_revision=args.parser_revision,
            extractor_revision=args.extractor_revision,
        )
        print(json.dumps(result, ensure_ascii=False))
        return 0 if result["status"] in {"cache_hit", "review_required"} else 2
    if args.command == "compile":
        result = compile_extraction_b(
            root,
            manifest_path=manifest,
            ledger_path=ledger,
            candidate_path=candidate,
            snapshot_path=snapshot,
            parser_revision=args.parser_revision,
            extractor_revision=args.extractor_revision,
        )
        print(json.dumps(result, ensure_ascii=False))
        return 0 if result.get("status") == "complete" else 2
    if args.command == "reconcile":
        task_id = _canonical_task_id(args.task_id)
        out = root / (args.out or (DEFAULT_RECONCILIATION_DIR / f"task-{task_id}.json").as_posix())
        readiness_out = root / (args.readiness_out or (DEFAULT_READINESS_DIR / f"task-{task_id}.json").as_posix())
        decisions = root / args.decisions if args.decisions else None
        reconciliation, readiness = reconcile(
            root,
            task_id=task_id,
            snapshot_path=snapshot,
            semantics_path=semantics,
            decisions_path=decisions,
            out_path=out,
            readiness_path=readiness_out,
            manifest_path=manifest,
            ledger_path=ledger,
        )
        changed_task_views: list[str] = []
        if args.apply_task_corrections:
            decisions_payload = _load_json(decisions, {}) if decisions and decisions.is_file() else {}
            changed_task_views = apply_task_corrections(
                root, task_id, reconciliation, readiness, decisions_payload
            )
            if changed_task_views:
                # Task corrections change the guarded input surface. Reconcile again so
                # readiness/fingerprint attest the post-correction Task state.
                reconciliation, readiness = reconcile(
                    root,
                    task_id=task_id,
                    snapshot_path=snapshot,
                    semantics_path=semantics,
                    decisions_path=decisions,
                    out_path=out,
                    readiness_path=readiness_out,
                    manifest_path=manifest,
                    ledger_path=ledger,
                )
        print(json.dumps({
            "status": readiness["readiness"],
            "closure_allowed": readiness["closure_allowed"],
            "reconciliation": out.relative_to(root).as_posix(),
            "readiness": readiness_out.relative_to(root).as_posix(),
            "summary": reconciliation["summary"],
            "changed_task_views": changed_task_views,
        }, ensure_ascii=False))
        return 0 if readiness["closure_allowed"] else 3
    ok, payload, reason = load_task_readiness(root, args.task_id)
    print(json.dumps({
        "task_id": _canonical_task_id(args.task_id),
        "status": "ready" if ok else "blocked",
        "reason": reason,
        "readiness": payload.get("readiness"),
        "closure_allowed": payload.get("closure_allowed", False),
    }, ensure_ascii=False))
    return 0 if ok else 3


if __name__ == "__main__":
    raise SystemExit(main())
