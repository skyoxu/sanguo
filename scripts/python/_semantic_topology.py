#!/usr/bin/env python3
"""Read-only semantic delivery topology projection helpers.

Repository source remains authority. This module never invents semantic nodes and
never mutates Taskmaster. It validates and projects registered topology artifacts
when they exist, otherwise it returns an explicit legacy/unavailable view.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

TOPOLOGY_DIR = "docs/planning/semantic-topology"
TOPOLOGY_ARTIFACTS = {
    "manifest": f"{TOPOLOGY_DIR}/topology-manifest.v1.json",
    "source_blocks": f"{TOPOLOGY_DIR}/source-blocks.v1.json",
    "requirements": f"{TOPOLOGY_DIR}/semantic-requirements.v1.json",
    "capabilities": f"{TOPOLOGY_DIR}/capabilities.v1.json",
    "edges": f"{TOPOLOGY_DIR}/topology-edges.v1.json",
}
WORKSPACE_TOPOLOGY = Path("logs/ci/project-health-knowledge/topology/workspace-latest.json")
WORKSPACE_TOPOLOGY_ATTEMPT = Path("logs/ci/project-health-knowledge/topology/workspace-last-attempt.json")
WORKSPACE_TOPOLOGY_STABLE = Path("logs/ci/project-health-knowledge/topology/workspace-latest-successful.json")
WORKSPACE_TOPOLOGY_STABILIZED = Path("logs/ci/project-health-knowledge/topology/workspace-latest-stabilized.json")


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _rows(value: Any, *keys: str) -> list[dict[str, Any]]:
    if isinstance(value, list):
        return [row for row in value if isinstance(row, dict)]
    if isinstance(value, dict):
        for key in keys:
            rows = value.get(key)
            if isinstance(rows, list):
                return [row for row in rows if isinstance(row, dict)]
    return []


def _identity(kind: str, revision: str | None, authority_ref: str | None = None) -> dict[str, Any]:
    result = {"kind": kind, "revision": revision}
    if authority_ref:
        result["authority_ref"] = authority_ref
    return result


def unavailable_topology(kind: str, revision: str | None, reason: str,
                         authority_ref: str | None = None) -> dict[str, Any]:
    return {
        "schema_version": "newrouge.semantic-topology-view.v1",
        "available": False,
        "fresh": False,
        "identity": _identity(kind, revision, authority_ref),
        "status": "legacy_unmapped",
        "reason": reason,
        "nodes": {
            "source_blocks": [],
            "requirements": [],
            "capabilities": [],
            "tasks": [],
            "acceptance": [],
        },
        "edges": [],
        "task_trace": {},
        "summary": {
            "source_blocks": 0,
            "delivery_requirements": 0,
            "requirements_with_sink": 0,
            "tasks_with_semantic_refs": 0,
            "acceptance_with_semantic_origin": 0,
            "orphan_requirements": 0,
            "unresolved_requirements": 0,
        },
        "problems": [],
    }


def _node_id(kind: str, row: dict[str, Any]) -> str | None:
    candidates = {
        "source_block": ("block_id", "source_block_id", "id"),
        "requirement": ("requirement_id", "semantic_id", "id"),
        "capability": ("capability_id", "id"),
        "task": ("task_id", "taskmaster_id", "id"),
        "acceptance": ("acceptance_id", "anchor", "id"),
    }
    for key in candidates.get(kind, ("id",)):
        value = row.get(key)
        if value is not None and str(value).strip():
            return str(value)
    return None


def _edge_endpoint(edge: dict[str, Any], side: str) -> tuple[str | None, str | None]:
    nested = edge.get(side)
    if isinstance(nested, dict):
        kind = nested.get("type") or nested.get("kind")
        value = nested.get("id")
        return (str(kind) if kind else None, str(value) if value is not None else None)
    kind = edge.get(f"{side}_type") or edge.get(f"{side}_kind")
    value = edge.get(f"{side}_id")
    if value is None:
        value = edge.get(side)
    return (str(kind) if kind else None, str(value) if value is not None else None)


def _task_rows(task_details: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for detail in task_details or []:
        task = detail.get("task") if isinstance(detail.get("task"), dict) else {}
        task_id = task.get("id")
        if task_id is None:
            continue
        rows.append({
            "task_id": str(task_id),
            "title": task.get("title"),
            "status": task.get("status"),
            "semantic_refs": task.get("semantic_refs", task.get("requirement_ids", [])),
            "capability_refs": task.get("capability_refs", []),
            "overlay_requirement_refs": task.get("overlay_requirement_refs", {}),
            "contract_requirement_refs": task.get("contract_requirement_refs", {}),
        })
    return rows


def _acceptance_rows(task_details: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    """Project existing task-view acceptance authority into stable read-only nodes."""
    by_key: dict[tuple[str, str], dict[str, Any]] = {}
    for detail in task_details or []:
        task = detail.get("task") if isinstance(detail.get("task"), dict) else {}
        task_id = task.get("id")
        if task_id is None:
            continue
        mappings = detail.get("mappings") if isinstance(detail.get("mappings"), dict) else {}
        for view_name, rows in mappings.items():
            if view_name not in {"tasks_back", "tasks_gameplay"} or not isinstance(rows, list):
                continue
            source_path = f".taskmaster/tasks/{view_name}.json"
            for row in rows:
                if not isinstance(row, dict):
                    continue
                values = row.get("acceptance", [])
                if not isinstance(values, list):
                    continue
                for index, value in enumerate(values, 1):
                    if not isinstance(value, str) or not value.strip():
                        continue
                    statement = value.strip()
                    key = (str(task_id), statement)
                    digest = hashlib.sha256(
                        (str(task_id) + "\0" + statement).encode("utf-8")
                    ).hexdigest()[:12]
                    node = by_key.setdefault(key, {
                        "acceptance_id": f"AC-T{task_id}-{digest}",
                        "task_id": str(task_id),
                        "statement": statement,
                        "source_views": [],
                        "source_paths": [],
                        "source_indexes": [],
                        "topology_origin": "unmapped",
                    })
                    if view_name not in node["source_views"]:
                        node["source_views"].append(view_name)
                    if source_path not in node["source_paths"]:
                        node["source_paths"].append(source_path)
                    marker = {"view": view_name, "index": index}
                    if marker not in node["source_indexes"]:
                        node["source_indexes"].append(marker)
    return sorted(by_key.values(), key=lambda row: (row["task_id"], row["acceptance_id"]))


def _sha_field(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    raw = value.removeprefix("sha256:")
    return len(raw) == 64 and all(ch in "0123456789abcdef" for ch in raw)


def _validate_minimum_shapes(documents: dict[str, Any],
                             problems: list[dict[str, Any]]) -> None:
    expected = {
        "manifest": "newrouge.semantic-topology-manifest.v1",
        "source_blocks": "newrouge.source-blocks.v1",
        "requirements": "newrouge.semantic-requirements.v1",
        "capabilities": "newrouge.capabilities.v1",
        "edges": "newrouge.topology-edges.v1",
    }
    for key, schema_version in expected.items():
        document = documents.get(key)
        if not isinstance(document, dict):
            problems.append({"kind": "invalid_artifact_shape", "artifact": key})
            continue
        if document.get("schema_version") != schema_version:
            problems.append({"kind": "schema_version_mismatch", "artifact": key,
                             "expected": schema_version,
                             "actual": document.get("schema_version")})

    manifest = documents.get("manifest") if isinstance(documents.get("manifest"), dict) else {}
    for field in ("source_revision", "schema_revision", "generator_revision"):
        if not isinstance(manifest.get(field), str) or not manifest.get(field):
            problems.append({"kind": "manifest_missing_field", "field": field})
    if not _sha_field(manifest.get("source_manifest_sha256")):
        problems.append({"kind": "manifest_invalid_source_manifest_hash"})

    for row in _rows(documents.get("source_blocks"), "blocks", "source_blocks"):
        block_id = _node_id("source_block", row)
        for field in ("source_path", "content_hash", "source_sha256"):
            if not isinstance(row.get(field), str) or not row.get(field):
                problems.append({"kind": "source_block_missing_field",
                                 "source_block_id": block_id, "field": field})
        if not isinstance(row.get("line_start"), int) or not isinstance(row.get("line_end"), int):
            problems.append({"kind": "source_block_invalid_line_range",
                             "source_block_id": block_id})
        elif row["line_start"] < 1 or row["line_end"] < row["line_start"]:
            problems.append({"kind": "source_block_invalid_line_range",
                             "source_block_id": block_id})
        if not _sha_field(row.get("content_hash")):
            problems.append({"kind": "source_block_invalid_content_hash",
                             "source_block_id": block_id})

    valid_kinds = {
        "functional", "non_functional", "invariant", "failure", "scope",
        "metric", "constraint", "risk", "context", "rationale",
    }
    for row in _rows(documents.get("requirements"), "requirements", "semantic_requirements", "atoms"):
        rid = _node_id("requirement", row)
        if row.get("kind") not in valid_kinds:
            problems.append({"kind": "invalid_requirement_kind",
                             "requirement_id": rid, "value": row.get("kind")})
        if not isinstance(row.get("statement"), str) or not row.get("statement").strip():
            problems.append({"kind": "requirement_missing_statement", "requirement_id": rid})
        refs = row.get("source_block_ids")
        if not isinstance(refs, list) or not refs:
            problems.append({"kind": "requirement_missing_source_blocks", "requirement_id": rid})
        if not isinstance(row.get("delivery_relevant"), bool):
            problems.append({"kind": "requirement_invalid_delivery_relevance", "requirement_id": rid})
        for field in ("sink_policy", "status"):
            if not isinstance(row.get(field), str) or not row.get(field):
                problems.append({"kind": "requirement_missing_field",
                                 "requirement_id": rid, "field": field})

    for row in _rows(documents.get("capabilities"), "capabilities"):
        cid = _node_id("capability", row)
        if not isinstance(row.get("title"), str) or not row.get("title").strip():
            problems.append({"kind": "capability_missing_title", "capability_id": cid})
        refs = row.get("requirement_ids")
        if not isinstance(refs, list) or not refs:
            problems.append({"kind": "capability_missing_requirements", "capability_id": cid})

    for edge in _rows(documents.get("edges"), "edges"):
        missing = [
            field for field in ("source_type", "source_id", "target_type", "target_id", "relation")
            if not isinstance(edge.get(field), str) or not edge.get(field)
        ]
        if missing:
            problems.append({"kind": "invalid_edge_shape", "missing_fields": missing})


def _validate_artifact_hashes(snapshot: Any, manifest: dict[str, Any],
                              problems: list[dict[str, Any]]) -> None:
    bindings = manifest.get("artifacts")
    expected_paths = {
        TOPOLOGY_ARTIFACTS["source_blocks"],
        TOPOLOGY_ARTIFACTS["requirements"],
        TOPOLOGY_ARTIFACTS["capabilities"],
        TOPOLOGY_ARTIFACTS["edges"],
    }
    if not isinstance(bindings, dict):
        problems.append({"kind": "missing_artifact_bindings"})
        return
    for required_path in sorted(expected_paths):
        if required_path not in bindings:
            problems.append({"kind": "missing_artifact_binding", "path": required_path})
    for path, expected in bindings.items():
        if not isinstance(path, str) or not isinstance(expected, str):
            problems.append({"kind": "invalid_manifest_binding", "path": str(path)})
            continue
        if path not in getattr(snapshot, "paths", ()):
            problems.append({"kind": "missing_artifact", "path": path})
            continue
        actual = snapshot.digest(path)
        if expected.removeprefix("sha256:") != actual:
            problems.append({"kind": "artifact_hash_mismatch", "path": path,
                             "expected": expected, "actual": actual})


def _validate_source_hashes(snapshot: Any, source_blocks: list[dict[str, Any]],
                            problems: list[dict[str, Any]]) -> None:
    paths = set(getattr(snapshot, "paths", ()))
    for row in source_blocks:
        block_id = _node_id("source_block", row)
        path = row.get("source_path")
        expected = row.get("source_sha256") or row.get("source_file_sha256")
        if not isinstance(path, str) or not path:
            problems.append({"kind": "source_block_missing_path", "source_block_id": block_id})
            continue
        if path not in paths:
            problems.append({"kind": "source_file_missing", "source_block_id": block_id, "path": path})
            continue
        if not isinstance(expected, str) or not expected:
            problems.append({"kind": "source_block_missing_source_hash",
                             "source_block_id": block_id, "path": path})
            continue
        actual = snapshot.digest(path)
        if expected.removeprefix("sha256:") != actual:
            problems.append({"kind": "source_hash_mismatch", "source_block_id": block_id,
                             "path": path, "expected": expected, "actual": actual})


def build_topology_view(identity: dict[str, Any], manifest: dict[str, Any],
                        source_blocks_doc: Any, requirements_doc: Any,
                        capabilities_doc: Any, edges_doc: Any,
                        task_details: list[dict[str, Any]] | None = None,
                        problems: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    problems = list(problems or [])
    source_blocks = _rows(source_blocks_doc, "blocks", "source_blocks")
    requirements = _rows(requirements_doc, "requirements", "semantic_requirements", "atoms")
    capabilities = _rows(capabilities_doc, "capabilities")
    edges = list(_rows(edges_doc, "edges"))
    tasks = _task_rows(task_details)
    acceptance = _acceptance_rows(task_details)
    overlay_nodes: dict[str, dict[str, Any]] = {}
    contract_nodes: dict[str, dict[str, Any]] = {}
    derived_edge_keys = {
        (
            str(edge.get("source_type") or ""),
            str(edge.get("source_id") or ""),
            str(edge.get("target_type") or ""),
            str(edge.get("target_id") or ""),
            str(edge.get("relation") or ""),
        )
        for edge in edges if isinstance(edge, dict)
    }
    for task in tasks:
        task_id = str(task.get("task_id") or "")
        for field, target_type, node_map in (
            ("overlay_requirement_refs", "overlay", overlay_nodes),
            ("contract_requirement_refs", "contract", contract_nodes),
        ):
            mapping = task.get(field)
            if not isinstance(mapping, dict):
                continue
            for target_id, refs in mapping.items():
                target = str(target_id or "").strip()
                if not target:
                    continue
                node_map.setdefault(target, {"id": target, "path": target})
                if not isinstance(refs, list):
                    problems.append({"kind": f"invalid_{target_type}_requirement_refs", "task_id": task_id, "target_id": target})
                    continue
                for rid in refs:
                    requirement_id = str(rid)
                    key = ("requirement", requirement_id, target_type, target, "constrained_by")
                    if key not in derived_edge_keys:
                        edges.append({
                            "source_type": "requirement",
                            "source_id": requirement_id,
                            "target_type": target_type,
                            "target_id": target,
                            "relation": "constrained_by",
                        })
                        derived_edge_keys.add(key)

    block_ids = {node_id for row in source_blocks if (node_id := _node_id("source_block", row))}
    requirement_ids = {node_id for row in requirements if (node_id := _node_id("requirement", row))}
    capability_ids = {node_id for row in capabilities if (node_id := _node_id("capability", row))}
    task_ids = {row["task_id"] for row in tasks}
    acceptance_ids = {
        node_id for row in acceptance
        if (node_id := _node_id("acceptance", row))
    }

    for kind, rows in (("source_block", source_blocks), ("requirement", requirements),
                       ("capability", capabilities)):
        ids = [_node_id(kind, row) for row in rows]
        if any(value is None for value in ids):
            problems.append({"kind": "missing_node_id", "node_type": kind})
        duplicates = sorted({value for value in ids if value is not None and ids.count(value) > 1})
        for value in duplicates:
            problems.append({"kind": "duplicate_node_id", "node_type": kind, "id": value})

    for row in requirements:
        rid = _node_id("requirement", row)
        refs = row.get("source_block_ids", [])
        if not isinstance(refs, list):
            problems.append({"kind": "invalid_source_block_refs", "requirement_id": rid})
            continue
        for ref in refs:
            if str(ref) not in block_ids:
                problems.append({"kind": "missing_source_block_ref",
                                 "requirement_id": rid, "source_block_id": str(ref)})
    for row in capabilities:
        cid = _node_id("capability", row)
        refs = row.get("requirement_ids", row.get("covers", []))
        if not isinstance(refs, list):
            problems.append({"kind": "invalid_capability_requirement_refs",
                             "capability_id": cid})
            continue
        for ref in refs:
            if str(ref) not in requirement_ids:
                problems.append({"kind": "missing_requirement_ref",
                                 "capability_id": cid, "requirement_id": str(ref)})

    for row in tasks:
        task_id = row["task_id"]
        semantic_refs = row.get("semantic_refs", [])
        capability_refs = row.get("capability_refs", [])
        if isinstance(semantic_refs, list):
            for ref in semantic_refs:
                if str(ref) not in requirement_ids:
                    problems.append({"kind": "invalid_task_semantic_ref",
                                     "task_id": task_id, "requirement_id": str(ref)})
        elif semantic_refs:
            problems.append({"kind": "invalid_task_semantic_refs_shape", "task_id": task_id})
        if isinstance(capability_refs, list):
            for ref in capability_refs:
                if str(ref) not in capability_ids:
                    problems.append({"kind": "invalid_task_capability_ref",
                                     "task_id": task_id, "capability_id": str(ref)})
        elif capability_refs:
            problems.append({"kind": "invalid_task_capability_refs_shape", "task_id": task_id})

    task_trace: dict[str, dict[str, set[str]]] = {
        task_id: {"requirements": set(), "capabilities": set(),
                  "source_blocks": set(), "acceptance": set()}
        for task_id in task_ids
    }
    for row in acceptance:
        task_id = str(row.get("task_id", ""))
        acceptance_id = _node_id("acceptance", row)
        if task_id in task_trace and acceptance_id:
            task_trace[task_id]["acceptance"].add(acceptance_id)
    sink_requirements: set[str] = set()
    acceptance_origins: set[str] = set()
    capability_sinks: set[str] = set()
    for edge in edges:
        left_kind, left_id = _edge_endpoint(edge, "source")
        right_kind, right_id = _edge_endpoint(edge, "target")
        if (left_kind or "").casefold() == "capability" and left_id and (
            (right_kind or "").casefold() in {"task", "global_constraint", "quality_gate", "adr"}
        ):
            capability_sinks.add(left_id)

    for edge in edges:
        left_kind, left_id = _edge_endpoint(edge, "source")
        right_kind, right_id = _edge_endpoint(edge, "target")
        if not left_id or not right_id:
            problems.append({"kind": "invalid_edge", "edge": edge})
            continue
        normalized = {(left_kind or "").casefold(): left_id,
                      (right_kind or "").casefold(): right_id}
        req = normalized.get("requirement") or normalized.get("semantic_requirement")
        task = normalized.get("task")
        cap = normalized.get("capability")
        acc = normalized.get("acceptance")
        block = normalized.get("source_block")
        if req and (
            task
            or ((right_kind or "").casefold() in {"global_constraint", "quality_gate", "adr", "deferred", "exclusion"})
            or (cap and cap in capability_sinks)
        ):
            sink_requirements.add(req)
        if acc and req:
            acceptance_origins.add(acc)
            if acc in acceptance_ids:
                for row in acceptance:
                    if _node_id("acceptance", row) == acc:
                        row["topology_origin"] = "mapped"
                        break
        if task and task in task_trace:
            if req:
                task_trace[task]["requirements"].add(req)
            if cap:
                task_trace[task]["capabilities"].add(cap)
            if block:
                task_trace[task]["source_blocks"].add(block)
            if acc:
                task_trace[task]["acceptance"].add(acc)

    req_by_id = {_node_id("requirement", row): row for row in requirements}
    cap_by_id = {_node_id("capability", row): row for row in capabilities}
    for task_id, trace in task_trace.items():
        for rid in list(trace["requirements"]):
            row = req_by_id.get(rid) or {}
            trace["source_blocks"].update(str(x) for x in row.get("source_block_ids", []) if x is not None)
            trace["capabilities"].update(str(x) for x in row.get("capability_ids", []) if x is not None)
        for cid in list(trace["capabilities"]):
            row = cap_by_id.get(cid) or {}
            refs = row.get("requirement_ids", row.get("covers", []))
            for rid in refs if isinstance(refs, list) else []:
                trace["requirements"].add(str(rid))
                req = req_by_id.get(str(rid)) or {}
                trace["source_blocks"].update(
                    str(x) for x in req.get("source_block_ids", []) if x is not None
                )

    delivery = [
        row for row in requirements
        if row.get("delivery_relevant", True) is True
        and str(row.get("status", "active")).casefold() == "active"
    ]
    unresolved = [
        row for row in requirements
        if str(row.get("status", "")).casefold() == "unresolved"
        or str(row.get("disposition", "")).casefold() == "unresolved"
    ]
    orphan = [
        row for row in delivery
        if (_node_id("requirement", row) or "") not in sink_requirements
        and str(row.get("sink_policy", "")).casefold()
        not in {"deferred", "excluded", "out_of_scope"}
    ]
    orphan_ids = {
        _node_id("requirement", row) for row in orphan
        if _node_id("requirement", row)
    }
    unresolved_ids = {
        _node_id("requirement", row) for row in unresolved
        if _node_id("requirement", row)
    }
    requirement_view: list[dict[str, Any]] = []
    for row in requirements:
        projected = dict(row)
        rid = _node_id("requirement", row)
        states: list[str] = []
        if rid in orphan_ids:
            states.append("orphan")
        if rid in unresolved_ids:
            states.append("unresolved")
        projected["topology_states"] = states
        projected["sink_resolved"] = rid not in orphan_ids
        requirement_view.append(projected)
    source_revision = manifest.get("source_revision")
    repository_revision = manifest.get("repository_revision")
    revision = identity.get("revision")
    fresh = True
    if repository_revision and revision and repository_revision != revision:
        fresh = False
        problems.append({"kind": "repository_revision_mismatch",
                         "manifest_revision": repository_revision,
                         "identity_revision": revision})

    serial_trace = {
        task_id: {key: sorted(values) for key, values in trace.items()}
        for task_id, trace in task_trace.items()
    }
    return {
        "schema_version": "newrouge.semantic-topology-view.v1",
        "available": True,
        "fresh": fresh and not problems,
        "identity": identity,
        "status": "fresh" if fresh and not problems else "stale_or_concern",
        "manifest": {
            "schema_version": manifest.get("schema_version"),
            "source_revision": source_revision,
            "schema_revision": manifest.get("schema_revision"),
            "generator_revision": manifest.get("generator_revision"),
        },
        "nodes": {
            "source_blocks": source_blocks,
            "requirements": requirement_view,
            "capabilities": capabilities,
            "tasks": tasks,
            "acceptance": acceptance,
            "overlays": sorted(overlay_nodes.values(), key=lambda row: row["id"]),
            "contracts": sorted(contract_nodes.values(), key=lambda row: row["id"]),
        },
        "edges": edges,
        "task_trace": serial_trace,
        "summary": {
            "source_blocks": len(source_blocks),
            "delivery_requirements": len(delivery),
            "requirements_with_sink": len([
                r for r in delivery
                if (_node_id("requirement", r) or "") in sink_requirements
            ]),
            "tasks_with_semantic_refs": len([
                t for t in tasks
                if serial_trace.get(t["task_id"], {}).get("requirements")
                or t.get("semantic_refs")
            ]),
            "acceptance_with_semantic_origin": len(
                [item for item in acceptance if item["acceptance_id"] in acceptance_origins]
            ),
            "overlays_with_semantic_origin": len(overlay_nodes),
            "contracts_with_semantic_origin": len(contract_nodes),
            "orphan_requirements": len(orphan),
            "unresolved_requirements": len(unresolved),
        },
        "problems": problems,
    }


def load_topology_from_snapshot(snapshot: Any,
                                task_details: list[dict[str, Any]] | None = None,
                                identity_kind: str = "main") -> dict[str, Any]:
    identity = _identity(identity_kind, getattr(snapshot, "commit", None),
                         getattr(snapshot, "authority_ref", None))
    missing = [
        path for path in TOPOLOGY_ARTIFACTS.values()
        if path not in getattr(snapshot, "paths", ())
    ]
    if missing:
        return unavailable_topology(
            identity_kind, identity.get("revision"),
            "topology artifacts are not present in this snapshot",
            identity.get("authority_ref"),
        )
    documents: dict[str, Any] = {}
    try:
        for key, path in TOPOLOGY_ARTIFACTS.items():
            documents[key] = json.loads(snapshot.read_text(path))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        result = unavailable_topology(
            identity_kind, identity.get("revision"),
            f"topology artifact read failed: {exc}", identity.get("authority_ref")
        )
        result["problems"] = [{"kind": "artifact_read_failed", "reason": str(exc)}]
        return result
    problems: list[dict[str, Any]] = []
    _validate_minimum_shapes(documents, problems)
    _validate_artifact_hashes(snapshot, documents["manifest"], problems)
    _validate_source_hashes(
        snapshot, _rows(documents["source_blocks"], "blocks", "source_blocks"), problems
    )
    return build_topology_view(
        identity, documents["manifest"], documents["source_blocks"],
        documents["requirements"], documents["capabilities"], documents["edges"],
        task_details, problems
    )


def load_workspace_topology(root: Path, view: str = "attempt") -> dict[str, Any]:
    if view not in {"attempt", "stable", "stabilized"}:
        return unavailable_topology(
            "workspace", None, f"unknown workspace topology view: {view}"
        )
    if view == "stabilized":
        path = root / WORKSPACE_TOPOLOGY_STABILIZED
        label = "latest Chapter 5 stabilized"
    elif view == "stable":
        path = root / WORKSPACE_TOPOLOGY_STABLE
        label = "latest successful"
    else:
        preferred = root / WORKSPACE_TOPOLOGY_ATTEMPT
        path = preferred if preferred.is_file() else root / WORKSPACE_TOPOLOGY
        label = "last attempt"
    if not path.is_file():
        result = unavailable_topology(
            "workspace", None, f"no workspace/chapter-run {label} topology exists"
        )
        result["workspace_view"] = view
        return result
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        result = unavailable_topology(
            "workspace", None, f"workspace topology preview is invalid: {exc}"
        )
        result["problems"] = [{"kind": "workspace_preview_invalid", "reason": str(exc)}]
        result["workspace_view"] = view
        return result
    identity = payload.get("identity") if isinstance(payload.get("identity"), dict) else {}
    if identity.get("kind") != "workspace":
        result = unavailable_topology(
            "workspace", identity.get("revision"),
            "workspace preview must declare identity.kind=workspace"
        )
        result["problems"] = [{"kind": "identity_mismatch"}]
        result["workspace_view"] = view
        return result
    revision = identity.get("revision")
    run_identity = identity.get("trigger_run_id") or identity.get("run_id")
    if not (
        isinstance(revision, str)
        and revision.startswith(("workspace:", "run:", "chapter:"))
    ) and not (isinstance(run_identity, str) and run_identity):
        result = unavailable_topology(
            "workspace", str(revision) if revision is not None else None,
            "workspace preview requires workspace/run identity"
        )
        result["problems"] = [{"kind": "workspace_identity_missing"}]
        result["workspace_view"] = view
        return result
    if identity.get("authority_ref") == "refs/heads/main":
        result = unavailable_topology(
            "workspace", str(revision) if revision is not None else None,
            "workspace preview cannot claim main authority"
        )
        result["problems"] = [{"kind": "workspace_claims_main_authority"}]
        result["workspace_view"] = view
        return result
    payload["schema_version"] = "newrouge.semantic-topology-view.v1"
    payload["available"] = bool(payload.get("available", True))
    payload["identity"] = identity
    payload["workspace_view"] = view
    return payload


def attach_scene_design_trace(scene_graph: dict[str, Any], topology: dict[str, Any],
                              task_details: list[dict[str, Any]]) -> None:
    traces: dict[str, dict[str, Any]] = {}
    task_trace = topology.get("task_trace", {}) if topology.get("available") else {}
    for detail in task_details:
        task = detail.get("task") if isinstance(detail.get("task"), dict) else {}
        task_id = str(task.get("id")) if task.get("id") is not None else None
        if not task_id:
            continue
        godot = detail.get("godot") if isinstance(detail.get("godot"), dict) else {}
        level = godot.get("status", "unmapped")
        scenes = godot.get("scenes", [])
        for scene in scenes if isinstance(scenes, list) else []:
            path = scene.get("scene") if isinstance(scene, dict) else scene
            if not isinstance(path, str) or not path:
                continue
            entry = traces.setdefault(path, {
                "tasks": [], "capabilities": set(), "requirements": set(),
                "source_blocks": set(), "evidence_levels": set(),
            })
            entry["tasks"].append({
                "task_id": task_id, "title": task.get("title"),
                "status": task.get("status")
            })
            entry["evidence_levels"].add(str(level))
            trace = task_trace.get(task_id, {})
            entry["capabilities"].update(trace.get("capabilities", []))
            entry["requirements"].update(trace.get("requirements", []))
            entry["source_blocks"].update(trace.get("source_blocks", []))
    scene_graph["design_trace"] = {
        path: {
            "tasks": value["tasks"],
            "capabilities": sorted(value["capabilities"]),
            "requirements": sorted(value["requirements"]),
            "source_blocks": sorted(value["source_blocks"]),
            "evidence_levels": sorted(value["evidence_levels"]),
            "semantic_claim": "navigation_only",
        }
        for path, value in traces.items()
    }
    scene_graph["topology_identity"] = topology.get("identity")
