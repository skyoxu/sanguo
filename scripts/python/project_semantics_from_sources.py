#!/usr/bin/env python3
"""Prepare and compile Chapter 3 semantic projection candidates.

The script does not bind an LLM provider. An approved Chapter 3 producer reads
the prepared batches and edits the candidate contract. Compilation is fully
deterministic and fail-closed.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
from pathlib import Path
from typing import Any

ALLOWED_DISPOSITIONS = {
    "atomized", "context", "rationale", "duplicate", "superseded", "deferred",
    "out_of_scope", "adr_owned", "unresolved",
}
ALLOWED_REQUIREMENT_STATUSES = {"active", "superseded", "removed", "unresolved"}
KIND_MAP = {
    "FR": "functional",
    "NFR": "non_functional",
    "INV": "invariant",
    "FAIL": "failure",
    "SCOPE": "scope",
    "METRIC": "metric",
    "CONSTRAINT": "constraint",
    "RISK": "risk",
    "CONTEXT": "context",
    "RATIONALE": "rationale",
    "functional": "functional",
    "non_functional": "non_functional",
    "invariant": "invariant",
    "failure": "failure",
    "scope": "scope",
    "metric": "metric",
    "constraint": "constraint",
    "risk": "risk",
    "context": "context",
    "rationale": "rationale",
}
DELIVERY_DEFAULT = {
    "functional": True,
    "non_functional": True,
    "invariant": True,
    "failure": True,
    "scope": True,
    "metric": True,
    "constraint": True,
    "risk": True,
    "context": False,
    "rationale": False,
}
PREFIX = {
    "functional": "FR",
    "non_functional": "NFR",
    "invariant": "INV",
    "failure": "FAIL",
    "scope": "SCOPE",
    "metric": "METRIC",
    "constraint": "CONSTRAINT",
    "risk": "RISK",
    "context": "CONTEXT",
    "rationale": "RATIONALE",
}


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")


def stable_requirement_id(kind: str, block_ids: list[str], statement: str) -> str:
    # Automatic ids are semantic-text bound rather than source-location bound so
    # exact duplicate atoms can merge across batches without id churn when the
    # same rule gains another source reference. Use an explicit requirement_id
    # when identical wording must intentionally remain separate.
    normalized = " ".join(statement.split()).casefold()
    raw = kind + chr(0) + normalized
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:12].upper()
    return f"{PREFIX[kind]}-{digest}"


def _batch_cost(row: dict[str, Any]) -> int:
    # Use serialized character count as a deterministic context-budget proxy.
    return len(json.dumps(row, ensure_ascii=False, separators=(",", ":")))


def build_batches(
    ledger: dict[str, Any],
    max_blocks: int,
    max_chars: int = 24000,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    blocks = [row for row in ledger.get("blocks", []) if isinstance(row, dict)]
    if max_blocks < 1 or max_chars < 1:
        raise ValueError("batch limits must be positive")

    # Reserve a bounded slice for adjacent context. Ownership/accounting still
    # applies only to target blocks; context is read-only evidence.
    context_reserve = min(4000, max(0, max_chars // 5))
    target_budget = max(1, max_chars - context_reserve)

    batches: list[dict[str, Any]] = []
    current: list[dict[str, Any]] = []
    current_chars = 0

    def flush() -> None:
        nonlocal current, current_chars
        if not current:
            return
        batch_id = f"BATCH-{len(batches) + 1:04d}"
        batches.append({
            "batch_id": batch_id,
            "first_block_id": current[0]["block_id"],
            "last_block_id": current[-1]["block_id"],
            "input_block_count": len(current),
            "owned_char_count": current_chars,
            "max_blocks_per_batch": max_blocks,
            "max_chars_per_batch": max_chars,
            "block_ids": [row["block_id"] for row in current],
            "blocks": current,
            "context_before": [],
            "context_after": [],
            "producer_contract": {
                "ownership": "Only block_ids in this batch may be claimed as primary ownership.",
                "context": "context_before/context_after are read-only adjacent context; never count them as primary ownership.",
                "cross_block": "Atoms may reference more source_block_ids when semantics span target/context blocks.",
                "no_silent_loss": "Every owned block requires atoms or one explicit disposition.",
                "context_budget": "Target plus context input is bounded deterministically; no source text may be truncated.",
            },
        })
        current = []
        current_chars = 0

    for row in blocks:
        cost = _batch_cost(row)
        if cost > max_chars:
            raise ValueError(
                f"source block {row.get('block_id')} exceeds max_chars_per_batch "
                f"({cost}>{max_chars}); do not truncate it silently"
            )
        effective_limit = target_budget if cost <= target_budget else max_chars
        if current and (
            len(current) >= max_blocks
            or current_chars + cost > target_budget
        ):
            flush()
        current.append(row)
        current_chars += cost
        if current_chars >= effective_limit or len(current) >= max_blocks:
            flush()
    flush()

    index_by_id = {
        str(row.get("block_id")): index
        for index, row in enumerate(blocks)
        if row.get("block_id")
    }
    for batch in batches:
        first_index = index_by_id[str(batch["first_block_id"])]
        last_index = index_by_id[str(batch["last_block_id"])]
        total_chars = int(batch["owned_char_count"])

        first_source = str(blocks[first_index].get("source_path") or "")
        last_source = str(blocks[last_index].get("source_path") or "")

        before = blocks[first_index - 1] if first_index > 0 else None
        if before is not None and str(before.get("source_path") or "") == first_source:
            cost = _batch_cost(before)
            if total_chars + cost <= max_chars:
                batch["context_before"] = [before]
                total_chars += cost

        after = blocks[last_index + 1] if last_index + 1 < len(blocks) else None
        if after is not None and str(after.get("source_path") or "") == last_source:
            cost = _batch_cost(after)
            if total_chars + cost <= max_chars:
                batch["context_after"] = [after]
                total_chars += cost

        batch["context_before_block_ids"] = [
            str(row["block_id"]) for row in batch["context_before"]
        ]
        batch["context_after_block_ids"] = [
            str(row["block_id"]) for row in batch["context_after"]
        ]
        batch["context_block_count"] = (
            len(batch["context_before"]) + len(batch["context_after"])
        )
        batch["context_char_count"] = total_chars - int(batch["owned_char_count"])
        batch["input_char_count"] = total_chars

    index = {
        "schema_version": "chapter3.semantic-projection-batches.v1",
        "generated_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "source_revision": ledger.get("source_revision"),
        "source_block_count": len(blocks),
        "batch_count": len(batches),
        "max_blocks_per_batch": max_blocks,
        "max_chars_per_batch": max_chars,
        "context_reserve_chars": context_reserve,
        "batches": [{
            key: value for key, value in batch.items()
            if key not in {"blocks", "context_before", "context_after"}
        } for batch in batches],
    }
    return index, batches


def _reviewed_result(row: dict[str, Any]) -> bool:
    atoms = row.get("atoms", [])
    disposition = str(row.get("disposition") or "").strip()
    return (
        isinstance(row.get("delivery_potential"), bool)
        and isinstance(atoms, list)
        and (bool(atoms) or disposition in ALLOWED_DISPOSITIONS)
    )


def _result_requirement_ids(row: dict[str, Any]) -> set[str]:
    result: set[str] = set()
    for atom in row.get("atoms", []):
        if not isinstance(atom, dict):
            continue
        kind_raw = atom.get("kind")
        try:
            kind = normalize_kind(kind_raw)
        except ValueError:
            continue
        statement = str(atom.get("statement") or "").strip()
        block_ids = [str(value) for value in atom.get("source_block_ids", [row.get("block_id")]) if value]
        if not statement or not block_ids:
            continue
        requirement_id = str(atom.get("requirement_id") or "").strip()
        result.add(requirement_id or stable_requirement_id(kind, block_ids, statement))
    return result


def _reusable_previous_result(
    block: dict[str, Any],
    previous: dict[str, Any],
    unchanged_ids: set[str],
) -> bool:
    block_id = str(block.get("block_id") or "")
    if block_id not in unchanged_ids or not _reviewed_result(previous):
        return False
    if str(previous.get("block_content_hash") or "") != str(block.get("content_hash") or ""):
        return False
    for atom in previous.get("atoms", []):
        if not isinstance(atom, dict):
            return False
        refs = {
            str(value)
            for value in atom.get("source_block_ids", [block_id])
            if value is not None
        }
        if not refs or not refs.issubset(unchanged_ids):
            return False
    return True


def prepare(
    ledger: dict[str, Any],
    max_blocks: int,
    batch_dir: Path,
    max_chars: int = 24000,
    previous_candidate: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    index, batches = build_batches(ledger, max_blocks, max_chars)
    batch_dir.mkdir(parents=True, exist_ok=True)
    for stale in batch_dir.glob("batch-*.json"):
        if stale.is_file():
            stale.unlink()
    block_to_batch: dict[str, str] = {}
    for batch in batches:
        for block_id in batch["block_ids"]:
            block_to_batch[str(block_id)] = batch["batch_id"]
        write_json(batch_dir / f"{batch['batch_id'].lower()}.json", batch)

    previous_by_block = {
        str(row.get("block_id")): row
        for row in (previous_candidate or {}).get("block_results", [])
        if isinstance(row, dict) and row.get("block_id")
    }
    delta = ledger.get("delta") if isinstance(ledger.get("delta"), dict) else {}
    unchanged_ids = {str(value) for value in delta.get("unchanged", [])}
    if str(ledger.get("mode") or "") != "add":
        unchanged_ids = set()

    results: list[dict[str, Any]] = []
    reused_requirement_ids: set[str] = set()
    reused_blocks: list[str] = []
    review_required_blocks: list[str] = []
    reused_per_batch: dict[str, int] = {}

    for block in ledger.get("blocks", []):
        if not isinstance(block, dict):
            continue
        block_id = str(block.get("block_id"))
        batch_id = block_to_batch.get(block_id)
        row: dict[str, Any] = {
            "batch_id": batch_id,
            "block_id": block_id,
            "block_content_hash": block.get("content_hash"),
            "atoms": [],
            "disposition": "",
            "delivery_potential": None,
            "decision": None,
            "review_status": "review_required",
        }
        prior = previous_by_block.get(block_id)
        if prior is not None and _reusable_previous_result(block, prior, unchanged_ids):
            row.update({
                "atoms": json.loads(json.dumps(prior.get("atoms", []), ensure_ascii=False)),
                "disposition": str(prior.get("disposition") or ""),
                "delivery_potential": prior.get("delivery_potential"),
                "decision": json.loads(json.dumps(prior.get("decision"), ensure_ascii=False)),
                "review_status": "reused_unchanged",
                "reused_from_source_revision": previous_candidate.get("source_revision"),
            })
            reused_blocks.append(block_id)
            reused_requirement_ids.update(_result_requirement_ids(row))
            if batch_id:
                reused_per_batch[batch_id] = reused_per_batch.get(batch_id, 0) + 1
        else:
            review_required_blocks.append(block_id)
        results.append(row)

    previous_capabilities = [
        row for row in (previous_candidate or {}).get("capabilities", [])
        if isinstance(row, dict)
    ]
    reusable_capabilities = []
    stale_capabilities = []
    for capability in previous_capabilities:
        refs = {str(value) for value in capability.get("requirement_ids", []) if value}
        if refs and refs.issubset(reused_requirement_ids):
            reusable_capabilities.append(json.loads(json.dumps(capability, ensure_ascii=False)))
        else:
            if capability.get("capability_id"):
                stale_capabilities.append(str(capability["capability_id"]))

    candidate = {
        "schema_version": "chapter3.semantic-projection-candidate.v1",
        "generated_at_utc": index["generated_at_utc"],
        "mode": ledger.get("mode"),
        "source_revision": ledger.get("source_revision"),
        "source_manifest_sha256": ledger.get("source_manifest_sha256"),
        "instructions": {
            "producer": "Review every review_required block. Reused unchanged blocks are already accounted and must not be silently rewritten.",
            "allowed_dispositions": sorted(ALLOWED_DISPOSITIONS),
            "allowed_kinds": sorted(set(KIND_MAP)),
            "delivery_potential": "Set a boolean for every review_required block. Keyword hints are hints only and never decide this field.",
            "uncertainty": "Use unresolved explicitly. Delivery-potential unresolved blocks block stable closure.",
            "batch_accounting": "output_accounted_count starts with verified reused blocks; after review it must equal the batch input count.",
            "equivalent_merge": "Exact normalized duplicate atoms auto-merge across blocks. Reuse one explicit requirement_id for semantically equivalent paraphrases; use distinct explicit ids when identical wording is intentionally separate.",
        },
        "batch_summaries": [{
            "batch_id": row["batch_id"],
            "first_block_id": row["first_block_id"],
            "last_block_id": row["last_block_id"],
            "input_block_count": row["input_block_count"],
            "input_char_count": row["input_char_count"],
            "output_accounted_count": reused_per_batch.get(row["batch_id"], 0),
            "reused_accounted_count": reused_per_batch.get(row["batch_id"], 0),
        } for row in index["batches"]],
        "block_results": results,
        "capabilities": reusable_capabilities,
        "reuse_summary": {
            "previous_source_revision": (previous_candidate or {}).get("source_revision"),
            "reused_blocks": sorted(reused_blocks),
            "review_required_blocks": sorted(review_required_blocks),
            "removed_blocks": sorted(str(value) for value in delta.get("removed", [])),
            "reused_capabilities": sorted(
                str(row.get("capability_id")) for row in reusable_capabilities if row.get("capability_id")
            ),
            "stale_capabilities": sorted(stale_capabilities),
        },
    }
    return index, candidate

def normalize_kind(value: Any) -> str:
    key = str(value or "").strip()
    if key in KIND_MAP:
        return KIND_MAP[key]
    upper = key.upper()
    if upper in KIND_MAP:
        return KIND_MAP[upper]
    raise ValueError(f"unsupported semantic kind: {value}")


def compile_projection(
    ledger: dict[str, Any],
    batches: dict[str, Any],
    candidate: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    source_revision = str(ledger.get("source_revision") or "")
    if str(batches.get("source_revision") or "") != source_revision:
        raise ValueError("semantic batch source_revision does not match source ledger")
    if str(candidate.get("source_revision") or "") != source_revision:
        raise ValueError("semantic candidate source_revision does not match source ledger")
    ledger_manifest_sha = str(ledger.get("source_manifest_sha256") or "")
    candidate_manifest_sha = str(candidate.get("source_manifest_sha256") or "")
    if not candidate_manifest_sha or candidate_manifest_sha != ledger_manifest_sha:
        raise ValueError("semantic candidate source_manifest_sha256 does not match source ledger")

    blocks = {
        str(row.get("block_id")): row
        for row in ledger.get("blocks", [])
        if isinstance(row, dict) and row.get("block_id")
    }
    owned_block_ids = [
        str(block_id)
        for batch in batches.get("batches", [])
        if isinstance(batch, dict)
        for block_id in batch.get("block_ids", [])
    ]
    duplicate_ownership = sorted({
        block_id for block_id in owned_block_ids
        if owned_block_ids.count(block_id) > 1
    })
    if duplicate_ownership:
        raise ValueError(
            "duplicate primary batch ownership: " + ", ".join(duplicate_ownership[:20])
        )
    unknown_owned = sorted(set(owned_block_ids) - set(blocks))
    if unknown_owned:
        raise ValueError(
            "prepared batches reference unknown source blocks: "
            + ", ".join(unknown_owned[:20])
        )
    missing_owned = sorted(set(blocks) - set(owned_block_ids))
    if missing_owned:
        raise ValueError(
            "prepared batches omit source blocks: " + ", ".join(missing_owned[:20])
        )
    assigned = {
        str(block_id): str(batch.get("batch_id"))
        for batch in batches.get("batches", [])
        for block_id in batch.get("block_ids", [])
    }
    expected_batches = {
        str(batch.get("batch_id")): batch
        for batch in batches.get("batches", [])
        if isinstance(batch, dict) and batch.get("batch_id")
    }
    summaries = candidate.get("batch_summaries", [])
    if not isinstance(summaries, list):
        raise ValueError("batch_summaries must be a list")
    summary_by_id = {
        str(row.get("batch_id")): row
        for row in summaries if isinstance(row, dict) and row.get("batch_id")
    }
    if set(summary_by_id) != set(expected_batches):
        raise ValueError("candidate batch summaries do not match prepared batches")
    for batch_id, expected in expected_batches.items():
        summary = summary_by_id[batch_id]
        for field in ("first_block_id", "last_block_id", "input_block_count"):
            if summary.get(field) != expected.get(field):
                raise ValueError(f"batch summary mismatch for {batch_id}: {field}")
        if int(summary.get("output_accounted_count") or 0) != int(expected.get("input_block_count") or 0):
            raise ValueError(f"batch {batch_id} output_accounted_count does not reconcile")

    results = candidate.get("block_results", [])
    if not isinstance(results, list):
        raise ValueError("block_results must be a list")
    seen_blocks = set()
    requirements = []
    accounting = []
    by_requirement = {}
    for result in results:
        if not isinstance(result, dict):
            raise ValueError("each block result must be an object")
        block_id = str(result.get("block_id") or "")
        if block_id not in blocks:
            raise ValueError(f"unknown block_id in candidate: {block_id}")
        if block_id in seen_blocks:
            raise ValueError(f"duplicate primary block result: {block_id}")
        seen_blocks.add(block_id)
        if str(result.get("block_content_hash") or "") != str(blocks[block_id].get("content_hash") or ""):
            raise ValueError(f"stale block_content_hash for {block_id}")
        batch_id = str(result.get("batch_id") or "")
        if assigned.get(block_id) != batch_id:
            raise ValueError(f"batch ownership mismatch for {block_id}")
        atoms = result.get("atoms", [])
        if not isinstance(atoms, list):
            raise ValueError(f"atoms must be a list for {block_id}")
        disposition = str(result.get("disposition") or "").strip()
        if not isinstance(result.get("delivery_potential"), bool):
            raise ValueError(f"block {block_id} must explicitly set delivery_potential")
        if not atoms and disposition not in ALLOWED_DISPOSITIONS:
            raise ValueError(f"block {block_id} has neither atoms nor valid disposition")
        if atoms and disposition and disposition not in ALLOWED_DISPOSITIONS:
            raise ValueError(f"block {block_id} has invalid disposition {disposition}")
        requirement_ids = []
        for atom in atoms:
            if not isinstance(atom, dict):
                raise ValueError(f"atom for {block_id} must be an object")
            kind = normalize_kind(atom.get("kind"))
            statement = str(atom.get("statement") or "").strip()
            if not statement:
                raise ValueError(f"atom for {block_id} has empty statement")
            source_block_ids = [str(value) for value in atom.get("source_block_ids", [block_id])]
            if not source_block_ids or any(value not in blocks for value in source_block_ids):
                raise ValueError(f"atom for {block_id} has invalid source_block_ids")
            requirement_id = str(atom.get("requirement_id") or "").strip()
            if not requirement_id:
                requirement_id = stable_requirement_id(kind, source_block_ids, statement)
            delivery_relevant = atom.get("delivery_relevant")
            if not isinstance(delivery_relevant, bool):
                delivery_relevant = DELIVERY_DEFAULT[kind]
            sinks = atom.get("non_task_sinks", [])
            if not isinstance(sinks, list):
                raise ValueError(f"non_task_sinks must be a list for {requirement_id}")
            status = str(atom.get("status") or "active").strip().casefold()
            if status not in ALLOWED_REQUIREMENT_STATUSES:
                raise ValueError(
                    f"unsupported requirement status for {requirement_id}: {status}"
                )
            row = {
                "requirement_id": requirement_id,
                "kind": kind,
                "statement": statement,
                "source_block_ids": sorted(set(source_block_ids)),
                "delivery_relevant": delivery_relevant,
                "capability_ids": sorted(set(str(value) for value in atom.get("capability_ids", []))),
                "sink_policy": str(atom.get("sink_policy") or "task_or_global_constraint"),
                "status": status,
                "priority": str(atom.get("priority") or "P2").upper(),
                "owner_hint": atom.get("owner_hint"),
                "layer_hint": atom.get("layer_hint"),
                "non_task_sinks": sinks,
            }
            if atom.get("rationale"):
                row["rationale"] = str(atom["rationale"])
            if isinstance(atom.get("decision"), dict):
                row["decision"] = atom["decision"]
            if atom.get("disposition"):
                row["disposition"] = str(atom["disposition"])

            existing = by_requirement.get(requirement_id)
            if existing is not None:
                if existing.get("kind") != kind:
                    raise ValueError(
                        f"equivalent requirement {requirement_id} has conflicting kinds"
                    )
                explicit_id = bool(str(atom.get("requirement_id") or "").strip())
                if (
                    not explicit_id
                    and " ".join(str(existing.get("statement") or "").split()).casefold()
                    != " ".join(statement.split()).casefold()
                ):
                    raise ValueError(
                        f"automatic requirement id collision for {requirement_id}"
                    )
                for field in ("delivery_relevant", "sink_policy", "status"):
                    if existing.get(field) != row.get(field):
                        raise ValueError(
                            f"equivalent requirement {requirement_id} conflicts on {field}"
                        )
                for field in ("owner_hint", "layer_hint"):
                    left = existing.get(field)
                    right = row.get(field)
                    if left and right and left != right:
                        raise ValueError(
                            f"equivalent requirement {requirement_id} conflicts on {field}"
                        )
                    if not left and right:
                        existing[field] = right
                existing["source_block_ids"] = sorted(set(
                    list(existing.get("source_block_ids", [])) + source_block_ids
                ))
                existing["capability_ids"] = sorted(set(
                    list(existing.get("capability_ids", []))
                    + list(row.get("capability_ids", []))
                ))
                sink_map = {
                    json.dumps(value, ensure_ascii=False, sort_keys=True): value
                    for value in list(existing.get("non_task_sinks", []))
                    + list(row.get("non_task_sinks", []))
                    if isinstance(value, dict)
                }
                existing["non_task_sinks"] = [
                    sink_map[key] for key in sorted(sink_map)
                ]
                priority_rank = {"P0": 0, "P1": 1, "P2": 2, "P3": 3}
                priorities = [
                    str(existing.get("priority") or "P2").upper(),
                    str(row.get("priority") or "P2").upper(),
                ]
                existing["priority"] = min(
                    priorities, key=lambda value: priority_rank.get(value, 99)
                )
                statements = {
                    str(existing.get("statement") or "").strip(),
                    statement,
                    *[
                        str(value).strip()
                        for value in existing.get("equivalent_statements", [])
                        if str(value).strip()
                    ],
                }
                statements.discard("")
                canonical = str(existing.get("statement") or "").strip()
                aliases = sorted(value for value in statements if value != canonical)
                if aliases:
                    existing["equivalent_statements"] = aliases
                rationales = {
                    str(value).strip()
                    for value in (
                        existing.get("rationale"),
                        row.get("rationale"),
                    )
                    if value and str(value).strip()
                }
                if rationales:
                    existing["rationale"] = " | ".join(sorted(rationales))
            else:
                requirements.append(row)
                by_requirement[requirement_id] = row
            requirement_ids.append(requirement_id)
        accounting.append({
            "block_id": block_id,
            "batch_id": batch_id,
            "block_content_hash": result.get("block_content_hash"),
            "requirement_ids": requirement_ids,
            "disposition": disposition or ("atomized" if atoms else ""),
            "delivery_potential": bool(result.get("delivery_potential")),
            "decision": result.get("decision"),
            "review_status": str(result.get("review_status") or "reviewed"),
            "reused_from_source_revision": result.get("reused_from_source_revision"),
        })
    missing = sorted(set(blocks) - seen_blocks)
    if missing:
        raise ValueError("candidate omitted source blocks: " + ", ".join(missing[:20]))

    capabilities_raw = candidate.get("capabilities", [])
    if not isinstance(capabilities_raw, list):
        raise ValueError("capabilities must be a list")
    capabilities = []
    capability_ids = set()
    for raw in capabilities_raw:
        if not isinstance(raw, dict):
            raise ValueError("capability must be an object")
        capability_id = str(raw.get("capability_id") or "").strip()
        title = str(raw.get("title") or "").strip()
        requirement_ids = sorted(set(str(value) for value in raw.get("requirement_ids", [])))
        if not capability_id or not title or not requirement_ids:
            raise ValueError("capability requires capability_id, title, and requirement_ids")
        if capability_id in capability_ids:
            raise ValueError(f"duplicate capability_id: {capability_id}")
        if any(rid not in by_requirement for rid in requirement_ids):
            raise ValueError(f"capability {capability_id} references unknown requirements")
        capability_ids.add(capability_id)
        capabilities.append({
            "capability_id": capability_id,
            "title": title,
            "description": str(raw.get("description") or ""),
            "requirement_ids": requirement_ids,
        })
        for rid in requirement_ids:
            values = set(by_requirement[rid].get("capability_ids", []))
            values.add(capability_id)
            by_requirement[rid]["capability_ids"] = sorted(values)

    edges = []
    edge_keys = set()

    def add_edge(source_type: str, source_id: str, target_type: str, target_id: str, relation: str, **extra: Any) -> None:
        key = (source_type, source_id, target_type, target_id, relation)
        if key in edge_keys:
            return
        edge_keys.add(key)
        edges.append({
            "source_type": source_type,
            "source_id": source_id,
            "target_type": target_type,
            "target_id": target_id,
            "relation": relation,
            **extra,
        })

    for requirement in requirements:
        for block_id in requirement.get("source_block_ids", []):
            add_edge("source_block", str(block_id), "requirement",
                     requirement["requirement_id"], "projects_to")
    for capability in capabilities:
        for rid in capability["requirement_ids"]:
            add_edge("requirement", rid, "capability", capability["capability_id"], "grouped_by")
    for requirement in requirements:
        rid = requirement["requirement_id"]
        for sink in requirement.get("non_task_sinks", []):
            if not isinstance(sink, dict):
                raise ValueError(f"non-task sink for {rid} must be an object")
            sink_type = str(sink.get("type") or "").strip()
            sink_id = str(sink.get("id") or "").strip()
            if sink_type == "adr_owned":
                sink_type = "adr"
                sink["type"] = "adr"
            if sink_type not in {"global_constraint", "quality_gate", "adr", "deferred", "exclusion"} or not sink_id:
                raise ValueError(f"invalid non-task sink for {rid}")
            add_edge("requirement", rid, sink_type, sink_id, str(sink.get("relation") or "governed_by"))

    generated = dt.datetime.now(dt.timezone.utc).isoformat()
    semantic_doc = {
        "schema_version": "newrouge.semantic-requirements.v1",
        "generated_at_utc": generated,
        "source_revision": ledger.get("source_revision"),
        "source_manifest_sha256": ledger.get("source_manifest_sha256"),
        "source_accounting": accounting,
        "requirements": requirements,
    }
    capability_doc = {
        "schema_version": "newrouge.capabilities.v1",
        "generated_at_utc": generated,
        "source_revision": ledger.get("source_revision"),
        "capabilities": capabilities,
    }
    edge_doc = {
        "schema_version": "newrouge.topology-edges.v1",
        "generated_at_utc": generated,
        "source_revision": ledger.get("source_revision"),
        "edges": edges,
    }
    return semantic_doc, capability_doc, edge_doc


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="action", required=True)

    prepare_parser = sub.add_parser("prepare")
    prepare_parser.add_argument("--repo-root", default=".")
    prepare_parser.add_argument("--ledger", default="logs/ci/task-generation/source-blocks.v1.json")
    prepare_parser.add_argument("--max-blocks-per-batch", type=int, default=40)
    prepare_parser.add_argument("--max-chars-per-batch", type=int, default=24000)
    prepare_parser.add_argument("--batch-dir", default="logs/ci/task-generation/semantic-batches")
    prepare_parser.add_argument("--batches-out", default="logs/ci/task-generation/semantic-projection.batches.v1.json")
    prepare_parser.add_argument("--candidate-out", default="logs/ci/task-generation/semantic-projection.candidate.json")
    prepare_parser.add_argument(
        "--previous-candidate",
        default="",
        help="Optional prior semantic candidate for add-mode per-block reuse. Defaults to candidate-out when it already exists.",
    )

    compile_parser = sub.add_parser("compile")
    compile_parser.add_argument("--repo-root", default=".")
    compile_parser.add_argument("--ledger", default="logs/ci/task-generation/source-blocks.v1.json")
    compile_parser.add_argument("--batches", default="logs/ci/task-generation/semantic-projection.batches.v1.json")
    compile_parser.add_argument("--candidate", default="logs/ci/task-generation/semantic-projection.candidate.json")
    compile_parser.add_argument("--requirements-out", default="logs/ci/task-generation/semantic-requirements.v1.json")
    compile_parser.add_argument("--capabilities-out", default="logs/ci/task-generation/capabilities.v1.json")
    compile_parser.add_argument("--edges-out", default="logs/ci/task-generation/topology-edges.base.v1.json")

    args = parser.parse_args(argv)
    root = Path(args.repo_root).resolve()
    if args.action == "prepare":
        ledger = load_json(root / args.ledger)
        previous_candidate = None
        if str(ledger.get("mode") or "") == "add":
            previous_path = root / (args.previous_candidate or args.candidate_out)
            if previous_path.is_file():
                previous_candidate = load_json(previous_path)
        try:
            index, candidate = prepare(
                ledger,
                max(1, args.max_blocks_per_batch),
                root / args.batch_dir,
                max(1, args.max_chars_per_batch),
                previous_candidate=previous_candidate,
            )
        except ValueError as exc:
            print(f"semantic_projection_prepare_error={exc}")
            return 2
        write_json(root / args.batches_out, index)
        write_json(root / args.candidate_out, candidate)
        print(
            f"semantic_batches={root / args.batches_out} batches={index['batch_count']} "
            f"blocks={index['source_block_count']} reused={len(candidate.get('reuse_summary', {}).get('reused_blocks', []))} "
            f"review_required={len(candidate.get('reuse_summary', {}).get('review_required_blocks', []))} "
            f"candidate={root / args.candidate_out}"
        )
        return 0
    try:
        semantics, capabilities, edges = compile_projection(
            load_json(root / args.ledger),
            load_json(root / args.batches),
            load_json(root / args.candidate),
        )
    except ValueError as exc:
        print(f"semantic_projection_error={exc}")
        return 2
    write_json(root / args.requirements_out, semantics)
    write_json(root / args.capabilities_out, capabilities)
    write_json(root / args.edges_out, edges)
    print(
        f"semantic_requirements={root / args.requirements_out} requirements={len(semantics['requirements'])} "
        f"capabilities={len(capabilities['capabilities'])}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
