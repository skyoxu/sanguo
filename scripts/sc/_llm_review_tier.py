from __future__ import annotations

import re
from typing import Any

from _taskmaster import TaskmasterTriplet


_TIER_ORDER = {"minimal": 0, "targeted": 1, "full": 2}
_ALLOWED_TIERS = {"auto", *tuple(_TIER_ORDER.keys())}
_FULL_RISK_KEYWORD_ALIASES = {
    "security": (
        "security",
        "secure",
        "auth",
        "authentication",
        "authorization",
        "permission",
        "permissions",
        "privacy",
        "secret",
        "secrets",
        "credential",
        "credentials",
        "token",
        "tokens",
        "encryption",
        "audit",
        "compliance",
    ),
    "contract": (
        "contract",
        "contracts",
        "contractref",
        "contractrefs",
        "contract_ref",
        "contract_refs",
        "eventtype",
        "eventtypes",
        "dto",
        "dtos",
        "schema",
        "schemas",
    ),
    "workflow": (
        "workflow",
        "workflows",
        "github actions",
    ),
    "pipeline": (
        "pipeline",
        "pipelines",
    ),
    "ci": (
        "ci",
        "continuous integration",
    ),
    "release": (
        "release",
        "releases",
        "deploy",
        "deployment",
        "rollback",
    ),
    "adr": (
        "adr",
        "adrs",
    ),
    "architecture": (
        "architecture",
        "architect",
        "architectural",
    ),
    "gate": (
        "gate",
        "gates",
        "gating",
        "quality gate",
        "quality gates",
    ),
    "sentry": (
        "sentry",
        "observability",
        "telemetry",
        "crash free",
        "crash-free",
    ),
    "performance": (
        "performance",
        "perf",
        "latency",
        "p95",
        "p99",
        "budget",
        "budgets",
    ),
}
_ALLOWED_WRITEBACK_MODES = {"conservative", "materialize"}


def _normalize_tier(value: Any) -> str | None:
    raw = str(value or "").strip().lower()
    return raw if raw in _ALLOWED_TIERS else None


def _max_tier(left: str, right: str) -> str:
    return left if _TIER_ORDER[left] >= _TIER_ORDER[right] else right


def _default_tier_for_profile(delivery_profile: str) -> str:
    profile = str(delivery_profile or "").strip().lower()
    if profile == "playable-ea":
        return "minimal"
    if profile == "standard":
        return "full"
    return "targeted"


def _view_field(entry: dict[str, Any] | None, *keys: str) -> Any | None:
    if not isinstance(entry, dict):
        return None
    for key in keys:
        if key in entry:
            return entry.get(key)
    return None


def _requested_tier(triplet: TaskmasterTriplet | None) -> tuple[str, list[str], list[str]]:
    if not triplet:
        return "auto", [], []
    sources: list[tuple[str, str]] = []
    candidates = [
        ("master", _normalize_tier(triplet.master.get("semantic_review_tier") or triplet.master.get("semanticReviewTier"))),
        ("back", _normalize_tier(_view_field(triplet.back, "semantic_review_tier", "semanticReviewTier"))),
        ("gameplay", _normalize_tier(_view_field(triplet.gameplay, "semantic_review_tier", "semanticReviewTier"))),
    ]
    for source, tier in candidates:
        if tier:
            sources.append((source, tier))
    if not sources:
        return "auto", [], []
    explicit = [tier for _, tier in sources if tier != "auto"]
    if not explicit:
        return "auto", [source for source, _ in sources], []
    chosen = explicit[0]
    for tier in explicit[1:]:
        chosen = _max_tier(chosen, tier)
    distinct = sorted({tier for _, tier in sources})
    reasons: list[str] = []
    if len(distinct) > 1:
        detail = ",".join(f"{source}:{tier}" for source, tier in sources)
        reasons.append(f"conflicting_requested_tiers({detail})")
    return chosen, [source for source, _ in sources], reasons


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def _has_contract_refs(triplet: TaskmasterTriplet | None) -> bool:
    if not triplet:
        return False
    for entry in (triplet.master, triplet.back or {}, triplet.gameplay or {}):
        refs = entry.get("contractRefs") if isinstance(entry, dict) else None
        if not refs:
            refs = entry.get("contract_refs") if isinstance(entry, dict) else None
        if _string_list(refs):
            return True
    return False


def _text_blob(triplet: TaskmasterTriplet | None) -> str:
    if not triplet:
        return ""
    parts: list[str] = []
    for entry in (triplet.master, triplet.back or {}, triplet.gameplay or {}):
        if not isinstance(entry, dict):
            continue
        for key in ("title", "details", "description", "layer", "owner"):
            value = entry.get(key)
            if isinstance(value, str) and value.strip():
                parts.append(value.strip().lower())
        for key in ("labels", "tags", "chapter_refs", "adr_refs", "overlay_refs"):
            parts.extend(x.lower() for x in _string_list(entry.get(key)))
    return "\n".join(parts)


def _has_keyword(blob: str, term: str) -> bool:
    pattern = rf"(?<![a-z0-9]){re.escape(term.lower())}(?![a-z0-9])"
    return re.search(pattern, str(blob or "").lower()) is not None


def _priority(triplet: TaskmasterTriplet | None) -> str:
    if not triplet:
        return ""
    return str(triplet.master.get("priority") or "").strip().upper()


def _is_full_risk(triplet: TaskmasterTriplet | None) -> tuple[bool, list[str]]:
    reasons: list[str] = []
    if _has_contract_refs(triplet):
        reasons.append("contract_refs_present")
    blob = _text_blob(triplet)
    keyword_hits = sorted(
        {
            canonical
            for canonical, aliases in _FULL_RISK_KEYWORD_ALIASES.items()
            if any(_has_keyword(blob, alias) for alias in aliases)
        }
    )
    if keyword_hits:
        reasons.append(f"high_risk_keywords({','.join(keyword_hits)})")
    if _priority(triplet) == "P0":
        reasons.append("priority_p0")
    return bool(reasons), reasons


def _config_for_tier(*, tier: str, profile_defaults: dict[str, Any]) -> dict[str, Any]:
    base_agents = str(profile_defaults.get("agents") or "all")
    base_gate = str(profile_defaults.get("semantic_gate") or "warn")
    base_timeout = int(profile_defaults.get("timeout_sec") or 900)
    base_agent_timeout = int(profile_defaults.get("agent_timeout_sec") or 300)
    base_strict = bool(profile_defaults.get("strict", False))
    if tier == "full":
        return {
            "agents": base_agents,
            "semantic_gate": base_gate,
            "timeout_sec": base_timeout,
            "agent_timeout_sec": base_agent_timeout,
            "strict": base_strict,
        }
    if tier == "targeted":
        return {
            "agents": base_agents,
            "semantic_gate": "warn",
            "timeout_sec": min(base_timeout, 420),
            "agent_timeout_sec": min(base_agent_timeout, 150),
            "strict": False,
        }
    return {
        "agents": base_agents,
        "semantic_gate": "skip",
        "timeout_sec": min(base_timeout, 300),
        "agent_timeout_sec": min(base_agent_timeout, 120),
        "strict": False,
    }


def resolve_llm_review_tier_plan(
    *,
    delivery_profile: str,
    triplet: TaskmasterTriplet | None,
    profile_defaults: dict[str, Any],
) -> dict[str, Any]:
    requested_tier, requested_sources, request_notes = _requested_tier(triplet)
    profile_default_tier = _default_tier_for_profile(delivery_profile)
    base_tier = profile_default_tier if requested_tier == "auto" else requested_tier
    effective_tier = base_tier
    escalation_reasons: list[str] = list(request_notes)

    if _priority(triplet) == "P1" and effective_tier == "minimal":
        effective_tier = "targeted"
        escalation_reasons.append("priority_p1")

    full_risk, risk_reasons = _is_full_risk(triplet)
    if full_risk and effective_tier != "full":
        effective_tier = "full"
        escalation_reasons.extend(risk_reasons)

    config = _config_for_tier(tier=effective_tier, profile_defaults=profile_defaults)
    return {
        "requested_tier": requested_tier,
        "requested_sources": requested_sources,
        "profile_default_tier": profile_default_tier,
        "effective_tier": effective_tier,
        "escalation_reasons": escalation_reasons,
        **config,
    }


def _clone_entry_without_requested_tier(entry: dict[str, Any] | None) -> dict[str, Any] | None:
    if not isinstance(entry, dict):
        return None
    cloned = dict(entry)
    cloned.pop("semantic_review_tier", None)
    cloned.pop("semanticReviewTier", None)
    return cloned


def _sanitize_triplet_for_writeback(triplet: TaskmasterTriplet | None) -> TaskmasterTriplet | None:
    if triplet is None:
        return None
    return TaskmasterTriplet(
        task_id=triplet.task_id,
        master=_clone_entry_without_requested_tier(triplet.master) or {},
        back=_clone_entry_without_requested_tier(triplet.back),
        gameplay=_clone_entry_without_requested_tier(triplet.gameplay),
        tasks_json_path=triplet.tasks_json_path,
        tasks_back_path=triplet.tasks_back_path,
        tasks_gameplay_path=triplet.tasks_gameplay_path,
        taskdoc_path=triplet.taskdoc_path,
    )


def suggest_llm_review_tier_writeback(
    *,
    delivery_profile: str,
    triplet: TaskmasterTriplet | None,
    mode: str = "conservative",
) -> dict[str, Any]:
    normalized_mode = str(mode or "").strip().lower()
    if normalized_mode not in _ALLOWED_WRITEBACK_MODES:
        raise ValueError(f"Unsupported writeback mode: {mode}")

    sanitized_triplet = _sanitize_triplet_for_writeback(triplet)
    preview = resolve_llm_review_tier_plan(
        delivery_profile=delivery_profile,
        triplet=sanitized_triplet,
        profile_defaults={},
    )
    full_risk, full_reasons = _is_full_risk(sanitized_triplet)

    if normalized_mode == "materialize":
        return {
            "mode": normalized_mode,
            "tier": preview["effective_tier"],
            "reason": "materialized_effective_tier",
            "preview_effective_tier": preview["effective_tier"],
            "preview_profile_default_tier": preview["profile_default_tier"],
            "escalation_reasons": list(preview["escalation_reasons"]),
        }

    reason = "defer_to_runtime_profile"
    escalation_reasons: list[str] = []
    tier = "auto"
    if full_risk:
        tier = "full"
        reason = "full_risk_floor"
        escalation_reasons = list(full_reasons)
    return {
        "mode": normalized_mode,
        "tier": tier,
        "reason": reason,
        "preview_effective_tier": preview["effective_tier"],
        "preview_profile_default_tier": preview["profile_default_tier"],
        "escalation_reasons": escalation_reasons,
    }
