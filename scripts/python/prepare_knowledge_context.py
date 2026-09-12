from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any


CONSUMERS = ("repository-session", "chapter4", "chapter5", "chapter6", "review")
POLICY_REVISION = "newrouge-knowledge-consumer-policies.v1"
STRUCTURED_SCOPE = re.compile(r"\b[A-Za-z][A-Za-z0-9]*(?:-[A-Za-z0-9]+)+\b")
TASK_SCOPE = re.compile(r"\btask\s+(?:id\s*)?\d+\b", re.IGNORECASE)
TASK_VIEW_SCOPE = re.compile(r"^(?:GM|NG)-\d+$", re.IGNORECASE)
ADR_SCOPE = re.compile(r"^ADR-\d+$", re.IGNORECASE)
PRD_SCOPE = re.compile(r"^PRD-.+$", re.IGNORECASE)


def _atomic_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    with tempfile.NamedTemporaryFile(
        "w",
        encoding="utf-8",
        newline="\n",
        delete=False,
        dir=path.parent,
        suffix=".tmp",
    ) as handle:
        handle.write(text)
        temporary = Path(handle.name)
    os.replace(temporary, path)


def _fallback(
    *,
    consumer: str,
    query: str,
    request_id: str,
    reason: str,
    snapshot: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "schema_version": "newrouge.knowledge-context-candidates.v1",
        "mode": "shadow",
        "consumer": consumer,
        "request_id": request_id,
        "query": query,
        "status": "fallback_required",
        "locator_status": "unavailable",
        "snapshot": snapshot,
        "policy_revision": POLICY_REVISION,
        "semantic_decision_required": True,
        "freeze_state": "unfrozen",
        "candidates": [],
        "fallback": {
            "required": True,
            "reason": reason,
            "authority_route": "docs/agents/13-rag-sources-and-session-ssot.md",
        },
    }


def _request_id(consumer: str, query: str, commit: str | None) -> str:
    seed = f"{consumer}\0{query}\0{commit or 'missing'}".encode("utf-8")
    return "shadow-" + hashlib.sha256(seed).hexdigest()[:16]


def _run_locator(root: Path, request: dict[str, Any]) -> tuple[int, dict[str, Any] | None, str]:
    completed = subprocess.run(
        [sys.executable, str(root / "scripts/python/knowledge_locator.py"), "--repository-root", str(root)],
        input=json.dumps(request, ensure_ascii=False),
        text=True,
        encoding="utf-8",
        capture_output=True,
        check=False,
        cwd=root,
    )
    if completed.returncode != 0:
        return completed.returncode, None, completed.stderr.strip() or "knowledge_locator_failed"
    try:
        return 0, json.loads(completed.stdout), ""
    except json.JSONDecodeError:
        return 1, None, "knowledge_locator_invalid_json"


def _consumer_policy(root: Path, consumer: str) -> dict[str, Any] | None:
    try:
        registry = json.loads(
            (root / "knowledge/policies/consumer-policies.v1.json").read_text(encoding="utf-8")
        )
    except (OSError, json.JSONDecodeError):
        return None
    if registry.get("policy_revision") != POLICY_REVISION:
        return None
    return next(
        (
            item
            for item in registry.get("policies", [])
            if isinstance(item, dict) and item.get("consumer") == consumer
        ),
        None,
    )


def _scope_terms(query: str) -> list[str]:
    values: list[str] = []
    for pattern in (STRUCTURED_SCOPE, TASK_SCOPE):
        for match in pattern.finditer(query):
            value = match.group(0).strip()
            folded = value.casefold()
            if value and all(existing.casefold() != folded for existing in values):
                values.append(value)
    return values


def _scope_type(value: str) -> str:
    if TASK_SCOPE.fullmatch(value) or TASK_VIEW_SCOPE.fullmatch(value):
        return "task"
    if ADR_SCOPE.fullmatch(value):
        return "adr"
    if PRD_SCOPE.fullmatch(value):
        return "prd"
    return "structured"


def _scope_for_context_class(policy: dict[str, Any], context_class: str, values: list[str]) -> list[str]:
    mapping = policy.get("context_query_scope_types")
    if not isinstance(mapping, dict) or context_class not in mapping:
        return values
    allowed = mapping.get(context_class)
    if not isinstance(allowed, list):
        return values
    allowed_types = {str(item).strip() for item in allowed if isinstance(item, str) and item.strip()}
    return [value for value in values if _scope_type(value) in allowed_types]


def _prefer_scope_for_context_class(
    policy: dict[str, Any], context_class: str, values: list[str]
) -> list[str]:
    mapping = policy.get("context_query_scope_preference")
    if not isinstance(mapping, dict):
        return values
    preference = mapping.get(context_class)
    if preference != "task-view-first":
        return values
    task_views = [value for value in values if TASK_VIEW_SCOPE.fullmatch(value)]
    if task_views:
        return [task_views[0]]
    task_numbers = [value for value in values if TASK_SCOPE.fullmatch(value)]
    if task_numbers:
        return [task_numbers[0]]
    return values


def _attribution_prefixes(policy: dict[str, Any], context_class: str | None) -> list[str] | None:
    if context_class is None:
        return None
    mapping = policy.get("context_query_attribution_prefixes")
    if not isinstance(mapping, dict) or context_class not in mapping:
        return None
    raw = mapping.get(context_class)
    if not isinstance(raw, list):
        return None
    return [str(value) for value in raw if isinstance(value, str) and value]


def _supplement_context_classes(policy: dict[str, Any]) -> list[str]:
    required = [
        value
        for value in policy.get("required_context_classes", [])
        if isinstance(value, str) and value
    ]
    optional = [
        value
        for value in policy.get("optional_context_classes", [])
        if isinstance(value, str) and value
    ]
    allowed = set(required + optional)
    configured = policy.get("context_query_supplement_classes")
    if not isinstance(configured, list):
        return required
    values: list[str] = []
    for raw in configured:
        if not isinstance(raw, str) or raw not in allowed or raw in values:
            continue
        values.append(raw)
    return values


def _append_query_plan(
    plan: list[tuple[str | None, str, int | None, str | None]],
    seen_queries: set[str],
    *,
    context_class: str,
    query: str,
    limit: int,
    attribution_path: str | None = None,
) -> None:
    normalized = query.strip()
    folded = normalized.casefold()
    if not normalized or folded in seen_queries:
        return
    seen_queries.add(folded)
    plan.append((context_class, normalized, limit, attribution_path))


def _context_query_plan(
    policy: dict[str, Any], query: str
) -> list[tuple[str | None, str, int | None, str | None]]:
    plan: list[tuple[str | None, str, int | None, str | None]] = [(None, query, None, None)]
    term_mapping = policy.get("context_query_terms")
    exact_path_mapping = policy.get("context_query_exact_path_templates")
    if not isinstance(term_mapping, dict) and not isinstance(exact_path_mapping, dict):
        return plan
    try:
        per_class_limit = max(1, int(policy.get("context_query_max_candidates", 4)))
    except (TypeError, ValueError):
        per_class_limit = 4
    all_scope = _scope_terms(query)
    seen_queries = {query.casefold().strip()}
    for context_class in _supplement_context_classes(policy):
        scope = _scope_for_context_class(policy, context_class, all_scope)
        scope = _prefer_scope_for_context_class(policy, context_class, scope)
        structured_scope = next((value for value in scope if STRUCTURED_SCOPE.fullmatch(value)), None)

        templates = exact_path_mapping.get(context_class) if isinstance(exact_path_mapping, dict) else None
        if isinstance(templates, list):
            for template in templates:
                if not isinstance(template, str) or not template.strip():
                    continue
                if "{scope}" in template:
                    if not structured_scope:
                        continue
                    rendered_path = template.replace("{scope}", structured_scope).strip()
                else:
                    rendered_path = template.strip()
                _append_query_plan(
                    plan,
                    seen_queries,
                    context_class=context_class,
                    query=rendered_path,
                    limit=per_class_limit,
                    attribution_path=rendered_path,
                )

        if not isinstance(term_mapping, dict) or context_class not in term_mapping:
            continue
        terms = term_mapping.get(context_class)
        if not isinstance(terms, list):
            continue
        normalized_terms = [str(value).strip() for value in terms if isinstance(value, str) and value.strip()]
        class_query = " ".join([*scope, *normalized_terms]).strip()
        if not class_query:
            continue
        _append_query_plan(
            plan,
            seen_queries,
            context_class=context_class,
            query=class_query,
            limit=per_class_limit,
        )
    return plan


def _candidate_attributable(
    raw: Any,
    *,
    context_class: str | None,
    attribution_path: str | None,
    attribution_prefixes: list[str] | None,
) -> bool:
    if context_class is None or not isinstance(raw, dict):
        return False
    path = raw.get("path")
    if not isinstance(path, str):
        return False
    if attribution_prefixes is not None and not any(
        path.startswith(prefix) for prefix in attribution_prefixes
    ):
        return False
    return attribution_path is None or path == attribution_path


def _merge_candidates(
    merged: dict[tuple[str, str], dict[str, Any]],
    order: list[tuple[str, str]],
    candidates: list[Any],
    *,
    context_class: str | None,
    limit: int | None,
    attribution_path: str | None,
    attribution_prefixes: list[str] | None,
) -> None:
    valid = [
        raw
        for raw in candidates
        if isinstance(raw, dict)
        and isinstance(raw.get("module_id"), str)
        and isinstance(raw.get("path"), str)
    ]
    if limit is None:
        selected = valid
    else:
        attributable = [
            raw
            for raw in valid
            if _candidate_attributable(
                raw,
                context_class=context_class,
                attribution_path=attribution_path,
                attribution_prefixes=attribution_prefixes,
            )
        ]
        related = [raw for raw in valid if raw not in attributable]
        selected = [*attributable, *related][:limit]

    for raw in selected:
        module_id = raw["module_id"]
        path = raw["path"]
        key = (module_id, path)
        if key not in merged:
            candidate = dict(raw)
            candidate["retrieval_context_classes"] = []
            merged[key] = candidate
            order.append(key)
        if _candidate_attributable(
            raw,
            context_class=context_class,
            attribution_path=attribution_path,
            attribution_prefixes=attribution_prefixes,
        ):
            classes = merged[key].setdefault("retrieval_context_classes", [])
            if context_class not in classes:
                classes.append(context_class)
                classes.sort()

        # Product intent is authoritative only for PRD sources.  Overlay
        # documents may share the same PRD identifier but must never inherit
        # this semantic class from broad or identifier-based queries.
        classes = merged[key].setdefault("retrieval_context_classes", [])
        if context_class == "product-intent" and path.startswith("docs/architecture/overlays/"):
            if "product-intent" in classes:
                classes.remove("product-intent")


def prepare(root: Path, *, consumer: str, query: str, request_id: str | None = None) -> dict[str, Any]:
    snapshot_path = root / "knowledge/snapshots/repository-source-snapshot.v1.json"
    required_generated = [
        snapshot_path,
        root / "knowledge/catalogs/repository-knowledge-catalog.v1.json",
        root / "knowledge/projections/consumer-projections.v1.json",
        root / "knowledge/policies/consumer-policies.v1.json",
    ]
    if not all(path.is_file() for path in required_generated):
        rid = request_id or _request_id(consumer, query, None)
        return _fallback(
            consumer=consumer,
            query=query,
            request_id=rid,
            reason="generated_knowledge_missing",
        )

    try:
        snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        rid = request_id or _request_id(consumer, query, None)
        return _fallback(
            consumer=consumer,
            query=query,
            request_id=rid,
            reason="source_snapshot_invalid",
        )

    commit = snapshot.get("commit")
    ref = snapshot.get("ref")
    rid = request_id or _request_id(consumer, query, commit if isinstance(commit, str) else None)
    if not isinstance(commit, str) or not isinstance(ref, str):
        return _fallback(
            consumer=consumer,
            query=query,
            request_id=rid,
            reason="source_snapshot_invalid",
            snapshot=snapshot if isinstance(snapshot, dict) else None,
        )

    policy = _consumer_policy(root, consumer)
    if policy is None:
        return _fallback(
            consumer=consumer,
            query=query,
            request_id=rid,
            reason="consumer_policy_invalid",
            snapshot={"ref": ref, "commit": commit},
        )

    merged: dict[tuple[str, str], dict[str, Any]] = {}
    order: list[tuple[str, str]] = []
    statuses: list[str] = []
    for plan_index, (context_class, locator_query, limit, attribution_path) in enumerate(
        _context_query_plan(policy, query)
    ):
        suffix = context_class or "base"
        request = {
            "schema_version": "newrouge.knowledge-locator-request.v1",
            "request_id": f"{rid}:{suffix}:{plan_index}",
            "consumer": consumer,
            "query": locator_query,
            "snapshot": {"ref": ref, "commit": commit},
            "policy_revision": POLICY_REVISION,
        }
        returncode, result, error = _run_locator(root, request)
        if returncode or result is None:
            return _fallback(
                consumer=consumer,
                query=query,
                request_id=rid,
                reason=error or "knowledge_locator_failed",
                snapshot=request["snapshot"],
            )
        if result.get("status") == "blocked":
            return _fallback(
                consumer=consumer,
                query=query,
                request_id=rid,
                reason="knowledge_locator_blocked",
                snapshot=request["snapshot"],
            )
        locator_status = str(result.get("status") or "insufficient_match")
        statuses.append(locator_status)
        candidates = result.get("candidates")
        if not isinstance(candidates, list):
            return _fallback(
                consumer=consumer,
                query=query,
                request_id=rid,
                reason="knowledge_locator_result_invalid",
                snapshot=request["snapshot"],
            )
        _merge_candidates(
            merged,
            order,
            candidates,
            context_class=context_class,
            limit=limit,
            attribution_path=attribution_path,
            attribution_prefixes=_attribution_prefixes(policy, context_class),
        )

    locator_status = "matched" if "matched" in statuses else "insufficient_match"
    candidates = [merged[key] for key in order]
    return {
        "schema_version": "newrouge.knowledge-context-candidates.v1",
        "mode": "shadow",
        "consumer": consumer,
        "request_id": rid,
        "query": query,
        "status": "shadow_ready",
        "locator_status": locator_status,
        "snapshot": {"ref": ref, "commit": commit},
        "policy_revision": POLICY_REVISION,
        "semantic_decision_required": True,
        "freeze_state": "unfrozen",
        "candidates": candidates,
        "fallback": {
            "required": False,
            "reason": None,
            "authority_route": "docs/agents/13-rag-sources-and-session-ssot.md",
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Prepare a non-authoritative shadow knowledge candidate bundle for a newrouge workflow consumer."
    )
    parser.add_argument("--repository-root", type=Path, default=Path.cwd())
    parser.add_argument("--consumer", choices=CONSUMERS, required=True)
    parser.add_argument("--query", required=True)
    parser.add_argument("--request-id")
    parser.add_argument("--output", type=Path)
    parser.add_argument(
        "--enforce",
        action="store_true",
        help="Return non-zero when generated knowledge is unavailable or blocked. Default shadow mode is non-blocking.",
    )
    args = parser.parse_args()
    root = args.repository_root.resolve()
    bundle = prepare(
        root,
        consumer=args.consumer,
        query=args.query,
        request_id=args.request_id,
    )
    if args.output:
        output = args.output if args.output.is_absolute() else root / args.output
        _atomic_json(output, bundle)
    print(json.dumps(bundle, ensure_ascii=False, indent=2, sort_keys=True))
    return 2 if args.enforce and bundle["status"] == "fallback_required" else 0


if __name__ == "__main__":
    raise SystemExit(main())
