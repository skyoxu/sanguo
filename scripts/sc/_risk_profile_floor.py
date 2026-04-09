from __future__ import annotations

from typing import Any

from _delivery_profile import default_security_profile_for_delivery, resolve_delivery_profile


PROFILE_ORDER = {
    "playable-ea": 0,
    "fast-ship": 1,
    "standard": 2,
}

SEMANTIC_PREFIXES = (
    ".taskmaster/",
    "examples/taskmaster/",
    "docs/architecture/",
    "docs/adr/",
    "docs/prd/",
    "execution-plans/",
    "decision-logs/",
)

HIGH_RISK_CODE_PREFIXES = (
    "game.core/",
    "game.godot/",
    "game.core.tests/",
    "tests.godot/",
)

HIGH_RISK_TOOLING_PREFIXES = (
    "scripts/sc/",
    "scripts/python/",
    ".github/",
)

HIGH_RISK_EXACT = {
    "project.godot",
    "workflow.md",
    "workflow.example.md",
}

CONTRACT_PREFIX = "game.core/contracts/"


def _normalize_paths(values: list[str] | tuple[str, ...] | None) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in values or []:
        normalized = str(item or "").strip().replace("\\", "/").lower()
        if normalized and normalized not in seen:
            seen.add(normalized)
            out.append(normalized)
    return out


def _risk_hits(change_scope: dict[str, Any] | None) -> dict[str, list[str]]:
    scope = change_scope if isinstance(change_scope, dict) else {}
    changed_paths = _normalize_paths(list(scope.get("changed_paths") or []))
    unsafe_paths = _normalize_paths(list(scope.get("unsafe_paths") or []))
    semantic_hits = [path for path in changed_paths if any(path.startswith(prefix) for prefix in SEMANTIC_PREFIXES)]
    code_hits = [
        path
        for path in changed_paths
        if any(path.startswith(prefix) for prefix in HIGH_RISK_CODE_PREFIXES) or path == "project.godot"
    ]
    tooling_hits = [
        path
        for path in changed_paths
        if any(path.startswith(prefix) for prefix in HIGH_RISK_TOOLING_PREFIXES) or path in HIGH_RISK_EXACT
    ]
    contract_hits = [path for path in changed_paths if path.startswith(CONTRACT_PREFIX)]
    return {
        "changed_paths": changed_paths,
        "unsafe_paths": unsafe_paths,
        "semantic_hits": semantic_hits,
        "code_hits": code_hits,
        "tooling_hits": tooling_hits,
        "contract_hits": contract_hits,
    }


def requires_security_auditor_for_change_scope(change_scope: dict[str, Any] | None) -> bool:
    hits = _risk_hits(change_scope)
    return bool(hits["code_hits"] or hits["tooling_hits"] or hits["contract_hits"])


def derive_delivery_profile_floor(
    *,
    delivery_profile: str,
    security_profile: str,
    change_scope: dict[str, Any] | None,
    explicit_security_profile: bool,
) -> dict[str, Any]:
    resolved_delivery = resolve_delivery_profile(delivery_profile)
    resolved_security = str(security_profile or "").strip().lower() or default_security_profile_for_delivery(resolved_delivery)
    hits = _risk_hits(change_scope)
    should_floor_fast_ship = bool(
        hits["tooling_hits"]
        or hits["contract_hits"]
        or hits["code_hits"]
        or (hits["semantic_hits"] and hits["unsafe_paths"])
    )
    target_delivery = "fast-ship" if should_floor_fast_ship else resolved_delivery
    applied = PROFILE_ORDER.get(target_delivery, 0) > PROFILE_ORDER.get(resolved_delivery, 0)
    target_security = resolved_security
    if applied and not explicit_security_profile:
        target_security = default_security_profile_for_delivery(target_delivery)
    return {
        "applied": applied,
        "delivery_profile": target_delivery,
        "security_profile": target_security,
        "reason": "risky-change-floor" if applied else "",
        "changed_paths": hits["changed_paths"],
        "unsafe_paths": hits["unsafe_paths"],
        "code_hits": hits["code_hits"],
        "tooling_hits": hits["tooling_hits"],
        "contract_hits": hits["contract_hits"],
        "semantic_hits": hits["semantic_hits"],
    }
